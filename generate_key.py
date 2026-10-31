"""Generate a Fernet key locally without exposing its value in terminal output."""

from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet


def ensure_secret_key_in_env(env_path: str | Path = ".env") -> str:
    path = Path(env_path)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("SECRET_KEY="):
                existing = line.split("=", 1)[1].strip()
                if existing:
                    print("Existing SECRET_KEY retained in the environment file.")
                    return existing

    key = Fernet.generate_key().decode()
    with path.open("a", encoding="utf-8") as stream:
        if path.exists() and path.stat().st_size:
            stream.write("\n")
        stream.write(f"SECRET_KEY={key}\n")
    print(f"Created a local SECRET_KEY in {path}. Do not commit this file.")
    return key


if __name__ == "__main__":
    ensure_secret_key_in_env()
