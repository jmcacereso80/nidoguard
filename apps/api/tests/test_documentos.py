import uuid

from app.main import app
from app.models import AssetDocument
from app.services.storage import get_storage
from tests.test_crud_equipo import _register
from tests.test_fase3_4 import setup

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 200
PDF = b"%PDF-1.4\n" + b"0" * 200


class FakeStorage:
    def __init__(self): self.objects = {}
    def presign_put(self, key, content_type, expires=600): return f"https://fake/{key}"
    def presign_get(self, key, expires=600): return f"https://fake/{key}"
    def head(self, key):
        return {"size": len(self.objects[key]), "content_type": None} if key in self.objects else None
    def get_bytes(self, key): return self.objects[key]
    def delete(self, key): self.objects.pop(key, None)


def _subir(c, db, fs, asset_id, kind, filename, ct, data):
    r = c.post(f"/assets/{asset_id}/documents/upload-url",
               json={"kind": kind, "filename": filename, "content_type": ct, "size": len(data)})
    assert r.status_code == 200, r.text
    doc_id = r.json()["document_id"]
    fs.objects[db.get(AssetDocument, uuid.UUID(doc_id)).storage_key] = data  # simula la subida directa a R2
    return doc_id, c.post(f"/assets/{asset_id}/documents/{doc_id}/process")


def test_upload_url_checks_kind_type_and_size(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    url = f"/assets/{a['id']}/documents/upload-url"
    assert c.post(url, json={"kind": "manual", "filename": "x.jpg", "content_type": "image/jpeg", "size": 10}).status_code == 422
    assert c.post(url, json={"kind": "garantia", "filename": "x.exe", "content_type": "application/x-msdownload", "size": 10}).status_code == 422
    assert c.post(url, json={"kind": "garantia", "filename": "x.pdf", "content_type": "application/pdf", "size": 21 * 1024 * 1024}).status_code == 413
    ok = c.post(url, json={"kind": "garantia", "filename": "garantia.pdf", "content_type": "application/pdf", "size": len(PDF)})
    assert ok.status_code == 200 and ok.json()["upload_url"].startswith("https://fake/") and ok.json()["headers"]["Content-Type"] == "application/pdf"


def test_process_checks_real_file_type_and_accepts_photo_and_pdf(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    doc, r = _subir(c, db, fs, a["id"], "garantia", "foto.jpg", "image/jpeg", JPEG)
    assert r.status_code == 200 and r.json()["uploaded"] is True
    doc2, r2 = _subir(c, db, fs, a["id"], "garantia", "garantia.pdf", "application/pdf", PDF)
    assert r2.status_code == 200 and r2.json()["uploaded"] is True
    # un texto con extension de foto se rechaza y el archivo se borra
    doc3, r3 = _subir(c, db, fs, a["id"], "factura", "falsa.jpg", "image/jpeg", b"hola, soy texto")
    assert r3.status_code == 422 and db.get(AssetDocument, uuid.UUID(doc3)) is None


def test_same_file_twice_is_not_stored_twice(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    _subir(c, db, fs, a["id"], "garantia", "a.jpg", "image/jpeg", JPEG)
    _, r = _subir(c, db, fs, a["id"], "garantia", "a-copia.jpg", "image/jpeg", JPEG)
    assert r.status_code == 200 and r.json()["duplicado"] is True
    assert db.query(AssetDocument).filter_by(asset_id=a["id"], kind="garantia").count() == 1


def test_warranty_needs_date_and_document_and_can_fix_price(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    doc, _ = _subir(c, db, fs, a["id"], "garantia", "garantia.jpg", "image/jpeg", JPEG)
    fac, _ = _subir(c, db, fs, a["id"], "factura", "factura.pdf", "application/pdf", PDF)
    pendiente = c.get(f"/assets/{a['id']}/documents").json()
    assert pendiente["warranty"] is None and pendiente["warranty_pending"]["document_id"] == doc
    assert c.post(f"/assets/{a['id']}/warranty", json={"document_id": fac, "ends_on": "2027-01-10"}).status_code == 422
    r = c.post(f"/assets/{a['id']}/warranty", json={"document_id": doc, "ends_on": "2027-01-10", "provider": "Mabe", "price": 8500})
    assert r.status_code == 200
    d = c.get(f"/assets/{a['id']}/documents").json()
    assert d["warranty"]["ends_on"] == "2027-01-10" and d["warranty"]["price"] == 8500 and d["warranty_pending"] is None
    assert d["invoice"]["name"] == "factura.pdf"
    # corregir el precio despues
    c.post(f"/assets/{a['id']}/warranty", json={"document_id": doc, "ends_on": "2027-01-10", "price": 7900})
    assert c.get(f"/assets/{a['id']}/documents").json()["warranty"]["price"] == 7900


def test_no_date_means_no_warranty_and_care_is_empty(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    assert c.get(f"/assets/{a['id']}/documents").json()["warranty"] is None
    care = c.get(f"/assets/{a['id']}/care").json()
    assert care == {"model_confirmed": False, "tasks": []}
