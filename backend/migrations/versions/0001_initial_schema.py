"""initial schema: bank_rates + custom_products (idempotent)

Loyihada migratsiyalar bo'lmagan oldin — sxema `create_all()` bilan
yashagan. Shu sabab bu birinchi rev MAXSUS idempotent yozilgan: mavjud
`bank_news.db` (yoki istalgan eski bazaga) birinchi marta qo'llaganda
"table already exists" bermaydi, bo'sh bazaga esa to'liq sxema yaratadi.
Avtomatik `stamp` bosqichi talab qilinmaydi.

Revision ID: 0001
Revises:
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _schema() -> sa.MetaData:
    """app/models.py sxemasining migratsiya-havolasidagi nusxasi
    (models o'zgarsa — yangi rev qo'shiladi, bu rev GA'yrilar)."""
    md = sa.MetaData()

    sa.Table(
        "bank_rates",
        md,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_code", sa.String(length=30), nullable=False),
        sa.Column("product_type", sa.String(length=30), nullable=False),
        sa.Column("segment", sa.String(length=20), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Index("ix_bank_rates_latest_lookup", "bank_code", "product_type", "segment", "fetched_at"),
        sa.Index("ix_bank_rates_bank_code", "bank_code"),
        sa.Index("ix_bank_rates_product_type", "product_type"),
        sa.Index("ix_bank_rates_segment", "segment"),
        sa.Index("ix_bank_rates_fetched_at", "fetched_at"),
    )

    sa.Table(
        "custom_products",
        md,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("product_type", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("bank_name", sa.String(length=200), nullable=True),
        sa.Column("purpose", sa.String(length=300), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("min_amount", sa.Float(), nullable=True),
        sa.Column("max_amount", sa.Float(), nullable=True),
        sa.Column("term_months", sa.Integer(), nullable=True),
        sa.Column("initial_payment_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Index("ix_custom_products_product_type", "product_type"),
        sa.Index("ix_custom_products_created_at", "created_at"),
    )

    return md


def upgrade() -> None:
    bind = op.get_bind()
    md = _schema()
    for table in md.sorted_tables:
        table.create(bind=bind, checkfirst=True)
        for index in table.indexes:
            index.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    md = _schema()
    for table in reversed(md.sorted_tables):
        table.drop(bind=bind, checkfirst=True)
