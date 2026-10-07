"""Konektorlar registri — ma'lumot yig'uvchi barcha manbalarning ro'yxati.

Modullar bittalab, har biri o'z `try`i ichida yuklanadi: bitta manba
modulidagi import xatosi butun ro'yxatni, demak butun skreypingni va
startapni, o'ldirmasligi kerak — 49 bank eski holda bitta import
satriga bog'liq edi. Yangi manba qo'shish = `connectors/` ichiga fayl
qo'yish + quyidagi jadvalga bitta qator."""

import importlib
import logging

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

# modul nomi -> undagi konektor sinflari. Oddiy `from ... import` emas:
# yuklash har modul uchun alohida (qarang `_load_classes`).
_CONNECTOR_MODULES: dict[str, tuple[str, ...]] = {
    "agrobank": ("AgrobankConnector", "AgrobankExchangeConnector"),
    "aloqabank": ("AloqabankConnector",),
    "asakabank": ("AsakabankConnector",),
    "anorbank": ("AnorbankConnector", "AnorbankExchangeConnector"),
    "apex_bank": ("ApexBankConnector", "ApexBankExchangeConnector"),
    "asia_alliance": ("AsiaAllianceConnector", "AsiaAllianceExchangeConnector"),
    "avobank": ("AvobankConnector", "AvobankCreditCardConnector"),
    "brb": ("BRBConnector",),
    "cbu": ("CBUConnector",),
    "davrbank": ("DavrbankConnector", "DavrbankExchangeConnector"),
    "depozit_exchange": ("DepozitExchangeConnector",),
    "depozit_tables": (
        "DepozitBondConnector",
        "DepozitCreditCardConnector",
        "DepozitDebitCardConnector",
    ),
    "depozit_uz": ("DepozitUzConnector",),
    "garantbank": ("GarantbankConnector",),
    "hamkorbank": ("HamkorbankConnector", "HamkorbankExchangeConnector"),
    "hayotbank": ("HayotBankConnector",),
    "infinbank": ("InFinbankConnector", "InFinbankExchangeConnector"),
    "ipakyulibank": ("IpakYuliBankConnector", "IpakYuliExchangeConnector"),
    "ipoteka_business": ("IpotekaBusinessConnector", "IpotekaExchangeConnector"),
    "kapitalbank": ("KapitalbankConnector",),
    "kdbbank": ("KDBBankCardConnector", "KDBBankConnector", "KDBBankExchangeConnector"),
    "madadinvestbank": ("MadadInvestBankConnector", "MadadInvestBankExchangeConnector"),
    "mikrokreditbank": ("MikrokreditbankConnector",),
    "mikroleasing": ("MikroLeasingConnector",),
    "nbu": ("NBUCardConnector", "NBUConnector", "NBUCreditConnector"),
    "octobank": ("OctobankCardConnector", "OctobankConnector"),
    "openbank": ("OpenBankConnector",),
    "opendata_rates": ("OpenDataRatesConnector",),
    "orient_finans": (
        "OrientFinansCardConnector",
        "OrientFinansConnector",
        "OrientFinansExchangeConnector",
    ),
    "poytaxtbank": ("PoytaxtbankConnector",),
    "saderatbank": ("SaderatBankConnector",),
    "sqb": ("SQBConnector", "SQBExchangeConnector"),
    "tayanchbank": ("TayanchBankConnector",),
    "tbcbank": ("TBCBankConnector",),
    "tengebank": ("TengeBankConnector",),
    "trastbank": ("TrastbankConnector", "TrastbankExchangeConnector"),
    "turonbank": ("TuronbankCardConnector", "TuronbankConnector"),
    "universalbank": ("UniversalbankConnector", "UniversalbankExchangeConnector"),
    "uzse": ("UzseBondConnector",),
    "uzumbank": ("UzumBankConnector",),
    "xb": ("XBConnector",),
    "ziraatbank": ("ZiraatBankConnector",),
}


