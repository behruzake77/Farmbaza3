from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.medicine_service import MedicineService
from app.services.category_service import CategoryService
from app.services.gopharm_service import GopharmService
from webapp.dependencies import get_current_admin_optional, get_db

router = APIRouter()
templates = Jinja2Templates(directory="webapp/templates")
templates.env.globals["settings"] = settings

import re as _re
templates.env.filters["regex_search"] = lambda s, pattern: bool(_re.search(pattern, s or ""))


def _gp_to_medicine_ctx(drug, local=None):
    """GopharmDrug ni medicine.html shablon kutayotgan kontekstga o'girish."""
    class _M:
        pass
    m = _M()
    m.id            = drug.id
    m.name          = drug.name
    m.category      = drug.category
    m.manufacturer  = drug.manufacturer
    m.country       = getattr(drug, "country", None)
    m.image_url     = drug.image_url
    m.price         = drug.price
    m.barcode       = drug.barcode
    m.dosage_form   = drug.dosage_form
    m.strength      = getattr(drug, "strength", None)
    m.composition   = drug.composition
    m.description   = drug.description
    m.frequency     = getattr(drug, "frequency", None)
    m.age_group     = getattr(drug, "age_group", None)
    m.prescription  = drug.prescription
    m.source_url    = drug.gopharm_url
    m.t136_filial   = bool(local.t136_filial) if local else False
    m.brand             = getattr(drug, "brand", None)
    m.rating            = getattr(drug, "rating", None)
    m.rating_stars      = getattr(drug, "rating_stars", "")
    m.quantity_per_pack = getattr(drug, "quantity_per_pack", None)
    m.price_range_str   = getattr(drug, "price_range_str", "")
    m.old_price_str     = getattr(drug, "old_price_str", "")
    m.discount          = getattr(drug, "discount", 0)
    m.pharm_group       = getattr(drug, "pharm_group", None)
    return m


def _letter(name: str) -> str:
    return (name or "?").strip()[0].upper()


# ── Bosh sahifa ──────────────────────────────────────────────────────────────

@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    med_service = MedicineService(db)
    gp          = GopharmService()

    categories  = await cat_service.get_all()
    counts      = await cat_service.count_by_category_bulk()   # bitta SQL, N+1 yo'q
    total_local = await med_service.count()

    # Gopharmdan ommabop dorlar (fon rejimida, xato bo'lsa bo'sh)
    popular = await gp.get_popular(limit=8)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "site_name": settings.site_name,
        "categories": categories,
        "counts": counts,
        "total_local": total_local,
        "popular": popular,
    })


# ── Qidiruv API (AJAX autocomplete) ─────────────────────────────────────────

@router.get("/api/qidiruv")
async def api_search(q: str = "", db: AsyncSession = Depends(get_db)):
    """Jonli qidiruv — Gopharm API orqali, mahalliy saqlangan kategoriya bilan."""
    gp = GopharmService()
    med_service = MedicineService(db)
    results = await gp.search(q, limit=12)

    data = []
    for m in results:
        category = m.category
        t136 = False
        age_group = None
        local = await med_service.get_by_source_url(m.gopharm_url)
        if local:
            if local.category:
                category = local.category
            t136 = bool(local.t136_filial)
            age_group = local.age_group
        data.append({
            "id":          m.id,
            "name":        m.name,
            "category":    category,
            "manufacturer": m.manufacturer,
            "image_url":   m.image_url,
            "price":       m.price_str,
            "age_group":   age_group,
            "url":         m.detail_url,
            "placeholder": m.placeholder,
            "t136_filial": t136,
        })
    return JSONResponse({"query": q, "results": data})


# ── Qidiruv sahifasi ─────────────────────────────────────────────────────────

@router.get("/qidiruv")
async def search_page(request: Request, q: str = "",
                       db: AsyncSession = Depends(get_db)):
    gp      = GopharmService()
    results = await gp.search(q, limit=48) if q else []

    med_service = MedicineService(db)
    for d in results:
        local = await med_service.get_by_source_url(d.gopharm_url)
        d.t136_filial = False
        d.age_group = None
        if local:
            if local.category:
                d.category = local.category
            d.t136_filial = bool(local.t136_filial)
            d.age_group = local.age_group

    return templates.TemplateResponse("search.html", {
        "request":   request,
        "site_name": settings.site_name,
        "query":     q,
        "results":   results,
    })


