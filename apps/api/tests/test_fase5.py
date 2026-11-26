import io
import uuid
from PIL import Image
from admin.gen_batch import generate
from app.models import AssetImage, AssetStatus, EquipmentAsset, ReadingStatus
from app.services.plate_reader import Field_, PlateExtraction, prepare_image
from app.services.readings import process_reading


def jpeg(w=3000, h=2000):
    b = io.BytesIO(); Image.new("RGB", (w, h), "white").save(b, format="JPEG"); return b.getvalue()


class Store:
    def get_bytes(self, key): return jpeg(400, 300)


class Fake:
    def __init__(self, name, extraction): self.name, self.e, self.calls = name, extraction, 0
    def read(self, image, ct, extra=None): self.calls += 1; return self.e


def ext(legible=True, brand=("Mabe", .95), model=("LMA123", .9)):
    return PlateExtraction(legible=legible, suggested_name="Lavadora", transcript="MABE LMA123",
                           brand=Field_(value=brand[0], confidence=brand[1]),
                           model=Field_(value=model[0], confidence=model[1]))


def make_asset(db):
    from app.models import Organization
    _, k, t = generate(db, "L5", kits=1, tags_per_kit=1)
    org = Organization(name="o"); db.add(org); db.flush()
    from app.models import SmartTag
    tag = db.query(SmartTag).filter_by(token=t[0][1]).one()
    a = EquipmentAsset(organization_id=org.id, tag_id=tag.id, name="Lavadora"); db.add(a); db.flush()
    img = AssetImage(asset_id=a.id, organization_id=org.id, kind="placa", storage_key="k/" + uuid.uuid4().hex,
                     content_type="image/jpeg", uploaded=True); db.add(img); db.commit()
    return a, img


def test_ready_reading_goes_to_por_confirmar(db):
    a, img = make_asset(db)
    fast = Fake("haiku", ext())
    r = process_reading(db, Store(), a.id, img.id, fast, Fake("sonnet", ext()))
    assert r.status == ReadingStatus.lista and r.model_used == "haiku"
    assert db.get(EquipmentAsset, a.id).status == AssetStatus.por_confirmar
    assert r.fields["brand"] == "Mabe" and r.fields["suggested_name"] == "Lavadora"


def test_low_confidence_retries_with_stronger_model(db):
    a, img = make_asset(db)
    slow = Fake("sonnet", ext())
    r = process_reading(db, Store(), a.id, img.id, Fake("haiku", ext(model=("LMA1?3", .3))), slow)
    assert slow.calls == 1 and r.model_used == "sonnet" and r.status == ReadingStatus.lista


def test_unreadable_photo_asks_for_another_photo_without_retry(db):
    a, img = make_asset(db)
    slow = Fake("sonnet", ext())
    r = process_reading(db, Store(), a.id, img.id, Fake("haiku", ext(legible=False)), slow)
    assert slow.calls == 0 and r.status == ReadingStatus.necesita_foto
    assert db.get(EquipmentAsset, a.id).status == AssetStatus.necesita_foto


def test_missing_model_marks_faltan_datos(db):
    a, img = make_asset(db)
    r = process_reading(db, Store(), a.id, img.id, Fake("haiku", ext(model=(None, 0))), None)
    assert r.status == ReadingStatus.faltan_datos


def test_provider_error_does_not_break(db):
    a, img = make_asset(db)
    class Boom:
        name = "x"
        def read(self, *a): raise RuntimeError("sin red")
    r = process_reading(db, Store(), a.id, img.id, Boom(), None)
    assert r.status == ReadingStatus.error and db.get(EquipmentAsset, a.id).status == AssetStatus.necesita_foto


def test_prepare_image_strips_exif_and_resizes():
    im = Image.new("RGB", (4000, 3000), "white")
    exif = im.getexif(); exif[0x010F] = "SecretCamera"
    b = io.BytesIO(); im.save(b, format="JPEG", exif=exif)
    data, mt = prepare_image(b.getvalue())
    out = Image.open(io.BytesIO(data))
    assert mt == "image/jpeg" and max(out.size) <= 1800 and 0x010F not in out.getexif()
