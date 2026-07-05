from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.medicine import Medicine
from app.models.history import SearchHistory, Favorite
from loguru import logger
from rapidfuzz import fuzz
from typing import Optional


class MedicineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, medicine_id: int) -> Optional[Medicine]:
        result = await self.session.execute(
            select(Medicine).where(Medicine.id == medicine_id, Medicine.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_name_exact(self, name: str) -> Optional[Medicine]:
        result = await self.session.execute(
            select(Medicine).where(
                Medicine.name == name,
                Medicine.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def get_by_source_url(self, source_url: str) -> Optional[Medicine]:
        """GoPharm manba havolasi bo'yicha mahalliy bazadagi yozuvni topadi."""
        if not source_url:
            return None
        result = await self.session.execute(
            select(Medicine).where(
                Medicine.source_url == source_url,
                Medicine.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def get_category_by_name(self, name: str) -> Optional[str]:
        """Dori nomi bo'yicha saqlangan kategoriyani qaytaradi."""
        result = await self.session.execute(
            select(Medicine.category).where(
                Medicine.name == name,
                Medicine.is_active == True,
                Medicine.category.isnot(None)
            )
        )
        return result.scalar_one_or_none()

    async def set_category_by_name(self, name: str, category: Optional[str],
                                    image_url: str = None, source_url: str = None) -> Medicine:
        """Dori nomiga kategoriya biriktiradi. Yo'q bo'lsa yaratadi."""
        med = await self.get_by_name_exact(name)
        if med:
            med.category = category
            if image_url and not med.image_url:
                med.image_url = image_url
            if source_url and not med.source_url:
                med.source_url = source_url
            await self.session.flush()
            return med
        else:
            return await self.create({
                "name": name,
                "category": category,
                "image_url": image_url,
                "source_url": source_url,
            })

    async def get_all(self, limit: int = 50, offset: int = 0) -> list[Medicine]:
        result = await self.session.execute(
            select(Medicine).where(Medicine.is_active == True)
            .order_by(Medicine.name)
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count(Medicine.id)).where(Medicine.is_active == True)
        )
        return result.scalar_one()

    async def create(self, data: dict) -> Medicine:
        medicine = Medicine(**data)
        self.session.add(medicine)
        await self.session.flush()
        await self.session.refresh(medicine)
        return medicine

    async def update(self, medicine_id: int, data: dict) -> Optional[Medicine]:
        medicine = await self.get_by_id(medicine_id)
        if not medicine:
            return None
        for key, value in data.items():
            setattr(medicine, key, value)
        await self.session.flush()
        return medicine

    async def get_or_create_by_source_url(self, source_url: str, defaults: dict) -> Medicine:
        """Manba havolasi bo'yicha mahalliy yozuvni topadi, bo'lmasa yaratadi."""
        medicine = await self.get_by_source_url(source_url)
        if medicine:
            return medicine
        data = dict(defaults)
        data["source_url"] = source_url
        return await self.create(data)

    async def delete(self, medicine_id: int) -> bool:
        medicine = await self.get_by_id(medicine_id)
        if not medicine:
            return False
        medicine.is_active = False
        await self.session.flush()
        return True

    async def search(self, query: str, user_id: int = None, limit: int = 10) -> list[Medicine]:
        """
        Kuchli qidiruv:
        1. Barcode — aniq moslik
        2. SQL ILIKE — tez va aniq
        3. score_match — fuzzy + translit + sinonimlar
        """
        from app.utils.search_engine import normalize, score_match

        q = (query or "").strip()
        if not q:
            return []

        # 1. Barcode
        if re.match(r"^\d{8,14}$", q):
            bc_res = await self.session.execute(
                select(Medicine).where(Medicine.is_active == True, Medicine.barcode == q).limit(5)
            )
            bc_meds = list(bc_res.scalars().all())
            if bc_meds:
                await self._save_history(user_id, q, len(bc_meds))
                return bc_meds

        q_norm = normalize(q)
        q_orig = q.lower()

        # 2. SQL ILIKE — so'z boshidan va ichidan
        sql_res = await self.session.execute(
            select(Medicine).where(
                Medicine.is_active == True,
                or_(
                    Medicine.name.ilike(f"{q_orig}%"),
                    Medicine.name.ilike(f"%{q_orig}%"),
                    Medicine.name.ilike(f"{q_norm}%"),
                    Medicine.name.ilike(f"%{q_norm}%"),
                    Medicine.composition.ilike(f"%{q_orig}%"),
                )
            ).order_by(Medicine.name).limit(limit * 2)
        )
        sql_meds = list(sql_res.scalars().all())

        # 3. score_match bilan tartiblash va fuzzy qo'shish
        all_res = await self.session.execute(
            select(Medicine).where(Medicine.is_active == True).limit(1000)
        )
        all_meds = list(all_res.scalars().all())

        scored = []
        seen = {m.id for m in sql_meds}
        for med in sql_meds:
            s = score_match(q, med.name or "", med.name_ru or "", med.composition or "")
            scored.append((med, max(s, 75.0)))  # SQL topganlar kamida 75

        for med in all_meds:
            if med.id in seen:
                continue
            s = score_match(q, med.name or "", med.name_ru or "", med.composition or "")
            if s >= 62:
                scored.append((med, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [m for m, _ in scored[:limit]]
        await self._save_history(user_id, q, len(results))
        return results

    async def _save_history(self, user_id: Optional[int], query: str, count: int):
        if not user_id:
            return
        try:
            self.session.add(SearchHistory(
                user_telegram_id=user_id,
                query=query,
                result_count=count,
            ))
            await self.session.flush()
        except Exception as e:
            logger.warning(f"Tarix saqlashda xato: {e}")

    async def autocomplete(self, query: str, limit: int = 12) -> list[Medicine]:
        """Veb-sayt uchun tezkor qidiruv (2-3 harfdan boshlab).

        SQL ILIKE orqali ishlaydi — barcha yozuvlarni xotiraga yuklamaydi.
        Natija yo'q bo'lsagina rapidfuzz fallback (faqat 500 ta).
        """
        from app.utils.search_engine import normalize_query

        query_clean = normalize_query(query)
        if len(query_clean) < 2:
            return []

        q_orig = query.strip().lower()
        pat = f"%{query_clean}%"
        pat_orig = f"%{q_orig}%"

        # 1) So'z boshidan mos keladiganlar
        starts_res = await self.session.execute(
            select(Medicine).where(
                Medicine.is_active == True,
                or_(
                    Medicine.name.ilike(f"{query_clean}%"),
                    Medicine.name.ilike(f"{q_orig}%"),
                    Medicine.name_uz.ilike(f"{query_clean}%"),
                    Medicine.name_ru.ilike(f"{q_orig}%"),
                )
            ).order_by(Medicine.name).limit(limit)
        )
        starts = list(starts_res.scalars().all())

        if len(starts) >= limit:
            return starts

        # 2) Ichida uchraydiganlar
        already_ids = {m.id for m in starts}
        contains_filter = (~Medicine.id.in_(already_ids),) if already_ids else ()
        contains_res = await self.session.execute(
            select(Medicine).where(
                Medicine.is_active == True,
                *contains_filter,
                or_(
                    Medicine.name.ilike(pat),
                    Medicine.name.ilike(pat_orig),
                    Medicine.name_uz.ilike(pat),
                    Medicine.name_ru.ilike(pat_orig),
                )
            ).order_by(Medicine.name).limit(limit - len(starts))
        )
        results = starts + list(contains_res.scalars().all())

        # 3) Hech narsa topilmasa — rapidfuzz fallback (faqat 500 ta)
        if not results:
            fallback_res = await self.session.execute(
                select(Medicine).where(Medicine.is_active == True).limit(500)
            )
            all_meds = list(fallback_res.scalars().all())
            scored = [
                (med, fuzz.WRatio(query_clean, (med.name or "").lower()))
                for med in all_meds
            ]
            scored = [(m, s) for m, s in scored if s >= 70]
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [m for m, _ in scored[:limit]]

        return results

    async def get_categories(self) -> list[str]:
        result = await self.session.execute(
            select(Medicine.category).where(
                Medicine.is_active == True,
                Medicine.category.isnot(None)
            ).distinct()
        )
        return [r for r in result.scalars().all() if r]

    async def get_favorites(self, user_id: int) -> list[Medicine]:
        result = await self.session.execute(
            select(Medicine).join(
                Favorite, Medicine.id == Favorite.medicine_id
            ).where(Favorite.user_telegram_id == user_id, Medicine.is_active == True)
        )
        return list(result.scalars().all())

    async def add_favorite(self, user_id: int, medicine_id: int) -> bool:
        existing = await self.session.execute(
            select(Favorite).where(
                Favorite.user_telegram_id == user_id,
                Favorite.medicine_id == medicine_id
            )
        )
        if existing.scalar_one_or_none():
            return False
        self.session.add(Favorite(user_telegram_id=user_id, medicine_id=medicine_id))
        await self.session.flush()
        return True

    async def remove_favorite(self, user_id: int, medicine_id: int) -> bool:
        result = await self.session.execute(
            select(Favorite).where(
                Favorite.user_telegram_id == user_id,
                Favorite.medicine_id == medicine_id
            )
        )
        fav = result.scalar_one_or_none()
        if not fav:
            return False
        await self.session.delete(fav)
        await self.session.flush()
        return True

    async def is_favorite(self, user_id: int, medicine_id: int) -> bool:
        result = await self.session.execute(
            select(Favorite).where(
                Favorite.user_telegram_id == user_id,
                Favorite.medicine_id == medicine_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_analogues(self, medicine: Medicine, limit: int = 8) -> list[Medicine]:
        """Xuddi shu kategoriya bo'yicha analoglarni qaytaradi (o'zini chiqarib tashlaydi)."""
        if not medicine.category:
            return []
        result = await self.session.execute(
            select(Medicine).where(
                Medicine.is_active == True,
                Medicine.category == medicine.category,
                Medicine.id != medicine.id,
            ).order_by(Medicine.name).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_category(self, category: str, limit: int = 20) -> list[Medicine]:
        result = await self.session.execute(
            select(Medicine).where(
                Medicine.is_active == True,
                Medicine.category == category
            ).order_by(Medicine.name).limit(limit)
        )
        return list(result.scalars().all())

    async def get_t136_medicines(self, limit: int = 500) -> list[Medicine]:
        """T136 filialida mavjud deb belgilangan dorilar."""
        result = await self.session.execute(
            select(Medicine).where(
                Medicine.is_active == True,
                Medicine.t136_filial == True
            ).order_by(Medicine.name).limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_category(self, category: str) -> int:
        result = await self.session.execute(
            select(func.count(Medicine.id)).where(
                Medicine.is_active == True,
                Medicine.category == category
            )
        )
        return result.scalar_one()

    async def get_search_history(self, user_id: int, limit: int = 10) -> list[SearchHistory]:
        result = await self.session.execute(
            select(SearchHistory).where(
                SearchHistory.user_telegram_id == user_id
            ).order_by(SearchHistory.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
