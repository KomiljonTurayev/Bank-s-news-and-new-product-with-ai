from app.connectors.tayanchbank import TayanchBankConnector, parse_products

DEPOSITS_HTML = """
<div class="card">
  <span>Omonat</span>
  <h3>Tayanchim</h3>
  <div class="flex items-center gap-0">
    <div class="flex flex-col">
      <span>Minimal miqdor</span>
      <div class="flex items-baseline gap-2"><span>100</span><span>ming so'm</span></div>
    </div>
    <div class="flex flex-col">
      <span>Foiz stavkasi</span>
      <div class="flex items-baseline gap-2"><span>23</span><span>%</span></div>
    </div>
  </div>
  <a href="/uz/private/deposits/tayanchim#productInfo"><span>Batafsil</span></a>
  <a href="/uz/private/deposits/tayanchim"><span>Batafsil</span></a>
</div>
"""

CREDITS_HTML = """
<div class="card">
  <span>Mikrokredit</span>
  <h3>Ishonchli Qadam</h3>
  <div class="flex items-center gap-0">
    <div class="flex flex-col">
      <span>Minimal miqdor</span>
      <div class="flex items-baseline gap-2"><span>100 000 000</span><span>so'm</span></div>
    </div>
  </div>
  <a href="/uz/business/business-credits/ishonchli-qadam"><span>Batafsil</span></a>
</div>
"""


def test_parse_products_extracts_stats_and_dedupes_repeated_links():
    records = parse_products(DEPOSITS_HTML, "/uz/private/deposits/")
    assert records == [
        {
            "name": "Tayanchim",
            "source": "tayanchbank.uz",
            "url": "https://tayanchbank.uz/uz/private/deposits/tayanchim",
            "Minimal miqdor": "100 ming so'm",
            "Foiz stavkasi": "23 %",
        }
    ]


def test_parse_products_ignores_cards_linking_outside_the_expected_prefix():
    # Bu karta jismoniy shaxslar sahifasida ko'rinsa-da, havolasi
    # /uz/business/... bilan boshlangani uchun yuridik shaxslar
    # mahsuloti — /uz/private/credits/ prefiksi bilan qidirilganda
    # topilmasligi kerak.
    records = parse_products(CREDITS_HTML, "/uz/private/credits/")
    assert records == []


# Haqiqiy sahifada bir nechta havola nusxasi (mobil/desktop yoki
# kalkulyator bo'limi uchun) turli chuqurlikda joylashadi — ba'zilari
# faqat yuqorida, ikkita mahsulotni ham o'z ichiga olgan umumiy o'ramga
# ko'tarilgandan keyingina <h3> topadi. Bunday "juda keng" o'ram rad
# etilishi va faqat aniq bitta mahsulotga tegishli tor o'ram qabul
# qilinishi kerak — aks holda ikkinchi mahsulotning statistikasi
# birinchisiga aralashib qolar edi.
MULTI_PRODUCT_PAGE_HTML = """
<section>
  <div class="wide-wrapper">
    <div class="card-a">
      <h3>Oila Tayanchi</h3>
      <div class="flex items-center gap-0">
        <div class="flex flex-col">
          <span>Minimal miqdor</span>
          <div class="flex items-baseline gap-2"><span>25 000 000</span><span>so'm</span></div>
        </div>
        <div class="flex flex-col">
          <span>Foiz stavkasi</span>
          <div class="flex items-baseline gap-2"><span>23-38</span><span>%</span></div>
        </div>
      </div>
      <a href="/uz/private/credits/oila-tayanchi"><span>Batafsil</span></a>
    </div>
    <div class="card-b">
      <h3>Boshqa mahsulot</h3>
      <div class="flex flex-col">
        <span>Minimal miqdor</span>
        <div class="flex items-baseline gap-2"><span>999</span><span>so'm</span></div>
      </div>
    </div>
  </div>
  <a href="/uz/private/credits/oila-tayanchi"><span>Yashirin nusxa</span></a>
</section>
"""


def test_parse_products_does_not_merge_stats_from_a_sibling_product_card():
    records = parse_products(MULTI_PRODUCT_PAGE_HTML, "/uz/private/credits/")
    assert records == [
        {
            "name": "Oila Tayanchi",
            "source": "tayanchbank.uz",
            "url": "https://tayanchbank.uz/uz/private/credits/oila-tayanchi",
            "Minimal miqdor": "25 000 000 so'm",
            "Foiz stavkasi": "23-38 %",
        }
    ]


def test_connector_picks_section_by_product_type():
    deposit_connector = TayanchBankConnector("deposit")
    assert deposit_connector.url == "https://tayanchbank.uz/uz/private/deposits"
    assert deposit_connector.bank_code == "TAYANCH"

    credit_connector = TayanchBankConnector("credit")
    assert credit_connector.url == "https://tayanchbank.uz/uz/private/credits"
