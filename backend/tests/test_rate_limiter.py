from app.rate_limiter import RateLimiter


def test_allows_requests_up_to_the_limit():
    limiter = RateLimiter(limit=2, window_seconds=3600)

    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False


def test_tracks_each_key_independently():
    limiter = RateLimiter(limit=1, window_seconds=3600)

    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is False


def test_old_hits_expire_out_of_the_window(monkeypatch):
    limiter = RateLimiter(limit=1, window_seconds=10)
    current_time = [1000.0]
    monkeypatch.setattr("app.rate_limiter.time.monotonic", lambda: current_time[0])

    assert limiter.allow("x") is True
    assert limiter.allow("x") is False

    current_time[0] += 11  # oyna (10s) dan tashqariga chiqadi
    assert limiter.allow("x") is True


def test_reset_clears_all_keys():
    limiter = RateLimiter(limit=1, window_seconds=3600)
    limiter.allow("x")
    assert limiter.allow("x") is False

    limiter.reset()

    assert limiter.allow("x") is True


def test_tracked_keys_stay_bounded_under_many_distinct_active_keys():
    # Har biri o'z oynasi hali tugamagan (demak bo'sh emas) minglab turli
    # kalitdan so'rov kelsa ham, ichki lug'at qattiq chegaradan oshmasligi
    # kerak — aks holda ko'p sonli noyob kalit bilan xotirani cheksiz
    # o'stirish (DoS) mumkin bo'lardi.
    from app.rate_limiter import _MAX_TRACKED_KEYS

    limiter = RateLimiter(limit=100, window_seconds=3600)

    for i in range(_MAX_TRACKED_KEYS + 1000):
        limiter.allow(f"key-{i}")

    assert len(limiter._hits) <= _MAX_TRACKED_KEYS


