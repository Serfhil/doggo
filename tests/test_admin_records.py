import pytest

from data.models import Record, Tag
from tests.conftest import make_form


def test_admin_pages_open(client):
    for url in ("/admin", "/admin/new", "/admin/taxonomy"):
        assert client.get(url).status_code == 200


def test_create_record_redirects_to_edit(client, session_factory, category_id):
    response = client.post(
        "/admin/new",
        data={**make_form(category_id), "tags": ["1"], "new_tags": "Послушание, лёгкий"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/edit/")
    with session_factory() as session:
        record = session.query(Record).one()
        assert record.title == "Сидеть"
        assert record.is_published is True
        # «лёгкий» совпал с предустановленным «Лёгкий» без учёта регистра и ё/е
        assert {t.name for t in record.tags} == {"Лёгкий", "Послушание"}
        assert "лежать" not in record.search_text and "сидеть" in record.search_text


def test_validation_errors_shown_in_form(client, session_factory, category_id):
    response = client.post(
        "/admin/new", data=make_form(category_id, title="  ", text="<p><br></p>")
    )
    assert response.status_code == 422
    assert "Введите название" in response.text
    assert "Для публикации нужен основной текст" in response.text
    with session_factory() as session:
        assert session.query(Record).count() == 0


def test_draft_needs_only_title_and_category(client, session_factory, category_id):
    form = make_form(category_id, text="")
    del form["is_published"]
    response = client.post("/admin/new", data=form, follow_redirects=False)
    assert response.status_code == 303
    with session_factory() as session:
        assert session.query(Record).one().is_published is False


def test_category_required(client):
    response = client.post("/admin/new", data=make_form("", title="X"))
    assert response.status_code == 422
    assert "Выберите категорию" in response.text


def test_edit_and_delete(client, session_factory, category_id):
    client.post("/admin/new", data=make_form(category_id))
    with session_factory() as session:
        record_id = session.query(Record).one().id
    page = client.get(f"/admin/edit/{record_id}")
    assert "Сидеть" in page.text

    response = client.post(
        f"/admin/edit/{record_id}",
        data=make_form(category_id, title="Лежать"),
        follow_redirects=False,
    )
    assert response.status_code == 303
    with session_factory() as session:
        assert session.get(Record, record_id).title == "Лежать"

    assert client.post(f"/admin/delete/{record_id}", follow_redirects=False).status_code == 303
    with session_factory() as session:
        assert session.query(Record).count() == 0
    assert client.post(f"/admin/delete/{record_id}").status_code == 404


def test_html_is_sanitized(client, session_factory, category_id):
    dirty = (
        '<p onclick="x()">Текст</p><script>alert(1)</script>'
        '<img src=x onerror=alert(1)><a href="javascript:alert(1)">bad</a>'
        '<a href="https://example.com">ok</a><h2>Заголовок</h2>'
    )
    client.post("/admin/new", data=make_form(category_id, text=dirty))
    with session_factory() as session:
        text = session.query(Record).one().text
    assert "script" not in text and "onclick" not in text
    assert "<img" not in text and "javascript:" not in text
    assert 'href="https://example.com"' in text and 'rel="noopener noreferrer"' in text
    assert "<h2>Заголовок</h2>" in text


def test_ids_are_not_reused(client, session_factory, category_id):
    client.post("/admin/new", data=make_form(category_id))
    with session_factory() as session:
        first = session.query(Record).one().id
    client.post(f"/admin/delete/{first}")
    client.post("/admin/new", data=make_form(category_id))
    with session_factory() as session:
        assert session.query(Record).one().id > first


def test_preview_shows_draft(client, session_factory, category_id):
    form = make_form(category_id)
    del form["is_published"]
    client.post("/admin/new", data=form)
    with session_factory() as session:
        record_id = session.query(Record).one().id
    assert client.get(f"/record/{record_id}").status_code == 404
    assert "Предпросмотр" in client.get(f"/admin/preview/{record_id}").text


def test_admin_list_search_filter(client, category_id):
    client.post("/admin/new", data=make_form(category_id, title="Сидеть"))
    client.post("/admin/new", data=make_form(category_id, title="Лежать"))
    page = client.get("/admin?q=ЛЕЖАТЬ")
    assert "Лежать" in page.text and "Сидеть" not in page.text
