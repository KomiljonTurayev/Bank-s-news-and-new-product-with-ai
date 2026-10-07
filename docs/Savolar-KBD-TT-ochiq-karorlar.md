# RASMIY SAVOLLAR RO'YXATI
## TT-2026-001 bo'yicha ochiq qarorlarni yopish uchun

| | |
|---|---|
| **Yuboruvchi** | Axborot texnologiyalari departamenti (Z. Orifxo'jayev) |
| **Qabul qiluvchi** | Kichik biznes departamenti (KBD) boshlig'i (J. Makhmudov) |
| **Asos** | TT-2026-001 v0.1, 23-bo'lim (Ochiq qarorlar) va 21-bo'lim (Buyurtmachi topshiqlari); BT-2026-001 v1.0 |
| **Javob muddati** | Har bir savolga ko'rsatilgan sana gacha |
| **Javob shakli** | Xat bilan (qog'oz yoki e-imzo). Har javob — savol raqami + tanlangan variant (masalan: «J-3 — B variant») yoki yozma izoh. |

**Nega bu muhim.** TT-2026-001 hozircha v0.1 loyihadir: 23-bo'lim talabiga ko'ra ochiq qarorlar yopilmasa hujjat imzolangan hisoblanmaydi va loyiha ish boshlanish sanasi siljiydi (TT 25.3). Har savol tagida **javob kelmasa kuchga kiradigan default** yozilgan — javobsizlik ham qaror, lekin eng noqulay variant sifatida.

---

## BLOK A. Taqqoslash metodologiyasi (eng og'ir savollar)

### J-1. Qaysi parametrlar bo'yicha va qanday og'irlikda «eng zomin/eng yaxshi» deb baholanadi?
*TT bog'lanish: OD-1, D-3, 9.3-bo'lim.*

Tizim har bir bank mahsulotini 12 parametr bo'yicha raqamlaydi, lekin «ustunlik» xulosasi uchun parametrlarning **nisbiy ahamiyati** kerak. Bu texnik emas — biznes qarori. Ijrochi buni o'zi belgilasa, natija «sizning savolingizga javob bermadi» deb rad etilishi mumkin.

| Variant | Mazmun |
|---|---|
| A | Barcha 12 parametr **teng** ahamiyatda (default — kuchsiz, real biznes mantig'iga ko'p hollarda to'g'ri kelmaydi) |
| B | KBD og'irliklarni o'zi belgilaydi: stavka __%, ta'minot __%, muddat __%, summa __%, komissiya __%, imtiyozli davr __% (yig'indisi 100%) |
| C | KBD parametrlarni faqat **darajalar**ga saralaydi (kritik / muhim / ikkinchi daraja), og'irlikni biz bir tekis taqsimlaymiz |

**Javob kelmasa:** A variant (teng taqsimot) va reyting ustiga «og'irliklar kelishilmagan» yozuvi chiqadi. Reyting bo'limi qabul qilinmaydi deb hisoblanadi (TT BRB-03).

### J-2. Taqqoslash qanday «guruhlar» ichida o'tkaziladi?
*TT bog'lanish: D-3, 9.3.1-bo'lim. Muddat: J-1 bilan birga.*

Har xil mahsulotlarni bitta jadvalga solish noto'g'ri natija beradi. Quyidagi guruhlash qoidasini tasdiqlang yoki to'g'rilang:

1. Mahsulot turlari bo'yicha alohida (aylanma kapital, investitsion kredit, lizing, kafolat va h.k.) — **KBD 1-turdagi mahsulot turlari ro'yxatini berishi kerak** (ro'yxat hozircha yo'q, bu ham shu javobning bir qismi);
2. Segment bo'yicha alohida (yuridik shaxs / KHB);
3. Summa va muddat oralig'i kesishmagandagina taqqoslash;
4. Guruhda 3 tadan kam taklif bo'lsa — «taqqoslash uchun asos yo'q» deb ko'rsatiladi, majburiy birlashtirish qilinmaydi.

**Javob kelmasa:** biz BT matnidan chiqarilgan taxminiy 6 ta tur ro'yxati bilan ishlaymiz — xato bo'lsa, Faza III qayta ishlanadi (jadval +3-4 hafta).

### J-3. BRB o'z mahsulotlari ma'lumoti tizimga qayerdan keladi?
*TT bog'lanish: OD-2, BRB-05. Muddat: **loyiha boshlanishigacha** — kechikish kritik yo'lni uzaytiradi.*

Raqobatchilarni o'z mahsulotimiz bilan solishtiramiz — demak BRB tomoni ham tizimda aniq turishi kerak.

| Variant | Mazmun | Narx / muddat ta'siri |
|---|---|---|
| A | KBD xodimi admin UI orqali **qo'lda kiritadi/yangilaydi** (default) | 0 PD; lekin aniqlik va yangilanish uchun javobgarlik KBD'da — mas'ul xodim va yangilash chastotasi ko'rsatilishi shart |
| B | **iABS read-only** ulanish orqali avtomatik | 13 PD + atamalar hisobi va tarmoq ruxsati **1-haftada** boshlanishi shart (BRB-05) |
| C | **DWH-DS** orqali (texnik kanal tayyor) | ~3 PD; lekin DWH'da kredit shartlari (ta'minot, komissiya, imtiyoz) bormi — tekshiruv kerak, javobingizdan keyin 3 kun ish |
| D | brb.uz saytimizni ham skreypering qilamiz | o'z mahsulotimiz uchun ikkinchi, nazoratsiz manba ochiladi (bir ma'lumot ikki xil yo'l bilan yangilanadi); tavsiya etilmaydi |

