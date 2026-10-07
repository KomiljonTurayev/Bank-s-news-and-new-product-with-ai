"""FastAPI ilovasining tarkib topish nuqtasi (composition root): `app`ni
yaratadi, CORS'ni sozlaydi va har bir domen uchun alohida routerni ulaydi
(`app/routers/*.py`). Marshrutlarning o'zi shu yerda emas — bu fayl faqat
ularni yig'ib qo'yadi."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_ORIGINS
from app.routers import meta, products, rates

_OPENAPI_TAGS = [
    {"name": "meta", "description": "Statik ma'lumotnomalar — banklar, mahsulot turlari, segmentlar ro'yxati."},
    {
        "name": "rates",
        "description": "Banklardan yig'ilgan foiz stavkalari/tariflar va cbu.uz rasmiy valyuta kursi dinamikasi.",
    },
    {
        "name": "products",
        "description": (
            "Foydalanuvchi kiritgan mahsulot g'oyalarini boshqarish va ularni bozordagi "
            "haqiqiy takliflar bilan solishtirib tahlil qilish."
        ),
    },
]

app = FastAPI(
    title="Bank's News API",
    description=(
        "O'zbekiston banklarining omonat/kredit/karta/valyuta takliflarini bir joyga yig'adigan "
        "va ularga solishtirib tahlil beradigan API. Ushbu Swagger hujjati tashqi tizimlar "
        "(masalan AI xizmatlari) API'ga ulanib bank ma'lumotlaridan foydalanishi uchun mo'ljallangan."
    ),
    version="1.0.0",
    openapi_tags=_OPENAPI_TAGS,
)
# Frontend endi alohida repo/origin'dan xizmat qiladi (masalan
# http://localhost:5500), shuning uchun brauzer buni cross-origin so'rov deb
# hisoblaydi va CORS ruxsati kerak. Wildcard ("*") ATAYLAB ishlatilmaydi —
# autentifikatsiya yo'qligi tufayli istalgan saytning JS kodi tashrif
# buyuruvchining brauzeri orqali POST/DELETE /api/products so'rovlarini
# yuborib, boshqa foydalanuvchilarning mahsulotlarini o'chira olardi yoki
# bazani spam yozuvlar bilan to'ldira olardi. Ruxsat FRONTEND_ORIGINS orqali
# aniq ro'yxatlangan origin'lar bilan cheklangan (app/config.py).
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    # PATCH ham ro'yxatda bo'lishi shart: mahsulotni tahrirlash shu metod bilan
    # boradi. Ro'yxatda bo'lmagan metod brauzer preflight'ida rad etiladi
    # (TestClient CORS tekshirmagani uchun testlar buni ushlamaydi).
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(meta.router)
app.include_router(rates.router)
app.include_router(products.router)
