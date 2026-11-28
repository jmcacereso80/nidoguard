"""Directorio de tecnicos.

Uso:
  python -m admin.proveedores buscar --ciudad "Ciudad de México" --especialidad aire_acondicionado [--forzar]
  python -m admin.proveedores listar [--ciudad "Ciudad de México"]
  python -m admin.proveedores no-llamar --telefono +5255...
  python -m admin.proveedores prueba --telefono "55 1234 5678" [--nombre "Técnico de prueba"]   (un técnico falso con TU número, en tu dirección)
  python -m admin.proveedores quitar-prueba
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
    t = sub.add_parser("prueba"); t.add_argument("--telefono", required=True); t.add_argument("--nombre", default="Técnico de prueba")
    sub.add_parser("quitar-prueba")
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
        elif a.cmd == "prueba":
            from app.models import Property
            from app.services.providers import to_e164_mx
            phone = to_e164_mx(a.telefono)
            prop = db.scalar(select(Property).where(Property.lat.is_not(None)).order_by(Property.created_at))
            if not phone or not prop:
                raise SystemExit("Hace falta un teléfono de 10 dígitos y una dirección guardada con ubicación (Mi hogar).")
            p = db.scalar(select(ServiceProvider).where(ServiceProvider.source_id == f"prueba:{phone}")) or ServiceProvider(source="prueba", source_id=f"prueba:{phone}")
            p.name, p.phone_e164, p.city, p.colony, p.address = a.nombre, phone, prop.city, prop.colony, prop.address
            p.lat, p.lng, p.specialties, p.rating, p.reviews, p.status, p.do_not_call = prop.lat, prop.lng, sorted(SPECIALTIES), 5.0, 1, "activo", False
            db.add(p)
            db.commit()
            print(f"Técnico de prueba listo en {prop.city}. Pon su número en CALLS_ALLOWLIST para que solo a él se llame.")
        elif a.cmd == "quitar-prueba":
            n = 0
            for p in db.scalars(select(ServiceProvider).where(ServiceProvider.source == "prueba")):
                p.status, p.do_not_call, n = "descartado", True, n + 1
            db.commit()
            print(f"Desactivados: {n}")
        else:
            p = db.scalar(select(ServiceProvider).where(ServiceProvider.phone_e164 == a.telefono))
            if not p:
                raise SystemExit("No encontré ese teléfono")
            p.do_not_call = True
            db.commit()
            print("Marcado: no llamar")


if __name__ == "__main__":
    main()
