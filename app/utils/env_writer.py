"""✅ .env faylini o'qish/yozish uchun yordamchi funksiyalar (Sozlamalar sahifasi uchun)."""

import os

ENV_PATH = ".env"


def update_env_values(values: dict) -> None:
    """.env fayldagi berilgan kalitlarni yangilaydi (mavjud bo'lmasa qo'shadi).

    Boshqa qatorlar (izohlar, bo'sh qatorlar, boshqa sozlamalar) o'zgarishsiz qoladi.
    """
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    remaining = dict(values)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}\n")
                continue
        new_lines.append(line)

    if remaining:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        for key, val in remaining.items():
            new_lines.append(f"{key}={val}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
