#!/usr/bin/env python3
"""Синхронізація постів з Instagram у статичний сайт Lys Montage.

Тягне останні публікації бізнес-акаунта через Instagram API with Instagram Login
(host graph.instagram.com, scope instagram_business_basic), складає локальні копії
зображень і пише `instagram.json`, який читає `assets/js/instagram.js`.

Запуск раз на добу (systemd timer або cron). Старий `instagram.json` ніколи не
перезаписується на порожній: будь-яка помилка завершує роботу з кодом 1 і залишає
попередній результат на місці, тож сайт не «згасає» через збій API.

Документація з налаштування — docs/instagram-sync.md
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

GRAPH_HOST = "https://graph.instagram.com"
MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,permalink,"
    "thumbnail_url,timestamp,children{id,media_type,media_url,thumbnail_url}"
)
# Публікації цих типів у галерею не йдуть: сторіс недовговічні, реклама — не роботи.
SKIP_PRODUCT_TYPES = {"STORY", "AD"}
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
USER_AGENT = "lys-montage-ig-sync/1.0"
# Токен живе 60 днів; обновлюємо заздалегідь, щоб кілька пропущених запусків не вбили доступ.
REFRESH_WHEN_DAYS_LEFT = 20
TITLE_MAX = 64
TEXT_MAX = 190


def load_dotenv(path: Path) -> None:
    """Підхоплює локальний .env для запуску з машини розробника.

    На сервері змінні дає systemd (EnvironmentFile), тож там файлу немає.
    Уже виставлені змінні оточення мають пріоритет — .env їх не перебиває.
    """
    try:
        raw = path.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}Z] {msg}", flush=True)


class SyncError(RuntimeError):
    """Помилка, після якої попередній instagram.json лишається недоторканим."""


# --- HTTP ------------------------------------------------------------------


def http_get(url: str, *, binary: bool = False):
    """GET з повторами. Повертає (bytes, headers) або розпарсений JSON."""
    last: Exception | None = None
    for attempt in range(1, HTTP_RETRIES + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                if binary:
                    return resp.read(MAX_IMAGE_BYTES + 1), resp.headers
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:400]
            last = SyncError(f"HTTP {exc.code} від {_redact(url)}: {body}")
            # 4xx — це не тимчасова проблема, повторювати немає сенсу.
            if 400 <= exc.code < 500 and exc.code != 429:
                raise last from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = SyncError(f"Запит до {_redact(url)} не вдався: {exc}")
        if attempt < HTTP_RETRIES:
            delay = 2**attempt
            log(f"  спроба {attempt}/{HTTP_RETRIES} невдала, повтор за {delay} с")
            time.sleep(delay)
    raise last if last else SyncError(f"Запит до {_redact(url)} не вдався")


def _redact(url: str) -> str:
    return re.sub(r"(access_token=)[^&]+", r"\1***", url)


# --- Токен -----------------------------------------------------------------


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        log(f"УВАГА: не читається {path} ({exc}) — починаємо зі свіжого стану")
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), "utf-8")
    os.chmod(tmp, 0o600)  # у файлі лежить access token
    os.replace(tmp, path)


def resolve_token(state_path: Path, env_token: str) -> str:
    """Бере збережений токен (він свіжіший за env) і за потреби продовжує його."""
    state = load_state(state_path)
    token = state.get("access_token") or env_token
    if not token:
        raise SyncError("Немає токена: задай IG_ACCESS_TOKEN або заповни файл стану")

    expires_at = state.get("expires_at", 0)
    obtained_at = state.get("obtained_at", 0)
    now = time.time()
    days_left = (expires_at - now) / 86400 if expires_at else None

    if days_left is not None:
        log(f"Токен дійсний ще {days_left:.1f} дн.")
    if days_left is not None and days_left > REFRESH_WHEN_DAYS_LEFT:
        return token
    # Instagram відмовляє в продовженні токена, молодшого за 24 години.
    if obtained_at and now - obtained_at < 24 * 3600:
        log("Токен молодший за 24 год — продовження пропущено")
        return token

    log("Продовжую long-lived токен")
    url = f"{GRAPH_HOST}/refresh_access_token?" + urllib.parse.urlencode(
        {"grant_type": "ig_refresh_token", "access_token": token}
    )
    try:
        data = http_get(url)
        new_token = data["access_token"]
        ttl = int(data.get("expires_in", 60 * 86400))
    except (SyncError, KeyError, TypeError, ValueError) as exc:
        # Протермінований токен — єдина помилка, яку мусить побачити людина.
        if days_left is not None and days_left <= 0:
            raise SyncError(f"Токен протермінований і не продовжується: {exc}") from exc
        log(f"УВАГА: продовження не вдалося ({exc}) — працюю поточним токеном")
        return token

    save_state(
        state_path,
        {"access_token": new_token, "obtained_at": now, "expires_at": now + ttl},
    )
    log(f"Токен продовжено, новий строк — {ttl / 86400:.0f} дн.")
    return new_token


# --- Підписи ---------------------------------------------------------------

HASHTAG_LINE = re.compile(r"^(?:#[^\s#]+\s*)+$")
TRAILING_HASHTAGS = re.compile(r"(?:\s*#[^\s#]+)+\s*$")
# Декоративні розділювачі й маркери на початку рядка в підписах Instagram.
LEADING_DECOR = re.compile(r"^[\s•·▪◾✅✔️➕➖—–\-*_=~.]+")


def clean_caption(caption: str) -> tuple[str, str]:
    """Робить з підпису Instagram пару (заголовок, текст) для картки."""
    if not caption:
        return "", ""

    lines = []
    for raw in caption.replace("\r", "").split("\n"):
        line = LEADING_DECOR.sub("", raw).strip()
        if not line or HASHTAG_LINE.match(line):
            continue
        line = TRAILING_HASHTAGS.sub("", line).strip()
        if line:
            lines.append(line)

    if not lines:
        return "", ""

    title = lines[0]
    # Перелічення в підписах часто йдуть окремими рядками — тримаємо межі видимими.
    rest = " · ".join(lines[1:])
    # Довгий перший рядок ріжемо по реченню, а хвіст віддаємо в текст картки.
    if len(title) > TITLE_MAX:
        cut = _split_point(title, TITLE_MAX)
        rest = (title[cut:].strip() + " · " + rest).strip(" ·")
        title = title[:cut].strip(" ,;:—–-")

    return title, truncate(rest, TEXT_MAX)


def _split_point(text: str, limit: int) -> int:
    window = text[: limit + 1]
    for sep in (". ", "! ", "? ", ", ", " — ", " "):
        idx = window.rfind(sep)
        if idx > limit // 2:
            return idx + (len(sep) if sep[0] in ".!?" else 0)
    return limit


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    idx = text.rfind(" ", 0, limit)
    return text[: idx if idx > limit // 2 else limit].rstrip(" ,;:.—–-") + "…"


# --- Зображення ------------------------------------------------------------


def pick_image_url(item: dict) -> str | None:
    """Обирає URL картинки для обкладинки картки."""
    media_type = item.get("media_type")
    if media_type == "IMAGE":
        return item.get("media_url")
    if media_type == "VIDEO":
        # media_url відео нам не підходить — беремо кадр-обкладинку.
        return item.get("thumbnail_url")
    if media_type == "CAROUSEL_ALBUM":
        children = (item.get("children") or {}).get("data") or []
        for child in children:
            url = pick_image_url(child)
            if url:
                return url
    return None


def download_image(url: str, images_dir: Path, media_id: str) -> tuple[str, int, int]:
    """Качає обкладинку. CDN-посилання Instagram протермінуються, тож тримаємо копію."""
    existing = next(iter(sorted(images_dir.glob(f"{media_id}.*"))), None)
    if existing:
        size = probe_size(existing)
        return existing.name, size[0], size[1]

    payload, headers = http_get(url, binary=True)
    if len(payload) > MAX_IMAGE_BYTES:
        raise SyncError(f"{media_id}: зображення більше за {MAX_IMAGE_BYTES} байт")

    content_type = (headers.get("Content-Type") or "").split(";")[0].strip().lower()
    suffix = ALLOWED_IMAGE_TYPES.get(content_type)
    if not suffix:
        raise SyncError(f"{media_id}: очікували зображення, прийшло {content_type!r}")

    images_dir.mkdir(parents=True, exist_ok=True)
    tmp = images_dir / f".{media_id}.part"
    tmp.write_bytes(payload)
    final = images_dir / f"{media_id}{suffix}"
    optimized = optimize(tmp, final)
    if not optimized:
        os.replace(tmp, final)
    else:
        tmp.unlink(missing_ok=True)

    width, height = probe_size(final)
    log(f"  ↓ {final.name} ({final.stat().st_size // 1024} КБ, {width}×{height})")
    return final.name, width, height


def optimize(src: Path, dest: Path) -> bool:
    """Стискає й розвертає EXIF через Pillow. Без Pillow — просто пропускаємо."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return False
    try:
        with Image.open(src) as img:
            img = ImageOps.exif_transpose(img)
            if img.width > 1200:
                img = img.resize(
                    (1200, round(img.height * 1200 / img.width)), Image.LANCZOS
                )
            if dest.suffix == ".jpg":
                img.convert("RGB").save(dest, "JPEG", quality=82, optimize=True, progressive=True)
            else:
                img.save(dest, optimize=True)
        return True
    except Exception as exc:  # noqa: BLE001 — зіпсоване фото не має валити синк
        log(f"  УВАГА: стиснення {src.name} не вдалося ({exc}) — беру оригінал")
        return False


