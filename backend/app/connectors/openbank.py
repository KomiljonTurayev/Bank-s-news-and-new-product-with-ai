"""openbank.uz (Open Bank) — jismoniy shaxslar uchun "Yangi uy" muddatli
to'lovi (ipoteka o'rniga sotib olish-sotish shartnomasi — Islomiy
moliyalashtirish, shu bois "foiz stavkasi" emas, "bank ustamasi"
(marja) deb ataladi). Omonat sahifasida (``/accounts``) hech qanday
statik stavka yo'q — faqat individual/ilova ichida ko'rsatiladigan
taklif, shu bois qamrab olinmagan.

Sayt Next.js App Router bo'lib, mahsulot ma'lumotlari (CMS'dan kelgan
"axborot varaqasi" — infoSheet) oddiy HTML emas, balki
``self.__next_f.push([1, "..."])`` React Server Component "flight"
oqimida JSON qatorlar sifatida keladi. Shu bois bu connector avval har
bir qatorni dekodlaydi, so'ng ``"infoSheet":{...}`` ob'ektini
qavslarni muvozanatlab (regex emas) ajratib oladi."""

import json
import re

from app.connectors.base import HtmlPageConnector

_URL = "https://openbank.uz/mortgage"

_FLIGHT_CHUNK_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')


def _decode_flight_text(html: str) -> str:
    chunks = []
    for match in _FLIGHT_CHUNK_RE.findall(html):
        try:
            chunks.append(json.loads(match))
        except json.JSONDecodeError:
            continue
    return "".join(chunks)


def _string_state_step(in_string: bool, escape: bool, ch: str) -> tuple[bool, bool]:
    """Skaner avtomatining bir belgili o'tishi -> yangi (in_string, escape).
    Satri tashqarisida backslash izlanmaydi (escape faqat satr ichida ma'noli)."""
    if not in_string:
        return (True, False) if ch == '"' else (False, escape)
    if escape:
        return True, False
    if ch == "\\":
        return True, True
    if ch == '"':
        return False, escape
    return True, escape


def _loads_or_none(fragment: str):
    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        return None


def _extract_json_object(text: str, start: int):
    """``text[start]`` "{" bo'lishi kerak — mos yopuvchi "}"ni qavslarni
    muvozanatlab topadi (qator ichidagi qavslarni e'tiborsiz qoldirib)."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        was_outside = not in_string
        in_string, escape = _string_state_step(in_string, escape, ch)
        if not was_outside or ch == '"':
            # Satr ichidagi belgilar va satrni ochuvchi qo'shtirnoq qavslarni
            # hisoblamaydi.
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return _loads_or_none(text[start : i + 1])
    return None


def _row_text(row: dict) -> str:
    blocks = row.get("value") or []
    return "".join(
        child.get("text", "") for block in blocks for child in block.get("children", [])
    ).strip()


def _group_rows(info_sheet: dict, group_title: str) -> list[tuple[str, str]]:
    for group in info_sheet.get("groups") or []:
        if group.get("title") == group_title:
            return [
                (row.get("label"), _row_text(row))
                for row in group.get("rows") or []
                if row.get("value")
            ]
    return []


def parse_mortgage(html: str, url: str = _URL) -> list[dict]:
    text = _decode_flight_text(html)

    marker = '"infoSheet":{'
    idx = text.find(marker)
    if idx == -1:
        return []
    info_sheet = _extract_json_object(text, idx + len('"infoSheet":'))
    if not info_sheet:
        return []

    basics = dict(_group_rows(info_sheet, "Mahsulot haqida asosiy ma’lumotlar"))
    financing_type = basics.get("Moliyalashtirish turi") or "Yangi uy"
    name = financing_type.split("—")[0].strip()

    records = []
    for label, value in _group_rows(info_sheet, "Bank ustamasi"):
        if not value or "%" not in value:
            continue
        records.append(
            {
                "name": f"{name} ({label})",
                "source": "openbank.uz",
                "url": url,
                "Bank ustamasi": value,
            }
        )

    return records


class OpenBankConnector(HtmlPageConnector):
    bank_code = "OPEN"
    product_type = "credit"
    segment = "individual"

    def __init__(self, url: str = _URL):
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_mortgage(html, self.url)