def test_concurrent_allow_and_reset_keep_invariants():
    # `reset()` `allow()` bilan parallel chaqirilganda (sync endpointlar
    # threadpool'da) hisob holati yarim aralash qolmasligi kerak: yakuniy
    # lug'at bo'sh yoki butun, kalitlar soni chegaradan oshmaydi, hech bir
    # oqim istisno olmaydi.
    import threading

    from app.rate_limiter import _MAX_TRACKED_KEYS

    limiter = RateLimiter(limit=5, window_seconds=3600)
    errors = []

    def spam():
        try:
            for i in range(200):
                limiter.allow(f"k{i % 50}")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def resetter():
        try:
            for _ in range(50):
                limiter.reset()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=spam) for _ in range(8)] + [
        threading.Thread(target=resetter) for _ in range(2)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(limiter._hits) <= _MAX_TRACKED_KEYS


def test_oldest_key_evicted_first_when_bound_exceeded():
    from app.rate_limiter import _MAX_TRACKED_KEYS

    limiter = RateLimiter(limit=100, window_seconds=3600)

    for i in range(_MAX_TRACKED_KEYS):
        limiter.allow(f"key-{i}")
    assert "key-0" in limiter._hits

    # Chegaradan bittaga oshirib, eng eski kalit chiqarib tashlanishini
    # tekshiramiz.
    limiter.allow("one-more")

    assert "key-0" not in limiter._hits
    assert "one-more" in limiter._hits


def test_retry_after_counts_down_to_the_oldest_hit(monkeypatch):
    limiter = RateLimiter(limit=2, window_seconds=10)
    current_time = [1000.0]
    monkeypatch.setattr("app.rate_limiter.time.monotonic", lambda: current_time[0])

    assert limiter.allow("x") is True          # hit @ 1000
    current_time[0] += 4
    assert limiter.allow("x") is True          # hit @ 1004 — kovak to'ldi
    assert limiter.allow("x") is False
    assert limiter.retry_after("x") == 6       # 10 - (1004-1000)

    current_time[0] = 1009.5  # eng eski hitga 0.5s qoldi → yuqoriga yaxlitlanadi
    assert limiter.retry_after("x") == 1

    current_time[0] = 1010.0  # age aynan window: `allow()` hali sanaydi → 1s
    assert limiter.retry_after("x") == 1
    assert limiter.allow("x") is False

    current_time[0] = 1010.5  # eng eski hit endi rostdan oyna tashqarisida
    assert limiter.retry_after("x") == 0
    assert limiter.allow("x") is True


def test_retry_after_is_zero_for_unknown_key():
    limiter = RateLimiter(limit=1, window_seconds=10)

    assert limiter.retry_after("hech_qachon_kelmagan") == 0


def test_refund_gives_a_charged_attempt_back():
    limiter = RateLimiter(limit=1, window_seconds=3600)

    assert limiter.allow("x") is True     # hisobga olindi
    assert limiter.allow("x") is False    # kovak to'lgan
    assert limiter.refund("x") is True    # sarflangan urinish qaytdi
    assert limiter.allow("x") is True     # qaytarilgan o'rin darhol ishlatildi
    assert limiter.allow("x") is False    # ...va kovak yana to'ldi
    assert limiter.refund("x") is True    # bu safar shu urinish qaytadi
    assert limiter.refund("x") is False   # kovak bo'sh — manfiyga ketmaydi


def test_refund_ignores_hits_that_already_left_the_window(monkeypatch):
    limiter = RateLimiter(limit=2, window_seconds=10)
    current_time = [1000.0]
    monkeypatch.setattr("app.rate_limiter.time.monotonic", lambda: current_time[0])

    assert limiter.allow("x") is True
    current_time[0] += 11  # yagona hit oyna tashqarisiga chiqdi
    assert limiter.refund("x") is False
    # Oyna tashqarisidagi hitlar qaytarilmaydi, lekin hisobdan tushiriladi:
    # kovak haqiqatan bo'sh — keyingi ikki urinish ham o'tadi.
    assert limiter.allow("x") is True
    assert limiter.allow("x") is True


# --- `refund()`: kovakni FAQAT yig'-tirik muvaffaqiyatsizlik to'ldiradi -------
# Kirish eshiklarida muvaffaqiyatli (yoki tashqi muhit>xatosi) urinish qaytariladi:
# aks holda bitta NAT chiqish IPidagi ofis qonuniy kirishlar bilan o'zini soatlab
# bloqlab qo'yardi.


def test_refund_on_unknown_key_is_harmless():
    limiter = RateLimiter(limit=2, window_seconds=3600)

    assert limiter.refund("hech_qachon_kelmagan") is False


def test_refund_returns_the_newest_hit_so_failures_stay_counted(monkeypatch):
    # LIFO: qaytariladigan urinish — shu so'rovning o'zi (eng yangi hit).
    # Undan oldingi muvaffaqiyatsiz urinishlar kovakda qolishi shart, aks
    # holda bitta to'g'ri parol hujumni "yuvib" tashlardi.
    limiter = RateLimiter(limit=10, window_seconds=10)
    current_time = [1000.0]
    monkeypatch.setattr("app.rate_limiter.time.monotonic", lambda: current_time[0])

    assert limiter.allow("x") is True  # @1000 — masalan yaroqsiz code (401)
    current_time[0] = 1001.0
    assert limiter.allow("x") is True  # @1001 — yana bir 401
    current_time[0] = 1002.0
    assert limiter.allow("x") is True  # @1002 — muvaffaqiyatli kirish

    assert limiter.refund("x") is True
    assert list(limiter._hits["x"]) == [1000.0, 1001.0]


def test_concurrent_refund_keeps_the_counter_sane():
    # Sync endpointlar threadpool'da — `refund()` ham `allow()` bilan bir lock
    # ostida bo'lishi kerak: yakuniy hisob hech qachon manfiy yola limitdan
    # oshib ketmasligi, hech bir oqim istisno olmasligi shart.
    import threading

    limiter = RateLimiter(limit=4, window_seconds=3600)
    errors = []

    def worker():
        try:
            for _ in range(300):
                if limiter.allow("k"):
                    limiter.refund("k")
        except Exception as exc:  # noqa: BLE001 - har qanday istisno bu yerda xato
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(limiter._hits["k"]) <= limiter.limit
