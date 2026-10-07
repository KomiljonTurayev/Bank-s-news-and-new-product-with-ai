"""Foydalanuvchi qo'shgan yangi mahsulotni bizning bazamizdagi (haqiqiy
bank saytlaridan yig'ilgan) shu turdagi takliflar bilan solishtirib,
qoidaga asoslangan (tashqi AI API'siz) tahlil matnini hosil qiladi."""

import re
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.banks import BANKS
from app.models import BankRate

_PERCENT_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_RATE_KEY_RE = re.compile(r"foiz|stavka", re.IGNORECASE)

# Tahlil matni tayyorlanadigan tillar to'plami. Yangi til qo'shilganda
# shu yerga qo'shish kifoya — FastAPI query parametri ham shu turdan
# foydalanib, ro'yxatdan tashqari qiymatlarni avtomatik rad etadi.
Lang = Literal["uz", "ru"]

# Har bir til uchun tahlil matnida ishlatiladigan iboralar. Yangi til
# qo'shish uchun shu yerga bitta yozuv qo'shish kifoya — `analyze_product`
# va `_rank_word` mantiqni takrorlamaydi.
_COPY: dict[Lang, dict] = {
    "uz": {
        "rank_words": ("juda raqobatbardosh", "o'rtachadan yaxshi", "o'rtachadan past", "kuchsiz raqobatbardosh"),
        "empty_summary": "Bozorda solishtirish uchun shu turdagi boshqa taklif hali topilmadi.",
        "summary_tpl": (
            "Bozorda shu turdagi {count} ta taklif topildi — ularning o'rtacha stavkasi {avg:.2f}%, "
            "eng past {min:.2f}%, eng baland {max:.2f}%. Ushbu mahsulotning {rate:.2f}% stavkasi "
            "bozorning {rank_word} qismida joylashadi."
        ),
        "direction_low": "past",
        "direction_high": "yuqori",
        "strength_tpl": "Stavka bozor o'rtachasiga nisbatan {direction} — bu mijoz uchun foydali.",
        "caution_tpl": (
            "Stavka bozor o'rtachasidan {direction} — raqobatbardoshligini oshirish uchun "
            "shartlarni qayta ko'rib chiqish tavsiya etiladi."
        ),
    },
    "ru": {
        "rank_words": ("очень конкурентоспособный", "выше среднего", "ниже среднего", "слабая конкурентоспособность"),
        "empty_summary": "На рынке пока не найдено других предложений этого типа для сравнения.",
        "summary_tpl": (
            "На рынке найдено {count} предложений данного типа — со средней ставкой {avg:.2f}%, "
            "минимальной {min:.2f}%, максимальной {max:.2f}%. Ставка данного продукта ({rate:.2f}%) "
            "относится к категории: {rank_word}."
        ),
        "direction_low": "ниже",
        "direction_high": "выше",
        "strength_tpl": "Ставка {direction} среднерыночной — это выгодно для клиента.",
        "caution_tpl": (
            "Ставка {direction} среднерыночной — рекомендуется пересмотреть условия "
            "для повышения конкурентоспособности."
        ),
    },
}
_BANK_NAMES = {b["code"]: b["name"] for b in BANKS}

# Kredit mahsuloti nomidan kategoriyani aniqlashda ishlatiladigan kalit
# so'zlar — birinchi mos kelgani tanlanadi, shu bois aniqroqlari
# (masalan "ipoteka") umumiyroqlaridan oldin turishi kerak. depozit.uz
# agregatoridan kelgan yozuvlar kategoriyani allaqachon o'z URL'idan olib
# yuradi (DepozitUzConnector); bu ro'yxat esa bankning o'z rasmiy
# saytidan olingan, kategoriyasiz yozuvlar uchun — ular ham xuddi shu
# kategoriyalar bo'yicha (masalan "Iste'mol krediti") solishtirilishi
# kerak, aks holda bozor taqqoslashida umuman ko'rinmay qoladi.
_CREDIT_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Ipoteka", ("ipoteka", "uy-joy", "uyjoy", "turar-joy", "turarjoy", "uy joy")),
    ("Avtokredit", ("avtokredit", "avto kredit", "avtomobil")),
    ("Ta'lim krediti", ("ta'lim", "talim", "ta’lim", "taʼlim")),
    ("Overdraft", ("overdraft",)),
    ("Mikroqarz", ("mikroqarz", "mikrokredit", "mikrozaym", "mikrozajm", "mikro qarz", "mikro kredit")),
    ("Iste'mol krediti", ("iste'mol", "istemol", "isteʼmol", "iste’mol")),
]


