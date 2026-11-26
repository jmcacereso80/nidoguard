import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://nido:pw@127.0.0.1:55434/nidoguard_test")
os.environ["DATABASE_URL"] = TEST_URL

from app.db import Base, get_db  # noqa: E402
from app import models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.security import optional_user  # noqa: E402

engine = create_engine(TEST_URL)
Session = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def schema():
    with engine.begin() as c:
        c.execute(text("drop schema public cascade"))
        c.execute(text("create schema public"))
        c.execute(text("create extension if not exists pgcrypto"))
    Base.metadata.create_all(engine)
    yield


@pytest.fixture()
def db():
    s = Session()
    yield s
    s.close()


@pytest.fixture()
def make_client(db):
    """Devuelve una funcion que crea un cliente autenticado como un usuario de Clerk concreto."""
    from app.models import User
    from sqlalchemy import select

    def _make(clerk_id: str | None):
        def _user():
            if clerk_id is None:
                return None
            u = db.scalar(select(User).where(User.clerk_id == clerk_id))
            if not u:
                u = User(clerk_id=clerk_id, email=f"{clerk_id}@test.mx", name=clerk_id)
                db.add(u); db.commit()
            return u
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[optional_user] = _user
        import random
        ip = ".".join(str(random.randint(1, 250)) for _ in range(4))
        return TestClient(app, headers={"x-forwarded-for": ip})
    yield _make
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def no_background_reading(monkeypatch):
    from app.services import readings
    monkeypatch.setattr(readings, "enqueue_reading", lambda *a, **k: None)
