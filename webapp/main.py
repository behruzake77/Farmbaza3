from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from loguru import logger
import time
from collections import defaultdict

from app.config import settings
from app.database import init_db
from webapp.routers import admin, public

app = FastAPI(title=settings.site_name)

app.add_middleware(SessionMiddleware, secret_key=settings.site_secret_key)

app.mount("/static", StaticFiles(directory="webapp/static"), name="static")

app.include_router(public.router)
app.include_router(admin.router)


# ── Rate limiting (xotiraga asoslangan, oddiy) ───────────────────────────────
# /admin yo'llariga rate limit qo'llanilmaydi — faqat ommaviy API uchun

_rate_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Admin yo'llari va statik fayllarni o'tkazib yuborish
    path = request.url.path
    if path.startswith("/admin") or path.startswith("/static"):
        return await call_next(request)

    ip = request.client.host or "unknown"
    now = time.time()
    window = settings.rate_limit_minutes * 60

    # Eski yozuvlarni tozalash
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window]

    if len(_rate_store[ip]) >= settings.rate_limit_requests:
        return JSONResponse(
            {"detail": "So'rovlar chegarasiga yetdingiz. Biroz kuting."},
            status_code=429,
            headers={"Retry-After": str(int(window))},
        )

    _rate_store[ip].append(now)
    return await call_next(request)


@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info(f"✅ {settings.site_name} sayti ishga tushdi")
    logger.info(
        f"⚡ Rate limit: {settings.rate_limit_requests} so'rov / "
        f"{settings.rate_limit_minutes} daqiqa"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp.main:app", host="0.0.0.0", port=8000, reload=True)
