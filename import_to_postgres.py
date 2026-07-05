"""
db_dump.json ni PostgreSQL ga import qiluvchi skript.

Ishlatish:
  pip install psycopg2-binary
  DATABASE_URL="postgresql://user:password@host:5432/dbname" python3 import_to_postgres.py
"""
import json, os, sys
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL muhit o'zgaruvchisi o'rnatilmagan!")
    print("   Masalan: export DATABASE_URL='postgresql://pharmuser:parol@localhost:5432/pharmbaseuz'")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 o'rnatilmagan. pip install psycopg2-binary")
    sys.exit(1)

DUMP_FILE = os.path.join(os.path.dirname(__file__), "db_dump.json")
if not os.path.exists(DUMP_FILE):
    print(f"❌ {DUMP_FILE} topilmadi!")
    sys.exit(1)

print("📂 db_dump.json o'qilmoqda...")
with open(DUMP_FILE, encoding="utf-8") as f:
    dump = json.load(f)

# postgres:// → postgresql://
url = DATABASE_URL
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

print(f"🔌 PostgreSQL ga ulanmoqda...")
conn = psycopg2.connect(url)
cur = conn.cursor()

# --- kategoriyalar ---
cats = dump.get("kategoriyalar", [])
if cats:
    print(f"📁 kategoriyalar: {len(cats)} ta...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kategoriyalar (
            id SERIAL PRIMARY KEY,
            nom TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    for c in cats:
        cur.execute(
            "INSERT INTO kategoriyalar (id, nom, created_at) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (c.get("id"), c.get("nom"), c.get("created_at") or datetime.now())
        )
    print(f"   ✅ {len(cats)} ta kategoriya saqlandi")

# --- medicines ---
meds = dump.get("medicines", [])
if meds:
    print(f"💊 medicines: {len(meds)} ta (bu biroz vaqt olishi mumkin)...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id SERIAL PRIMARY KEY,
            name TEXT,
            name_uz TEXT,
            name_ru TEXT,
            barcode TEXT,
            manufacturer TEXT,
            category TEXT,
            description TEXT,
            image_url TEXT,
            dosage_form TEXT,
            strength TEXT,
            composition TEXT,
            age_group TEXT,
            age_ai_generated INTEGER DEFAULT 0,
            description_ai_generated INTEGER DEFAULT 0,
            frequency TEXT,
            prescription INTEGER DEFAULT 0,
            source_url TEXT,
            price REAL,
            is_active INTEGER DEFAULT 1,
            t136_filial INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cols = ["id","name","name_uz","name_ru","barcode","manufacturer","category",
            "description","image_url","dosage_form","strength","composition",
            "age_group","age_ai_generated","description_ai_generated","frequency",
            "prescription","source_url","price","is_active","t136_filial",
            "created_at","updated_at"]

    batch = []
    for i, m in enumerate(meds):
        row = tuple(m.get(c) for c in cols)
        batch.append(row)
        if len(batch) == 500:
            execute_values(cur,
                f"INSERT INTO medicines ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING",
                batch)
            batch = []
            print(f"   ... {i+1}/{len(meds)} ta import qilindi", end="\r")
    if batch:
        execute_values(cur,
            f"INSERT INTO medicines ({','.join(cols)}) VALUES %s ON CONFLICT (id) DO NOTHING",
            batch)
    print(f"\n   ✅ {len(meds)} ta dori saqlandi")

conn.commit()
cur.close()
conn.close()
print("\n🎉 Import muvaffaqiyatli yakunlandi!")