def _infer_credit_category(name: str | None) -> str | None:
    """Rasmiy bank saytidan olingan, kategoriyasi ko'rsatilmagan kredit
    yozuvlari uchun mahsulot nomidan taxminiy kategoriyani topadi.

    Diqqat: aniq mos kelgan kalit so'z bo'lmasa, "Iste'mol krediti" deb
    taxmin QILINMAYDI — banklar avtokredit/aksiya mahsulotlariga ko'pincha
    brend nomi beradi (masalan "ADM Global I", "UzAuto Motors Damas"),
    umumiy so'zsiz. Bunday nomlarni "Iste'mol krediti" deb faraz qilish
    ularning (ko'pincha aksiyaviy, 0% kabi past) stavkasini haqiqiy
    iste'mol krediti taklifi sifatida noto'g'ri ko'rsatib qo'yar edi."""
    if not name:
        return None
    lowered = name.lower()
    for category, keywords in _CREDIT_CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
    return None

# Kredit turidagi mahsulotlar uchun PASTROQ foiz mijozga foydali — web/app.js
# dagi isBetterWhenLower() bilan bir xil qoida.
_LOWER_IS_BETTER_TYPES = {"credit"}

_MARKET_SAMPLE_LIMIT = 8


def extract_rate_percent(data: dict) -> float | None:
    """Yozuvdan foiz stavkasini topadi (masalan "22%" yoki "14%").

    Avval nomida "foiz"/"stavka" so'zi bor maydonni qidiramiz — masalan
    ba'zi banklarda "Miqdori: Kontraktning 100% gacha" kabi foizli, lekin
    stavka bo'lmagan maydon "Foiz stavkasi"dan oldin kelib, uni xato
    ushlab qolishi mumkin edi. Topilmasa, avvalgidek birinchi %+raqam
    saqlagan maydonga qaytamiz (masalan nomida "Zor 6%" kabi foizi bor
    mahsulotlar uchun)."""
    for key, value in data.items():
        if isinstance(value, str) and "%" in value and _RATE_KEY_RE.search(key):
            match = _PERCENT_RE.search(value)
            if match:
                return float(match.group(0).replace(",", "."))
    for value in data.values():
        if isinstance(value, str) and "%" in value:
            match = _PERCENT_RE.search(value)
            if match:
                return float(match.group(0).replace(",", "."))
    return None


def _market_rows(product_type: str, session: Session, category: str | None = None) -> list[BankRate]:
    rows = session.scalars(select(BankRate).where(BankRate.product_type == product_type)).all()

    # Har fetch bir bankning bir mahsuloti uchun yangi qator qo'shadi va
    # eskisini o'chirmaydi — shu bois har bank/kredit turi/mahsulot nomi
    # kombinatsiyasi bo'yicha faqat eng so'nggi qatorni qoldiramiz, aks
    # holda bozor statistikasi (o'rtacha, taklif soni) eski, allaqachon
    # o'zgargan stavkalar bilan shishib ketadi.
    latest_by_key: dict[tuple, BankRate] = {}
    for row in rows:
        key = (row.bank_code, row.data.get("category"), row.data.get("name"))
        current = latest_by_key.get(key)
        if current is None or row.fetched_at > current.fetched_at:
            latest_by_key[key] = row
    rows = list(latest_by_key.values())

    if not category:
        return rows

    # Kredit turlari (Ipoteka, Avtokredit, ...) stavkalari bir-biridan keskin
    # farq qiladi — faqat bir xil turdagi takliflar bilan solishtiramiz.
    # Bankning rasmiy saytidan olingan yozuvlarda "category" maydoni
    # bo'lmasligi mumkin (depozit.uz'dan farqli, u yerda har bir
    # kategoriya alohida URL'ga ega) — bunday hollarda mahsulot nomidan
    # taxminan aniqlanadi, aks holda bu yozuvlar hech qanday
    # kategoriyaga mos kelmay, bozor taqqoslashida butunlay ko'rinmay
    # qolar edi.
    def _row_category(row: BankRate) -> str | None:
        explicit = row.data.get("category")
        if explicit:
            return explicit
        return _infer_credit_category(row.data.get("name")) if product_type == "credit" else None

    # MOS KATEGORIYA BO'LMASA BO'SH RO'YXAT qaytaramiz. Avval `matching or
    # rows` edi — ya'ni kategoriya bo'yicha bironta taklif bo'lmasa butun
    # bozor qaytarilardi: jadvalda "Ipoteka: 2 ta taklif" yonida aslida 5
    # ta aralash turdagi o'rtacha chiqardi (ipoteka 25% yonida avtokredit
    # 60%). Kredit turlari stavkalari keskin farq qilgani uchun bunday
    # "o'rtacha" moliyaviy xulosa sifatida noto'g'ri. Bo'sh bo'lsa
    # analyze_product halol "solishtirish uchun taklif topilmadi" deydi.
    return [row for row in rows if _row_category(row) == category]


