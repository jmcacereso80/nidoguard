import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.main import app
from app.models import (AssetDocument, EquipmentAsset, ManufacturerServiceLine, ServiceAppointment, ServiceCall, ServiceProvider, ServiceQuote,
                        ServiceRequest, Warranty)
from app.services import call_policy, call_results
from app.services import requests_flow as F
from app.services.manufacturers import brand_key, mark_verified
from app.services.quote_extractor import AppointmentDraft, ManufacturerDraft, SlotDraft, get_extractor
from app.services.retell import RetellCaller
from tests.test_llamadas_reales import Extractor, analizada, cid, estados, evento, real  # noqa: F401
from tests.test_servicios import buscar, caso, con_direccion, equipo, pedir  # noqa: F401

MX = ZoneInfo("America/Mexico_City")


def mx(y, m, d, h=10, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=MX).astimezone(timezone.utc)


DOMINGO, LUNES = mx(2026, 11, 29, 11), mx(2026, 11, 30, 10)


class Ext(Extractor):
    def __init__(self, appt=None, manu=None, **over):
        super().__init__(**over)
        self.appt, self.manu = appt, manu

    def appointment(self, transcript, today, slot):
        return self.appt

    def manufacturer(self, transcript, today):
        return self.manu


@pytest.fixture(autouse=True)
def limpiar(db):
    yield
    db.rollback()
    db.query(ManufacturerServiceLine).delete()
    db.query(ServiceProvider).filter(ServiceProvider.source == "prueba").update({"status": "descartado", "do_not_call": True})
    db.commit()


def usar(ext):
    app.dependency_overrides[get_extractor] = lambda: ext


def dia(n):
    return (F.today_mx() + timedelta(days=n)).isoformat()


# ------------------------------------------------------------------ piezas puras
def test_horario_de_llamadas(monkeypatch):
    monkeypatch.setattr(get_settings(), "calls_window_enabled", True)
    assert call_policy.in_window(mx(2026, 11, 28, 10))  # sabado
    assert not call_policy.in_window(DOMINGO)
    assert not call_policy.in_window(mx(2026, 11, 30, 8, 59)) and call_policy.in_window(mx(2026, 11, 30, 9))
    assert not call_policy.in_window(mx(2026, 11, 30, 19))
    assert call_policy.next_open(DOMINGO) == mx(2026, 11, 30, 9)
    assert call_policy.next_open(mx(2026, 11, 30, 20)) == mx(2026, 12, 1, 9)
    assert call_policy.next_open(mx(2026, 11, 28, 20)) == mx(2026, 11, 30, 9)  # sabado en la noche: lunes
    assert call_policy.next_open(LUNES) == LUNES


# ------------------------------------------------------------------ pieza 6: oleadas, horario, reintentos, topes
def test_fuera_de_horario_espera_y_sigue_al_abrir(real, db, monkeypatch):
    c, tokens, enviados = real
    monkeypatch.setattr(get_settings(), "calls_window_enabled", True)
    monkeypatch.setattr(F, "utcnow", lambda: DOMINGO)
    r = buscar(c, db, tokens)
    assert enviados == [] and r["status"] == "buscando"
    assert datetime.fromisoformat(r["resumes_at"]) == mx(2026, 11, 30, 9)
    monkeypatch.setattr(F, "utcnow", lambda: LUNES)
    assert call_results.tick(db, RetellCaller())["busquedas"] >= 1
    assert len(enviados) == 3
    assert c.get(f"/service-requests/{r['id']}").json()["resumes_at"] is None


