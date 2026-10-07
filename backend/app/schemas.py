"""API so'rov/javob shakllari (Pydantic) — marshrut handlerlaridan
(`app/api.py`) ajratilgan, shu bois validatsiya qoidalari mustaqil
o'qilishi/testlanishi mumkin.

Bu yerdagi javob (response) sxemalari OpenAPI/Swagger (`/docs`, `/openapi.json`)
uchun ham xizmat qiladi — API'ga tashqi tizim (masalan AI xizmati) ulanganda, aynan shu sxemalar orqali javob shaklini oldindan biladi."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CustomProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    product_type: str
    category: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=150)
    purpose: str | None = Field(default=None, max_length=300)
    currency: Literal["UZS", "USD", "EUR"] = "UZS"
    # Foiz stavkasi uchun yuqori chegara — qo'l xatosini ("20" o'rniga
    # "200" kabi) ushlash uchun sanity-check: bozordagi eng yuqori stavka
    # (mikroqarz) ~45%, 100% undan ancha yuqori.
    rate: float = Field(ge=0, le=100)
    # 1 milliard — summa maydonlari uchun yuqori chegara (qo'l xatosini,
    # masalan ortiqcha nol qo'shib yuborishni, ushlaydi).
    min_amount: float | None = Field(default=None, ge=0, le=1_000_000_000)
    max_amount: float | None = Field(default=None, ge=0, le=1_000_000_000)
    # 240 oy = 20 yil — O'zbekistondagi eng uzun keng tarqalgan kredit
    # muddati (masalan ipoteka) hisobga olingan yuqori chegara.
    term_months: int | None = Field(default=None, ge=1, le=240)
    initial_payment_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Mahsulot nomi bo'sh bo'lishi mumkin emas")
        return value

    @model_validator(mode="after")
    def _min_amount_not_above_max(self) -> "CustomProductIn":
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("Min. summa maks. summadan katta bo'lishi mumkin emas")
        return self


class CustomProductPatch(BaseModel):
    """Tahrirlash so'rovi — yaratishdagi maydonlarning istalgan qismi.
    Yuborilmagan maydon o'zgarishsiz qoladi, shu bois handler'da
    `exclude_unset` bilan o'qiladi."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    product_type: str | None = None
    category: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=150)
    purpose: str | None = Field(default=None, max_length=300)
    currency: Literal["UZS", "USD", "EUR"] | None = None
    rate: float | None = Field(default=None, ge=0, le=100)
    min_amount: float | None = Field(default=None, ge=0, le=1_000_000_000)
    max_amount: float | None = Field(default=None, ge=0, le=1_000_000_000)
    term_months: int | None = Field(default=None, ge=1, le=240)
    initial_payment_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Mahsulot nomi bo'sh bo'lishi mumkin emas")
        return value

    @model_validator(mode="after")
    def _mandatory_not_cleared(self) -> "CustomProductPatch":
        # Uchtasiga ham `null` yuborish mumkin emas: qatorda NOT NULL ustunlar.
        # None ni "maydon yuborilmadi"dan ajratish uchun model_fields_set qaraymiz.
        for field in ("name", "product_type", "rate"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"`{field}` maydonini bo'sh qilish mumkin emas")
        return self


class BankOut(BaseModel):
    code: str = Field(description="Bankning ichki qisqa kodi, masalan \"SQB\"")
    name: str = Field(description="Bankning to'liq nomi")


class ProductTypeOut(BaseModel):
    code: str = Field(description="Mahsulot turi kodi, masalan \"deposit\"")
    label: str = Field(description="Mahsulot turining o'qiladigan nomi")


class SegmentOut(BaseModel):
    code: str = Field(description="Segment kodi: \"individual\" yoki \"business\"")
    label: str = Field(description="Segmentning o'qiladigan nomi")


class MetaOut(BaseModel):
    banks: list[BankOut]
    product_types: list[ProductTypeOut]
    segments: list[SegmentOut]


