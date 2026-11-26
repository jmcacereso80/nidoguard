import uuid
from datetime import date

import pytest

from app.main import app
from sqlalchemy import delete

from app.models import AssetStatus, CareTemplate, EquipmentAsset, Warranty
from app.services.care_planner import CareItem, CarePlan, add_every, first_due, get_planner
from app.services.storage import get_storage
from tests.test_crud_equipo import _register
from tests.test_documentos import FakeStorage
from tests.test_fase3_4 import setup, uid

HOY = date(2026, 11, 26)


def por_titulo(tareas, titulo):
    return next(t for t in tareas if t["title"] == titulo)


class FakePlanner:
    name = "falso"

    def __init__(self, fail=False):
        self.calls, self.fail = 0, fail

    def plan(self, category, name, brand, model):
        self.calls += 1
        if self.fail:
            raise RuntimeError("sin conexión")
        return CarePlan(tasks=[
            CareItem(title="Dejar la puerta entreabierta", detail="Evita humedad", instructions="1. Deja la puerta abierta",
                     every_n=1, every_unit="dia", priority="baja"),
            CareItem(title="Limpiar el cajón del detergente", detail="Evita moho", instructions="1. Sácalo\n2. Lávalo",
                     every_n=1, every_unit="mes", priority="media"),
            CareItem(title="Limpiar el filtro de la bomba", detail="Evita fallas", instructions="1. Apaga y desconecta",
                     every_n=3, every_unit="mes", priority="alta"),
            CareItem(title="Correr un ciclo de limpieza", detail="Limpia el tambor", instructions="1. Elige el ciclo",
                     every_n=1, every_unit="anio", priority="media"),
            CareItem(title="limpiar el filtro de la bomba", detail="repetida", instructions="x", every_n=3, every_unit="mes", priority="alta"),
        ])


@pytest.fixture()
def caso(make_client, db, monkeypatch):
    monkeypatch.setattr("app.routers.care.today_mx", lambda: HOY)
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    db.execute(delete(CareTemplate)); db.commit()  # los planes aprendidos son compartidos: cada prueba empieza sin ninguno
    planner = FakePlanner()
    app.dependency_overrides[get_planner] = lambda: planner
    c, tokens = setup(make_client, db, tags=4)
    a = _register(c, tokens[0])
    return c, a, planner, tokens


def test_fechas_de_calendario():
    assert add_every(date(2026, 1, 31), 1, "mes") == date(2026, 2, 28)
    assert add_every(date(2026, 11, 26), 3, "mes") == date(2027, 2, 26)
    assert add_every(date(2028, 2, 29), 1, "anio") == date(2029, 2, 28)
    assert add_every(date(2026, 11, 26), 2, "semana") == date(2026, 12, 10)
    assert add_every(date(2026, 11, 26), 1, "dia") == date(2026, 11, 27)
    # la primera fecha nunca pasa de 30 dias
    assert first_due(HOY, 1, "dia") == date(2026, 11, 27)
    assert first_due(HOY, 1, "anio") == date(2026, 12, 26)


def test_generar_crea_cuidados_sugeridos_sin_repetir(caso):
    c, a, planner, _ = caso
    assert c.get(f"/assets/{a['id']}/care").json() == {"model_confirmed": False, "tasks": []}
    r = c.post(f"/assets/{a['id']}/care/generate")
    assert r.status_code == 200, r.text
    tareas = r.json()["tasks"]
    assert len(tareas) == 4  # la repetida no se guarda
    assert all(t["source"] == "sugerencia" and not t["confirmed"] for t in tareas)
    diario = por_titulo(tareas, "Dejar la puerta entreabierta")
    assert diario["every"] == {"n": 1, "unit": "dia"} and diario["next_due"] == "2026-11-27"
    assert por_titulo(tareas, "Correr un ciclo de limpieza")["next_due"] == "2026-12-26"  # anual: primera revision en 30 dias
    fechas = [t["next_due"] for t in tareas]
    assert fechas == sorted(fechas)
    # segunda llamada: no vuelve a generar
    assert len(c.post(f"/assets/{a['id']}/care/generate").json()["tasks"]) == 4
    assert planner.calls == 1


def test_modelo_confirmado_solo_con_equipo_completo(caso, db):
    c, a, _, _ = caso
    asset = db.get(EquipmentAsset, uuid.UUID(a["id"]))
    asset.model = "WA17"
    db.commit()
    assert c.get(f"/assets/{a['id']}/care").json()["model_confirmed"] is False  # hay modelo, pero no esta confirmado
    asset.status = AssetStatus.completo
    db.commit()
    assert c.get(f"/assets/{a['id']}/care").json()["model_confirmed"] is True


