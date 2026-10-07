"""Bir nechta bank (Turonbank, Poytaxtbank, Aloqabank, Mikrokreditbank —
hammasi bir xil Bitrix veb-ustaxonasi qurgan ko'rinadi) bir xil "ochiq
ma'lumotlar" moduliga ega: ``/uz/services/open_data/rates/json/``
bir xil G1-G5 sxemasi bilan JSON qaytaradi — G1 sana, G2 kanal
(``BANK``=filial, ``APP``=mobil ilova, ``ATM``, ``IMT``), G3 valyuta
kodi, G4 bankning xarid narxi ("Sotib olish"), G5 sotish narxi
("Sotish"). Bu boshqa banklardagi kabi scraping emas — rasmiy,
hujjatlashtirilgan ochiq ma'lumotlar xizmati, shu bois parser bitta
umumiy joyda saqlanadi va har bir bank shu klassni faqat o'z domeni
bilan qayta ishlatadi."""

from app.connectors.base import JsonApiConnector
from app.connectors.exchange import rate_pair


def parse_open_data_rates(raw: list[dict], url: str, source: str) -> list[dict]:
    records = []
    for item in raw:
        if item.get("G2") != "BANK":
            continue
        buy_text, sell_text = item.get("G4"), item.get("G5")
        try:
            buy_rate = float(buy_text) if buy_text and buy_text != "-" else None
            sell_rate = float(sell_text) if sell_text and sell_text != "-" else None
        except (TypeError, ValueError):
            continue
        records.extend(rate_pair(item.get("G3"), buy_rate, sell_rate, source=source, url=url))

    return records


class OpenDataRatesConnector(JsonApiConnector):
    product_type = "currency"
    segment = "individual"

    def __init__(self, bank_code: str, base_url: str, source: str):
        self.bank_code = bank_code
        self.url = f"{base_url}/uz/services/open_data/rates/json/"
        self.api_url = self.url
        self.source = source

    def parse_payload(self, payload: list[dict], url: str) -> list[dict]:
        return parse_open_data_rates(payload, url, self.source)
