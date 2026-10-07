from app.product_analysis import analyze_product, extract_rate_percent, _infer_credit_category


def test_extract_rate_percent_finds_percent_field():
    assert extract_rate_percent({"Foiz stavkasi": "22%"}) == 22.0


def test_extract_rate_percent_handles_comma_decimal():
    assert extract_rate_percent({"rate": "21,5%"}) == 21.5


def test_extract_rate_percent_none_when_no_percent_field():
    assert extract_rate_percent({"name": "Omonat"}) is None


def test_extract_rate_percent_prefers_foiz_stavka_field_over_earlier_percent_field():
    # BRB'da "Miqdori: Kontraktning 100% gacha" haqiqiy "Foiz stavkasi"dan
    # (14%) OLDIN keladi — naiv "birinchi % maydoni" mantig'i noto'g'ri
    # 100% ni stavka deb hisoblagan edi.
    data = {"Miqdori": "Kontraktning 100% gacha", "Foiz stavkasi": "14%", "Muddati": "7 yilgacha"}
    assert extract_rate_percent(data) == 14.0


def test_extract_rate_percent_falls_back_when_no_foiz_stavka_key():
    # Nomida "6%" bo'lgan omonat kabi — kalitida "foiz"/"stavka" so'zi
    # yo'q, lekin baribir yagona foizli maydon shu.
    assert extract_rate_percent({"name": "Zor 6%"}) == 6.0


def insert_rate(session_factory, product_type, data, bank_code="SQB"):
    from datetime import datetime, timezone

    from app.models import BankRate

    with session_factory() as session:
        session.add(BankRate(bank_code=bank_code, product_type=product_type, segment="individual", data=data, fetched_at=datetime.now(timezone.utc)))
        session.commit()


def test_analyze_product_scores_deposit_higher_rate_as_better(session_factory):
    insert_rate(session_factory, "deposit", {"name": "A", "Foiz stavkasi": "20%"})
    insert_rate(session_factory, "deposit", {"name": "B", "Foiz stavkasi": "22%"})

    with session_factory() as session:
        result = analyze_product("deposit", 24.0, session)

    assert result["market_count"] == 2
    assert result["market_min"] == 20.0
    assert result["market_max"] == 22.0
    assert result["score"] == 100
    assert result["strengths"]
    assert not result["cautions"]


def test_analyze_product_scores_credit_lower_rate_as_better(session_factory):
    insert_rate(session_factory, "credit", {"name": "A", "Foiz stavkasi": "20%"})
    insert_rate(session_factory, "credit", {"name": "B", "Foiz stavkasi": "22%"})

    with session_factory() as session:
        result = analyze_product("credit", 18.0, session)

    assert result["score"] == 100
    assert result["strengths"]


def test_analyze_product_flags_uncompetitive_rate(session_factory):
    insert_rate(session_factory, "deposit", {"name": "A", "Foiz stavkasi": "25%"})
    insert_rate(session_factory, "deposit", {"name": "B", "Foiz stavkasi": "26%"})

    with session_factory() as session:
        result = analyze_product("deposit", 10.0, session)

    assert result["score"] == 0
    assert result["cautions"]
    assert not result["strengths"]


def test_analyze_product_no_market_data(session_factory):
    with session_factory() as session:
        result = analyze_product("investment", 15.0, session)

    assert result["market_count"] == 0
    assert result["score"] is None
    assert result["market_sample"] == []


def test_analyze_product_market_sample_ranks_best_first_per_bank(session_factory):
    insert_rate(session_factory, "deposit", {"name": "A", "Foiz stavkasi": "18%"}, bank_code="SQB")
    insert_rate(session_factory, "deposit", {"name": "B", "Foiz stavkasi": "22%", "url": "https://sqb.uz/b"}, bank_code="SQB")
    insert_rate(session_factory, "deposit", {"name": "C", "Foiz stavkasi": "20%"}, bank_code="AGRO")

    with session_factory() as session:
        result = analyze_product("deposit", 24.0, session)

    sample = result["market_sample"]
    assert len(sample) == 2
    assert sample[0]["bank_code"] == "SQB"
    assert sample[0]["rate"] == 22.0
    assert sample[1]["bank_code"] == "AGRO"
    assert sample[1]["rate"] == 20.0


