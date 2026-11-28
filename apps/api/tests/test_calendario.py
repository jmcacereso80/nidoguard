import time
from app.routers import calendar as cal

EV = {"title": "Visita: refri, Samsung", "start": "2026-12-01T16:00:00+00:00", "end": "2026-12-01T18:00:00+00:00", "location": "Calle 1, Roma", "details": "Irá: Luis\nAcceso: caseta"}


def test_enlace_firmado_sirve_ics(make_client):
    client = make_client(None)
    t = cal.sign(EV)
    r = client.get(f"/calendar/{t}.ics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    assert "inline" in r.headers["content-disposition"]
    assert "SUMMARY:Visita: refri\\, Samsung" in r.text and "DTSTART:20261201T160000Z" in r.text and "TRIGGER:-PT1H" in r.text
    assert "Irá: Luis\\nAcceso: caseta" in r.text


def test_enlace_alterado_o_caducado_no_sirve(make_client):
    client = make_client(None)
    t = cal.sign(EV)
    assert client.get(f"/calendar/{t[:-2]}xx.ics").status_code == 404
    assert client.get(f"/calendar/{cal.sign(EV, now=time.time() - 3600)}.ics").status_code == 404
    assert client.get("/calendar/basura.ics").status_code == 404


def test_pedir_enlace_requiere_sesion_y_devuelve_ruta(make_client):
    body = {"title": "Visita", "start": "2026-12-01T16:00:00Z", "end": "2026-12-01T18:00:00Z", "location": None, "details": "x"}
    assert make_client(None).post("/calendar/link", json=body).status_code == 401
    r = make_client("cal-user").post("/calendar/link", json=body)
    assert r.status_code == 200 and r.json()["path"].startswith("/calendar/") and r.json()["path"].endswith(".ics")
    assert make_client(None).get(r.json()["path"]).status_code == 200
