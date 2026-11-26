from app.main import app
from app.models import AssetEvent, EquipmentAsset, SmartTag, TagStatus
from app.services.storage import get_storage
from tests.test_fase3_4 import setup, uid


class FakeStorage:
    def __init__(self): self.deleted = []; self.objects = {}
    def presign_put(self, key, content_type, expires=600): return f"https://fake/{key}"
    def presign_get(self, key, expires=600): return f"https://fake/{key}"
    def head(self, key): return self.objects.get(key)
    def get_bytes(self, key): return b"x"
    def delete(self, key): self.deleted.append(key)


def _register(c, token, name="Lavadora", space="Cocina", photo=False):
    body = {"tag_token": token, "name": name, "new_space_name": space}
    if photo:
        body["plate_content_type"] = "image/jpeg"
    r = c.post("/assets", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_edit_fixes_name_brand_and_records_event(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    r = c.patch(f"/assets/{a['id']}", json={"name": "Refrigerador", "brand": "Mabe", "serial": " 8H2K9 "})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Refrigerador" and body["brand"] == "Mabe" and body["serial"] == "8H2K9"
    assert body["status"] == a["status"]                     # editar no cambia el estado
    ev = db.query(AssetEvent).filter_by(asset_id=a["id"], type="edicion").one()
    assert sorted(ev.payload["fields"]) == ["brand", "name", "serial"]


def test_edit_can_move_to_another_space_and_clear_a_field(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0], space="Cocina")
    b = _register(c, tokens[1], name="Taller", space="Taller")
    assert c.patch(f"/assets/{a['id']}", json={"brand": "Mabe"}).status_code == 200
    r = c.patch(f"/assets/{a['id']}", json={"space_id": b["space_id"], "brand": ""})
    assert r.status_code == 200
    assert r.json()["space_id"] == b["space_id"] and r.json()["brand"] is None


def test_edit_rejects_empty_name_and_unknown_space(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    assert c.patch(f"/assets/{a['id']}", json={"name": "   "}).status_code == 422
    assert c.patch(f"/assets/{a['id']}", json={"space_id": None}).status_code == 422
    import uuid
    assert c.patch(f"/assets/{a['id']}", json={"space_id": str(uuid.uuid4())}).status_code == 404


def test_delete_removes_asset_frees_tag_and_deletes_photo(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0], photo=True)
    assert c.delete(f"/assets/{a['id']}").status_code == 204
    assert db.get(EquipmentAsset, a["id"]) is None
    assert c.get(f"/assets/{a['id']}").status_code == 404
    tag = db.query(SmartTag).filter_by(token=tokens[0]).one()
    assert tag.status == TagStatus.disponible                # la etiqueta queda libre
    assert len(fs.deleted) == 1                              # la foto se borra de R2
    # la misma etiqueta ya sirve para otro equipo
    assert _register(c, tokens[0], name="Estufa", space="Cocina")["name"] == "Estufa"


def test_other_home_cannot_edit_or_delete(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    intruso = make_client(uid()); intruso.post("/home", json={"name": "Otra"})
    assert intruso.patch(f"/assets/{a['id']}", json={"name": "Robado"}).status_code in (403, 404)
    assert intruso.delete(f"/assets/{a['id']}").status_code in (403, 404)
    assert db.get(EquipmentAsset, a["id"]) is not None


def test_name_is_taken_from_ai_when_user_does_not_type_it(make_client, db):
    from app.models import AssetImage
    from app.services.readings import process_reading
    from tests.test_fase5 import Fake, Store, ext
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = c.post("/assets", json={"tag_token": tokens[0], "new_space_name": "Cocina",
                                "plate_content_type": "image/jpeg"}).json()
    assert a["name"] == "Equipo sin nombre"                # sin nombre: se espera la lectura
    img = db.query(AssetImage).filter_by(asset_id=a["id"]).one()
    process_reading(db, Store(), img.asset_id, img.id, Fake("haiku", ext()), None)  # sugiere "Lavadora"
    assert c.get(f"/assets/{a['id']}").json()["name"] == "Lavadora"


def test_without_ai_name_user_must_type_it_before_confirming(make_client, db):
    from app.models import AssetImage
    from app.services.plate_reader import PlateExtraction
    from app.services.readings import process_reading
    from tests.test_fase5 import Fake, Store, ext
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = c.post("/assets", json={"tag_token": tokens[0], "new_space_name": "Cocina",
                                "plate_content_type": "image/jpeg"}).json()
    img = db.query(AssetImage).filter_by(asset_id=a["id"]).one()
    sin_nombre = ext().model_copy(update={"suggested_name": None})
    process_reading(db, Store(), img.asset_id, img.id, Fake("haiku", sin_nombre), None)
    assert c.post(f"/assets/{a['id']}/confirm", json={}).status_code == 422
    assert c.patch(f"/assets/{a['id']}", json={"name": "Estufa"}).status_code == 200
    r = c.post(f"/assets/{a['id']}/confirm", json={})
    assert r.status_code == 200 and r.json()["name"] == "Estufa" and r.json()["status"] == "completo"


def test_retake_photo_for_existing_asset_restarts_reading(make_client, db):
    from app.models import AssetImage
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0], photo=True)
    r = c.post(f"/assets/{a['id']}/fotos", json={"content_type": "image/png"})
    assert r.status_code == 200, r.text
    up = r.json()
    assert up["url"].startswith("https://fake/") and up["headers"]["Content-Type"] == "image/png"
    img = db.get(AssetImage, __import__("uuid").UUID(up["image_id"]))
    assert img.asset_id is not None and img.kind == "placa"
    assert c.post(f"/assets/{a['id']}/fotos", json={"content_type": "text/html"}).status_code == 422
    fs.objects[img.storage_key] = {"size": 10, "content_type": "image/png"}
    assert c.post(f"/assets/{a['id']}/images/{up['image_id']}/uploaded").status_code == 200
    assert c.get(f"/assets/{a['id']}").json()["status"] == "registrado"


