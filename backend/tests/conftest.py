import os
import tempfile

# Configure a throwaway data dir + fixed admin password BEFORE the app imports
# its config (which is cached at import time).
_tmp = tempfile.mkdtemp(prefix="instabi_test_")
os.environ["INSTABI_DATA_DIR"] = _tmp
os.environ["INSTABI_ADMIN_PASSWORD"] = "test-password"
os.environ["INSTABI_SCRAPER_PROVIDER"] = "mock"
os.environ["INSTABI_SCHEDULE_ENABLED"] = "false"
os.environ["INSTABI_PER_HANDLE_DELAY"] = "0"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from backend.app.main import app
    from backend.app.database import Base, engine
    from backend.app import models  # noqa: F401  (register mappings)

    # Reset the database for test isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "test-password"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}
