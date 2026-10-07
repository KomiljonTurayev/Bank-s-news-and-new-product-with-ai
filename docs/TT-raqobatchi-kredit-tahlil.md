# TEXNIK TOPSHIRIQ (TT)
## Raqobatchi tijorat banklari kredit mahsulotlarini monitoring qilish, tahlil qilish va taqqoslash tizimi

| | |
|---|---|
| **Hujjat raqami** | TT-2026-001 |
| **Asos hujjat** | BT-2026-001 v1.0 "Raqobatchi tijorat banklarining kredit mahsulotlarini sun'iy intellekt yordamida tahlil qilish tizimi"; xizmat yozishmasi № D-14984 (06.07.2026) |
| **Buyurtmachi** | Kichik biznes departamenti (J. Makhmudov) |
| **Ijrochi** | Axborot texnologiyalari departamenti (Z. Orifxo'jayev) |
| **Versiya** | v0.1 — dastlabki loyiha, kelishish uchun |
| **Holat** | 23-bo'limdagi ochiq qarorlar yopilgunicha imzolangan hisoblanmaydi |
| **Amala oshirish bazasi** | `Bank's News` platformasi (backend: FastAPI/SQLAlchemy/APScheduler; frontend: React 19/Mantine 8) |

### 0.1 Bu hujjat BT'dan nima bilan farq qiladi

BT "nima kerak"ligini belgilagan. TT uchta ishni qo'shimcha qiladi:

1. **BT'dagi 9 ta nuqson va ziddiyatni aniqlash va yopish** (3-bo'lim) — ular orasida bajarib bo'lmaydigan qabul mezonlari va o'zaro mos kelmaydigan talablar bor.
2. **"Qanday"ni kod haqiqatiga bog'lash** — tizim havodan emas, `Bank's News`da allaqachon ishlayotgan konnektor, scheduler, SSO, Vault, resilience qatlamlari ustiga quriladi (5-bo'lim).
3. **Nimani biz, nimani buyurtmachi berishini sanab chiqish** — tugallanmagan BT bandlariga javobgar biriktirish (21-bo'lim).

### 0.2 Atamalar

| Atama | Ma'nosi |
|---|---|
| **Kanonik parametr** | 12 ta solishtiriladigan kredit parametri; har biri aniq tur va birlikka ega (24-bo'lim) |
| **CreditOffer** | Bitta bankning bitta kredit mahsulotining kanonik ko'rinishi |
| **Snapshot** | Offer'ning ma'lum lahzadagi holati; tarix snapshot'lardan quriladi |
| **Ekstraksiya quvuri** | Manba sahifasi → kanonik parametr bo'lmagacha bo'lgan 3 bosqichli zanjir (8-bo'lim) |
| **Etalon to'plam (gold set)** | Qo'lda belgilangan, to'g'riligi tasdiqlangan reference to'plam; aniqlik shu ustida o'lchanadi |
| **Detection latency** | Manbada o'zgarish ochiq chiqqan lahzadan biz uni aniqlaguncha o'tgan vaqt |
| **Delivery latency** | Biz o'zgarishni aniqlagandan keyin xabarnoma yetguncha o'tgan vaqt |
| **Review queue** | Model ishonchsiz yoki qayta ishlash mumkin bo'lmagan holatlarning qo'lda tekshirish navbati |

---

## 1. MAQSAD VA MUVAFFAQIYAT MEZONLARI

BT'dagi AC-01…AC-07 ko'pincha "qanday o'lchanadi"ni o'z ichiga olmaydi. Quyidagi mezonlarning har biri **o'lchov usuli, o'lchovchi va ma'lumot manbai** bilan birga keladi va avtomatik tekshiriladigan holatda yoziladi.

| # | Muvaffaqiyat mezon | O'lchov usuli | O'lchovchi | Maqsad |
|---|---|---|---|---|
| M-1 | 34 ta bank manbai uzluksiz yig'iladi | `extraction_runs` jadvalidan 30 kunlik hisob: muvaffaqiyatli sikl ulushi | Avtomatik (dashboard) | ≥ 34 bank; sikl muvaffaqiyati ≥ 95% |
| M-2 | Parametr aniqligi | Etalon to'plam ustida rekkord; har parametr bo'yicha alohida | AI/MA muhandisi + KBD vakili | agregat ≥ 98%; hech bir parametr < 90% |
| M-3 | Detection latency | Manba versiyasi o'zgargan vaqt (sahifa versiyasi snapshot'i) ↔ `change_events.detected_at` | Avtomatik | P95 ≤ 45 daqiqa |
| M-4 | Delivery latency | `change_events.detected_at` ↔ `notification_deliveries.delivered_at` | Avtomatik | P95 ≤ 5 daqiqa |
| M-5 | Dashboard unumdorligi | so'rov profili → SQL `EXPLAIN` + server javob vaqti; CI performance smoke | Avtomatik | API P95 ≤ 800 ms; birinchi ekran TTI ≤ 3 s |
| M-6 | Qabul qilingan ish hajmi | KBD xodimlari so'rovnomasi (5+ xodim, 4 haftalik qarish) | KBD | "qo'lda taqqoslash vaqti ≥ 70% kamaydi" |

> **Eslatma (M-2).** BT'dagi "xatolik < 2%" va "≥ 98%" bir xil narsaning ikki xil yozilishi. TT ularni bitta mezonning ikki tomoni deb oladi va **etalon to'plam bo'lmasa bu mezon umuman o'lchansiz** degan shart qo'yadi: 18-bo'lim topshirig'i M-2'dan oldin yopilishi kerak.

---

## 2. DOIRA

### 2.1 Tizim tarkibiga kiradi

- **34 ta** raqobatchi tijorat bankining rasmiy saytlaridan kredit mahsulotlari ma'lumotlarini avtomatik yig'ish (HTML + JS-render + PDF).
- **12 ta kanonik parametr** (24-bo'lim) bo'yicha strukturalangan ma'lumot.
- Kredit turlari: **yuridik shaxslar / KHB** segmenti ustuvor, jismoniy shaxslar ikkinchi bosqichda (segmentlar soni — ochiq qaror OD-3).
- BRB o'z mahsulotlari bilan avtomatik taqqoslash (benchmark manbai — OD-2).
- O'zgarish monitoringi + alert (Email, SMS, tizim ichi).
- Taqqoslash dashboardi, filtrlar, trend, tarix (≥ 12 oy), Excel/PDF eksport.
- Admin interfeysi: manbalar, ekstraksiya natijalari, review queue, alert obunalari.
- ONE-ID SSO + RBAC (4 rol), O'zbek va Rus tillari.

### 2.2 Tizim tarkibiga KIRMAYDI

- Banklar bilan to'g'ridan-to'g'ri (shartnoma/API) integratsiya; faqat ochiq manbalar.
- Norasmiy, maxfiy yoki shaxsga oid ma'lumot yig'ish.
- Kredit qaror qabul qilish, skorling, limit hisoblash.
- Mijozlarga (`front-office`) chiqariladigan oferta/baho moduli.
- Mahsulot ishlab chiqish jarayonining o'zi (tizim faqat tavsiya beradi).

### 2.3 Doirani muzlatish

Doira **34 bank birdaniga** — bosqichma-bosqich tarqatish nazarda tutilmagan (buyurtmachi qarori). Shu sabab:

- Doira o'zgarishi (bank qo'shish, parametr qo'shish) faqat yozma o'zgarish so'rovi orqali, 7 vaqt jadvali ta'siri bilan;
- Ichki qurish tartibi (19-bo'lim) doira emas, texnik masala: kod ketma-ket yoziladi, lekin **topshirish bitta, to'liq kontur bilan** bo'ladi.

### 2.4 BT'ga izlilik matritsasi (har bir BT bandi qayerda)

Qoida: jadvalda bo'sh yoki "qisman" ustun qolsa — bu TT nuqsoni, yuklovchi nuqsoni emas. 1-bosqich chegarasi shu jadval to'lishi bilan belgilanadi.

| BT bandi | TT bo'limi | Holat |
|---|---|---|
| FR-01 avtomatik yig'ish | 8.1, 8.3 | kiritildi (M-1 = ≥95% o'qish) |
| FR-02 AI-parser | 8.2, 18.2 | kiritildi, LLM qatlami OD-7 ga bog'liq |
| FR-03 manba boshqaruvi | 7.2 (`sources`), 12 (`pages/sources-admin`) | kiritildi |
| FR-04 yangilash chastotasi | 10.1, 6 | kiritildi + favqulodda tugma |
| FR-05 parametr tahlili | 7.4, 24 (12 parametr) | kiritildi |
| FR-06 taqqoslash jadvali | 9.2, 9.3, 11 (`/api/compare/matrix`) | kiritildi |
| FR-07 ustun/zaif (SWOT) | 9.4 | **o'zgartirildi** — SWOT o'rniga raqamli gap-analysis (D-4) |
| FR-08 tendensiya tahlili | 9.5, 11 (`/api/monitor/trends`), 12 (`pages/trends`) | kiritildi — rezolyutsiya cheklovi 9.5 da ochiq yozilgan |
| FR-09 AI tavsiyalar | 9.6, 22 (5-band) | **qisman** — generativ qism OD-8 |
| FR-10 o'zgarish monitoringi | 10.1, 10.2 | kiritildi, SLA ikkiga ajratilgan (D-1) |
| FR-11 alert kanallar | 10.3 | kiritildi, kanal to'plami OD-9 |
| FR-12 alert sozlamalari | 10.4, 12 | kiritildi |
| FR-13 interaktiv dashboard | 12, 15.3 | kiritildi |
| FR-14 filtr va qidiruv | 12 (`features/compare-filters`) | kiritildi |
| FR-15 eksport | 17 | kiritildi (Excel serverda; PDF kutubxonasi reliz ichida) |
| FR-16 tarixiy ma'lumotlar | 7.3 | kiritildi, 12 oy AC-07 bandiga bog'liq |
| AC-01 ≥ 34 bank | 5, 19.2 | asbuilt zaxira bor: `app/banks.py` da **43** bank |
| AC-02 aniqlik ≥ 98% | 18.2 (etalon to'plam, M-2) | kiritildi |
| AC-03 ≤ 30 daqiqa alert | 10.1, 22 (2-band) | **o'zgartirildi** — detection ≤45 daq + delivery ≤5 daq, imzolashda ochiq |
| AC-04 ≤ 3 soniya | 15.3 (CI P95 bo'sag'asi) | kiritildi |
| AC-05 Excel + PDF | 17 | kiritildi |
| AC-06 BRB SSO | 13.2, 14 | kiritildi (ONE-ID ishlab turibdi) |
| AC-07 ≥ 12 oy tarix | 7.3, 22 (1-band) | **qisman** — mexanizm 1-bosqichda, oy to'lishi vaqt masalasi |
| NFR yuklanish 3 s | 15.3 | kiritildi |
| NFR AI tahlil ≤ 10 s | 15.3 (hisob sikl ichida, API keshdan o'qiydi) | **o'zgartirildi** — so'rovda LLM chaqirilmaydi |
| NFR uptime ≥ 99.5% | 15.1, 16 | **o'zgartirildi** — o'lchov shartnomasi quyida |
| NFR BRB SSO | 13.2 | kiritildi |
| NFR RBAC | 13.1 | kiritildi |
| NFR ≥ 34 manba | 15.2 | kiritildi |
| NFR UZ/RU | 12 | kiritildi |

**Uptime o'lchov shartnomasi (BT "≥ 99.5%, texnik xizmat soatlaridan tashqari" ni birinchi marta o'lchanadigan qiladi):** hisob derazi = oylik, manba = `/api/health` tashqi probe (har 1 daqiqada), istisno = rejalashtirilgan oynalar (har yakshanba 03:00–05:00 Asia/Tashkent) **va** tashqi bank manbalari holati — tashqi sayt o'lik bo'lsa, bu bizning uptime'miz emas, M-1 manba salomatligi ko'rsatkichiga yoziladi. Shu ajratish yozilmasa, 34 bankning har bir buzilishi bizning SLA'mizni yiqqoniga hisoblanadi.


---

## 3. BT NUQSONLARI VA TT YECHIMLARI

Bu bo'lim TT asosiy qiymatidir. Har bir nuqson imzolashdan oldin yopilishi kerak.

| # | BT'dagi muammo | Qayerda | Xavf darajasi | TT yechimi |
|---|---|---|---|---|
| **D-1** | **Ichki ziddiyat:** FR-04 "har 24 soatda" yangilanadi, FR-10 esa o'zgarishdan "30 daqiqa ichida" alert so'raydi. Manba kuniga bir marta o'qilsa, 30 daqiqalik SLA fizik jihatdan bajarilmaydi. | 5.1 / 5.3 | **Kritik** | SLA ikkiga ajratiladi: **detection** (M-3, P95 ≤ 45 daqiqa — shuning uchun saralash o'rniga sozlanadigan 15-30 daqiqalik tekshiruv sikli va qo'lda "hozir tekshirish" tugmasi) va **delivery** (M-4, ≤ 5 daqiqa). "Har 24 soat" to'liq qayta ishlash sikli sifatida saqlanadi; yuzaki o'zgarishni aniqlash sikli esa undan tez ishlaydi (10.1). |
| **D-2** | **AC-02 o'lchansiz:** "aniqlik ≥ 98%", "xatolik < 2%" — lekin nazorat to'plamini kim, qancha hajmda, qanday belgilash aytilmagan. Reference bo'lmasa mezon subyektiv bahoga aylanadi va qabul janjalga kiradi. | 5.1 / 9 | **Kritik** | Etalon to'plam TT majburiy yetkazib berish obyekti: 34 bank × ≥ 2 mahsulot × 12 parametr ≥ **800 belgilangan qiymat**, 2 mustaqil belgilovchi, Kappa ≥ 0.85; ochiq kodli baholash skripti. 18.2. |
| **D-3** | **Taqqoslash metodologiyasi yo'q.** Turli ta'minot, muddat va komissiyali mahsulotlarni qanday qilib bitta jadvalga va bitta "ustun/zaif" xulosasiga joylash — aniqlanmagan. Bu texnik emas, biznes qarori. | 5.2 FR-06, FR-07 | **Kritik** | TT **mexanizmni** belgilaydi (normalizatsiya + effektiv stavka + og'irlikli skoring, 9-bo'lim), **raqamlarni emas**: mezon og'irliklari va taqqoslash guruhlash qoidalari KBD tomonidan imzolangan `PRICING-COMPARISON-MATRIX` hujjatidan olinadi. Bu hujjat bo'lmasa FR-06/FR-07 topshirilmaydi (BRB-03, OD-1). |
| **D-4** | **"AI" atamasi noaniq.** FR-02 "AI-parser", FR-07 "SWOT", FR-09 "AI tavsiya" — model qayerda ishlaydi, qanday ma'lumot unga beriladi, hal qiluvchi kim? | 5.1 / 5.2 / 7.1 | **Kritik** | Ekstraksiya 3 bosqichga bo'linadi (8-bo'lim): L1 deterministik konnektor → L2 LLM (ichki BRB gateway, structured output, majburiy iqtibos-span) → L3 inson tasdiqlash. Hech bir parametr tasdiqsiz dashboardga chiqmaydi. SWOT o'rniga **gap-analysis** (9.4): AI taxmin qilmaydi, farqning sababini ko'rsatadi. |
| **D-5** | **Yuridik/etika tomoni yo'q.** "Faqat ochiq manbalar" deyilgan, lekin 34 bank saytini avtomatik o'qishning robots.txt, foydalanish shartlari, WAF/anti-bot holati biror bandda qamrovga olinmagan. | 3.2 / 7.1 | **Kritik** | 13.4 banda: mexanizmlar allaqachon bor (`app/outbound.py` — faollik oynasi, host oralig'i, jitter) va kuchaytiriladi. Huquqiy xulosa (har bir manba uchun ruxsat) **Yurist boshqarmasining topshig'i**, OD-4; bu bitmasa tashqi risk bizda qoladi. |
| **D-6** | **Stek "yoki-yoki" holda:** FastAPI *yoki* Node.js, React *yoki* Vue, Airflow *yoki* Celery. Shartnomaviy kelishmovchilik urug'i. | 7.1 | O'rta | TT qaror:FastAPI + React (mavjud baza). **Airflow qabul qilinmaydi** — 34 manba / kunlik ritm uchun ortiqcha; mavjud APScheduler yetarli (4.3). Agar korporativ standart Airflow'ni majburlasa — OD-5. |
| **D-7** | **`BRB iABS (Read-only)` bitta qatorga siqilgan.** Holbuki bu tarmoq segmentatsiyasi, hisobga kirish, DB audit va xavfsizlik ro'yxatidan o'tishni talab qiladi. "Integratsiya 2 hafta"ga sig'maydi. | 7.2 / 11 | O'rta | 14.3: alohida ish oqimi, 8 PD kod + 5 PD kelishuv; andoza sifatida `app/chakana_ai.py` (DWH-DS'ga OAuth2 `client_credentials`) to'liq qayta ishlatiladi. Kritik yo'lda: ro'yxatdan o'tish boshlanishi 1-haftada. |
| **D-8** | **RBAC talab qilingan, lekin rollar yo'q.** NFR "role-based access control" deydi, qaysi rollar va qaysi huquqlar — aytilmagan. | 6 | O'rta | 13.1: 4 rol va aniq matritsa. Mavjud kodda faqat obyekt egaligi bor (`products.py:54` `created_by == owner`), rol yo'q — shu sabab bu haqiqiy yangi ish. |
| **D-9** | **§2 tugallanmagan gap** ("Taqqoslash jarayonining sezilarli" — kim nima qiladi aytilmagan) va FR-03 manba boshqaruvi kabi talablarda "qanday boshqariladi" yo'q (hozir manbalar kodda ro'yxatlangan). | 2 / 5.1 | Past | §2 bandi quyidagicha o'qiladi: "taqqoslash jarayonining sezilarli davomiyligi". FR-03: manba konfigratsiyasi DB'ga ko'chiriladi (`sources` jadvali, 7.2), admin UI'dan qo'shiladi/o'chiriladi (12-bo'lim). |

---

## 4. ARXITEKTURA QARORI: IKKI VARIANT

TT buyurtmachi qarori bilan **ikki variantni ham** solishtirib chiqadi. Qaror nuqtasi: 0-qadam (19.1) oxiri.

### 4.1 A variant — `Bank's News` ichida yangi modul

