from app.connectors.base import BaseConnector
from app.models import BankRate


class FakeConnector(BaseConnector):
    bank_code = "TESTBANK"
    product_type = "deposit"
    segment = "individual"

    def __init__(self, records):
        self._records = records

    def fetch_raw(self):
        return None

    def parse(self, raw):
        return self._records

    def run_with_records(self, records):
        self._records = records
        return self.run()


def test_run_stores_one_row_per_record(session_factory):
    connector = FakeConnector([{"name": "A", "rate": "10%"}, {"name": "B", "rate": "12%"}])

    result = connector.run()

    assert result.total == 2
    assert result.inserted == 2
    assert result.unchanged == 0
    assert int(result) == 2  # eski chaqiruvchilar bilan moslik uchun
    with session_factory() as session:
        rows = session.query(BankRate).all()
        assert len(rows) == 2
        assert {r.bank_code for r in rows} == {"TESTBANK"}
        assert {r.product_type for r in rows} == {"deposit"}
        assert {r.segment for r in rows} == {"individual"}


def test_run_uses_per_record_bank_code_override(session_factory):
    connector = FakeConnector([
        {"_bank_code": "SQB", "name": "Omonat-1"},
        {"_bank_code": "XB", "name": "Omonat-2"},
    ])

    connector.run()

    with session_factory() as session:
        rows = {r.bank_code: r.data for r in session.query(BankRate).all()}
        assert rows["SQB"]["name"] == "Omonat-1"
        assert rows["XB"]["name"] == "Omonat-2"
        # ichki "_bank_code" maydoni saqlanmasligi kerak
        assert "_bank_code" not in rows["SQB"]


def test_run_uses_per_record_segment_override(session_factory):
    connector = FakeConnector([{"_segment": "business", "name": "Yuridik omonat"}])

    connector.run()

    with session_factory() as session:
        row = session.query(BankRate).one()
        assert row.segment == "business"
        assert row.bank_code == "TESTBANK"  # default holicha qoladi


def test_run_touches_fetched_at_instead_of_duplicating_unchanged_data(session_factory):
    connector = FakeConnector([{"name": "A", "rate": "10%"}])

    connector.run_with_records([{"name": "A", "rate": "10%"}])
    with session_factory() as session:
        first_fetched_at = session.query(BankRate).one().fetched_at

    result = connector.run_with_records([{"name": "A", "rate": "10%"}])

    assert result.inserted == 0
    assert result.unchanged == 1
    with session_factory() as session:
        rows = session.query(BankRate).all()
        assert len(rows) == 1
        assert rows[0].fetched_at >= first_fetched_at


def test_run_inserts_new_row_when_data_changes(session_factory):
    connector = FakeConnector([])

    connector.run_with_records([{"name": "A", "rate": "10%"}])
    result = connector.run_with_records([{"name": "A", "rate": "12%"}])

    assert result.inserted == 1
    assert result.unchanged == 0
    with session_factory() as session:
        rows = session.query(BankRate).all()
        assert len(rows) == 2
        assert {r.data["rate"] for r in rows} == {"10%", "12%"}


def test_run_ignores_record_order_when_comparing_for_dedup(session_factory):
    connector = FakeConnector([])

    connector.run_with_records([{"name": "A"}, {"name": "B"}])
    connector.run_with_records([{"name": "B"}, {"name": "A"}])

    with session_factory() as session:
        rows = session.query(BankRate).all()
        assert len(rows) == 2
