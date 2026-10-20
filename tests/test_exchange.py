import json

import pytest

from data import exchange
from data.models import Category, Record, Tag, record_prerequisite, record_related
from tests.conftest import make_form


def seed(client, category_id):
    client.post("/admin/new", data={**make_form(category_id), "new_tags": "Послушание", "tags": ["1"]})
    draft = make_form(category_id, title="Лежать", text="<h2>Шаги</h2><p>Раз</p>")
    del draft["is_published"]
    client.post("/admin/new", data=draft)


def snapshot(session):
    payload = exchange.export_data(session)
    payload.pop("exported_at")
    return payload


def test_export_shape(client, session_factory, category_id):
    seed(client, category_id)
    with session_factory() as session:
        payload = exchange.export_data(session)
    first, second = payload["records"]
    assert payload["schema_version"] == 1
    assert first["tags"] == ["Лёгкий", "Послушание"] and first["is_published"] is True
    assert second["is_published"] is False and "created_at" in second
    assert "views" not in first
    # читаемый русский текст
    assert "Сидеть" in json.dumps(payload, ensure_ascii=False)


def test_round_trip_replace(client, session_factory, category_id):
    seed(client, category_id)
    with session_factory() as session:
        before = snapshot(session)
        session.execute(record_related.insert().values(record_id=1, related_id=2))
        session.execute(record_prerequisite.insert().values(record_id=2, requires_id=1))
        session.commit()
        before = snapshot(session)
        assert before["records"][0]["related"] == [2]
        assert before["records"][1]["related"] == [1]  # симметрия
        assert before["records"][1]["requires"] == [1]

    with session_factory() as session:
        report = exchange.import_data(session, json.loads(json.dumps(before)), replace=True)
    assert report.added == 2
    with session_factory() as session:
        assert snapshot(session) == before


def test_import_adds_and_updates(client, session_factory, category_id):
    seed(client, category_id)
    with session_factory() as session:
        payload = exchange.export_data(session)
    payload["records"][0]["title"] = "Сидеть!"
    payload["records"].append({"id": 50, "title": "Новая", "category": "Прогулка", "text": "<p>x</p>", "tags": ["Свой"]})
    with session_factory() as session:
        report = exchange.import_data(session, payload)
        assert (report.added, report.updated) == (1, 2)
        assert session.get(Record, 1).title == "Сидеть!"
        assert session.get(Record, 50).category.name == "Прогулка"
        assert session.query(Tag).filter_by(name="Свой").count() == 1


def test_invalid_import_changes_nothing(client, session_factory, category_id):
    seed(client, category_id)
    with session_factory() as session:
        payload = exchange.export_data(session)
    payload["records"][0]["title"] = "Испорченное"
    payload["records"].append({"id": 9, "category": "x"})  # нет title
    with session_factory() as session:
        with pytest.raises(exchange.ImportFailed) as exc:
            exchange.import_data(session, payload, replace=True)
        assert "title" in str(exc.value)
    with session_factory() as session:
        assert session.get(Record, 1).title == "Сидеть"


def test_import_sanitizes_html_and_warns(client, session_factory):
    payload = {"records": [{"id": 1, "title": "T", "category": "команда", "text": "<p>a</p><script>x</script>", "лишнее": 1}]}
    with session_factory() as session:
        report = exchange.import_data(session, payload)
        assert "script" not in session.get(Record, 1).text
    assert any("неизвестные поля" in w for w in report.warnings)


def test_broken_relation_is_skipped(client, session_factory):
    payload = {"records": [{"id": 1, "title": "T", "category": "команда", "text": "<p>a</p>", "related": [1, 77], "requires": [77]}]}
    with session_factory() as session:
        report = exchange.import_data(session, payload)
    assert len(report.warnings) == 3
