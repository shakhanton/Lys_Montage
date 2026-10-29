#!/usr/bin/env bash
# Оновлення коду сайту на сервері з git. Instagram-фід не торкаємо —
# він живе в /srv/lys-montage/data і переживає будь-який деплой.
#
#   ssh root@IP 'bash -s' < deploy/deploy.sh
set -euo pipefail

BASE=/srv/lys-montage
BRANCH="${BRANCH:-main}"

[[ $EUID -eq 0 ]] || { echo "Потрібні права root" >&2; exit 1; }

git -C "$BASE/repo" fetch --quiet origin "$BRANCH"
echo "Було:  $(git -C "$BASE/repo" rev-parse --short HEAD)"
git -C "$BASE/repo" reset --hard --quiet "origin/$BRANCH"
echo "Стало: $(git -C "$BASE/repo" rev-parse --short HEAD)"

# Конфіги в репозиторії могли змінитися — переставляємо їх.
# Лише правила сайту; server-блок із сертифікатом certbot не перезаписуємо.
install -m 644 "$BASE/repo/deploy/nginx-lys-montage-site.conf" /etc/nginx/snippets/lys-montage-site.conf
# Server-блок ставимо лише раз: після certbot у ньому живе сертифікат.
# Старий конфіг «все в одному» (до винесення правил у snippet) замінюємо,
# поки certbot його ще не чіпав.
SITE_CONF=/etc/nginx/sites-available/lys-montage
if [[ ! -f $SITE_CONF ]] || ! grep -q 'snippets/lys-montage-site.conf' "$SITE_CONF"; then
  if [[ -f $SITE_CONF ]] && grep -q 'managed by Certbot' "$SITE_CONF"; then
    echo "УВАГА: $SITE_CONF уже з сертифікатом, але без include snippets/lys-montage-site.conf — перенести вручну" >&2
  else
    install -m 644 "$BASE/repo/deploy/nginx-lys-montage.conf" "$SITE_CONF"
  fi
fi
install -m 644 "$BASE/repo/deploy/lys-ig-sync.service" /etc/systemd/system/lys-ig-sync.service
install -m 644 "$BASE/repo/deploy/lys-ig-sync.timer" /etc/systemd/system/lys-ig-sync.timer
systemctl daemon-reload
nginx -t && systemctl reload nginx

echo "Деплой завершено"
