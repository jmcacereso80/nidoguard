import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from app.config import get_settings
from app.main import app
from app.models import AssetEvent, CareTask, CareTemplate, EquipmentAsset, Property, ServiceProvider, ServiceRequest
from app.services import requests_flow as F
from app.services.geocoder import FakeGeocoder, get_geocoder
from app.services.providers import FakeSource
from app.services.scope import FakeScopeWriter, get_scope_writer
from app.services.storage import get_storage
from tests.test_crud_equipo import _register
from tests.test_documentos import FakeStorage
from tests.test_fase3_4 import setup, uid


@pytest.fixture()
def caso(make_client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "fake_voice_step_seconds", 0)
    monkeypatch.setattr(get_settings(), "voice", "fake")
    monkeypatch.setattr(F, "get_source", lambda: FakeSource())
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder()
    app.dependency_overrides[get_scope_writer] = lambda: FakeScopeWriter()
    c, tokens = setup(make_client, db, tags=6)
    return c, tokens


def con_direccion(c, city="Ciudad Servicios"):
    pid = c.get("/me").json()["home"]["properties"][0]["id"]
    r = c.put(f"/properties/{pid}/address", json={"street": "Gabriel Mancera 123", "colony": "Del Valle Centro",
                                                  "postal_code": "03100", "city": city, "state": "CDMX"})
    assert r.status_code == 200


def equipo(c, db, token, nombre="Aire de la sala", brand="Carrier", category="aire acondicionado"):
    a = _register(c, token, name=nombre, space="Sala")
    row = db.get(EquipmentAsset, uuid.UUID(a["id"]))
    row.brand, row.model, row.category = brand, "X1", category
    db.commit()
    return a


def pedir(c, a, symptom="Gotea agua por dentro y ya no enfría bien."):
    r = c.post("/service-requests", json={"asset_id": a["id"], "symptom": symptom})
    assert r.status_code == 201, r.text
    return r.json()


def test_solicitud_libre_arma_el_alcance(caso, db):
    c, tokens = caso
    a = equipo(c, db, tokens[0])
    r = pedir(c, a)
    assert r["status"] == "borrador" and r["origin"] == "libre" and r["route"] == "tecnico"
    assert "Gotea agua" in r["scope_text"] and r["specialty"] == "aire_acondicionado" and r["safety"] is None
    # "Otro equipo": sin equipo de la lista
    otro = c.post("/service-requests", json={"equipment_label": "Bomba de agua", "symptom": "No sube el agua al tinaco"})
    assert otro.status_code == 201 and otro.json()["equipment_label"] == "Bomba de agua"
    assert c.post("/service-requests", json={"asset_id": a["id"], "symptom": "ya"}).status_code == 422
    assert c.post("/service-requests", json={"symptom": "Algo pasa con mi equipo"}).status_code == 422


def test_el_alcance_se_puede_corregir_antes_de_empezar(caso, db):
    c, tokens = caso
    r = pedir(c, equipo(c, db, tokens[0]))
    s = c.post(f"/service-requests/{r['id']}/scope", json={"scope_text": "Revisar el minisplit que gotea.", "urgency": "hoy"}).json()
    assert s["scope_text"] == "Revisar el minisplit que gotea." and s["urgency"] == "hoy"


def test_alerta_de_seguridad_no_se_puede_saltar(caso, db):
    c, tokens = caso
    con_direccion(c)
    r = pedir(c, equipo(c, db, tokens[0]), "Huele a gas cerca de la estufa y sale una chispa")
    assert r["safety"]["kind"] == "gas" and r["safety"]["acknowledged"] is False and "911" in r["safety"]["advice"]
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 409
    c.post(f"/service-requests/{r['id']}/ack-safety")
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 200


def test_para_empezar_hace_falta_direccion_y_permiso(caso, db):
    c, tokens = caso
    r = pedir(c, equipo(c, db, tokens[0]))
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 422  # sin dirección
    con_direccion(c)
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": False}).status_code == 422  # sin permiso
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 200
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 409  # ya en marcha


def buscar(c, db, tokens, **kw):
    con_direccion(c)
    r = pedir(c, equipo(c, db, tokens[0], **kw))
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 200
    return c.get(f"/service-requests/{r['id']}").json()


