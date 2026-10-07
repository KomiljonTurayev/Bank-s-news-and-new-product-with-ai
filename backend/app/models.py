from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CustomProduct(Base):
    """Foydalanuvchi kiritgan, hali bozorda haqiqiy taklif sifatida
    tasdiqlanmagan mahsulot g'oyasi — bozordagi mavjud BankRate
    yozuvlariga solishtirib, AI tahlili shu asosda hisoblanadi."""

    __tablename__ = "custom_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    product_type: Mapped[str] = mapped_column(String(30), index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(300), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")
    rate: Mapped[float] = mapped_column(Float)
    min_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_payment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Login (ONE-ID) olib tashlanganidan oldingi yozuvlar uchun saqlangan
    # tarixiy ustun — yangi yozuvlarda NULL, filtrlashda ishlatilmaydi.
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "product_type": self.product_type,
            "category": self.category,
            "bank_name": self.bank_name,
            "purpose": self.purpose,
            "currency": self.currency,
            "rate": self.rate,
            "min_amount": self.min_amount,
            "max_amount": self.max_amount,
            "term_months": self.term_months,
            "initial_payment_pct": self.initial_payment_pct,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


class BankRate(Base):
    __tablename__ = "bank_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_code: Mapped[str] = mapped_column(String(30), index=True)
    product_type: Mapped[str] = mapped_column(String(30), index=True)
    segment: Mapped[str] = mapped_column(String(20), default="individual", index=True)
    data: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        # /api/rates/latest har doim shu to'rttala ustun bo'yicha guruhlab,
        # eng so'nggi fetched_at'ni qidiradi — composite indeks bu so'rovni
        # to'rtta alohida indeksni birlashtirishdan ancha tezlashtiradi.
        Index("ix_bank_rates_latest_lookup", "bank_code", "product_type", "segment", "fetched_at"),
    )