def test_segundo_intento_solo_uno(real, db, monkeypatch):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    assert evento(c, "call_ended", {"call_id": cid(2), "disconnection_reason": "dial_no_answer"}).json()["result"] == "sin_respuesta"
    db.query(ServiceCall).filter(ServiceCall.request_id == uuid.UUID(r["id"]), ServiceCall.status == "en_cola").update({"status": "cancelada"})
    db.commit()
    n = len(enviados)
    call_results.tick(db, RetellCaller())
    assert len(enviados) == n  # todavía no toca el reintento
    monkeypatch.setattr(F, "utcnow", lambda: datetime.now(timezone.utc) + timedelta(hours=3))
    call_results.tick(db, RetellCaller())
    db.expire_all()
    mismo = db.scalar(select(ServiceCall).where(ServiceCall.retell_call_id == cid(2)))
    intentos = sorted(x.attempt for x in db.scalars(select(ServiceCall).where(ServiceCall.request_id == uuid.UUID(r["id"]), ServiceCall.label == mismo.label)))
    assert intentos == [1, 2]
    nuevo = db.scalar(select(ServiceCall).where(ServiceCall.request_id == uuid.UUID(r["id"]), ServiceCall.label == mismo.label, ServiceCall.attempt == 2))
    assert nuevo.status == "llamando"
    evento(c, "call_ended", {"call_id": nuevo.retell_call_id, "disconnection_reason": "dial_no_answer"})
    call_results.tick(db, RetellCaller())
    db.expire_all()
    assert db.scalar(select(ServiceCall.id).where(ServiceCall.request_id == uuid.UUID(r["id"]), ServiceCall.label == mismo.label, ServiceCall.attempt == 3)) is None
    vista = c.get(f"/service-requests/{r['id']}").json()
    assert [x["label"] for x in vista["calls"]].count(mismo.label) == 1  # el usuario ve una sola fila por técnico


def test_tope_de_costo_detiene_las_llamadas(real, db, monkeypatch):
    c, tokens, enviados = real
    monkeypatch.setattr(get_settings(), "max_cost_per_request_usd", 0.5)
    r = buscar(c, db, tokens)
    assert len(enviados) == 3
    analizada(c, 1)  # cuesta 0.85 dólares: pasa el tope
    assert len(enviados) == 3
    assert "en_cola" not in estados(db, r["id"])


def test_la_busqueda_vence_con_lo_que_haya(real, db, monkeypatch):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    analizada(c, 1)
    monkeypatch.setattr(F, "utcnow", lambda: datetime.now(timezone.utc) + timedelta(hours=25))
    call_results.tick(db, RetellCaller())
    v = c.get(f"/service-requests/{r['id']}").json()
    assert v["status"] == "lista" and v["quote_count"] == 1
    assert "en_cola" not in estados(db, r["id"]) and "llamando" not in estados(db, r["id"])


def test_tecnico_de_prueba_con_tu_numero(real, db, monkeypatch):
    c, tokens, enviados = real
    con_direccion(c)
    monkeypatch.setattr(sys, "argv", ["x", "prueba", "--telefono", "55 7777 0001"])
    from admin import proveedores
    proveedores.main()
    monkeypatch.setattr(get_settings(), "calls_allowlist", "+525577770001")
    r = pedir(c, equipo(c, db, tokens[0]))
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True}).status_code == 200
    assert [b["to_number"] for b in enviados] == ["+525577770001"]  # a nadie más se le llama
    assert evento(c, "call_analyzed", {"call_id": cid(1), "transcript": "Técnico: la revisión cuesta setecientos pesos y puedo ir mañana por la tarde.", "duration_ms": 30000}).json()["result"] == "completada"
    v = c.get(f"/service-requests/{r['id']}").json()
    assert v["quote_count"] == 1 and v["status"] == "lista"  # los demás quedaron omitidos: se cierra con la que hay
    assert "5577770001" not in json.dumps(v)


# ------------------------------------------------------------------ pieza 7: agendar, reprogramar, recordatorio
def agendada(c, db, tokens, enviados, ext, quote_n=1):
    """Una cotización por webhook, la persona agenda y el técnico contesta con `ext`."""
    r = buscar(c, db, tokens)
    analizada(c, quote_n)
    r = c.get(f"/service-requests/{r['id']}").json()
    c.put("/me/phone", json={"phone": "55 1234 5678"})
    s = c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": r["quotes"][0]["id"], "slot_index": 0, "consent": True, "share_phone": True, "access_notes": "Caseta: registrar INE"})
    assert s.status_code == 200, s.text
    usar(ext)
    return r["id"], s.json()


