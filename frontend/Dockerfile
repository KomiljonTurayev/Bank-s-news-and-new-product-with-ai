# Bank's News frontend — haqiqiy build + statik nginx.
# Build:  docker build -t bank-news-front .
# Run:    docker run -p 8080:80 -e API_UPSTREAM=http://backend:8000 bank-news-front

FROM node:22-alpine AS build
WORKDIR /build

# Qatlam keshi: kod o'zgarganda ham deps qatlami qayta o'rnatilmaydi.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# Bo'sh (default) = API so'rovlari nisbiy /api orqali, ya'ni shu nginx
# proksisidan o'tadi — CORS umuman kerak bo'lmaydi.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build
# CSP uchun inline skript xeshi — tayyor dist/index.html'dan hisoblanadi.
RUN node scripts/csp-hash.mjs dist/index.html security-headers.conf

FROM nginx:1.27-alpine

# OS qatlami har build'da yangilanadi (backend'dagi `apt-get upgrade`ning
# akasi): runner'dagi `nginx:1.27-alpine` eskiicha qoladi (qatlam kachesi +
# if-not-present), shuning uchun tuzatilgan versiyasi chiqqan paketlar
# (busybox, libssl3, libcrypto3) imajda eski holicha qoladi va Trivy image
# skani ularni HIGH/CRITICAL qilib ko'rsatadi. CI build'da
# `--build-arg OS_REFRESH=$CI_PIPELINE_ID` beradi — qiymat o'zgarganda bu
# va keyingi qatlamlar kachedan chiqadi.
# `|| echo WARN`: apk zerikarlari korxona proksi ortida javob bermasa build
# yiqilmasligi kerak — xavfsizlik qadami deploy'ni to'xtatmaydi, belgisi
# build jurnalida ko'rinadi.
ARG OS_REFRESH=0
RUN apk update \
    && apk upgrade --no-cache \
    || echo "WARN: apk upgrade bajarilmadi - imaj eski OS qatlami bilan qurildi"

# API_UPSTREAM — /api proksi manzili (standart: docker-compose'dagi backend;
# Railway'da Variables orqali beriladi, DEPLOY.md).
ENV API_UPSTREAM=http://backend:8000

# nginx.conf shablon sifatida qo'yiladi — entrypoint.sh uni ishga
# tushishda envsubst bilan renderlab /etc/nginx/conf.d/default.conf'ga
# yozadi (faqat ${API_UPSTREAM} va ${RESOLVER};
# nginx'ning o'z $host/$uri kabi o'zgaruvchilariga tegilmaydi).
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /build/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /build/dist/ /usr/share/nginx/html/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
