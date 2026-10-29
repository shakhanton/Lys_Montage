# Автооновлення галереї з Instagram

Секція «Виконані роботи» наповнюється автоматично з бізнес-профілю
[@lys_montag](https://www.instagram.com/lys_montag/). Раз на добу сервер звертається
до Instagram API, забирає останні публікації, зберігає копії фото в себе й
перезаписує `instagram.json`, який читає браузер.

Новий пост у Instagram → максимум за добу він на сайті. Руками нічого робити не треба.

## Як це влаштовано

```
Instagram API (graph.instagram.com)
        │  раз на добу, systemd timer lys-ig-sync.timer
        ▼
tools/ig_sync.py                       на сервері Hetzner
        │  качає фото, чистить підписи
        ▼
/srv/lys-montage/data/
    instagram.json        ← список постів
    instagram/<id>.jpg    ← локальні копії обкладинок
        │  nginx віддає їх як /assets/data/… і /assets/instagram/…
        ▼
assets/js/instagram.js    ← малює картки в секції «Виконані роботи»
```

Три рішення, які варто знати наперед:

- **Фото зберігаємо в себе.** Посилання на картинки, які віддає Instagram,
  протермінуються за кілька днів. Якби сайт посилався на них напряму, галерея
  розсипалася б між запусками.
- **Згенероване не лежить у git.** `instagram.json` і каталог з фото — у `.gitignore`.
  Вони живуть у `/srv/lys-montage/data` і переживають будь-який деплой.
- **Збій не ламає сайт.** Якщо API недоступний, скрипт виходить з помилкою і
  **не чіпає** попередній `instagram.json` — на сайті лишаються вчорашні пости.
  Якщо `instagram.json` зникне зовсім, браузер покаже статичну галерею з `index.html`.

---

## 1. Доступ до Instagram API

Робиться один раз. Кроки нижче виконує **власник профілю** @lys_montag зі свого
акаунта Meta — перешли йому
[`instagram-token-for-client.md`](instagram-token-for-client.md), там те саме
розписано без технічних термінів. Тобі він передає лише готовий токен.

> Цей розділ — та сама процедура стисло, щоб було чим звіритись, якщо клієнт
> застрягне. Під час налаштування 22.10.2026 кроки 1.2–1.4 пройдено в консолі
> вживу; крок 1.5 не вдалося відтворити на особистому акаунті (див. врізку там).

### 1.1. Створити застосунок

Лише якщо застосунку ще немає: <https://developers.facebook.com/apps> →
**Create app** → назва → контактний email → **Next** → випадок використання
**Other** → **Next** → тип **Business** → **Create app**.

### 1.2. Додати use case

Інтерфейс Meta змінився: замість колишнього «Add a product» тепер use cases.

1. На дашборді застосунку — **+ Add use cases**.
2. Фільтр зліва: **Content management**.
3. Відмітити **Manage messaging & content on Instagram** → **Save**.
4. У вікні «Extra steps required…» — **Add to app**.

### 1.3. Додати дозволи

**Use cases → Customize**, зліва обрати **API setup with Instagram login**.

У секції **1. Add required messaging permissions** натиснути
**Add all required permissions** і дочекатися **зеленої галочки**.

> Не пропускати. Поки дозволів немає, кнопка `Generate token` на кроці 1.5
> нічого не робить — мовчки, без повідомлення про помилку.

Додаються `instagram_business_basic`, `instagram_business_manage_comments`,
`instagram_business_manage_messages`. Синку потрібен лише перший, але use case
вимагає всі три.

### 1.4. Підключити акаунт

У секції **2. Generate access tokens**:

1. **Add account** → у вікні «Add an Instagram account» — **Continue**.
2. У вікні «Add people to your app» обрати роль **Instagram Tester**
   (окремий блок «Additional roles for this app», не плутати з просто «Tester»).
3. У полі нижче ввести `lys_montag` і обрати акаунт із підказки —
   звіряй за аватаром, схожих імен багато.
4. **Add**.

З'явиться попередження: *«The account will appear here once the invitation is
accepted»*. Далі — черга власника профілю: він приймає запрошення на
<https://www.instagram.com/accounts/manage_access/>, вкладка **Tester invitations**.

### 1.5. Згенерувати токен

Коли запрошення прийнято, акаунт з'явиться в таблиці секції 2. Навпроти нього:
**Generate token** → галочка **I Understand** → скопіювати → **Done**.

Токен показують один раз, він довгий (~200 символів) і дійсний 60 днів.
Генерувати повторно можна скільки завгодно.

> Акаунт обов'язково має бути **професійним**. Для особистого Meta дозволяє
> додати тестера, але токен не видає — теж мовчки. Перевірено 22.10.2026 на
> особистому акаунті: діалог `Generate token` просто не відкривається.

App Review не потрібен: для власного акаунта вистачає Standard Access.

### 1.6. Перевірити токен

```sh
curl -s "https://graph.instagram.com/me/media?fields=id,caption,media_type,permalink&limit=3&access_token=ТОКЕН" | head -40
```

Має повернутися JSON зі списком публікацій.

### Про строк дії токена

Токен живе **60 днів**. Скрипт продовжує його сам при кожному запуску, коли
лишається менше 20 днів, і зберігає новий у `/srv/lys-montage/state/token.json`
(звідти ж і читає — значення в `.env` потрібне лише для першого разу).

Отже, поки синк працює щодня, токен не протермінується ніколи. Але якщо сервер
пролежить вимкненим понад 60 днів, токен доведеться видавати заново з кроку 1.5.

## 2. Сервер Hetzner

### 2.1. Створити сервер

У Hetzner Cloud: **Add Server** → локація Nuremberg або Falkenstein →
образ **Ubuntu 24.04** → тип **CX22** (вистачає з запасом) → додати свій SSH-ключ.

### 2.2. Налаштувати

З локальної машини, з каталогу проєкту:

```sh
ssh root@IP_СЕРВЕРА 'bash -s' < deploy/bootstrap.sh
```

Скрипт поставить nginx, git, Python з Pillow і certbot, створить системного
користувача `lysmontage`, склонує репозиторій у `/srv/lys-montage/repo`,
увімкне щодобовий таймер і фаєрвол. Повторний запуск безпечний.

### 2.3. Вписати токен і зробити перший синк

```sh
ssh root@IP_СЕРВЕРА
nano /srv/lys-montage/ig-sync.env        # замінити ВСТАВ_ТОКЕН_СЮДИ
systemctl start lys-ig-sync.service
journalctl -u lys-ig-sync.service -n 40 --no-pager
```

В логу має бути рядок на кшталт `Готово: 9 постів → /srv/lys-montage/data/instagram.json`.

Перевірити результат: `curl -s http://IP_СЕРВЕРА/assets/data/instagram.json | head -20`

### 2.4. Домен і HTTPS

Спершу в DNS домену зробити `A`-записи на IP сервера (для `@` і для `www`).
Коли записи розійдуться (перевірка: `dig +short lysmontage.com`):

```sh
certbot --nginx --redirect -d lysmontage.com -d www.lysmontage.com
```

Certbot допише сертифікат і редирект HTTP → HTTPS у `/etc/nginx/sites-available/lys-montage`
і поставить автопродовження. `deploy.sh` цей файл не перезаписує — оновлює лише
правила сайту в `/etc/nginx/snippets/lys-montage-site.conf`. Адреси з `www` переадресовуються
на `lysmontage.com`.

Якщо домен інший, ніж `lysmontage.com`, замінити його в усіх файлах до першого деплою:
`grep -rl lysmontage.com index.html robots.txt sitemap.xml deploy/`.

---

## 3. Щоденна робота

### Оновити код сайту після змін у git

```sh
ssh root@IP_СЕРВЕРА 'bash -s' < deploy/deploy.sh
```

Галерею Instagram це не чіпає.

### Підтягнути пости негайно, не чекаючи ночі

```sh
systemctl start lys-ig-sync.service
```

### Подивитися, що з синком

```sh
systemctl list-timers lys-ig-sync.timer          # коли наступний запуск
journalctl -u lys-ig-sync.service -n 50 --no-pager   # лог останнього
systemctl is-failed lys-ig-sync.service          # failed → щось зламалось
```

### Прибрати пост із сайту або дати йому свій підпис

Instagram-підписи не завжди годяться для сайту: у них хештеги, емодзі та
анонси. Файл `tools/ig-overrides.json` дозволяє втрутитися точково.

1. Взяти `id` потрібного поста з `/srv/lys-montage/data/instagram.json`.
2. Додати запис:

```json
{
  "posts": {
    "17912345678901234": { "hide": true },
    "17998765432109876": {
      "title": "Долобів, Львівська обл.",
      "text": "Мережева СЕС під зелений тариф, 42 кВт панелей"
    }
  }
}
```

3. Закомітити, задеплоїти (`deploy.sh`) і запустити синк.

### Скільки постів показувати

У `/srv/lys-montage/ig-sync.env`:

- `IG_MAX_POSTS` — скільки карток на сайті (типово 9);
- `IG_LIMIT` — скільки публікацій запросити в API (типово 12; беремо з запасом,
  бо частина відсіюється: реклама, сторіс, пости без придатного зображення).

---

## 4. Що робить скрипт з постами

| Тип публікації | Що потрапляє на сайт |
|---|---|
| Фото | саме фото |
| Карусель | перше фото з каруселі |
| Відео / Reels | кадр-обкладинка, картка з позначкою «▶ Відео» |
| Сторіс, реклама | пропускається |
| Відео без обкладинки | пропускається |

Підписи скрипт чистить: прибирає хештеги й декоративні маркери, перший рядок
стає заголовком картки, решта — текстом (до ~190 символів). Кожна картка —
посилання на оригінальну публікацію в Instagram.

Фото стискаються до ширини 1200 px (JPEG, якість 82). За це відповідає Pillow —
`bootstrap.sh` ставить його пакетом `python3-pil`. Без Pillow синк теж працює,
просто зберігає оригінали.

---

## 5. Якщо щось пішло не так

| Симптом | Причина й що робити |
|---|---|
| `ПОМИЛКА: Токен протермінований і не продовжується` | Сервер довго не працював. Видати новий токен за кроком 1.5, вписати в `ig-sync.env`, видалити `/srv/lys-montage/state/token.json`, запустити синк. |
| `HTTP 400 … Invalid OAuth access token` | Токен скопійовано не повністю або не для того акаунта. Повторити крок 1.5. |
| На сайті стара галерея з 6 фото | Браузер не дістав `instagram.json`. Перевірити `curl -I https://ДОМЕН/assets/data/instagram.json` і права на `/srv/lys-montage/data`. |
| Нові пости не з'являються | `systemctl list-timers lys-ig-sync.timer` — чи активний таймер; `journalctl -u lys-ig-sync.service` — чи не падає. |
| Картинки 404 | Перевірити, що в nginx `location /assets/instagram/` вказує на `/srv/lys-montage/data/instagram/` і каталог має права 755. |
| `Інший запуск ще працює` | Нормально: попередній синк не завершився. Якщо повторюється — `journalctl` покаже, де завис. |

## 6. Локальний перегляд

Без доступу до API сторінка показує статичну галерею з `index.html`.
Щоб подивитися, як виглядає Instagram-версія, можна покласти власний
`assets/data/instagram.json` і фото в `assets/instagram/` — обидва шляхи
в `.gitignore`, у репозиторій вони не потраплять.

З токеном локальний синк запускається так:

```sh
IG_ACCESS_TOKEN=ТОКЕН python3 tools/ig_sync.py
python3 -m http.server 8000
```
