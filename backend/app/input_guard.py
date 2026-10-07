"""AI strategiga yuboriladigan erkin matnni (jamoa maqsadi) tekshirish.

Birinchi qatlam — shu modul: uyatli so'zlar (o'zbek, rus, ingliz) AI'ga
yuborilmasdan, token sarflanmasdan rad etiladi. Ikkinchi qatlam — mavzudan
tashqari so'rovlar — AI javobining o'zida (`goal_on_topic`) tekshiriladi,
chunki "bank sohasiga aloqadormi" degan savolga so'z ro'yxati javob bera olmaydi.
"""

import re

# Lotin yozuvidagi o'xshash belgilar va raqamli "niqoblar" (f*ck, 5uka, ...)
# kirill/lotin ildizlari bilan solishtirishdan oldin bir xil shaklga keltiriladi.
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s", "*": "", "'": "", "`": "", "ʻ": "", "ʼ": "", "‘": "", "’": ""})

# So'z boshi bo'yicha ildizlar: qo'shimchalar (-lar, -ing, -ть, -ed) bilan
# ham ushlanadi. Bank matnlarida uchramaydigan, yolg'on topilma bermaydigan
# ildizlargina olingan.
_ROOTS = (
    # o'zbek
    "jalab", "qotag", "qotoq", "dalbayob", "dalbaeb", "qanjiq", "haromi", "harom zoda",
    "sikay", "sikdi", "sikib", "sikish", "sikam", "onangni",
    # rus (kirill va lotin)
    "хуй", "хуе", "хуё", "хуя", "пизд", "ебат", "ебан", "ёбан", "еба", "заеб", "выеб", "бля",
    "сука", "суки", "мудак", "мудил", "пидор", "пидар", "гандон", "шлюх", "дерьм", "говн",
    "xuy", "xuev", "pizd", "eban", "ebat", "blya", "blyat", "suka", "mudak", "pidor", "gandon",
    # ingliz
    "fuck", "fck", "fuk", "shit", "bitch", "btch", "cunt", "asshole", "bastard", "dick", "pussy", "whore", "slut",
    # 18+ mavzu
    "porn", "порн", "sex", "секс", "xxx", "nude", "голая",
)
_PATTERN = re.compile(r"(?<![\w])(?:" + "|".join(re.escape(root) for root in _ROOTS) + r")", re.IGNORECASE)

INAPPROPRIATE_MESSAGE = (
    "So'rovda nojo'ya so'zlar bor. Iltimos, bank mahsuloti bo'yicha maqsadingizni "
    "odobli shaklda yozing."
)
OFF_TOPIC_MESSAGE = (
    "AI strategi faqat bank mahsulotlari (kredit, omonat, karta, investitsiya) bo'yicha "
    "ishlaydi. Iltimos, maqsadingizni shu soha doirasida yozing."
)


def is_inappropriate(text: str | None) -> bool:
    """Matnda uyatli so'z ildizi bormi (katta-kichik harf, niqoblarga befarq)."""
    if not text:
        return False
    normalized = text.lower().translate(_LEET)
    return bool(_PATTERN.search(normalized))
