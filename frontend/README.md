# Bank's News — Frontend

React 18 + Vite + TypeScript (Feature-Sliced Design). Shu repo'dagi
`backend/` REST API ustida ishlaydi.

## Bitta origin printsipi

Brauzer faqat bitta manzilda (`http://localhost:5500`) qoladi: `/api/...`
so'rovlari Vite dev proksi orqali backend'ga (`127.0.0.1:8000`) uzatiladi
(`vite.config.ts`). Prod'da nginx xuddi shu `location /api/`ni bajaradi
(`API_UPSTREAM`), shu bois CORS kerak emas.

## Sozlash va ishga tushirish

```bash
cp .env.example .env   # VITE_API_BASE_URL bo'sh qoladi — so'rovlar nisbiy /api/...
npm install
npm run dev            # http://localhost:5500
```

Backend (`../backend`, `python main.py`) oldindan ishga tushirilgan bo'lishi kerak.

Production build:

```bash
npm run build      # dist/ papkasiga
npm run preview    # buildni lokal ko'rish
```

Docker (nginx): `docker build -t bank-news-front .` va
`docker run -p 8080:80 -e API_UPSTREAM=http://backend:8000 bank-news-front`.
Railway'ga joylash — repo ildizidagi `DEPLOY.md`.

## Loyiha tuzilishi (Feature-Sliced Design)

```
src/
  app/            root, provider'lar (Mantine, react-query, i18n, tema),
                  routing/app-router.tsx, layouts/
  pages/          home, mpl, products, product-new, product-edit,
                  product-result, not-found
  widgets/        header, footer, hero, offers-section, mpl-screen,
                  global-error-notification
  features/       product-calculator (mahsulot pasporti, tahlil va
                  ai-advisor — AI mahsulot strategi chat paneli)
  entities/       offer, currency, meta
  shared/         api/ (so'rov qatlami), lib/ (i18n, format, mpl-chart), ui/,
                  assets/, model/
```

Uslublar bitta faylda: `src/app/index.css`. Barcha matn uz/ru
`src/shared/lib/i18n/dictionary.ts` orqali o'tadi.

## Tekshiruvlar

```bash
npm test               # vitest
npm run lint           # eslint
npm run lint:security  # xavfsizlik qoidalari
```
