import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="pcmsc-tests-"))
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["ADMIN_API_KEY"] = "demo-admin-key"
os.environ["OPERATOR_API_KEY"] = "demo-operator-key"
os.environ["REVIEWER_API_KEY"] = "demo-reviewer-key"
os.environ["READONLY_API_KEY"] = "demo-readonly-key"
os.environ["AI_PROVIDER"] = "mock"
os.environ["PAYMENT_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import create_app
from app.services.bootstrap import seed_api_keys


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_api_keys(db)
        db.commit()
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers():
    return {"X-API-Key": "demo-admin-key"}


@pytest.fixture()
def operator_headers():
    return {"X-API-Key": "demo-operator-key"}


@pytest.fixture()
def reviewer_headers():
    return {"X-API-Key": "demo-reviewer-key"}


@pytest.fixture()
def readonly_headers():
    return {"X-API-Key": "demo-readonly-key"}
