"""add created_by to custom_products (per-user product privacy)

ONE-ID orqali kirgan foydalanuvchining doimiy identifikatorini (JWT `sub`,
app/auth.py:create_token) saqlaydi — shu orqali har kim faqat o'zi
yaratgan mahsulotlarni ko'radi/o'chira oladi (app/routers/products.py).
Parol darvozasi orqali (yoki bu ustun qo'shilishidan OLDIN) yaratilgan
yozuvlar NULL bo'lib qoladi — umumiy/anonim havzada.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("custom_products", sa.Column("created_by", sa.String(length=200), nullable=True))
    op.create_index("ix_custom_products_created_by", "custom_products", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_custom_products_created_by", table_name="custom_products")
    op.drop_column("custom_products", "created_by")
