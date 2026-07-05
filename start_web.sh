#!/bin/bash
# PharmBaseUZ sayti — Alwaysdata ishga tushirish skripti
# Alwaysdata panelida "Command" maydoniga shu yo'lni yozing:
#   /home/yourlogin/www/Farmbaza/start_web.sh

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Alwaysdata odatda $PORT muhit o'zgaruvchisini beradi, bo'lmasa 8000 ishlatiladi
PORT="${PORT:-8000}"

exec uvicorn webapp.main:app --host 0.0.0.0 --port "$PORT"