def test_busqueda_completa_da_cinco_cotizaciones_anonimas(caso, db):
    c, tokens = caso
    r = buscar(c, db, tokens)
    assert r["status"] == "lista" and r["quote_count"] == 5 and len(r["quotes"]) == 5
    assert [q["label"] for q in r["quotes"]] == [f"Técnico {n}" for n in (1, 2, 4, 5, 6)]
    estados = {c_["label"]: c_["status"] for c_ in r["calls"]}
    assert estados["Técnico 3"] == "sin_respuesta" and estados["Técnico 1"] == "completada"
    tags = {t for q in r["quotes"] for t in q["tags"]}
    assert tags == {"mas_barata", "mas_pronto", "mas_cerca"}
    assert any(q["matches"] == "distinto" for q in r["quotes"])  # una cotizó otra cosa
    assert all(q["scope_quoted"] and q["price_min"] is not None and q["availability"] for q in r["quotes"])
    # lo que ya no se llamó queda cancelado: no se sigue llamando de más
    assert all(c_["status"] != "en_cola" for c_ in r["calls"])


def test_nunca_se_entregan_datos_de_contacto_del_tecnico(caso, db):
    c, tokens = caso
    r = buscar(c, db, tokens)
    q = c.get(f"/service-requests/{r['id']}/quotes/{r['quotes'][0]['id']}").json()
    texto = json.dumps([r, q, c.get("/service-requests").json()], ensure_ascii=False)
    for p in db.scalars(select(ServiceProvider).where(ServiceProvider.city == "Ciudad Servicios")):
        assert p.name not in texto
        assert (p.phone_e164 or "x") not in texto and (p.phone_e164 or "x")[3:] not in texto
        assert (p.address or "x") not in texto
    for prohibido in ("phone", "telefono", "website", "transcript", "recording", "provider_id", "retell"):
        assert prohibido not in texto.lower()
    assert r["appointment"] is None


def test_agendar_pide_permiso_y_revela_el_nombre_solo_al_confirmar(caso, db, monkeypatch):
    c, tokens = caso
    r = buscar(c, db, tokens)
    monkeypatch.setattr(get_settings(), "fake_voice_step_seconds", 3600)  # la visita tarda en confirmarse
    qid = r["quotes"][0]["id"]
    assert c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": qid, "slot_index": 0, "consent": False}).status_code == 422
    assert c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": qid, "slot_index": 9, "consent": True}).status_code == 422
    s = c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": qid, "slot_index": 0, "consent": True}).json()
    ap = s["appointment"]
    assert s["status"] == "agendada" and ap["status"] == "por_confirmar" and ap["technician_name"] is None
    assert ap["agreed"]["label"] == "Técnico 1"
    # pasa el tiempo: el técnico confirma y ahora sí se ve su nombre
    monkeypatch.setattr(F, "utcnow", lambda: datetime.now(timezone.utc) + timedelta(days=1))
    s2 = c.get(f"/service-requests/{r['id']}").json()["appointment"]
    assert s2["status"] == "confirmada" and s2["technician_name"] and s2["starts_at"]
    assert s2["technician_phone"] is None  # sin compartir su teléfono, tampoco se le da el del técnico
    assert "+52" not in json.dumps(s2)


def test_visita_realizada_queda_en_el_historial(caso, db):
    c, tokens = caso
    r = buscar(c, db, tokens)
    c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": r["quotes"][0]["id"], "slot_index": 1, "consent": True})
    ap = c.get(f"/service-requests/{r['id']}").json()["appointment"]
    assert ap["status"] == "confirmada"
    out = c.post(f"/appointments/{ap['id']}/done", json={"final_cost": 580}).json()
    assert out["status"] == "terminada" and out["appointment"]["final_cost"] == 580
    ev = db.scalars(select(AssetEvent).where(AssetEvent.type == "servicio_realizado")).all()
    assert len(ev) == 1 and ev[0].payload["costo_final"] == 580 and ev[0].payload["con"] == "tecnico"


def test_cancelar_cita_vuelve_a_las_cotizaciones(caso, db):
    c, tokens = caso
    r = buscar(c, db, tokens)
    c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": r["quotes"][0]["id"], "slot_index": 0, "consent": True})
    ap = c.get(f"/service-requests/{r['id']}").json()["appointment"]
    out = c.post(f"/appointments/{ap['id']}/cancel").json()
    assert out["status"] == "lista" and out["appointment"] is None


