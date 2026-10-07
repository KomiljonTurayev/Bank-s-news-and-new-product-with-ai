import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from app import db, outbound, schedule
from app.config import FETCH_INTERVAL_MINUTES, SCRAPE_TIMES
from app.connectors.registry import CONNECTORS
from app.models import BankRate

logger = logging.getLogger(__name__)


def _run_one(connector) -> bool:
    """Bitta connectorni ishga tushiradi. Xatosi ichida qoladi — bitta
    manbaning nosozligi siklni to'xtatmasligi kerak. Qaytarma qiymat:
    muvaffaqiyatli bo'ldimi-yo'qmi."""
    try:
        result = connector.run()
        logger.info(
            "%s (%s): %d ta yozuv (%d yangi, %d o'zgarishsiz)",
            connector.bank_code, connector.product_type,
            result.total, result.inserted, result.unchanged,
        )
        return True
    except Exception:
        logger.exception("%s connectorida xatolik", connector.bank_code)
        return False


_MAX_WORKERS = 8

# Jadval rejimidagi watchdog ustki chegarasi. O'tishlar orasi soatlab
# bo'lishi mumkin, lekin osilib qolgan sikl keyingi soatgacha "hammasi
# joyida" bo'lib turmasin: u lokolni ushlab turgani uchun keyingi rejadagi
# tikish ham o'tkazib yuboriladi. 54 daqiqa interval rejimining amalchi
# chegarasini (60×0.9) saqlaydi — normal sikl bir necha daqiqa.
_SCHEDULED_CYCLE_CAP_SECONDS = 54 * 60


def _cycle_deadline_seconds() -> int:
    """Bir siklning eng uzoq kutish chegarasi.

    Keyingi tikkadan oldin qaytish shart: aks holda APScheduler
    (`max_instances=1`) navbatdagi sikllarni chop etib yuboradi va bitta
    osilib qolgan manba kurs yangilanishlarini cheksiz to'xtatib qo'yadi.
    Jadval rejimida bog'lovchi masofa — eng QISQA o'tish oralig'i (sikl
    o'sha tikkaga yetib qaytishi kerak), lekin u ham ustki chegaraga
    qadariladi: osiq sikl orada tikkalar uzoq bo'lsa ham foyda bermaydi."""
    if SCRAPE_TIMES:
        gap_seconds = schedule.min_gap_minutes(SCRAPE_TIMES) * 60
        return max(60, min(int(gap_seconds * 0.9), _SCHEDULED_CYCLE_CAP_SECONDS))
    return max(60, int(FETCH_INTERVAL_MINUTES * 60 * 0.9))


# Sikllar bir-biri bilan ustma-ust tushmasin: startapdagi birinchi skreyping
# hali ketayotgan bo'lsa, jadvalning birinchi tikishi keraksiz ikkinchi to'lqin
# emas, chop etishga loyiq voqea bo'lishi kerak.
_cycle_lock = threading.Lock()


def run_all_connectors() -> None:
    # Faollik darvozasi (app/outbound.py): sikl tashqi manbalarga chiqishga
    # ruxsat berilmagan vaqtda tushsa, hech qanday so'rov ketmaydi — bu
    # "bajarildi, natija bo'sh" emas, bu "hozir skreyping qilish kerak emas".
    # Job'ning o'zi to'xtatilmaydi: oynani surish uchun jadvalni qayta
    # qurish (yoki qayta ishga tushirish) shart emas, bitta sozlama yetadi.
    window = outbound.active_window()
    now = datetime.now(timezone.utc)
    if not window.contains(now):
        logger.info(
            "skreyping sikli o'tkazib yuborildi — faollik oynasi %s (Toshkent vaqti) tashqarisida, "
            "tashqi manbalarga murojaat qilinmadi", window,
        )
        return

    # Har bir connector mustaqil tarmoq so'rovi va o'z DB sessiyasi bilan
    # ishlaydi — ketma-ket emas, parallel ishga tushirish umumiy kutish
    # vaqtini bir nechta ulanish orasidagi eng sekinigacha qisqartiradi.
    # Worker'lar soni connectorlar soniga tenglashtirilmaydi — bir nechta
    # Playwright-asosidagi connector (har biri o'z headless Chromium'ini
    # ochadi) bir vaqtda ishga tushsa, resurs tanqisligi sabab bir-birini
    # timeout qilib qo'yishi mumkin edi.
    if not _cycle_lock.acquire(blocking=False):
        logger.warning("oldingi skreyping sikli tugamagan — bu sikl o'tkazib yuborildi")
        return
    try:
        deadline = _cycle_deadline_seconds()
        pool = ThreadPoolExecutor(
            max_workers=min(len(CONNECTORS), _MAX_WORKERS), thread_name_prefix="scrape"
        )
        try:
            futures = {pool.submit(_run_one, connector): connector for connector in CONNECTORS}
            done, stuck = wait(futures, timeout=deadline)
        finally:
            # Muddatdan keyin kutish fayda bermaydi: har bir so'rovning o'z
            # transport timeouti bor, osilib qolgan oqim erinda-yu kech
            # tugaydi — sikl esa qaytib, navbatdagi tikishga yo'l ochadi.
            #
            # `cancel_futures=True` shu yerda hal qiluvchi: navbatda turgan
            # connectorlarni bekor qilmasak, ular sikl "tugagandan" keyin ham
            # ketaveradi va navbatdagi sikl ustiga chiqadi. Manbalar sekin
            # holatda har bir sikl qoldiq qatorni orttirib, cheksiz o'sib
            # ketadigan yuk berardi. Bekor qilingan banklar ma'lumoti keyingi
            # tikilda o'qiladi.
            pool.shutdown(wait=False, cancel_futures=True)

        if stuck:
            # Navbatda qolib bekor qilinganlar "javob bermadi" emas — ularning
            # so'rovi umuman boshlanmagan. Farqi monitoring uchun muhim: birin-
            # chisi manba nosozligi, ikkinchisi bizning yukni cheklaganimiz.
            never_started = sum(1 for future in futures if future.cancelled())
            logger.error(
                "skreyping sikli %d soniyada tugamadi — %d ta manba natija bermadi "
                "(%d tasiga navbat yetmadi, keyingi siklda o'qiladi): %s",
                deadline, len(stuck), never_started,
                ", ".join(sorted(futures[f].bank_code for f in stuck)),
            )
        succeeded = sum(bool(f.result()) for f in done if f.exception() is None)
        logger.info(
            "skreyping sikli yakunlandi: %d muvaffaqiyatli, %d xato, %d tugamagan (%d manba)",
            succeeded, len(done) - succeeded, len(stuck), len(futures),
        )
    finally:
        _cycle_lock.release()