def test_analyze_product_market_sample_includes_source_url_of_best_offer(session_factory):
    # Diagrammada bankni bosganda aynan shu (eng maqbul) taklifning
    # havolasiga o'tish uchun — eski (yomonroq) yozuvning emas.
    insert_rate(session_factory, "deposit", {"name": "A", "Foiz stavkasi": "18%", "url": "https://sqb.uz/a"}, bank_code="SQB")
    insert_rate(session_factory, "deposit", {"name": "B", "Foiz stavkasi": "22%", "url": "https://sqb.uz/b"}, bank_code="SQB")

    with session_factory() as session:
        result = analyze_product("deposit", 24.0, session)

    assert result["market_sample"][0]["url"] == "https://sqb.uz/b"


def test_infer_credit_category_matches_known_keywords():
    assert _infer_credit_category("Ipoteka eko") == "Ipoteka"
    assert _infer_credit_category("Onlayn Avtokredit") == "Avtokredit"
    assert _infer_credit_category("Ta'lim krediti") == "Ta'lim krediti"
    assert _infer_credit_category("Onlayn overdraft") == "Overdraft"
    assert _infer_credit_category("Mikroqarz 2.6") == "Mikroqarz"


def test_infer_credit_category_matches_consumer_credit_keyword():
    assert _infer_credit_category("Oson iste'mol krediti") == "Iste'mol krediti"


def test_infer_credit_category_returns_none_for_brand_names_without_a_keyword():
    # "ADM Global I" kabi brend nomli aksiya mahsulotlari — bular
    # ko'pincha avtokredit bo'lsa-da, umumiy kalit so'zsiz — "Iste'mol
    # krediti" deb noto'g'ri taxmin qilinmasligi kerak (masalan aksiyaviy
    # 0% stavkasi haqiqiy iste'mol krediti sifatida ko'rsatilib qolmasin).
    assert _infer_credit_category("ADM Global I") is None
    assert _infer_credit_category("Yashil makon") is None


def test_infer_credit_category_returns_none_for_empty_name():
    assert _infer_credit_category(None) is None
    assert _infer_credit_category("") is None


def test_analyze_product_market_sample_infers_category_for_official_site_rows_without_one(session_factory):
    # Rasmiy sayt connectorlari (masalan Asakabank) "category" maydonini
    # to'ldirmaydi — depozit.uz'dan farqli, ularda har bir kategoriya
    # uchun alohida URL yo'q. Shunday bo'lsa-da, mahsulot nomidan
    # kategoriya taxmin qilinib, depozit.uz'dagi (kategoriyasi aniq)
    # taklifdan ustun qo'yilishi kerak.
    insert_rate(
        session_factory, "credit",
        {"name": "Aggregator taklifi", "category": "Iste'mol krediti", "Foiz stavkasi": "10%",
         "source": "depozit.uz", "url": "https://depozit.uz/x"},
        bank_code="ASAKA",
    )
    insert_rate(
        session_factory, "credit",
        {"name": "Iste'mol krediti", "Foiz stavkasi": "19.5%", "source": "asakabank.uz", "url": "https://asakabank.uz/x"},
        bank_code="ASAKA",
    )

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session, category="Iste'mol krediti")

    sample = result["market_sample"]
    assert len(sample) == 1
    assert sample[0]["rate"] == 19.5
    assert sample[0]["url"] == "https://asakabank.uz/x"


def test_analyze_product_market_sample_does_not_leak_unclassified_promo_rows_into_a_category(session_factory):
    # Haqiqiy topilgan xato: Asakabankning rasmiy saytidagi "ADM Global I"
    # aslida 0% aksiyali AVTOKREDIT, lekin nomida hech qanday kalit so'z
    # yo'q. Avvalgi (fallback bilan) mantiq buni "Iste'mol krediti" deb
    # noto'g'ri taxmin qilib, uning aksiyaviy 0% stavkasini shu
    # kategoriyadagi eng "raqobatbardosh" taklif sifatida ko'rsatib
    # qo'yayotgan edi.
    insert_rate(
        session_factory, "credit",
        {"name": "ADM Global I", "Foiz stavkasi": "0 % dan", "source": "asakabank.uz", "url": "https://asakabank.uz/x"},
        bank_code="ASAKA",
    )
    insert_rate(
        session_factory, "credit",
        {"name": "Onlayn iste'mol krediti", "category": "Iste'mol krediti", "Foiz stavkasi": "22%",
         "source": "depozit.uz", "url": "https://depozit.uz/x"},
        bank_code="ASAKA",
    )

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session, category="Iste'mol krediti")

    sample = result["market_sample"]
    assert len(sample) == 1
    assert sample[0]["rate"] == 22.0
    assert sample[0]["url"] == "https://depozit.uz/x"


