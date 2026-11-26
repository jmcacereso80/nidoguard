from app.main import app
from app.models import AssetEvent, EquipmentAsset, SmartTag, TagStatus
from app.services.storage import get_storage
from tests.test_fase3_4 import setup, uid


class FakeStorage:
    def __init__(self): self.deleted = []
    def presign_put(self, key, content_type, expires=600): return f"https://fake/{key}"
    def presign_get(self, key, expires=600): return f"https://fake/{key}"
    def head(self, key): return None
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
