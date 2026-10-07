# Railway'ga joylash

Loyiha Railway'da bitta **project** ichida 3 ta xizmat sifatida ishlaydi:

| Xizmat | Manba | Root directory | Ommaviy domen |
|---|---|---|---|
| `Postgres` | Railway plugin | — | yo'q |
| `backend` | `backend/Dockerfile` | `/backend` | ixtiyoriy (Swagger uchun) |
| `frontend` | `frontend/Dockerfile` | `/frontend` | **ha** |

Frontend nginx `/api/*` so'rovlarini Railway ichki tarmog'i orqali backend'ga
uzatadi (`http://backend.railway.internal:<PORT>`), shuning uchun brauzer faqat
frontend domeni bilan ishlaydi va CORS sozlash shart emas.

## 1. Dashboard orqali (GitHub'dan avtomatik deploy)

1. <https://railway.com/new> → **Deploy from GitHub repo** →
   `KomiljonTurayev/Bank-s-news-and-new-product-with-ai`.
2. Project ichida **+ New → Database → PostgreSQL**.
3. GitHub repo'dan xizmatni `backend` deb nomlang, **Settings → Root Directory**
   = `/backend`. Variables:

   | O'zgaruvchi | Qiymat |
   |---|---|
   | `PROFILE` | `prod` |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `HOST` | `::` (Railway ichki tarmog'i IPv6) |
   | `PORT` | `8000` |
   | `FORWARDED_ALLOW_IPS` | `*` |
   | `ANTHROPIC_API_KEY` | `sk-ant-...` (AI tavsiyasi uchun) |
   | `SCRAPE_TIMES` | `09:00,14:00` (ixtiyoriy) |
   | `SENTRY_DSN` | ixtiyoriy |

4. Yana bir xizmat — `frontend`, **Root Directory** = `/frontend`. Variables:

   | O'zgaruvchi | Qiymat |
   |---|---|
   | `API_UPSTREAM` | `http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000` |

5. `frontend` → **Settings → Networking → Generate Domain**. Ilova shu manzilda.

`main` branch'ga har bir push ikkala xizmatni avtomatik qayta deploy qiladi.

## 2. CLI orqali

```bash
npm i -g @railway/cli
railway login

railway init --name bank-news                 # yangi project
railway add --database postgres
railway add --service backend
railway add --service frontend

# backend o'zgaruvchilari
railway variables --service backend \
  --set "PROFILE=prod" --set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' \
  --set "HOST=::" --set "PORT=8000" --set "FORWARDED_ALLOW_IPS=*" \
  --set "ANTHROPIC_API_KEY=sk-ant-..."

# frontend o'zgaruvchisi
railway variables --service frontend \
  --set 'API_UPSTREAM=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000'

# kodni yuklash (lokal papkadan)
railway up backend  --path-as-root --service backend  --detach
railway up frontend --path-as-root --service frontend --detach

railway domain --service frontend             # ommaviy URL
```

## Tekshirish

```bash
curl https://<frontend-domen>/api/health      # {"status": "ok", ...}
railway logs --service backend
railway logs --service frontend
```

- Backend ishga tushishda Alembic migratsiyalarini o'zi bajaradi
  (`alembic upgrade head`), alohida qadam kerak emas.
- Birinchi skreyping keyingi jadval soatida (`SCRAPE_TIMES`) bo'ladi; ungacha
  ro'yxatlar bo'sh bo'lishi normal.
- Frontend `502 {"error":"api_upstream_unreachable"}` qaytarsa — `API_UPSTREAM`
  manzili yoki backend porti noto'g'ri, yoki backend `HOST=::` bilan ishga
  tushmagan. Batafsil tashxis: [`ops/502-staging.md`](ops/502-staging.md).

## Cheklovlar

- Docker obrazida Chromium o'rnatilmagan: JS bilan render qilinadigan
  4 ta manba (Asakabank, Hamkorbank, Hayot bank, Orient Finans — Playwright
  connectorlari) prod'da xato bilan o'tkazib yuboriladi (logda ko'rinadi),
  qolgan manbalar oddiy HTTP orqali ishlaydi.
