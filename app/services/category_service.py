from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.category import Category
from typing import Optional


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[Category]:
        result = await self.session.execute(
            select(Category).order_by(Category.nomi)
        )
        return list(result.scalars().all())

    async def get_names(self) -> list[str]:
        result = await self.session.execute(
            select(Category.nomi).order_by(Category.nomi)
        )
        return list(result.scalars().all())

    async def get_by_id(self, cat_id: int) -> Optional[Category]:
        result = await self.session.execute(
            select(Category).where(Category.id == cat_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, nomi: str) -> Optional[Category]:
        result = await self.session.execute(
            select(Category).where(Category.nomi == nomi.strip())
        )
        return result.scalar_one_or_none()

    async def create(self, nomi: str, gopharm_slug: Optional[str] = None) -> Optional[Category]:
        existing = await self.get_by_name(nomi)
        if existing:
            return None
        cat = Category(nomi=nomi.strip(), gopharm_slug=gopharm_slug)
        self.session.add(cat)
        await self.session.flush()
        await self.session.refresh(cat)
        return cat

    async def update(self, cat_id: int, nomi: str,
                     gopharm_slug: Optional[str] = None) -> Optional[Category]:
        cat = await self.get_by_id(cat_id)
        if not cat:
            return None
        cat.nomi = nomi.strip()
        cat.gopharm_slug = gopharm_slug
        await self.session.flush()
        return cat

    async def delete(self, cat_id: int) -> bool:
        cat = await self.get_by_id(cat_id)
        if not cat:
            return False
        await self.session.delete(cat)
        await self.session.flush()
        return True

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(Category.id)))
        return result.scalar_one()

    async def count_by_category_bulk(self) -> dict[str, int]:
        """Barcha kategoriyalar uchun bitta SQL so'rovda dori sonini qaytaradi.
        N+1 muammosini hal qiladi (12 kategoriya = 1 so'rov, 13 emas)."""
        from app.models.medicine import Medicine
        result = await self.session.execute(
            select(Medicine.category, func.count(Medicine.id))
            .where(Medicine.is_active == True, Medicine.category.isnot(None))
            .group_by(Medicine.category)
        )
        return {row[0]: row[1] for row in result.all()}
