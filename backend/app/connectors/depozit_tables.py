from bs4 import BeautifulSoup

from app.banks import resolve_bank_code
from app.connectors.base import HtmlPageConnector
from app.connectors.html_cards import dedupe_records

_PARSER = "html.parser"
_ROWS_SELECTOR = "table tr"
_SOURCE = "depozit.uz"


def parse_credit_cards(html: str) -> list[dict]:
    """depozit.uz/cards/credit — reyting jadvali, rowspan yo'q. Bank katakchasi
    ba'zan bank nomi + karta nomini ikkita alohida qatorda birga saqlaydi."""
    soup = BeautifulSoup(html, _PARSER)
    records = []

    for row in soup.select(_ROWS_SELECTOR)[1:]:
        cells = row.select("td")
        if len(cells) < 6:
            continue

        lines = cells[1].get_text("\n", strip=True).split("\n")
        bank_name = lines[0].strip()
        if not bank_name:
            continue
        card_name = lines[1].strip() if len(lines) > 1 else "Kredit karta"

        records.append({
            "_bank_code": resolve_bank_code(bank_name),
            "bank_name": bank_name,
            "name": card_name,
            "source": _SOURCE,
            "category": "Kredit karta",
            "Maksimal summa": cells[2].get_text(strip=True),
            "Foiz stavkasi": cells[3].get_text(strip=True),
            "Muddat": cells[4].get_text(strip=True),
            "Imtiyozli davr": cells[5].get_text(strip=True),
        })

    return dedupe_records(records)


def parse_debit_cards(html: str) -> list[dict]:
    """depozit.uz/cards/debet — bank nomi rowspan bilan bir nechta karta
    ustiga cho'zilgan, shu sabab keyingi qatorlar uchun oxirgi bank nomi
    saqlab qolinadi."""
    soup = BeautifulSoup(html, _PARSER)
    records = []
    current_bank = None

    for row in soup.select(_ROWS_SELECTOR)[1:]:
        cells = row.select("td")
        if len(cells) >= 5:
            current_bank = cells[1].get_text(strip=True)
            card_name, price, min_balance = (c.get_text(strip=True) for c in cells[2:5])
        elif len(cells) == 3:
            card_name, price, min_balance = (c.get_text(strip=True) for c in cells)
        else:
            continue

        if not current_bank or not card_name:
            continue

        records.append({
            "_bank_code": resolve_bank_code(current_bank),
            "bank_name": current_bank,
            "name": card_name,
            "source": _SOURCE,
            "category": "Debet karta",
            "Ochish narxi": price,
            "Minimal qoldiq": min_balance,
        })

    return dedupe_records(records)


def parse_bonds(html: str) -> list[dict]:
    """depozit.uz/bonds — obligatsiyalar reytingi (chiqaruvchi har doim ham
    bank emas, lekin resolve_bank_code baribir barqaror kod chiqaradi)."""
    soup = BeautifulSoup(html, _PARSER)
    records = []

    for row in soup.select(_ROWS_SELECTOR)[1:]:
        cells = row.select("td")
        if len(cells) < 5:
            continue

        issuer = cells[0].get_text(strip=True)
        if not issuer:
            continue

        records.append({
            "_bank_code": resolve_bank_code(issuer),
            "bank_name": issuer,
            "name": "Obligatsiya",
            "source": _SOURCE,
            "Foiz stavkasi": cells[1].get_text(strip=True),
            "Joriy narxi": cells[2].get_text(strip=True),
            "Nominal qiymati": cells[3].get_text(strip=True),
            "Muddati": cells[4].get_text(strip=True),
        })

    # depozit.uz manbasining o'zida ba'zan bitta obligatsiya qatori aynan
    # bir xil holda bir necha marta chiqadi — bizda takrorlanmasin.
    return dedupe_records(records)


def _tag_url(records: list[dict], url: str) -> list[dict]:
    """Har bir yozuvga shu jadval joylashgan haqiqiy sahifa manzilini qo'shadi
    (jadvalda qatorga xos alohida havola bo'lmagani uchun butun sahifaga
    yo'naltiramiz)."""
    for record in records:
        record["url"] = url
    return records


class DepozitCreditCardConnector(HtmlPageConnector):
    bank_code = "AGGREGATED"
    product_type = "card"
    segment = "individual"
    url = "https://depozit.uz/cards/credit"

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return _tag_url(parse_credit_cards(html), self.url)


class DepozitDebitCardConnector(HtmlPageConnector):
    bank_code = "AGGREGATED"
    product_type = "card"
    segment = "individual"
    url = "https://depozit.uz/cards/debet"

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return _tag_url(parse_debit_cards(html), self.url)


class DepozitBondConnector(HtmlPageConnector):
    bank_code = "AGGREGATED"
    product_type = "investment"
    segment = "individual"
    url = "https://depozit.uz/bonds"

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return _tag_url(parse_bonds(html), self.url)
