import json
import uuid

from sqlalchemy import select

from app.models import Property, ServiceQuote
from app.services.quote_extractor import clean_excerpt
from tests.test_servicios import buscar, caso, con_direccion, equipo, pedir  # noqa: F401

TRANSCRIPT = ("Cliente: hola, buen día, le llamo de parte de un cliente. Técnico: Buenas, habla Frío Técnico del Valle, "
              "sí hacemos ese trabajo, la revisión y limpieza cuesta setecientos pesos, no cobro la visita y puedo ir el jueves por la tarde. "
              "Mi número es 55 1234 5678.")


def test_extracto_solo_trabajo_y_precio_sin_nombre_del_negocio():
    said = "Sí hacemos ese trabajo, la revisión y limpieza cuesta setecientos pesos con Frío Técnico del Valle, no cobro la visita. Llame al 55 1234 5678."
    out = clean_excerpt(said, TRANSCRIPT, ["Frío Técnico del Valle"])
    assert out and "setecientos pesos" in out
    assert "Valle" not in out and "5512345678" not in out.replace(" ", "") and "1234" not in out


def test_extracto_inventado_se_descarta():
    assert clean_excerpt("Cobra mil quinientos pesos por cambiar el compresor completo y da dos años de garantía.", TRANSCRIPT, []) is None
    assert clean_excerpt("ok", TRANSCRIPT, []) is None


def test_cotizaciones_traen_extracto_pero_nunca_la_transcripcion(caso, db):
    c, tokens = caso
    r = buscar(c, db, tokens)
    assert all(q["excerpt"] for q in r["quotes"])
    d = c.get(f"/service-requests/{r['id']}/quotes/{r['quotes'][0]['id']}").json()
    assert d["quote"]["excerpt"]
    nombres = [p.name for p in db.scalars(select(Property).where(False))]  # sin tocar propiedades
    assert "transcript" not in json.dumps(r).lower() and nombres == []


def test_telefono_del_perfil(caso, db):
    c, tokens = caso
    assert c.get("/me").json()["user"]["phone"] is None
    assert c.put("/me/phone", json={"phone": "123"}).status_code == 422
    assert c.put("/me/phone", json={"phone": "55 1234 5678"}).json()["phone"] == "+525512345678"
    assert c.get("/me").json()["user"]["phone"] == "+525512345678"
    assert c.put("/me/phone", json={"phone": ""}).json()["phone"] is None


def test_varias_direcciones_y_elegir_al_pedir(caso, db):
    c, tokens = caso
    con_direccion(c)
    nueva = c.post("/properties", json={"name": "Casa de mamá"})
    assert nueva.status_code == 201 and nueva.json()["address"]["complete"] is False
    pid = nueva.json()["id"]
    r = pedir(c, equipo(c, db, tokens[0]))
    assert c.post(f"/service-requests/{r['id']}/scope", json={"property_id": pid}).status_code == 422  # aún sin dirección completa
    assert c.put(f"/properties/{pid}/address", json={"street": "Calle Falsa 45", "colony": "Roma Norte", "postal_code": "06700",
                                                     "city": "Ciudad Servicios", "state": "CDMX", "search_radius_km": 10}).status_code == 200
    s = c.post(f"/service-requests/{r['id']}/scope", json={"property_id": pid}).json()
    assert s["property_id"] == pid and s["address_name"] == "Casa de mamá"
    assert c.post(f"/service-requests/{r['id']}/scope", json={"property_id": str(uuid.uuid4())}).status_code == 404
    assert len(c.get("/me").json()["home"]["properties"]) == 2
    for _ in range(3):
        c.post("/properties", json={"name": "Otra"})
    assert c.post("/properties", json={"name": "Una de más"}).status_code == 409  # máximo 5


def test_compartir_telefono_solo_con_telefono_y_permiso(caso, db):
    c, tokens = caso
    r = buscar(c, db, tokens)
    qid = r["quotes"][0]["id"]
    body = {"quote_id": qid, "slot_index": 0, "consent": True, "share_phone": True}
    assert c.post(f"/service-requests/{r['id']}/schedule", json=body).status_code == 422  # no tiene teléfono guardado
    c.put("/me/phone", json={"phone": "55 1234 5678"})
    s = c.post(f"/service-requests/{r['id']}/schedule", json=body).json()
    assert s["appointment"]["contact_shared"] is True
    assert "5512345678" not in json.dumps(s)  # el número nunca regresa en la respuesta de la cita