def test_si_la_ia_falla_no_se_guarda_nada(caso):
    c, a, _, _ = caso
    app.dependency_overrides[get_planner] = lambda: FakePlanner(fail=True)
    r = c.post(f"/assets/{a['id']}/care/generate")
    assert r.status_code == 503 and "Inténtalo de nuevo" in r.json()["detail"]
    assert c.get(f"/assets/{a['id']}/care").json()["tasks"] == []
    app.dependency_overrides[get_planner] = lambda: FakePlanner()
    assert c.post(f"/assets/{a['id']}/care/generate").status_code == 200  # reintento funciona


def test_marcar_realizado_calcula_siguiente_fecha_y_registra_historial(caso):
    c, a, _, _ = caso
    t = por_titulo(c.post(f"/assets/{a['id']}/care/generate").json()["tasks"], "Limpiar el filtro de la bomba")  # cada 3 meses
    r = c.post(f"/care/{t['id']}/done")
    assert r.status_code == 200, r.text
    assert r.json()["next_due"] == "2027-02-26" and r.json()["confirmed"] is True and r.json()["done_at"]
    eventos = [e["type"] for e in c.get(f"/assets/{a['id']}").json()["events"]]
    assert "cuidado_hecho" in eventos and "cuidados_sugeridos" in eventos
    # se puede indicar que se hizo antes; nunca en el futuro
    r2 = c.post(f"/care/{t['id']}/done", json={"done_on": "2026-11-01"})
    assert r2.status_code == 200 and r2.json()["next_due"] == "2027-02-01"
    assert c.post(f"/care/{t['id']}/done", json={"done_on": "2026-12-01"}).status_code == 422
    assert c.post(f"/care/{t['id']}/done", json={"done_on": "2024-01-01"}).status_code == 422


def test_un_cuidado_diario_hecho_hoy_vuelve_manana(caso):
    c, a, _, _ = caso
    t = por_titulo(c.post(f"/assets/{a['id']}/care/generate").json()["tasks"], "Dejar la puerta entreabierta")
    assert c.post(f"/care/{t['id']}/done").json()["next_due"] == "2026-11-27"


def test_reprogramar(caso):
    c, a, _, _ = caso
    t = por_titulo(c.post(f"/assets/{a['id']}/care/generate").json()["tasks"], "Limpiar el cajón del detergente")
    assert c.post(f"/care/{t['id']}/reschedule", json={"next_due": "2026-12-15"}).json()["next_due"] == "2026-12-15"
    assert c.post(f"/care/{t['id']}/reschedule", json={"next_due": "2026-11-25"}).status_code == 422
    assert c.post(f"/care/{t['id']}/reschedule", json={"next_due": "2040-01-01"}).status_code == 422


def test_me_sirve_y_no_aplica(caso):
    c, a, planner, _ = caso
    ts = c.post(f"/assets/{a['id']}/care/generate").json()["tasks"]
    sirve, no_aplica = por_titulo(ts, "Dejar la puerta entreabierta"), por_titulo(ts, "Limpiar el cajón del detergente")
    assert c.post(f"/care/{sirve['id']}/confirm").json()["confirmed"] is True
    assert c.post(f"/care/{no_aplica['id']}/dismiss").status_code == 200
    despues = c.get(f"/assets/{a['id']}/care").json()["tasks"]
    assert len(despues) == 3 and no_aplica["id"] not in [t["id"] for t in despues]
    assert por_titulo(despues, "Dejar la puerta entreabierta")["confirmed"] is True
    # lo descartado no vuelve a aparecer ni se regenera
    assert len(c.post(f"/assets/{a['id']}/care/generate").json()["tasks"]) == 3 and planner.calls == 1
    assert c.post(f"/care/{no_aplica['id']}/done").status_code == 404


def test_cuidados_de_todo_el_hogar(caso):
    c, a, _, tokens = caso
    c.post(f"/assets/{a['id']}/care/generate")
    b = _register(c, tokens[1], name="Refrigerador", space="Cocina")
    c.post(f"/assets/{b['id']}/care/generate")
    r = c.get("/care").json()
    assert r["today"] == "2026-11-26" and len(r["tasks"]) == 8
    assert {t["asset_name"] for t in r["tasks"]} == {"Lavadora", "Refrigerador"}
    assert r["tasks"][0]["space_name"] == "Cocina"
    fechas = [t["next_due"] for t in r["tasks"]]
    assert fechas == sorted(fechas)


