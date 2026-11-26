import json
import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.main import app
from app.models import ServiceCall, ServiceQuote, ServiceRequest
from app.services import call_results
from app.services.quote_extractor import ManufacturerDraft, QuoteDraft, SlotDraft, get_extractor, scrub
from app.services.retell import RetellCaller, sign, verify_signature
from tests.test_servicios import buscar, caso, con_direccion, equipo, pedir  # noqa: F401

KEY = "clave-de-prueba"
TAG = {"v": ""}


def cid(n):
    return f"call_{TAG['v']}_{n}"


class Extractor:
    def __init__(self, **over):
        self.over = over

    def quote(self, transcript, scope, today):
        base = dict(outcome="cotiza", scope_quoted="Revisión y limpieza.", price_type="fijo", price_min=700, price_max=700, visit_fee=0,
                    availability=[SlotDraft(date=(today + timedelta(days=1)).isoformat(), window="tarde")],
                    summary="Cobra $700. Marca al 55 1234 5678.", matches="igual", payment_methods=["efectivo"])
        return QuoteDraft(**{**base, **self.over})

    def manufacturer(self, transcript, today):
        return ManufacturerDraft(scheduled=False, reason_if_not="No acepta asistentes")


@pytest.fixture()
def real(caso, monkeypatch):
    c, tokens = caso
    s = get_settings()
    for k, v in dict(voice="retell", calls_enabled=True, calls_allowlist="", retell_api_key=KEY, retell_agent_id="agent_x",
                     retell_from_number="+5255000000", calls_wave=3).items():
        monkeypatch.setattr(s, k, v)
    TAG["v"] = uuid.uuid4().hex[:8]
    enviados = []

    def post(self, path, body):
        enviados.append(body)
        return {"call_id": cid(len(enviados))}
    monkeypatch.setattr(RetellCaller, "_post", post)
    app.dependency_overrides[get_extractor] = lambda: Extractor()
    yield c, tokens, enviados
    app.dependency_overrides.pop(get_extractor, None)


def evento(c, event, call, key=KEY):
    raw = json.dumps({"event": event, "call": call}).encode()
    return c.post("/webhooks/retell", content=raw, headers={"x-retell-signature": sign(raw, key, int(time.time() * 1000)),
                                                           "content-type": "application/json"})


def analizada(c, n, transcript="Técnico: sí, la revisión cuesta setecientos pesos y puedo ir mañana por la tarde."):
    return evento(c, "call_analyzed", {"call_id": cid(n), "transcript": transcript, "duration_ms": 61000, "call_cost": {"combined_cost": 85}})


def test_firma_de_retell():
    raw, ts = b'{"event":"call_ended"}', 1_700_000_000_000
    h = sign(raw, KEY, ts)
    assert verify_signature(raw, h, KEY, now_ms=ts + 1000)
    assert not verify_signature(raw + b" ", h, KEY, now_ms=ts + 1000)  # cuerpo cambiado
    assert not verify_signature(raw, h, "otra", now_ms=ts + 1000)
    assert not verify_signature(raw, h, KEY, now_ms=ts + 10 * 60_000)  # vencida
    assert not verify_signature(raw, None, KEY) and not verify_signature(raw, "basura", KEY)


def test_limpia_telefonos_y_correos():
    assert "5512345678" not in (scrub("Llámale al 55 1234 5678 o a x@y.com") or "")
    assert scrub("Cobra $700 por la revisión") == "Cobra $700 por la revisión"


def estados(db, rid):
    db.expire_all()
    return [c.status for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == uuid.UUID(rid)).order_by(ServiceCall.created_at, ServiceCall.label))]


def test_con_llamadas_apagadas_no_sale_nada(real, db, monkeypatch):
    c, tokens, enviados = real
    monkeypatch.setattr(get_settings(), "calls_enabled", False)
    r = buscar(c, db, tokens)
    assert enviados == [] and r["status"] == "sin_respuesta"
    assert set(estados(db, r["id"])) == {"omitida"}


def test_la_lista_permitida_bloquea_numeros_ajenos(real, db, monkeypatch):
    c, tokens, enviados = real
    monkeypatch.setattr(get_settings(), "calls_allowlist", "+520000000000")
    r = buscar(c, db, tokens)
    assert enviados == [] and r["status"] == "sin_respuesta"


