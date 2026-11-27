"""Ver que paso en las llamadas (para pruebas con tu numero). La transcripcion es de TU prueba: no la compartas.

Uso:
  python -m admin.llamadas ultimas [--n 5]            estado, duracion, costo y tamano de la transcripcion
  python -m admin.llamadas ver <id> [--lineas 40]     el final de la transcripcion de una llamada
  python -m admin.llamadas releer <id>                vuelve a leer la transcripcion con Claude y muestra el resultado (NO guarda nada)
"""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from app.db import SessionLocal
from app.models import ServiceCall


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("ultimas"); u.add_argument("--n", type=int, default=5)
    v = sub.add_parser("ver"); v.add_argument("id"); v.add_argument("--lineas", type=int, default=40)
    r = sub.add_parser("releer"); r.add_argument("id")
    a = ap.parse_args()
    with SessionLocal() as db:
        if a.cmd == "ultimas":
            for c in db.scalars(select(ServiceCall).order_by(ServiceCall.created_at.desc()).limit(a.n)):
                t = c.transcript or ""
                print(f"{c.id}  {c.purpose:<11} {c.status:<12} {c.duration_s or 0:>4}s  US${c.cost_usd or 0:.2f}  transcripción {len(t)} caracteres  "
                      f"{c.created_at.astimezone(ZoneInfo('America/Mexico_City')):%d/%m %H:%M}")
            return
        c = db.get(ServiceCall, a.id)
        if not c:
            raise SystemExit("No encontré esa llamada.")
        if a.cmd == "ver":
            print("\n".join((c.transcript or "(sin transcripción)").splitlines()[-a.lineas:]))
        else:
            from app.services.quote_extractor import get_extractor
            from app.models import ServiceRequest
            req = db.get(ServiceRequest, c.request_id)
            hoy = datetime.now(ZoneInfo("America/Mexico_City")).date()
            if not (c.transcript or "").strip():
                raise SystemExit("Esa llamada no tiene transcripción.")
            print(get_extractor().quote(c.transcript, req.scope_text or "", hoy).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
