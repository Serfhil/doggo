# tests/test_save_card.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import data.db as db
from data.base import Base
from data.models import Record, Tag
from main import app


@pytest.fixture
def session_factory():
    # БД в оперативной памяти: тест не трогает настоящую базу и исчезает после прогона.
    # StaticPool нужен, чтобы все соединения видели одну и ту же in-memory БД.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    # Подменяем зависимость get_db: роут получит тестовую сессию вместо боевой
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[db.get_db] = override_get_db
    yield TestClient(app)
    # Возвращаем приложение в исходное состояние
    app.dependency_overrides.clear()


VALID_FORM = {
    "title": "Sit",
    "description": "Basic command",
    "text": "Hold a treat above the nose and move it back",
    "record_type": "command",
}


def test_save_card_creates_record_and_redirects(client, session_factory):
    response = client.post(
        "/save_card",
        data={**VALID_FORM, "tags": ["basic", "puppy"]},
        follow_redirects=False,
    )

    # 303 + редирект на /admin
    assert response.status_code == 303
    assert response.headers["location"].endswith("/admin")

    # Проверяем, что запись реально попала в БД вместе с тегами
    with session_factory() as session:
        records = session.query(Record).all()
        assert len(records) == 1
        assert records[0].title == "Sit"
        assert records[0].record_type == "command"
        assert {t.name for t in records[0].tags} == {"basic", "puppy"}


def test_save_card_without_tags(client, session_factory):
    response = client.post("/save_card", data=VALID_FORM, follow_redirects=False)

    assert response.status_code == 303
    with session_factory() as session:
        record = session.query(Record).one()
        assert record.tags == []


def test_save_card_reuses_existing_tag(client, session_factory):
    # Два запроса с одним тегом не должны создавать дубликат в таблице tags
    for _ in range(2):
        client.post(
            "/save_card",
            data={**VALID_FORM, "tags": ["basic"]},
            follow_redirects=False,
        )

    with session_factory() as session:
        assert session.query(Record).count() == 2
        assert session.query(Tag).count() == 1


@pytest.mark.parametrize("missing", ["title", "description", "text", "record_type"])
def test_save_card_missing_field_returns_422(client, session_factory, missing):
    form = {k: v for k, v in VALID_FORM.items() if k != missing}

    response = client.post("/save_card", data=form, follow_redirects=False)

    # FastAPI сам отклоняет запрос без обязательного поля формы
    assert response.status_code == 422
    with session_factory() as session:
        assert session.query(Record).count() == 0
