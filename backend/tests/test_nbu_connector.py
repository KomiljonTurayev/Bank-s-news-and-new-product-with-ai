from app.connectors.nbu import NBUCardConnector, NBUConnector, NBUCreditConnector, parse_credits, parse_deposits

DEPOSITS_HTML = """
<div class="product_19_items-wrapper">
  <div
    class="product_19_item-wrapper "
    data-is-milliy="1"
    data-proc="18"
    data-percent-app="18"
    data-min="100000"
    data-max="900000000"
    data-days="540"
    data-month="18"
    data-month-from="1"
    data-precent-month='[{"term":"1","interest":"13"}]'
    data-contrubutecost="sum"
  >
    <div class="product_19_item-content">
      <div class="product_19_item-title-wrapper">
        <div class="product_19_item-title">
          <h3 class="product_19_item-heading">Hamma uchun</h3>
        </div>
      </div>
      <div class="actions">
        <a href="/jismoniy-shaxslar-omonatlar/hamma-uchun" class="button">Omonat haqida batafsil</a>
      </div>
    </div>
  </div>
  <div
    class="product_19_item-wrapper "
    data-is-milliy="1"
    data-proc="0"
    data-percent-app=""
    data-min="1000"
    data-max="900000000"
    data-days="0"
    data-month=""
    data-month-from=""
    data-precent-month='[]'
    data-contrubutecost="sum"
  >
    <div class="product_19_item-content">
      <div class="product_19_item-title-wrapper">
        <div class="product_19_item-title">
          <h3 class="product_19_item-heading">Talab qilib olinguncha</h3>
        </div>
      </div>
      <div class="actions">
        <a href="/jismoniy-shaxslar-omonatlar/talab-qilib-olinguncha" class="button">Batafsil</a>
      </div>
    </div>
  </div>
  <div
    class="product_19_item-wrapper "
    data-is-milliy=""
    data-proc="2"
    data-percent-app="2"
    data-min="1"
    data-max="100000000"
    data-days="90"
    data-month="3"
    data-month-from=""
    data-precent-month="false"
    data-contrubutecost="evro"
  >
    <div class="product_19_item-content">
      <div class="product_19_item-title-wrapper">
        <div class="product_19_item-title">
          <h3 class="product_19_item-heading">Yevro</h3>
        </div>
      </div>
      <div class="actions">
        <a href="/jismoniy-shaxslar-omonatlar/evro" class="button">Batafsil</a>
      </div>
    </div>
  </div>
</div>
"""


def test_parse_deposits_extracts_rate_term_and_amount_range():
    records = parse_deposits(DEPOSITS_HTML)
    assert records[0] == {
        "name": "Hamma uchun",
        "source": "nbu.uz",
        "Valyuta": "So'm",
        "Foiz stavkasi": "18%",
        "Muddati": "1-18 oy",
        "Minimal summa": "100 000 so'm",
        "Maksimal summa": "900 000 000 so'm",
        "url": "https://nbu.uz/jismoniy-shaxslar-omonatlar/hamma-uchun",
    }


def test_parse_deposits_skips_rate_when_zero_percent():
    records = parse_deposits(DEPOSITS_HTML)
    on_demand = next(r for r in records if r["name"] == "Talab qilib olinguncha")
    assert "Foiz stavkasi" not in on_demand
    assert "Muddati" not in on_demand


def test_parse_deposits_maps_foreign_currency():
    records = parse_deposits(DEPOSITS_HTML)
    euro = next(r for r in records if r["name"] == "Yevro")
    assert euro["Valyuta"] == "Yevro"
    assert euro["Foiz stavkasi"] == "2%"
    assert euro["Muddati"] == "3 oy"
    assert euro["Maksimal summa"] == "100 000 000 EUR"


def test_connector_uses_nbu_bank_code_and_individual_segment():
    connector = NBUConnector()
    assert connector.bank_code == "NBU"
    assert connector.segment == "individual"
    assert connector.product_type == "deposit"


# Haqiqiy sahifada bir xil mahsulot to'plami bir necha marta (turli
# tab/filtrlarda) takrorlanadi — birinchi karta to'liq shartlar bilan,
# ikkinchisi (dublikat) xuddi shu nom/havola bilan, uchinchisi esa
# ro'yxatsiz reklama banneri (haqiqiy mahsulot emas).
CREDITS_HTML = """
<div class="feature_09_content">
  <div class="feature_09_title-wrapper">
    <div class="feature_09_title">
      <h4 class="feature_09_heading">Imtiyozli ipoteka</h4>
      <div class="feature_09_paragraph">
        <ul>
          <li><strong>Kredit stavkasi: </strong>yillik 16,5% dan</li>
          <li><strong>Kredit muddati:</strong> 240 oy</li>
        </ul>
      </div>
    </div>
  </div>
  <div class="actions"><a href="/jismoniy-shaxslarga-kreditlar/standard-ipoteka-krediti">Batafsil</a></div>
</div>
<div class="feature_09_content">
  <div class="feature_09_title-wrapper">
    <div class="feature_09_title">
      <h4 class="feature_09_heading">Imtiyozli ipoteka</h4>
      <div class="feature_09_paragraph">
        <ul>
          <li><strong>Kredit stavkasi: </strong>yillik 16,5% dan</li>
          <li><strong>Kredit muddati:</strong> 240 oy</li>
        </ul>
      </div>
    </div>
  </div>
  <div class="actions"><a href="/jismoniy-shaxslarga-kreditlar/standard-ipoteka-krediti">Batafsil</a></div>
</div>
<div class="feature_09_content">
  <div class="feature_09_title-wrapper">
    <div class="feature_09_title">
      <h4 class="feature_09_heading">Ko'chmas mulk bo'yicha hamkorlarga</h4>
    </div>
  </div>
  <div class="actions"><a href="https://ipoteka-pro.nbu.uz/">O'tish</a></div>
</div>
"""


