"""Lineas de servicio de fabricantes (una vez por marca; una persona verifica el numero antes de usarlo).

Uso:
  python -m admin.fabricantes agregar --marca Carrier --telefono "55 1234 5678" [--horario "L-V 8 a 20"] [--requiere-titular] [--fuente URL]
  python -m admin.fabricantes verificar --marca Carrier
  python -m admin.fabricantes descartar --marca Carrier
  python -m admin.fabricantes listar
  python -m admin.fabricantes buscar --marca Carrier          (busca en internet la linea de servicio; queda por verificar)
  python -m admin.fabricantes buscar-pendientes [--max 20]    (las marcas de los equipos registrados que aun no tienen linea)
"""
import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import EquipmentAsset, ManufacturerServiceLine
from app.services.line_finder import get_line_finder
from app.services.manufacturers import brand_key, ensure_line, mark_verified
from app.services.providers import to_e164_mx


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("agregar"); a_.add_argument("--marca", required=True); a_.add_argument("--telefono", required=True)
    a_.add_argument("--horario"); a_.add_argument("--requiere-titular", action="store_true"); a_.add_argument("--fuente")
    for n in ("verificar", "descartar"):
        sub.add_parser(n).add_argument("--marca", required=True)
    sub.add_parser("listar")
    sub.add_parser("buscar").add_argument("--marca", required=True)
    sub.add_parser("buscar-pendientes").add_argument("--max", type=int, default=20)
    a = ap.parse_args()
    with SessionLocal() as db:
        if a.cmd == "listar":
            for l in db.scalars(select(ManufacturerServiceLine).order_by(ManufacturerServiceLine.brand)):
                listo = " <- lista para verificar" if l.status == "por_verificar" and l.confirmed_count >= 3 and l.wrong_count == 0 else ""
                print(f"{l.brand:20} {l.phone_e164 or '-':15} {l.status:13} sí:{l.confirmed_count} no:{l.wrong_count}  {l.source or ''}{listo}")
            return
        if a.cmd in ("buscar", "buscar-pendientes"):
            finder = get_line_finder()
            if a.cmd == "buscar":
                marcas = [a.marca]
            else:
                tenemos = {l.brand_key for l in db.scalars(select(ManufacturerServiceLine))}
                vistas = {}
                for b in db.scalars(select(EquipmentAsset.brand).where(EquipmentAsset.brand.is_not(None)).distinct()):
                    if brand_key(b) and brand_key(b) not in tenemos:
                        vistas.setdefault(brand_key(b), b)
                marcas = list(vistas.values())[: a.max]
            for marca in marcas:
                l = ensure_line(db, marca, finder)
                print(f"{marca}: {l.status if l else 'sin cambios'} {l.phone_e164 or '' if l else ''} {l.source or '' if l else ''}")
            print("Recuerda: lo encontrado queda por_verificar. Una persona debe llamar al número y luego correr 'verificar'.")
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
