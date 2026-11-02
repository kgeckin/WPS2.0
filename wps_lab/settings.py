"""Private local configuration. No fixed fallback credentials or shared keys."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "var"


def data_directory() -> Path:
    return Path(os.environ.get("WPS_DATA_DIR", str(DEFAULT_DATA))).expanduser().resolve()


def initialize_secret(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / "secret.key"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(secrets.token_urlsafe(48))
            handle.write("\n")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except FileExistsError:
        pass
    return path


def secret_for(folder: Path) -> str:
    value = os.environ.get("WPS_SECRET_KEY", "")
    if not value:
        path = folder / "secret.key"
        if path.is_file():
            value = path.read_text(encoding="utf-8").strip()
    if len(value) < 40:
        raise RuntimeError("Run 'python main.py init' before serving. A strong local secret is required.")
    return value