def _load_classes() -> tuple[dict[str, type[BaseConnector]], list[str]]:
    """Manba modullarini yuklaydi; yiqilganlarini nomlab qaytaradi."""
    classes: dict[str, type[BaseConnector]] = {}
    unloaded: list[str] = []
    for module_name, class_names in _CONNECTOR_MODULES.items():
        try:
            module = importlib.import_module(f"app.connectors.{module_name}")
            classes.update({name: getattr(module, name) for name in class_names})
        except Exception:
            # Bitta manba butun ro'yxat evaziga chetga suriladi. Jim chetga
            # surish ma'lumotning yo'qolishini yashirgani uchun yozuv
            # loglanadi va modul `UNLOADED_MODULES`ga tushadi.
            logger.exception("konektor moduli yuklanmadi: %s", module_name)
            unloaded.append(module_name)
    return classes, unloaded


CLASSES, UNLOADED_MODULES = _load_classes()


def _make(class_name: str, *args, **kwargs):
    """Konektor yaratadi; moduli yuklanmagan bo'lsa None — ro'yxatning
    qolgani shu javob bilan ham to'liq ishlaydi."""
    klass = CLASSES.get(class_name)
    return None if klass is None else klass(*args, **kwargs)


_INSTANCES = [
    _make("CBUConnector"),
    _make("DepozitExchangeConnector"),
    _make("NBUConnector"),
    _make("NBUCreditConnector", [
        "ipoteka-kreditlari", "avtokreditlar", "mikroqarzlar",
        "talim-krediti-1", "overdraft", "national-green",
    ]),
    _make("NBUCardConnector"),
    _make("IpotekaBusinessConnector", "deposit", "https://ipotekabank.uz/uz/business/deposites/"),
    _make("IpotekaBusinessConnector", "credit", "https://ipotekabank.uz/uz/business/financing/"),
    _make("IpotekaBusinessConnector", "deposit", "https://www.ipotekabank.uz/uz/private/deposits/", segment="individual"),
    _make("IpotekaBusinessConnector", "credit", "https://www.ipotekabank.uz/uz/private/crediting/", segment="individual"),
    _make("IpotekaExchangeConnector"),
    _make("SQBConnector", "deposit", "https://sqb.uz/uz/individuals/deposits/"),
    _make("SQBConnector", "credit", "https://sqb.uz/uz/individuals/credits/"),
    _make("SQBConnector", "card", "https://sqb.uz/uz/individuals/bank-cards/"),
    _make("SQBExchangeConnector"),
    _make("XBConnector", "deposit", "https://xb.uz/page/physical-deposit?currency=UZS"),
    _make("XBConnector", "credit", "https://xb.uz/page/ipoteka-kreditlari", category="Ipoteka"),
    _make("XBConnector", "credit", "https://xb.uz/page/istemol-kreditlari", category="Iste'mol krediti"),
    _make("XBConnector", "credit", "https://xb.uz/page/mikrokreditlar", category="Mikroqarz"),
    _make("XBConnector", "credit", "https://xb.uz/page/avtokredit-3", category="Avtokredit"),
    # Playwright orqali (JS-render qilinadigan sayt) — boshqa connectorlarga
    # nisbatan sezilarli sekinroq (har biri o'z headless Chromium'ini ochadi).
    _make("HamkorbankConnector", "deposit", "https://hamkorbank.uz/uz/physical/deposits/"),
    _make("HamkorbankConnector", "credit", "https://hamkorbank.uz/uz/physical/credits/"),
    _make("HamkorbankConnector", "card", "https://hamkorbank.uz/uz/physical/bank-cards/"),
    _make("HamkorbankExchangeConnector"),
    _make("KapitalbankConnector", "deposit", "https://www.kapital24.uz/uz/deposit/"),
    _make("KapitalbankConnector", "credit", "https://www.kapital24.uz/uz/crediting/"),
    _make("KapitalbankConnector", "card", "https://www.kapital24.uz/uz/plastic-cards/list/"),
    _make("KDBBankConnector"),
    _make("KDBBankCardConnector", "https://kdb.uz/uz/individuals/local-cards"),
    _make("KDBBankCardConnector", "https://kdb.uz/uz/individuals/international-cards"),
    _make("KDBBankExchangeConnector"),
    _make("OpenBankConnector"),
    _make("AgrobankConnector", "deposit", "uz/person/deposits"),
    _make("AgrobankConnector", "credit", "uz/person/loans"),
    _make("AgrobankConnector", "card", "uz/person/cards"),
    _make("AgrobankExchangeConnector"),
    _make("AnorbankConnector", "deposit", "https://anorbank.uz/uz/deposit/"),
    _make("AnorbankConnector", "credit", "https://anorbank.uz/uz/credits/"),
    _make("AnorbankConnector", "card", "https://anorbank.uz/uz/cards/"),
    _make("AnorbankExchangeConnector"),
    # Playwright orqali (JS-render qilinadigan Nuxt SPA).
    _make("AsakabankConnector", "deposit", "https://asakabank.uz/uz/physical-persons/deposits"),
    _make("AsakabankConnector", "credit", "https://asakabank.uz/uz/physical-persons/credits"),
    _make("AsakabankConnector", "card", "https://asakabank.uz/uz/physical-persons/cards"),
    _make("IpakYuliBankConnector", "deposit", "https://ipakyulibank.uz/physical/omonatlar"),
    _make("IpakYuliBankConnector", "credit", "https://ipakyulibank.uz/physical/kreditlar"),
    _make("IpakYuliExchangeConnector"),
    _make("TBCBankConnector"),
    _make("DavrbankConnector", "deposit", "https://davrbank.uz/uz/deposits"),
    _make("DavrbankConnector", "credit", "https://davrbank.uz/uz/loans/all"),
    _make("DavrbankExchangeConnector"),
    # Ro'yxat sahifasi yo'q — har bir mahsulot o'z alohida sahifasida.
    _make("GarantbankConnector", "deposit", ["/uz/vklad-orzu-sari", "/uz/bingo", "/uz/vklad-onlajn-kunlik"]),
    _make("GarantbankConnector", "credit", [
        "/uz/ipotechnyj-kredit-makon", "/uz/ipotechnyj-kredit-makon1",
        "/uz/mikrozajm-tez-va-qulay-online-20", "/uz/mikrozajm-imkoniyat",
        "/uz/mikrozajm-zarplatnyj-proekt", "/uz/kredit-farovonlik",
        "/uz/mikrozajm-onlajn", "/uz/go", "/uz/pervyj-shag-k-biznesu",
        "/uz/avtokredit-qulay-avto", "/uz/avtokredit-changan-adm",
        "/uz/avtokredit-changan", "/uz/avto-mahallij", "/uz/avto-import",
        "/uz/avtokredit-Yengil", "/uz/avtokredit-lixiang",
    ]),
    _make("MadadInvestBankConnector", "deposit"),
    _make("MadadInvestBankConnector", "credit"),
    _make("MadadInvestBankExchangeConnector"),
    # Ravnaq-bank -> Octobank (qayta nomlangan); saytda omonat yo'q,
    # faqat kredit va karta bor.
    _make("OctobankConnector", [
        "/jismoniy-shaxslarga/avtokredit",
        "/jismoniy-shaxslarga/avtokredit-20",
        "/jismoniy-shaxslarga/ipoteka-octobank",
    ]),
    _make("OctobankCardConnector", [
        "/jismoniy-shaxslarga/som-kartalari/humo",
        "/jismoniy-shaxslarga/som-kartalari/humo-virtual",
        "/jismoniy-shaxslarga/xalqaro-kartalar/visa-classic-virtual",
        "/jismoniy-shaxslarga/xalqaro-kartalar/visa-signature",
        "/jismoniy-shaxslarga/xalqaro-kartalar/visa-infinite",
        "/jismoniy-shaxslarga/xalqaro-kartalar/mastercard-standard-virtual",
    ]),
    _make("TengeBankConnector", "deposit", ["/deposit/srochnye-vklady", "/deposit/vklad-v-inostrannoj-valyute"]),
    _make("TengeBankConnector", "credit", [
        "/credit/avtokredit-dlya-samozanyatyh", "/credit/avtokredit-drive",
        "/credit/avtokredit-drive-plus", "/credit/avtokredit-na-elektromobil",
        "/credit/avtokredit-na-importnyj-avtomobil", "/credit/avtokredit-na-novyj-avtomobil",
        "/credit/avtokredit-roodell-i", "/credit/ipoteka-na-novoe-jilyo",
        "/credit/ipoteka-na-vtorichnoe-zhile", "/credit/mikrozajm-onlajn",
        "/credit/pervyj-shag-k-biznesu",
    ]),
    _make("ZiraatBankConnector", "deposit", ["/uz/milliy-valyutadagi-omonatlar", "/uz/xorijiy-valyutagi-omonatlar"]),
    _make("ZiraatBankConnector", "credit", [
        "/uz/birlamchi-bozor-uchun-avtokredit", "/uz/ikkilamchi-bozor-uchun-avtokredit-",
        "/uz/iste-mol-kredit----yashil-komfort---", "/uz/mikroqarz",
        "/uz/uy-joy-sotib-olish-uchun-kreditlar", "/uz/шинам-уй",
    ]),
    # Omonat yo'nalishi saytda hozircha ishlamaydi (bosh sahifaga
    # qaytaradi) — faqat kredit ulangan.
    _make("HayotBankConnector"),
    _make("AvobankConnector", ["/uz/products/deposits", "/uz/products/flexible-deposit"]),
    _make("AvobankCreditCardConnector"),
    _make("SaderatBankConnector", ["avtokredit", "istemol-krediti", "ipoteka-1"]),
    _make("TayanchBankConnector", "deposit"),
    _make("TayanchBankConnector", "credit"),
    _make("UzumBankConnector"),
    _make("InFinbankConnector", "deposit", "https://www.infinbank.com/uz/private/deposit/"),
    _make("InFinbankConnector", "credit", "https://www.infinbank.com/uz/private/credits/"),
    _make("InFinbankExchangeConnector"),
    _make("AloqabankConnector", "deposit", "https://aloqabank.uz/uz/private/deposit/"),
    _make("AloqabankConnector", "credit", "https://aloqabank.uz/uz/private/crediting/"),
    _make("OpenDataRatesConnector", "ALOQA", "https://aloqabank.uz", "aloqabank.uz"),
    _make("TuronbankConnector", "deposit", "https://turonbank.uz/uz/private/deposit/"),
    _make("TuronbankConnector", "credit", "https://turonbank.uz/uz/private/crediting/"),
    _make("TuronbankCardConnector", [
        "/uz/private/plastic-cards/list/humo-/",
        "/uz/private/plastic-cards/list/tulov-kartalar/",
        "/uz/private/plastic-cards/list/humo-visa-kobeyjing-kartasi/",
        "/uz/private/plastic-cards/list/mastercard-gold/",
        "/uz/private/plastic-cards/list/mastercard-standart/",
        "/uz/private/plastic-cards/list/mastercard-turist-uz-kobrend-kartasi/",
        "/uz/private/plastic-cards/list/visa-classic/",
        "/uz/private/plastic-cards/list/visa-electron/",
        "/uz/private/plastic-cards/list/visa-gold/",
    ]),
    _make("OpenDataRatesConnector", "TURON", "https://turonbank.uz", "turonbank.uz"),
    _make("PoytaxtbankConnector", "deposit", "https://poytaxtbank.uz/uz/private/deposit/"),
    _make("PoytaxtbankConnector", "credit", "https://poytaxtbank.uz/uz/private/crediting/"),
    _make("OpenDataRatesConnector", "POYTAXT", "https://poytaxtbank.uz", "poytaxtbank.uz"),
    _make("TrastbankConnector", "deposit", "https://trastbank.uz/uz/private/deposit/"),
    _make("TrastbankConnector", "credit", "https://trastbank.uz/uz/private/crediting/"),
    _make("TrastbankExchangeConnector"),
    _make("AsiaAllianceConnector", "deposit", "https://aab.uz/uz/private/deposit/"),
    _make("AsiaAllianceConnector", "credit", "https://aab.uz/uz/private/crediting/"),
    _make("AsiaAllianceExchangeConnector"),
    _make("MikrokreditbankConnector", "deposit", "https://mkbank.uz/uz/private/deposit/"),
    _make("MikrokreditbankConnector", "credit", "https://mkbank.uz/uz/private/crediting/"),
    _make("OpenDataRatesConnector", "MICROCREDITBANK", "https://mkbank.uz", "mkbank.uz"),
    _make("BRBConnector", "deposit", "https://brb.uz/jismoniy-shaxslarga/omonatlar"),
    _make("BRBConnector", "credit", "https://brb.uz/jismoniy-shaxslarga/kreditlar"),
    _make("UniversalbankConnector", "deposit", "https://universalbank.uz/uz/deposit"),
    _make("UniversalbankConnector", "credit", "https://universalbank.uz/uz/credit"),
    _make("UniversalbankConnector", "card", "https://universalbank.uz/uz/cards"),
    _make("UniversalbankExchangeConnector"),
    _make("ApexBankConnector", "deposit", "https://www.apexbank.uz/customer/deposit/"),
    _make("ApexBankConnector", "credit", "https://www.apexbank.uz/customer/credits/"),
    _make("ApexBankExchangeConnector"),
    # Playwright orqali (JS-render qilinadigan sayt).
    _make("OrientFinansConnector", "deposit", "https://ofb.uz/omonatlar"),
    # Umumiy /kreditlar sahifasi faqat 10 ta "vitrina" mahsulotni ko'rsatadi —
    # to'liq katalog toifa bo'yicha alohida sahifalarda (masalan
    # /kreditlar/avtokreditlar'da 10 ta avtokredit, umumiy sahifada esa
    # ulardan atigi bir nechtasi namoyish etiladi).
    _make("OrientFinansConnector", "credit", "https://ofb.uz/kreditlar/avtokreditlar"),
    _make("OrientFinansConnector", "credit", "https://ofb.uz/kreditlar/ipoteka-kreditlari"),
    _make("OrientFinansConnector", "credit", "https://ofb.uz/kreditlar/mikroqarzlar"),
    _make("OrientFinansConnector", "credit", "https://ofb.uz/kreditlar/overdraft"),
    _make("OrientFinansConnector", "credit", "https://ofb.uz/kreditlar/talim-kreditlari"),
    _make("OrientFinansConnector", "credit", "https://ofb.uz/kreditlar/istemol-kreditlari"),
    _make("OrientFinansCardConnector", [
        "https://ofb.uz/kartalar/uzcard-sherdor",
        "https://ofb.uz/kartalar/mastercard-black-edition",
        "https://ofb.uz/kartalar/mastercard-world-elite",
        "https://ofb.uz/kartalar/visa-infinite",
        "https://ofb.uz/kartalar/sumli",
        "https://ofb.uz/kartalar/niyat-kredit-kartasi",
        "https://ofb.uz/kartalar/ofb-kids",
        "https://ofb.uz/kartalar/ofb-junior",
        "https://ofb.uz/kartalar/moment",
    ]),
    _make("OrientFinansExchangeConnector"),
    _make("DepozitUzConnector", "deposit", "https://depozit.uz/deposits", "deposit-name"),
    _make("DepozitUzConnector", "credit", "https://depozit.uz/credits/consumer", "credit-name", category="Iste'mol krediti"),
    _make("DepozitUzConnector", "credit", "https://depozit.uz/credits/mortgage", "credit-name", category="Ipoteka"),
    _make("DepozitUzConnector", "credit", "https://depozit.uz/credits/auto", "credit-name", category="Avtokredit"),
    _make("DepozitUzConnector", "credit", "https://depozit.uz/credits/education", "credit-name", category="Ta'lim krediti"),
    _make("DepozitUzConnector", "credit", "https://depozit.uz/credits/overdraft", "credit-name", category="Overdraft"),
    _make("DepozitCreditCardConnector"),
    _make("DepozitDebitCardConnector"),
    _make("DepozitBondConnector"),
    _make("UzseBondConnector"),
    # Mikro Leasing — bank emas, lizing kompaniyasi (qarang
    # app/connectors/mikroleasing.py izohi: foiz stavkasi e'lon
    # qilinmaydi, shu bois bu yozuvlar bozor saralashida ishtirok etmaydi).
    _make("MikroLeasingConnector", [
        "/uz/loans/yengil-avtomobillar-lizingi.html",
        "/uz/loans/yuk-avtomobillarining-lizingi.html",
        "/uz/loans/maxsus-uskunalar-lizingi.html",
        "/uz/loans/qishloq-xojaligi-texnikasi-lizingi.html",
        "/uz/loans/uskunalar-lizingi.html",
        "/uz/loans/tijorat-kochmas-mulk-lizing.html",
    ]),
    # Yangi bank/manba qo'shish uchun: o'xshash tuzilmali bank connectorni
    # (masalan trastbank.py) namunabop olib, tayyor connectorni shu yerga
    # qo'shing.
]

# `None` faqat moduli yuklanmagan konektor uchun (`_make`ning javobi).
CONNECTORS: list[BaseConnector] = [c for c in _INSTANCES if c is not None]

# Yangi bank/manba qo'shish uchun: o'xshash tuzilmali bank connectorni
# (masalan trastbank.py) namunabop olib, `connectors/` ichiga fayl qo'ying,
# `_CONNECTOR_MODULES`ga qator qo'shing va quyidagi ro'yxatga ulang.