Bitta FastAPI ilovasi, bitta PostgreSQL, bitta scheduler. Yangi kontrlar `credit_*` prefiksi bilan alohida sxemada, yangi routelar `/api/compare/*`, `/api/monitor/*`, `/api/admin/*`. Frontend bitta SPA ichida yangi bo'lim sifatida.

### 4.2 B variant — alohida servis (yangi repo)

`brb-competitive-analysis` — alohida FastAPI + baza + ishchi jarayon. `Bank's News`dan konnektor kutubxonasi nusxalanadi yoki umumiy paketga chiqariladi; ikki servis alohida joylashtiriladi.

### 4.3 Solishtirish matritsasi

| Mezon | A variant | B variant |
|---|---|---|
| SSO (ONE-ID), E-IMZO qayta ishlatilishi | To'liq, `app/oneid.py` o'zgarishsiz | Alohida ulangandan keyin, alohida klient ro'yxatdan o'tadi |
| Vault/sir boshqaruvi, sozlamalar profili | Mavjud `config/` paketi | Qayta quriladi (1.5 PD) |
| Chiqish siyosati (`outbound.py` faollik oynasi, host oralig'i, jitter) | To'liq qayta ishlatiladi — bank saytlari oldidagi xatti-harakatimiz bitta bo'ladi | Nusxalanadi; ikki servis bir xil bankni turli vaqtda so'rab, anti-bot riskini ikki barobar oshiradi |
| Resilience (breaker), `rate_limiter`, `ttl_cache` | Bepul | Alohida o'rnatish va sozlash |
| DWH/iABS uchun OAuth2 andozasi (`chakana_ai.py`) | Tayyor | Nusxalanadi |
| 43 bank konnektori | Bir bazada; kredit konnektorlari `product_type` qo'shish orqali | Nusxalash yoki umumiy paket chiqarish (ikkinchisi to'g'ri, lekin 6-8 PD + versiyalash og'rig'i) |
| Mavjud `bank_rates` ma'lumoti | Bir bazada JOIN qilib bo'ladi | Replikatsiya yoki servislararo so'rov kerak |
| Test/CI/Sonar/Sentry | Mavjud quvishga qo'shiladi | Ikkinchi quvish, ikkinchi Sonar loyihasi |
| Ishga tushirish kontaktlari | Bitta | Ikkita (ikkinchi cluster/nodesetizatsiya, alohida kuzatuv) |
| Izolyatsiya (xato tarqalishi) | Zaifroq: og'ir LLM ish yukidagi bilaroq agregatsiyaga ta'sir qiladi | Kuchli |
| Mustaqil joylashtirish/bo'shashish ritmi | Bitta reliz | Har biri alohida |
| Jamoa tarkibi | 1 ta kod bazasi, chegara yo'q | Ikki repoda parallel ishlash, chegara kelishuvi |
| Taxminiy boshlang'ich xarajat | **0,75×** | **1,35×** (asos, ulangandan keyin 0,75) |
| 3 yillik xarajat | Past (bitta nazorat nuqtasi) | Yuqori (ikkita versiya, ikkita bog'liqlik to'plami) |

### 4.4 Tavsiya va qaror sharti

**A variantni tavsiya qilaman**, lekin **bitta shart bilan**: og'ir ishlar (skreyping sikli, LLM chaqiruvi, hisobot generatsiyasi) so'rov-so'rov asosida API'ga qo'shib qo'yilmasin, balki izchil ishchi-loyiha orqali yuritilsin (`fetch` → `extract` → `score` → `notify` vazifalari) va **API sinfi ularning bajarilishini kutmasin**.

Agar bu ajratishni bizning intizomimiz ta'minlay olmasa yoki bank ichida "razvedka ma'lumotlari ombori" boshqa tizimlari bilan bir xil konteynerda turishini xavfsizlik bo'limi rad etsa — unda B variant olinsin. B variantda A variantning barcha qayta ishlatishlari umumiy ichki paketga (`brb-bankcollect`) chiqarilishi shart; nusxalash qabul qilinmaydi.

**Qabul qilinmagan holatida:** 4.1 bo'limi dizayn bazasi sifatida ishlatilsin, bu — 0-qadamning oxirgi ochiq qarori (OD-6).

---

## 5. MAVJUD BAZA — QAYTA ISHLATILADIGAN QISMLAR

TT taxminga emas, kodga asoslanadi. Quyidagilarning barchasi **allaqachon ishlayapti**:

| Imkoniyat | Manba | TT'dagi roli |
|---|---|---|
| Konnektor andozasi (`fetch_raw` → `parse` → `run` → `_save`, `RunResult`) | `app/connectors/base.py:71-108` | Kredit konnektorlari shu interfeysdan meros oladi |
| Konnektor registry (hozir **118** ro'yxatdan o'tgan ekzemplar) | `app/connectors/registry.py` | FR-03 uchun DB'ga ko'chiriladi (7.5) |
| 43 bank ro'yxati, kod/slug kelishuvi | `app/banks.py` | `sources` jadvali shu kodlarni ishlatadi |
| Playwright (JS-render), HTML kartalar, HTTP qatlami | `connectors/playwright_fetch.py`, `html_cards.py`, `http.py` | L1 bosqich poydevori |
| Scheduler (`max_instances=1`, `coalesce`, cycle deadline, `cancel_futures`) | `app/scheduler.py` | Detection sikli shu uslubda qo'shiladi — sikullar ustma-ust chiqmaydi |
| **Chiqish siyosati:** faollik oynasi + host oralig'i + jitter | `app/outbound.py` | D-5 ga texnik javob; yangi sikllar ham shu darvozadan o'tadi |
| Circuit breaker, `rate_limiter`, `ttl_cache` | `app/resilience.py`, `rate_store.py`, `ttl_cache.py` | LLM gateway'ga ham xuddi shu breaker |
| **BRB ichki tizimiga OAuth2 `client_credentials` ulanish andozasi** (token keshi, muddatdan oldin yangilash, 401 → `force_refresh`) | `app/chakana_ai.py` (DWH-DS, `dwh-ds.brb.uz`) | **iABS read-only integratsiyasi shu andozaning ko'chirmasidir** (D-7) |
| ONE-ID SSO: authorization_code + PKCE, JWKS, `aud` siyosati | `app/oneid.py`, `config/base.py` | BT'dagi "BRB SSO" — **notanish emas, ishlab turibdi** |
| E-IMZO autentifikatsiya | `app/eimzo.py` | Ikkilamchi kirish eshigi |
| Token bekor qilish bazada (`RevokedToken`) + tozalovchi job | `app/auth.py:55`, `scheduler.purge_expired_revocations` | Sessiya siyosati tayyor |
| Sirlar boshqaruvi: Vault/.env profili (`PROFILE`, `SECRETS_BACKEND`) | `config/{base,dev,staging,prod,vault}.py` | LLM gateway kaliti shu yerdan |
| Xato yig'ish + log tashishi | `sentry.py`, `logging_config.py`, `python-logstash-async` | 16-bo'lim |
| Alembic, PostgreSQL 16, compose | `alembic.ini`, `migrations/`, `docker-compose.yml` | Yangi jadvallar alembic orqali |
| Sifat eshiklari | `.gitlab-ci.yml`, `sonar-project.properties`, 87 ta test fayli | 18-bo'lim shu quvish ichida |

**Mavjud bo'lmagan (yaratiladi):** LLM mijoz, kanonik kredit sxemasi, diff/alert dvigateli, Email/SMS kanallar, Excel/PDF eksport, RBAC rollari, PDF parse kutubxonasi, Redis (kerak emas — 15.4).

---

## 6. ARXITEKTURA (A variant detallizatsiyasi)

```
[34 bank sayti / PDF]      [BRB iABS read-only]        [DWH-DS]
        |                          |                        |
  +-----v-------+                  |   OAuth2 client_credentials (andoza: chakana_ai.py)
  | L1 Collector|<-- outbound.py darvozasi (oyna, oralig', jitter, breaker)
  +-----+-------+
        | raw (HTML/PDF) + sahifa versiyasi (sha256)
  +-----v-------+
  | L2 Extractor|--> ichki LLM gateway (structured output + iqtibos-span)
  +-----+-------+
        | CreditOfferDraft + confidence
  +-----v-------+
  | L3 Review   |--> review queue (past confidence / anomaliya) --> tasdiq
  +-----+-------+
        | tasdiqlangan snapshot
  +-----v--------------------------------------------------+
  | PostgreSQL: sources / credit_offers / *_snapshots / change_events |
  +-----+------------------------+-------------------------+
        |                        |
  +-----v-------+        +-------v--------+
  | Compare     |        | Alert engine   |--> Email | SMS | tizim ichi
  | (skoring)   |        +----------------+
  +-----+-------+
        | API /api/compare  /api/monitor  /api/admin  --> React SPA (UZ/RU)
```

**Qat'iy qoida:** API qatlami hech qachon LLM chaqiruvi yoki skreyping tugishini kutmaydi (4.4 sharti). Og'ir ish — jadval yoki navbat orqali.

Ishga tushirish rejasi (A variant, bitta jarayon ichida):

| Sikl | Chastota | Vazifa |
|---|---|---|
| To'liq yig'ish (mavjud) | `FETCH_INTERVAL_MINUTES` (hozir 60 daqiqa) | Barcha konnektorlar; **mavjud xatti-harakat o'zgarmaydi** |
| Kredit yig'ish | `CREDIT_FETCH_INTERVAL_HOURS=4` | 34 bank kredit sahifalari, to'liq parsel |
| **Detection sweep** | `DETECT_INTERVAL_MINUTES=20` | Sahifa versiyasini solishtirish; o'zgartsa — ekstraktsiyani navbatga qo'yish |
| Ekstraksiya navbati | uzluks (worker'lar) | LLM + confidence + review'ga tushirish |
| Alert dispatch | voqea chiqishi bilan + 60 s skan | Yetkazish, urinishlar, kvota |
| Tozalash | 24 soat | Eskirgan yozuvlar (7.3) |

---

## 7. MA'LUMOT MODELI — HAL QILUVCHI BO'LIM

### 7.1 Nega `bank_rates` ustiga qurilmaydi

Hozirgi sxema (`app/models.py:77`) butun mahsulotni `data: JSON` blokgiiga soladi: `(bank_code, product_type, segment, fetched_at) + JSON`. Agregator uchun bu to'g'ri — u yerda ma'lumot **ko'rsatiladi**.

Bu tizimda esa ma'lumot **taqqoslanadi, differensiallanadi va baholanadi**. JSON ustida:

- 12 parametrning biri bo'yicha trend qurish har so'rovda kalit nomini taxmin qilishni talab qiladi (bir bankda `rate`, ikkinchisida `interest`, uchinchisida `"22,5%"`);
- Parametr qiymatining 12 oy davomida qachon o'zgarganini aniqlab bo'lmaydi;
- Aniqlikni parametr kesimida o'lchash (M-2) umkin emas.

Shu sabab **alohida kanonik sxema** kiritiladi. `bank_rates` o'z vazifasini bajaradi — ikkalasi bir bazada yonma-yon yashaydi, `bank_code` orqali bog'lanadi.

### 7.2 Jadvallar

```sql
-- Manbalar KODDAN DB'ga o'tadi (FR-03, D-9)
CREATE TABLE sources (
  id            SERIAL PRIMARY KEY,
  bank_code     VARCHAR(30) NOT NULL,           -- app/banks.py kodlari bilan kelishilgan
  page_url      TEXT        NOT NULL,
  product_kind  VARCHAR(40) NOT NULL,           -- aylanma_kapital | investitsion | ...
  segment       VARCHAR(20) NOT NULL,           -- business | individual
  method        VARCHAR(20) NOT NULL,           -- http | playwright | pdf
  selector_hint JSONB,                          -- L1 uchun ixtiyoriy yo'naltirgich
  enabled       BOOLEAN NOT NULL DEFAULT TRUE,
  priority      SMALLINT    NOT NULL DEFAULT 100,
  robots_policy VARCHAR(20) NOT NULL DEFAULT 'pending',  -- yuristik tasdiq (13.4)
  UNIQUE (bank_code, page_url)
);

-- Mahsulot: identifikatsiya qilingan offer, versiyalanmaydi
CREATE TABLE credit_offers (
  id            BIGSERIAL PRIMARY KEY,
  source_id     INT  NOT NULL REFERENCES sources(id),
  bank_code     VARCHAR(30) NOT NULL,
  external_name VARCHAR(300) NOT NULL,          -- bankdagi nomi, o'zgartirmasdan
  product_kind  VARCHAR(40) NOT NULL,
  segment       VARCHAR(20) NOT NULL,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  first_seen_at TIMESTAMPTZ NOT NULL,
  last_seen_at  TIMESTAMPTZ NOT NULL
);

-- Parametr lug'ati: 12 parametr shu yerda (24-bo'lim)
CREATE TABLE credit_params (
  code        VARCHAR(40) PRIMARY KEY,          -- nominal_rate | effective_rate | amount_min ...
  name_uz     VARCHAR(120) NOT NULL,
  name_ru     VARCHAR(120) NOT NULL,
  value_type  VARCHAR(16) NOT NULL,             -- number|percent|money|duration|enum|text|bool|array
  unit        VARCHAR(20),                      -- UZS | USD | month | year | percent
  weight      NUMERIC(5,2),                     -- biznes og'irligi (D-3, matritsadan)
  nullable_ok BOOLEAN NOT NULL DEFAULT TRUE
);

-- Bitta offer uchun bitta parametr qiymati. Tiplar ALOHIDA ustunda — JSON emas.
CREATE TABLE credit_offer_params (
  offer_id    BIGINT NOT NULL REFERENCES credit_offers(id) ON DELETE CASCADE,
  param_code  VARCHAR(40) NOT NULL REFERENCES credit_params(code),
  num_value   NUMERIC(18,4),
  txt_value   TEXT,
  enum_code   VARCHAR(40),
  currency    CHAR(3),
  unit        VARCHAR(20),
  raw_quote   TEXT NOT NULL,                    -- manbadagi xarfma-xarf satr (L2 iqtibosi)
  confidence  NUMERIC(4,3),                     -- 0.000-1.000
  method      VARCHAR(12) NOT NULL,             -- rule | llm | human
  reviewed_by VARCHAR(64),
  reviewed_at TIMESTAMPTZ,
  PRIMARY KEY (offer_id, param_code)
);

-- Snapshot: tarix va diff shu ustida (FR-16, AC-07)
CREATE TABLE credit_offer_snapshots (
  id           BIGSERIAL PRIMARY KEY,
  offer_id     BIGINT NOT NULL REFERENCES credit_offers(id),
  snapshot_at  TIMESTAMPTZ NOT NULL,
  content_hash CHAR(64) NOT NULL,               -- parametr jamlanmasining sha256
  params       JSONB NOT NULL                   -- o'qish tezligi uchun replika
);
CREATE INDEX ix_snapshot_offer_time ON credit_offer_snapshots (offer_id, snapshot_at DESC);

CREATE TABLE page_versions (                    -- detection uchun (10.1)
  id BIGSERIAL PRIMARY KEY,
  source_id INT NOT NULL REFERENCES sources(id),
  checked_at TIMESTAMPTZ NOT NULL,
  content_hash CHAR(64) NOT NULL,               -- sahifa yoki tanlangan blok sha256
  http_status SMALLINT, error TEXT
);

CREATE TABLE extraction_runs (                  -- M-1 shu jadvaldan hisoblanadi
  id BIGSERIAL PRIMARY KEY, source_id INT REFERENCES sources(id),
  started_at TIMESTAMPTZ NOT NULL, finished_at TIMESTAMPTZ,
  status VARCHAR(16) NOT NULL,                  -- ok | partial | error | skipped_window
  records_found SMALLINT DEFAULT 0, llm_calls INT DEFAULT 0, error TEXT
);

CREATE TABLE change_events (                    -- alert asosi (10.2)
  id BIGSERIAL PRIMARY KEY, offer_id BIGINT NOT NULL,
  param_code VARCHAR(40),
  detected_at TIMESTAMPTZ NOT NULL,
  old_value TEXT, new_value TEXT,
  delta NUMERIC(18,4), delta_pct NUMERIC(8,2),
  event_type VARCHAR(20) NOT NULL,              -- new_offer | param_changed | offer_removed
  dedup_key CHAR(64) NOT NULL UNIQUE            -- takrorlanishni baza darajasida kesadi
);

CREATE TABLE subscriptions (
  user_id VARCHAR(64) NOT NULL, bank_code VARCHAR(30) NOT NULL,
  param_code VARCHAR(40) NOT NULL, channel VARCHAR(16) NOT NULL,
  threshold_pct NUMERIC(6,2), quiet_hours VARCHAR(20),
  UNIQUE (user_id, bank_code, param_code, channel)
);
CREATE TABLE notification_deliveries (
  id BIGSERIAL PRIMARY KEY, event_id BIGINT NOT NULL,
  user_id VARCHAR(64) NOT NULL, channel VARCHAR(16) NOT NULL,
  status VARCHAR(16) NOT NULL, attempts SMALLINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL, delivered_at TIMESTAMPTZ, last_error TEXT,
  UNIQUE (event_id, user_id, channel)           -- bir voqea → bir kanal → bir xabar
);

CREATE TABLE roles (code VARCHAR(20) PRIMARY KEY, name_uz VARCHAR(80), name_ru VARCHAR(80));
CREATE TABLE user_roles (
  user_id VARCHAR(64) NOT NULL, role_code VARCHAR(20) NOT NULL REFERENCES roles(code),
  granted_at TIMESTAMPTZ NOT NULL, granted_by VARCHAR(64), PRIMARY KEY (user_id, role_code)
);
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY, at TIMESTAMPTZ NOT NULL, user_id VARCHAR(64),
  action VARCHAR(40) NOT NULL, object VARCHAR(120), detail JSONB
);
CREATE TABLE gold_annotations (                 -- etalon to'plam (18.2)
  id BIGSERIAL PRIMARY KEY,
  offer_id BIGINT NOT NULL REFERENCES credit_offers(id),
  param_code VARCHAR(40) NOT NULL REFERENCES credit_params(code),
  gold_value TEXT NOT NULL,
  labeler VARCHAR(64) NOT NULL, second_labeler VARCHAR(64),
  agreed BOOLEAN NOT NULL DEFAULT FALSE, annotated_at TIMESTAMPTZ NOT NULL,
  UNIQUE (offer_id, param_code, labeler)
);
```

### 7.3 Tarix va saqlash muddati

- Snapshot **faqat qo'shiladi**, hech qachon o'chirilmaydi; joriy holat = offer bo'yicha eng katta `snapshot_at`.
- `content_hash` o'zgarmasa snapshot yozilmaydi — shunda 12 oylik tarix shishib ketmaydi va `change_events` sababsiz to'ilmaydi (soxta alertlar manbai aynan shu).
- Saqlash: snapshot 24 oy (talab 12 oy — ikki barobar zaxira), `page_versions` 90 kun, `notification_deliveries` 180 kun.
- **AC-07 haqida ogohlantirish:** 12 oylik tarix tizim ishga tushgan kuni hosil bo'lmaydi — u birinchi kundan yig'ila boshlaydi. Qabul aktida bu band "tarix yig'ish mexanizmi ishlaydi va so'rovlar javob beradi" deb qabul qilinadi; 12 oy to'lgach qayta tekshiriladi. BT bu bandni texnik imkoniyatdan tashqari talab qilmoqda — 22-bo'limda alohida belgilanadi.

### 7.4 Normalizatsiya

Har parametr bazaga kirishdan **oldin** normalizatsiya qilinadi (9.1). Xom matn `raw_quote`da qoladi — kelishmovchilik bo'lsa, qiymat qayerdan olingani ko'rinib turadi. Bu M-2 bahosining asosi.

### 7.5 Migratsiya

Alembic (`migrations/versions/`), faqat oldinga. `sources` boshlang'ich ma'lumoti `app/banks.py` + `registry.py`dan bir martalik skript (`scripts/seed_sources.py`) bilan generatsiya qilinadi; keyin faqat admin UI orqali boshqariladi. `bank_rates` ma'lumoti ko'chirilmaydi.

---

## 8. EKSTRAKSIYA QUVURI (FR-01, FR-02, FR-05, D-4)

### 8.1 Uch bosqich — bitta qoida bilan: **tasdiqlanmagan parametr dashboardga chiqmaydi**

| Bosqich | Nima | Qachon | Natija |
|---|---|---|---|
| **L1 — Deterministik** | Mavjud `BaseConnector`/`HtmlPageConnector` andozasida selector/regex bilan o'qish | Har doim birinchi | `method='rule'`, `confidence=1.000` |
| **L2 — LLM** | Strukturalangan chiqarish (`JSON Schema` majburiy), har parametr uchun **iqtibos-span** | L1 parametzni topmagan yoki format buzilgan bo'lsa | `method='llm'`, `confidence` model scores |
| **L3 — Inson** | Review queue: confidence < `REVIEW_THRESHOLD` (default 0.90), qiymat anomaliyasi, yoki parametr birinchi marta ko'rilyapti | L2 dan keyin | `method='human'`, `reviewed_by` to'lgan |

Aniqlik mezonining (M-2) ma'nosi shu bo'linishda: **har parametrning `method`i ko'rinib turadi**, shuning uchun "98% aniqlik" qaysi qatlamdan yutilgan — bilinadi.

### 8.2 LLM erishuvlarga qarshi himoya (hal qiluvchi intizom)

1. **Structured output.** Model erkin matn yozmaydi — sxemaga bo'ysunadigan obyekt chiqaradi; sxemaga tushmagan javob texnik xato hisoblanadi, ma'lumot emas.
2. **Iqtibosspan majburiy.** Har parametr uchun model manbadan **xarfma-xarf satr** keltirishi shart. Sistemada tekshiriladi: `raw_quote` xom HTML/PDF matnida roppa-rosa topilmasa → qabul qilinmaydi, review'ga tushadi. Bu **bitta tekshiruv hallyutsinatsiyaning katta qismini kesadi**.
3. **Har qatorda `temperature=0`**, har bir parametr alohida so'rov (aralash holda emas), chunki bir xatolik butun jadvalni buzmasin.
4. **Qiymat oralig'i nazorati (sanity envelope).** Stavka 0-100%, muddat 0-600 oy, summa manfiy emas; tashqariga chiqsa — avtomatik reject.
5. **Modelgateway tashqariga chiqmaydi.** Kredit shartlari — bank uchun sezgir ma'lumot; so'rovlar faqat bank ichidagi LLM gateway'ga (OD-7). Agar bunday gateway bo'lmasa, FR-02 ning L2 bosqichi **qabul qilingan cheklov bilan** qoldiriladi va L1 + L3 bilan yopishadi; bu holda M-2 ni "≥ 98%" deb imzolash **mumkin emas** — bu holat 23-bo'limdagi eng og'riqli ochiq qarordir.
6. **Breaker va kvota.** LLM gateway'ga `app/resilience.py` breaker'i, kunlik so'rov limit va narx limiti (`LLM_DAILY_CALL_CAP`). Gateway javob bermasa — quvur to'xtamaydi: L1 natijasi saqlanadi, L2 navbatga qaytadi.

### 8.3 Manba sinishini aniqlash (eng ko'p uchraydigan real nosozlik)

Bank sayti dizayni o'zgarsa, L1 sezmasdan "hech narsa topilmadi" deb javob beradi — bu nosozlik emasdek ko'rinadi, lekin ma'lumot yo'qoladi. Shu sabab:

- Har parametr uchun **tapuvchi (hit rate)** kuzatiladi; 7 kunlik o'rtacha 95% dan 40% ga tushsa → `source_degraded` voqeasi, manba avtomatik `priority` pasaytiradi va admin'ga chiqadi.
- Sahifa javob qaytarmasa yoki HTTP 200 bo'lib tana hajmi keskin kichraylsa (`page_versions` qatori) → darhol signal.
- Hech qachon "javob bor-yo'q" emas, **"kutilgan parametr yo'q"** holati alohida status: `extraction_runs.status = 'partial'`.

---

## 9. TAQQOSLASH VA TAHLIL DVIGATELI (FR-05…FR-09, D-3)

### 9.1 Normalizatsiya (taqqoslash bundan keyin boshlanadi)

| Xom ko'rinish | Kanonik |
|---|---|
| `22,5 %`, `22.5%`, `yillik 22,5` | `num_value=22.5000, unit='percent'` |
| `50 mln so'm`, `50 000 000 UZS`, `50 000 USD` | `num_value=50000000, currency='UZS'` (valyuta — alohida ustun, aralashtirilmaydi) |
| `3 yil`, `36 oy`, `hozrga qadar` | `unit='month'`, `hozrga qadar` → `NULL` + `enum_code='until_end_of_term'` |
| `garovsiz`, `ko'chmas mulk garovi` | `enum_code` (24-bo'limdagi qat'iy ro'yxat) |
| `0% birinchi 3 oy` | `grace_period_months=3` **va** `commission_once` — bir gapning ikki parametrga tarqatilishi |

### 9.2 Effektiv stavka — taqqoslashning yagona asosi

Nominal stavka aldaydi: komissiya va boshlang'ich badal haqiqiy qiymatni o'zgartiradi. Shu sabab taqqoslash **effektiv yillik stavka (EIR)** ustida bajariladi:

```
EIR: ichki normallashtiruvchi stavka r, unda
  SUM( to'lov_t_i / (1 + r/12)^(t_i) )  =  mijoz oladigan toza summa
  (boshlang'ich badal va bir martalik komissiya "oladigan summa"dan ayiriladi;
   oylik komissiya to'lov oqimiga qo'shiladi)
```

Bu — PDM/panjarali hisoblash (`scipy` emas, sof Python, testlar bilan qoplanadi). Uchta nazorat misoli (qo'lda hisoblangan) `tests/test_eir.py` ichida doimiy saqlanadi.

### 9.3 Taqqoslash guruhlash va skoring

1. **Guruhlash:** faqat o'xshash mahsulotlar taqqoslanadi — `product_kind` + `segment` + summa oralig'i kesishuvi + muddat oralig'i kesishuvi. Guruh bo'lmasa, jadval "taqqoslash imkoni yo'q" deb ko'rsatadi; **majburiy birlashtirish qilmaydi**.
2. **Skoring:** har mezon bo'yicha normalizatsiya (min-max emas — persentil), so'ng `credit_params.weight` bo'yicha og'irlikli yig'indi.
3. **Og'irliklarni TT belgilamaydi.** Ular `PRICING-COMPARISON-MATRIX` hujjatidan `credit_params.weight`ga yuklanadi (BRB-03, D-3). Skoring formulasini o'zgartirish — audit yozuviga chiqadi (`audit_log`).
4. **Reyting yolg'iz raqam emas:** har o'rinda "negu" ko'rsatiladi (qaysi parametr qancha ta'sir qildi) — qora quti qabul qilinmaydi.

### 9.4 SWOT o'rniga — gap-analysis (D-4)

BT FR-07 da "SWOT tarzida report" deydi. SWOTni LLM'ga generatsiya qildirish — xulosa ixtiro qilish degani. TT buni almashtiradi:

- Har bir BRB mahsuloti uchun guruhidagi **mediana/p25/p75** ga nisbatan farqlar ro'yxati, aniq raqam va aniq manba bilan ("foiz stavkasi guruh medianasidan +3.2 p.p. yuqori — 11 ta raqobatchidan 9 tasi past");
- Yo'q parametrlar ajratiladi: BRB'da bor/raqobatchida yo'q va aksincha — bu "imkoniyat" bloki;
- Matnli xulosalar shu raqamlar **ustiga** quriladi va har gapning oldida qaysi parametr/qaysi snapshot asos ekanligi ko'rsatiladi. Raqamsiz xulosa UI'da chiqmaydi.

### 9.5 FR-08 (Tendensiya tahlili) — grafik emas, rezolyutsiya muammosi

BT mezonisi: "Trend chart mavjud". Bajarilishi oson talab, lekin o'lchami noto'g'ri baholangan — muammo chizishda emas, ma'lumot zichligida:

- Trend `snapshots` ustidan quriladi, `snapshots` esa FR-04 bo'yicha **kuniga ~2 mahal** yangilanadi. Real rezolyutsiya shu — **kunlik**. "So'nggi 24 soat dinamikasi" grafigi 0–2 ta nuqtadan iborat bo'ladi: chiziq emas, kasratka chiqadi va noto'g'ri xulosa beradi.
- Shuning uchun default ko'lam **≥ 90 kun**; kunlik ko'lam faqat alohida nuqtalar (`change_events`) bilan, chiziqsiz ko'rsatiladi. Bu — BT talabini bajarish va bir vaqtda yolg'on grafik chizmaslik.
- Har nuqta = guruh **medianasi** + p25/p75 tasmasi (34 bankda bitta ekstremal e'lon o'rtacha chiziqni buzadi; mediana barqaror).
- Trend = **kuzatilgan o'zgarish, prognoz emas**. Regressiya/bo'lg'usi chiziq qasddan yo'q: AC-07 izohidagi sababga ko'ra uzluksiz 12 oylik qator birinchi bosqichda fizik mavjud emas. Prognoz alohida talab va alohida javobgarlik — OD-8 qaroriga bog'langan.
- Texnik qaror (chiqimsiz, AT ichida): yangi grafik kutubxonasi qo'shilmaydi — mavjud qo'lda yozilgan SVG dvigateli kengaytiriladi (`frontend/src/shared/lib/mpl-chart.ts::buildChartGeometry`, `statsFromPoints`, `shared/ui/sparkline.tsx`). Asos: `frontend/package.json`da recharts/echarts/d3 **yo'q**, va kutubxona AC-04 (≤ 3 soniya) byudjetini to'g'ridan-to'g'ri yeydi (15.3).

Amalga oshirish: `/api/monitor/trends` (11-bo'lim) + `pages/trends` (12-bo'lim).

### 9.6 FR-09 (AI tavsiyalar) — doirada, lekin past ishonch bilan

Doiraga kiritilgan, lekin **qabul mezonisiz**. Tavsiya etiladi: birinchi relizda "tavsiya" bloki **o'rniga** "kuzatilgan nomuvofiqliklar" ro'yxati chiqarilsin; generativ tavsiya — OD-8 bo'yicha qarordan keyin.

---

## 10. MONITORING VA ALERT (FR-10, FR-11, FR-12, D-1)

### 10.1 D-1 ni yechish: ikki xil SLA

| Atama | Ta'rif | SLA | Mexanizmi |
|---|---|---|---|
| **Detection latency** | O'zgarish saytga chiqqandan biz uni bilguncha | **P95 ≤ 45 daqiqa** | 20 daqiqalik `DETECT_INTERVAL_MINUTES` yengil sweep: sahifa versiyasi (hash) solishtiriladi, og'ir parsel emas |
| **Full refresh** | To'liq parsel va bazani yangilash | `CREDIT_FETCH_INTERVAL_HOURS=4` | FR-04 dagi "har 24 soat" shu sikl ichida qanoatlanadi |
| **Delivery latency** | Aniqlagandan xabar yetguncha | **P95 ≤ 5 daqiqa** | Voqea chiqishi bilan dispatch |

Shu bilan BT'dagi FR-04 ↔ FR-10 ziddiyati yo'qoladi: **tez nazorat qilish, sekin qayta ishlash.** Qo'shimcha: admin UI'da "tekshirishni boshlash" tugmasi (FR-04 "favqulodda yangilanish") — bitta manba yoki butun doira; navbatga qo'yadi, so'rovni bloklamaydi.

### 10.2 Voqea modeli

1. Snapshot hash'i oldingisi bilan solishtiriladi. Farq = `change_events` qatori (parametr darajasida).
2. **`dedup_key` UNIQUE** — bitta o'zgarish bir necha marta alert bermaydi (eng ko'p uchraydigan amaliy nosozlik).
3. **Shovqin chegarasi:** `subscriptions.threshold_pct` — masalan foiz 0.3 p.p. dan o'zgarsagina yuboriladi; `<` qiymatlar yig'ilib, oylik hisobotga (digest) ketadi.
4. Yangi mahsulot va mahsulot yo'qolishi — alohida `event_type`; "yo'qolishi" darhol emas, ikki ketma-ket siklda tasdiqlansa yuboriladi (vaqtincha sayt nosozligi "mahsulot olib tashlandi" bo'lib chiqmasin uchun).

### 10.3 Yetkazish

| Kanal | Manba | Holat |
|---|---|---|
| Tizim ichi | SPA notification markazi | eng arzon, har doim yoqilgan |
| Email | BRB SMTP relay (OD-9) | yaratiladi |
| SMS | BRB SMS gateway (OD-9) | yaratiladi; **kvota** — bir foydalanuvchiga kuniga `SMS_DAILY_CAP` (default 20), oshsa digest'ga o'tadi |

Urinishlar: 3 marta, eksponensial oraliq bilan; `notification_deliveries` holati, `attempts`, `last_error` — to'liq saqlanadi. `quiet_hours` (default 21:00-07:00) — yuqori ahamiyatli voqealardan tashqari; bu `outbound.py` falsafiyasiga mos.

### 10.4 FR-12 — obuna sozlamalari

UI: bank × parametr × kanal × shovqin chegarasi × tinch soatlar. Bitta kanal ishlamay qolsa, ikkinchisi ishlayveradi (AC "kamida 2 kanal" shu bilan bajariladi, 3-channelar emas).

---

## 11. API SHARTNOMASI

Uslub mavjud kodda: `/api/...` prefixli, JWT `require_auth`, xatolar `detail` maydonida. Yangi guruhlarga ham RBAC qo'llanadi (13.1).

| Metod | Manzil | Rol | Vazifa |
|---|---|---|---|
| GET | `/api/compare/matrix` | analyst+ | Taqqoslash jadvali: `product_kind`, `segment`, filtrlar, `params[]` |
| GET | `/api/compare/options` | analyst+ | Filtrlar uchun qimmlar (bank, mahsulot turi, sana oralig'i) |
| GET | `/api/compare/gap/{bank_code}/{offer_id}` | analyst+ | Gap-analysis (9.4) |
| GET | `/api/compare/ranking` | analyst+ | Og'irlikli reyting + "negu" izohi |
| GET | `/api/monitor/trends` | analyst+ | Parametr bo'yicha vaqt qatori (snapshot'lar) |
| GET | `/api/monitor/events` | viewer+ | Oxirgi o'zgarishlar tasmasi |
| GET/PUT | `/api/monitor/subscriptions` | viewer+ | FR-12 obunalar |
| GET | `/api/monitor/deliveries` | admin | Yetkazish jurnali |
| GET/POST/POST | `/api/admin/sources` … `/sources/{id}:rescan` | admin | FR-03 manba CRUD + qo'lda tekshirish |
| GET/PATCH | `/api/admin/review/queue`, `/api/admin/review/{id}` | reviewer | L3 tasdiq: qiymat, iqtibos, reject sababi |
| GET | `/api/admin/sources/{id}/health` | admin | 8.3 tapuvchi statistikosi |
| GET | `/api/export/matrix.xlsx` / `.pdf` | analyst+ | FR-15 eksport |
| GET | `/api/meta/credit-params` | viewer+ | 12 parametr lug'ati (UZ/RU) |

**Kelishuv qoidalari:** barcha ro'yxat javoblari `limit/offset`, `page` emas — vaqt qatorlari `from`/`to` (ISO-8601, UTC) va `tz=Asia/Tashkent` ko'rsatmasi bilan; 409 — idempotentlik konflikti; 422 — noma'lum parametr kodi. Xatolar `detail` matnida foydalanuvchi tilida emas, **kod** bilan qaytadi (i18n frontenda) — mavjud `/api/npl` uslubidagi `_AGG_RESPONSES` amaliyotiga mos.

## 12. FRONTEND (FR-13, FR-14, FR-15, FR-12)

Feature-sliced struktura saqlanadi (`frontend/src/{app,entities,features,pages,shared,widgets}`).

| Qatlam | Yangi |
|---|---|
| `entities/credit-offer`, `entities/credit-param` | modellalar, react-query hook'lari |
| `features/compare-filters` | bank, mahsulot turi, parametr, sana filtri (FR-14) |
| `features/compare-table` | dinamik jadval, ustunlar tanlanadi, BRB ustuni ajratilgan ko'rinadi (FR-06) |
| `features/gap-analysis` | raqamli farq kartalari (9.4) |
| `features/alert-subscriptions` | obuna matritsasi (FR-12) |
| `pages/compare`, `pages/trends`, `pages/events`, `pages/review`, `pages/sources-admin` | yangi sahifalar |
| `widgets/notification-center` | tizim ichi xabarlar |

Talablar: UZ/RU (mavjud `shared/lib/i18n/dictionary.ts`), jadvalda **virtualizatsiya** (34 bank × mahsulotlar + 12 parametr = minglab katak, M-5 shu yerida yiqiladi), mobil moslashuv shart emas (ichki ish stoli), eksport tugmasi jadval ustida.

---

## 13. XAVFSIZLIK

### 13.1 RBAC — 4 rol, aniq matritsa (D-8 yechimi)

| Huquq | viewer | analyst | reviewer | admin |
|---|:-:|:-:|:-:|:-:|
| Dashboard/tarix/o'qish | + | + | + | + |
| Gap-analysis, reyting, eksport | — | + | + | + |
| Obuna sozlash (o'zi uchun) | + | + | + | + |
| Review queue tasdiqi | — | — | + | + |
| Manba CRUD, "hozir tekshirish" | — | — | — | + |
| Yetkazish jurnali, audit log | — | — | — | + |
| Rol biriktirish, og'irliklar o'zgartirish | — | — | — | + |

Rol tekshiruvi API qatlamida dependency sifatida (`require_role("analyst")`), frontend'da emas — UI'da tugmaning ko'rinmasligi xavfsizlik chora emas. `user_roles` bo'sh bo'lsa hech kim analyst emas (fail-closed, ONE-ID `aud` siyosati falsafiyasi bilan bir xil). Rol birinishi: ONE-ID token claim'laridagi `authorities` (Java reference paritysi) → `user_roles`; claim bo'sh bo'lsa admin qo'lda biriktiradi.

### 13.2 Autentifikatsiya
Mavjud ONE-ID (authorization_code + PKCE, `aud` majburiy) va E-IMZO o'zgarishsiz. Yangi: sessiya umr bo'ylab `RevokedToken` nazorati; review queue amallari faqat One-ID orqali aniqlangan foydalanuvchi (`require_identified_auth` amaliyoti) bilan — kim tasdiqlagani `reviewed_by`da ko'rinadi.

### 13.3 Sirlar
LLM gateway kaliti, SMTP/SMS kredensiallari, iABS read-only paroli — faqat Vault (`SECRETS_BACKEND=vault` profili). Hech qaysiri .env.example, CI log, hujjat yoki commitga tushmaydi (mavjud majburiy skan siyosati). iABS uchun alohida read-only hisob: faqat `SELECT`, alohida IP-ohlak, parolni aylanish muddati bank siyosati bo'yicha.

### 13.4 Tashqi manbalar: texnik + huquqiy qatlam (D-5 yechimi)

Texnik (allaqachon bor, kengaytiriladi):
- Barcha chiqish `app/outbound.py` darvozasi orqali: faollik oynasi 07:00–21:00 (Asia/Tashkent),host oralig'i ≥ 2 s + jitter, breaker. Kredit sweep ham shu darvozadan chiqadi — **istisno yo'q**.
- User-Agent orqali tanishtiruv: `BankNewsBot/1.0 (+mailto:...)` — kim ekanimizni yashirmaymiz.
- robots.txt hurmati: har bir manba uchun `sources.robots_policy` yuristik tasdiqdan oldin `pending` turadi; `crawl-delay` bo'lsa unga rioya qilinadi. 403/429/WAF signal → breaker ochiladi, manba `blocked` holatiga o'tadi va **urinishlar soni oshirilmaydi** ("haker deb block" scenariyidan himoya).

Huquqiy (bizning qo'limizda emas): Yurist boshqarmasi har bir manba uchun foydalanish shartlari xulosasini beradi (BRB-04 / OD-4). U kelmay qolsa: tizim ishlaydi, lekin javobgarlik deklaratsiyasi qabul aktiga yoziladi.

### 13.5 Audit
Review tasdiqlari, manba o'zgarishlari, og'irlik/skoring parametrlari o'zgarishi, eksport faktlari — `audit_log`ga (kim, nima, eski→yangi). Hisobotlarga "ko'rinmagan ma'lumot qo'shish" aybloviga javob shu jurnal.

---

## 14. INTEGRATSIYALAR

| # | Tizim | Holat | Kontrakt | Ish |
|---|---|---|---|---|
| 14.1 | ONE-ID SSO | **ishlayapti** | o'zgarishsiz | sozlash 0 |
| 14.2 | DWH-DS (`dwh-ds.brb.uz`) | **ishlayapti** (`chakana_ai.py`) | OAuth2 client_credentials, token keshi | BRB o'z mahsulotlari manbai sifatida qo'shilishi mumkin (OD-2) |
| 14.3 | **BRB iABS (read-only)** | yo'q | JDBC/POST — OD-2 qarorigacha aniqlashtirilmaydi | **13 PD** (8 kod + 5 kelishuv/ro'yxatdan o'tish); D-7: alohida ish oqimi, 1-haftada boshlanadi |
| 14.4 | Ichki LLM gateway | yo'q (OD-7) | OpenAI-siz mos OpenAI-ko'rinish API yoki bank standarti; structured output; per-call timeout 30 s; breaker | mijoz ~4 PD; kelishuv noma'lum |
| 14.5 | SMTP relay / SMS gateway | yo'q (OD-9 / BRB-07) | SMTP auth; SMS HTTP API + kvota | 6 PD |
| 14.6 | Sentry / Logstash | ishlayapti | o'zgarishsiz | 0 |

**iABS haqida ogohlantirish (TT burchi):** BT buni "Read-only" deb bir qatorga yozgan. Haqiqatda: tarmoq segmenti ruxsati, hisob yaratish, ma'lumot sinfi kelishuvi, xavfsizlik ro'yxatidan o'tish. Bu 5 PDlik qism **bizning tezligimizga bo'ysunmaydi** — 19-bo'limda kritik yo'lga qo'yilgan sabab shu.

---

## 15. INFRASTRUKTURA, UNUMDORLIK VA SIG‘IM

### 15.1 Joylashtirish
Mavjud k8s kontur (staging: `npl-tahlil-test.brb.uz`), Docker obraz, GitLab CI — qayta ishlatiladi. Yangi komponentlar: worker jarayonlari (bitta image, `MODE=worker`), migratsiyalar startapda (mavjud amaliyot).

### 15.2 Ma'lumot hajmi (taxmin, dizayn uchun — kafolat emas)
34 bank × ~4 offer × 12 parametr ≈ **1 600 parametr qatori** joriy holatda; snapshot kuniga ~2 mahsul sikl × o'zgarishlar ulushi ~5% → yiliga ~50–100 ming snapshot qatori. PostgreSQL 16 buning uchun og'ir emas; `page_versions` (20 daqiqalik sweep × 170 soat/hafta) eng katta jadval — 90 kundan keyin tozalash (7.3).

### 15.3 Unumdorlik byudjeti (M-5)
- `/api/compare/matrix`: snapshot replika `JSONB` + `content_hash` indekslari; og'ir agregatsiya so'rovda emas — sikl oxirida `mv_compare_matrix` materializatsiyalangan ko'rinishga yoziladi, API uni o'qiydi. Yangilanish chastotasi = full refresh sikli.
- Tarix so'rovlari `(offer_id, snapshot_at DESC)` indeksi bilan coverage-index; limit majburiy.
- CI'da performance smoke: seed 50 k snapshot ustida matrix so'rovi P95 bo'sag'asi (800 ms) — sekinlashsa build qizil.

### 15.4 Nega Redis/Celery/Airflow hozircha yo'q (D-6 davomi)
34 manba, kunlik ritm, daqiqiy sweep — bu **kichik** ish yuk. APScheduler (`max_instances=1`, `coalesce`) + Postgres navbat (`SELECT … FOR UPDATE SKIP LOCKED`, `extraction_queue` mavzusi 6-bo'lim rasmlaridagi `extract` vazifasi) bitta konteyner ichida yetarli va operatsion yukni zero saqlaydi. Qayta ko'rib chiqish triggersi (yozib qo'yiladi): kunlik_extraction_run_ > 5 000 yoki worker > 4ta yoki sweep P95 > 10 daqiqa — shundagina alohida broker ko'tariladi. Bu "hech qachon" emas, "hozircha soddalik afzal" qarori.

---

## 16. KUZATUV VA DIAGNOSTIKA

| Signal | Qayerdan | Qayoqqa |
|---|---|---|
| Sikl salomatligi (M-1): oxirgi muvaffaqiyatli sikl, davomiyligi | `extraction_runs` agregat | `/api/health` kengaytmasi + admin panel |
| Manba degeneratsiyasi (8.3): 7 kunlik tapuvchi | `credit_offer_params.method` stat | admin panel + email (gunde) |
| Detection/delivery latency (M-3/M-4) | `change_events` ↔ hash o'zgarish vaqti | dashboard percentil |
| LLM gateway javobsiz / breaker ochiq | `resilience` holati | `/api/meta/sources` uslubidagi snapshot |
| Review queue uzunligi / karantin yoshi | `review` so'rovi | admin panel; > 3 kun bo'lsa qizil |
| Sentry | istisnolar | mavjud |

Qoida: **har bir avtomatik mezon (M-1…M-5) ekransiz qoldirilmasa — mezon emas, tilak.** Barcha M-mezonlari admin panelda son ko'rinishida turadi va qabul akti shu ekranlarning rasmi bilan tasdiqlanadi.

---

## 17. EKSPORT VA HISOBOTLAR (FR-15)

- `GET /api/export/matrix.xlsx` — serverda ochiq generatsiya (openpyxl), jadval + filtr sarlavhasi + "ma'lumot sanasi" tamg'asi va manba holati yorlig'i (`partial` manbalar belgilangan). Sinkron so'rov (jadval hajmi kichik); M-5 byudjeti ichida.
- `GET /api/export/matrix.pdf` — A3 landscape — jadvalning butunligicha chop etiladigan ko'rinishi; generatsiya kutubxonasi bank standarti bo'yicha tanlanadi (print-kanal cheklovi — ochiq qaror emas, AT ichidagi texnik qaror, reliz davomida yopiladi).
- Eksport `audit_log`ga yoziladi (kim, qachon, qaysi firqa bilan).
- Oylik digest: oy ichidagi barcha `change_events` + trendlar — email jobi; shovqindan past o'zgarishlar shu yerga tushadi (10.2.3).

---

## 18. SIFAT, TEST VA QABUL

### 18.1 Test qatlamlari (mavjud 87 fayllik pytest quvishiga qo'shiladi)

| Qatlam | Nima tekshiriladi | Eshik |
|---|---|---|
| Unit | normalizatsiya (9.1 jismoniy hujjatlar: vergul/nuqta, mln/mlrd, "hozrga qadar"), EIR (qo'lda hisoblangan 3 nazorat misoli), diff/dedup, sanity envelope | CI majburiy |
| Property-based | normalizatorga istalgan kirish → tur/binlik buzilmasligi (`hypothesis`) | CI |
| Connector contract | har 34 manba uchun: fixture HTML/PDF → kutilgan kanonik to'plam (nokaut test emas — `partial` ham valid status) | CI, snapshot fixture |
| LLM contract | gateway mock: sxemaga tushmagan javob → reject; iqtibos matnda yo'q → reject | CI |
| Integration | sweep→event→subscription→delivery zincari (test SMTP transport); RBAC matritsasi (har rol × har endpoint) | CI |
| Performance smoke | 15.3 bo'sag'asi | CI |
| Evals (18.2) | etalon to'plam ustida rekkord | alohida skript, reliz oldidan |

`backend/.pytest_cache` holati emas, **CI yashil/yolg'iz** hukm: lokaldagi `.env` imtiyoziga ishonmaymiz (CI muhitida `SECRETS_BACKEND=env` bilan qaytalanadi).

### 18.2 Etalon to'plam (D-2 yechimi — qabul asoslari)

1. **Hajm:** 34 bank × ≥ 2 mahsulot × 12 parametr ≥ **800 belgilangan qiymat**.
2. **Mustaqillik:** 2 belgilovchi (KBD xodimi) alohida belgilaydi; kelishmovchilikni esa uchunchi tomon (KBD rahbari) hal qiladi; **Cohen's Kappa ≥ 0.85** bo'lmasa — lug'at/9.1 qoidalari yozilishi qayta ko'rib chiqiladi (bu aniqlik emas, ta'rif muammosi).
3. **Chorrah:** har parametr bo'yicha alohida aniqlik; agregat vaznlangan (og'irliklar — 24-bo'lim).
4. **Asbob:** `scripts/evaluate_gold.py` — ochiq kod, `gold_annotations` jadvalidan o'qiydi, hisobot Markdown chiqaradi. Qabul aktiga shu hisobot ilova qilinadi.
5. **Muddat:** etalon to'plam I-fazda yig'iladi; **M-2 etalon yo'qligida o'lchangan hisoblanmaydi** (1-bo'lim eslatmasi).

### 18.3 Qabul tartibi
1. Ichki test (biz): barcha CI eshiklar + etalon rekkord hisoboti.
2. Pilot (KBD, 4 hafta): real foydalanish; M-6 so'rovnoma shu oynaning oldidan/keyinidan.
3. Qabul akti: M-1…M-6 ko'rsatkichlarining ekrandan olingan rasmi bilan (16-bo'lim qoidasi); 22-bo'lim cheklovlari aktga ko'chiriladi.

---

## 19. BOSQICHLAR VA KRITIK YO'L

Fazalar **ichki qurish tartibi** (2.3): topshirish bitta, to'liq kontur bilan.

### 19.1 0-qadam (2 hafta, parallel) — qarorlar va ruxsatlar
- OD-1…OD-9 yopilishi (23-bo'lim);
- Yuristik xulosa boshlanadi (BRB-04) va iABS ro'yxatdan o'tish boshlanadi (BRB-05) — **ikkalasi ham kritik yo'lda**, chunki tashqi organlar tezligiga bog'liq;
- `PRICING-COMPARISON-MATRIX` ishlab chiqish boshlanadi (BRB-03);
- Etalon belgilovchilar tayinlanadi (BRB-02);
- Variant A/B yakuniy tasdiq (OD-6).

**0-qadam tugamasa davom fazalari boshlanmaydi** — noto'g'ri mezon ustiga yozilgan kod qayta yoziladi.

### 19.2 Fazalar

| Faza | Tarkib | Chiqish mezoni |
|---|---|---|
| I. Ma'lumot yadrosi | `sources`/kanonik jadvallar migratsiyasi, `seed_sources.py`, L1 konnektorlari 34 manba, sweep (hash) dvigateli | 34 manba `extraction_runs`da ko'rinadi; M-1 dashboard ishlaydi; hash sweep P95 ≤ 45 daqiqa tasdiqlangan |
| II. Ekstraksiya quvuri | L2 LLM mijoz + structured output + iqtibos tekshiruvi, L3 review queue + admin UI, sanity envelope | Etalon rekkord hisoboti birinchi marta chiqadi (maqsad shart emas, o'lchanish shart) |
| III. Taqqoslash | normalizatsiya to'liq, EIR, guruhlash, skoring (matritsa yuklangan), gap-analysis, API `/api/compare/*`, dashboard | M-5 bo'sag'asi o'talgan; har ratingda "negu" izohi |
| IV. Monitoring/alert | `change_events`, dedup, kanallar (ichki/email/SMS), obunalar, digest | M-3/M-4 laboratoriya testida o'lchangan; kanallardan biri ishlamasada ikkinchisi ishlaydi (10.4) |
| V. Qotirish | eksport, i18n to'liq, RBAC siypalash, kuzatuv paneli, xavfsizlik sharhi, pilot | 18.3 qabuliga tayyor holat |

Har faza oxiri: demo + CI yashil + yangi M-ko'rsatkichlar ekranda. Hech bir faza "keyin qo'shamiz" bilan yopilmaydi.

---

## 20. BAHOLAR VA JAMOA

Baho — Variant A uchun, noaniqlik ±25% (0-qadamdan keyin ±15% ga torayadi). PD = kishi-kun (1 foydali kun ≈ 6 soat kod).

| Ish | PD |
|---|---:|
| Migratsiyalar + `sources` + seed | 8 |
| L1 konnektorlar (34 manba, o'rt. 0.6 PD — andoza bor) | 20 |
| Detection sweep + page_versions | 6 |
| L2 LLM quvuri (mijoz, sxema, iqtibos tekshiruvi, kvota) | 15 |
| L3 review queue (API + UI) | 12 |
| Ma'lumot modeli operatsiyalari (snapshot, diff, dedup) | 10 |
| Taqqoslash dvigateli (normalizatsiya, EIR, guruhlash, skoring, gap) | 18 |
| API qatlami | 10 |
| Frontend (5 sahifa + 5 feature + notifications) | 35 |
| Alert kanallari (email/SMS/ichki, kvota, retry) | 12 |
| RBAC + audit | 6 |
| iABS read-only (8 kod + 5 kelishuv) | 13 |
| Eksport (xlsx/pdf/digest) | 8 |
| Kuzatuv paneli + M-mezon displeylari | 6 |
| Testlar (contract fixturelar, evals, perf) | 14 |
| DevOps (worker rejimi, CI, staging) | 6 |
| 0-qadam (qaror, prototip-skrinlar) | 10 |
| **Jami** | **≈ 209 PD** |

Jamoa: 2 backend + 1 frontend + 0.5 DevOps + 0.5 QA + KBD analytigi (etalon/matritsa, doimiy). ≈ 209 PD ÷ 3.0 samarali FTE ≈ **14–15 hafta** (ta'til/kasallik zaxirasi bilan ~4 oy). Variant B boshlang'ich xarajat ≈ 1.8×(1.35/0.75) va 2 ta qo'shimcha operatsion yuk doimiy qoladi.

Cheklov: bahoda **tashqi kutishlar** (yuristik xulosa, iABS hisob, gateway ruxsati) hisobga olinmagan — ular kritik yo'lda turadi va jadvalning haqiqiy tezligi 0-qadamdagi tashqi qaror/ruxsatlar kelish tezligiga bog'liq.

---

## 21. BUYURTMACHI TOPSHIQLARI (bu kelmasa TT bajarilmaydi)

| # | Topshiq | Mas'ul | Muddat | Kechikish oqibati |
|---|---|---|---|---|
| BRB-01 | OD-1…OD-9 qarorlarini yozma berish (23-bo'lim) | KBD + AT departamenti | 0-qadam oxiri | Faza I boshlanmaydi |
| BRB-02 | Etalon to'plam uchun 2 belgilovchi + 1 hakam, ~120 soat ish vaqti | KBD | Faza I davomida | M-2 o'lchansiz qoladi, qabul kechikadi |
| BRB-03 | `PRICING-COMPARISON-MATRIX`ni imzolash (taqqoslash guruhlanishi va og'irliklar) | KBD | Faza III boshiga | FR-06/FR-07 topshirilmaydi (D-3) |
| BRB-04 | Manbalar bo'yicha yuristik xulosa (foydalanish shartlari, robots, avtomatik o'qish ruxsati) | Yurist boshqarmasi | 0-qamadda boshlangan bo'lishi shart | Huquqiy risk bizda qoladi; aktga deklaratsiya |
| BRB-05 | iABS read-only hisob + tarmoq ruxsati + xavfsizlik ro'yxatidan o'tish | AT + iABS egalari | 1-haftada boshlangan bo'lishi shart | OD-2 bo'yicha zahira qarorga o'tiladi |
| BRB-06 | Ichki LLM gateway: berish **yoki** yozma rad (OD-7) | AT departamenti | 0-qadam oxiri | L2 o'chadi; M-2 mezoni qayta yoziladi |
| BRB-07 | SMTP relay va SMS gateway kredensiallari + kvota (OD-9) | AT departamenti | Faza IV boshiga | Faqat tizim ichi kanal — AC "2 kanal" bajarilmaydi |
| BRB-08 | Pilot: 5+ xodim, 4 hafta real foydalanish + M-6 so'rovnomasi | KBD | Faza V | M-6 o'lchanmaydi |

---

## 22. TEXNIK IMKONIYATDAN TASHQARI BANDLAR (imzolashda ochiq yozilishi shart)

1. **AC-07 (12 oylik tarix, 1-bosqichda):** tarix tizim bilan birga tug'iladi, birinchi kundan 12 oy yo'q — bo'lishi ham mumkin emas (tarix yo'q bank sahifasini orqaga qaytarib bo'lmaydi). Qabul: mexanizm ishlaydi; 12 oy to'lgach avtomatik qanoatlanish.
2. **"Har qanday o'zgarishdan 30 daqiqada xabar" (FR-10 to'liq matni):** kafolat faqat tashqi faollik oynasi ichida (07:00–21:00) va detection+delivery ajratilgan holda (D-1). Oyna tashqarisida ochilgan o'zgarish — oyna ochilgani bilan aniqlanadi; buning fizik sababi: biz bank ichki tizimiga ulanmaymiz, faqat ochiq sahifani o'qiymiz.
3. **"Aniqlik < 2% xatolik"ni `text` turidagi parametrda** (maxsus shartlar) so'zma-so'z o'lchab bo'lmaydi: mezon = etalon kalit iboralarning qamrovi (18.2), foiz emas.
4. **Bank anti-bot bilan to'sib qo'ysa** (WAF, JS-challenge): majburan aylanib o'tish qilmaymiz (13.4 siyosati va "haker deb block" xavfi). Bunday manba `blocked` holatiga o'tadi va qo'lda kiritish (review queue) kanali ochiq qoladi — M-1 hisobida bu manbalar maxsus statusda, "yiqilish" emas.
5. **FR-09 generativ tavsiya** ichki LLM gateway'siz imkonsiz va tavsiyaning javobgarligi belgilanmagan — reliz 1 da "kuzatilgan nomuvofiqliklar" ro'yxati bilan almashtiriladi (9.6, OD-8).

---

## 23. OCHIQ QARORLAR (OD) — shu yopilmasa hujjat imzolangan hisoblanmaydi

| # | Savol | Taklif etilgan default (javob bo'lmasa shu kuchga kiradi) | Qaror beruvchi |
|---|---|---|---|
| OD-1 | Taqqoslash mezonlari og'irliklari | teng og'irlik + mediana bilan taqqoslash (kuchsiz default — imzolashga majbur qilish uchun shunday qoldirildi) | KBD |
| OD-2 | BRB o'z mahsulotlari manbai | qo'lda kiritish (admin UI); iABS/DWH avtomatik emas | KBD + AT |
| OD-3 | Segmentlar | 1-bosqich: yuridik shaxslar + KHB; jismoniy shaxslar 2-bosqich | KBD |
| OD-4 | Yuristik xulosa | default yo'q — bu savob emas, shart | Yurist boshqarmasi |
| OD-5 | Korporativ stek standarti Airflow'ni majburlaydimi? | yo'q — APScheduler (D-6) | AT |
| OD-6 | Variant A / B | A (4.4 sharti bilan) | AT + Xavfsizlik |
| OD-7 | Ichki LLM gateway bormi? | yo'q deb olamiz → L2 o'chadi, M-2 qayta yoziladi | AT |
| OD-8 | FR-09 generativ tavsiya kerakmi? | kerak emas (9.4 gap-analysis yetarli) | KBD |
| OD-9 | SMS/Email kanallari | faqat tizim ichi kanal | AT |

Eslatma: defaultlar **majburan noqulay** qilib tanlangan — ularning har biri KBD'ga "bu menga kerakmi?" savolini bir marta pulga tushiradi. Yaxshiroq qaror olishning arzon yo'li shu.

---

## 24. KANONIK PARAMETRLAR LUG'ATI (12 ta — 7.2 `credit_params` to'ldiruvchisi)

| # | code | Nom (UZ) | Tur / birlik | Qat'iy qiymatlar / izoh |
|---|---|---|---|---|
| 1 | `nominal_rate` | Yillik nominal stavka | percent | 0–100; sanity envelope (8.2.4) |
| 2 | `effective_rate` | Effektiv yillik stavka (EIR) | percent | **hisoblanadigan** (9.2), `method='rule'` — hech qachon LLM qo'li bilan kirmaydi |
| 3 | `amount_min` | Minimal summa | money (UZS/USD) | |
| 4 | `amount_max` | Maksimal summa | money | `NULL` = cheklanmagan |
| 5 | `term_min_months` | Minimal muddat | month | |
| 6 | `term_max_months` | Maksimal muddat | month | `NULL` + enum `until_end_of_term` |
| 7 | `down_payment_pct` | Boshlang'ich badalaha | percent | 0–100 |
| 8 | `commission_once` | Bir martalik komissiya | money yoki percent (alohida ustun!) | EIR'ga kiradi |
| 9 | `collateral_type` | Ta'minot turi | enum | `unsecured / real_estate / equipment / vehicles / deposit / guarantee / other` — lug'at qat'iy, LLM boshqa qiymat chiqarsa reject |
| 10 | `grace_period_months` | Imtiyozli davr | month | |
| 11 | `early_repay_penalty` | Muddatidan oldin qaytarish jarimasi | enum | `none / fixed_pct / variable_pct / unknown` |
| 12 | `special_conditions` | Maxsus shartlar | text | qabul meizoni foiz emas — kalit ibora qamrovi (22.3) |

Har qator `raw_quote` (iqtibos), `confidence`, `method` bilan yashaydi (7.2). Lug'at kengayishi faqat yozma o'zgarish so'rovi bilan (2.3).

---

## 25. IMZOLASH TARTIBI

1. TT 23-bo'lim OD-lari yopilgach v1.0ga o'tadi; 21-bo'lim muddatlari kalendargachiziladi.
2. Imzodan keyin yagona o'zgarish yo'li — yozma change request + ta'sir bahosi (jadval/baho/qamrov). Og'zaki kelishuvlar yuridik kuchi ga ega emas (BT'dagi tugallanmangan §2 shundan chiqdi).
3. Ish boshlanish sanasi: **BRB-01 (qarorlar) va BRB-04 (yuristik boshlanish) yozma qayd etilgan kuni**; qolgan BRB-bandlar parallel yuradi, lekin 19.1dagi kritik yo'lni kechiktirmaydi.

*Tayyorladi: Axborot texnologiyalari departamenti. Hujjat ichki foydalanish uchun.*