def test_no_se_ven_cuidados_de_otro_hogar(caso, make_client, db):
    c, a, _, _ = caso
    t = c.post(f"/assets/{a['id']}/care/generate").json()["tasks"][0]
    otro = make_client(uid()); otro.post("/home", json={"name": "Otra casa"})
    assert otro.get(f"/assets/{a['id']}/care").status_code == 404
    assert otro.post(f"/assets/{a['id']}/care/generate").status_code == 404
    for ruta in ("done", "confirm", "dismiss"):
        assert otro.post(f"/care/{t['id']}/{ruta}").status_code == 404
    assert otro.post(f"/care/{t['id']}/reschedule", json={"next_due": "2026-12-01"}).status_code == 404
    assert otro.get("/care").json()["tasks"] == []


def test_garantias_del_hogar_y_historial(caso, db):
    c, a, _, tokens = caso
    from tests.test_documentos import JPEG, _subir
    fs = FakeStorage(); app.dependency_overrides[get_storage] = lambda: fs
    b = _register(c, tokens[1], name="Refrigerador", space="Cocina")
    for asset, fecha in ((a, "2027-03-01"), (b, "2026-12-23")):
        doc_id, _ = _subir(c, db, fs, asset["id"], "garantia", "g.jpg", "image/jpeg", JPEG)
        assert c.post(f"/assets/{asset['id']}/warranty", json={"document_id": doc_id, "ends_on": fecha}).status_code == 200
    g = c.get("/care/warranties").json()
    assert g["today"] == "2026-11-26"
    assert [(w["asset_name"], w["ends_on"]) for w in g["warranties"]] == [("Refrigerador", "2026-12-23"), ("Lavadora", "2027-03-01")]
    assert g["warranties"][0]["space_name"] == "Cocina"
    # historial: lo mas reciente primero
    ts = c.post(f"/assets/{a['id']}/care/generate").json()["tasks"]
    c.post(f"/care/{ts[0]['id']}/done", json={"done_on": "2026-11-20"})
    c.post(f"/care/{ts[1]['id']}/done")
    h = c.get("/care/history").json()["records"]
    assert [r["done_on"] for r in h] == ["2026-11-26", "2026-11-20"] and h[0]["asset_name"] == "Lavadora"
    assert c.get("/care/history?limit=1").json()["records"][0]["done_on"] == "2026-11-26"


def test_garantias_e_historial_son_privados(caso, make_client):
    c, a, _, _ = caso
    t = c.post(f"/assets/{a['id']}/care/generate").json()["tasks"][0]
    c.post(f"/care/{t['id']}/done")
    otro = make_client(uid()); otro.post("/home", json={"name": "Otra casa"})
    assert otro.get("/care/history").json()["records"] == []
    assert otro.get("/care/warranties").json()["warranties"] == []


def test_confirmar_equipo_prepara_cuidados_en_segundo_plano(caso, monkeypatch):
    c, a, _, tokens = caso
    lanzadas = []
    monkeypatch.setattr("app.services.care.prepare_in_background", lambda aid: lanzadas.append(str(aid)))
    r = c.post(f"/assets/{a['id']}/confirm", json={"brand": "LG", "model": "WA17"})
    assert r.status_code == 200, r.text
    assert lanzadas == [a["id"]]


def test_segundo_plano_solo_con_equipo_confirmado_y_sin_error(caso, db, monkeypatch):
    from app.services import care as svc
    c, a, planner, _ = caso
    monkeypatch.undo()  # quita el stub automatico
    monkeypatch.setattr("app.services.care.SessionLocal", lambda: db)
    monkeypatch.setattr("app.services.care.get_planner", lambda: planner)
    monkeypatch.setattr("app.services.care.today_mx", lambda: HOY)
    db.close = lambda: None
    aid = uuid.UUID(a["id"])
    svc.prepare_in_background(aid)  # registrado, no confirmado: no hace nada
    assert planner.calls == 0
    asset = db.get(EquipmentAsset, aid); asset.status = AssetStatus.completo; db.commit()
    svc.prepare_in_background(aid)
    assert planner.calls == 1 and len(c.get(f"/assets/{a['id']}/care").json()["tasks"]) == 4
    svc.prepare_in_background(aid)  # ya tiene: no repite
    assert planner.calls == 1
    # si la IA falla, no revienta ni guarda nada
    asset2 = _register(c, caso[3][2], name="Estufa", space="Cocina")
    a2 = db.get(EquipmentAsset, uuid.UUID(asset2["id"])); a2.status = AssetStatus.completo; db.commit()
    monkeypatch.setattr("app.services.care.get_planner", lambda: FakePlanner(fail=True))
    svc.prepare_in_background(a2.id)
    assert c.get(f"/assets/{asset2['id']}/care").json()["tasks"] == []


