# Bank's News — Backend

O'zbekiston banklarining depozit, kredit, karta, valyuta kursi va
obligatsiya shartlarini bitta joyda solishtirish uchun agregator
backend'i (REST API). Ma'lumotlarni ochiq manbalardan (CBU,
depozit.uz, banklarning o'z saytlari) muntazam yig'ib bazaga saqlaydi.

Frontend shu repo'ning `frontend/` papkasida. Backend faqat REST API beradi;
frontend unga nginx (prod) yoki vite (dev) proksi orqali `/api` bilan ulanadi.

Standart bazaviy sozlama — PostgreSQL (`docker-compose.yml` orqali
mahalliy konteynerda); prototip/bitta-foydalanuvchi rejimida SQLite
ham qo'llab-quvvatlanadi (`DATABASE_URL`ni almashtirish yetarli,
SQLAlchemy orqali kod o'zgarmaydi).

## Xususiyatlar

- **Kunlik jadval bo'yicha yig'ish** — `APScheduler` soatlari
  `SCRAPE_TIMES`da (standart `09:00,14:00`, Asia/Tashkent) kuniga aynan
  2 marta ishga tushadi; jadval bo'sh qoldirilsa `FETCH_INTERVAL_MINUTES`
  oralig'li interval rejimiga qaytadi.
- **Ko'p mahsulot turi** — omonatlar, kreditlar (iste'mol, ipoteka,
  avto, ta'lim, overdraft), kredit/debet kartalar, obligatsiyalar,
  valyuta kursi.
- **Jismoniy/yuridik shaxs segmentlari**.
- **Oddiy REST API** (`/api/meta`, `/api/rates/latest`, ...) — frontend
  (yoki boshqa tashqi tizim) shu API ustida ishlaydi.
- **CORS** — faqat `FRONTEND_ORIGINS`da ro'yxatlangan origin'larga
  ruxsat beriladi (wildcard yo'q).
- **AI mahsulot tavsiyasi** — `POST /api/products/recommend` bazadagi bozor
  takliflarini Claude'ga berib, raqobatbardosh yangi mahsulot g'oyalarini
  (stavka, muddat, summa, asoslash, xavflar) qaytaradi. Kalit:
  `ANTHROPIC_API_KEY` (yoki `CLAUDE_API_KEY`).
- **Kengaytiriladigan connector arxitekturasi** — yangi bank yoki
  manba qo'shish uchun bitta klass yozish yetarli.

## Texnologiyalar

Python, FastAPI, SQLAlchemy, PostgreSQL (yoki SQLite), APScheduler,
BeautifulSoup, Playwright (JS orqali render qilinadigan banklar
uchun — birinchi marta ishlatishdan oldin
`playwright install chromium` bajarilishi kerak).

## O'rnatish

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# yoki: source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
copy .env.example .env          # Windows; Linux/macOS: cp .env.example .env

docker compose up -d postgres   # mahalliy PostgreSQL konteynerini ko'taradi
```

`.env` faylida quyidagilarni sozlash mumkin:

| O'zgaruvchi | Ma'nosi | Standart qiymat |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy ulanish satri | `postgresql+psycopg://bank_news:bank_news@localhost:5433/bank_news` |
| `FETCH_INTERVAL_MINUTES` | Interval rejimi qadami — faqat `SCRAPE_TIMES` bo'sh bo'lganda tikish oralig'i | `60` |
| `SCRAPE_TIMES` | Kunlik skreyping soatlari, vergul bilan `HH:MM` (Asia/Tashkent); bo'sh satr = interval rejimi | `09:00,14:00` |
| `FRONTEND_ORIGINS` | CORS uchun ruxsat etilgan frontend origin'lari (vergul bilan) | `http://localhost:5500,http://127.0.0.1:5500` |

Diqqat: `docker-compose.yml` Postgres'ni host'da **5433**-portga
chiqaradi (5432 emas) — ba'zi mashinalarda 5432 allaqachon boshqa
mahalliy PostgreSQL xizmati tomonidan band bo'lishi mumkin.

Eski SQLite fayldan (`bank_news.db`) Postgres'ga bir martalik
ma'lumot ko'chirish uchun:

```bash
python scripts/migrate_sqlite_to_postgres.py "postgresql+psycopg://bank_news:bank_news@localhost:5433/bank_news"
```

## Ishga tushirish

```bash
python main.py
```

Bu buyruq bazani yaratadi, fonda schedulerni yoqadi va
`http://localhost:8000` manzilida FastAPI serverini (faqat API, `/docs`da
Swagger) ko'taradi. Startafdagi skreyping jadvalga bo'ysunadi: o'tkazib
yuborilgan tikish soati bo'lsa (crash-restart shu holatga kiradi) fonda
qoplanadi, aks holda keyingi soat kutiladi — jadval yoqiqda boot "reja
tashqarisidagi tashqi chiqish" bo'lmaydi.

Windows'da fon xizmati sifatida ishga tushirish uchun
`run_service.bat` (konsol bilan) yoki `start_hidden.vbs` (konsolsiz,
orqa fonda) fayllaridan foydalaning — loglar `logs/service.log`ga
yoziladi.

## Monitoring

`GET /api/health` — scheduler haqiqatan ishlab turganini tekshirish uchun
(bazadagi eng so'nggi `fetched_at`ni qaytaradi):

```bash
curl http://localhost:8000/api/health
```

```json
{
  "status": "ok",
  "last_fetch_at": "2026-09-15T09:00:12.345Z",
  "fetch_interval_minutes": 60,
  "stale_after_minutes": 1185,
  "scrape_times": ["09:00", "14:00"],
  "next_fire_at": "2026-09-15T14:00:00+05:00"
}
```

`status` — jadval rejimida (`scrape_times` to'la) `"stale"` degani:
o'tgan tikish soati (masalan 09:00) grace (45 daqiqa) bilan ham tugadi-yu,
o'sha soatda yig'ish tugamadi. Bu rejimda tuni (14:00→ertaga 09:00) NORMAL
jimlik — "soatiga 1 marta" geometriyasi bilan 19 soatlik uzilish deb
o'lgazmaslik uchun. Interval rejimida (`scrape_times: []`) esa oxirgi
yig'ish `stale_after_minutes` (standart: 2 x `FETCH_INTERVAL_MINUTES`)dan
eskirgan bo'lsa `"stale"`. `stale_after_minutes` skalyari monitoringga
"normal holatda shu qadar jimlik kutilsin" deydi: jadvalda — eng uzon reja
oralig'i + 45 daqiqa zaxira. Bazaga bog'liq bo'lmagan oddiy tiriklik
tekshiruvi: `GET /actuator/health` → `{"status": "alive"}`.

## Testlar

```bash
pytest
```

## Loyiha tuzilishi

```
app/
  api.py                 FastAPI endpointlari (CORS shu yerda yoqiladi)
  product_recommendation.py  AI (Claude) orqali yangi mahsulot tavsiyasi
  banks.py                Banklar ro'yxati, mahsulot turlari, segmentlar,
                           bank nomini kodga moslashtirish (resolve_bank_code)
  config.py                Nozik adapter — qiymatlarni `config/` paketidan oladi
  db.py, models.py        SQLAlchemy sozlamalari va BankRate modeli
  schedule.py              Kunlik jadval matematikasi (soatlar, keyingi/o'tgan tikish) — sof modul
  scheduler.py             Connectorlarni fon rejimida jadval/interval bo'yicha ishga tushirish
  connectors/
    base.py               Barcha connectorlar uchun umumiy asos (BaseConnector)
    cbu.py                 O'zbekiston Markaziy banki — rasmiy JSON API
    depozit_uz.py          depozit.uz'dagi depozit/kredit kartochka blokllari
    depozit_tables.py      depozit.uz'dagi jadval ko'rinishidagi sahifalar
                           (kredit/debet kartalar, obligatsiyalar)
    example_bank_scraper.py  Rasmiy API bermaydigan banklar uchun shablon
    registry.py             Barcha connectorlar shu yerda ro'yxatga olinadi
tests/                     pytest testlari
config/                    Sozlamalar paketi:
  base.py                   Maydon shakli (qiymatlar env/.env'dan keladi)
  dev.py / prod.py          Profile klasslari
  __init__.py               PROFILE bo'yicha tanlash
```

## Yangi connector qo'shish

1. `app/connectors/example_bank_scraper.py`ni nusxalab, yangi fayl
   yarating (yoki mos struktura bo'lsa `depozit_uz.py` /
   `depozit_tables.py`dagi mavjud parserlardan foydalaning).
2. `BaseConnector`dan meros oling, `fetch_raw()` va `parse()`
   metodlarini amalga oshiring — `parse()` har bir yozuv uchun oddiy
   `dict` qaytarishi kerak (kalitlar frontendda ustun/maydon nomi
   sifatida ko'rinadi).
3. Kerak bo'lsa `_bank_code` va `_segment` maxsus kalitlari orqali
   standart `bank_code`/`segment`ni har bir yozuv uchun bekor qiling.
4. Yangi connectorni `app/connectors/registry.py`dagi `CONNECTORS`
   ro'yxatiga qo'shing.

## Deploy

Railway'ga joylash — repo ildizidagi `DEPLOY.md`. Barcha sozlamalar muhit
o'zgaruvchilaridan o'qiladi, to'liq ro'yxat `.env.example`da.
