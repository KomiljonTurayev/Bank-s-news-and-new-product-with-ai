#!/bin/sh
set -e

# Standart — docker-compose'dagi backend; Railway'da API_UPSTREAM Variables
# orqali beriladi (http://<backend>.railway.internal:8000, DEPLOY.md).
API_UPSTREAM="${API_UPSTREAM:-http://backend:8000}"
export API_UPSTREAM

RESOLVER="$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf 2>/dev/null)"
RESOLVER="${RESOLVER:-127.0.0.11}"
# IPv6 nameserver (masalan Railway'ning ichki DNS'i) nginx'da qavs ichida yoziladi.
case "$RESOLVER" in *:*) RESOLVER="[$RESOLVER]" ;; esac
export RESOLVER

# Railway kabi PaaS tinglanadigan portni PORT orqali beradi.
PORT="${PORT:-80}"
export PORT

envsubst '${API_UPSTREAM} ${RESOLVER} ${PORT}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

# Renderdan keyin tekshirish: o'zgaruvchilardan biri kutilmagan bo'lsa
# xato shu yerda, qaysi qator ekanligi bilan chiqadi (set -e konteynerni
# to'xtatadi), aks holda xato foydalanuvchining har bir /api so'roviga
# tarqaladi.
nginx -t

exec nginx -g "daemon off;"
