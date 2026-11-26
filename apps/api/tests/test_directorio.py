from sqlalchemy import select, func
from app.models import ProviderSearch, ServiceProvider
from app.services import providers as P


class Counting:
    def __init__(self, inner=None):
        self.calls, self.inner = 0, inner or P.FakeSource()

    def search(self, city, specialty):
        self.calls += 1
        return self.inner.search(city, specialty)


def test_phone_normalization():
    assert P.to_e164_mx("55 5501 0001") == "+525555010001"
    assert P.to_e164_mx("+52 1 55 5501 0001") == "+525555010001"
    assert P.to_e164_mx("(55) 5501-0001") == "+525555010001"
    assert P.to_e164_mx("5501") is None and P.to_e164_mx(None) is None


def test_search_runs_once_per_city_and_specialty(db):
    src = Counting()
    a = P.ensure_directory(db, "Ciudad de México Prueba1", "aire_acondicionado", src)
    b = P.ensure_directory(db, "ciudad de mexico prueba1", "aire_acondicionado", src)  # misma clave normalizada
    assert src.calls == 1 and a.new_providers == 12 and b.id == a.id
    P.ensure_directory(db, "Ciudad de México Prueba1", "aire_acondicionado", src, force=True)
    assert src.calls == 2


def test_no_duplicates_across_specialties_and_phone(db):
    src = Counting()
    P.ensure_directory(db, "Ciudad Prueba2", "refrigeracion", src)
    again = P.ensure_directory(db, "Ciudad Prueba2", "lavadoras", src)
    assert again.new_providers == 0  # mismos telefonos y mismos ids del mapa
    n = db.scalar(select(func.count()).select_from(ServiceProvider).where(ServiceProvider.city == "Ciudad Prueba2"))
    assert n == 12
    p = db.scalar(select(ServiceProvider).where(ServiceProvider.city == "Ciudad Prueba2"))
    assert set(p.specialties) == {"refrigeracion", "lavadoras"}


def test_failed_search_is_recorded_and_retried(db):
    class Boom:
        def search(self, city, specialty):
            raise RuntimeError("apify caído")
    r = P.ensure_directory(db, "Ciudad Prueba3", "boiler", Boom())
    assert r.status == "error" and "apify" in r.detail
    ok = P.ensure_directory(db, "Ciudad Prueba3", "boiler", Counting())
    assert ok.status == "lista" and ok.new_providers == 12


def test_candidates_ordered_filtered_and_respect_do_not_call(db):
    P.ensure_directory(db, "Ciudad Prueba4", "aire_acondicionado", Counting())
    near = P.candidates(db, "aire_acondicionado", 19.3869, -99.1693, radius_km=15)
    assert 0 < len(near) <= 30 and all(d <= 15 for _, d in near)
    first = near[0][0]
    first.do_not_call = True
    db.commit()
    assert first.id not in [p.id for p, _ in P.candidates(db, "aire_acondicionado", 19.3869, -99.1693, 15)]
    assert P.candidates(db, "aire_acondicionado", 25.67, -100.31, 15) == []  # lejos (Monterrey)


def test_parse_maps_items_skips_closed_and_no_id():
    items = [{"placeId": "A", "title": "Frío Uno", "phone": "55 1234 5678", "location": {"lat": 19.4, "lng": -99.1}},
             {"placeId": "B", "title": "Cerrado", "permanentlyClosed": True},
             {"title": "Sin id"}]
    recs = P.parse_maps_items(items, "CDMX")
    assert [r.source_id for r in recs] == ["maps:A"] and recs[0].lat == 19.4
