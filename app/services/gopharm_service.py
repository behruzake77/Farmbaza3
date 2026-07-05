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


_ALLOWED_TAGS = {"h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "b", "em", "i", "br"}


class _HTMLSanitizer(HTMLParser):
    """GoPharm tavsifidagi HTML tuzilishini (sarlavhalar, ro'yxatlar) saqlab,
    faqat xavfsiz teglarni qoldiradi — matn "tekis" bo'lib qolmasligi uchun."""

    def __init__(self):
        super().__init__()
        self._out: list[str] = []
        self._skip_stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _ALLOWED_TAGS:
            self._out.append(f"<{tag}>")
        elif tag not in ("html", "body", "div", "span", "table", "tr", "td", "th", "tbody", "thead"):
            self._skip_stack.append(tag)

    def handle_endtag(self, tag):
        if tag in _ALLOWED_TAGS:
            self._out.append(f"</{tag}>")

    def handle_data(self, data):
        self._out.append(data.replace("&nbsp;", " "))

    def get_html(self) -> str:
        html = "".join(self._out)
        html = re.sub(r"[ \t]+", " ", html)
        html = re.sub(r"\n\s*\n+", "\n", html)
        html = re.sub(r"(<p>\s*</p>)+", "", html)
        html = re.sub(r"(<br>\s*){2,}", "<br>", html)
        return html.strip()


def _rich_html(html: str) -> str:
    """Tavsifni tuzilishini saqlagan holda tozalaydi (sarlavha/ro'yxat qoladi)."""
    if not html:
        return ""
    s = _HTMLSanitizer()
    s.feed(html)
    result = s.get_html()
    return result if result else _strip_html(html)


_SECTION_HEAD_RE = re.compile(r"<h[234]>(.*?)</h[234]>", re.IGNORECASE | re.DOTALL)


def split_description_sections(html: str) -> list[dict]:
    """Tozalangan tavsif HTML'ini <h2>/<h3>/<h4> sarlavhalari bo'yicha bo'laklarga ajratadi.

    Har bir bo'lak {"id": slug, "title": matn, "html": kontent} shaklida qaytadi.
    Sarlavhasiz boshlang'ich matn bo'lsa, u "Umumiy ma'lumot" nomi bilan alohida bo'lak bo'ladi.
    """
    if not html:
        return []

    matches = list(_SECTION_HEAD_RE.finditer(html))
    if not matches:
        return [{"id": "umumiy", "title": "Umumiy ma'lumot", "html": html}]

    sections: list[dict] = []
    used_ids: set = set()

    def _slug(text: str, idx: int) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", _strip_html(text).lower()).strip("-") or f"bolim-{idx}"
        base = base[:40]
        candidate = base
        n = 2
        while candidate in used_ids:
            candidate = f"{base}-{n}"
            n += 1
        used_ids.add(candidate)
        return candidate

    lead = html[: matches[0].start()].strip()
    if lead and _strip_html(lead):
        sections.append({"id": _slug("Umumiy ma'lumot", 0), "title": "Umumiy ma'lumot", "html": lead})

    for i, m in enumerate(matches):
        title = _strip_html(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        body = html[start:end].strip()
        if not title:
            continue
        sections.append({"id": _slug(title, i + 1), "title": title, "html": body})

    return sections


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

    brand: Optional[str] = None
    rating: Optional[float] = None
    quantity_per_pack: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    discount: int = 0
    discount_label: Optional[str] = None
    pharm_group: Optional[str] = None

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
    def old_price_str(self) -> str:
        """Chegirmagacha bo'lgan narx (agar discount bo'lsa)."""
        if not self.discount or not self.price:
            return ""
        old = self.price / (1 - self.discount / 100)
        return f"{old:,.0f} so'm".replace(",", " ")

    @property
    def price_range_str(self) -> str:
        """Turli dorixonalardagi narx oralig'i (min-max farqli bo'lsa)."""
        if not self.price_min or not self.price_max or self.price_min == self.price_max:
            return ""
        return (
            f"{self.price_min:,.0f} — {self.price_max:,.0f} so'm"
        ).replace(",", " ")

    @property
    def rating_stars(self) -> str:
        if not self.rating:
            return ""
        full = int(round(self.rating))
        return "★" * full + "☆" * (5 - full)

    @property
    def placeholder(self) -> str:
        return (self.name or "?")[0].upper()


def _from_list(d: dict) -> GopharmDrug:
    cat  = d.get("category") or {}
    mfr  = d.get("manufacturer") or {}
    cntry = d.get("country") or {}
    brand = d.get("brand_uz") or d.get("brand") or {}
    price = d.get("price")
    price_min = d.get("price_min")
    price_max = d.get("price_max")
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
        brand              = brand.get("name") if isinstance(brand, dict) else None,
        rating             = d.get("rating"),
        quantity_per_pack  = d.get("quantity_per_pack") or None,
        price_min          = float(price_min) if price_min else None,
        price_max          = float(price_max) if price_max else None,
        discount           = int(d.get("discount") or 0),
        discount_label     = d.get("discount_label"),
        pharm_group        = d.get("pharm_group"),
    )


def _from_detail(d: dict) -> GopharmDrug:
    drug = _from_list(d)
    drug.name        = d.get("name_uz") or d.get("name") or drug.name
    drug.description = _rich_html(d.get("description") or "")
    drug.rating      = d.get("rating") or drug.rating
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