class LivenessOut(BaseModel):
    """Readiness/liveness probe javobi.

    Ma'lumot holati bu yerda ATAYLAB yo'q: probe DB'ga bog'lansa, baza
    istalmaganda pod trafikdan olib tashlanadi (services.endpoints bo'sh →
    edge nginx 502). Ma'lumot yangiligi `/api/health`da.
    """

    status: Literal["alive"] = Field(description="\"alive\" — app HTTP so'rovlarini qabul qilyapti; DB tekshirilmadi")


class SourceFreshnessOut(BaseModel):
    """Manbalar kesimidagi yangilik. Global `status` bitta tirik manba bilan
    qolganlarining uzilganini yashirmasligi uchun bor."""

    total: int = Field(description="Konektorlar o'zi yozadigan noyob manzil soni (bank + mahsulot turi + segment); agregatorlar tashqarida")
    stale: int = Field(description="Shu qancha vaqtdan beri yangilanmagan manba; bazada umuman yozuvi bo'lmaganlari ham shunda")
    sample: list[str] = Field(description="Eng eskilari (\"bank/mahsulot/segment\"), eng ko'pi 10 ta")


class HealthOut(BaseModel):
    """Fon rejimidagi scheduler (`app/scheduler.py`) haqiqatan ishlab
    turganini tashqi monitoring xizmati (masalan UptimeRobot, Healthchecks.io)
    orqali tekshirish uchun — bazadagi eng so'nggi yig'ilgan yozuv qachonligini
    ko'rsatadi."""

    status: Literal["ok", "stale"] = Field(
        description="\"stale\" — jadval rejimida oxirgi rejalashtirilgan tikish o'tib, shu soatda yig'ish tugamagan; interval rejimida oxirgi yig'ish stale_after_minutes'dan eskirgan (yoki hali umuman bo'lmagan)"
    )
    last_fetch_at: datetime | None = Field(description="Bazadagi eng so'nggi fetched_at; hali hech narsa yig'ilmagan bo'lsa null")
    fetch_interval_minutes: int = Field(description="Interval rejimi qadami (FETCH_INTERVAL_MINUTES) — faqat scrape_times bo'sh bo'lganda tikish oralig'i sifatida ishlatiladi")
    stale_after_minutes: int = Field(description="Normal holatda kutishga bo'ladigan eng katta jimlik: jadval rejimida eng uzon reja oralig'i + 45 daqiqa zaxira, interval rejimida 2xFETCH_INTERVAL_MINUTES")
    scrape_times: list[str] = Field(description="Kuniga qo'ng'iroq soatlari, HH:MM (Asia/Tashkent), masalan [\"09:00\", \"14:00\"]; bo'sh ro'yxat — interval rejimi")
    next_fire_at: datetime | None = Field(description="Keyingi rejalashtirilgan tikish (Toshkent, tz-aware); interval rejimida null")
    sources: SourceFreshnessOut = Field(description="Manba-ma'noda holat — bitta tirik bank qolganlarini yashirmasin")
    git_commit: str = Field(description="Obraz yig'ilgan commit (CI_COMMIT_SHA); lokal/CI'siz build'da \"dev\"")
    scrape_window: str = Field(description="Skreypingga ruxsat berilgan mahalliy vaqt oralig'i (Asia/Tashkent); cheklov bo'lmasa \"24/7\"")
    scrape_active_now: bool = Field(description="false — hozir oyna tashqarisida, skreyping bo'lmayapti (bu normal holat)")


class SourceStatusOut(BaseModel):
    """Bitta tashqi manba (host) bo'yicha circuit breaker holati."""

    source: str = Field(description="Host nomi (masalan `cbu.uz`) — breaker shu nom bo'yicha yuritiladi")
    open: bool = Field(description="true — manba vaqtincha nosoz, so'rovlar hozircha manbaga bormayapti")
    consecutive_failures: int = Field(description="Ketma-ket muvaffaqiyatsiz urinishlar soni (breaker ochilishiga necha qoldi)")


