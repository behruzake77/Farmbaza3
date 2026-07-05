from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models.user import User
from app.config import settings
from loguru import logger
from typing import Optional


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, telegram_id: int, username: str = None,
                             first_name: str = None, last_name: str = None) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            is_admin = telegram_id in settings.admin_id_list
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=is_admin,
            )
            self.session.add(user)
            await self.session.flush()
            logger.info(f"Yangi foydalanuvchi: {telegram_id} (@{username})")
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            await self.session.flush()

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def increment_search_count(self, telegram_id: int):
        await self.session.execute(
            update(User).where(User.telegram_id == telegram_id)
            .values(search_count=User.search_count + 1)
        )

    async def get_all(self, limit: int = 50) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