def test_solicitud_desde_una_tarea_de_cuidado(caso, db):
    c, tokens = caso
    a = equipo(c, db, tokens[0])
    t = CareTask(asset_id=uuid.UUID(a["id"]), organization_id=db.get(EquipmentAsset, uuid.UUID(a["id"])).organization_id,
                 title="Mantenimiento preventivo con un técnico", every_n=1, every_unit="anio", next_due=datetime.now().date(),
                 needs_technician=True)
    db.add(t); db.commit()
    r1 = c.post(f"/care/{t.id}/quote-request").json()
    r2 = c.post(f"/care/{t.id}/quote-request").json()
    assert r1["id"] == r2["id"] and r1["origin"] == "tarea" and "Mantenimiento preventivo" in r1["scope_text"]
    assert r1["care_task_id"] == str(t.id)


def test_equipo_pequeno_va_por_el_fabricante(caso, db):
    c, tokens = caso
    con_direccion(c)
    a = equipo(c, db, tokens[0], "Licuadora Oster", "Oster", "Licuadora")
    r = pedir(c, a, "El motor no gira y la jarra gotea.")
    assert r["route"] == "fabricante"
    assert r["manufacturer"]["brand"] == "Oster" and r["manufacturer"]["phone"] is None
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 422  # sin teléfono
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "55 1234 5678"}).status_code == 200
    s = c.get(f"/service-requests/{r['id']}").json()
    assert s["manufacturer"]["phone"] == "+525512345678"
    ap = s["appointment"]
    assert s["status"] == "agendada" and ap["kind"] == "fabricante" and ap["location_type"] == "centro"
    assert ap["folio"].startswith("OS-") and ap["center_address"] and ap["starts_at"] and ap["bring"]
    from app.models import Consent
    assert db.scalar(select(Consent).where(Consent.request_id == uuid.UUID(r["id"]), Consent.type == "compartir_datos_con_fabricante"))


def test_fabricante_que_no_acepta_y_la_persona_registra_su_cita(caso, db):
    c, tokens = caso
    con_direccion(c)
    a = equipo(c, db, tokens[0], "Licuadora", "Marca Sin Linea", "Licuadora")
    r = pedir(c, a, "No enciende por ningún lado")
    c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "5512345678"})
    assert c.get(f"/service-requests/{r['id']}").json()["status"] == "sin_cita"
    out = c.post(f"/service-requests/{r['id']}/register", json={"date": "2026-12-04", "window": "manana", "folio": "ABC123"}).json()
    assert out["status"] == "agendada" and out["appointment"]["registered_by_user"] is True and out["appointment"]["folio"] == "ABC123"


def test_fabricante_requiere_el_equipo_de_la_lista(caso, db):
    c, tokens = caso
    con_direccion(c)
    r = c.post("/service-requests", json={"equipment_label": "Licuadora", "symptom": "No enciende"}).json()
    c.post(f"/service-requests/{r['id']}/scope", json={"route": "fabricante"})
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 422


def test_aislamiento_entre_hogares_y_cancelar(caso, db, make_client):
    c, tokens = caso
    r = pedir(c, equipo(c, db, tokens[0]))
    assert c.post(f"/service-requests/{r['id']}/cancel").json()["status"] == "cancelada"
    assert c.post(f"/service-requests/{r['id']}/cancel").status_code == 409
    otro = make_client(uid()); otro.post("/home", json={"name": "Otra"})  # desde aquí las llamadas son de otro hogar
    assert otro.get(f"/service-requests/{r['id']}").status_code == 404
    assert otro.post(f"/service-requests/{r['id']}/cancel").status_code == 404
    assert otro.get("/service-requests").json() == {"requests": []}


def test_sin_tecnicos_en_la_zona_no_se_queda_buscando(caso, db, monkeypatch):
    c, tokens = caso

    class Vacia:
        def search(self, city, specialty):
            return []
    monkeypatch.setattr(F, "get_source", lambda: Vacia())
    monkeypatch.setattr(F, "candidates", lambda *a, **k: [])  # el directorio es compartido: aquí no hay nadie cerca
    con_direccion(c, "Ciudad Vacia")
    c2 = pedir(c, equipo(c, db, tokens[0]))
    c.post(f"/service-requests/{c2['id']}/start", json={"consent": True})
    s = c.get(f"/service-requests/{c2['id']}").json()
    assert s["status"] == "sin_respuesta" and s["quote_count"] == 0 and s["calls"] == []
