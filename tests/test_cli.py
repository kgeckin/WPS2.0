from __future__ import annotations

from wps_lab.cli import main


def test_cli_init_status_report_and_link(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WPS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("WPS_SECRET_KEY", raising=False)
    assert main(["init"]) == 0
    assert main(["status"]) == 0
    assert "synthetic local demo" in capsys.readouterr().out
    assert main(["report"]) == 0
    assert "participant_alias" in capsys.readouterr().out
    assert main(["link", "--campaign", "1", "--participant", "1"]) == 0
    assert "http://127.0.0.1:5000/practice/" in capsys.readouterr().out
    assert main(["link", "--campaign", "2", "--participant", "8"]) == 1
    assert "not eligible" in capsys.readouterr().err