def test_analyze_product_market_sample_prefers_official_source_over_depozit_uz(session_factory):
    # Bir xil bank uchun ham depozit.uz agregatoridan, ham bankning o'z
    # rasmiy saytidan yozuv kelgan bo'lsa — depozit.uz'dagi stavka
    # ko'proq foydali bo'lsa ham, diagrammada bank bosilganda
    # foydalanuvchi bankning haqiqiy sahifasiga tushishi uchun rasmiy
    # sayt yozuvi tanlanishi kerak.
    insert_rate(
        session_factory, "credit",
        {"name": "Aggregator taklifi", "Foiz stavkasi": "10%", "source": "depozit.uz", "url": "https://depozit.uz/x"},
        bank_code="SQB",
    )
    insert_rate(
        session_factory, "credit",
        {"name": "Rasmiy taklif", "Foiz stavkasi": "18%", "source": "sqb.uz", "url": "https://sqb.uz/x"},
        bank_code="SQB",
    )

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session)

    sample = result["market_sample"]
    assert len(sample) == 1
    assert sample[0]["rate"] == 18.0
    assert sample[0]["url"] == "https://sqb.uz/x"


def test_analyze_product_market_sample_falls_back_to_depozit_uz_when_no_official_source(session_factory):
    insert_rate(
        session_factory, "credit",
        {"name": "Aggregator taklifi", "Foiz stavkasi": "10%", "source": "depozit.uz", "url": "https://depozit.uz/x"},
        bank_code="SQB",
    )

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session)

    sample = result["market_sample"]
    assert sample[0]["rate"] == 10.0
    assert sample[0]["url"] == "https://depozit.uz/x"


def test_analyze_product_market_sample_picks_best_rate_among_multiple_official_rows(session_factory):
    insert_rate(
        session_factory, "credit",
        {"name": "A", "Foiz stavkasi": "20%", "source": "sqb.uz", "url": "https://sqb.uz/a"},
        bank_code="SQB",
    )
    insert_rate(
        session_factory, "credit",
        {"name": "B", "Foiz stavkasi": "15%", "source": "sqb.uz", "url": "https://sqb.uz/b"},
        bank_code="SQB",
    )

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session)

    sample = result["market_sample"]
    assert sample[0]["rate"] == 15.0
    assert sample[0]["url"] == "https://sqb.uz/b"


def test_analyze_product_market_sample_treats_missing_source_as_not_official(session_factory):
    # Agar bironta connector "source" maydonini to'ldirmasdan qoldirsa,
    # bunday yozuv avtomatik "rasmiy" deb hisoblanmasligi kerak — aks
    # holda depozit.uz'ning haqiqiy rasmiy yozuvidan ustun chiqib qolardi.
    insert_rate(
        session_factory, "credit",
        {"name": "Manbasiz yozuv", "Foiz stavkasi": "5%", "url": "https://example.uz/x"},
        bank_code="SQB",
    )
    insert_rate(
        session_factory, "credit",
        {"name": "Rasmiy taklif", "Foiz stavkasi": "18%", "source": "sqb.uz", "url": "https://sqb.uz/x"},
        bank_code="SQB",
    )

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session)

    sample = result["market_sample"]
    assert sample[0]["rate"] == 18.0
    assert sample[0]["url"] == "https://sqb.uz/x"


def test_analyze_product_market_sample_credit_ranks_lowest_first(session_factory):
    insert_rate(session_factory, "credit", {"name": "A", "Foiz stavkasi": "18%"}, bank_code="SQB")
    insert_rate(session_factory, "credit", {"name": "B", "Foiz stavkasi": "15%"}, bank_code="AGRO")

    with session_factory() as session:
        result = analyze_product("credit", 16.0, session)

    sample = result["market_sample"]
    assert sample[0]["bank_code"] == "AGRO"
    assert sample[0]["rate"] == 15.0


def test_analyze_product_russian_language_support(session_factory):
    insert_rate(session_factory, "credit", {"name": "A", "Foiz stavkasi": "20%"}, bank_code="SQB")
    insert_rate(session_factory, "credit", {"name": "B", "Foiz stavkasi": "24%"}, bank_code="AGRO")

    with session_factory() as session:
        result = analyze_product("credit", 18.0, session, lang="ru")

    assert "На рынке найдено 2 предложений данного типа" in result["summary"]
    assert "Ставка ниже среднерыночной" in result["strengths"][0]
    assert not result["cautions"]