class SourcesStatusOut(BaseModel):
    """"Biror manba uzilib qoldimi?" degan savolga javob. Bitta manbaning
    ochiq breaker'i loyihani to'xtatmaydi — qolgan manbalar ishlaveradi,
    shu sabab `status` bu yerda `ok`/`degraded`, `error` EMAS."""

    status: Literal["ok", "degraded"] = Field(description="\"degraded\" — hozir kamida bitta manba chetda (breaker ochiq)")
    open_sources: int = Field(description="Hozir ochiq (nosoz deb topilgan) manbalar soni")
    sources: list[SourceStatusOut] = Field(description="So'ralgan barcha manbalar; birorta so'rov bo'lmagan hostlar ro'yxatda bo'lmaydi")
    scrape_window: str = Field(description="Skreypingga ruxsat etilgan mahalliy vaqt oralig'i; cheklov bo'lmasa \"24/7\"")
    scrape_active_now: bool = Field(description="false — hozir skreyping oynasi yopiq, tashqi manbalarga murojaat qilinmayapti")
    min_host_interval_seconds: float = Field(description="Bitta hostga ketma-ket so'rovlar orasidagi majburiy tanaffus (anti-block); 0 — o'chiq")


class BankRateOut(BaseModel):
    """Bitta bankning bitta mahsuloti bo'yicha eng so'nggi yig'ilgan yozuvi.
    `data` maydoni manbaga qarab har xil kalitlarga ega bo'lishi mumkin
    (masalan kredit uchun "name"/"Foiz stavkasi", valyuta uchun "code"/"side") —
    shu bois erkin JSON ob'ekt sifatida qaytariladi."""

    bank_code: str
    product_type: str
    segment: str
    data: dict = Field(description="Manbaga qarab o'zgaruvchi xom ma'lumot (masalan foiz stavkasi, mahsulot nomi, havola)")
    fetched_at: datetime = Field(description="Ma'lumot manbadan qachon yig'ilgani")
    facets: dict = Field(
        default_factory=dict,
        description="Filtr qirralari: valyuta, muddat (oy), summa, kredit turi, karta turi/to'lov tizimi",
    )


class CurrencyStatsOut(BaseModel):
    code: str = Field(description="Valyuta kodi, masalan \"USD\"")
    min: float = Field(description="Tanlangan davrdagi eng past rasmiy kurs")
    max: float = Field(description="Tanlangan davrdagi eng baland rasmiy kurs")
    avg: float = Field(description="Tanlangan davrdagi o'rtacha rasmiy kurs")
    current: float = Field(description="Eng so'nggi ma'lum rasmiy kurs")
    change_pct: float = Field(description="Davr boshidan hozirgacha foizdagi o'zgarish")
    samples: int = Field(description="Statistikaga kirgan kunlik nuqtalar soni")
    sparkline: list[float] = Field(description="Kichik grafik uchun so'nggi qiymatlar ro'yxati (eng ko'pi 60 ta)")


class CurrencyPointOut(BaseModel):
    date: str = Field(description="Sana, ISO shaklida (YYYY-MM-DD)")
    value: float = Field(description="O'sha kundagi rasmiy kurs")


class CurrencyHistoryOut(BaseModel):
    code: str = Field(description="Valyuta kodi, masalan \"USD\"")
    points: list[CurrencyPointOut]


class CustomProductOut(BaseModel):
    id: int
    name: str
    product_type: str
    category: str | None = None
    bank_name: str | None = None
    purpose: str | None = None
    currency: str
    rate: float
    min_amount: float | None = None
    max_amount: float | None = None
    term_months: int | None = None
    initial_payment_pct: float | None = None
    created_at: datetime
    created_by: str | None = Field(
        default=None, description="Tarixiy maydon (login olib tashlanishidan oldingi yozuvlar); yangi yozuvlarda bo'sh"
    )


class MarketSampleItem(BaseModel):
    bank_code: str
    bank_name: str
    rate: float = Field(description="Shu bankning mos taklifidagi eng maqbul stavkasi")
    url: str | None = Field(default=None, description="Taklif manbasiga havola, mavjud bo'lsa")


