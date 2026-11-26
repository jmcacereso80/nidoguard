import uuid

from app.main import app
from app.models import ModelKnowledge, ModelResearchRun
from app.services import manuales
from app.services.storage import get_knowledge_storage, get_storage
from tests.test_crud_equipo import FakeStorage, _register
from tests.test_fase3_4 import setup

PDF = b"%PDF-1.4\n" + b"0" * 300


class KStorage:
    def __init__(self): self.objects = {}
    def put_bytes(self, key, data, content_type): self.objects[key] = data
    def presign_get(self, key, expires=600): return f"https://fake-k/{key}"


def test_orden_prefiere_pdf_de_la_marca_y_descarta_tiendas():
    c = [("https://www.amazon.com.mx/x/manual.pdf", "Manual"),
         ("https://www.mabe.com.mx/files/manual-lavadora.pdf", "Manual de uso Mabe"),
         ("https://foro.ejemplo.com/hilo", "Pregunta"),
         ("https://www.mabe.com.mx/producto", "Producto con manual en el titulo")]
    assert [u for u, _ in manuales.ordenar_candidatos(c, "Mabe")] == ["https://www.mabe.com.mx/files/manual-lavadora.pdf"]


def test_guarda_copia_del_primer_pdf_real_y_registra_la_corrida(db):
    key = manuales.model_key("Mabe", "LMA7120")
    db.add(ModelKnowledge(model_key=key, brand="Mabe", model="LMA7120", status="buscando", attempts=0))
    db.commit()
    kst = KStorage()
    def candidatos(b, m): return [("https://www.mabe.com.mx/lma7120/manual-a.pdf", "Manual Mabe"), ("https://www.mabe.com.mx/lma7120/manual-b.pdf", "Otro")]
    def descargar(url): return None if url.endswith("manual-a.pdf") else PDF  # el primero no responde un PDF
    estado = manuales.buscar_y_guardar(db, key, "Mabe", "LMA7120", candidatos, descargar, kst)
    row = db.query(ModelKnowledge).filter_by(model_key=key).one()
    assert estado == "listo" and row.status == "listo" and row.source_url.endswith("manual-b.pdf")
    assert row.storage_key in kst.objects and kst.objects[row.storage_key] == PDF
    assert db.query(ModelResearchRun).filter_by(model_key=key, status="listo").count() == 1


def test_sin_manual_queda_no_encontrado_y_se_reintenta_despues(db):
    key = manuales.model_key("Xyz", "1")
    db.add(ModelKnowledge(model_key=key, brand="Xyz", model="1", status="buscando", attempts=0)); db.commit()
    estado = manuales.buscar_y_guardar(db, key, "Xyz", "1", lambda b, m: [], lambda u: None, KStorage())
    row = db.query(ModelKnowledge).filter_by(model_key=key).one()
    assert estado == "no_encontrado" and row.status == "no_encontrado" and row.next_try_at is not None
    # mientras no llega la fecha de reintento no se vuelve a buscar
    assert manuales.ensure_search(db, "Xyz", "1") is None


def test_no_duplica_busquedas_ni_busca_si_ya_existe(db):
    k = manuales.ensure_search(db, "Lg", "VM122C9")
    assert k is not None                                  # primera vez: lanza la busqueda
    assert manuales.ensure_search(db, "Lg", "VM122C9") is None  # ya esta buscando
    row = db.query(ModelKnowledge).filter_by(model_key=k).one()
    row.status = "listo"; db.commit()
    assert manuales.ensure_search(db, "Lg", "VM122C9") is None  # ya existe el manual


def test_confirmar_equipo_con_marca_y_modelo_dispara_busqueda_una_vez(make_client, db, monkeypatch):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    app.dependency_overrides[get_knowledge_storage] = lambda: KStorage()
    lanzadas = []
    monkeypatch.setattr(manuales, "run_search", lambda k, b, m: lanzadas.append(k))
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    c.patch(f"/assets/{a['id']}", json={"brand": "Hisense", "model": "HS-PRUEBA-1"})
    assert lanzadas == []                                  # aun no confirmado: no se busca
    c.post(f"/assets/{a['id']}/confirm", json={})
    assert lanzadas == [manuales.model_key("Hisense", "HS-PRUEBA-1")]
    c.post(f"/assets/{a['id']}/confirm", json={})
    assert len(lanzadas) == 1                              # no se repite mientras se busca


def test_documentos_muestra_manual_listo_con_enlace_a_la_copia(make_client, db, monkeypatch):
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    app.dependency_overrides[get_knowledge_storage] = lambda: KStorage()
    monkeypatch.setattr(manuales, "run_search", lambda *a: None)
    c, tokens = setup(make_client, db)
    a = _register(c, tokens[0])
    c.patch(f"/assets/{a['id']}", json={"brand": "Mabe", "model": "DOC-PRUEBA-9"})
    c.post(f"/assets/{a['id']}/confirm", json={})
    d = c.get(f"/assets/{a['id']}/documents").json()
    assert d["model_confirmed"] is True and d["manuals"][0]["status"] == "buscando" and d["manuals"][0]["url"] is None
    row = db.query(ModelKnowledge).filter_by(model_key=manuales.model_key("Mabe", "DOC-PRUEBA-9")).one()
    row.status, row.storage_key, row.source_url, row.title = "listo", "manuales/x/y.pdf", "https://www.mabe.com.mx/m.pdf", "Manual Mabe"
    db.commit()
    m = c.get(f"/assets/{a['id']}/documents").json()["manuals"][0]
    assert m["status"] == "listo" and m["url"] == "https://fake-k/manuales/x/y.pdf" and "mabe.com.mx" in m["note"]
