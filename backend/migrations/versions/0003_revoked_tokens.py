"""revoked_tokens — logout revokatsiyasini doimiy saqlash

Bekor qilingan tokenlar avval faqat jarayot xotirasida (`app/auth.py`
dastlabki `_revoked_tokens` to'plami) edi: server qayta ishga tushganda
ro'yxat tozalanib, "chiqqan" foydalanuvchining tokeni o'z 30 kunlik
muddatigacha yana amal qila boshlardi. Endi shu jadvalda turadi — restart
va bir nechta worker/instance holatlarida ham revoke saqlanadi.

Xom token EMAS, SHA-256 hash'i saqlanadi (app/models.py:RevokedToken
docstring'ida sababi). `expires_at` tozalash uchun kerak: token tabiiy
muddati tugagach qatorning keragi qolmaydi.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
