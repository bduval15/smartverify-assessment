import os
import shutil
import uuid
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app
from app.routers.policies import get_git_service
from app.services import GitStorageService

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def git_service():
    workspace_root = Path(__file__).parent / "_workspaces"
    repo_path = workspace_root / uuid.uuid4().hex / "policy_data_store"
    repo_path.mkdir(parents=True)
    repo = Repo.init(repo_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "SmartVerify Tests")
        config.set_value("user", "email", "tests@smartverify.local")
    service = GitStorageService(repo_path)
    try:
        yield service
    finally:
        shutil.rmtree(repo_path.parent, ignore_errors=True)


@pytest.fixture
def client(db_session, git_service, monkeypatch):
    def override_get_db():
        yield db_session

    monkeypatch.setattr(
        GitStorageService,
        "validate_cedar_syntax",
        staticmethod(lambda content: content.startswith("permit(")),
    )
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_git_service] = lambda: git_service

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
