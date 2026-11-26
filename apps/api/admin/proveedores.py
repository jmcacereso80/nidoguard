"""Directorio de tecnicos.

Uso:
  python -m admin.proveedores buscar --ciudad "Ciudad de México" --especialidad aire_acondicionado [--forzar]
  python -m admin.proveedores listar [--ciudad "Ciudad de México"]
  python -m admin.proveedores no-llamar --telefono +5255...
Nunca imprime llaves. Los telefonos solo se muestran aqui, nunca en la API de personas usuarias.
"""
import argparse
from sqlalchemy import select
from app.db import SessionLocal
from app.models import ServiceProvider
from app.services.providers import SPECIALTIES, ensure_directory


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buscar"); b.add_argument("--ciudad", required=True)
    b.add_argument("--especialidad", required=True, choices=sorted(SPECIALTIES)); b.add_argument("--forzar", action="store_true")
    l = sub.add_parser("listar"); l.add_argument("--ciudad")
    n = sub.add_parser("no-llamar"); n.add_argument("--telefono", required=True)
    a = ap.parse_args()
    with SessionLocal() as db:
        if a.cmd == "buscar":
            r = ensure_directory(db, a.ciudad, a.especialidad, force=a.forzar)
            print(f"{r.key}: {r.status}, {r.results} resultados, {r.new_providers} nuevos {r.detail or ''}")
        elif a.cmd == "listar":
            q = select(ServiceProvider).order_by(ServiceProvider.city, ServiceProvider.name)
            if a.ciudad:
                q = q.where(ServiceProvider.city == a.ciudad)
            for p in db.scalars(q):
                print(f"{p.name} | {p.phone_e164} | {p.city} | {p.rating} ({p.reviews}) | {','.join(p.specialties)} | {'NO LLAMAR' if p.do_not_call else p.status}")
        else:
            p = db.scalar(select(ServiceProvider).where(ServiceProvider.phone_e164 == a.telefono))
            if not p:
                raise SystemExit("No encontré ese teléfono")
            p.do_not_call = True
            db.commit()
            print("Marcado: no llamar")


if __name__ == "__main__":
    main()
