#!/usr/bin/env bash
# Початкове налаштування сервера Hetzner під Lys Montage.
# Запускати на СВІЖОМУ сервері від root, один раз:
#
#   ssh root@IP 'bash -s' < deploy/bootstrap.sh
#
# Скрипт ідемпотентний — повторний запуск нічого не зламає.
# Після нього лишається два ручні кроки: вписати токен у ig-sync.env
# і випустити сертифікат (обидва описані в docs/instagram-sync.md).
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/shakhanton/Lys_Montage.git}"
BRANCH="${BRANCH:-main}"
BASE=/srv/lys-montage
USER_NAME=lysmontage

log() { printf '\n== %s\n' "$1"; }

[[ $EUID -eq 0 ]] || { echo "Потрібні права root" >&2; exit 1; }

log "Пакети"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx git python3 python3-pil certbot python3-certbot-nginx ufw

log "Часовий пояс (від нього залежить час запуску таймера)"
timedatectl set-timezone Europe/Kyiv

log "Користувач $USER_NAME"
id -u "$USER_NAME" &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin "$USER_NAME"

log "Каталоги в $BASE"
mkdir -p "$BASE"/{data/instagram,state}
if [[ -d "$BASE/repo/.git" ]]; then
  git -C "$BASE/repo" remote set-url origin "$REPO_URL"
  git -C "$BASE/repo" fetch --quiet origin "$BRANCH"
  git -C "$BASE/repo" reset --hard --quiet "origin/$BRANCH"
else
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$BASE/repo"
fi
git config --global --add safe.directory "$BASE/repo"

chown -R "$USER_NAME:$USER_NAME" "$BASE/data" "$BASE/state"
chmod 755 "$BASE" "$BASE/data" "$BASE/data/instagram"
chmod 700 "$BASE/state"

log "Файл з токеном"
if [[ ! -f "$BASE/ig-sync.env" ]]; then
  cat > "$BASE/ig-sync.env" <<'ENVEOF'
# Довгоживучий токен Instagram (instagram_business_basic).
# Як отримати — docs/instagram-sync.md, розділ 1.
# Скрипт сам продовжує токен і зберігає новий у state/token.json,
# тож тут значення потрібне лише для першого запуску.
IG_ACCESS_TOKEN=ВСТАВ_ТОКЕН_СЮДИ

# Скільки публікацій запросити в API і скільки показати на сайті.
IG_LIMIT=12
IG_MAX_POSTS=9
ENVEOF
  echo "створено $BASE/ig-sync.env — токен треба вписати вручну"
else
  echo "$BASE/ig-sync.env уже є, не змінюю"
fi
chown root:"$USER_NAME" "$BASE/ig-sync.env"
chmod 640 "$BASE/ig-sync.env"

log "nginx"
install -m 644 "$BASE/repo/deploy/nginx-lys-montage.conf" /etc/nginx/sites-available/lys-montage
ln -sfn /etc/nginx/sites-available/lys-montage /etc/nginx/sites-enabled/lys-montage
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

log "systemd timer"
install -m 644 "$BASE/repo/deploy/lys-ig-sync.service" /etc/systemd/system/lys-ig-sync.service
install -m 644 "$BASE/repo/deploy/lys-ig-sync.timer" /etc/systemd/system/lys-ig-sync.timer
systemctl daemon-reload
systemctl enable --now lys-ig-sync.timer

log "Фаєрвол"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

log "Готово"
cat <<'DONE'
Лишилось два кроки:

  1. Вписати токен:   nano /srv/lys-montage/ig-sync.env
     Перший запуск:   systemctl start lys-ig-sync.service
     Подивитись лог:  journalctl -u lys-ig-sync.service -n 40 --no-pager

  2. Домен і HTTPS (коли A-запис уже вказує на цей сервер):
     certbot --nginx -d lysmontage.com -d www.lysmontage.com

Розклад таймера: systemctl list-timers lys-ig-sync.timer
DONE
