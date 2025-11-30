"""Pytest configuration and shared fixtures."""
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from src.models.base import Base
from src.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        database_url="postgresql://marketprep:devpassword@localhost:5432/marketprep_test",
        redis_url="redis://localhost:6379/15",  # Separate Redis DB for tests
        environment="testing",
        debug=True,
    )


@pytest.fixture(scope="session")
def test_engine(test_settings: Settings):
    """Create test database engine."""
    engine = create_engine(str(test_settings.database_url), echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client."""
    from src.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_square_api(mocker):
    """Mock Square API responses."""
    return mocker.patch("src.adapters.square_adapter.SquareAdapter")


@pytest.fixture
def mock_weather_api(mocker):
    """Mock Weather API responses."""
    return mocker.patch("src.adapters.weather_adapter.WeatherAdapter")


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client."""
    return mocker.patch("redis.Redis")
