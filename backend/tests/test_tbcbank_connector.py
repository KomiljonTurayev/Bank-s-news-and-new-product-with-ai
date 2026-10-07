from app.connectors.tbcbank import TBCBankConnector, parse_deposits

DEPOSITS_HTML = """
<div data-block-type="blocks.image-with-text-tabs-block">
  <h4 data-testid="text">Muddatli omonat</h4>
  <ul data-testid="list">
    <li><h4 data-testid="text">Muddati</h4><h4 data-testid="text">3 oydan 24 oygacha</h4></li>
    <li><h4 data-testid="text">Stavkasi</h4><h4 data-testid="text">18% gacha</h4></li>
  </ul>
</div>
<div data-block-type="blocks.image-with-text-block">
  <h4 data-testid="text">"Odat" omonati</h4>
  <ul data-testid="list">
    <li><h4 data-testid="text">Muddati</h4><h4 data-testid="text">Cheklanmagan</h4></li>
    <li><h4 data-testid="text">Stavkasi</h4><h4 data-testid="text">13%</h4></li>
  </ul>
</div>
<div data-block-type="blocks.image-with-text-block">
  <h4 data-testid="text">Ishonchli va kafolatlangan onlayn omonatlar</h4>
</div>
<div data-block-type="blocks.deposit-calculator-form-block">
  <button type="button">3 oy (18%)</button>
  <button type="button">6 oy (18%)</button>
  <button type="button">13 oy (17%)</button>
  <button type="button">24 oy (16%)</button>
  <button type="button">Omonat ochish</button>
</div>
"""


def test_parse_deposits_reads_summary_cards():
    records = parse_deposits(DEPOSITS_HTML)
    named = {r["name"]: r for r in records}
    assert named["Muddatli omonat"]["Stavkasi"] == "18% gacha"
    assert named['"Odat" omonati']["Stavkasi"] == "13%"


def test_parse_deposits_skips_cards_with_no_stats():
    records = parse_deposits(DEPOSITS_HTML)
    names = [r["name"] for r in records]
    assert "Ishonchli va kafolatlangan onlayn omonatlar" not in names


def test_parse_deposits_expands_calculator_terms_into_separate_records():
    records = parse_deposits(DEPOSITS_HTML)
    term_records = [r for r in records if "oy)" in r["name"]]
    assert len(term_records) == 4
    thirteen_month = next(r for r in term_records if r["Muddati"] == "13 oy")
    assert thirteen_month["Foiz stavkasi"] == "17%"


def test_parse_deposits_ignores_non_term_buttons():
    records = parse_deposits(DEPOSITS_HTML)
    names = [r["name"] for r in records]
    assert not any("Omonat ochish" in n for n in names)


def test_connector_uses_tbc_bank_code_and_individual_segment():
    connector = TBCBankConnector()
    assert connector.bank_code == "TBC"
    assert connector.segment == "individual"
    assert connector.product_type == "deposit"
