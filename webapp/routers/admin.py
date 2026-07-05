import os
import uuid

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.medicine import Medicine
from app.services.category_service import CategoryService
from app.services.medicine_service import MedicineService
from app.services.gopharm_service import GopharmService
from app.utils.env_writer import update_env_values
from app.utils.security import hash_password
from webapp.dependencies import check_admin_credentials, get_current_admin, get_db

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="webapp/templates")
templates.env.globals["settings"] = settings

UPLOAD_DIR = "webapp/static/uploads/dorilar"
BG_UPLOAD_DIR = "webapp/static/uploads/fon"
ANIM_UPLOAD_DIR = "webapp/static/uploads/animatsiya"
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


async def _save_uploaded_bg(file: UploadFile) -> str | None:
    """Yuklangan fon rasmini saqlaydi va static URL manzilini qaytaradi."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return None
    os.makedirs(BG_UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(BG_UPLOAD_DIR, filename)
    content = await file.read()
    if not content:
        return None
    with open(filepath, "wb") as f:
        f.write(content)
    return f"/static/uploads/fon/{filename}"


async def _save_uploaded_anim(file: UploadFile) -> str | None:
    """Yuklangan 3D animatsiya rasmini saqlaydi va static URL manzilini qaytaradi."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return None
    os.makedirs(ANIM_UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(ANIM_UPLOAD_DIR, filename)
    content = await file.read()
    if not content:
        return None
    with open(filepath, "wb") as f:
        f.write(content)
    return f"/static/uploads/animatsiya/{filename}"


async def _save_uploaded_image(file: UploadFile) -> str | None:
    """Yuklangan rasm faylini saqlaydi va static URL manzilini qaytaradi."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    if not content:
        return None
    with open(filepath, "wb") as f:
        f.write(content)
    return f"/static/uploads/dorilar/{filename}"


# ── Kirish / chiqish ──────────────────────────────────────────────────────────

@router.get("/login")
async def login_page(request: Request):
    if request.session.get("admin_username"):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "site_name": settings.site_name, "error": None}
    )


@router.post("/login")
async def login_submit(request: Request,
                        username: str = Form(...), password: str = Form(...)):
    if check_admin_credentials(username, password):
        request.session["admin_username"] = username
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "site_name": settings.site_name,
         "error": "Login yoki parol noto'g'ri"},
        status_code=400,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


# ── Boshqaruv paneli ───────────────────────────────────────────────────────────

@router.get("")
async def dashboard(request: Request,
                     admin: str = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    cat_service = CategoryService(db)
    total_medicines  = await med_service.count()
    total_categories = await cat_service.count()
    uncategorized_result = await db.execute(
        select(func.count(Medicine.id)).where(
            Medicine.is_active == True,
            Medicine.category.is_(None),
        )
    )
    uncategorized = uncategorized_result.scalar_one()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "site_name": settings.site_name,
        "admin": admin,
        "total_medicines":  total_medicines,
        "total_categories": total_categories,
        "uncategorized":    uncategorized,
    })


# ── Kategoriyalar ──────────────────────────────────────────────────────────────

@router.get("/kategoriyalar")
async def categories_page(request: Request,
                            admin: str = Depends(get_current_admin),
                            db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    med_service = MedicineService(db)
    categories  = await cat_service.get_all()
    counts      = await cat_service.count_by_category_bulk()   # bitta SQL
    return templates.TemplateResponse("admin/categories.html", {
        "request": request,
        "site_name": settings.site_name,
        "admin": admin,
        "categories": categories,
        "counts": counts,
    })


@router.post("/kategoriyalar/qoshish")
async def category_add(request: Request,
                        nomi: str = Form(...),
                        gopharm_slug: str = Form(""),
                        admin: str = Depends(get_current_admin),
                        db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    med_service = MedicineService(db)
    nomi_clean = nomi.strip()
    cat = await cat_service.create(nomi_clean, gopharm_slug=gopharm_slug.strip() or None)
    if cat is None:
        categories = await cat_service.get_all()
        counts     = await cat_service.count_by_category_bulk()
        return templates.TemplateResponse("admin/categories.html", {
            "request": request,
            "site_name": settings.site_name,
            "admin": admin,
            "categories": categories,
            "counts": counts,
            "error": f'"{ nomi_clean }" nomli kategoriya allaqachon mavjud.',
        }, status_code=400)
    return RedirectResponse("/admin/kategoriyalar", status_code=303)


@router.post("/kategoriyalar/{category_id}/tahrirlash")
async def category_edit(category_id: int,
                         nomi: str = Form(...),
                         gopharm_slug: str = Form(""),
                         admin: str = Depends(get_current_admin),
                         db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    await cat_service.update(category_id, nomi=nomi.strip(),
                              gopharm_slug=gopharm_slug.strip() or None)
    return RedirectResponse("/admin/kategoriyalar", status_code=303)


@router.post("/kategoriyalar/{category_id}/ochirish")
async def category_delete(category_id: int,
                           admin: str = Depends(get_current_admin),
                           db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    await cat_service.delete(category_id)
    return RedirectResponse("/admin/kategoriyalar", status_code=303)


# ── Gopharm API (admin AJAX) ───────────────────────────────────────────────────

@router.get("/api/gopharm-izlash")
async def gopharm_search_api(q: str = "",
                               admin: str = Depends(get_current_admin)):
    """Admin uchun Gopharm qidiruv JSON API."""
    gp = GopharmService()
    results = await gp.search(q, limit=20)
    return JSONResponse({
        "results": [
            {
                "id":           d.id,
                "name":         d.name,
                "category":     d.category or "",
                "manufacturer": d.manufacturer or "",
                "image_url":    d.image_url or "",
                "price":        d.price_str,
                "gopharm_url":  d.gopharm_url,
                "slug":         d.slug,
                "barcode":      d.barcode or "",
                "dosage_form":  d.dosage_form or "",
                "composition":  d.composition or "",
                "prescription": d.prescription,
            }
            for d in results
        ]
    })


@router.post("/gopharm/saqlash")
async def gopharm_save(
    gp_id:        int  = Form(...),
    gp_name:      str  = Form(...),
    gp_category:  str  = Form(""),
    gp_mfr:       str  = Form(""),
    gp_image:     str  = Form(""),
    gp_price:     str  = Form(""),
    gp_barcode:   str  = Form(""),
    gp_dosage:    str  = Form(""),
    gp_comp:      str  = Form(""),
    gp_recept:    str  = Form(""),
    gp_slug:      str  = Form(""),
    local_category: str = Form(""),
    admin: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Gopharmdan topilgan dorini mahalliy bazaga saqlash."""
    med_service = MedicineService(db)
    source_url = f"https://gopharm.uz/uz/product/{gp_slug}" if gp_slug else None

    # Takror saqlashni oldini olish (source_url orqali)
    if source_url:
        from sqlalchemy import select
        existing = await db.execute(
            select(Medicine).where(Medicine.source_url == source_url)
        )
        if existing.scalar_one_or_none():
            return JSONResponse({"ok": True, "duplicate": True})

    price = None
    try:
        price = float(gp_price.replace(" ", "").replace(",", "")) if gp_price else None
    except Exception:
        pass

    data = {
        "name":        gp_name.strip(),
        "category":    local_category.strip() or gp_category.strip() or None,
        "manufacturer": gp_mfr.strip() or None,
        "image_url":   gp_image.strip() or None,
        "price":       price,
        "barcode":     gp_barcode.strip() or None,
        "dosage_form": gp_dosage.strip() or None,
        "composition": gp_comp.strip() or None,
        "prescription": gp_recept == "true",
        "source_url":  source_url,
        "is_active":   True,
    }
    med = await med_service.create(data)
    return JSONResponse({"ok": True, "id": med.id})


# ── Dorilar ───────────────────────────────────────────────────────────────────

@router.get("/dorilar")
async def medicines_page(request: Request,
                          admin: str = Depends(get_current_admin),
                          db: AsyncSession = Depends(get_db),
                          q: str = "",
                          kategoriya: str = "",
                          page: int = 1):
    med_service = MedicineService(db)
    cat_service = CategoryService(db)
    categories  = await cat_service.get_all()

    per_page = 30
    if q:
        medicines = await med_service.autocomplete(q, limit=200)
    elif kategoriya:
        medicines = await med_service.get_by_category(kategoriya, limit=500)
    else:
        medicines = await med_service.get_all(limit=per_page, offset=(page - 1) * per_page)

    total = await med_service.count()

    return templates.TemplateResponse("admin/medicines.html", {
        "request":    request,
        "site_name":  settings.site_name,
        "admin":      admin,
        "medicines":  medicines,
        "categories": categories,
        "q":          q,
        "kategoriya": kategoriya,
        "page":       page,
        "total":      total,
        "per_page":   per_page,
    })


@router.get("/dorilar/yangi")
async def medicine_new_form(request: Request,
                             admin: str = Depends(get_current_admin),
                             db: AsyncSession = Depends(get_db)):
    cat_service = CategoryService(db)
    categories  = await cat_service.get_all()
    return templates.TemplateResponse("admin/medicine_form.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "categories": categories,
        "medicine":  None,
    })