def test_la_direccion_solo_sale_en_la_llamada_de_agendar(real, db):
    c, tokens, enviados = real
    rid, s = agendada(c, db, tokens, enviados, Ext(appt=AppointmentDraft(outcome="confirma")))
    antes, agenda = enviados[:-1], enviados[-1]
    assert "Gabriel Mancera" not in json.dumps(antes)
    cot = antes[0]["retell_llm_dynamic_variables"]
    assert cot["marca"] == "Carrier" and cot["modelo"] == "X1" and "serie" not in cot  # el tecnico recibe marca y modelo; nunca la serie
    v = agenda["retell_llm_dynamic_variables"]
    assert v["tipo"] == "agendar" and "Gabriel Mancera" in v["direccion"] and v["telefono_cliente"] == "+525512345678" and v["franja_elegida"] and v["acceso"] == "Caseta: registrar INE"
    assert s["appointment"]["status"] == "por_confirmar" and s["appointment"]["technician_name"] is None
    assert s["appointment"]["technician_phone"] is None  # el telefono del tecnico solo se ve con la visita confirmada


def test_confirmacion_fuera_de_horario_espera_se_marca_al_abrir_y_se_puede_cancelar(real, db, monkeypatch):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    analizada(c, 1)
    r = c.get(f"/service-requests/{r['id']}").json()
    c.put("/me/phone", json={"phone": "55 1234 5678"})
    n = len(enviados)
    monkeypatch.setattr(call_policy, "in_window", lambda now: False)  # son las 9 de la noche
    s = c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": r["quotes"][0]["id"], "slot_index": 0, "consent": True}).json()
    assert len(enviados) == n and s["resumes_at"]  # no se marca fuera de horario y la app dice cuándo sigue
    ap = db.scalar(select(ServiceAppointment).where(ServiceAppointment.id == uuid.UUID(s["appointment"]["id"])))
    tel = db.get(ServiceProvider, ap.provider_id).phone_e164
    monkeypatch.setattr(call_policy, "in_window", lambda now: True)  # abre el horario
    c.get(f"/service-requests/{r['id']}")
    assert len(enviados) == n + 1 and enviados[-1]["retell_llm_dynamic_variables"]["tipo"] == "agendar"
    assert enviados[-1]["to_number"] == tel  # se llama al teléfono del técnico (en la prueba, el de la persona)


def test_cancelar_la_visita_cancela_la_llamada_de_confirmacion_en_cola(real, db, monkeypatch):
    c, tokens, enviados = real
    r = buscar(c, db, tokens)
    analizada(c, 1)
    r = c.get(f"/service-requests/{r['id']}").json()
    monkeypatch.setattr(call_policy, "in_window", lambda now: False)
    s = c.post(f"/service-requests/{r['id']}/schedule", json={"quote_id": r["quotes"][0]["id"], "slot_index": 0, "consent": True}).json()
    n = len(enviados)
    assert c.post(f"/appointments/{s['appointment']['id']}/cancel").status_code == 200
    monkeypatch.setattr(call_policy, "in_window", lambda now: True)
    out = c.get(f"/service-requests/{r['id']}").json()
    assert len(enviados) == n and out["status"] == "lista"  # ya no sale la llamada y puede elegir otra cotización
    assert c.post(f"/service-requests/{r['id']}/cancel").status_code == 200  # y también puede cancelar todo, con cotizaciones listas


def test_confirma_revela_nombre_y_marca_recordatorio_el_dia_anterior(real, db):
    c, tokens, enviados = real
    d = dia(3)
    rid, s = agendada(c, db, tokens, enviados, Ext(appt=AppointmentDraft(outcome="confirma", date=d, start_hour=10, end_hour=12, person_name="Luis Pérez")))
    assert analizada(c, len(enviados)).json()["result"] == "completada"
    ap = c.get(f"/service-requests/{rid}").json()["appointment"]
    assert ap["status"] == "confirmada" and ap["technician_name"] == "Luis" and ap["starts_at"].startswith(d) and ap["technician_phone"] and ap["access_notes"]  # quien irá, solo el nombre de pila
    row = db.scalar(select(ServiceAppointment).where(ServiceAppointment.id == uuid.UUID(ap["id"])))
    inicio = row.starts_at
    n = len(enviados)
    assert call_results.send_reminders(db, RetellCaller(), inicio - timedelta(hours=30)) == 0  # todavía no es el día anterior
    assert call_results.send_reminders(db, RetellCaller(), inicio - timedelta(hours=20)) == 1
    db.commit()
    assert len(enviados) == n + 1 and enviados[-1]["retell_llm_dynamic_variables"]["tipo"] == "recordatorio"
    assert "direccion" not in enviados[-1]["retell_llm_dynamic_variables"]
    assert call_results.send_reminders(db, RetellCaller(), inicio - timedelta(hours=19)) == 0  # una sola vez


