from app.main import app
from app.models import ModelKnowledge, ModelResearchRun
from app.services import manuales
from app.services.storage import get_storage
from tests.test_crud_equipo import FakeStorage, _register
from tests.test_fase3_4 import setup


def test_parse_apify_saca_los_enlaces_organicos():
    items = [{"organicResults": [{"url": "https://www.mabe.com.mx/m", "title": "Manual Mabe"}, {"url": "", "title": "x"}]},
             {"organicResults": [{"url": "https://otro.mx/a", "title": "A"}]}]
    assert manuales.parse_apify_items(items) == [("https://www.mabe.com.mx/m", "Manual Mabe"), ("https://otro.mx/a", "A")]


def test_elige_hasta_tres_paginas_del_modelo_y_descarta_tiendas():
    c = [("https://www.mercadolibre.com.mx/rms400ivmrm0", "Refrigerador RMS400IVMRM0"),
         ("https://www.notice-facile.com/en/manual/3026442/mabe+rms400i", "Mabe RMS400I manual"),
         ("https://mabeglobal.com/soporte/rms400ivmrm0-manual", "Manual RMS400IVMRM0"),
         ("https://foro.mx/hilo", "Pregunta sobre otro modelo"),
         ("https://www.manualslib.com/mabe/rms400ivmrm0.html", "Mabe RMS400IVMRM0 manual"),
         ("https://ejemplo.mx/rms400ivmrm0-ficha", "ficha")]
    out = manuales.elegir_paginas(c, "Mabe", "RMS400IVMRMO")
    assert len(out) == 3
    assert all("mercadolibre" not in u for u, _ in out)
    assert "https://www.notice-facile.com/en/manual/3026442/mabe+rms400i" in [u for u, _ in out]


def test_sin_pagina_del_modelo_no_sugiere_nada():
    c = [("https://foro.mx/hilo", "Pregunta sobre refrigeradores"), ("https://otra.mx/lavadora", "Lavadora LMA7120 manual")]
    assert manuales.elegir_paginas(c, "Mabe", "RMS400IVMRMO") == []


def test_registra_los_enlaces_y_los_muestra_con_nota(db):
    key = manuales.model_key("Mabe", "NOTA-PRUEBA-1")
    db.add(ModelKnowledge(model_key=key, brand="Mabe", model="NOTA-PRUEBA-1", status="buscando", attempts=0)); db.commit()
    c = [("https://a.mx/nota-prueba-1-manual", "Manual A"), ("https://b.mx/nota-prueba-1-manual", "Manual B")]
    estado = manuales.buscar_y_registrar(db, key, "Mabe", "NOTA-PRUEBA-1", lambda b, m: c)
    row = db.query(ModelKnowledge).filter_by(model_key=key).one()
    assert estado == "listo" and row.status == "listo" and len(row.links) == 2
    assert db.query(ModelResearchRun).filter_by(model_key=key, status="listo").count() == 1


def test_sin_coincidencia_queda_no_encontrado_y_reintenta_despues(db):
    key = manuales.model_key("Xyz", "SIN-PAG-9")
    db.add(ModelKnowledge(model_key=key, brand="Xyz", model="SIN-PAG-9", status="buscando", attempts=0)); db.commit()
    estado = manuales.buscar_y_registrar(db, key, "Xyz", "SIN-PAG-9", lambda b, m: [])
    row = db.query(ModelKnowledge).filter_by(model_key=key).one()
    assert estado == "no_encontrado" and row.next_try_at is not None
    assert manuales.ensure_search(db, "Xyz", "SIN-PAG-9") is None  # no se vuelve a buscar antes de tiempo


def test_no_duplica_busquedas_ni_busca_si_ya_existe(db):
    k = manuales.ensure_search(db, "Lg", "DUP-PRUEBA-3")
    assert k is not None
    assert manuales.ensure_search(db, "Lg", "DUP-PRUEBA-3") is None  # ya esta buscando
    row = db.query(ModelKnowledge).filter_by(model_key=k).one()
    row.status = "listo"; db.commit()
    assert manuales.ensure_search(db, "Lg", "DUP-PRUEBA-3") is None  # ya existe


def test_confirmar_equipo_con_marca_y_modelo_dispara_busqueda_una_vez(make_client, db, monkeypatch):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    lanzadas = []
    monkeypatch.setattr(manuales, "run_search", lambda k, b, m: lanzadas.append(k))
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    c.patch(f"/assets/{a['id']}", json={"brand": "Hisense", "model": "HS-PRUEBA-1"})
    assert lanzadas == []                                   # aun no confirmado
    c.post(f"/assets/{a['id']}/confirm", json={})
    assert lanzadas == [manuales.model_key("Hisense", "HS-PRUEBA-1")]
    c.post(f"/assets/{a['id']}/confirm", json={})
    assert len(lanzadas) == 1


def test_documentos_muestra_los_enlaces_con_la_nota(make_client, db, monkeypatch):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    c.patch(f"/assets/{a['id']}", json={"brand": "Mabe", "model": "DOC-PRUEBA-9"})
    c.post(f"/assets/{a['id']}/confirm", json={})
    d = c.get(f"/assets/{a['id']}/documents").json()
    assert d["model_confirmed"] is True and d["manuals"][0]["status"] == "buscando" and d["manuals"][0]["url"] is None
    row = db.query(ModelKnowledge).filter_by(model_key=manuales.model_key("Mabe", "DOC-PRUEBA-9")).one()
    row.status = "listo"
    row.links = [{"url": "https://www.notice-facile.com/x", "title": "Manual Mabe"}, {"url": "https://b.mx/y", "title": "B"}]
    db.commit()
    m = c.get(f"/assets/{a['id']}/documents").json()["manuals"]
    assert [x["url"] for x in m] == ["https://www.notice-facile.com/x", "https://b.mx/y"]
    assert all(x["note"] == manuales.NOTA and x["status"] == "listo" for x in m)
