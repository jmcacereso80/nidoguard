import uuid
from admin.gen_batch import generate
from app.main import app
from app.services.storage import get_storage


class FakeStorage:
    def __init__(self): self.objects = {}
    def presign_put(self, key, content_type, expires=600): return f"https://fake/{key}"
    def presign_get(self, key, expires=600): return f"https://fake/{key}"
    def head(self, key): return self.objects.get(key)
    def get_bytes(self, key): return b"x"


def uid(): return "u_" + uuid.uuid4().hex[:8]


def setup(make_client, db, kits=1, tags=3):
    _, k, t = generate(db, "L", kits=kits, tags_per_kit=tags)
    c = make_client(uid()); c.post("/home", json={"name": "Casa"})
    c.post("/kits/claim", json={"code": k[0][1]})
    return c, [x[1] for x in t if x[0] == k[0][0]]


def test_fast_registration_with_new_space_and_upload(make_client, db):
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    c, tokens = setup(make_client, db)
    r = c.post("/assets", json={"tag_token": tokens[0], "name": "Lavadora", "new_space_name": "Lavandería",
                                "plate_content_type": "image/jpeg"})
    assert r.status_code == 201
    up = r.json()["upload"]
    assert up["method"] == "PUT" and "fake/org/" in up["url"]
    assert c.post(f"/assets/{r.json()['id']}/images/{up['image_id']}/uploaded").status_code == 409
    fs.objects[up["url"].replace("https://fake/", "")] = {"size": 1000, "content_type": "image/jpeg"}
    assert c.post(f"/assets/{r.json()['id']}/images/{up['image_id']}/uploaded").status_code == 200
    kit = c.get("/kits").json()[0]
    assert kit["tags_used"] == 1 and kit["tags_total"] == 3
    # la etiqueta ya no se puede reutilizar
    again = c.post("/assets", json={"tag_token": tokens[0], "name": "Otra", "new_space_name": "Cocina"})
    assert again.status_code == 409
    assert c.get(f"/tags/{tokens[0]}").json()["state"] == "vinculada"


def test_location_is_required_and_file_types_checked(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    assert c.post("/assets", json={"tag_token": tokens[0], "name": "X"}).status_code == 422
    bad = c.post("/assets", json={"tag_token": tokens[0], "name": "X", "new_space_name": "A",
                                  "plate_content_type": "application/pdf"})
    assert bad.status_code == 422


def test_other_home_cannot_use_or_see_asset(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = c.post("/assets", json={"tag_token": tokens[0], "name": "Mia", "new_space_name": "Sala"}).json()
    intruder = make_client(uid()); intruder.post("/home", json={"name": "Intruso"})
    assert intruder.get(f"/assets/{a['id']}").status_code == 404
    assert intruder.post("/assets", json={"tag_token": tokens[1], "name": "Robo", "new_space_name": "X"}).status_code == 404
    assert intruder.get("/assets").json() == []


def test_manual_and_confirm_flow(make_client, db):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = c.post("/assets", json={"tag_token": tokens[0], "name": "Aire", "new_space_name": "Recámara"}).json()
    assert [x["id"] for x in c.get("/assets?status=por_confirmar").json()] == [a["id"]]
    m = c.patch(f"/assets/{a['id']}/manual", json={"brand": "Mabe", "model": "LMA123", "extra": {"btu": 12000}})
    assert m.json()["status"] == "completo" and m.json()["extra"]["btu"] == 12000
    d = c.get(f"/assets/{a['id']}").json()
    assert d["reading"]["source"] == "manual" and [e["type"] for e in d["events"]] == ["registro", "datos_manuales"]
    assert c.get("/assets?status=por_confirmar").json() == []