def test_parse_credits_dedupes_repeated_cards_by_name_and_link():
    records = parse_credits(CREDITS_HTML)
    assert len(records) == 1
    assert records[0] == {
        "name": "Imtiyozli ipoteka",
        "source": "nbu.uz",
        "Kredit stavkasi": "yillik 16,5% dan",
        "Kredit muddati": "240 oy",
        "url": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/standard-ipoteka-krediti",
    }


def test_parse_credits_skips_banner_cards_without_a_stats_list():
    records = parse_credits(CREDITS_HTML)
    names = [r["name"] for r in records]
    assert "Ko'chmas mulk bo'yicha hamkorlarga" not in names


def test_credit_connector_builds_category_urls():
    connector = NBUCreditConnector(["ipoteka-kreditlari", "avtokreditlar"])
    assert connector.urls == [
        "https://nbu.uz/jismoniy-shaxslarga-kreditlar/ipoteka-kreditlari",
        "https://nbu.uz/jismoniy-shaxslarga-kreditlar/avtokreditlar",
    ]
    assert connector.bank_code == "NBU"
    assert connector.product_type == "credit"


# Haqiqiy sahifada (nbu.uz/jismoniy-shaxslarga-debet-kartalar) bir xil karta
# bir nechta tabda ("free", "premium" va h.k.) qayta ko'rsatiladi — kredit
# sahifasi bilan bir xil ``.feature_09_content`` shabloni.
CARDS_HTML = """
<section data-tab-content="free">
  <div class="feature_09_content">
    <div class="feature_09_title-wrapper">
      <div class="feature_09_title">
        <h4 class="feature_09_heading">UzCard Virtual</h4>
        <div class="feature_09_paragraph w-richtext">
          <p><p>Xavfsiz onlayn xarid qilish uchun bepul karta</p><ul>
            <li><strong>Muddat: </strong>5 yil</li>
            <li><strong>Summasi : </strong>Bepul</li>
            <li><strong>Karta valyutasi : </strong>UZS</li>
          </ul></p>
        </div>
      </div>
    </div>
    <div class="actions">
      <a href="/jismoniy-shaxslarga-debet-kartalar/uzcard-virtual">Batafsil</a>
      <a href="https://milliy.nbu.uz/">Ochish</a>
    </div>
  </div>
</section>
<section data-tab-content="premium">
  <div class="feature_09_content">
    <div class="feature_09_title-wrapper">
      <div class="feature_09_title">
        <h4 class="feature_09_heading">Mastercard World Elite</h4>
        <div class="feature_09_paragraph w-richtext">
          <p><p>Eng talabchan mijozlar uchun</p><ul>
            <li><strong>Muddat: </strong>5 yil</li>
            <li><strong>Summasi : </strong>700 000 so'm</li>
            <li><strong>Karta valyutasi : </strong>USD / UZS</li>
          </ul></p>
        </div>
      </div>
    </div>
    <div class="actions">
      <a href="/jismoniy-shaxslarga-debet-kartalar/mastercard-world-elite">Batafsil</a>
      <a href="https://milliy.nbu.uz/">Ochish</a>
    </div>
  </div>
  <!-- Bir xil karta boshqa tabda ham ko'rsatiladi -->
  <div class="feature_09_content">
    <div class="feature_09_title-wrapper">
      <div class="feature_09_title">
        <h4 class="feature_09_heading">UzCard Virtual</h4>
        <div class="feature_09_paragraph w-richtext">
          <p><p>Xavfsiz onlayn xarid qilish uchun bepul karta</p><ul>
            <li><strong>Muddat: </strong>5 yil</li>
            <li><strong>Summasi : </strong>Bepul</li>
            <li><strong>Karta valyutasi : </strong>UZS</li>
          </ul></p>
        </div>
      </div>
    </div>
    <div class="actions">
      <a href="/jismoniy-shaxslarga-debet-kartalar/uzcard-virtual">Batafsil</a>
      <a href="https://milliy.nbu.uz/">Ochish</a>
    </div>
  </div>
</section>
"""


def test_card_connector_uses_nbu_bank_code_and_default_url():
    connector = NBUCardConnector()
    assert connector.bank_code == "NBU"
    assert connector.product_type == "card"
    assert connector.segment == "individual"
    assert connector.url == "https://nbu.uz/jismoniy-shaxslarga-debet-kartalar"


def test_card_connector_parses_fee_term_and_currency_and_dedupes_across_tabs():
    connector = NBUCardConnector()
    records = connector.parse_html(CARDS_HTML, connector.base_url)

    assert len(records) == 2
    uzcard = next(r for r in records if r["name"] == "UzCard Virtual")
    assert uzcard == {
        "name": "UzCard Virtual",
        "source": "nbu.uz",
        "Muddat": "5 yil",
        "Summasi": "Bepul",
        "Karta valyutasi": "UZS",
        "url": "https://nbu.uz/jismoniy-shaxslarga-debet-kartalar/uzcard-virtual",
    }

    mastercard = next(r for r in records if r["name"] == "Mastercard World Elite")
    assert mastercard["Summasi"] == "700 000 so'm"
    assert mastercard["Karta valyutasi"] == "USD / UZS"


def test_card_connector_picks_first_actions_link_not_the_open_link():
    connector = NBUCardConnector()
    records = connector.parse_html(CARDS_HTML, connector.base_url)
    uzcard = next(r for r in records if r["name"] == "UzCard Virtual")
    assert uzcard["url"].endswith("/uzcard-virtual")
    assert "milliy.nbu.uz" not in uzcard["url"]
