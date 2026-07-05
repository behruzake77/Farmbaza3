from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import AsyncSessionLocal
from app.config import settings
from app.utils.security import verify_password


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Har bir so'rov uchun DB sessiya beradi va oxirida commit/rollback qiladi."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def check_admin_credentials(username: str, password: str) -> bool:
    """Admin login ma'lumotlarini tekshiradi.

    Agar .env faylda ADMIN_PASSWORD_HASH berilgan bo'lsa — bcrypt bilan
    tekshiradi (tavsiya etiladi). Aks holda ADMIN_PASSWORD bilan oddiy
    solishtiradi (faqat rivojlantirish uchun, productionda hash ishlating).
    """
    if username != settings.admin_username:
        return False
    if settings.admin_password_hash:
        return verify_password(password, settings.admin_password_hash)
    return password == settings.admin_password


def get_current_admin(request: Request) -> str:
    """Sessiyada admin login borligini tekshiradi, aks holda 401 qaytaradi."""
    admin = request.session.get("admin_username")
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return admin


def get_current_admin_optional(request: Request) -> Optional[str]:
    return request.session.get("admin_username")
