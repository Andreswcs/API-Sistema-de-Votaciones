from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    test_engine = create_engine(settings.database_url(settings.test_postgres_db))
    with test_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS votes, voters, candidates, persons"))
        # psycopg admite varias sentencias en un solo execute cuando no hay parámetros.
        connection.connection.driver_connection.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE votes, voters, candidates, persons RESTART IDENTITY"))
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