def _market_rates(rows: list[BankRate]) -> list[float]:
    rates = (extract_rate_percent(row.data) for row in rows)
    return [r for r in rates if r is not None]


def _beats_current(current: tuple[float, BankRate, bool] | None, rate: float, is_official: bool,
                   lower_is_better: bool) -> bool:
    """Yangi yozuv o'sha bankning joriy nomzodini bosadimi? Rasmiy sayt
    yozuvi depozit.uz'dan qat'i nazar ustun turadi (mavjud bo'lmagandagina
    agregator qoladi), shundan keyin mijozga foydaliroq stavka tanlanadi."""
    if current is None:
        return True
    current_rate, _current_row, current_is_official = current
    if is_official != current_is_official:
        return is_official
    return rate < current_rate if lower_is_better else rate > current_rate


def _market_sample(rows: list[BankRate], lower_is_better: bool, limit: int = _MARKET_SAMPLE_LIMIT) -> list[dict]:
    """Har bir bank uchun eng maqbul (mijozga eng foydali) stavkasini
    tanlab, diagramma uchun eng yaxshi `limit` ta bankni qaytaradi. Har bir
    yozuv o'sha aniq taklifning manba havolasini ham olib yuradi — frontend
    diagrammadagi bankni bosganda to'g'ridan-to'g'ri o'sha sahifaga
    o'tkazish uchun.

    Bir xil bank uchun ham bankning o'z rasmiy saytidan, ham depozit.uz
    agregatoridan yozuv kelgan bo'lishi mumkin — havola bosilganda
    foydalanuvchi bankning haqiqiy sahifasiga tushishi uchun tanlov
    qoidasi `_beats_current`da."""
    best_by_bank: dict[str, tuple[float, BankRate, bool]] = {}
    for row in rows:
        rate = extract_rate_percent(row.data)
        if rate is None:
            continue
        source = row.data.get("source")
        is_official = bool(source) and source != "depozit.uz"
        current = best_by_bank.get(row.bank_code)
        if _beats_current(current, rate, is_official, lower_is_better):
            best_by_bank[row.bank_code] = (rate, row, is_official)

    best_by_bank_rate = {code: (rate, row) for code, (rate, row, _is_official) in best_by_bank.items()}
    ordered = sorted(best_by_bank_rate.items(), key=lambda item: item[1][0], reverse=not lower_is_better)
    return [
        {
            "bank_code": code,
            "bank_name": _BANK_NAMES.get(code, code),
            "rate": rate,
            "url": row.data.get("url"),
        }
        for code, (rate, row) in ordered[:limit]
    ]


def _score(rate: float, market_rates: Sequence[float], lower_is_better: bool) -> int:
    if lower_is_better:
        beats = sum(1 for r in market_rates if rate <= r)
    else:
        beats = sum(1 for r in market_rates if rate >= r)
    return round(beats / len(market_rates) * 100)


def _rank_word(score: int, lang: Lang = "uz") -> str:
    excellent, good, weak, poor = _COPY[lang]["rank_words"]
    if score >= 75:
        return excellent
    if score >= 50:
        return good
    if score >= 25:
        return weak
    return poor


