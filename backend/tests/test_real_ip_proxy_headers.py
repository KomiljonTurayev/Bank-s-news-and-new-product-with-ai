"""Proksi ortidagi haqiqiy mijoz IP'si — login/yozuv limiterlarining kaliti.

main.py uvicorn'ni `proxy_headers=True, forwarded_allow_ips=FORWARDED_ALLOW_IPS`
bilan yoqadi; shu test lar aynan shu zanjirning xatti-harakatini bog'lab
qo'yadi (soxta XFF bilan limiterdan qochib bo'lmasligi — xavfsizlik
chizig'i shu yerda)."""

import asyncio

import httpx
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import FORWARDED_ALLOW_IPS


async def _resolved_client(peer: tuple[str, int], forwarded_for: str | None) -> tuple:
    """`peer`dan kelgan so'rov `forwarded_for` sarlavhasi bilan uvicorn
    proksi-midjeydan o'tkazilganda `scope["client"]`ga nima yozilishini
    qaytaradi (echo-app orqali)."""

    seen: dict = {}

    async def echo(scope, receive, send):
        seen["client"] = scope["client"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    app = ProxyHeadersMiddleware(echo, trusted_hosts=FORWARDED_ALLOW_IPS)
    headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
    transport = httpx.ASGITransport(app=app, client=peer)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/api/auth/oneid", headers=headers)
    return seen["client"]


def test_haqiqiy_mijoz_ongdan_birinchi_ishonchsiz_manzil():
    # nginx (10.42.0.5) o'z oldidagi haqiqiy mijozni XFF oxiriga qo'shadi;
    # mijoz chapga soxta yozma qo'shib yuborgan bo'lsa ham o'sha emas,
    # nginx qo'shgan manzil tanlanadi.
    client = asyncio.run(
        _resolved_client(("10.42.0.5", 43210), "198.51.100.1, 203.0.113.7")
    )
    assert client[0] == "203.0.113.7"


def test_ishonchsiz_proksidan_kelgan_xff_butunlay_e_tiborsiz():
    # Backend'dan bevosita so'rov (proksi ishtirokisiz): header'dagi manzil
    # qanchalik ishonchli ko'rinsa ham e'tiborsiz — limiter haqiqiy TCP
    # mijozni hisoblaydi, soxta header bilan hisobni chalg'itib bo'lmaydi.
    client = asyncio.run(_resolved_client(("203.0.113.9", 40000), "1.2.3.4"))
    assert client[0] == "203.0.113.9"


def test_xff_bo_lmasa_proksi_manzili_shunday_qoladi():
    # Lokal dev (vite/ nginx XFFsiz): hech narsa buzilmaydi.
    peer = ("127.0.0.1", 54321)
    assert asyncio.run(_resolved_client(peer, None))[0] == "127.0.0.1"
