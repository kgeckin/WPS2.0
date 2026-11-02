from __future__ import annotations

import pytest

from wps_lab import storage
from wps_lab.app import create_app


@pytest.fixture
def lab(tmp_path):
    storage.initialize(tmp_path / "lab.sqlite3")
    app = create_app({
        "DATA_DIR": tmp_path,
        "SECRET_KEY": "test-only-strong-random-like-value-" + "X" * 32,
        "TESTING": True,
    })
    return app, tmp_path


@pytest.fixture
def client(lab):
    return lab[0].test_client()
