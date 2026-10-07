"""`/api/meta`, `/api/health` (ma'lumot yangiligi), `/api/meta/sources`
(tashqi manbalar holati) va `/actuator/health` (K8s-uslubidagi DB'siz liveness
probe) — statik ma'lumotnomalar va monitoring."""

import os
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app import schedule
from app.banks import BANKS, PRODUCT_TYPES, SEGMENTS
from app.config import FETCH_INTERVAL_MINUTES, SCRAPE_TIMES
from app.connectors.registry import CONNECTORS
from app.db import SessionLocal
from app.models import BankRate
from app.outbound import active_window, policy_snapshot
from app.resilience import breaker_statuses
from app.schemas import HealthOut, LivenessOut, MetaOut, SourceFreshnessOut, SourcesStatusOut

router = APIRouter(tags=["meta"])

# Chegaralar DARRA HOLDA (so'rov paytida) hisoblanadi: jadval/interval
# sozlamalari modda importi paytida muzlasa, testi soatlarni almashtira
# olmas edi (har ikki rejim bir jarayonda sinash imkonsiz bo'lardi).
#
# Interval rejimida scheduler har FETCH_INTERVAL_MINUTES'da ishga tushadi
# (app/scheduler.py); tarmoq/sayt o'zgarishi sabab bitta-ikkita connector
# muvaffaqiyatsiz tugashi normal, shu bois "stale" chegarasi 1x emas 2x
# oraliq qilib olingan — vaqtincha kechikishni yolg'on ogohlantirishga
# aylantirmaslik uchun. Kunlik jadval rejimida (SCRAPE_TIMES) global status
# shu skalyar bilan EMAS, `schedule.missed_fire` predicate'i bilan
# hisoblanadi (quyida) — 14:00→ertaga 09:00 oralig'i normal holat, uni
# "2× oraliq" geometriyasi bilmaydi, jadvalning o'zi esa biladi.
_STALE_GRACE_MINUTES = 45
# Jadval rejimida "o'tkazib yuborildi" hukmi tikish soatidan nech daqiqa
# o'tgach yoqiladi: sikl o'zi bir necha daqiqadan kech tugamaydi (watchdog
# chegarasi ~54 daq), lekin 09:01'da hali ishlayotgan siklga stale deyish
# ham noto'g'ri. 45 daqiqa — navbatdagi tikishdan ancha oldin, normal
# sikldan esa yetarlicha kech.


def _stale_threshold_minutes(times: list) -> int:
    """Interval rejimining "eskirgan" chegarasi (jadval rejimida statusga
    ta'siri yo'q, faqat javob skalyari va — pastdagi izohda — manbalar
    holisi uchun ishlatiladi)."""
    if times:
        return 2 * schedule.max_gap_minutes(times)
    return 2 * FETCH_INTERVAL_MINUTES


def _monitor_idle_limit_minutes(times: list) -> int:
    """`stale_after_minutes` javob skalyari: monitoring shu muddat jimlikni
    NORMAL holat deb bilsin (jadval rejimida — eng uzon reja oralig'i + grace;
    14:00→09:00 tuni "ma'lumot to'xtadi" emas)."""
    if times:
        return schedule.max_gap_minutes(times) + _STALE_GRACE_MINUTES
    return _stale_threshold_minutes(times)
# Javobdagi nomlar ro'yxati cheklangan: 49 bankning hammasi uzilganda
# monitoring javobini kilobaytlik qilishning hojati yo'q, holat baribir
# son bilan ko'rinadi.
_STALE_SAMPLE_LIMIT = 10


def _as_utc(moment: datetime | None) -> datetime | None:
    """SQLite (standart DB) DateTime(timezone=True) ustunidan ko'pincha
    tzinfo'siz qiymat qaytaradi (Postgres'dan farqli) — connectorlar doim
    UTC yozgani uchun (app/connectors/base.py) shu deb tiklaymiz, aks holda
    aware/naive solishtirish TypeError beradi."""
    if moment is not None and moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


# Agregator konektorlar (depozit.uz, uzse.uz — app/connectors/depozit_uz.py,
# uzse.py, depozit_tables.py) har yozuvni O'Z banki kodi ostida yozadi, registrdagi
# manzili esa shu belgi. Ularning manzilida bazada hech qachon qator bo'lmaydi,
# shu sabab "hech qachon yangilanmagan" deb ko'rsatish monitoringni BIRINCHI
# kundan yolg'on ogohlantirishga o'rgatardi (bunday manzillarning o'zi hech
# qachon to'lmaydi, holisi esa baribir rost bo'lsa ham).
_AGGREGATED_CODE = "AGGREGATED"