**Javob kelmasa:** A variant kuchga kiradi va «BRB ma'lumoti eskirgan» da'vosi qabuldan keyingi kelishmovchilik hisoblanmaydi (aktga yoziladi).

### J-4. Birinchi bosqich qamrovi: faqat yuridik shaxslar + KHBmi?
*TT bog'lanish: OD-3, 2.1-bo'lim.*

| Variant | Mazmun |
|---|---|
| A | **Faza 1** — yuridik shaxslar + KHB kreditlari; jismoniy shaxslar — 2-bosqich (default, tavsiya) |
| B | Bir bosqichda hammasi, jismoniy shaxslar bilan. Manba soni ~2 barobar oshadi, jadval ≈ +6-8 hafta, baho +35-45 PD |
| C | Faqat yuridik shaxslar (KHB ham keyin). Jadval −2 hafta |

**Javob kelmasa:** A.

---

## BLOK B. AI qatlamiga oid savollar

### J-5. «AI tavsiyalar» (FR-09) o'rniga nima bo'ladi?
*TT bog'lanish: OD-8, 9.4–9.5-bo'limlar.*

BT'da «AI mahsulot tavsiyalari» bor, lekin qabul mezoni yo'q va tavsiyaga asoslanib biznes qaror qilingan taqdirda javobgarlik belgilanmagan. Biz buni **raqamli tahlil** bilan almashtirishni taklif qilamiz: «foiz stavkangiz guruh medianasidan +3.2 p.p. yuqori — 11 tadan 9 tasi past» kabi aniq, tekshiriladigan xulosalar (har xulosa tagida manba va sana).

