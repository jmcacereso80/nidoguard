import uuid
from app.main import app
from app.models import Property
from app.services.geocoder import FakeGeocoder, get_geocoder


def uid():
    return "u_" + uuid.uuid4().hex[:8]


def _home(c):
    c.post("/home", json={"name": "Casa"})
    return c.get("/me").json()["home"]["properties"][0]["id"]


def test_address_saved_with_coordinates(make_client, db):
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder()
    c = make_client(uid())
    pid = _home(c)
    assert c.get("/me").json()["home"]["properties"][0]["address"]["complete"] is False
    r = c.put(f"/properties/{pid}/address", json={"street": "Gabriel Mancera 123", "colony": "Del Valle Centro",
                                                  "postal_code": "03100", "city": "Ciudad de México", "state": "CDMX"})
    assert r.status_code == 200 and r.json()["complete"] is True
    p = db.get(Property, pid)
    assert p.lat and p.lng and p.geocoded_at and p.search_radius_km == 15
    assert c.get("/me").json()["home"]["properties"][0]["address"]["city"] == "Ciudad de México"


def test_address_not_found_does_not_save(make_client, db):
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder()
    c = make_client(uid())
    pid = _home(c)
    r = c.put(f"/properties/{pid}/address", json={"street": "Calle Sin Mapa 1", "city": "Ciudad de México"})
    assert r.status_code == 422 and "ubicar" in r.json()["detail"]
    assert db.get(Property, pid).lat is None


def test_address_validates_postal_code(make_client):
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder()
    c = make_client(uid())
    pid = _home(c)
    assert c.put(f"/properties/{pid}/address", json={"street": "Calle 1", "city": "CDMX", "postal_code": "31"}).status_code == 422


def test_address_is_isolated_between_homes(make_client):
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder()
    a = make_client(uid()); pid = _home(a)
    b = make_client(uid()); b.post("/home", json={"name": "B"})
    r = b.put(f"/properties/{pid}/address", json={"street": "Calle 1", "city": "CDMX"})
    assert r.status_code == 404


def test_search_radius_is_saved_and_validated(make_client, db):
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder()
    c = make_client(uid()); pid = _home(c)
    ok = c.put(f"/properties/{pid}/address", json={"street": "Calle 1 número 2", "city": "CDMX", "search_radius_km": 25})
    assert ok.status_code == 200 and ok.json()["search_radius_km"] == 25 and db.get(Property, pid).search_radius_km == 25
    assert c.put(f"/properties/{pid}/address", json={"street": "Calle 1 número 2", "city": "CDMX", "search_radius_km": 7}).status_code == 422