def test_tecnico_propone_otra_hora_y_la_persona_acepta(real, db):
    c, tokens, enviados = real
    d = dia(4)
    rid, s = agendada(c, db, tokens, enviados, Ext(appt=AppointmentDraft(outcome="propone_otra", date=d, start_hour=16, end_hour=18)))
    analizada(c, len(enviados))
    ap = c.get(f"/service-requests/{rid}").json()["appointment"]
    assert ap["status"] == "por_reprogramar" and ap["proposed_slot"]["date"] == d and ap["proposal_round"] == 1
    r = c.post(f"/appointments/{ap['id']}/respond", json={"accept": True}).json()["appointment"]
    assert r["status"] == "confirmada" and r["starts_at"].startswith(d) and r["proposed_slot"] is None
    assert c.post(f"/appointments/{ap['id']}/respond", json={"accept": True}).status_code == 409


def test_la_persona_elige_otra_franja_maximo_dos_rondas(real, db):
    c, tokens, enviados = real
    usar(Ext(availability=[SlotDraft(date=dia(1), window="tarde"), SlotDraft(date=dia(2), window="manana"), SlotDraft(date=dia(3), window="tarde")]))
    rid, s = agendada(c, db, tokens, enviados, Ext(appt=AppointmentDraft(outcome="propone_otra", date=dia(4), start_hour=16)))
    analizada(c, len(enviados))
    ap = c.get(f"/service-requests/{rid}").json()["appointment"]
    n = len(enviados)
    r = c.post(f"/appointments/{ap['id']}/respond", json={"accept": False, "slot_index": 1}).json()["appointment"]
    assert r["status"] == "por_confirmar" and len(enviados) == n + 1  # se vuelve a llamar con la franja nueva
    analizada(c, len(enviados))  # propone otra por segunda vez
    ap = c.get(f"/service-requests/{rid}").json()["appointment"]
    assert ap["status"] == "por_reprogramar" and ap["proposal_round"] == 2
    analizada(c, len(enviados))  # ya cerrada: no hace nada
    n = len(enviados)
    c.post(f"/appointments/{ap['id']}/respond", json={"accept": False, "slot_index": 2})  # ya no hay más rondas: se deja la visita
    v = c.get(f"/service-requests/{rid}").json()
    assert v["appointment"] is None and len(enviados) == n


def test_rechazo_ofrece_la_siguiente_cotizacion(real, db):
    c, tokens, enviados = real
    rid, s = agendada(c, db, tokens, enviados, Ext(appt=AppointmentDraft(outcome="rechaza")))
    analizada(c, 2)  # una segunda cotización llega mientras tanto
    analizada(c, len(enviados))
    v = c.get(f"/service-requests/{rid}").json()
    assert v["appointment"] is None and v["status"] == "lista" and v["quote_count"] == 1  # la que rechazó ya no se ofrece
    assert all(q["id"] != s["appointment"]["agreed"] and q["label"] != "Técnico 1" for q in v["quotes"])


def test_no_contesta_al_agendar_reintenta_y_luego_ofrece_otra(real, db):
    c, tokens, enviados = real
    rid, s = agendada(c, db, tokens, enviados, Ext(appt=AppointmentDraft(outcome="confirma")))
    n = len(enviados)
    evento(c, "call_ended", {"call_id": cid(n), "disconnection_reason": "dial_no_answer"})
    call_results.tick(db, RetellCaller())
    assert len(enviados) == n + 1  # segundo intento
    evento(c, "call_ended", {"call_id": cid(n + 1), "disconnection_reason": "dial_no_answer"})
    v = c.get(f"/service-requests/{rid}").json()
    assert v["appointment"] is None and v["status"] in ("lista", "sin_respuesta")


# ------------------------------------------------------------------ pieza 9: fabricante con línea verificada
def oster(c, db, tokens):
    con_direccion(c)
    a = equipo(c, db, tokens[0], "Licuadora Oster", "Oster", "Licuadora")
    return pedir(c, a, "El motor no gira y la jarra gotea.")


def linea(db, estado):
    db.query(ManufacturerServiceLine).filter_by(brand_key=brand_key("Oster")).delete()
    l = ManufacturerServiceLine(brand_key=brand_key("Oster"), brand="Oster", phone_e164="+525599990000", hours="L a V de 8 a 20", status="por_verificar")
    if estado == "verificada":
        mark_verified(l)
    db.add(l)
    db.commit()