@router.post("/dorilar/yangi")
async def medicine_create(request: Request,
                           name: str = Form(...),
                           category: str = Form(""),
                           manufacturer: str = Form(""),
                           dosage_form: str = Form(""),
                           strength: str = Form(""),
                           composition: str = Form(""),
                           description: str = Form(""),
                           image_url: str = Form(""),
                           image_file: UploadFile = None,
                           price: str = Form(""),
                           barcode: str = Form(""),
                           age_group: str = Form(""),
                           t136_filial: str = Form(""),
                           admin: str = Depends(get_current_admin),
                           db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    cat_service = CategoryService(db)
    uploaded_url = await _save_uploaded_image(image_file)
    category_name = category.strip() or None
    if category_name and not await cat_service.get_by_name(category_name):
        await cat_service.create(category_name)
    data = {
        "name":        name.strip(),
        "category":    category_name,
        "manufacturer": manufacturer.strip() or None,
        "dosage_form": dosage_form.strip() or None,
        "strength":    strength.strip() or None,
        "composition": composition.strip() or None,
        "description": description.strip() or None,
        "image_url":   uploaded_url or (image_url.strip() or None),
        "barcode":     barcode.strip() or None,
        "price":       float(price) if price.strip() else None,
        "age_group":   age_group.strip() or None,
        "t136_filial": bool(t136_filial),
    }
    medicine = await med_service.create(data)
    return RedirectResponse(f"/admin/dorilar/{medicine.id}/tahrirlash", status_code=303)


@router.get("/dorilar/{medicine_id}/tahrirlash")
async def medicine_edit_form(request: Request, medicine_id: int,
                              admin: str = Depends(get_current_admin),
                              db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    cat_service = CategoryService(db)
    medicine   = await med_service.get_by_id(medicine_id)
    categories = await cat_service.get_all()
    return templates.TemplateResponse("admin/medicine_form.html", {
        "request":    request,
        "site_name":  settings.site_name,
        "admin":      admin,
        "categories": categories,
        "medicine":   medicine,
    })


@router.post("/dorilar/{medicine_id}/tahrirlash")
async def medicine_update(request: Request, medicine_id: int,
                           name: str = Form(...),
                           category: str = Form(""),
                           manufacturer: str = Form(""),
                           dosage_form: str = Form(""),
                           strength: str = Form(""),
                           composition: str = Form(""),
                           description: str = Form(""),
                           image_url: str = Form(""),
                           image_file: UploadFile = None,
                           price: str = Form(""),
                           barcode: str = Form(""),
                           age_group: str = Form(""),
                           t136_filial: str = Form(""),
                           admin: str = Depends(get_current_admin),
                           db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    cat_service = CategoryService(db)
    uploaded_url = await _save_uploaded_image(image_file)
    category_name = category.strip() or None
    if category_name and not await cat_service.get_by_name(category_name):
        await cat_service.create(category_name)
    data = {
        "name":        name.strip(),
        "category":    category_name,
        "manufacturer": manufacturer.strip() or None,
        "dosage_form": dosage_form.strip() or None,
        "strength":    strength.strip() or None,
        "composition": composition.strip() or None,
        "description": description.strip() or None,
        "image_url":   uploaded_url or (image_url.strip() or None),
        "barcode":     barcode.strip() or None,
        "price":       float(price) if price.strip() else None,
        "age_group":   age_group.strip() or None,
        "t136_filial": bool(t136_filial),
    }
    await med_service.update(medicine_id, data)
    return RedirectResponse("/admin/dorilar", status_code=303)


@router.post("/dorilar/{medicine_id}/ochirish")
async def medicine_delete(medicine_id: int,
                           admin: str = Depends(get_current_admin),
                           db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    await med_service.delete(medicine_id)
    return RedirectResponse("/admin/dorilar", status_code=303)


@router.post("/dorilar/{medicine_id}/kategoriya")
async def medicine_quick_category(medicine_id: int,
                                   kategoriya: str = Form(""),
                                   admin: str = Depends(get_current_admin),
                                   db: AsyncSession = Depends(get_db)):
    med_service = MedicineService(db)
    medicine = await med_service.update(medicine_id, {"category": kategoriya.strip() or None})
    if not medicine:
        return JSONResponse({"ok": False}, status_code=404)
    return JSONResponse({"ok": True, "id": medicine.id, "category": medicine.category})


# ── Gopharm dorisini kategoriya bilan tez saqlash (ommaviy /gp/{id} sahifasidan) ──

@router.post("/dorilar/saqlash-gp")
async def gopharm_quick_save(
    gp_id: int = Form(...),
    category_id: str = Form(""),
    t136_filial: str = Form(""),
    admin: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ommaviy GoPharm dori sahifasidagi \"Mahalliy bazaga saqlash\" formasi uchun."""
    gp = GopharmService()
    drug = await gp.get_by_id(gp_id)
    if not drug:
        return RedirectResponse(f"/gp/{gp_id}", status_code=303)

    med_service = MedicineService(db)
    cat_service = CategoryService(db)

    category_name = None
    if category_id.strip():
        cat = await cat_service.get_by_id(int(category_id))
        if cat:
            category_name = cat.nomi

    is_t136 = bool(t136_filial)
    source_url = drug.gopharm_url

    existing = await db.execute(
        select(Medicine).where(Medicine.source_url == source_url)
    )
    existing_med = existing.scalar_one_or_none()
    if existing_med:
        update_data = {"t136_filial": is_t136}
        if category_name:
            update_data["category"] = category_name
        await med_service.update(existing_med.id, update_data)
        return RedirectResponse(f"/gp/{gp_id}", status_code=303)

    data = {
        "name":         drug.name,
        "category":     category_name or drug.category,
        "manufacturer": drug.manufacturer,
        "image_url":    drug.image_url,
        "price":        drug.price,
        "barcode":      drug.barcode,
        "dosage_form":  drug.dosage_form,
        "composition":  drug.composition,
        "description":  drug.description,
        "prescription": drug.prescription,
        "source_url":   source_url,
        "is_active":    True,
        "t136_filial":  is_t136,
    }
    await med_service.create(data)
    return RedirectResponse(f"/gp/{gp_id}", status_code=303)


# ── Sozlamalar ──────────────────────────────────────────────────────────────

@router.get("/sozlamalar")
async def settings_page(request: Request,
                         admin: str = Depends(get_current_admin)):
    return templates.TemplateResponse("admin/settings.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "settings":  settings,
        "success":   None,
        "error":     None,
    })


@router.post("/sozlamalar/umumiy")
async def settings_update_general(request: Request,
                                   site_name: str = Form(...),
                                   timezone: str = Form(...),
                                   rate_limit_requests: int = Form(...),
                                   rate_limit_minutes: int = Form(...),
                                   admin: str = Depends(get_current_admin)):
    site_name_clean = site_name.strip() or "PharmBaseUZ"
    update_env_values({
        "SITE_NAME": site_name_clean,
        "TIMEZONE": timezone.strip() or "Asia/Tashkent",
        "RATE_LIMIT_REQUESTS": rate_limit_requests,
        "RATE_LIMIT_MINUTES": rate_limit_minutes,
    })
    settings.site_name = site_name_clean
    settings.timezone = timezone.strip() or "Asia/Tashkent"
    settings.rate_limit_requests = rate_limit_requests
    settings.rate_limit_minutes = rate_limit_minutes
    return templates.TemplateResponse("admin/settings.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "settings":  settings,
        "success":   "Umumiy sozlamalar saqlandi.",
        "error":     None,
    })


@router.post("/sozlamalar/admin")
async def settings_update_admin(request: Request,
                                 admin_username: str = Form(...),
                                 current_password: str = Form(""),
                                 new_password: str = Form(""),
                                 new_password_confirm: str = Form(""),
                                 admin: str = Depends(get_current_admin)):
    error = None
    success = None

    username_clean = admin_username.strip() or "admin"
    env_updates = {"ADMIN_USERNAME": username_clean}

    if new_password or new_password_confirm or current_password:
        if not check_admin_credentials(admin, current_password):
            error = "Joriy parol noto'g'ri."
        elif len(new_password) < 4:
            error = "Yangi parol kamida 4 belgidan iborat bo'lishi kerak."
        elif new_password != new_password_confirm:
            error = "Yangi parollar bir-biriga mos kelmadi."
        else:
            hashed = hash_password(new_password)
            env_updates["ADMIN_PASSWORD_HASH"] = hashed
            settings.admin_password_hash = hashed

    if not error:
        update_env_values(env_updates)
        settings.admin_username = username_clean
        request.session["admin_username"] = username_clean
        admin = username_clean
        success = "Admin ma'lumotlari saqlandi."

    return templates.TemplateResponse("admin/settings.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "settings":  settings,
        "success":   success,
        "error":     error,
    })


@router.post("/sozlamalar/animatsiya")
async def settings_update_animation(request: Request,
                                     site_animation_style: str = Form(...),
                                     animation_image: UploadFile = None,
                                     admin: str = Depends(get_current_admin)):
    allowed = {"pills", "particles", "molecules", "waves", "custom", "none"}
    style_clean = site_animation_style.strip().lower()
    if style_clean not in allowed:
        style_clean = "pills"

    error = None
    success = "3D animatsiya uslubi yangilandi."
    env_updates = {"SITE_ANIMATION_STYLE": style_clean}

    if style_clean == "custom":
        uploaded_url = await _save_uploaded_anim(animation_image)
        if uploaded_url:
            env_updates["SITE_ANIMATION_IMAGE_URL"] = uploaded_url
            settings.site_animation_image_url = uploaded_url
            success = "Rasmingiz yuklandi va butun sayt bo'ylab harakatlanadigan 3D fon sifatida qo'yildi."
        elif not settings.site_animation_image_url:
            error = "\"Mening rasmim\" uslubini tanlash uchun avval rasm yuklang (JPG, PNG, WEBP yoki GIF)."
            style_clean = settings.site_animation_style or "pills"
            env_updates["SITE_ANIMATION_STYLE"] = style_clean

    update_env_values(env_updates)
    settings.site_animation_style = style_clean

    return templates.TemplateResponse("admin/settings.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "settings":  settings,
        "success":   None if error else success,
        "error":     error,
    })


@router.post("/sozlamalar/fon")
async def settings_update_background(request: Request,
                                      background_file: UploadFile = None,
                                      admin: str = Depends(get_current_admin)):
    error = None
    success = None

    uploaded_url = await _save_uploaded_bg(background_file)
    if uploaded_url:
        update_env_values({"SITE_BACKGROUND_URL": uploaded_url})
        settings.site_background_url = uploaded_url
        success = "Fon rasmi yangilandi."
    else:
        error = "Rasm yuklanmadi. JPG, PNG, WEBP yoki GIF formatidagi faylni tanlang."

    return templates.TemplateResponse("admin/settings.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "settings":  settings,
        "success":   success,
        "error":     error,
    })


@router.post("/sozlamalar/fon/ochirish")
async def settings_remove_background(request: Request,
                                      admin: str = Depends(get_current_admin)):
    update_env_values({"SITE_BACKGROUND_URL": ""})
    settings.site_background_url = ""
    return templates.TemplateResponse("admin/settings.html", {
        "request":   request,
        "site_name": settings.site_name,
        "admin":     admin,
        "settings":  settings,
        "success":   "Fon rasmi olib tashlandi.",
        "error":     None,
    })
