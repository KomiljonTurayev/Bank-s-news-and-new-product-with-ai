# Ops so'rovi — npl-tahlil-test (staging) backend 502

Holat: **502 davom etyapti** — oxirgi tekshiruv 2026-10-02 10:59 (+05), uzluvi ~8 kunga cho'zildi.
Frontend podi tirik (`/` → 200, yangi `:staging` imaj), backend Service'da tayyor endpoint yo'q.

**A-5 — eng so'nggi matn.** Kalit Vault yo'liga `SECRETS_BACKEND` sifatida qo'yilgan:
u yerda tursa ishlamaydi (bayroq Vault'dan OLDIN env'dan o'qiladi) — Deployment env'iga kerak.

**Vault tomoni TASDIQLANDI** (`brb_it_department/mono_deployments/ai_npl_tahlil/staging`,
kalitlar `db_url` / `db_username` / `db_password`) — kod kutilayotgan manzil va kalit
nomlari bilan bir xil. Quyida "VAULT MANZILI TASDIQLANDI" bo'limi.

**SABAB ANIQLASHDI (quyidagi "YANGI DALIL" bo'limi):** ops yuborgan konteyner logi —
pod yangi imajda turibdi va import paytida `DATABASE_URL: Field required` bilan yiqilyapti.
Yechim — deployment'ga bitta oddiy belgi: `SECRETS_BACKEND=vault`.

Fayl workspace ildizida (`ops/502-staging.md`), hech bir git repoda kuzatilmaydi — erkin yuborish/muharrirlash mumkin.
Maxfiy qiymatlar yo'q: faqat env KALIT NOMLARI tilga olinadi, qiymat so'ralmaydi.

---

## YANGI DALIL (2026-09-24) — ops yuborgan traceback: sabab aniq, kerak bo'lgani bitta env belgi

Ops konteyner logini yubordi. Ikkita xulosa, ikkalasi ham hujjatli:

**(1) Pod ENDI yangi imajda.** Traceback'dagi satinumerlar `gitlab/staging` HEAD
(`da29435`) bilan bayt-baytga tushadi:
- `/app/config/__init__.py`, line 108 → `return _validate_result(settings_cls())`
- `/app/config/__init__.py`, line 150 → `settings = get_settings()`
- log qatori `SECRETS_BACKEND=None: sozlamalar Vault'dan EMAS, env/.env'dan olindi (PROFILE=staging)`
  — bu bizning ataylab qo'shgan warningimiz (`config/__init__.py:103-107`).

Eski staging'da (`da29435`ning ota-katak `^1` versiyasi) `_validate_result` **umuman yo'q** edi.
Demak restart bo'lgan va imaj yangilangan.

> **To'g'rilangan xabar (2026-09-24).** Bu faylning avvalgi tahririda "eski
> `Vault credential missing: x_role_id` xatosi yo'qoldi, demak AppRole kalitlari env'da bor"
> deb yozilgan edi — **bu xulosa adashgan edi.** `SECRETS_BACKEND` berilmaganda kod Vault'ga
> **umuman bormaydi** (`config/__init__.py:86,103-107`), shuning uchun o'sha xatoning
> ko'rinmasligi kalitlar mavjudligini hech narsa isbotlamaydi. AppRole kalitlari
> (`x_role_id` / `x_secret_id`) hozir Deployment'da barmi-yo'qmi — **noma'lum**, quyidagi
> so'rov shu sababli ham qo'shilgan.

**(2) Yiqilish sababi — `SECRETS_BACKEND` berilmagani.** Bu merge bilan `653fed8` qatori ham
staging'ga tushdi: standart `vault` → **`env`** bo'ldi
(eski: `config/__init__.py:56` — `os.environ.get("SECRETS_BACKEND", "vault")`;
yangi: `:86` — `os.environ.get("SECRETS_BACKEND", "env")`).
Endi `SECRETS_BACKEND` bo'shligi "Vault'ga kirmaslik" degani, shuning uchun:
Vault'ga so'rov ketmaydi (AppRole kaliti bo'lsa ham) → `db_url` / `db_username` / `db_password`
kalitlaridan `DATABASE_URL` yig'ilmaydi → `config/base.py:15` (`DATABASE_URL: str`, defaulti yo'q)
maydoni to'ldirilmaydi → pydantic `ValidationError` → jarayon importda o'ladi → crash-loop →
Service'da tayyor endpoint yo'q → nginx `/api/*` uchun 502.

### Kerakli o'zgarish (bitta qator, maxfiy emas)

```yaml
# npl-tahlil-back Deployment, container env:
- name: SECRETS_BACKEND
  value: "vault"
```

Shunda u `VAULT_KV_MOUNT=brb_it_department`, path `mono_deployments/ai_npl_tahlil/staging`dan
`db_url` / `db_username` / `db_password`ni o'qib `DATABASE_URL`ni o'zi yig'adi — bu uchovlon
Vault UI'da borligi tasdiqlandi. Parol uchun `SECRET_KEY` va ONE-ID / E-IMZO / CHAKANA_AI
kalitlari ham shu yo'lda turadi deb kutamiz; **ular ham shu yo'ldami — hozircha noma'lum**
(bo'lmasa pod ko'tariladi, lekin parol bilan kirish 503 / ONE-ID tugmasi o'chiq bo'ladi).

**Bu bayroq QAYERGA qo'yiladi (2026-09-24 kuzatilgan amaliy xato):** faqat jarayon
muhitiga — k8s Deployment `env`'i, yoki obraz ichidagi `.env`
(`config/__init__.py:10` dagi `load_dotenv()` qaror qabul qilishdan oldin ishlaydi).
**Vault KV'iga kalit qilib qo'ysa ishlamaydi:** `SECRETS_BACKEND` sozlama maydoni emas
(`config/base.py`da bunday maydon yo'q), shuning uchun Vault'dan kelgan bu kalit
`extra="allow"` tufayli jim sig'adiriladi va faqat
`Vault'dagi nomga mos kelmagan kalitlar: SECRETS_BACKEND` ogohlantirishida ko'rinadi.
Chain: bayroq "Vault'ga bormasin" degan holatda qoladi → Vault'ga so'rov ketmaydi →
kalitning o'zi ham o'qilmaydi.

**Muqobil (Vault'siz):** `DATABASE_URL`ni to'g'ridan-to'g'ri env'ga qo'ysa pod ko'tariladi
(qolgan barcha maydonlarda default bor), lekin `SECRET_KEY`, `ONEID_*`, `EIMZO_*` kalitlari ham
env'da kelmasa: parol bilan kirish 503, ONE-ID tugmasi `{"configured":false}` bo'lib qoladi
(fail-closed). Shuning uchun **`SECRETS_BACKEND=vault` tavsiya qilinadi.**

**Keyingi kutilayotgan xato (oldindan aytib qo'yamiz):** `SECRETS_BACKEND=vault`dan keyin
`Failed to read secret at brb_it_department/...` chiqsa — o'sha mount KV **v1**, bizning mijoz
esa KV v2 API bilan o'qiydi (`config/vault.py:68` → `read_secret_version`). Unda mount'ni v2
qilish yoki muqobil yo'lga o'tish kerak.

**Eslatma:** standartni qaytadan `vault` qilishni taklif qilmaymiz — aynan shu standart
AppRole kaliti yo'q holatda podni birorta so'rov qabul qilmasdan o'ldirardi; kalitlar endi
borligi uchun aniq belgi (`=vault`) yetarli.

**Bizning ulushimiz (ochiq aytganda):** `SECRETS_BACKEND` standartini `vault`dan `env`ga
biz o'zgartirgandik (`653fed8`, MR !12 tarkibida). Eski standart qolganda, hozirgi
deployment (AppRole kalitlari env'da mavjud) o'z-o'zidan Vault'ga borib ko'tarilardi.
Shuning uchun agar Deployment'ga tegish qulay bo'lmasa, biz tomondan ham yechim bor —
keyingi `:staging` imajda standartni qaytarish. Lekin bu kalitlar yo'q holatdagi
crash-loop xavfini qayta tiriltiradi, shu sababli avval bitta `SECRETS_BACKEND=vault`
qatorini so'raymiz.

---

## VAULT MANZILI TASDIQLANDI (2026-09-24) — nomlar bo'yicha kelishuv yo'q, faqat bitta belgi yetishmayapti

Vault UI'dan ko'rsatilgan to'liq manzil va kalit nomlari:

```
brb_it_department/mono_deployments/ai_npl_tahlil/staging
  db_password
  db_url
  db_username
```

Kod kutayotgan narsa bilan **bayt-baytga bir xil** — ya'ni bizda hech qanday
konfiguratsiya/no'm nom kesishuvi yo'q:

| bizning kod | kutilayotgan qiymat | vault UI'da |
|---|---|---|
| `config/base.py:6` `VAULT_KV_MOUNT` (default) | `brb_it_department` | mos |
| `config/staging.py` `vault_kv_path` (default) | `mono_deployments/ai_npl_tahlil/staging` | mos |
| `config/__init__.py:37` `_DB_KEYS` | `db_url`, `db_username`, `db_password` | mos (uchovlon bor) |

Uchovlon bitta SQLAlchemy URL'ga kodning o'zida yig'iladi
(`config/__init__.py:40-64`): `db_url`da scheme bo'lmasa `postgresql+psycopg://user:pass@<db_url>`
qilinadi, `db_url`da user:pass ko'milgan bo'lsa o'sha ishlatiladi, paroldagi `@ + space`
percent-encode qilinadi. `DATABASE_URL` kaliti Vault'da **kerak emas**.

**Shu sabab sabab nomlarda emas — `SECRETS_BACKEND` belgisi berilmaganida.** Vault ma'lumotlari
joyida, pod ularga kira olmayapti.

### Qolgan ikkita noaniq (shularni aytsangiz ish tugaydi)

1. **AppRole kalitlar Deployment env'ida barmi?** Kod faqat **env'ni** o'qiydi:
   `x_role_id` va `x_secret_id` (nomni katta-kichikligiga befarq, `config/vault.py:11-29`).
   Fayl ko'rinishidagi variantimiz **yo'q** — secret'ni `valueFrom/secretKeyRef` bilan
   **env nomi `x_role_id`/`x_secret_id` bo'lib** berilsa ham to'g'ri ishlaydi.
   Yo'q bo'lsa: `Vault credential missing: set x_role_id` xatosi chiqadi (bu holda biz
   AppRole'ni so'raymiz).
2. **`brb_it_department` mount'i KV v2mi?** Kod `kv.v2.read_secret_version` bilan o'qiydi va
   javobdan `data.data`ni oladi (`config/vault.py:71-75`). Mount `kv` (v1) bo'lsa
   `Failed to read secret at 'brb_it_department/mono_deployments/ai_npl_tahlil/staging'` chiqadi.
   Bilishning eng oson yo'li: Vault UI'da Secrets engine ro'yxatidagi **Type** ustuni
   (`kv-v2` yoki `kv`), yoki secret sahifasining manzilida `/data/` qismi bormi.
   **Agar v1 chiqsa — yechim biz tomonda, lekin hali yozilmagan** (avval v2 urinishi,
   bo'lmasa v1'ga tushish); u holda logni tashlashiz yetadi, tuzatishni biz yozib
   keyingi `:staging` imajni chiqaramiz. Shoshilsa tezroq yo'l — env'ga
   `DATABASE_URL` berish, u holda Vault'ga umuman borilmaydi.

---

## Variant A-5 — Telegram uchun (2026-09-24 10:12, **eng yangi**) — SECRETS_BACKEND qayerga qo'yilishi kerakligi haqida

Kontekst (biz tomonda): kalit `SECRETS_BACKEND` Vault yo'liga qo'yilgani aytildi.
Kodda tekshirildi — **u yerda tursa ishlamaydi**, chunki "Vault'ga boramizmi-yo'qmi"
qarorining o'sha bayrog'idan olinadi va bayroq Vault'dan oldin o'qiladi.

```
Rahmat! Bitta joyini tuzatish kerak — SECRETS_BACKEND ni Vault'dagi kalit sifatida
qo'yish ishlamaydi (db_url/db_username/db_password esa joyida, ularni tegmang).

Sabab (kodda): bu bayroq jarayon muhitidan o'qiladi va Vault'ga borish-ketmaslik
shundan keyin qaror qilinadi — Vault'dagi SECRETS_BACKEND kalitigacha kod yetib
bormaydi. Config'da bunday maydon yo'qligi uchun u jim-jit e'tiborsiz qoladi,
faqat logda ogohlantirishda ko'rinadi:
  "Vault'dagi nomga mos kelmagan kalitlar: SECRETS_BACKEND"

Kerakli joy — Deployment env'ining o'zi:
  kubectl -n monolith-service edit deploy npl-tahlil-back
    spec.template.spec.containers[0].env:
    - name: SECRETS_BACKEND
      value: "vault"

Shu bilan birga env'da AppRole kalitlari ham bo'lishi shart (nomlari aynan
x_role_id va x_secret_id). Secret'ni secretKeyRef orqali bersangiz ham bo'ladi,
faqat ENV NOMI shu bo'lsin — kod fayl o'qimaydi.

Ayni paytda (10:16 +05) pod hali ko'tarilmagan, ya'ni bayroq pod muhitiga tushmagan:
  /                       → 200
  /api/health             → 502 {"error":"api_upstream_unreachable","request_id":"e4a33a35ab8e3e9d6765f9f07a1a11e4"}
  /api/auth/oneid/params  → 502 (request_id a74b6885e7b369396ed5904a84770c79)
  /portfolio/             → 503 (bu bizning nginx ataylab qaytaradi — front tirik)

Env qo'yilgandan keyin shu ikkisini tashlasangiz keyingi qadamni bir zumda aytamiz:
  kubectl -n monolith-service logs deploy/npl-tahlil-back --tail=60
  (pod ko'tarilmasa yana:  ... logs deploy/npl-tahlil-back --previous --tail=60)
  kubectl -n monolith-service get deploy npl-tahlil-back -o jsonpath='{.spec.template.spec.containers[0].env[*].name}'
  (faqat env KALIT NOMLARI, qiymatlar kerak emas)

Logda uch xatodan biri chiqsa — har biriga javobimiz tayyor:
  1) "SECRETS_BACKEND=None: sozlamalar Vault'dan EMAS..." → env tushmagan/restart bo'lmagan
  2) "Vault credential missing: set x_role_id"            → AppRole kalitlari env'da yo'q
  3) "Failed to read secret at 'brb_it_department/mono_deployments/ai_npl_tahlil/staging'"
     → o'sha mount KV v1 bo'lishi ehtimoli katta: bizning kod hozircha kalitlarni
       faqat KV v2 API bilan o'qiydi. Bunda ikki yo'l bor —
       (a) eng tez: env'ga DATABASE_URL ni to'g'ridan-to'g'ri berish (u holda
           SECRETS_BACKEND ni "env" qoldirsa ham pod ko'tariladi; biroq SECRET_KEY,
           ONEID_* va qolgan kalitlar ham env'da bo'lishi kerak — Vault aylanib
           o'tilgan bo'ladi);
       (b) toza yo'l: mount KV v2 bo'lsa 1 qatorlik tuzatish ham kerak emas,
           v1 bo'lsa biz v1'ni ham o'qiy oladigan tuzatishni yozib yangi
           :staging imajni chiqaramiz (bu biz tomonda ish, sizdan kerak emas).
       Shuning uchun bitta savol: o'sha mount Type'yi kv-v2 mi, kv mi?
```

**Eski variantlar (A-4 va oldinroqlari) — o'qilmasdan o'tilsa ham mayli, A-5 ni yuboring.**

---

## Variant A-4 — Telegram uchun (2026-09-24 10:10, **ESKIDI — A-5 ni yuboring**) — SECRETS_BACKEND=vault qo'yilgandan keyingi so'rov

```
Rahmat! SECRETS_BACKEND=vault qiymati to'g'ri — kodda istalgan qiymat "env/local/dotenv"
bo'lmasa Vault rejimini yoqadi, katta-kichik harf farqi yo'q.

Ammo pod hali ko'tarilmagan (10:10 +05):
  /                        → 200
  /api/health              → 502 {"error":"api_upstream_unreachable","request_id":"de6417939e1f0dd7456010bac46e0c7d"}
  /api/auth/oneid/params   → 502 (request_id 4857ef77d2d6a93ece00847317b6bf11)

Endi bizga kerak bo'lgani — FQAT YANGI POD LOGINI (boshqa hech narsa so'ramaymiz):
  kubectl -n monolith-service logs deploy/npl-tahlil-back --tail=60
  (agar pod umumen ko'tarilmasa: --previous qo'shib ham bir marta)

Logda qaysat chiqishini oldindan aytamiz — uchtasidan biri bo'lsa, o'sha yechiladigan narsa:
  1) "SECRETS_BACKEND=None: sozlamalar Vault'dan EMAS..."
     → env podga tushmagan (restart/apply bo'lmagan yoki boshka konteynerga qo'yilgan).
  2) "Vault credential missing: set x_role_id"
     → AppRole kalitlari env'da yo'q. Env nomlari aynan x_role_id va x_secret_id
       (secretKeyRef bo'lsa ham mayli, faqat env nomi shu bo'lsin — fayl o'qish yo'q).
  3) "Failed to read secret at 'brb_it_department/mono_deployments/ai_npl_tahlil/staging'"
     → brb_it_department mount'i KV v1. Unda biz tomonda tuzatish bor, sizda hech
       narsa o'zgartirish shart emas — logni tashlang, keyingi imajda v1'ni ham
       o'qiydigan qilib tuzatamiz.

Agar logda parol/token ko'rinsa — qo'lda o'chirib yuborsangiz bo'ladi, qiymatlar
kerak emas, bizga xato matni va python traceback'i yetadi.

Vaqtni tejash uchun bitta qo'shimcha: shu ikkisini birga bersangiz keyingi qadamni
bir zumda aytamiz:
  kubectl -n monolith-service get pods -l app=npl-tahlil-back -o wide
  kubectl -n monolith-service get deploy npl-tahlil-back -o jsonpath='{.spec.template.spec.containers[0].env[*].name}'
  (faqat env KALIT NOMLARI, qiymatlar EMAS)
```

---

## Variant A-3 — Telegram uchun (2026-09-24 09:58, **ESKIDI — A-4 ni yuboring**)

```
Salom! Log uchun rahmat, sabab aniq: SECRETS_BACKEND belgisi berilmagani uchun pod
Vault'ga umuman kirmayapti (logda "SECRETS_BACKEND=None ... env/.env'dan olindi"),
shu bois DATABASE_URL yig'ilmaydi va importda "DATABASE_URL: Field required" bilan
yiqiladi → crash-loop → nginx 502.

Vault tomoni to'g'ri ekanini tekshirdik — kod ham aynan shu manzilni kutadi:
  brb_it_department/mono_deployments/ai_npl_tahlil/staging
  kalitlar: db_url, db_username, db_password  (DATABASE_URL EMAS)
Ya'ni Vault'da hech narsa o'zgartirish shart emas.

Iltimos, Deployment'ga shu ikki/uchta env qatorini qo'shing (qiymatlarni so'ramaymiz):
  SECRETS_BACKEND = vault
  x_role_id, x_secret_id  — AppRole kalitlari, env nomi aynan shunday
                            (secret'ni secretKeyRef orqali bersangiz ham bo'ladi,
                            faqat env nomi shu bo'lsin; fayl ko'rinishini kod o'qimaydi)

Muqobil: DATABASE_URL ni to'g'ridan-to'g'ri env'ga qo'ysangiz ham pod ko'tariladi,
lekin u holda SECRET_KEY va ONEID_*/EIMZO_* kalitlari ham env'da kelishi kerak
(bo'lmasa parol bilan kirish 503, ONE-ID tugmasi o'chiq bo'ladi).

Bitta savol: brb_it_department mount'i KV v2mi (Vault UI'da Type ustuni kv-v2)?
Kod v2 API bilan o'qiydi. Agar kv (v1) bo'lsa "Failed to read secret at
brb_it_department/..." xatosi chiqadi — unda biz tomonda tuzatish bor, sizdan
hech narsa so'ramaymiz, shunchaki logni qayta tashlang.

Ayni paytda (09:58 +05): / 200 · /api/health 502 (request_id 4667d05c2e4c16fd4ea8052e410495b0)
· /api/auth/oneid/params 502 · /portfolio/ 503. Backend ~32 soatdir 502.
```

---

## Variant A-2 — Telegram uchun (2026-09-24, **ESKIDI — A-3 ni yuboring**)
```
Salom! Logni yuborganingiz uchun rahmat — sabab aniq chiqdi.

Pod yangi imajda turibdi (traceback satrilari gitlab/staging da29435 bilan bir xil).
(Eskirgan jumla: bu yerda "AppRole kalitlari ham env'da bor" deyilgan edi — bu
tasdiqlanmagan taxmin edi, A-3 dagidek so'raladi.)
Lekin SECRETS_BACKEND belgisi berilmagani uchun
Vault'ga umuman kirmayapti ("SECRETS_BACKEND=None ... env/.env'dan olindi"),
shu bois DATABASE_URL yig'ilmaydi va importda "DATABASE_URL Field required" bilan
yiqiladi → crash-loop → nginx 502.

Kerak bo'lgani bitta qator (maxfiy emas):
  npl-tahlil-back Deployment env'iga:  SECRETS_BACKEND=vault

Shunda kod o'zi Vault'dan (brb_it_department / mono_deployments/ai_npl_tahlil/staging)
db_url + db_username + db_password ni o'qib DATABASE_URL yig'adi.

Agar shundan keyin "Failed to read secret at brb_it_department/..." chiqsa — u mount
KV v1, bizning kod esa v2 bilan o'qiydi; unda yozib turgan logni qayta tashlasangiz,
keyingi qadamni aytamiz.

Ayni paytda (09:52 +05): / 200, /api/health 502
(request_id c7ccf5478edbea6c13add5f28aaa2fa7).
```

---

## Variant A — Telegram uchun (qisqa, copy-paste) — **ESKIDI: pod allaqachon yangilangan**

```
Salom! npl-tahlil-test.brb.uz'da backend podi ko'tarilmayapti — frontend ishlaydi,
barcha /api/* so'rovlariga nginx "api_upstream_unreachable" (502) qaytaryapti.
Endi ~31 soat shu holatda (oxirgi tekshiruv 2026-09-24 09:16 +05).

Imaj esa tayyor va yangi:
  registry.brb.uz/brb-it-department/mono-deployments/ai-npl-tahlil/npl-tahlil-back:staging
  tag yaratilgan vaqti 2026-09-23 17:38:52 (+05), pipeline #41681, commit da29435 (test+build success).
Ya'ni muammo imajda emas — pod eskicha yoki crash-loop.

Biror action so'ramayapmiz, avval shu 3 ta narsani ko'rsangiz yetadi:
1) kubectl -n monolith-service get pods -l app=npl-tahlil-back -o wide
2) kubectl -n monolith-service get deploy npl-tahlil-back -o wide
   (image qatorida tag/digest qaysi — :staging yoki eski digest pinnedmi, imagePullPolicy nimami)
3) kubectl -n monolith-service logs deploy/npl-tahlil-back --previous --tail=100

Taxminimiz: start-up'da configuration fail bo'lyapti. Staging config'da DATABASE_URL
majburiy maydon, imajda esa .env yo'q. Ikkala holat ham podni yiqitadi:
 - SECRETS_BACKEND=vault qo'yilgan, lekin AppRole kalislari (x_role_id / x_secret_id) yo'q —
   "Vault credential missing: x_role_id";
 - SECRETS_BACKEND umuman qo'yilmagan — yangi standart "env", ya'ni Vault'ga umuman
   bormaydi, DATABASE_URL bo'lmasa "field required" bilan yiqiladi.
Shu bois deployment'dagi env KALIT NOMLARINI ham ko'rsatsangiz (qiymatlar kerak emas,
so'ramaymiz):
   kubectl -n monolith-service get deploy npl-tahlil-back -o jsonpath='{.spec.template.spec.containers[0].env[*].name}'

Vault yo'li kerak bo'lsa — yana bitta savol: brb_it_department mount'i KV v2mi?
Kod v2 API'si bilan o'qiydi, v1 bo'lsa "Failed to read secret at ..." beradi.

Vaqti kelgan so'rov — ONEID_AUTHORIZE_URL qiymati (maxfiy emas, bu faqat manzil).
Bu kalit bo'sh bo'lsa pod ko'tarilganda ham ONE-ID kirishi o'chiq turadi:
  /api/auth/oneid/params → {"configured":false},  POST /api/auth/oneid → 503.
Issuer https://id.brb.uz, lekin kirish oynasi (authorize) boshqa hostda bo'lishi
mumkin — eski frontend sozlamasida id-login.brb.uz tegilgan edi, bu tasdiqlanmagan
taxmin. Bank IT'dan avval shu manzilni, keyin shu hostda /login qaytish manzilimiz
ro'yxatga olinganini aytib bersangiz yaxshi bo'lardi.

Biz tomondan toza: nginx/envsubst ishlayapti (/portfolio/ ataylab 503 qaytaryapti),
frontend :staging imaji yangi va / 200 qaytaryapti, test+build+secret-scan yashil.
```

---

## Variant B — to'liq xat / ticket

```
Mavzu: npl-tahlil-test (staging) — backend podi 502; imaj registry'da tayyor, restart kerak

1. BELGI (biz tomondan, takrorlanadigan)
   GET https://npl-tahlil-test.brb.uz/                         → 200 (frontend yangi imaj: index-iyUNKahW.js)
   GET https://npl-tahlil-test.brb.uz/api/health                → 502 {"error":"api_upstream_unreachable","request_id":"9989599b7fc7c67118c3d4e1248aacc0"}
   GET https://npl-tahlil-test.brb.uz/api/auth/oneid/params     → 502 {"error":"api_upstream_unreachable","request_id":"46389a694d5aa409e820d06b4176bbb9"}
   GET https://npl-tahlil-test.brb.uz/portfolio/                → 503 {"error":"portfolio_app_not_configured",...}
   17:53:02–17:54:22 (+05) oralig'ida 5 marta /api/health — 502; 17:36–17:51 oralig'ida ham 502;
   18:02 (+05) qayta tekshirildi — / 200, /api/health 502, /api/auth/oneid/params 502, /portfolio/ 503.
   2026-09-24 09:16 (+05) — hammasi o'sha holicha: /api/health 502
     {"error":"api_upstream_unreachable","request_id":"907b5a66466426c9330beef9655d80b4"},
     /api/auth/oneid/params 502 (request_id 3e1ed176341ee5f326b8fefdabc971e0), / 200, /portfolio/ 503.

   502 bizning nginx shablonimizdan chiqyapti (location @api_down) — ya'ni front podi
   tirik, envsubst/resolv.conf to'g'ri (/portfolio/ 503 shuni isbotlaydi),
   lekin http://npl-tahlil-back.monolith-service.svc.cluster.local:8000 da tayyor
   endpoint yo'q. Frontend nginx konfigi bilan ish yo'q.

2. NIJAT QILINMAGAN FAKT — IMAJ ESKI EMAS
   repository : registry.brb.uz/brb-it-department/mono-deployments/ai-npl-tahlil/npl-tahlil-back
   tag :staging yaratilgan: 2026-09-23 17:38:52 (+05)
   pipeline #41681 (commit da29435, dev->staging MR !12): test=success, build=success.
   Ushbu imajda so'nggi auth+secrets ishlari ham bor: start-up'da Vault majburiy EMAS,
   standart SECRETS_BACKEND=env.

3. KERAKLI MA'LUMOT (faqat ko'rish, o'zgartirish so'ramaymiz)
   a) kubectl -n monolith-service get pods -l app=npl-tahlil-back -o wide
      (READY / RESTARTS / STATUS — CrashLoopBackOff yoki ImagePullBackOffmi)
   b) kubectl -n monolith-service get deploy npl-tahlil-back \
        -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}{.spec.template.spec.containers[0].imagePullPolicy}{"\n"}'
      — Agar oldin tortilgan :staging'ga pinlangan bo'lsa va imagePullPolicy=IfNotPresent
      bo'lsa, yangi :staging tag podga tushmaydi. Bunday holda imajni to'g'ridan-to'g'ri
      digest bo'yicha qo'yishni so'raymiz (digestni registry'dan aytib beramiz).
   c) kubectl -n monolith-service logs -l app=npl-tahlil-back --previous --tail=100
   d) Deployment env KALIT NOMLARI (qiymatlar EMAS, bizda maxfiy saqlanadi):
      kubectl -n monolith-service get deploy npl-tahlil-back \
        -o jsonpath='{.spec.template.spec.containers[0].env[*].name}'
   e) ONEID_AUTHORIZE_URL — authorization so'rovi yuboriladigan manzil (maxfiy
      emas, shuning uchun qiymatini so'raymiz). Kalit bo'shligicha qolsa pod
      ko'tariladi, lekin ONE-ID kirishi o'chiq qoladi (fail-closed):
        GET  /api/auth/oneid/params → {"configured":false}
        POST /api/auth/oneid        → 503
      Issuer: https://id.brb.uz. Authorize hosti issuer bilan bir xil bo'lishi
      shart emas (eski frontend sozlamasida id-login.brb.uz tegilgan edi — bu
      taxmin, Bank IT tasdiqlamagan). Birga: scope ro'yxati va /login qaytish
      manzilimiz shu hostda ro'yxatdan o'tganmi.

4. TAXMIN VA IKKITA YECHIM SHIGI  — 2026-09-24: log kelgani uchun tanlov aniq: **(b)**,
       ya'ni `SECRETS_BACKEND=vault` (yuqoridagi "YANGI DALIL" bo'limiga qarang; bu band
       tarix uchun qoldirildi).
   a) "Vault'ga bormasin" rejimi:
      SECRETS_BACKEND=env  +  DATABASE_URL (+ SECRET_KEY va boshqa kalitlar) env/secret orqali
   b) "Vault" rejimi (TAVSIYA ETILADI):
      SECRETS_BACKEND=vault + VAULT_ADDR (default https://vault-staging.brb.uz) +
      AppRole kalitlari ENV NOMI `x_role_id` va `x_secret_id` bo'lib
      (value yoki secretKeyRef — farqi yo'q; FAYL yo'li orqali bermang, kodda
      fayl o'qish yo'q: config/vault.py:11-29).
      KV mount/path bizda default sozlangan: brb_it_department +
      mono_deployments/ai_npl_tahlil/staging — qayta berish shart emas.
      Bu holda KV dvigatel v2 ekanini tasdiqlashingiz kerak — kod read_secret_version
      (v2-only) bilan o'qiydi, config/vault.py:71.
      KV kalitlari: db_url / db_username / db_password (uchovlon), DATABASE_URL EMAS.
      Uchovlon Vault UI'da borligi 2026-09-24'da tasdiqlendi.
   Hozirgi imaj ham shu ikkisidan birini kutadi; pod ko'tarilmasa /api/* 502 bo'lib qoladi.

5. BIZ TOMONDAN
   Test to'plami, build va secret-skan yashil (pipeline #41681). Qizil joblar — security:image
   (Trivy HIGH: jaraco.context 5.3.0 va wheel 0.45.1) va sonar:quality (Sonar token ruxsatsiz)
   — podga aloqador emas, imaj build bo'lgan.

6. TEKSHIRUV (restartdan keyin)
   curl -sS -o /dev/null -w '%{http_code}\n' https://npl-tahlil-test.brb.uz/api/health      → 200
   curl -sS https://npl-tahlil-test.brb.uz/api/auth/oneid/params → {"configured":...} JSON'i
   Shundan keyin ONE-ID kirishining to'liq siklini biz testdan o'tkazamiz.
   E'tibor: /api/auth/oneid/params JSON bo'lib keldi-yu ichida "configured":false
   bo'lsa — pod ko'tarilgan, xatto 502 emas; shunchaki ONEID_AUTHORIZE_URL /
   ONEID_CLIENT_ID / ONEID_CLIENT_SECRET kalitlaridan biri yo'q. Bu alohida
   konfiguratsiya masalasi (3-band "e"), qayta restart talab qilmaydi.
```

---

## Biz allaqachon istisno qilgan narsalar (qayta tekshirmaslik uchun)

| gumon | nega emas |
|---|---|
| frontend nginx/xatolik | `/` 200 va `/portfolio/` ataylab 503 qaytaryapti → envsubst va konfig ishlayapti |
| eski imaj / noto'g'ri tagning tortilgani | Ikkita dalil: (a) `:staging` tag 2026-09-23 17:38:52'da build bo'lgan (pipeline #41681); (b) ops yuborgan traceback satrilari `gitlab/staging` = `da29435` bilan bayt-baytga tushadi — eski imajda `_validate_result` yo'q edi |
| bizning dev→staging mergemiz pas qo'yib yubordi | `/api/health` mergedan (~15 soat) oldin ham 502 edi; sabab import paytidagi konfiguratsiya xatosi |
| kod testi qizil | test + secret-scan yashil; qizillari Trivy/token |

## Bizda yo'q bo'lgan lever

Bu mashinada `kubectl`/`helm`/`docker` yo'q va CI'da deploy job yo'q (deploy — faqat ops
tomonidagi GitLab push-hook orqali). Shuning uchun so'rov "ko'rsating" shaklida, action so'rovisiz.

## Kuzatuv yangilanishi — bitta qatorli xabar

```
2026-09-24 09:16 (+05) — qayta tekshirdik: /api/health 502, /api/auth/oneid/params 502 (/ 200, /portfolio/ 503).
Backend podi hali ko'tarilmagan; imaj registry'da tayyor turibdi (#41681, commit da29435, 23.09 17:38:52).
Endi ~31 soat shu holatda. Tunda hech qanday yangi commit/yangi image bo'lmagan (gitlab/staging = da29435).
```

**Oldingi qator (tarix uchun):** 18:02 (+05) — `/api/health` 502, `/api/auth/oneid/params` 502, pod ko'tarilmagan.

```
2026-09-24 09:52 (+05) — ops log yubordi: pod yangi imajda (da29435), lekin hali ham crash-loop.
Sabab: SECRETS_BACKEND berilmagan → yangi standart "env" → Vault o'qilmaydi →
"DATABASE_URL: Field required" (config/base.py:15). So'rov bir qatorga qisqardi:
deployment'ga SECRETS_BACKEND=vault. Tekshiruv: / 200 · /api/health 502
(request_id c7ccf5478edbea6c13add5f28aaa2fa7) · /api/auth/oneid/params 502.
```

```
2026-09-24 09:58 (+05) — qayta tekshirildi: / 200 · /api/health 502 (request_id
4667d05c2e4c16fd4ea8052e410495b0) · /api/auth/oneid/params 502 · /portfolio/ 503.
Vault tomoni tasdiqlandi: brb_it_department/mono_deployments/ai_npl_tahlil/staging
ichida db_url + db_username + db_password bor — kod kutayotgan manzil/nomlar bilan
bir xil. Demak Vault'da ish yo'q; kerak bo'lgani env: SECRETS_BACKEND=vault
(+ x_role_id / x_secret_id borligini tekshirish) va bitta savol: mount KV v2mi?
```

```
2026-10-02 10:59 (+05) — E-IMZO o'chirish merge bo'ldi (MR !24, merge sha 9f7f2014).
Staging push-pipeline #44094 YASHIL: test + build + secret-scan + security:image + security:python.
Ya'ni yangi :staging imaj registry'da tayyor (repositoriya: npl-tahlil-back, tag staging).
SHUNGA QARAMASDAN jonli tekshiruv (10:47–10:59 +05, 8 daqiqalik polling):
  POST /api/auth/eimzo  → 502 application/json (nginx xatolik sahifasi)
  GET  /api/health      → 502
Pod hali ko'tarilmagan — sabab 09-24dagidek: Deployment env'ida SECRETS_BACKEND belgisi
(hozir ham qo'yilmagan, yoki qo'yilgan bo'lsa-u boshqa sabab — logni ko'rmaymiz).
Biz tomonda qiladigan hech narsa qolmadi: kod, test (675 passed), skan, imaj — hammasi tayyor.
Iltimos: (1) deploy env'da SECRETS_BACKEND=vault + x_role_id/x_secret_id borligini tekshirib,
restart bering; (2) pod holati va logini (tail=60, qiymatlar emas, xato matni yetadi).
```

### Taymlayn (+05)

| vaqt | natija |
|---|---|
| 2026-09-24 10:16 | `/` 200 · `/api/health` 502 (request_id `e4a33a35ab8e3e9d6765f9f07a1a11e4`) · `/api/auth/oneid/params` 502 (request_id `a74b6885e7b369396ed5904a84770c79`) · `/portfolio/` 503 — pod hali ko'tarilmagan |
| 2026-09-24 10:12 | `/` 200 · `/api/health` 502 (request_id `6748b3e9679f75fbbc107be7b57aef5d`) · `/api/auth/oneid/params` 502 (request_id `1135a93417a5346f153c252b344ed6a0`) · `/portfolio/` 503 — pod hali ko'tarilmagan |
| 2026-09-24 ~10:05 | **`SECRETS_BACKEND=vault` Vault yo'liga kalit qilib qo'yilgan** — kodda tekshirildi: u yerda o'qilmaydi (bayroq Vault'dan oldin env'dan o'tadi), Deployment env'iga ko'chirish kerak (A-5) |
| 2026-09-24 09:58 | `/` 200 · `/api/health` 502 (request_id `4667d05c2e4c16fd4ea8052e410495b0`) · `/api/auth/oneid/params` 502 · `/portfolio/` 503 — pod hali ko'tarilmagan |
| 2026-09-24 09:55 atrofi | **Vault UI'dan manzil va kalit nomlari keldi** → `brb_it_department/mono_deployments/ai_npl_tahlil/staging` + `db_url`/`db_username`/`db_password` — kod kutayotgan bilan bir xil (nom kesishuvi yo'q, yuqoridagi tasdiq bo'limi) |
| 2026-09-24 09:40 atrofi | **ops konteyner logini yubordi** → sabab: `DATABASE_URL Field required`, `SECRETS_BACKEND=None` (yuxoridagi "YANGI DALIL") |
| 2026-09-24 09:52 | `/` 200 · `/api/health` 502 (request_id `c7ccf5478edbea6c13add5f28aaa2fa7`) · `/api/auth/oneid/params` 502 — pod hali ko'tarilmagan |
| MR !11 ochilganidan beri | `/api/health` 502 (≥15 soat; bizning dev→staging mergemizdan oldin ham) |
| 17:36–17:51 | 502 |
| 17:53:02–17:54:22 | 5 marta /api/health — hammasi 502 |
| 18:02 | `/` 200 · `/api/health` 502 · `/api/auth/oneid/params` 502 · `/portfolio/` 503 |
| 18:07 | `/` 200 · `/api/health` 502 |
| 2026-09-24 09:16 | `/` 200 (bundling o'sha: `index-iyUNKahW.js`) · `/api/health` 502 · `/api/auth/oneid/params` 502 · `/portfolio/` 503 — tunda yangi commit yo'q |

## Berilgan log — ops'ga qayta yuborish uchun (bizga 2026-09-24 09:40 da kelgan matn)

Kelgan matnni o'zgarishsiz qayta yuborish mumkin; `x_role_id` qiymatini qo'lda
to'sib qo'yishni unutmaslik kerak (biz_artefaktlarda maxfiy qiymat saqlamaymiz),
bizga qiymat emas, xato matni kerak.

```
SECRETS_BACKEND=None: sozlamalar Vault'dan EMAS, env/.env'dan olindi (PROFILE=staging)
Traceback (most recent call last):
  File "/app/main.py", line 9, in <module>
    from app.api import app
  File "/app/app/api.py", line 9, in <module>
    from app.config import FRONTEND_ORIGINS
  File "/app/app/config.py", line 6, in <module>
    from config import settings
  File "/app/config/__init__.py", line 150, in <module>
    settings = get_settings()
               ^^^^^^^^^^^^^^
  File "/app/config/__init__.py", line 108, in get_settings
    return _validate_result(settings_cls())
                            ^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/pydantic_settings/main.py", line 262, in __init__
    super().__init__(**__pydantic_self__.__class__._settings_build_values(sources, init_kwargs))
  File "/usr/local/lib/python3.11/site-packages/pydantic/main.py", line 263, in __init__
    validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
pydantic_core._pydantic_core.ValidationError: 1 validation error for StagingSettings
DATABASE_URL
  Field required [type=missing, input_value={'x_role_id': '<_TO'SIB_QO'YILGAN>', 'profile': 'staging'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
```

Bu log nimani anglatadi (qisqa):
- `SECRETS_BACKEND=None` → pod bayroqni ko'rmayapti → Vault'ga umuman borilmayapti;
- shu bois `db_url`/`db_username`/`db_password`dan `DATABASE_URL` yig'ilmaydi;
- `base.py:15`da bu maydon majburiy (defaulti yo'q) → importda `ValidationError`
  → crash-loop → Service'da ready endpoint yo'q → nginx `/api/*` uchun 502.
- Satrinumerlar (`:108`, `:150`) `gitlab/staging` HEAD `da29435` bilan bayt-baytga
  tushadi → imaj yangi, muammo imajda emas, env'da.
- `x_role_id` env'da ko'rsatilgan (biz qidiradigan nom shu) — AppRole kalitlari
  Deployment'da barmi-yo'qmi holaticha qolmoqda, chunki bayroq `None` bo'lganda
  kod ularga yetib bormaydi ham.

---

## Ichimizda qoladigan qism — ops'ga yubormang

Backend registrida `:main` tag **yo'q**: `main` pipeline `#41691` `build` jobida yiqilgan,
lexat kodda emas, runner/dind darajasida (`mount: permission denied (are you root?)`,
`/proc/net/ip6_tables_names`, `modprobe … /lib/modules`). Frontend `main` pipeline esa
muvaffaqiyatli (`#41683`, `d1ac73a`) → prod front `authorization_code` kontraktida, prod back
esa eski kontrakt (yoki umuman imajsiz). Foydalanuvchi buyrug'i: **main'ga tegilmaydi** — shu
sabab bu band yuqoridagi ikkala matnda ham yo'q.
