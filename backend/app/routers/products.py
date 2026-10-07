"""`/api/products/*` — foydalanuvchi kiritgan mahsulot g'oyalarini
boshqarish va ularni bozordagi haqiqiy takliflar bilan solishtirib tahlil
qilish."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import select

from app.banks import PRODUCT_TYPES
from app.db import SessionLocal
from app.models import CustomProduct
from app.product_analysis import Lang, analyze_product, top_market_offers
from app.product_recommendation import RecommendationError, recommend_products
from app.rate_limiter import RateLimiter
from app.schemas import (
    CustomProductIn,
    CustomProductOut,
    CustomProductPatch,
    MarketLeaderOut,
    ProductWithAnalysisOut,
    RecommendationIn,
    RecommendationOut,
)

router = APIRouter(prefix="/api/products", tags=["products"])

_CUSTOM_PRODUCT_TYPES = {p["code"] for p in PRODUCT_TYPES if p["code"] != "currency"}

# Hisob tizimi yo'qligi sababli haqiqiy egalik tekshiruvi mavjud emas — hech
# bo'lmasa bitta IP manzil /api/products'ni spam yozuvlar bilan cheksiz
# to'ldirib, DoS holatiga olib kelishining oldini olamiz (20 ta/soatiga).
_create_product_limiter = RateLimiter(limit=20, window_seconds=3600)

# Tahrirlash bazaga yangi qator qo'shmaydi, shu bois yaratishdagidan kengroq
# limit bilan cheklanadi — maqsad baribir shu: bitta IPdan cheksiz yozuv.
_update_product_limiter = RateLimiter(limit=60, window_seconds=3600)

# AI tavsiyasi har chaqiruvda pullik tashqi API'ga boradi — bitta IPdan
# cheksiz so'rov xarajatni portlatmasin.
_recommend_limiter = RateLimiter(limit=10, window_seconds=3600)

# PATCH bilan almashtiriladigan maydonlar (created_at / created_by tashqarida).
_EDITABLE_FIELDS = (
    "name",
    "product_type",
    "category",
    "bank_name",
    "purpose",
    "currency",
    "rate",
    "min_amount",
    "max_amount",
    "term_months",
    "initial_payment_pct",
)


def _get_or_404(session, product_id: int) -> CustomProduct:
    product = session.get(CustomProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    return product


@router.post(
    "",
    status_code=201,
    response_model=CustomProductOut,
    summary="Yangi mahsulot g'oyasini qo'shish",
    responses={
        400: {"description": "Noto'g'ri mahsulot turi"},
        429: {"description": "Juda ko'p so'rov — bitta IP manzildan soatiga 20 tadan ortiq yaratib bo'lmaydi"},
    },
)
def create_product(payload: CustomProductIn, request: Request):
    """Foydalanuvchi kiritgan yangi mahsulot g'oyasini saqlaydi — bazaviy
    ma'lumotlar keyinchalik /api/products/{id} orqali bizning bazamizdagi
    haqiqiy takliflar bilan solishtirilib, AI tahlili chiqariladi."""
    if payload.product_type not in _CUSTOM_PRODUCT_TYPES:
        raise HTTPException(status_code=400, detail="Noto'g'ri mahsulot turi")

    client_ip = request.client.host if request.client else "unknown"
    if not _create_product_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Juda ko'p so'rov — birozdan so'ng qayta urinib ko'ring",
            headers={"Retry-After": str(_create_product_limiter.retry_after(client_ip))},
        )

    with SessionLocal() as session:
        product = CustomProduct(
            name=payload.name,
            product_type=payload.product_type,
            category=payload.category,
            bank_name=payload.bank_name,
            purpose=payload.purpose,
            currency=payload.currency,
            rate=payload.rate,
            min_amount=payload.min_amount,
            max_amount=payload.max_amount,
            term_months=payload.term_months,
            initial_payment_pct=payload.initial_payment_pct,
            created_at=datetime.now(timezone.utc),
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product.to_dict()


@router.post(
    "/recommend",
    response_model=RecommendationOut,
    summary="AI orqali yangi mahsulot tavsiya qilish",
    responses={
        404: {"description": "Bu turdagi bozor takliflari bazada yo'q"},
        422: {"description": "Maqsad matni nojo'ya yoki bank sohasiga aloqasiz"},
        429: {"description": "Juda ko'p so'rov — bitta IP manzildan soatiga 10 tadan ortiq emas"},
        502: {"description": "AI xizmati javob bermadi yoki rad etdi"},
        503: {"description": "AI tavsiya sozlanmagan (API kalit yo'q)"},
    },
)
def recommend(payload: RecommendationIn, request: Request):
    """Bazadagi shu turdagi bozor takliflarini Claude'ga berib, raqobatbardosh
    yangi mahsulot g'oyalarini (stavka, muddat, summa va asoslash bilan)
    qaytaradi. Natija saqlanmaydi — frontend uni "Yangi mahsulot" formasiga
    to'ldirib beradi."""
    client_ip = request.client.host if request.client else "unknown"
    if not _recommend_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Juda ko'p so'rov — birozdan so'ng qayta urinib ko'ring",
            headers={"Retry-After": str(_recommend_limiter.retry_after(client_ip))},
        )
    with SessionLocal() as session:
        try:
            return recommend_products(
                payload.product_type,
                session,
                category=payload.category,
                goal=payload.goal,
                count=payload.count,
                lang=payload.lang,
            )
        except RecommendationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.patch(
    "/{product_id}",
    response_model=CustomProductOut,
    summary="Mahsulot g'oyasini tahrirlash (qismiy yangilash)",
    responses={
        400: {"description": "Biznes qoidasi buzildi (masalan min. summa maks. summadan katta)"},
        422: {
            "description": "Sxema talabi buzildi (majburiy maydonni null qilish, bo'sh nom, "
            "diapazondan tashqari qiymat) — FastAPI standart javobi"
        },
        404: {"description": "Mahsulot topilmadi"},
        429: {"description": "Juda ko'p so'rov — bitta IP manzildan soatiga 60 tadan ortiq tahrirlab bo'lmaydi"},
    },
)
def update_product(
    product_id: int,
    payload: CustomProductPatch,
    request: Request,
):
    """Yaratilgan mahsulotning kiritilgan ma'lumotlarini o'zgartiradi.
    Sxemaga keyinchalik qo'siladigan maydonlar `_EDITABLE_FIELDS`ga kiritilmasa,
    jimlik bilan e'tiborsiz qoldiriladi."""
    updates = payload.model_dump(exclude_unset=True)

    if (product_type := updates.get("product_type")) is not None and product_type not in _CUSTOM_PRODUCT_TYPES:
        raise HTTPException(status_code=400, detail="Noto'g'ri mahsulot turi")

    client_ip = request.client.host if request.client else "unknown"
    if not _update_product_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Juda ko'p so'rov — birozdan so'ng qayta urinib ko'ring",
            headers={"Retry-After": str(_update_product_limiter.retry_after(client_ip))},
        )

    with SessionLocal() as session:
        product = _get_or_404(session, product_id)

        # Yakuniy umumiy qiymatlar: so'rovda bo'lmagan yarim (min yoki max)
        # qatordagi eski qiymat bilan to'ldiriladi, ya'ni bu tekshiruv
        # sxemadagidan ko'ra to'liqroq rasmda bajariladi.
        new_min = updates["min_amount"] if "min_amount" in updates else product.min_amount
        new_max = updates["max_amount"] if "max_amount" in updates else product.max_amount
        if new_min is not None and new_max is not None and new_min > new_max:
            raise HTTPException(status_code=400, detail="Min. summa maks. summadan katta bo'lishi mumkin emas")

        for field in _EDITABLE_FIELDS:
            if field in updates:
                setattr(product, field, updates[field])

        session.commit()
        session.refresh(product)
        return product.to_dict()