def _source_addresses() -> list[tuple[str, str, str]]:
    """Konektorlar o'zi yozadigan noyob manzillar (bank/tur/segment).

    Noyobligi shart: bir bankning bir necha sahifasi bitta manzilga yozadi
    (ORIENT krediti 6 URL, XB krediti 4 ta), bazada esa bitta guruh bor —
    takrorlansa `stale` soni va `sample` ro'yxati shishib, necha manba o'lganini
    o'qib bo'lmaydi."""
    addresses: dict[tuple[str, str, str], None] = {}
    for source in CONNECTORS:
        key = (source.bank_code, source.product_type, source.segment)
        if key[0] != _AGGREGATED_CODE:
            addresses.setdefault(key)
    return list(addresses)


def _source_freshness(window, now: datetime, rows, times: list) -> SourceFreshnessOut:
    """_manbalar kesimida_ yangilikni hisoblaydi.

    Global `max(fetched_at)` bitta tirik konektor bilan qolganlarining
    o'limini yashiradi — monitoring "hammasi ok" deb uyquga ketadi. Shu
    sabab har bir manzilning oxirgi yozuvi alohida ko'riladi; bazada umuman
    yozuvi bo'lmagan manba ham yangilanmayapti hisoblanadi.

    Jadval rejimida mezon — "o'tgan tikish soatida bu manba yozildi_mi"
    (missed_fire, grace bilan): kuniga 2 tortishda "2× oraliq" chegarasi
    ~38 soatni tark etardi, bugun 09:00'da o'lgan sayt 4 kundan oldin
    ko'rinmas edi. Interval rejimida eski oyna-geometriyasi qoladi."""
    newest = {(bank_code, product_type, segment): _as_utc(fetched_at)
              for bank_code, product_type, segment, fetched_at in rows}
    threshold = _stale_threshold_minutes(times) * 60
    addresses = _source_addresses()
    stale: list[tuple[float, str]] = []
    for key in addresses:
        fetched_at = newest.get(key)
        name = f"{key[0]}/{key[1]}/{key[2]}"
        if times:
            if schedule.missed_fire(times, fetched_at, now, grace_minutes=_STALE_GRACE_MINUTES):
                # Jadvalda tartib — kim KECHA o'tgan tikishni qaytargani
                # emas, "shu soatda yo'q"lar bir xil og'irlikda.
                stale.append((0.0 if fetched_at is not None else float("inf"), name))
            continue
        if fetched_at is None:
            # `inf` — bazada hech qachon yozuv bo'lmagan; eng yomon holat,
            # shu sabab ro'yxatda birinchi bo'ladi.
            stale.append((float("inf"), name))
            continue
        idle = window.open_seconds_between(fetched_at, now)
        if idle > threshold:
            stale.append((idle, name))
    stale.sort(key=lambda item: -item[0])
    return SourceFreshnessOut(
        total=len(addresses),
        stale=len(stale),
        sample=[name for _, name in stale[:_STALE_SAMPLE_LIMIT]],
    )



@router.get(
    "/api/meta",
    response_model=MetaOut,
    summary="Banklar, mahsulot turlari va segmentlar ro'yxati",
)
def get_meta():
    return {"banks": BANKS, "product_types": PRODUCT_TYPES, "segments": SEGMENTS}


