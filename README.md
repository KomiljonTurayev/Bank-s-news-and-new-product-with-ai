# Bank's News — bank mahsulotlari agregatori va AI mahsulot strategi

O'zbekiston banklarining **depozit, kredit, karta, valyuta kursi va obligatsiya**
shartlarini ochiq manbalardan (CBU, depozit.uz, UZSE va 40 dan ortiq bank sayti) muntazam
yig'ib, bitta joyda solishtirish imkonini beruvchi veb-ilova. Ustiga **Claude AI**
asosidagi mahsulot strategi qurilgan: bozordagi haqiqiy takliflar asosida
raqobatbardosh yangi bank mahsuloti g'oyalarini (stavka, muddat, summa,
asoslash, xavflar) taklif qiladi.

```
┌──────────────┐   /api/*    ┌──────────────────┐   SQL   ┌────────────┐
│  Frontend    │ ──────────► │  Backend         │ ──────► │ PostgreSQL │
│  React+Vite  │  (nginx     │  FastAPI         │         └────────────┘
│  nginx       │   proksi)   │  APScheduler     │ ──────► Claude API
└──────────────┘             │  44 ta connector │ ──────► CBU, depozit.uz,
                             └──────────────────┘         bank saytlari
```

Brauzer faqat frontend origin'iga murojaat qiladi — `/api/*` nginx (prod) yoki
Vite (dev) proksisi orqali backend'ga o'tadi, shu sababli CORS kerak emas.

## Imkoniyatlar

- **Bozor monitoringi** — 44 ta connector (40+ bank); omonatlar, kreditlar
  (iste'mol, ipoteka, avto, ta'lim, overdraft), kartalar, obligatsiyalar,
  valyuta kurslari; jismoniy/yuridik shaxs segmentlari.
- **Kunlik jadval** — skreyping kuniga 2 marta (`09:00`, `14:00`, Asia/Tashkent),
  faol oyna (`07:00–21:00`) va har bir hostga so'rovlar orasida tanaffus bilan.
- **Mahsulot pasporti** — o'z mahsulot g'oyangizni kiritib, bozordagi
  analoglar bilan solishtirma tahlil olish.
- **AI mahsulot strategi** — `POST /api/products/recommend` Claude orqali
  yangi mahsulot tavsiyalari.
- **Valyuta dinamikasi** — kurs statistikasi va tarixi.
- **Ikki til** — o'zbek va rus interfeysi, yorug'/qorong'i tema.
- **Ishonchlilik** — rate limiter, circuit-breaker/retry (`resilience.py`),
  `/api/health` monitoringi, Sentry (ixtiyoriy), Alembic migratsiyalari.

## Repo tuzilishi

| Papka | Tarkibi |
|---|---|
| [`backend/`](backend/README.md) | FastAPI REST API, skreyperlar, scheduler, AI tavsiya |
| [`frontend/`](frontend/README.md) | React 19 + Vite + TypeScript + Mantine (Feature-Sliced Design) |
| [`docs/`](docs/) | Tahliliy hujjatlar (raqobatchi kredit tahlili, ochiq savollar) |
| [`ops/`](ops/) | Ekspluatatsiya qaydlari (502 tashxisi) |
| [`DEPLOY.md`](DEPLOY.md) | Railway'ga joylash bo'yicha qo'llanma |

## Tez boshlash (lokal)

Talablar: **Python 3.11**, **Node.js 22**, Docker (Postgres uchun; ixtiyoriy —
SQLite bilan ham ishlaydi).

```bash
# 1) Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env
docker compose up -d postgres     # yoki .env'da DATABASE_URL=sqlite:///bank_news.db
python main.py                    # http://localhost:8000  (Swagger: /docs)

# 2) Frontend (yangi terminalda)
cd frontend
cp .env.example .env
npm install
npm run dev                       # http://localhost:5500
```

AI tavsiyasi uchun `backend/.env`ga `ANTHROPIC_API_KEY` (yoki `CLAUDE_API_KEY`)
yozing. Kalitsiz ham ilova to'liq ishlaydi, faqat tavsiya endpoint'i `503`
qaytaradi.

## Testlar va sifat

```bash
cd backend  && pytest
cd frontend && npm test && npm run lint && npm run lint:security
```

## Deploy

Railway'da 3 ta xizmat: **Postgres**, **backend**, **frontend**. Batafsil —
[DEPLOY.md](DEPLOY.md).

## Xavfsizlik

- `.env` fayllar git'ga va Docker obraziga tushmaydi (`.gitignore`, `.dockerignore`).
- Konteynerlar root bo'lmagan foydalanuvchi ostida ishlaydi (backend).
- CORS faqat `FRONTEND_ORIGINS` ro'yxati bo'yicha, wildcard yo'q.