@router.get(
    "",
    response_model=list[CustomProductOut],
    summary="Mahsulot g'oyalarini ro'yxatlash",
)
def list_products():
    with SessionLocal() as session:
        stmt = select(CustomProduct).order_by(CustomProduct.created_at.desc())
        rows = session.scalars(stmt).all()
        return [p.to_dict() for p in rows]


@router.get(
    "/market-leaders",
    response_model=list[MarketLeaderOut],
    summary="Bozordagi eng maqbul stavkali takliflar (AI'siz)",
)
def market_leaders(product_type: Literal["credit", "deposit", "card", "investment"], limit: int = Query(3, ge=1, le=10)):
    """AI strategi paneli so'rovdan OLDIN ko'rsatadigan yetakchilar: so'mdagi,
    jismoniy shaxslar uchun, har bankdan bittadan eng maqbul stavkali taklif.
    Tashqi API'ga murojaat yo'q — bepul va bir zumda."""
    with SessionLocal() as session:
        return top_market_offers(product_type, session, limit)


@router.get(
    "/{product_id}",
    response_model=ProductWithAnalysisOut,
    summary="Mahsulotni bozor takliflari bilan solishtirib tahlil qilish",
    responses={404: {"description": "Mahsulot topilmadi"}},
)
def get_product(product_id: int, lang: Lang = "uz"):
    """Mahsulot ma'lumotlari + shu turdagi bozor takliflariga solishtirib
    hisoblangan tahlil (statistika, kuchli/zaif tomonlar)."""
    with SessionLocal() as session:
        product = _get_or_404(session, product_id)
        analysis = analyze_product(product.product_type, product.rate, session, category=product.category, lang=lang)
        return {**product.to_dict(), "analysis": analysis}


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Mahsulot g'oyasini o'chirish",
    responses={404: {"description": "Mahsulot topilmadi"}},
)
def delete_product(product_id: int):
    with SessionLocal() as session:
        product = _get_or_404(session, product_id)
        session.delete(product)
        session.commit()
    return Response(status_code=204)
