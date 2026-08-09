import os

import app.models  # noqa: F401
import pytest
from app.cache.base import RedisCache
from app.db.session import Base, get_db
from app.dependencies.cache import get_cache
from app.dependencies.rate_limiter import get_rate_limiter
from app.main import app as fastapi_app
from app.security.rate_limiter import RateLimiter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tests.fakes import InMemoryRedis

DATABASE_URL = os.getenv("DATABASE_URL")
_TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not _TEST_DATABASE_URL:
    raise ValueError("TEST_DATABASE_URL is not set")
TEST_DATABASE_URL: str = _TEST_DATABASE_URL


def validate_test_database_url() -> None:
    test_url = make_url(TEST_DATABASE_URL)
    database_url = DATABASE_URL

    if database_url:
        main_url = make_url(database_url)
        if (
            test_url.drivername == main_url.drivername
            and test_url.username == main_url.username
            and test_url.host == main_url.host
            and test_url.port == main_url.port
            and test_url.database == main_url.database
        ):
            raise RuntimeError(
                "TEST_DATABASE_URL points to the main database. "
                "Refusing to run destructive test setup."
            )

    if not test_url.database or "test" not in test_url.database.lower():
        raise RuntimeError(
            "TEST_DATABASE_URL must point to a dedicated test database "
            "(database name should contain 'test')."
        )


validate_test_database_url()


engine = create_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"connect_timeout": 5},
)


@pytest.fixture(scope="session")
def test_engine():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def fake_redis():
    return InMemoryRedis()


@pytest.fixture(scope="function")
def client(db_session: Session, fake_redis: InMemoryRedis):
    def override_get_db():
        yield db_session

    def override_get_cache():
        return RedisCache(fake_redis)

    def override_get_rate_limiter():
        return RateLimiter(fake_redis)

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_cache] = override_get_cache
    fastapi_app.dependency_overrides[get_rate_limiter] = override_get_rate_limiter

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