def probe_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.width, img.height
    except Exception:  # noqa: BLE001
        return 0, 0


# --- Основний прохід -------------------------------------------------------


def fetch_media(token: str, limit: int, api_version: str) -> list[dict]:
    prefix = f"/{api_version}" if api_version else ""
    url = f"{GRAPH_HOST}{prefix}/me/media?" + urllib.parse.urlencode(
        {"fields": MEDIA_FIELDS, "limit": limit, "access_token": token}
    )
    data = http_get(url)
    items = data.get("data")
    if not isinstance(items, list):
        raise SyncError(f"Несподівана відповідь API: {str(data)[:300]}")
    return items


def load_overrides(path: Path) -> dict:
    """Ручні правки: свій заголовок/текст або приховування поста."""
    if not path:
        return {}
    try:
        raw = json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        log(f"УВАГА: {path} не читається ({exc}) — правки проігноровані")
        return {}
    return raw.get("posts", raw) if isinstance(raw, dict) else {}


def build_posts(items: list[dict], images_dir: Path, url_prefix: str, overrides: dict,
                max_posts: int) -> list[dict]:
    posts: list[dict] = []
    for item in items:
        media_id = str(item.get("id", ""))
        if not media_id:
            continue
        rule = overrides.get(media_id, {})
        if rule.get("hide"):
            log(f"  ∅ {media_id} прихований через ig-overrides.json")
            continue
        if item.get("media_product_type") in SKIP_PRODUCT_TYPES:
            continue

        image_url = pick_image_url(item)
        if not image_url:
            log(f"  ∅ {media_id}: немає доступного зображення — пропуск")
            continue
        try:
            filename, width, height = download_image(image_url, images_dir, media_id)
        except SyncError as exc:
            log(f"  УВАГА: {exc} — пропуск")
            continue

        title, text = clean_caption(item.get("caption") or "")
        post = {
            "id": media_id,
            "src": f"{url_prefix}/{filename}",
            "title": rule.get("title") or title,
            "text": rule.get("text", text),
            "permalink": item.get("permalink") or "https://www.instagram.com/lys_montag/",
            "timestamp": item.get("timestamp") or "",
            "type": item.get("media_type") or "IMAGE",
        }
        # Розміри є лише якщо Pillow зміг прочитати файл; нулі в розмітку не пускаємо.
        if width and height:
            post["width"], post["height"] = width, height
        posts.append(post)
        if len(posts) >= max_posts:
            break
    return posts


