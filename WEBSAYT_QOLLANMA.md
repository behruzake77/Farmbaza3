# PharmBaseUZ — Sayt (webapp/) qo'llanmasi

Bu — **mustaqil veb-sayt**. Telegram bot bilan bog'liq barcha kod
(`app/handlers`, `app/keyboards`, `app/middlewares`, bot tokeni va h.k.)
loyihadan olib tashlangan — sayt ishlashi uchun Telegram bot tokeni yoki
boshqa hech qanday bot sozlamasi kerak emas.

## Nima qo'shildi

```
webapp/
  main.py              — FastAPI ilovasi
  dependencies.py       — DB sessiya va admin autentifikatsiya
  routers/
    public.py           — bosh sahifa, qidiruv API, kategoriya/dori sahifalari
    admin.py             — login, dashboard, kategoriya va dori CRUD
  templates/             — HTML sahifalar (Jinja2)
  static/css/style.css   — dizayn
  static/js/search.js    — jonli qidiruv (rasm bilan, apteka.uz uslubida)
  static/js/admin.js     — admin panelda tez kategoriya biriktirish (AJAX)
start_web.sh              — saytni ishga tushirish skripti
```

`app/services/medicine_service.py` ichida `autocomplete()` metodi bor —
saytdagi jonli qidiruv shundan foydalanadi.

## Mahalliy ishga tushirish

```bash
cd Farmbaza
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # va qiymatlarni to'ldiring
uvicorn webapp.main:app --reload
```

Brauzerda: `http://localhost:8000`
Admin panel: `http://localhost:8000/admin` (login: `.env` dagi `ADMIN_USERNAME`/`ADMIN_PASSWORD`)

## Qidiruv qanday ishlaydi (apteka.uz uslubida)

Bosh sahifadagi qidiruv katagiga 2 ta harf yozilishi bilan (`webapp/static/js/search.js`)
`/api/qidiruv?q=...` manziliga so'rov ketadi va natijalar rasm + nom + kategoriya
bilan pastda ochiladigan ro'yxatda chiqadi. Bazadagi nomlar ko'pincha kirillcha
("КРЕОН"), foydalanuvchi esa lotincha yozishi mumkin ("kreon") — shuning uchun
`app/utils/search_engine.py` dagi transliteratsiya funksiyasidan foydalanilib,
ikkala yozuv ham bir-biriga solishtiriladi. Avval nom **shu harflar bilan
boshlanadigan** dorilar, keyin **ichida uchraydigan** dorilar, hech narsa
topilmasa esa imlo xatosiga chidamli (rapidfuzz) qidiruv ishga tushadi.

## Kategoriyaga dori qo'shishni osonlashtirish

`/admin/dorilar` sahifasida har bir dori qatorida kategoriya tanlash oynachasi
bor. Uni o'zgartirishning o'zi yetarli — sahifa qayta yuklanmaydi, AJAX orqali
darhol saqlanadi va yashil "✓ saqlandi" belgisi chiqadi
(`webapp/static/js/admin.js`). Bu — ko'p sonli dorilarni tezda tartiblash uchun.

Yangi dori qo'shish, tahrirlash va o'chirish uchun `/admin/dorilar/yangi` va
`/admin/dorilar/{id}/tahrirlash` sahifalari bor. Kategoriyalarni qo'shish/o'chirish
uchun — `/admin/kategoriyalar`.

## Admin parolini xavfsiz qilish (production uchun MUHIM)

`.env` dagi oddiy `ADMIN_PASSWORD` faqat sinov uchun. Productionda hash ishlating:

```bash
python3 app/utils/security.py
```

Bu sizdan parol so'raydi va `ADMIN_PASSWORD_HASH=$2b$12$...` qiymatini beradi —
shuni `.env` fayliga qo'shing. `ADMIN_PASSWORD_HASH` mavjud bo'lsa, tizim
avtomatik o'shani ishlatadi.

`.env` dagi `SITE_SECRET_KEY` ni albatta o'zgartiring (tasodifiy uzun matn),
aks holda login sessiyalari xavfsiz bo'lmaydi.

## Alwaysdata'ga joylash

Alwaysdata panelida "Scheduled task → Daemon" bo'limida:

- **Command**: `/home/yourlogin/www/Farmbaza/start_web.sh`
- Alwaysdata odatda `PORT` muhit o'zgaruvchisini beradi — skript uni avtomatik ishlatadi.
- Sайт uchun domain/subdomain (masalan `pharmbaseuz.uz`) ni shu portga
  "reverse proxy" qilib bog'lang (Alwaysdata panelida Site → Add site → Proxy).

## Keyingi qadam sifatida tavsiya

- Har bir dori uchun `image_url` to'ldirilsa, qidiruv natijalarida va sahifada
  rasm chiqadi; bo'lmasa, nom bosh harfi bilan avtomatik belgicha chiqadi.
- Dorilar ko'payishi bilan (~10,000+) `autocomplete()` metodini to'liq matn
  qidiruvga (masalan PostgreSQL `pg_trgm` yoki Meilisearch) o'tkazish tezlikni
  yanada oshiradi — hozirgi yechim SQLite/oddiy PostgreSQL uchun yetarli tez.


---

## 🚀 Render.com da deploy qilish

### Nega SQLite Render da ishlamaydi?
Render free trifida fayl tizimi **ephemeral** — har deploydan keyin yoki restart bo'lganda barcha fayllar (shu jumladan `pharmbaseuz.db`) o'chib ketadi. Shuning uchun **PostgreSQL** ishlatish shart.

### Qadamlar

**1. GitHub ga yuklang**
```bash
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/SIZNING/farmbaseuz.git
git push -u origin main
```

**2. Render dashboard da:**
- [dashboard.render.com](https://dashboard.render.com) → **New** → **PostgreSQL**
  - Name: `pharmbaseuz-db`
  - Plan: **Free**
  - Yaratib bo'lgach Internal Database URL ni nusxalang

- **New** → **Web Service** → GitHub repo tanlang
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn webapp.main:app --host 0.0.0.0 --port $PORT`

**3. Environment variables qo'shing:**
| Kalit | Qiymat |
|---|---|
| `DATABASE_URL` | PostgreSQL Internal URL (Render beradi) |
| `USE_SQLITE` | `False` |
| `SITE_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | O'z parolingiz |

**4. Deploy — tayyor!** Render avtomatik `render.yaml` ni taniydi.

### Ma'lumotlarni SQLite → PostgreSQL ko'chirish
```bash
# Lokal: SQLite dan dump olish
python3 - <<'PYEOF'
import sqlite3, json

conn = sqlite3.connect("pharmbaseuz.db")
conn.row_factory = sqlite3.Row
tables = ["medicines", "kategoriyalar", "users"]
dump = {}
for t in tables:
    rows = conn.execute(f"SELECT * FROM {t}").fetchall()
    dump[t] = [dict(r) for r in rows]
with open("db_dump.json", "w", encoding="utf-8") as f:
    json.dump(dump, f, ensure_ascii=False, default=str)
print(f"✅ {sum(len(v) for v in dump.values())} ta yozuv saqlandi")
PYEOF

# Keyin Render da yoki psql bilan import qiling
```
