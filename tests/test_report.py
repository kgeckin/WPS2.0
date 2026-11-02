from __future__ import annotations

import csv
import io

from wps_lab import storage


def test_report_has_only_minimal_columns(client, lab):
    app, folder = lab
    storage.acknowledge(folder / "lab.sqlite3", 1, 1)
    result = client.get("/api/v1/report.csv")
    assert result.status_code == 200
    rows = list(csv.reader(io.StringIO(result.get_data(as_text=True))))
    assert rows[0] == ["campaign", "participant_alias", "event", "timestamp_utc"]
    assert rows[1][1] == "TRAIN-001"
    assert "password" not in result.get_data(as_text=True).lower()
    assert "email" not in result.get_data(as_text=True).lower()


def test_formula_injection_protection(tmp_path):
    path = tmp_path / "lab.sqlite3"
    storage.initialize(path)
    with storage.database(path) as con:
        con.execute("UPDATE campaigns SET name=? WHERE id=1", ("=HYPERLINK(1)",))
    storage.acknowledge(path, 1, 1)
    result = storage.export_csv(path)
    rows = list(csv.reader(io.StringIO(result)))
    assert rows[1][0].startswith("'=")


def test_report_is_stable_when_empty(tmp_path):
    path = tmp_path / "lab.sqlite3"
    storage.initialize(path)
    rows = list(csv.reader(io.StringIO(storage.export_csv(path))))
    assert len(rows) == 1