def prune_images(images_dir: Path, keep: set[str]) -> None:
    if not images_dir.is_dir():
        return
    for path in images_dir.iterdir():
        if path.is_file() and path.name not in keep:
            path.unlink()
            log(f"  × прибрано {path.name}")


def write_json(path: Path, posts: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": "https://www.instagram.com/lys_montag/",
        "posts": posts,
    }
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".instagram-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.chmod(tmp_name, 0o644)
    os.replace(tmp_name, path)  # заміна атомарна: nginx ніколи не бачить напівфайл


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    parser = argparse.ArgumentParser(description="Синхронізація постів Instagram у сайт")
    parser.add_argument("--json-out", default=os.environ.get("IG_JSON_OUT", root / "assets/data/instagram.json"))
    parser.add_argument("--images-out", default=os.environ.get("IG_IMAGES_OUT", root / "assets/instagram"))
    parser.add_argument("--url-prefix", default=os.environ.get("IG_URL_PREFIX", "assets/instagram"))
    parser.add_argument("--overrides", default=os.environ.get("IG_OVERRIDES", root / "tools/ig-overrides.json"))
    parser.add_argument("--state", default=os.environ.get("IG_STATE", root / ".ig-state/token.json"))
    parser.add_argument("--limit", type=int, default=int(os.environ.get("IG_LIMIT", "12")),
                        help="скільки публікацій запросити в API")
    parser.add_argument("--max-posts", type=int, default=int(os.environ.get("IG_MAX_POSTS", "9")),
                        help="скільки карток показати на сайті")
    parser.add_argument("--api-version", default=os.environ.get("IG_API_VERSION", ""),
                        help="напр. v23.0; порожнє — версія за замовчуванням graph.instagram.com")
    args = parser.parse_args()

    json_out = Path(args.json_out)
    images_out = Path(args.images_out)
    state_path = Path(args.state)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.parent / "ig_sync.lock"
    with open(lock_path, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log("Інший запуск ще працює — виходжу")
            return 0

        try:
            token = resolve_token(state_path, os.environ.get("IG_ACCESS_TOKEN", "").strip())
            log(f"Запрошую до {args.limit} публікацій")
            items = fetch_media(token, args.limit, args.api_version)
            log(f"API віддав {len(items)} публікацій")

            overrides = load_overrides(Path(args.overrides) if args.overrides else None)
            posts = build_posts(items, images_out, args.url_prefix.rstrip("/"), overrides, args.max_posts)
            if not posts:
                raise SyncError("Жодного придатного поста — лишаю попередній instagram.json")

            prune_images(images_out, {Path(p["src"]).name for p in posts})
            write_json(json_out, posts)
            log(f"Готово: {len(posts)} постів → {json_out}")
            return 0
        except SyncError as exc:
            log(f"ПОМИЛКА: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001
            log(f"НЕОЧІКУВАНА ПОМИЛКА: {type(exc).__name__}: {exc}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
