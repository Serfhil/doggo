import io

import pytest
from PIL import Image as PILImage

from core import settings
from data.models import Image, Record
from tests.conftest import make_form


def png_bytes(size=(2000, 1000), color="red", fmt="PNG"):
    buffer = io.BytesIO()
    PILImage.new("RGB", size, color).save(buffer, fmt)
    return buffer.getvalue()


@pytest.fixture
def record_id(client, session_factory, category_id):
    client.post("/admin/new", data=make_form(category_id))
    with session_factory() as session:
        return session.query(Record).one().id


def upload(client, record_id, data, name="a.png", content_type="image/png"):
    return client.post(
        f"/admin/api/records/{record_id}/images",
        files={"file": (name, data, content_type)},
    )


def test_upload_resizes_and_makes_thumb(client, record_id):
    response = upload(client, record_id, png_bytes())
    assert response.status_code == 201
    body = response.json()
    assert body["url"].endswith(".webp") and body["thumb_url"].endswith("_thumb.webp")
    main = settings.upload_path / body["url"].split("/")[-1]
    thumb = settings.upload_path / body["thumb_url"].split("/")[-1]
    assert max(PILImage.open(main).size) == 1600
    assert max(PILImage.open(thumb).size) == 480


def test_upload_strips_metadata(client, record_id):
    img = PILImage.new("RGB", (100, 100), "blue")
    exif = img.getexif()
    exif[0x010F] = "SecretCamera"
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", exif=exif)
    body = upload(client, record_id, buffer.getvalue(), "p.jpg", "image/jpeg").json()
    saved = PILImage.open(settings.upload_path / body["url"].split("/")[-1])
    assert 0x010F not in saved.getexif()


def test_rejects_non_image_even_with_image_extension(client, record_id):
    response = upload(client, record_id, b"<script>alert(1)</script>", "evil.png")
    assert response.status_code == 400
    assert not list(settings.upload_path.glob("*")) if settings.upload_path.exists() else True


def test_rejects_gif(client, record_id):
    response = upload(client, record_id, png_bytes(fmt="GIF"), "a.gif", "image/gif")
    assert response.status_code == 400


def test_rejects_too_large(client, record_id, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    assert upload(client, record_id, png_bytes((50, 50))).status_code == 400


def test_image_count_limit(client, record_id, monkeypatch):
    monkeypatch.setattr(settings, "MAX_IMAGES_PER_RECORD", 2)
    for _ in range(2):
        assert upload(client, record_id, png_bytes((50, 50))).status_code == 201
    assert upload(client, record_id, png_bytes((50, 50))).status_code == 400


def test_alt_order_and_delete(client, session_factory, record_id):
    ids = [upload(client, record_id, png_bytes((50, 50))).json()["id"] for _ in range(3)]
    assert client.patch(f"/admin/api/images/{ids[0]}", json={"alt": "  Пёс   сидит "}).json()["alt"] == "Пёс сидит"

    new_order = [ids[2], ids[0], ids[1]]
    response = client.put(f"/admin/api/records/{record_id}/images/order", json={"ids": new_order})
    assert [i["id"] for i in response.json()] == new_order
    assert client.put(f"/admin/api/records/{record_id}/images/order", json={"ids": ids[:2]}).status_code == 409

    assert client.delete(f"/admin/api/images/{ids[2]}").status_code == 204
    with session_factory() as session:
        rest = session.query(Image).order_by(Image.position).all()
        assert [i.id for i in rest] == [ids[0], ids[1]]
        assert [i.position for i in rest] == [0, 1]
    assert client.delete(f"/admin/api/images/{ids[2]}").status_code == 404


def test_deleting_record_removes_files(client, record_id):
    body = upload(client, record_id, png_bytes((50, 50))).json()
    name = body["url"].split("/")[-1]
    assert (settings.upload_path / name).exists()
    client.post(f"/admin/delete/{record_id}")
    assert not (settings.upload_path / name).exists()
    assert not (settings.upload_path / name.replace(".webp", "_thumb.webp")).exists()


def test_cover_shown_on_home_and_record_page(client, record_id):
    body = upload(client, record_id, png_bytes((50, 50))).json()
    assert body["thumb_url"] in client.get("/").text
    assert body["url"] in client.get(f"/record/{record_id}").text
    assert 'id="images-app"' in client.get(f"/admin/edit/{record_id}").text
