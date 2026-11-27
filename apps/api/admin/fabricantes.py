"""Lineas de servicio de fabricantes (una vez por marca; una persona verifica el numero antes de usarlo).

Uso:
  python -m admin.fabricantes agregar --marca Carrier --telefono "55 1234 5678" [--horario "L-V 8 a 20"] [--requiere-titular] [--fuente URL]
  python -m admin.fabricantes verificar --marca Carrier
  python -m admin.fabricantes descartar --marca Carrier
  python -m admin.fabricantes listar
"""
import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ManufacturerServiceLine
from app.services.manufacturers import brand_key, mark_verified
from app.services.providers import to_e164_mx


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("agregar"); a_.add_argument("--marca", required=True); a_.add_argument("--telefono", required=True)
    a_.add_argument("--horario"); a_.add_argument("--requiere-titular", action="store_true"); a_.add_argument("--fuente")
    for n in ("verificar", "descartar"):
        sub.add_parser(n).add_argument("--marca", required=True)
    sub.add_parser("listar")
    a = ap.parse_args()
    with SessionLocal() as db:
        if a.cmd == "listar":
            for l in db.scalars(select(ManufacturerServiceLine).order_by(ManufacturerServiceLine.brand)):
                print(f"{l.brand:20} {l.phone_e164:15} {l.status:13} {l.hours or ''}")
            return
        key = brand_key(a.marca)
        line = db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == key))
        if a.cmd == "agregar":
            phone = to_e164_mx(a.telefono)
            if not phone:
                raise SystemExit("Teléfono inválido (10 dígitos).")
            line = line or ManufacturerServiceLine(brand_key=key, brand=a.marca.strip(), phone_e164=phone)
            line.phone_e164, line.hours, line.source = phone, a.horario, a.fuente
            line.requires_account_holder, line.status, line.verified_at = a.requiere_titular, "por_verificar", None
            db.add(line)
        elif not line:
            raise SystemExit("No existe esa marca.")
        elif a.cmd == "verificar":
            mark_verified(line)
        else:
            line.status = "descartada"
        db.commit()
        print(f"{line.brand}: {line.status}")


if __name__ == "__main__":
    main()