def analyze_product(
    product_type: str,
    rate: float,
    session: Session,
    category: str | None = None,
    lang: Lang = "uz",
) -> dict:
    """Berilgan mahsulot turining bozordagi statistikasi va shu asosdagi
    matnli tahlilni qaytaradi. Bozorda solishtiriladigan ma'lumot
    topilmasa, tegishli maydonlar None bo'ladi."""
    copy = _COPY[lang]
    lower_is_better = product_type in _LOWER_IS_BETTER_TYPES
    rows = _market_rows(product_type, session, category)
    market_rates = _market_rates(rows)

    if not market_rates:
        return {
            "market_count": 0,
            "market_min": None,
            "market_avg": None,
            "market_max": None,
            "score": None,
            "summary": copy["empty_summary"],
            "strengths": [],
            "cautions": [],
            "market_sample": [],
        }

    market_min = min(market_rates)
    market_max = max(market_rates)
    market_avg = sum(market_rates) / len(market_rates)
    score = _score(rate, market_rates, lower_is_better)
    rank_word = _rank_word(score, lang=lang)

    summary = copy["summary_tpl"].format(
        count=len(market_rates), avg=market_avg, min=market_min, max=market_max, rate=rate, rank_word=rank_word
    )

    if score >= 50:
        direction = copy["direction_low"] if lower_is_better else copy["direction_high"]
        strengths = [copy["strength_tpl"].format(direction=direction)]
        cautions = []
    else:
        direction = copy["direction_high"] if lower_is_better else copy["direction_low"]
        strengths = []
        cautions = [copy["caution_tpl"].format(direction=direction)]

    return {
        "market_count": len(market_rates),
        "market_min": market_min,
        "market_avg": market_avg,
        "market_max": market_max,
        "score": score,
        "summary": summary,
        "strengths": strengths,
        "cautions": cautions,
        "market_sample": _market_sample(rows, lower_is_better),
    }


# --- Bozor yetakchilari (AI'siz, so'rovdan oldin ko'rsatiladi) ---

_FOREIGN_CURRENCY_RE = re.compile(r"\b(usd|eur|aqsh dollar|dollar|yevro|evro|euro)\b|\$|€", re.IGNORECASE)
_TERM_KEY_RE = re.compile(r"muddat", re.IGNORECASE)
_AMOUNT_KEY_RE = re.compile(r"summa|miqdor", re.IGNORECASE)
# Kreditda bundan past stavka deyarli doim subsidiyali/aksiya ("0% dan",
# avtosalon bilan hamkorlikdagi 5-6% avtokreditlar) — "bozordagi eng arzon"
# deb ko'rsatish chalg'itadi.
_MIN_CREDIT_RATE = 10.0
# Karta bo'limida stavka asosan kredit kartaning foizi — u yerda past stavka
# maqbul; bunday yozuvlar nomidan ajratiladi.
_CREDIT_CARD_RE = re.compile(r"kredit|credit|кредит", re.IGNORECASE)
_DETAIL_LIMIT = 60


def _first_field(data: dict, key_re: re.Pattern) -> str | None:
    for key, value in data.items():
        if key_re.search(key) and isinstance(value, str) and value.strip():
            return value.strip()[:_DETAIL_LIMIT]
    return None


def offer_details(data: dict) -> dict:
    """Kartochkada stavka yonida ko'rsatiladigan muddat va summa matni."""
    return {"term": _first_field(data, _TERM_KEY_RE), "amount": _first_field(data, _AMOUNT_KEY_RE)}


def top_market_offers(product_type: str, session: Session, limit: int = 3) -> list[dict]:
    """Jismoniy shaxslar uchun so'mdagi eng maqbul stavkali takliflar — har
    bankdan bittadan. Omonatda yuqori, kredit va kredit kartada past stavka
    maqbul (karta bo'limida faqat kredit kartalar solishtiriladi)."""
    lower_is_better = product_type in _LOWER_IS_BETTER_TYPES or product_type == "card"
    rated = []
    for row in _market_rows(product_type, session):
        if row.segment != "individual" or _FOREIGN_CURRENCY_RE.search(" ".join(map(str, row.data.values()))):
            continue
        if product_type == "card" and not _CREDIT_CARD_RE.search(str(row.data.get("name") or "")):
            continue
        rate = extract_rate_percent(row.data)
        if rate is None or rate <= 0 or rate > 100 or (lower_is_better and rate < _MIN_CREDIT_RATE):
            continue
        rated.append((rate, row))
    rated.sort(key=lambda item: item[0], reverse=not lower_is_better)

    leaders, seen_banks = [], set()
    for rate, row in rated:
        if row.bank_code in seen_banks:
            continue
        seen_banks.add(row.bank_code)
        leaders.append(
            {
                "bank_code": row.bank_code,
                "bank_name": _BANK_NAMES.get(row.bank_code, row.bank_code),
                "name": str(row.data.get("name") or ""),
                "category": row.data.get("category"),
                "segment": row.segment,
                "rate": rate,
                "url": row.data.get("url"),
                **offer_details(row.data),
            }
        )
        if len(leaders) == limit:
            break
    return leaders