def test_linea_sin_verificar_nunca_se_llama(real, db):
    c, tokens, enviados = real
    linea(db, "por_verificar")
    r = oster(c, db, tokens)
    assert r["manufacturer"]["line"] is None
    c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "55 1234 5678"})
    assert enviados == [] and c.get(f"/service-requests/{r['id']}").json()["status"] == "sin_cita"


def test_fabricante_con_linea_verificada_agenda_por_webhook(real, db):
    c, tokens, enviados = real
    linea(db, "verificada")
    r = oster(c, db, tokens)
    assert r["manufacturer"]["line"]["phone"] == "+525599990000" and r["manufacturer"]["line"]["hours"]
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "55 1234 5678"}).status_code == 200
    assert [b["to_number"] for b in enviados] == ["+525599990000"]
    v = enviados[0]["retell_llm_dynamic_variables"]
    assert v["marca"] == "Oster" and v["telefono_titular"] == "+525512345678"
    usar(Ext(manu=ManufacturerDraft(scheduled=True, date=dia(5), start_hour=10, end_hour=13, center_name="Centro de Servicio Oster Polanco",
                                    center_address="Av. Ejemplo 456", folio="OS-88421", bring=["El equipo", "Tu factura"])))
    assert analizada(c, 1).json()["result"] == "completada"
    s = c.get(f"/service-requests/{r['id']}").json()
    assert s["status"] == "agendada" and s["appointment"]["folio"] == "OS-88421" and s["appointment"]["kind"] == "fabricante"


def test_fabricante_que_rechaza_cae_en_agendala_tu(real, db):
    c, tokens, enviados = real
    linea(db, "verificada")
    r = oster(c, db, tokens)
    c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "55 1234 5678"})
    usar(Ext(manu=ManufacturerDraft(scheduled=False, reason_if_not="Piden hablar con el titular")))
    analizada(c, 1)
    s = c.get(f"/service-requests/{r['id']}").json()
    assert s["status"] == "sin_cita" and s["manufacturer"]["line"]["phone"]  # la persona recibe la línea para llamar


def test_garantia_vigente_y_linea_verificada_manda_al_fabricante(caso, db):
    c, tokens = caso
    con_direccion(c)
    a = equipo(c, db, tokens[0], "Aire de la sala", "Oster", "aire acondicionado")
    row = db.get(EquipmentAsset, uuid.UUID(a["id"]))
    doc = AssetDocument(asset_id=row.id, organization_id=row.organization_id, kind="garantia", filename="g.pdf", storage_key=f"k/{uuid.uuid4()}",
                        content_type="application/pdf", size=10)
    db.add(doc)
    db.flush()
    db.add(Warranty(asset_id=row.id, organization_id=row.organization_id, document_id=doc.id, ends_on=F.today_mx() + timedelta(days=100)))
    db.commit()
    linea(db, "por_verificar")
    assert pedir(c, a)["route"] == "tecnico"  # sin línea verificada sigue por técnicos
    linea(db, "verificada")
    assert pedir(c, a)["route"] == "fabricante"


def test_extractor_reintenta_en_modo_automatico_si_el_modelo_no_acepta_forzar(monkeypatch):
    """Sonnet 5.5 rechaza tool_choice forzado: el extractor debe reintentar en auto, no fallar la llamada."""
    from types import SimpleNamespace
    from app.services import quote_extractor as qe
    llamadas = []
    class Cliente:
        class messages:
            @staticmethod
            def create(**kw):
                llamadas.append(kw["tool_choice"]["type"])
                if kw["tool_choice"]["type"] == "tool":
                    raise RuntimeError('tool_choice: type "tool" and "any" are not supported for this model.')
                return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input={"outcome": "cotizo", "price": 500})])
    ext = qe.ClaudeExtractor.__new__(qe.ClaudeExtractor)
    ext.client, ext.model = Cliente(), "modelo-prueba"
    from pydantic import BaseModel
    class Esquema(BaseModel):
        outcome: str
        price: int
    out = ext._run("p", Esquema, "registrar", "texto")
    assert out.price == 500 and llamadas == ["tool", "auto"]
