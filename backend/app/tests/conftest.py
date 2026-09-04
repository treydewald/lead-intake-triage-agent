import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
import app.models  # noqa: F401 - registers models on Base.metadata

from main import app  # noqa: E402 - must come after `import app.models` or it clobbers this name


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session_factory():
    """An isolated in-memory SQLite DB per test, independent of the dev `leads.db`."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
