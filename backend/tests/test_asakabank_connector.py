from app.connectors.asakabank import AsakabankConnector, parse_products

PRODUCTS_HTML = """
<div role="tabpanel" id="panel-all">
  <div class="ui-card">
    <h1>Maksimal foyda</h1>
    <div class="product-description-list">
      <div><h1>13 oygacha</h1><p>Saqlash muddati</p></div>
      <div><h1>14% gacha</h1><p>Depozit bo'yicha foizlar</p></div>
      <div><h1>100 000 so'm</h1><p>Minimal miqdor</p></div>
    </div>
    <a href="/uz/physical-persons/deposits/maksimal-foyda">Batafsil</a>
  </div>
  <div class="ui-card">
    <h1>Onlayn Avtokredit</h1>
    <div class="product-description-list">
      <div><h1>60 oygacha</h1><p>Kredit muddati</p></div>
      <div><h1>18.9 % dan</h1><p>Foiz stavkasi</p></div>
    </div>
    <a href="/uz/physical-persons/credits/onlayn-avtokredit">Batafsil</a>
  </div>
</div>
<div role="tabpanel" id="panel-foreign" hidden>
  <div class="ui-card">
    <h1>Maksimal foyda (USD)</h1>
    <div class="product-description-list">
      <div><h1>24 oygacha</h1><p>Saqlash muddati</p></div>
    </div>
    <a href="/uz/physical-persons/deposits/maksimal-foyda-usd">Batafsil</a>
  </div>
</div>
"""

# "UzukPay" kabi ayrim kartalar xuddi shu ".product-description-list"
# klassini reklama matni uchun ishlatadi — sarlavha (qisqa) h1'da, tavsif
# (uzun) esa p'da, ya'ni haqiqiy stavka/muddat maydonlariga teskari tartibda.
CARD_WITH_MARKETING_BLOCK_HTML = """
<div role="tabpanel" id="panel-all">
  <div class="ui-card">
    <h1>UzukPay</h1>
    <div class="product-description-list">
      <div><h1>15 daqiqa</h1><p>karta tayyorlash</p></div>
      <div>
        <h1>Qulay va doimo qo'l ostida</h1>
        <p>To'lov uchun hamyon yoki telefon izlash shart emas. UzukPay doimo qo'lingizda bo'ladi — uni quvvatlash, ulash yoki qo'shimcha sozlash talab etilmaydi.</p>
      </div>
    </div>
    <a href="/uz/physical-persons/cards/payring">Batafsil</a>
  </div>
</div>
"""


def test_parse_products_reads_only_the_visible_tabpanel():
    records = parse_products(PRODUCTS_HTML)
    names = [r["name"] for r in records]
    assert names == ["Maksimal foyda", "Onlayn Avtokredit"]
    assert "Maksimal foyda (USD)" not in names


def test_parse_products_maps_stat_labels_directly_as_keys():
    records = parse_products(PRODUCTS_HTML)
    deposit = records[0]
    assert deposit == {
        "name": "Maksimal foyda",
        "source": "asakabank.uz",
        "Saqlash muddati": "13 oygacha",
        "Depozit bo'yicha foizlar": "14% gacha",
        "Minimal miqdor": "100 000 so'm",
        "url": "https://asakabank.uz/uz/physical-persons/deposits/maksimal-foyda",
    }


def test_parse_products_handles_credit_labels_too():
    records = parse_products(PRODUCTS_HTML)
    credit = records[1]
    assert credit["Kredit muddati"] == "60 oygacha"
    assert credit["Foiz stavkasi"] == "18.9 % dan"


def test_parse_products_skips_long_marketing_text_blocks():
    records = parse_products(CARD_WITH_MARKETING_BLOCK_HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "UzukPay",
        "source": "asakabank.uz",
        "karta tayyorlash": "15 daqiqa",
        "url": "https://asakabank.uz/uz/physical-persons/cards/payring",
    }


def test_connector_uses_asaka_bank_code_and_individual_segment():
    connector = AsakabankConnector("deposit", "https://asakabank.uz/uz/physical-persons/deposits")
    assert connector.bank_code == "ASAKA"
    assert connector.segment == "individual"
    assert connector.product_type == "deposit"
