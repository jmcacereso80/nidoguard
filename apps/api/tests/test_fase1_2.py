import os
import uuid
from sqlalchemy import select
from admin.gen_batch import generate, write_files
from app.models import Kit, SmartTag, TagStatus


def uid():
    return "u_" + uuid.uuid4().hex[:8]


def test_me_requires_login(make_client):
    c = make_client(None)
    assert c.get("/me").status_code == 401


def test_home_and_spaces(make_client):
    c = make_client(uid())
    assert c.get("/me").json()["home"] is None
    r = c.post("/home", json={"name": "Casa Lomas"})
    assert r.status_code == 201 and r.json()["name"] == "Casa Lomas"
    s = c.post("/spaces", json={"name": "Taller de papá", "icon": "wrench"})
    assert s.status_code == 201
    assert [x["name"] for x in c.get("/spaces").json()] == ["Taller de papá"]
    # crear el hogar dos veces no duplica
    assert c.post("/home", json={"name": "Otra"}).json()["name"] == "Casa Lomas"


def test_spaces_are_isolated_between_homes(make_client):
    a, b = make_client(uid()), None
    a.post("/home", json={"name": "A"}); a.post("/spaces", json={"name": "Cocina A"})
    b = make_client(uid()); b.post("/home", json={"name": "B"})
    assert b.get("/spaces").json() == []


def test_batch_generation_stores_only_hashes(db, tmp_path):
    batch, kits, tags = generate(db, "Lote prueba", kits=3, tags_per_kit=4)
    assert len(kits) == 3 and len(tags) == 12
    code = kits[0][1]
    stored = db.scalars(select(Kit)).all()
    assert all(code not in (k.code_hash, k.short_hash) for k in stored)
    write_files(str(tmp_path), kits, tags)
    assert os.path.getsize(tmp_path / "hojas.pdf") > 1000
    assert (tmp_path / "etiquetas.csv").read_text().count("/t/") == 12


def test_claim_flow_and_one_time_use(make_client, db):
    _, kits, _ = generate(db, "Lote claim", kits=2, tags_per_kit=3)
    code, short = kits[0][1], kits[0][2]
    a = make_client(uid()); a.post("/home", json={"name": "Hogar A"})
    r = a.post("/kits/claim", json={"code": code})
    assert r.status_code == 200 and r.json()["tags_total"] == 3 and r.json()["tags_used"] == 0
    assert a.post("/kits/claim", json={"code": code}).status_code == 200  # idempotente para su dueño
    b = make_client(uid()); b.post("/home", json={"name": "Hogar B"})
    assert b.post("/kits/claim", json={"code": code}).status_code == 409
    assert b.post("/kits/claim", json={"code": short}).status_code == 409  # el corto tambien esta usado
    # codigo corto escrito en minusculas y sin guion tambien sirve
    c2 = b.post("/kits/claim", json={"code": kits[1][2].replace("-", "").lower()})
    assert c2.status_code == 200
    assert len(a.get("/kits").json()) == 1


def test_claim_rate_limit(make_client):
    c = make_client(uid()); c.post("/home", json={"name": "H"})
    codes = [c.post("/kits/claim", json={"code": f"INVALIDO{i}"}).status_code for i in range(12)]
    assert codes[:10] == [404] * 10 and codes[10:] == [429, 429]


def test_tag_cases(make_client, db):
    _, kits, tags = generate(db, "Lote tags", kits=1, tags_per_kit=2)
    token = tags[0][1]
    anon = make_client(None)
    assert anon.get(f"/tags/{token}").json() == {"state": "necesita_sesion"}
    assert anon.get("/tags/NOEXISTE").status_code == 404
    owner = make_client(uid()); owner.post("/home", json={"name": "Dueño"})
    assert owner.get(f"/tags/{token}").json() == {"state": "ajena"}  # kit sin activar
    owner.post("/kits/claim", json={"code": kits[0][1]})
    assert owner.get(f"/tags/{token}").json()["state"] == "disponible"
    other = make_client(uid()); other.post("/home", json={"name": "Otro"})
    assert other.get(f"/tags/{token}").json() == {"state": "ajena"}
