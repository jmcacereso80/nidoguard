"""Busqueda automatica de la linea de servicio de cada marca: se muestra a la persona, nunca se llama sin verificar."""
import pytest
from sqlalchemy import select

from app.main import app
from app.models import ManufacturerServiceLine, ServiceProvider
from app.services.line_finder import FakeLineFinder, LineCandidate, get_line_finder, validate
from app.services.manufacturers import brand_key, ensure_line
from tests.test_etapa_c import limpiar  # noqa: F401
from tests.test_llamadas_reales import real  # noqa: F401
from tests.test_servicios import caso  # noqa: F401

OSTER = LineCandidate(phone="+525599990000", hours="L a V de 8 a 20", requires_holder=True, source_url="https://www.oster.com.mx/servicio")


@pytest.fixture()
def finder(db):
    db.query(ManufacturerServiceLine).filter_by(brand_key=brand_key("Oster")).delete()
    db.commit()
    f = FakeLineFinder({brand_key("Oster"): OSTER})
    app.dependency_overrides[get_line_finder] = lambda: f
    yield f
    app.dependency_overrides.pop(get_line_finder, None)
    db.query(ManufacturerServiceLine).filter_by(brand_key=brand_key("Oster")).delete()
    db.commit()


def pide_fabricante(c, db, tokens, n=0):
    from tests.test_servicios import con_direccion, equipo, pedir
    con_direccion(c)
    r = pedir(c, equipo(c, db, tokens[n], "Licuadora Oster", "Oster", "Licuadora"), "El motor no gira y la jarra gotea.")  # una etiqueta distinta por equipo
    out = c.post(f"/service-requests/{r['id']}/scope", json={"route": "fabricante"}).json()  # la busqueda corre en segundo plano
    return out["id"]


def test_la_linea_encontrada_se_muestra_pero_no_se_llama(real, db, finder):
    c, tokens, enviados = real
    rid = pide_fabricante(c, db, tokens)
    l = db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == brand_key("Oster")))
    db.refresh(l)
    assert l.status == "por_verificar" and l.found_by == "ia" and l.phone_e164 == "+525599990000" and l.source.startswith("https://www.oster.com.mx")
    m = c.get(f"/service-requests/{rid}").json()["manufacturer"]
    assert m["line"] is None  # sin verificar no es "linea"
    assert m["candidate"] == {"phone": "+525599990000", "hours": "L a V de 8 a 20", "requires_holder": True, "source_domain": "oster.com.mx"}
    assert c.post(f"/service-requests/{rid}/start", json={"consent": True, "phone": "55 1234 5678"}).status_code == 200
    v = c.get(f"/service-requests/{rid}").json()
    assert enviados == [] and v["status"] == "sin_cita" and v["manufacturer"]["reason"] == "linea_por_verificar"  # no se llama a una linea sin verificar


def test_marca_sin_resultado_no_se_busca_otra_vez_en_dos_semanas(real, db, finder):
    c, tokens, enviados = real
    finder.table.clear()
    rid = pide_fabricante(c, db, tokens)
    l = db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == brand_key("Oster")))
    db.refresh(l)
    assert l.status == "sin_resultado" and l.phone_e164 is None and len(finder.calls) == 1
    pide_fabricante(c, db, tokens, 1)
    assert len(finder.calls) == 1  # ya se busco: no se gasta otra busqueda
    c.post(f"/service-requests/{rid}/start", json={"consent": True, "phone": "55 1234 5678"})
    assert c.get(f"/service-requests/{rid}").json()["manufacturer"]["reason"] == "sin_linea"


def test_si_ya_existe_la_linea_no_se_vuelve_a_buscar(real, db, finder):
    c, tokens, enviados = real
    pide_fabricante(c, db, tokens, 0)
    pide_fabricante(c, db, tokens, 1)
    assert len(finder.calls) == 1


def test_validacion_de_lo_que_encuentra_el_buscador():
    ok = {"found": True, "phone": "01 55 1234 5678", "source_url": "https://marca.mx/servicio", "confidence": "alta", "hours": "8 a 20"}
    assert validate(ok).phone == "+525512345678"
    assert validate({**ok, "confidence": "baja"}) is None  # poca confianza: no se guarda
    assert validate({**ok, "phone": "123"}) is None  # telefono inválido
    assert validate({**ok, "source_url": "javascript:alert(1)"}) is None  # sin fuente real
    assert validate({"found": False}) is None and validate(None) is None


def test_la_persona_confirma_o_descarta_la_linea(real, db, finder):
    c, tokens, enviados = real
    rid = pide_fabricante(c, db, tokens)
    assert c.post(f"/service-requests/{rid}/line-feedback", json={"worked": True}).json()["manufacturer"]["feedback"] is True
    assert c.post(f"/service-requests/{rid}/line-feedback", json={"worked": False}).status_code == 409  # una sola vez por solicitud
    l = db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == brand_key("Oster")))
    db.refresh(l)
    assert l.confirmed_count == 1 and l.wrong_count == 0
    for i in (1, 2):  # dos personas más dicen que no era esa línea
        r2 = pide_fabricante(c, db, tokens, i)
        assert c.post(f"/service-requests/{r2}/line-feedback", json={"worked": False}).status_code == 200
    db.refresh(l)
    assert l.wrong_count == 2 and l.status == "descartada"  # más "no" que "sí": deja de mostrarse
    assert c.get(f"/service-requests/{rid}").json()["manufacturer"]["candidate"] is None


def test_ensure_line_no_toca_lineas_ya_verificadas_ni_revive_descartadas(db, finder):
    db.add(ManufacturerServiceLine(brand_key=brand_key("Oster"), brand="Oster", phone_e164="+525511110000", status="descartada"))
    db.commit()
    l = ensure_line(db, "Oster", finder)
    assert l.status == "descartada" and l.phone_e164 == "+525511110000" and finder.calls == []