def test_analyze_product_russian_language_empty(session_factory):
    with session_factory() as session:
        result = analyze_product("credit", 18.0, session, lang="ru")

    assert "На рынке пока не найдено других предложений" in result["summary"]


def test_analyze_product_market_stats_cover_only_the_requested_category(session_factory):
    """Bozor statistikasi (o'rtacha / min / max / son) FAQAT so'ralgan
    kategoriyadagi takliflardan hisoblanishi kerak. Aks holda jadvalda har bir
    kategoriya yonida soni o'sha kategoriyniki, o'rtacha stavkasi esa butun
    bozorniki chiqardi — bir xilda ko'ringan, lekin har kategoriya uchun
    noto'g'ri moliyaviy raqam."""
    for name, rate in (("A", "20%"), ("B", "30%")):
        insert_rate(session_factory, "credit",
                    {"name": name, "category": "Ipoteka", "Foiz stavkasi": rate})
    for name, rate in (("C", "40%"), ("D", "50%"), ("E", "60%")):
        insert_rate(session_factory, "credit",
                    {"name": name, "category": "Iste'mol krediti", "Foiz stavkasi": rate})

    with session_factory() as session:
        ipoteka = analyze_product("credit", 26.0, session, category="Ipoteka")
        istamol = analyze_product("credit", 26.0, session, category="Iste'mol krediti")

    # Ipoteka: (20 + 30) / 2 = 25.0 — 2 ta taklif.
    assert ipoteka["market_count"] == 2
    assert ipoteka["market_avg"] == 25.0
    assert ipoteka["market_min"] == 20.0
    assert ipoteka["market_max"] == 30.0

    # Iste'mol krediti: (40 + 50 + 60) / 3 = 50.0 — 3 ta taklif.
    assert istamol["market_count"] == 3
    assert istamol["market_avg"] == 50.0
    assert istamol["market_min"] == 40.0
    assert istamol["market_max"] == 60.0

    # Ikkala o'rtacha har xil bo'lishi shart — aks holda raqamlar umumiy
    # bo'lib ketgan (barcha 5 ta taklif bo'yicha o'rtacha 40.0).
    assert ipoteka["market_avg"] != istamol["market_avg"]


def test_analyze_product_does_not_mix_other_categories_when_requested_one_is_empty(session_factory):
    """So'ralgan kategoriya bo'yicha HALI bironta taklif bo'lmasa, bozor
    statistikasi butun bozordan hisoblanmasligi kerak: kredit turlari
    (Ipoteka 20-30% / Iste'mol 40-60%) stavkalari keskin farq qiladi, shuning
    uchun "Overdraft" uchun 5 ta aralash taklifning o'rtachasi (40.0) moliyaviy
    xulosa sifatida noto'g'ri — `analyze_product` bunda halol "taklif
    topilmadi" deydi.
    Bozor umuman bo'sh bo'lsa raqamlar `None` bo'ladi, 0.0 EMAS — 0% haqiqiy
    (kredit uchun eng arzon) stavka deb o'qilardi."""
    for name, rate in (("A", "20%"), ("B", "30%")):
        insert_rate(session_factory, "credit",
                    {"name": name, "category": "Ipoteka", "Foiz stavkasi": rate})
    for name, rate in (("C", "40%"), ("D", "50%"), ("E", "60%")):
        insert_rate(session_factory, "credit",
                    {"name": name, "category": "Iste'mol krediti", "Foiz stavkasi": rate})

    with session_factory() as session:
        no_overdraft = analyze_product("credit", 26.0, session, category="Overdraft")
        empty_market = analyze_product("deposit", 20.0, session)

    # "Overdraft" bo'yicha ma'lumot yo'q — aralash bozor emas, bo'sh natija.
    assert no_overdraft["market_count"] == 0
    assert no_overdraft["market_avg"] is None
    assert no_overdraft["score"] is None
    assert "topilmadi" in no_overdraft["summary"]
    # Kategoriyaga mos yozuv bo'lmaganda boshqa kategoriyadagi banklar
    # diagrammaga ham sizib kirmasligi kerak.
    assert no_overdraft["market_sample"] == []

    # Solishtiradigan hech narsa yo'q — 0.0 emas, None.
    assert empty_market["market_count"] == 0
    assert empty_market["market_avg"] is None
    assert empty_market["market_min"] is None
    assert empty_market["score"] is None


