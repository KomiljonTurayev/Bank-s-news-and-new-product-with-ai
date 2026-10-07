"""Valyuta ayirboshlash kursi yozuvlarining umumiy shakli va raqam o'qish.

Barcha bank connectorlari kursni bir xil ikkita yozuv sifatida saqlaydi —
bank xarid qiladigan narx ("Olish") va bank sotadigan narx ("Sotish") —
chunki frontend va taqqoslash mantig'i shu yagona konvensiyaga tayanadi.
Avval bu juftlik o'n beshdan ortiq connectorda qo'lda tuzilar edi; yorliq
matnini bitta joyda saqlash ularning bir-biridan ajralib ketish xavfini
yo'qotadi.

Raqamlarni o'qish ham xuddi shunday takrorlanar edi: saytlar minglik
ajratgich sifatida oddiy bo'shliq yoki uzilmas bo'shliq (``\\xa0``),
kasr ajratgich sifatida esa nuqta yoki vergul ishlatadi."""

from __future__ import annotations

BUY = "Olish"
SELL = "Sotish"

_THOUSAND_SEPARATORS = ("\xa0", " ", " ", "'")


def parse_amount(text: str | None) -> float | None:
    """Saytdagi matnli kursni songa aylantiradi; son bo'lmasa `None`."""
    if text is None:
        return None
    cleaned = str(text)
    for separator in _THOUSAND_SEPARATORS:
        cleaned = cleaned.replace(separator, "")
    cleaned = cleaned.replace(",", ".").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def rate_pair(
    code: str | None,
    buy: float | None,
    sell: float | None,
    *,
    source: str,
    url: str,
    **extra: object,
) -> list[dict]:
    """Bitta valyuta uchun "Olish"/"Sotish" yozuvlari juftligini qaytaradi.

    Kod bo'lmasa, UZS bo'lsa (bankning o'z valyutasini almashtirish
    ma'nosiz) yoki tomonlardan biri nol/bo'sh bo'lsa (bank hozircha shu
    valyutani almashtirmayapti degani, haqiqiy stavka emas) — bo'sh
    ro'yxat qaytadi."""
    if not code or code == "UZS" or not buy or not sell:
        return []
    return [
        {"code": code, "side": BUY, "rate": float(buy), "source": source, "url": url, **extra},
        {"code": code, "side": SELL, "rate": float(sell), "source": source, "url": url, **extra},
    ]
