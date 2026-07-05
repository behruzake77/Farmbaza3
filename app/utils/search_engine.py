"""
Kuchli qidiruv tizimi:
- Mahalliy baza birinchi (tez)
- Gopharm API parallel (to'liq)
- Fuzzy + translit + token search
"""
import re
from typing import List, Tuple
from rapidfuzz import fuzz

TRANSLIT = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh",
    "з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o",
    "п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"kh","ц":"ts",
    "ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
    # lotin → kirill (teskari)
    "a":"а","b":"б","d":"д","e":"е","f":"ф","g":"г","i":"и","j":"й",
    "k":"к","l":"л","m":"м","n":"н","o":"о","p":"п","r":"р","s":"с",
    "t":"т","u":"у","v":"в","z":"з",
}

# Keng tarqalgan xato yozilishlar
SYNONYMS = {
    "paratsetamol": ["paracetamol","парацетамол","парацетамол","acetaminophen"],
    "paracetamol":  ["paratsetamol","парацетамол","acetaminophen"],
    "ibuprofen":    ["ibuklin","ибупрофен","nurofen","нурофен"],
    "nurofen":      ["ibuprofen","нурофен","nurofen"],
    "amoxicillin":  ["amoksisilin","амоксициллин","amoxil"],
    "vitamin":      ["витамин","vit"],
    "kreon":        ["креон","pancreatin","панкреатин"],
    "omez":         ["omeprazol","omeprazole","омепразол"],
    "aspirin":      ["аспирин","asperine","ацетилсалициловая"],
}


def transliterate(text: str) -> str:
    """Kirill ↔ lotin transliteratsiya."""
    result = []
    i = 0
    text = text.lower()
    while i < len(text):
        # Ikki harfli kombinatsiyalar
        two = text[i:i+2]
        if two in ("sh","ch","zh","kh","ts","yo","yu","ya","sch"):
            result.append(text[i:i+2])
            i += 2
        else:
            result.append(TRANSLIT.get(text[i], text[i]))
            i += 1
    return "".join(result)


def normalize(text: str) -> str:
    """Matnni normallashtiryish: kichik harf, ortiqcha belgilarni olib tashlash."""
    if not text:
        return ""
    text = text.lower().strip()
    # Kirill bo'lsa transliteratsiya
    if re.search(r"[а-яёА-ЯЁ]", text):
        text = transliterate(text)
    # Faqat harf, raqam, bo'sh joy
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_synonyms(query: str) -> List[str]:
    """So'z uchun sinonimlar ro'yxati."""
    q = normalize(query)
    syns = [q]
    for key, vals in SYNONYMS.items():
        if q == normalize(key) or q in [normalize(v) for v in vals]:
            syns.append(normalize(key))
            syns.extend(normalize(v) for v in vals)
    return list(dict.fromkeys(syns))  # takrorsiz


def score_match(query: str, name: str, name_ru: str = "", composition: str = "") -> float:
    """
    Dori nomi bilan so'rov qanchalik mos kelishini hisoblash.
    0-100 oralig'ida ball qaytaradi.
    """
    q = normalize(query)
    if not q:
        return 0.0

    # Tekshiriladigan matnlar
    targets = [
        normalize(name or ""),
        normalize(name_ru or ""),
        normalize(composition or ""),
    ]
    # Transliteratsiya variantlari
    targets += [transliterate(t) for t in targets if t]
    targets = [t for t in targets if t]

    if not targets:
        return 0.0

    best = 0.0
    q_words = q.split()

    for target in targets:
        t_words = target.split()

        # 1. To'liq mos (100 ball)
        if q == target:
            return 100.0

        # 2. Boshlanish mos (so'z boshlanishi)
        if target.startswith(q):
            best = max(best, 97.0)
            continue

        # 3. So'z boshidan mos (masalan "par" → "paracetamol")
        for tw in t_words:
            if tw.startswith(q):
                best = max(best, 92.0)

        # 4. Birinchi so'z boshi mos
        if t_words and t_words[0].startswith(q_words[0] if q_words else ""):
            best = max(best, 88.0)

        # 5. Fuzzy (xato yozilish uchun)
        s1 = fuzz.token_set_ratio(q, target)
        s2 = fuzz.partial_ratio(q, target)
        s3 = fuzz.WRatio(q, target)
        best = max(best, s1 * 0.9, s2 * 0.85, s3 * 0.88)

    # Sinonimlar orqali bonus
    for syn in get_synonyms(query)[1:]:  # birinchisi o'zi
        for target in targets:
            if target.startswith(syn) or syn in target:
                best = max(best, 82.0)

    return round(best, 1)


def normalize_query(query: str) -> str:
    """Public API — qidiruv so'zini normallash."""
    return normalize(query)


def transliterate_cyrillic(text: str) -> str:
    """Public API — kirill → lotin."""
    return transliterate(text)


# build_search_corpus va fuzzy_search — eski kod bilan moslik
def build_search_corpus(records):
    corpus = []
    for record_id, name, latin_name, keywords, barcode in records:
        parts = []
        if name:
            parts.append(name.lower())
            parts.append(transliterate(name))
        if latin_name:
            parts.append(latin_name.lower())
        if keywords:
            parts.extend(k.strip().lower() for k in keywords.split(","))
        if barcode:
            parts.append(barcode.lower())
        combined = " | ".join(dict.fromkeys(filter(None, parts)))
        corpus.append((record_id, combined))
    return corpus


def fuzzy_search(query, corpus, threshold=65, limit=20):
    if not query or not corpus:
        return []
    is_barcode = bool(re.match(r"^\d{8,14}$", query.strip()))
    if is_barcode:
        results = []
        for rid, text in corpus:
            for part in text.split("|"):
                part = part.strip()
                if part == query.strip():
                    results.append((rid, 100.0))
                elif query.strip() in part:
                    results.append((rid, 95.0))
        unique = {}
        for rid, s in results:
            if rid not in unique or unique[rid] < s:
                unique[rid] = s
        return sorted(unique.items(), key=lambda x: x[1], reverse=True)[:limit]

    q = normalize(query)
    scored = []
    for rid, text in corpus:
        parts = [p.strip() for p in text.split("|")]
        best = 0.0
        for part in parts:
            s = max(
                fuzz.token_set_ratio(q, part),
                fuzz.partial_ratio(q, part),
                fuzz.WRatio(q, part),
            )
            best = max(best, s)
        if best >= threshold:
            scored.append((rid, best))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
