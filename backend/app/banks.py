# depozit.uz'dagi banklar, kredit kartalar va valyuta almashinuvi
# jadvallarida haqiqatda uchragan, hozirda faoliyat yuritayotgan banklar
# ro'yxati (o'ylab topilmagan — barchasi tirik manbalardan tasdiqlangan).
BANKS = [
    {"code": "NBU", "name": "Milliy bank (NBU)"},
    {"code": "SQB", "name": "Sanoat-qurilish banki (SQB)"},
    {"code": "XB", "name": "Xalq banki"},
    {"code": "IPOTEKA", "name": "Ipoteka-bank"},
    {"code": "ASAKA", "name": "Asakabank"},
    {"code": "KDB", "name": "Kapitalbank"},
    {"code": "HAMKOR", "name": "Hamkorbank"},
    {"code": "IPAKYULI", "name": "Ipak Yo'li bank"},
    {"code": "ANOR", "name": "Anorbank"},
    {"code": "TBC", "name": "TBC bank"},
    {"code": "INFIN", "name": "InFinbank"},
    {"code": "AGRO", "name": "Agrobank"},
    {"code": "MICROCREDITBANK", "name": "Mikrokreditbank"},
    {"code": "ALOQA", "name": "Aloqabank"},
    {"code": "ASIAALLIANCE", "name": "Asia Alliance Bank"},
    {"code": "BRB", "name": "Biznesni rivojlantirish banki"},
    {"code": "DAVR", "name": "Davr-bank"},
    {"code": "GARANT", "name": "Garant bank"},
    {"code": "MADAD", "name": "Madad Invest Bank"},
    {"code": "ORIENT", "name": "Orient Finans bank"},
    {"code": "POYTAXT", "name": "Poytaxt bank"},
    {"code": "RAVNAQ", "name": "Ravnaq-bank"},
    {"code": "TENGEBANK", "name": "Tenge Bank"},
    {"code": "TRAST", "name": "Trastbank"},
    {"code": "TURON", "name": "Turonbank"},
    {"code": "UNIVERSAL", "name": "Universal bank"},
    {"code": "ZIRAAT", "name": "Ziraat Bank Uzbekiston"},
    # cbu.uz rasmiy litsenziyalangan banklar ro'yxati (Tijorat banklari /
    # Bosh ofislar bo'limi) bo'yicha qo'shilgan, hali alohida manba
    # ulanmagan banklar — ma'lumot kelib tushguncha "Ma'lumot hali
    # ulanmagan" deb ko'rinadi, lekin bank sifatida ro'yxatda bo'ladi.
    {"code": "HAYOT", "name": "Hayot Bank"},
    {"code": "UZUM", "name": "Uzum Bank"},
    {"code": "SODEROT", "name": "Soderot Bank"},
    {"code": "TAYANCH", "name": "Tayanch mikromoliya banki"},
    # depozit.uz'da haqiqiy omonat mahsuloti bilan uchragan, lekin
    # avvalgi ro'yxatda yo'q edi.
    {"code": "APEX", "name": "Apex Bank"},
    {"code": "AVOBANK", "name": "AVO bank"},
    {"code": "KDBUZ", "name": "KDB Bank O'zbekiston"},
    {"code": "OPEN", "name": "Open Bank"},
    # Bank emas, lizing kompaniyasi — depozit.uz kredit ro'yxatida
    # uchraganidan beri "MIKROLEASING" kodi bilan bazada yozilib kelgan,
    # lekin shu ro'yxatda bo'lmagani uchun frontendda ko'rinmas edi. Endi
    # o'z rasmiy saytidan ham olinadi (app/connectors/mikroleasing.py).
    {"code": "MIKROLEASING", "name": "Mikro Leasing"},
]

PRODUCT_TYPES = [
    {"code": "currency", "label": "Valyuta kursi"},
    {"code": "deposit", "label": "Omonatlar"},
    {"code": "credit", "label": "Kreditlar"},
    {"code": "card", "label": "Karta tariflari"},
    {"code": "investment", "label": "Investitsiya"},
]

SEGMENTS = [
    {"code": "individual", "label": "Jismoniy shaxs"},
    {"code": "business", "label": "Yuridik shaxs"},
]

def _slugify(name: str) -> str:
    return "".join(ch for ch in name.strip().lower() if ch.isalnum())


