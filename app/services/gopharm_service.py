"""
GoPharm.uz API mijozi — real-time dori ma'lumotlari
"""
import asyncio
import json
import re
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional

API_BASE  = "https://api2.gopharm.uz/api/"
GP_SITE   = "https://gopharm.uz/uz/product/"
LANG      = "uz"
TIMEOUT   = 12


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
    def handle_data(self, data: str):
        self._parts.append(data)
    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def _strip_html(html: str) -> str:
    if not html:
        return ""
    s = _HTMLStripper()
    s.feed(html)
    return re.sub(r"\s+", " ", s.get_text()).strip()


try:
    from loguru import logger as _log
except ImportError:
    import logging as _log  # type: ignore


def _fetch(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


@dataclass
class GopharmDrug:
    id: int
    name: str
    slug: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    country: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    barcode: Optional[str] = None
    dosage_form: Optional[str] = None
    composition: Optional[str] = None
    description: Optional[str] = None
    prescription: bool = False
    analogs: list = field(default_factory=list)  # GoPharm detail API'dan keladi

    @property
    def detail_url(self) -> str:
        return f"/gp/{self.id}"

    @property
    def gopharm_url(self) -> str:
        return f"{GP_SITE}{self.slug}"

    @property
    def price_str(self) -> str:
        if not self.price:
            return ""
        return f"{self.price:,.0f} so'm".replace(",", " ")

    @property
    def placeholder(self) -> str:
        return (self.name or "?")[0].upper()


def _from_list(d: dict) -> GopharmDrug:
    cat  = d.get("category") or {}
    mfr  = d.get("manufacturer") or {}
    cntry = d.get("country") or {}
    price = d.get("price")
    return GopharmDrug(
        id          = d["id"],
        name        = d.get("name") or "",
        slug        = d.get("slug") or "",
        category    = d.get("item_category2") or cat.get("name") or d.get("item_category"),
        manufacturer= mfr.get("name"),
        country     = cntry.get("name"),
        image_url   = d.get("image_thumbnail"),
        price       = float(price) if price else None,
        barcode     = d.get("barcode"),
        dosage_form = (d.get("unit_uz") or d.get("unit") or "").strip("-") or None,
        composition = d.get("international_name_uz") or d.get("international_name"),
        prescription= bool(d.get("is_recept")),
    )


def _from_detail(d: dict) -> GopharmDrug:
    drug = _from_list(d)
    drug.name        = d.get("name_uz") or d.get("name") or drug.name
    drug.description = _strip_html(d.get("description") or "")
    # GoPharm detail API o'zida analoglarni qaytaradi — alohida so'rov kerak emas
    drug.analogs     = [_from_list(a) for a in (d.get("analog") or []) if a.get("id")]
    return drug


class GopharmService:
    """Gopharm.uz API bilan ishlash uchun async mijoz."""

    # ── Search ──────────────────────────────────────────────────────────────────

    async def search(self, q: str, limit: int = 24) -> list[GopharmDrug]:
        """Gopharm API orqali dori qidirish."""
        q = (q or "").strip()
        if len(q) < 2:
            return []
        url = (
            f"{API_BASE}v1/drugs"
            f"?lan={LANG}&search={urllib.parse.quote(q)}&limit={limit}"
        )
        try:
            data = await asyncio.to_thread(_fetch, url)
            return [_from_list(d) for d in data.get("results", [])]
        except Exception as exc:
            _log.warning(f"GopharmService.search({q!r}) failed: {exc}")
            return []

    # ── Detail ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, drug_id: int) -> Optional[GopharmDrug]:
        """ID bo'yicha to'liq ma'lumot olish."""
        url = f"{API_BASE}v1/drugs/{drug_id}?lan={LANG}"
        try:
            data = await asyncio.to_thread(_fetch, url)
            if not data.get("id"):
                return None
            return _from_detail(data)
        except Exception as exc:
            _log.warning(f"GopharmService.get_by_id({drug_id}) failed: {exc}")
            return None

    # ── Analogues ───────────────────────────────────────────────────────────────

    async def get_analogues(self, drug: "GopharmDrug", limit: int = 8) -> list["GopharmDrug"]:
        """Xuddi shu tarkib (composition) bo'yicha analoglarni qidirish."""
        query = (drug.composition or "").strip()
        if not query or len(query) < 3:
            # Fallback: kategoriya bo'yicha qidirish
            query = (drug.category or "").strip()
        if not query or len(query) < 3:
            return []
        url = (
            f"{API_BASE}v1/drugs"
            f"?lan={LANG}&search={urllib.parse.quote(query)}&limit={limit + 2}"
        )
        try:
            data = await asyncio.to_thread(_fetch, url)
            results = [_from_list(d) for d in data.get("results", [])]
            # Joriy dorini chiqarib tashlash
            return [r for r in results if r.id != drug.id][:limit]
        except Exception as exc:
            _log.warning(f"GopharmService.get_analogues({query!r}) failed: {exc}")
            return []

    # ── Popular ─────────────────────────────────────────────────────────────────

    async def get_popular(self, limit: int = 8) -> list[GopharmDrug]:
        """Birinchi sahifadan ommabop dorilar."""
        url = f"{API_BASE}v1/drugs?lan={LANG}&limit={limit}&page=1"
        try:
            data = await asyncio.to_thread(_fetch, url)
            return [_from_list(d) for d in data.get("results", [])]
        except Exception as exc:
            _log.warning(f"GopharmService.get_popular() failed: {exc}")
            return []
