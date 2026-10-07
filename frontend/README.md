# Bank's News — Frontend

Bank mahsulotlari agregatorining veb-interfeysi: bozordagi takliflarni
solishtirish, valyuta dinamikasi, mahsulot pasporti va AI mahsulot strategi.
Shu repo'dagi `backend/` REST API ustida ishlaydi.

**Stek:** React 19, TypeScript 5.8, Vite 7, Mantine 8, TanStack Query 5,
Redux Toolkit, React Router 7, Vitest + Testing Library.

## Sahifalar

| Yo'l | Sahifa |
|---|---|
| `/` | Bosh sahifa — bozor takliflari va filtrlar |
| `/mpl` | MPL — valyuta kursi tahlili (davr bo'yicha min/o'rtacha/max, CBU arxivi) |
| `/products` | Saqlangan mahsulot g'oyalari |
| `/products/new` | Yangi mahsulot pasporti (+ AI strategi paneli) |
| `/products/:id` | Mahsulot tahlili — bozor analoglari bilan solishtirish |
| `/products/:id/edit` | Mahsulotni tahrirlash |

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

Konteyner o'zgaruvchilari:

| O'zgaruvchi | Ma'nosi | Standart |
|---|---|---|
| `API_UPSTREAM` | `/api/*` proksilanadigan backend manzili | `http://backend:8000` |
| `PORT` | nginx tinglaydigan port (Railway beradi) | `80` |
| `VITE_API_BASE_URL` | *build-arg*; bo'sh = nisbiy `/api` (tavsiya) | bo'sh |

Railway'ga joylash — repo ildizidagi [`DEPLOY.md`](../DEPLOY.md).

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
