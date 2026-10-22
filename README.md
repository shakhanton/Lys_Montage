# Lys Montag — сайт

Односторінковий статичний сайт для сантехніка/монтажника Андрія (бренд **Lys Montag**, Львів та область). Без збірки, без залежностей — чистий HTML/CSS.

Секція «Виконані роботи» оновлюється автоматично: раз на добу сервер тягне останні публікації з Instagram [@lys_montag](https://www.instagram.com/lys_montag/). Налаштування — у [`docs/instagram-sync.md`](docs/instagram-sync.md).

## Структура

```text
index.html               — уся розмітка сторінки
assets/css/styles.css    — стилі, кольорова палітра, адаптивність
assets/js/main.js        — карусель відгуків (кнопки + клавіатура)
assets/js/instagram.js   — рендер галереї з Instagram-фіду
assets/images/           — реальні фото (джерела — docs/sources.md)
assets/images/logos/     — логотипи брендів, Public domain (реєстр — docs/sources.md)
tools/ig_sync.py         — щодобовий синк постів з Instagram API
tools/ig-overrides.json  — ручні правки підписів і приховування постів
deploy/                  — nginx, systemd timer, bootstrap і deploy для Hetzner
docs/instagram-sync.md   — налаштування Instagram API та сервера
docs/instagram-token-for-client.md — інструкція для власника профілю: отримати токен
docs/sources.md          — реєстр джерел, фактів і походження фото
docs/content-map.md      — палітра, структура секцій, тексти з прив'язкою до джерел
docs/delivery-report.md  — результати перевірок і відомі обмеження
```

Згенероване синком (`assets/data/instagram.json`, `assets/instagram/`) у git не потрапляє — воно живе на сервері.

## Локальний запуск

Потрібен Python 3 (перевірено: `python3 --version`).

```sh
python3 -m http.server 8000
```

Відкрити у браузері: http://localhost:8000

Зупинити сервер: `Ctrl+C` у терміналі.

Без Instagram-фіду сторінка показує статичну галерею з `index.html` — це штатний запасний варіант.

## Зміст сторінки

Перший екран → Послуги → Виконані роботи → Матеріали та системи → Про майстра → Відгук → Контакти.

## Розгортання

Сайт працює на сервері Hetzner під nginx. Початкове налаштування і щодобовий синк Instagram описані в [`docs/instagram-sync.md`](docs/instagram-sync.md).

```sh
ssh root@IP 'bash -s' < deploy/bootstrap.sh   # перший раз
ssh root@IP 'bash -s' < deploy/deploy.sh      # оновити код
```

## Джерела та достовірність

Усі бізнес-факти, матеріали й фотографії мають джерело в `docs/sources.md`. Ціни, стаж, сертифікати й партнерства, які не вдалося підтвердити, на сайті не публікуються.
