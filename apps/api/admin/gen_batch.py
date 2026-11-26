"""Genera un lote de kits: guarda solo hashes en la base y escribe los archivos de impresion.

Uso:  python -m admin.gen_batch --name "Lote 1" --kits 100 --tags-per-kit 20 --out ./salida

Salidas (los codigos en claro solo existen en estos archivos, nunca en la base):
  kits.csv      codigo de activacion, codigo corto y URL del QR de cada kit
  etiquetas.csv URL /t/<token> de cada etiqueta, para grabar el NFC
  hojas.pdf     una hoja por kit con su QR y el codigo corto
"""
import argparse
import csv
import io
import os

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Kit, KitStatus, SmartTag, TagBatch
from app.services.codes import hash_code, new_activation_code, new_short_code, new_tag_token


def generate(db: Session, name: str, kits: int, tags_per_kit: int):
    base = get_settings().app_url.rstrip("/")
    batch = TagBatch(name=name, tags_per_kit=tags_per_kit)
    db.add(batch)
    db.flush()
    kit_rows, tag_rows = [], []
    for _ in range(kits):
        code, short = new_activation_code(), new_short_code()
        kit = Kit(batch_id=batch.id, code_hash=hash_code(code), short_hash=hash_code(short),
                  status=KitStatus.fabricado)
        db.add(kit)
        db.flush()
        kit_rows.append((str(kit.id), code, short, f"{base}/k/{code}"))
        for _ in range(tags_per_kit):
            token = new_tag_token()
            db.add(SmartTag(kit_id=kit.id, token=token))
            tag_rows.append((str(kit.id), token, f"{base}/t/{token}"))
    db.commit()
    return batch, kit_rows, tag_rows


def write_files(out: str, kit_rows, tag_rows):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "kits.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kit_id", "codigo", "codigo_corto", "url_activacion"])
        w.writerows(kit_rows)
    with open(os.path.join(out, "etiquetas.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kit_id", "token", "url_nfc"])
        w.writerows(tag_rows)
    c = canvas.Canvas(os.path.join(out, "hojas.pdf"), pagesize=A4)
    W, H = A4
    for _, code, short, _url in kit_rows:
        # El QR lleva solo el codigo corto que se imprime debajo (D-004 actualizado).
        img = qrcode.make(short)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(W / 2, H - 90, "Activa tu kit NidoGuard")
        c.drawImage(ImageReader(buf), W / 2 - 110, H - 400, 220, 220)
        c.setFont("Helvetica", 13)
        c.drawCentredString(W / 2, H - 430, "Escanea el QR con tu celular, o escribe este código en la app:")
        c.setFont("Courier-Bold", 26)
        c.drawCentredString(W / 2, H - 470, short)
        c.setFont("Helvetica", 10)
        c.drawCentredString(W / 2, 50, "nidoguard.com")
        c.showPage()
    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--kits", type=int, required=True)
    ap.add_argument("--tags-per-kit", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with SessionLocal() as db:
        batch, kit_rows, tag_rows = generate(db, a.name, a.kits, a.tags_per_kit)
    write_files(a.out, kit_rows, tag_rows)
    print(f"Lote {batch.id}: {len(kit_rows)} kits, {len(tag_rows)} etiquetas en {a.out}")


if __name__ == "__main__":
    main()