# ── Kategoriya sahifasi ──────────────────────────────────────────────────────

@router.get("/kategoriya/{category_id}")
async def category_page(request: Request, category_id: int,
                         db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    med_service = MedicineService(db)
    category = await cat_service.get_by_id(category_id)
    if not category:
        return templates.TemplateResponse(
            "404.html", {"request": request, "site_name": settings.site_name}, status_code=404
        )
    medicines = await med_service.get_by_category(category.nomi, limit=200)
    return templates.TemplateResponse("category.html", {
        "request":   request,
        "site_name": settings.site_name,
        "category":  category,
        "medicines": medicines,
    })


# ── Mahalliy dori detail ─────────────────────────────────────────────────────

@router.get("/dori/{medicine_id}")
async def medicine_detail(request: Request, medicine_id: int,
                           db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    medicine = await med_service.get_by_id(medicine_id)
    if not medicine:
        return templates.TemplateResponse(
            "404.html", {"request": request, "site_name": settings.site_name}, status_code=404
        )

    analogues = await med_service.get_analogues(medicine, limit=8)

    return templates.TemplateResponse("medicine.html", {
        "request":          request,
        "site_name":        settings.site_name,
        "medicine":         medicine,
        "placeholder":      _letter(medicine.name),
        "analogues":        analogues,
        "analogue_prefix":  "/dori/",
    })


# ── Gopharm dori detail ──────────────────────────────────────────────────────

@router.get("/gp/{drug_id}")
async def gopharm_medicine_detail(request: Request, drug_id: int,
                                   db: AsyncSession = Depends(get_db)):
    gp   = GopharmService()
    drug = await gp.get_by_id(drug_id)
    if not drug:
        return templates.TemplateResponse(
            "404.html", {"request": request, "site_name": settings.site_name}, status_code=404
        )

    # Avval mahalliy bazada saqlangan kategoriya bo'lsa — o'shani ko'rsatamiz
    med_service = MedicineService(db)
    local = await med_service.get_or_create_by_source_url(drug.gopharm_url, {
        "name":         drug.name,
        "category":     drug.category,
        "manufacturer": drug.manufacturer,
        "dosage_form":  drug.dosage_form,
        "composition":  drug.composition,
        "description":  drug.description,
        "image_url":    drug.image_url,
        "barcode":      drug.barcode,
        "price":        drug.price,
    })
    if local.category:
        drug.category = local.category

    drug.age_group = local.age_group
    drug.age_ai_generated = False
    if local.description:
        drug.description = local.description
    if local.composition:
        drug.composition = local.composition

    # Kategoriya ma'lumotini mahalliy bazadan ham olish (faqat admin uchun)
    is_admin = bool(get_current_admin_optional(request))
    categories = None
    if is_admin:
        cat_service = CategoryService(db)
        categories  = await cat_service.get_all()
        if local.category:
            for c in categories:
                if c.nomi == local.category:
                    saved_category_id = c.id
                    break
            else:
                saved_category_id = None
        else:
            saved_category_id = None

    # drug.analogs GoPharm detail API'dan avtomatik keladi — alohida so'rov kerak emas
    return templates.TemplateResponse("medicine.html", {
        "request":           request,
        "site_name":         settings.site_name,
        "medicine":          _gp_to_medicine_ctx(drug, local),
        "placeholder":       (drug.name or "?")[0].upper(),
        "categories":        categories,
        "saved_category_id": saved_category_id if is_admin else None,
        "is_t136":           bool(local.t136_filial),
        "analogues":         drug.analogs,
        "analogue_prefix":   "/gp/",
    })


# ── T136 filiali menyusi ─────────────────────────────────────────────────────

@router.get("/t136")
async def t136_menu(request: Request, db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    medicines = await med_service.get_t136_medicines(limit=500)
    return templates.TemplateResponse("t136.html", {
        "request":   request,
        "site_name": settings.site_name,
        "medicines": medicines,
    })