def test_se_marca_en_oleadas_y_sin_datos_de_la_casa(real, db):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    assert r["status"] == "buscando" and len(enviados) == 3
    e = estados(db, r["id"])
    assert e.count("llamando") == 3 and e.count("en_cola") == len(e) - 3
    texto = json.dumps(enviados, ensure_ascii=False)
    assert "Gabriel Mancera" not in texto and "03100" not in texto  # solo la zona
    v = enviados[0]["retell_llm_dynamic_variables"]
    assert v["zona"] and all(isinstance(x, str) for x in v.values()) and enviados[0]["metadata"]["call_id"]


def test_webhook_rechaza_firma_mala(real, db):
    c, tokens, enviados = real
    assert evento(c, "call_analyzed", {"call_id": "call_1"}, key="otra").status_code == 401
    assert c.post("/webhooks/retell", json={"event": "x"}).status_code == 401


def test_cotizacion_por_webhook_es_idempotente_y_marca_la_siguiente(real, db):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    assert analizada(c, 1).json()["result"] == "completada"
    assert analizada(c, 1).json()["result"] == "repetida"
    db.expire_all()
    qs = list(db.scalars(select(ServiceQuote).where(ServiceQuote.request_id == uuid.UUID(r["id"]))))
    assert len(qs) == 1 and qs[0].price_min == 700 and qs[0].price_type == "fijo" and qs[0].availability
    assert "5512345678" not in (qs[0].summary or "")
    assert len(enviados) == 4  # entro la siguiente llamada
    llamada = db.scalar(select(ServiceCall).where(ServiceCall.retell_call_id == cid(1)))
    assert llamada.duration_s == 61 and llamada.cost_usd == 0.85 and "setecientos" in llamada.transcript
    vista = c.get(f"/service-requests/{r['id']}").json()
    assert vista["quote_count"] == 1 and "Teléfono" not in json.dumps(vista)


def test_no_contesta_pasa_a_otro_tecnico(real, db):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    assert evento(c, "call_ended", {"call_id": cid(2), "disconnection_reason": "dial_no_answer"}).json()["result"] == "sin_respuesta"
    assert len(enviados) == 4 and estados(db, r["id"]).count("sin_respuesta") == 1


def test_cinco_cotizaciones_cierran_la_busqueda(real, db):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    n = 1
    while n <= len(enviados) and db.get(ServiceRequest, uuid.UUID(r["id"])).status == "buscando":
        analizada(c, n)
        db.expire_all()
        n += 1
    v = c.get(f"/service-requests/{r['id']}").json()
    assert v["status"] == "lista" and v["quote_count"] == 5
    assert "llamando" not in estados(db, r["id"]) and "en_cola" not in estados(db, r["id"])


def test_sin_precio_no_crea_cotizacion_y_rechazo_se_anota(real, db):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    app.dependency_overrides[get_extractor] = lambda: Extractor(outcome="sin_precio", price_min=None, price_max=None)
    analizada(c, 1)
    app.dependency_overrides[get_extractor] = lambda: Extractor(outcome="rechaza")
    analizada(c, 2)
    db.expire_all()
    assert db.scalar(select(ServiceQuote.id).where(ServiceQuote.request_id == uuid.UUID(r["id"]))) is None
    assert estados(db, r["id"])[:2] == ["completada", "rechazo"]


def test_transcripcion_vacia_o_extractor_roto_no_tumban_la_busqueda(real, db):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    assert analizada(c, 1, transcript="hola").json()["result"] == "sin_respuesta"

    class Roto(Extractor):
        def quote(self, *a):
            raise RuntimeError("sin red")
    app.dependency_overrides[get_extractor] = lambda: Roto()
    assert analizada(c, 2).json()["result"] == "error"


def test_evento_de_llamada_desconocida_se_ignora(real, db):
    c, tokens, enviados = real
    assert analizada(c, 999).json()["result"] == "desconocida"


def test_fabricante_sin_linea_conocida_pasa_a_manual(real, db):
    c, tokens, enviados = real
    con_direccion(c)
    a = equipo(c, db, tokens[0], "Licuadora Oster", "Oster", "Licuadora")
    r = pedir(c, a, "El motor no gira y la jarra gotea.")
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "55 1234 5678"}).status_code == 200
    v = c.get(f"/service-requests/{r['id']}").json()
    assert v["status"] == "sin_cita" and enviados == []  # todavia no hay linea del fabricante: la persona agenda por su cuenta
