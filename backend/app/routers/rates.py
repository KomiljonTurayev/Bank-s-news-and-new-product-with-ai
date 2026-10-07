"""`/api/rates/*` — banklardan yig'ilgan foiz stavkalari/tariflar va
cbu.uz rasmiy valyuta kursi dinamikasi."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.offer_facets import offer_facets
from app.connectors.cbu_dynamics import TRACKED_CODES, fetch_all_histories, stats_for_window, window_for_days
from app.db import SessionLocal
from app.models import BankRate
from app.rate_store import record_identity
from app.schemas import BankRateOut, CurrencyHistoryOut, CurrencyStatsOut
from app.ttl_cache import TTLCache

router = APIRouter(prefix="/api/rates", tags=["rates"])


@router.get(
    "/latest",
    response_model=list[BankRateOut],
    summary="Har bir bank/mahsulot bo'yicha eng so'nggi yig'ilgan stavka/tarif",
)
def get_latest_rates(
    bank: str | None = Query(None, description="Bank kodi bo'yicha filtr, masalan \"SQB\" (/api/meta'dagi banks[].code)"),
    product_type: str | None = Query(
        None, description="Mahsulot turi bo'yicha filtr, masalan \"deposit\" (/api/meta'dagi product_types[].code)"
    ),
    segment: str | None = Query(None, description="Segment bo'yicha filtr: \"individual\" yoki \"business\""),
):
    with SessionLocal() as session:
        stmt = select(BankRate)
        if bank:
            stmt = stmt.where(BankRate.bank_code == bank)
        if product_type:
            stmt = stmt.where(BankRate.product_type == product_type)
        if segment:
            stmt = stmt.where(BankRate.segment == segment)

        rows = session.scalars(stmt).all()

        # Bir xil bank/mahsulot turi/segment kombinatsiyasini bir nechta
        # connector mustaqil to'ldirishi mumkin — nafaqat turli manbalar
        # (depozit.uz VA bankning o'z sayti), balki bitta manbaning o'zi
        # ham bir nechta connector orqali (masalan xb.uz'da har kredit
        # turi — Ipoteka, Avtokredit, ... — o'z alohida connectoriga ega).
        # Ularning fetched_at vaqti bir-biridan sal-pal farq qiladi. Shu
        # bois "eng so'nggi" har bir aniq mahsulot (record_identity(), ya'ni
        # manba+kategoriya+nom/kod+tomon) bo'yicha alohida hisoblanadi —
        # aks holda ba'zi connectorlar tasodifan oldinroq tugagani sabab
        # butunlay ko'rinmay qoladi. record_identity() "name"i bo'lmagan
        # (masalan valyuta — "code"/"side") yozuvlarni ham to'g'ri ajratadi;
        # aks holda bitta bankning barcha valyutalari bitta kalitga
        # to'planib, faqat bittasi qolib ketardi.
        latest_by_key: dict[tuple, BankRate] = {}
        for row in rows:
            key = (row.bank_code, row.product_type, row.segment, *record_identity(row.data))
            current = latest_by_key.get(key)
            if current is None or row.fetched_at > current.fetched_at:
                latest_by_key[key] = row

        return [
            {
                "bank_code": row.bank_code,
                "product_type": row.product_type,
                "segment": row.segment,
                "data": row.data,
                "fetched_at": row.fetched_at,
                "facets": offer_facets(row.product_type, row.data),
            }
            for row in latest_by_key.values()
        ]


# CBU tarixi kuniga bir marta yangilanadi, shu bois har so'rovda qayta
# yuklash shart emas — 6 soatlik TTL bilan keshlanadi.
# retry_backoff: keshda umuman ma'lumot bo'lmasa (yangi start) va cbu.uz
# bo'lmasa, har bir so'rov 20+ soniya kutib thread'ni band qilmasligi uchun
# bir muvaffaqiyatsizlikdan keyin 5 daqiqa davomida darrov rad etiladi.
# refresh_wait_seconds: birinchi (sovuq) yuklash TRACKED_CODES bo'ylab bir
# nechta so'rov qilgani uchun uzun kechishi mumkin — shu muddatgacha kutamiz,
# lekin undan uzoq emas: cbu.uz javobsiz qolganda kutuvchi thread'lar ham
# 60s'dan keyin qaytadi (nginx proxy_read_timeout'i bilan bir xil chegara).
_dynamics_cache: TTLCache[dict[str, list[dict]]] = TTLCache(
    lambda: fetch_all_histories(TRACKED_CODES),
    ttl_seconds=6 * 60 * 60,
    retry_backoff_seconds=5 * 60,
    refresh_wait_seconds=60,
    name="cbu-dynamics",
)


def _get_dynamics_histories() -> dict[str, list[dict]]:
    return _dynamics_cache.get()


@router.get(
    "/currency-stats",
    response_model=list[CurrencyStatsOut],
    summary="cbu.uz rasmiy valyuta kursi arxividan Min/O'rtacha/Max (MPL) statistikasi",
    responses={502: {"description": "cbu.uz'dan tarixiy kursni olib bo'lmadi"}},
)
def get_currency_stats(
    days: int = Query(30, description="Necha kunlik oyna (masalan 7, 30, 90, 365); 0 yoki manfiy — butun tarix"),
):
    """cbu.uz'ning rasmiy kurs dinamikasi arxividan (1994-yildan buyon
    kundalik tarix) Min / O'rtacha / Max (MPL) tahlili. `days` — necha
    kunlik oyna (masalan 7, 30, 90, 365); 0 yoki manfiy — butun tarix."""
    try:
        histories = _get_dynamics_histories()
    except Exception:
        raise HTTPException(status_code=502, detail="cbu.uz'dan tarixiy kursni olib bo'lmadi")

    window = days if days > 0 else None
    stats = []
    for code, points in histories.items():
        window_stats = stats_for_window(points, window)
        if window_stats:
            stats.append({"code": code, **window_stats})

    stats.sort(key=lambda s: s["code"])
    return stats


@router.get(
    "/currency-history",
    response_model=CurrencyHistoryOut,
    summary="Bitta valyutaning to'liq kurs tarixi (diagramma uchun)",
    responses={
        404: {"description": "Bunday valyuta topilmadi"},
        502: {"description": "cbu.uz'dan tarixiy kursni olib bo'lmadi"},
    },
)
def get_currency_history(
    code: str = Query(..., description="Valyuta kodi, masalan \"USD\" (katta-kichik harf farqi yo'q)"),
    days: int = Query(30, description="Necha kunlik oyna (masalan 7, 30, 90, 365); 0 yoki manfiy — butun tarix"),
):
    """Bitta valyuta uchun cbu.uz arxividan tanlangan davr bo'yicha
    to'liq {date, value} nuqtalar ro'yxati — katta diagramma chizish
    uchun (MPL jadvalidagi qisqartirilgan sparkline'dan farqli)."""
    try:
        histories = _get_dynamics_histories()
    except Exception:
        raise HTTPException(status_code=502, detail="cbu.uz'dan tarixiy kursni olib bo'lmadi")

    code = code.upper()
    points = histories.get(code)
    if points is None:
        raise HTTPException(status_code=404, detail="Bunday valyuta topilmadi")

    window = days if days > 0 else None
    return {"code": code, "points": window_for_days(points, window)}
