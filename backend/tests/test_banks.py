from app.banks import resolve_bank_code


def test_known_alias_is_case_and_spacing_insensitive():
    assert resolve_bank_code("Kapitalbank") == "KDB"
    assert resolve_bank_code("kapital bank") == "KDB"
    assert resolve_bank_code("  KAPITALBANK  ") == "KDB"


def test_known_alias_variants_map_to_same_code():
    assert resolve_bank_code("Ipoteka bank") == "IPOTEKA"
    assert resolve_bank_code("Ipoteka-bank") == "IPOTEKA"


def test_unknown_bank_name_falls_back_to_slug():
    assert resolve_bank_code("Yangi Bank") == "YANGIBANK"


def test_unknown_bank_name_strips_apostrophes():
    assert resolve_bank_code("Ipak Yo'li Extra") == "IPAKYOLIEXTRA"


def test_unknown_bank_name_slug_is_truncated_to_24_chars():
    code = resolve_bank_code("Juda Ham Uzun Nomga Ega Bo'lgan Bank")
    assert len(code) <= 24


def test_uzse_bond_issuer_names_map_to_the_existing_depozit_derived_codes():
    # uzse.uz va depozit.uz bir xil obligatsiya emitentini boshqa so'z
    # tartibi/yuridik shakl qisqartmasi bilan yozadi — ikkalasi ham bir
    # xil real kompaniyaga tegishli bo'lishi foydalanuvchi tomonidan
    # tasdiqlangan, shu bois qo'lda bog'langan.
    assert resolve_bank_code("AGAT CREDIT AJ MMT") == "AGATCREDITMMTMCHJ"
    assert resolve_bank_code("DELTA MMT AJ") == "DELTAMMTMCHJ"
    assert resolve_bank_code("IMKON FINANS MIKROMOLIYA TASHKILOTI AJ") == "IMKONFINANSMIKROKREDITTA"