# Kalitlar _slugify() natijasiga mos keladi (bo'shliq, defis, apostrof va turli
# tirnoq belgilaridan qat'i nazar), shu bois manbalar orasidagi yozilish farqi
# alias'ni buzmaydi.
_BANK_NAME_ALIASES = {
    _slugify("milliy bank"): "NBU",
    _slugify("nbu"): "NBU",
    _slugify("o'zmilliybank"): "NBU",
    _slugify("sanoat-qurilish banki"): "SQB",
    _slugify("sqb"): "SQB",
    _slugify("o'zsanoatqurilishbank"): "SQB",
    _slugify("xalq banki"): "XB",
    _slugify("xalq bank"): "XB",
    _slugify("ipoteka bank"): "IPOTEKA",
    _slugify("ipoteka-bank"): "IPOTEKA",
    _slugify("asakabank"): "ASAKA",
    _slugify("asaka bank"): "ASAKA",
    _slugify("kapitalbank"): "KDB",
    _slugify("kapital bank"): "KDB",
    _slugify("hamkorbank"): "HAMKOR",
    _slugify("hamkor bank"): "HAMKOR",
    _slugify("ipak yo'li bank"): "IPAKYULI",
    _slugify("ipak yo'li banki"): "IPAKYULI",
    _slugify("anor bank"): "ANOR",
    _slugify("tbc bank"): "TBC",
    _slugify("tbc"): "TBC",
    _slugify("infinbank"): "INFIN",
    _slugify("infin bank"): "INFIN",
    _slugify("agrobank"): "AGRO",
    _slugify("agro bank"): "AGRO",
    _slugify("mikrokreditbank"): "MICROCREDITBANK",
    _slugify("aloqabank"): "ALOQA",
    _slugify("aloqa bank"): "ALOQA",
    _slugify("asia alliance bank"): "ASIAALLIANCE",
    _slugify("asia alliance bank atb"): "ASIAALLIANCE",
    _slugify("biznesni rivojlantirish banki"): "BRB",
    _slugify("qishloq qurilish bank"): "BRB",  # depozit.uz'dagi eski/muqobil nomi
    _slugify("davr-bank"): "DAVR",
    _slugify("davr bank"): "DAVR",
    _slugify("garant bank"): "GARANT",
    # "Invest Finance Bank" — InFinbank'ning rasmiy yuridik nomi (CBU
    # ro'yxatida shu nom bilan), alohida bank emas.
    _slugify("invest finance bank"): "INFIN",
    _slugify("madad invest bank"): "MADAD",
    _slugify("orient finans bank"): "ORIENT",
    _slugify("poytaxt bank"): "POYTAXT",
    _slugify("ravnaq-bank"): "RAVNAQ",
    _slugify("ravnaq bank"): "RAVNAQ",
    # Ravnaq-bank "Octobank" deb qayta nomlandi (ravnaqbank.uz domeni
    # hozir octobank.uz'ga yo'naltiriladi) — alohida bank emas.
    _slugify("octobank"): "RAVNAQ",
    _slugify("tenge bank"): "TENGEBANK",
    _slugify("trastbank"): "TRAST",
    _slugify("trast bank"): "TRAST",
    _slugify("turonbank"): "TURON",
    _slugify("turon bank"): "TURON",
    _slugify("universal bank"): "UNIVERSAL",
    _slugify("universalbank"): "UNIVERSAL",
    _slugify("ziraat bank uzbekistan"): "ZIRAAT",
    _slugify("ziraat bank uzbekiston"): "ZIRAAT",
    _slugify("hayot bank"): "HAYOT",
    _slugify("uzum bank"): "UZUM",
    _slugify("soderot bank"): "SODEROT",
    _slugify("saderat bank"): "SODEROT",
    _slugify("tayanch mikromoliya banki"): "TAYANCH",
    _slugify("tayanch bank"): "TAYANCH",
    # O'zagroeksportbank 2023-yilda xususiylashtirilib "AVO bank"ga
    # qayta nomlangan — alohida bank emas.
    _slugify("o'zagroeksportbank"): "AVOBANK",
    _slugify("ozagroeksportbank"): "AVOBANK",
    _slugify("apex bank"): "APEX",
    _slugify("avo bank"): "AVOBANK",
    # "KDB Bank O'zbekiston" (Koreya Taraqqiyot banki sho'ba korxonasi)
    # Kapitalbank'dan (kod "KDB") butunlay boshqa tashkilot — avval
    # xato ravishda shu kodga bog'langan edi.
    _slugify("kdb bank o'zbekiston"): "KDBUZ",
    _slugify("kdb bank"): "KDBUZ",
    _slugify("open bank"): "OPEN",
    _slugify("openbank"): "OPEN",
    # Obligatsiya (bonds) ro'yxatida ba'zi banklar rasmiy "ATB"
    # (aksiyadorlik tijorat banki) qo'shimchasi bilan chiqadi — bu bank
    # emas, balki xuddi shu bankning o'zi, faqat rasmiy nom bilan.
    _slugify("hamkorbank atb"): "HAMKOR",
    _slugify("kapitalbank atb"): "KDB",
    _slugify("ozsanoatqurilishbank atb"): "SQB",
    _slugify("tbc bank atb"): "TBC",
    # uzse.uz (fond birjasi) va depozit.uz bir xil obligatsiya emitentini
    # boshqa-boshqa so'z tartibi/yuridik shakl qisqartmasi bilan yozadi
    # (masalan "X MMT MChJ" va "X AJ MMT") — foydalanuvchi tasdig'i bilan
    # qo'lda bog'langan, chunki avtomatik slugify ikkalasini boshqa-boshqa
    # kodga aylantirar edi.
    _slugify("agat credit aj mmt"): "AGATCREDITMMTMCHJ",
    _slugify("delta mmt aj"): "DELTAMMTMCHJ",
    _slugify("imkon finans mikromoliya tashkiloti aj"): "IMKONFINANSMIKROKREDITTA",
}


def resolve_bank_code(bank_name: str) -> str:
    """Turli manbalarda turlicha yozilgan bank nomlarini bitta koda birlashtiradi."""
    slug = _slugify(bank_name)
    if slug in _BANK_NAME_ALIASES:
        return _BANK_NAME_ALIASES[slug]

    return slug.upper()[:24] or "NOMALUM"
