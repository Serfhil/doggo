import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import data.db as db
from core import settings
from data.base import Base
from data.models import Category
from main import app


@pytest.fixture
def session_factory():
    # БД в памяти: тест не трогает настоящую базу. StaticPool: все соединения видят одну БД
    engine = db.make_engine("sqlite://")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with factory() as session:
        db.seed_defaults(session)
    yield factory
    engine.dispose()


@pytest.fixture
def client(session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[db.get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def category_id(session_factory):
    with session_factory() as session:
        return session.query(Category).order_by(Category.id).first().id


def make_form(category_id, **overrides):
    form = {
        "title": "Сидеть",
        "category_id": str(category_id),
        "description": "Базовая команда",
        "text": "<p>Возьмите лакомство</p>",
        "is_published": "on",
    }
    form.update(overrides)
    return form