def _latest_success() -> datetime | None:
    """Bazadagi eng so'nggi muvaffaqiyatli yig'ish vaqti (SQLite naive
    qaytarsa UTC hisoblanadi — app/routers/meta.py:_as_utc konvensiyasi,
    `schedule.missed_fire` naive'ni o'zi UTC deb oladi)."""
    with db.SessionLocal() as session:
        return session.scalar(select(func.max(BankRate.fetched_at)))


def startup_scrape() -> bool:
    """Protsess ishga tushgandagi skreyping. Qaytarma: sikl ishga tushdi_mi.

    Kunlik jadval yoqiqda istalgan vaqtda bo'ladigan boot "reja tashqarisidagi
    tashqi chiqish" bo'lmasligi kerak: faqat o'tkazib yuborilgan soat bo'lsa
    qoplab o'ladi (crash-restart shu holatga kiradi — sikl yarim qolsa oxirgi
    muvaffaqiyat soatdan oldin qolgan). Aks holda jarayon shunchaki keyingi
    soatni kutadi. Ikkala holda ham run_all_connectors() ichidagi faollik
    darvozasi (app/outbound.py) o'rinida qoladi — bu funksiya siyosatni
    aylanib o'tmaydi, faqat qachon urilishini hal qiladi."""
    if not SCRAPE_TIMES:
        run_all_connectors()
        return True
    if schedule.missed_fire(SCRAPE_TIMES, _latest_success(), grace_minutes=0):
        logger.info(
            "startap: %s soatidagi skreyping o'tkazib yuborilgan — qoplab olinadi",
            schedule.last_passed_fire(SCRAPE_TIMES),
        )
        run_all_connectors()
        return True
    logger.info(
        "startap: jadval bo'yicha hammasi o'z vaqtida — keyingi soat %s (Toshkent) kutilmoqda",
        schedule.next_fire(SCRAPE_TIMES),
    )
    return False


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # max_instances=1 + coalesce: eski qoida — sikl davom etsa, navbatdagi
    # tikish ustma-ust boshlanmaydi (resurs va DB lock uchun o'zaro kurash) va
    # o'tkazib yuborilgan bir nechta tikish bir vaqtda "qarz" bo'lib qaytmaydi.
    if SCRAPE_TIMES:
        # Kunlik jadval (talab: kuniga aynan 2 tortish — 09:00 va 14:00).
        # Har bir soatga alohida cron job: bitta CronTrigger Minute=0,
        # Hour=9,14 ni ifodalaydi, lekin "09:00,14:30" kabi juftliklarni
        # emas — minut per soat yozuvi general yechim bermaydi.
        # Vaqt mintaqasi Toshkent (UTC+5, yoz/qish siljishi yo'q): talab
        # mahalliy soat bilan aytilgan, konteyner UTC'da yurs ham buzilmasin.
        # Process o'sha damda o'lik bo'lsa cron o'tmishni qayta ishla-
        # MAYDI — buning uchun startup_scrape() bor.
        for scrape_time in SCRAPE_TIMES:
            scheduler.add_job(
                run_all_connectors,
                CronTrigger(
                    hour=scrape_time.hour, minute=scrape_time.minute,
                    timezone=schedule.TASHKENT,
                ),
                id=f"scrape_{scrape_time.hour:02d}{scrape_time.minute:02d}",
                max_instances=1, coalesce=True,
            )
    else:
        scheduler.add_job(
            run_all_connectors, "interval", minutes=FETCH_INTERVAL_MINUTES,
            max_instances=1, coalesce=True,
        )
    scheduler.start()
    return scheduler
