"""Un paso de las llamadas (avanza busquedas, reintentos, citas y recordatorios). Para cron mientras Prefect no esta alojado:
  * * * * * cd apps/api && python -m admin.tick"""
from app.db import SessionLocal
from app.services.call_results import tick
from app.services.voice import get_voice

if __name__ == "__main__":
    with SessionLocal() as db:
        print(tick(db, get_voice()))