| Variant | Mazmun | Narx / shart |
|---|---|---|
| A | Raqamli gap-analysis yetarli (default, tavsiya) | 0 qo'shimcha PD |
| B | Generativ matnli tavsiyalar ham kerak | Ichki LLM gateway shart (OD-7, AT tomoniga alohida so'raladi) + har tavsiya yoniga «bu AI taxmini, qaror javobgarligi foydalanuvchida» degan yozuv + Yurist kelishuvi |

**Javob kelmasa:** A. B varianti keyin ochilsa — alohida o'zgarish so'rovi orqali.

### J-6. Qo'lda tekshirish navbati (review queue) uchun KBD resursi — kim va qancha vaqt?
*TT bog'lanish: BRB-02, 18.2-bo'lim.*

Model ishonchsiz topilgalarni va etalon to'plamni inson tasdiqlaydi. Bu KBD'ning **eng katta doimiy ishtiroki**:

1. Etalon to'plam: **2 belgilovchi + 1 hakam**, jami ≈ **120 soat**, Faza I davomida (haftasiga ~8-10 soat/odam);
2. Doimiy rejim: review queue uchun haftasiga ≈ 3-5 soat (taxmin — real hajm Faza II'da aniqlanadi).

Iltimos javob bering: **(a)** belgilovchilarning familiyalari va ularning bandligiga rozilik; **(b)** haftalik ~3-5 soatlik doimiy yuk KBD uchun qabul qilinganmi?

**Javob kelmasa:** etalon yig'ilmaydi → «98% aniqlik» mezoni **o'lchansiz** qoladi → qabul testini o'tkazib bo'lmaydi. Bu — loyihadagi KBD ixtiyoridagi yagona almashtirib bo'lmaydigan javob.

### J-7. Alertlarni nima «muhim» deb hisoblaydi?
*TT bog'lanish: 10.2–10.3-bo'limlar (shovqin chegarasi va kvotalar).*

| Sozlama | Bizning default | J-7 bo'yicha KBD javobi (e/yoq yoki o'z qiymatingiz) |
|---|---|---|
| Stavka o'zgarishi bo'yicha minimal sezgirlik | 0.3 p.p. dan kichik o'zgarish xabar qilmaydi | e / yoq / son: ____ |
| SMS limiti | 1 kishiga kuniga 20 ta | e / yoq / son: ____ |
| Tinch soatlar (xabar yuborilmaydi) | 21:00–07:00 | e / yoq / oralik: ____ |
| «Mahsulot olib tashlandi» xabari | 2 ta ketma-ket siklda tasdiqlangan keyin | e / yoq |

**Javob kelmasa:** defaultlar; «ko'p xabar keldi / yetib kelmadi» shikoyati asossiz hisoblanadi.

---

## BLOK C. Qabul shartlarini yozma tasdiqlash

Bular «savol» emas, **imzo talab qiladigan e'lonlardir** — TT 22-bo'limida batafsil asoslangan. Har biriga «tasdiqlayman (1) / tasdiqlamayman + sabab (2)» deb javob bering.

| № | Band | Tasdiqlanmasa nima bo'ladi |
|---|---|---|
| T-1 | **12 oylik tarix** (AC-07) qabul aktida «tarix yig'ish mexanizmi ishlaydi» deb qabul qilinadi; to'liq 12 oy natural ravishda 12 oydan keyin hosil bo'ladi | Qabul aktida AC-07 yopilolmaydi — tizim texnik jihatdan tayyor bo'lsa ham |
| T-2 | **O'zgarishdan xabar** SLA: 45 daqiqa (aniqlash) + 5 daqiqa (yetkazish), faqat 07:00–21:00 oynasi ichida (tungi sayt o'zgarishi ertalab sanaladi) | FR-10'ning 24/7 talabi bajarilmaydigan band sifatida hujjatga tushadi, bahs aktga qadar cho'ziladi |
| T-3 | Bank sayti anti-bot bilan to'ssa — biz to'siqni aylanib o'tmaymiz; manba «bloklangan» holatiga o'tadi va qo'lda kiritish kanali ishlaydi | Huquqiy va bloklanish riski bahslari bizning blokimizga qoladi |
| T-4 | Muvaffaqiyat mezonlari (M-1…M-6) qabul aktida **tizim ekrani hisobotlari** bilan tasdiqlanadi; M-6 — 5 nafar xodimning 4 haftalik piloti + so'rovnoma (BRB-08: 5+ xodim, 4 hafta — bandlikka rozilikmii?) | Qabul subyektiv bahoga aylanadi va imzo cho'ziladi |

---

## JAVOB VARAQASI (shu jadvalni to'ldirib qaytaring)

| Savol | Javob (variant/son/matn) | Javobgar | «Kechiktiriladi» bo'lsa — sanasi |
|---|---|---|---|
| J-1 | | | |
| J-2 | | | |
| J-3 | | | |
| J-4 | | | |
| J-5 | | | |
| J-6 | | | |
| J-7 | | | |
| T-1…T-4 | (har biri uchun 1 yoki 2 + sabab) | | |

---

### KBD ixtiyorida bo'lmagan savollar (alohida yuboriladi)

Qolgan 5 ochiq qaror boshqa mas'ullarga yozma so'raladi — KBD javobsizligi ularni bloklamasin: **OD-4** (Yurist boshqarmasi — manbalar huquqiy xulosasi, TT BRB-04), **OD-5/OD-6** (AT + Xavfsizlik xizmati — stek va arxitektura varianti), **OD-7** (AT — ichki LLM gateway, BRB-06), **OD-9** (AT — SMTP/SMS kanallari, BRB-07).

*Eslatma: «javob kelmasa default» mexanizmi hujjatni cheksiz kutishdan saqlaydi, majburiyot tug'maydi. Defaultlarning barchasi ongli ravishda eng past qulaylikdagi variantlar etib tanlangan — ulardan birortasi qaytarilishi faqat yozma «keling, boshqacha qilib ko'ramiz» javobi bilan mumkin.*

---

## IMZO

| | |
|---|---|
| Ma'lumot uchun:<br>Z. Orifxo'jayev<br>AT departamenti | «___» ______________ 2026 y.<br><br>_________________________ (imzo) |
