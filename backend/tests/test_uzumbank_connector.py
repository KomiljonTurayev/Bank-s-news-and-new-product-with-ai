from app.connectors.uzumbank import UzumBankConnector, parse_deposits

# Haqiqiy sahifaning soddalashtirilgan nusxasi — stavka/summa/muddat
# alohida data-atributlarda emas, erkin matn jumlalarida keladi (Astro
# landing sahifasi, boshqa banklardagi kabi karta ro'yxati emas).
DEPOSITS_HTML = """
<html><body>
<h1><span class="selected">16% yillik daromad</span> bilan qulay shartli omonat</h1>
<p>Omonatning minimal summasi - 500 000 so'm</p>
<p>Butun muddat - 9 oy davomida omonatni to'ldiring va pul yeching</p>
<p>Omonat bo'yicha foiz stavkasi — 15%. Foizlar har kuni qo'shib boriladi.</p>
<p>Agar mablag' jamg'arishda davom etishni istasangiz, minimal summa — kamida 500 000 so'm qolishi kerak.</p>
</body></html>
"""


def test_parse_deposits_extracts_rate_amount_and_term():
    records = parse_deposits(DEPOSITS_HTML, url="https://uzumbank.uz/uz/deposits/")
    assert records == [
        {
            "name": "Qulay shartli omonat",
            "source": "uzumbank.uz",
            "url": "https://uzumbank.uz/uz/deposits/",
            "Foiz stavkasi": "15%",
            "Minimal summa": "500 000 so'm",
            "Muddati": "9 oy",
        }
    ]


def test_parse_deposits_returns_empty_when_rate_sentence_is_missing():
    records = parse_deposits("<html><body><h1>Boshqa sahifa</h1></body></html>")
    assert records == []


def test_connector_defaults_to_the_deposits_page():
    connector = UzumBankConnector()
    assert connector.url == "https://uzumbank.uz/uz/deposits/"
    assert connector.bank_code == "UZUM"
    assert connector.product_type == "deposit"
