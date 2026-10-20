from data.models import Record, Tag
from tests.conftest import make_form


def _create(client, category_id, **kw):
    client.post("/admin/new", data=make_form(category_id, **kw))


def test_home_and_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Записей пока нет" in response.text


def test_home_lists_only_published(client, category_id):
    _create(client, category_id, title="Видимая")
    draft = make_form(category_id, title="Скрытая")
    del draft["is_published"]
    client.post("/admin/new", data=draft)
    page = client.get("/")
    assert "Видимая" in page.text and "Скрытая" not in page.text


def test_search_ignores_case_in_cyrillic(client, category_id):
    _create(client, category_id, title="Команда «Лежать»", description="Ёлка")
    assert "Лежать" in client.get("/?q=лежать").text
    assert "Лежать" in client.get("/?q=ЕЛКА").text
    assert "Ничего не найдено" in client.get("/?q=прыгать").text


def test_category_and_tag_filters(client, session_factory, category_id):
    client.post("/admin/new", data={**make_form(category_id, title="Первая"), "new_tags": "Особый"})
    _create(client, category_id, title="Вторая")
    with session_factory() as session:
        tag_id = session.query(Tag).filter_by(name="Особый").one().id
    page = client.get(f"/?tag={tag_id}")
    assert "Первая" in page.text and "Вторая" not in page.text
    other = category_id + 1
    assert "В этой категории пока нет записей" in client.get(f"/?category={other}").text


def test_pagination(client, category_id):
    for i in range(14):
        _create(client, category_id, title=f"Запись {i}")
    assert "1 из 2" in client.get("/").text
    assert "2 из 2" in client.get("/?page=2").text


def test_record_page_and_back_link(client, session_factory, category_id):
    _create(client, category_id)
    with session_factory() as session:
        record_id = session.query(Record).one().id
    response = client.get(f"/record/{record_id}?q=сид&evil=http://x.ru")
    assert response.status_code == 200
    assert "Возьмите лакомство" in response.text
    # «назад» только с известными параметрами
    assert 'href="/?q=%D1%81%D0%B8%D0%B4"' in response.text
    assert "evil" not in response.text


def test_404_pages_are_html(client):
    for url in ("/record/999", "/nowhere"):
        response = client.get(url)
        assert response.status_code == 404
        assert "Страница не найдена" in response.text


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
