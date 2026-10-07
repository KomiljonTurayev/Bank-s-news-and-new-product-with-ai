from app.offer_facets import offer_facets


def test_credit_facets_infer_category_term_and_limit():
    facets = offer_facets("credit", {"name": "Avtokredit Nexia", "Foiz": "24%", "Muddati": "4 yil", "Summa": "300 mln so'mgacha"})
    assert facets == {
        "currency": "UZS",
        "term_months": 48,
        "min_amount": None,
        "max_amount": 300_000_000,
        "category": "Avtokredit",
    }


def test_credit_facets_keep_source_category_and_fallback():
    assert offer_facets("credit", {"name": "X", "category": "Ipoteka"})["category"] == "Ipoteka"
    assert offer_facets("credit", {"name": "ADM Global I"})["category"] == "Boshqa"


def test_deposit_facets_currency_online_kids():
    facets = offer_facets("deposit", {"name": "Onlayn omonat", "Valyuta": "USD", "Muddati": "12 oy"})
    assert facets["currency"] == "USD" and facets["online"] and not facets["kids"] and facets["term_months"] == 12
    assert offer_facets("deposit", {"name": "Bolalar xazinasi"})["kids"]


def test_card_facets_type_and_network():
    assert offer_facets("card", {"name": "Visa Classic"}) == {"currency": "UZS", "card_type": "debit", "network": "Visa"}
    credit = offer_facets("card", {"name": "Humo kredit kartasi"})
    assert credit["card_type"] == "credit" and credit["network"] == "Humo"


def test_currency_rows_have_no_facets():
    assert offer_facets("currency", {"code": "USD"}) == {}
