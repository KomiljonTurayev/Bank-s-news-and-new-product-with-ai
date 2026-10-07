from app.connectors.base import JsonApiConnector

_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/"
_API_URL = f"{_URL}json/"


class CBUConnector(JsonApiConnector):
    """O'zbekiston Markaziy banki rasmiy valyuta kursi API'si. Rasmiy API bor
    banklar uchun namuna — scraping shart emas."""

    bank_code = "CBU"
    product_type = "currency"
    url = _URL
    api_url = _API_URL

    def parse_payload(self, payload: list[dict], url: str) -> list[dict]:
        return [
            {"code": item["Ccy"], "rate": float(item["Rate"]), "date": item["Date"], "url": url}
            for item in payload
        ]