def test_product_photo_alone_does_not_start_a_reading(make_client, db):
    from app.models import AssetImage, AssetReading
    import uuid
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0], photo=True)
    r = c.post(f"/assets/{a['id']}/fotos", json={"content_type": "image/jpeg", "kind": "equipo"})
    assert r.status_code == 200
    img = db.get(AssetImage, uuid.UUID(r.json()["image_id"]))
    fs.objects[img.storage_key] = {"size": 10, "content_type": "image/jpeg"}
    up = c.post(f"/assets/{a['id']}/images/{img.id}/uploaded")
    assert up.status_code == 200 and up.json()["lectura"] is False
    assert db.query(AssetReading).filter_by(asset_id=a["id"]).count() == 0


def test_reader_gets_plate_and_product_photos_together(make_client, db):
    import uuid
    from app.models import AssetImage
    from app.services.readings import process_reading
    from tests.test_fase5 import ext
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0], photo=True)
    placa = db.query(AssetImage).filter_by(asset_id=a["id"]).one()
    placa.uploaded = True
    r = c.post(f"/assets/{a['id']}/fotos", json={"content_type": "image/jpeg", "kind": "equipo"})
    equipo = db.get(AssetImage, uuid.UUID(r.json()["image_id"]))
    equipo.uploaded = True; db.commit()

    class Capture:
        name = "capture"
        def __init__(self): self.calls = []
        def read(self, image, ct, extra=None):
            self.calls.append((image, ct, extra)); return ext()
    cap = Capture()
    process_reading(db, fs, uuid.UUID(a["id"]), placa.id, cap, None)
    _, _, extra = cap.calls[0]
    assert extra is not None and len(extra) == 1 and extra[0][1] == "image/jpeg"
    assert c.post(f"/assets/{a['id']}/fotos", json={"content_type": "image/jpeg", "kind": "equipo"}).status_code == 200
    assert c.post(f"/assets/{a['id']}/fotos", json={"content_type": "image/jpeg", "kind": "equipo"}).status_code == 422
