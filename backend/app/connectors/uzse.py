"""uzse.uz — "Toshkent" Respublika fond birjasi, O'zbekistondagi yagona
rasmiy fond birjasi. Korporativ obligatsiyalarning to'liq ro'yxati
(``/bonds2``) — bir nechta banklar EMAS bank bo'lgan kompaniya
(mikromoliya tashkilotlari, lizing kompaniyalari va h.k.) uchun ham
obligatsiya ma'lumotini o'z ichiga oladi. Sahifa client-tomonda render
qilinadi, shu bois Playwright orqali ochiladi.

Diqqat: emitent nomidan ``resolve_bank_code()`` orqali chiqarilgan kod
ba'zan depozit.uz'dan kelgan mavjud kod bilan mos kelmasligi mumkin —
masalan bir manbada "X MMT MChJ", ikkinchisida "X AJ MMT" kabi yuridik
shakl qisqartmasi tartibi boshqacha bo'lishi yoki umuman boshqa yuridik
shakl (AJ/MChJ) ko'rsatilishi mumkin. Bunday holatlarni qo'lda "bir xil
kompaniya" deb faraz qilib zo'rma-zo'raki bitta kodga birlashtirish xato
ma'lumot biriktirish xavfini tug'diradi, shu bois bu yerga HECH QANDAY
MAXSUS ALIAS QO'SHILMAGAN — ``resolve_bank_code()``ning umumiy
(slugify) qoidasi qanday natija bersa, shu qabul qilinadi. Ba'zan bir
xil real kompaniya ikki xil kod ostida ko'rinishi mumkin — bu xato
emas, manbalar orasidagi nom yozilishi farqini halol aks ettirish."""

from bs4 import BeautifulSoup

from app.banks import resolve_bank_code
from app.connectors.base import RenderedPageConnector
from app.connectors.html_cards import dedupe_records

_URL = "https://uzse.uz/bonds2?locale=uz"
_SOURCE = "uzse.uz"


def parse_bonds(html: str, url: str = _URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table")
    if not table:
        return []

    records = []
    for row in table.select("tr")[1:]:
        cells = row.select("td")
        if len(cells) < 11:
            continue

        issuer = cells[1].get_text(strip=True)
        ticker = cells[2].get_text(strip=True)
        if not issuer or not ticker:
            continue

        records.append({
            "_bank_code": resolve_bank_code(issuer),
            "bank_name": issuer,
            "name": ticker,
            "source": _SOURCE,
            "ISIN": cells[3].get_text(strip=True),
            "Nominal qiymati": cells[4].get_text(strip=True),
            "Miqdori": cells[5].get_text(strip=True),
            "Emissiya hajmi": cells[6].get_text(strip=True),
            "Kupon stavkasi": cells[7].get_text(strip=True),
            "Ro'yxatga olingan sana": cells[8].get_text(strip=True),
            "To'lov muddati": cells[9].get_text(strip=True),
            "Holati": cells[10].get_text(strip=True),
            "url": url,
        })

    # Sahifa bir necha marta (masalan mobil/desktop razmetkasi) bir xil
    # qatorni takrorlashi mumkin.
    return dedupe_records(records)


class UzseBondConnector(RenderedPageConnector):
    bank_code = "AGGREGATED"
    product_type = "investment"
    segment = "individual"
    url = _URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_bonds(html, self.url)
