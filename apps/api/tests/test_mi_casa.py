from sqlalchemy import select

from app.models import EquipmentAsset, Property, Space
from tests.test_servicios import buscar, caso, con_direccion, equipo, pedir  # noqa: F401

DIR2 = {"street": "Calle Falsa 45", "colony": "Roma Norte", "postal_code": "06700", "city": "Ciudad Servicios", "state": "CDMX", "search_radius_km": 10}


def test_perfil_nombres_apellidos_y_telefono(caso, db):
    c, _ = caso
    r = c.put("/me/profile", json={"first_name": " Juan Manuel ", "last_name": "Cáceres", "phone": "55 1234 5678"})
    assert r.status_code == 200 and r.json()["name"] == "Juan Manuel Cáceres" and r.json()["phone"] == "+525512345678"
    u = c.get("/me").json()["user"]
    assert (u["first_name"], u["last_name"], u["name"]) == ("Juan Manuel", "Cáceres", "Juan Manuel Cáceres")
    # sin mandar teléfono, no se toca
    assert c.put("/me/profile", json={"first_name": "Juan", "last_name": ""}).json()["phone"] == "+525512345678"
    assert c.put("/me/profile", json={"first_name": "Juan", "phone": "123"}).status_code == 422
    assert c.put("/me/profile", json={"first_name": "", "last_name": "x"}).status_code == 422
    assert c.put("/me/profile", json={"first_name": "Juan", "phone": ""}).json()["phone"] is None


def test_direccion_principal_nombre_y_equipos(caso, db):
    c, tokens = caso
    con_direccion(c)
    props = c.get("/me").json()["home"]["properties"]
    assert len(props) == 1 and props[0]["address"]["is_primary"] is True
    nueva = c.post("/properties", json={"name": "Casa de mamá"}).json()
    assert nueva["address"]["is_primary"] is False
    r = c.put(f"/properties/{nueva['id']}/address", json={**DIR2, "name": "Casa de Mamá", "is_primary": True})
    assert r.status_code == 200 and r.json()["is_primary"] is True
    props = {p["id"]: p for p in c.get("/me").json()["home"]["properties"]}
    assert props[nueva["id"]]["name"] == "Casa de Mamá"
    assert sum(1 for p in props.values() if p["address"]["is_primary"]) == 1
    assert c.get("/me").json()["home"]["properties"][0]["id"] == nueva["id"]  # la principal va primero


def test_quitar_direccion_pasa_los_equipos(caso, db):
    c, tokens = caso
    con_direccion(c)
    a = equipo(c, db, tokens[0])
    props = c.get("/me").json()["home"]["properties"]
    original = props[0]["id"]
    assert props[0]["assets_count"] >= 1
    assert c.delete(f"/properties/{original}").status_code == 409  # única
    otra = c.post("/properties", json={"name": "Oficina"}).json()["id"]
    assert c.delete(f"/properties/{original}").status_code == 409  # tiene equipos: hay que elegir a dónde
    assert c.delete(f"/properties/{original}", params={"move_to": "00000000-0000-0000-0000-000000000000"}).status_code == 404
    out = c.delete(f"/properties/{original}", params={"move_to": otra})
    assert out.status_code == 200
    ps = out.json()["properties"]
    assert [p["id"] for p in ps] == [otra] and ps[0]["address"]["is_primary"] is True and ps[0]["assets_count"] >= 1
    assert db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == a["id"])) is not None
