from data.models import Category, Record, Tag
from tests.conftest import make_form


def test_add_tag_unique_ignoring_case_and_yo(client, session_factory):
    response = client.post("/admin/taxonomy/tags/add", data={"name": "лёгкий"})
    assert response.status_code == 422
    assert "уже есть" in response.text
    with session_factory() as session:
        assert session.query(Tag).count() == 3


def test_rename_and_delete_tag(client, session_factory):
    with session_factory() as session:
        tag_id = session.query(Tag).first().id
    client.post(f"/admin/taxonomy/tags/{tag_id}/rename", data={"name": "Новое имя"})
    with session_factory() as session:
        assert session.get(Tag, tag_id).name == "Новое имя"
    client.post(f"/admin/taxonomy/tags/{tag_id}/delete")
    with session_factory() as session:
        assert session.get(Tag, tag_id) is None


def test_merge_tags(client, session_factory, category_id):
    with session_factory() as session:
        a, b = [t.id for t in session.query(Tag).order_by(Tag.id).limit(2)]
    client.post("/admin/new", data={**make_form(category_id), "tags": [str(a)]})
    client.post(f"/admin/taxonomy/tags/{a}/merge", data={"target_id": str(b)})
    with session_factory() as session:
        assert session.get(Tag, a) is None
        assert [t.id for t in session.query(Record).one().tags] == [b]


def test_cannot_delete_used_category(client, session_factory, category_id):
    client.post("/admin/new", data=make_form(category_id))
    response = client.post(f"/admin/taxonomy/categories/{category_id}/delete")
    assert response.status_code == 422
    assert "используется в записях" in response.text
    with session_factory() as session:
        assert session.get(Category, category_id) is not None


def test_move_then_delete_category(client, session_factory, category_id):
    client.post("/admin/new", data=make_form(category_id))
    with session_factory() as session:
        other = session.query(Category).filter(Category.id != category_id).first().id
    client.post(f"/admin/taxonomy/categories/{category_id}/move", data={"target_id": str(other)})
    client.post(f"/admin/taxonomy/categories/{category_id}/delete")
    with session_factory() as session:
        assert session.get(Category, category_id) is None
        assert session.query(Record).one().category_id == other


def test_add_category(client, session_factory):
    client.post("/admin/taxonomy/categories/add", data={"name": "Прогулка"})
    with session_factory() as session:
        assert session.query(Category).count() == 5
