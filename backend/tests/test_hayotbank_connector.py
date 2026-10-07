from app.connectors.hayotbank import HayotBankConnector, parse_credits

CREDITS_HTML = """
<div class="hb-card deposit-item">
  <h2 class="deposit-item-title">Mikroqarz "Yaxshisi"</h2>
  <p class="deposit-item-description">Shaxsiy ehtiyojlar uchun samarali yechim</p>
  <div class="info">
    <div class="d-grid"><p class="fw-700 fs-24">10 kun</p><p class="opacity-06 fw-500">Foizsiz davr</p></div>
    <div class="d-grid"><p class="fw-700 fs-24">100 mln so'mgacha</p><p class="opacity-06 fw-500">Maksimal miqdor</p></div>
    <div class="d-grid"><p class="fw-700 fs-24">48 oygacha</p><p class="opacity-06 fw-500">Kredit muddati</p></div>
  </div>
  <button routerlink="yaxshisi">Batafsil</button>
</div>
"""


def test_parse_credits_extracts_stat_pairs_and_builds_relative_url():
    records = parse_credits(CREDITS_HTML, "https://hayotbank.uz/main/individual/credit")
    assert records == [
        {
            "name": 'Mikroqarz "Yaxshisi"',
            "source": "hayotbank.uz",
            "Foizsiz davr": "10 kun",
            "Maksimal miqdor": "100 mln so'mgacha",
            "Kredit muddati": "48 oygacha",
            "url": "https://hayotbank.uz/main/individual/credit/yaxshisi",
        }
    ]


def test_connector_uses_hayot_bank_code_and_credit_product_type():
    connector = HayotBankConnector()
    assert connector.bank_code == "HAYOT"
    assert connector.product_type == "credit"
    assert connector.segment == "individual"