class ProductAnalysisOut(BaseModel):
    """Foydalanuvchi kiritgan mahsulotni bozordagi shu turdagi haqiqiy
    takliflar bilan solishtirib chiqarilgan tahlil — tashqi AI oqimlari uchun asosiy qiziqish uyg'otadigan qism."""

    market_count: int = Field(description="Solishtirishda ishtirok etgan bozor takliflari soni")
    market_min: float | None = Field(default=None, description="Bozordagi eng past stavka (taklif topilmasa null)")
    market_avg: float | None = Field(default=None, description="Bozordagi o'rtacha stavka (taklif topilmasa null)")
    market_max: float | None = Field(default=None, description="Bozordagi eng baland stavka (taklif topilmasa null)")
    score: int | None = Field(default=None, description="0-100 oralig'idagi raqobatbardoshlik bahosi (taklif topilmasa null)")
    summary: str = Field(description="Tahlil matni")
    strengths: list[str] = Field(description="Mahsulotning kuchli tomonlari haqidagi izohlar")
    cautions: list[str] = Field(description="Mahsulotning zaif tomonlari haqidagi ogohlantirishlar")
    market_sample: list[MarketSampleItem] = Field(description="Diagramma uchun bank bo'yicha eng maqbul takliflar namunasi")


class ProductWithAnalysisOut(CustomProductOut):
    analysis: ProductAnalysisOut


class RecommendationIn(BaseModel):
    product_type: Literal["credit", "deposit", "card", "investment"]
    category: str | None = Field(default=None, max_length=100, description="Kredit turi (masalan Ipoteka) — ixtiyoriy")
    goal: str | None = Field(
        default=None, max_length=500, description="Jamoaning maqsadi, masalan \"yoshlar uchun omonat\" — ixtiyoriy"
    )
    count: int = Field(default=3, ge=1, le=5, description="Nechta mahsulot tavsiya qilinsin")
    lang: Literal["uz", "ru"] = "uz"


class RecommendedProductOut(BaseModel):
    name: str
    product_type: str
    category: str | None = None
    currency: str
    rate: float
    min_amount: float | None = None
    max_amount: float | None = None
    term_months: int | None = None
    initial_payment_pct: float | None = None
    target_segment: str
    purpose: str
    rationale: str
    risks: list[str]


class MarketLeaderOut(BaseModel):
    bank_code: str
    bank_name: str
    name: str
    category: str | None = None
    segment: str
    rate: float
    url: str | None = None
    term: str | None = None
    amount: str | None = None
    why: str | None = Field(default=None, description="AI izohi — faqat AI tanlagan yetakchilarda")


class CompareOfferOut(BaseModel):
    bank_code: str
    bank_name: str
    name: str
    category: str | None = None
    rate: float
    term_months: int | None = None
    term_text: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    amount_text: str | None = None
    url: str | None = None


class CompareStatsOut(BaseModel):
    count: int
    min_rate: float
    avg_rate: float
    max_rate: float
    banks: int
    best: CompareOfferOut


class TermBucketOut(CompareStatsOut):
    key: str
    from_months: int
    to_months: int | None = None


class CategoryStatsOut(CompareStatsOut):
    name: str


class MarketCompareOut(BaseModel):
    product_type: str
    category: str | None = None
    lower_is_better: bool
    overall: CompareStatsOut | None = None
    term_buckets: list[TermBucketOut]
    categories: list[CategoryStatsOut]
    offers: list[CompareOfferOut]


class RecommendationOut(BaseModel):
    product_type: str
    category: str | None = None
    market_count: int = Field(description="AI'ga berilgan bozor takliflari soni")
    model: str = Field(description="Javob bergan Claude modeli")
    market_overview: str
    market_leaders: list[MarketLeaderOut] = Field(
        default_factory=list, description="Bozordagi mavjud takliflardan eng jozibador 3 tasi (ma'lumot bazadan)"
    )
    recommendations: list[RecommendedProductOut]