@router.get(
    "/api/health",
    response_model=HealthOut,
    summary="Fon rejimidagi ma'lumot yig'ish holati — tashqi monitoring uchun",
)
def get_health():
    """Tashqi monitoring xizmati (cron+curl va h.k.) shu endpointni davriy
    so'rab, scheduler haqiqatan ishlab turganini — qo'lda tekshirmasdan —
    kuzatishi mumkin.

    Javob bazaning ichki holatini (oxirgi yangilanish vaqti, interval) va
    obraz commit'ini ko'rsatgani uchun `Authorization: Bearer` talab
    qilinadi. Sana sarlavhasi yoki so'rov soni ham yashirilmaydi — shuning
    uchun monitor ushbu sarlavhani yubora olishi kerak; avtorizatsiyani
    sozlab bo'lmaydigan monitorlar uchun `/actuator/health` ochiq.

    `status` BUTUN tizim darajasi (eng so'nggi yozuv). Bitta tirik manba
    qolganlarining uzilganini yashirmasin uchun manba-ma'noda holat `sources`
    blokkida alohida beriladi; `status`ning ma'nosi esa ataylab eskiicha —
    monitor unda "ma'lumot to'xtadi"ni ko'radi, ayrim bank sayti uzilganda
    avtomatik ogohlantirish toshib ketmasin (manbalardan biri har doim javob
    bermasligi normal holat)."""
    with SessionLocal() as session:
        last_fetch_at = session.scalar(select(func.max(BankRate.fetched_at)))
        # Har bir manbaning oxirgi yozuvi alohida o'qiladi: global max
        # bir tirik manba ortida qolganlarni butunlay ko'rinmas qiladi.
        per_source = session.execute(
            select(
                BankRate.bank_code,
                BankRate.product_type,
                BankRate.segment,
                func.max(BankRate.fetched_at),
            ).group_by(BankRate.bank_code, BankRate.product_type, BankRate.segment)
        ).all()
    last_fetch_at = _as_utc(last_fetch_at)

    # Yagona soat manbai — app/schedule.utc_now: testlar shu nomni patch
    # qilib butun health mantig'ini devor soatidan uzadi.
    now = schedule.utc_now()
    # Rejim SO'ROV paytida o'qiladi (modda konstantasi emas): jadval va
    # interval rejimlarining ikkalasi ham bir jarayonda, monkeypatch bilan
    # sinovdan o'tishi uchun.
    times = SCRAPE_TIMES
    window = active_window()
    # "Qancha vaqtdan beri yangilanmagan" deb interval rejimida faqat
    # skreyping oynasi ICHIDA o'tgan soniyalar hisoblanadi (app/outbound.py):
    # oyna tashqarisida skreyping bo'lmaydi, aks holda monitor har kuni
    # oynaning birinchi tekshiruvida asossiz "stale" deb ogohlantirardi.
    # Haqiqiy uzilish bu ayirishdan keyin ham ko'rinadi — kunlar bo'yi oyna
    # ichida ham yangilanmasa, qolgan soniyalar baribir chegaradan oshadi.
    if times:
        # Jadval rejimi: "o'sha soatda ish tugamadi" savolining javobi
        # bazadagi oxirgi muvaffaqiyatni O'TGAN tikish soati bilan
        # solishtirishdan chiqadi (grace bilan — sikl endigina tugayotgan
        # bo'lishi mumkin). Oyna/interval geometriyasi bu rejimda kerak
        # emas: jadvalning o'zi qachon yangilanish KUTISHNI biladi.
        is_stale = schedule.missed_fire(
            times, last_fetch_at, now, grace_minutes=_STALE_GRACE_MINUTES
        )
    else:
        idle_seconds = window.open_seconds_between(last_fetch_at, now) if last_fetch_at else 0.0
        is_stale = last_fetch_at is None or idle_seconds > _stale_threshold_minutes(times) * 60
    return {
        "status": "stale" if is_stale else "ok",
        "last_fetch_at": last_fetch_at,
        "fetch_interval_minutes": FETCH_INTERVAL_MINUTES,
        "stale_after_minutes": _monitor_idle_limit_minutes(times),
        "scrape_times": [t.strftime("%H:%M") for t in times],
        "next_fire_at": schedule.next_fire(times, now),
        "sources": _source_freshness(window, now, per_source, times),
        "scrape_window": str(window),
        "scrape_active_now": window.contains(now),
        # Obraz qaysi commit'dan yig'ilgani (Dockerfile ARG GIT_COMMIT). Joyida
        # o'qiladi: modda darajasidagi konstanta import payti muzlaydi va
        # sozlangan muhitda eskirgan qiymatni ko'rsatar edi.
        "git_commit": os.environ.get("GIT_COMMIT", "dev"),
    }


@router.get(
    "/actuator/health",
    response_model=LivenessOut,
    summary="Kubernetes readiness/liveness probe — DB'ga urmaydi",
)
def get_actuator_health():
    """Spring Boot konvensiyasi: k8s probe'lari shu yo'lni kutadi.

    Bu yo'l DB'ga UMUMAN urilmaydi. Probe bazaga bog'lansa, Postgres bir
    lahzaga istalmaganda pod hech qachon Ready bo'lmaydi, Service'ning tayyor
    endpoint'i qolmaydi va edge nginx butun sayt bo'ylab HTML 502 qaytaradi
    (2026-09-21 staging 502'i shu zanjir bilan o'lchandi). Ma'lumot
    yangiligi/DB holati monitoringi uchun — `/api/health`.
    """
    return {"status": "alive"}


@router.get(
    "/api/meta/sources",
    response_model=SourcesStatusOut,
    summary="Tashqi manbalar holati — qaysi sayt hozir chetda",
)
def get_sources_status():
    """Bitta manbaning nosozligi loyihani to'xtatmaydi, shu bois bu yerda
    "biror manba ochiq" = `degraded`, xato EMAS.

    Skreyping sekinlashganda yoki ma'lumot to'xtaganda birinchi savol —
    "manbalar javob bermayaptimi, yoki biz ularni chetga surib qo'ydikmi?" —
    shu yerdan javoblanadi: `sources` host bo'yicha breaker holatini,
    `scrape_window` va `min_host_interval_seconds` esa tashqariga chiqish
    siyosatini (app/outbound.py) ko'rsatadi.

    Ro'yxat faqat so'ralgan hostlarni oladi — birorta so'rov bo'lmagan bank
    bu yerda ko'rinmaydi, bu uning nosozligi emas."""
    statuses = breaker_statuses()
    open_sources = sum(1 for status in statuses if status["open"])
    return {
        "status": "degraded" if open_sources else "ok",
        "open_sources": open_sources,
        "sources": statuses,
        **policy_snapshot(),
    }