def _equipo(c, db, token, nombre, brand=None, model=None, category=None):
    a = _register(c, token, name=nombre, space="Cocina")
    row = db.get(EquipmentAsset, uuid.UUID(a["id"]))
    row.brand, row.model, row.category = brand, model, category
    db.commit()
    return a


def test_el_plan_se_aprende_una_vez_por_modelo_y_se_reutiliza(caso, db):
    from app.models import CareTemplate, CareTask
    from sqlalchemy import select
    c, a, planner, tokens = caso
    a1 = _equipo(c, db, tokens[1], "Lavadora de la cocina", "LG", "WA-17 X", "lavadora")
    a2 = _equipo(c, db, tokens[2], "Lavadora de mamá", "lg", "wa17x", "Lavadora")  # mismo modelo escrito distinto
    t1 = c.post(f"/assets/{a1['id']}/care/generate").json()["tasks"]
    t2 = c.post(f"/assets/{a2['id']}/care/generate").json()["tasks"]
    assert planner.calls == 1  # la IA solo se llamo para el primero
    assert sorted(t["title"] for t in t1) == sorted(t["title"] for t in t2) and len(t1) == 4
    plantilla = db.scalars(select(CareTemplate).where(CareTemplate.kind == "modelo")).all()
    assert len(plantilla) == 1 and plantilla[0].uses == 2 and plantilla[0].verified is False
    assert plantilla[0].key == "modelo|lg|wa17x" and plantilla[0].brand == "LG"
    # cada equipo tiene sus propias tareas: marcar una en uno no mueve la del otro
    c.post(f"/care/{t1[0]['id']}/done")
    otra = [t for t in c.get(f"/assets/{a2['id']}/care").json()["tasks"] if t["title"] == t1[0]["title"]][0]
    assert otra["done_at"] is None
    assert db.scalar(select(CareTask).where(CareTask.id == uuid.UUID(otra["id"]))).last_done_at is None


def test_otro_modelo_aprende_su_propio_plan(caso, db):
    c, a, planner, tokens = caso
    a1 = _equipo(c, db, tokens[1], "Lavadora", "LG", "WA17", "lavadora")
    a2 = _equipo(c, db, tokens[2], "Otra lavadora", "LG", "WA20", "lavadora")
    c.post(f"/assets/{a1['id']}/care/generate"); c.post(f"/assets/{a2['id']}/care/generate")
    assert planner.calls == 2


def test_sin_modelo_se_comparte_por_tipo_y_sin_tipo_no_se_comparte(caso, db):
    c, a, planner, tokens = caso
    r1 = _equipo(c, db, tokens[1], "Refri de la casa", category="refrigerador")
    r2 = _equipo(c, db, tokens[2], "Refri de la oficina", category="Refrigerador")
    c.post(f"/assets/{r1['id']}/care/generate"); c.post(f"/assets/{r2['id']}/care/generate")
    assert planner.calls == 1  # mismo tipo: un solo plan
    # sin marca, modelo ni tipo: el nombre de la persona no se comparte; se genera para ese equipo
    c.post(f"/assets/{a['id']}/care/generate")
    assert planner.calls == 2


def test_el_nombre_de_la_persona_no_llega_al_plan_compartido(caso, db):
    c, a, _, tokens = caso
    vistos = []
    class Espia(FakePlanner):
        def plan(self, category, name, brand, model):
            vistos.append(name); return super().plan(category, name, brand, model)
    app.dependency_overrides[get_planner] = lambda: Espia()
    x = _equipo(c, db, tokens[1], "La lavadora de Juan en Polanco", "LG", "WA17", "lavadora")
    c.post(f"/assets/{x['id']}/care/generate")
    assert vistos == ["lavadora"]


def test_si_la_ia_falla_no_queda_plantilla(caso, db):
    from app.models import CareTemplate
    from sqlalchemy import select
    c, a, _, tokens = caso
    x = _equipo(c, db, tokens[1], "Lavadora", "LG", "WA17", "lavadora")
    app.dependency_overrides[get_planner] = lambda: FakePlanner(fail=True)
    assert c.post(f"/assets/{x['id']}/care/generate").status_code == 503
    assert db.scalars(select(CareTemplate)).all() == []
    app.dependency_overrides[get_planner] = lambda: FakePlanner()
    assert c.post(f"/assets/{x['id']}/care/generate").status_code == 200
