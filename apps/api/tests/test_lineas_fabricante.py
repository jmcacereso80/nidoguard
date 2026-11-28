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


# ---------------------------------------------------------------- Apify y los telefonos de la persona
from app.services.line_finder import ChainLineFinder, official_domain, parse_search_items, phones_in  # noqa: E402

ITEMS = [{"organicResults": [
    {"url": "https://www.mercadolibre.com.mx/oster", "title": "Oster licuadora", "description": "Compra aquí. Tel 55 9999 0001"},
    {"url": "https://www.liverpool.com.mx/oster", "title": "Oster en Liverpool", "description": "Llama al 55 8888 0002"},
    {"url": "https://www.oster.com.mx/soporte", "title": "Servicio técnico Oster México", "description": "Centro de servicio. Atención a clientes: 01 800 123 4567, de lunes a viernes."},
]}]


def test_apify_toma_el_telefono_solo_de_paginas_oficiales_de_la_marca():
    c = parse_search_items(ITEMS, "Oster")
    assert c.phone == "+528001234567" and c.source_url == "https://www.oster.com.mx/soporte"  # ignora tiendas y marketplaces
    assert parse_search_items([{"organicResults": [ITEMS[0]["organicResults"][0], ITEMS[0]["organicResults"][1]]}], "Oster") is None
    assert parse_search_items([], "Oster") is None and parse_search_items([{"organicResults": None}], "Oster") is None
    assert official_domain("https://www.lg.com/mx/soporte", "LG") and not official_domain("https://algo.com/x", "LG")
    assert official_domain("https://mabe.com.mx/servicio", "Mabe") and not official_domain("https://facebook.com/oster", "Oster")


def test_extrae_telefonos_de_mexico_de_un_texto():
    assert [p for p, _ in phones_in("Servicio: (55) 1234-5678 o 800 123 4567")] == ["+525512345678", "+528001234567"]
    assert phones_in("Modelo 2024, precio 12345") == []
    assert phones_in("Llama al 01 800 123 4567")[0] == ("+528001234567", True)  # junto a "llama": confianza alta


def test_la_cadena_usa_el_primero_que_encuentra_y_sigue_si_falla():
    class Roto:
        def find(self, brand): raise RuntimeError("sin red")
    chain = ChainLineFinder([Roto(), FakeLineFinder({brand_key("Oster"): OSTER}), FakeLineFinder({brand_key("Oster"): OSTER})])
    assert chain.find("Oster") == OSTER and ChainLineFinder([Roto()]).find("Oster") is None


def test_la_persona_guarda_el_fabricante_y_la_tienda_en_el_equipo(real, db, finder):
    from datetime import timedelta
    from app.services import requests_flow as F
    from tests.test_servicios import con_direccion, equipo
    c, tokens, enviados = real
    con_direccion(c)
    a = equipo(c, db, tokens[0], "Licuadora Oster", "Oster", "Licuadora")
    hasta = (F.today_mx() + timedelta(days=100)).isoformat()
    assert c.put(f"/assets/{a['id']}/service-contacts", json={"store_phone": "123"}).status_code == 422  # teléfono inválido
    out = c.put(f"/assets/{a['id']}/service-contacts", json={"maker_name": "Oster", "maker_phone": "800 123 4567", "store_name": "Liverpool",
                                                              "store_phone": "55 5262 9999", "store_until": hasta}).json()
    assert out["service_contacts"]["maker"] == {"name": "Oster", "phone": "+528001234567"}
    assert out["service_contacts"]["store"] == {"name": "Liverpool", "phone": "+525552629999", "until": hasta, "active": True}
    assert c.get(f"/assets/{a['id']}").json()["service_contacts"]["store"]["active"] is True
    # con la tienda cubriendo la garantia, agendar con el fabricante no llama al fabricante: se agenda con la tienda
    linea_ok = ManufacturerServiceLine(brand_key=brand_key("Oster"), brand="Oster", phone_e164="+525599990000", status="verificada")
    db.add(linea_ok); db.commit()
    from tests.test_servicios import pedir
    r = pedir(c, a, "El motor no gira.")
    c.post(f"/service-requests/{r['id']}/scope", json={"route": "fabricante"})
    assert c.post(f"/service-requests/{r['id']}/start", json={"consent": True, "phone": "55 1234 5678"}).status_code == 200
    v = c.get(f"/service-requests/{r['id']}").json()
    assert enviados == [] and v["status"] == "sin_cita" and v["manufacturer"]["reason"] == "garantia_tienda"
    assert v["manufacturer"]["contacts"]["store"]["name"] == "Liverpool"
    # borrar todo
    assert c.put(f"/assets/{a['id']}/service-contacts", json={}).json()["service_contacts"] == {"maker": None, "store": None}
