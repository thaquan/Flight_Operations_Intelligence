"""Local database configuration checks; no Docker daemon needed."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.phase3.config import bootstrap_env, read_env


def test_bootstrap_creates_strong_secret_once(tmp_path: Path) -> None:
    destination = tmp_path / ".env"
    assert bootstrap_env(destination) is True
    settings = read_env(destination)
    assert settings["POSTGRES_DB"] == "flight_warehouse"
    assert settings["POSTGRES_USER"] == "flight_app"
    assert settings["POSTGRES_PORT"] == "5433"
    assert len(settings["POSTGRES_PASSWORD"]) >= 32
    first_bytes = destination.read_bytes()
    assert bootstrap_env(destination) is False
    assert destination.read_bytes() == first_bytes


def test_missing_or_placeholder_credentials_are_rejected(tmp_path: Path) -> None:
    destination = tmp_path / ".env"
    with pytest.raises(FileNotFoundError):
        read_env(destination)
    destination.write_text(
        "POSTGRES_DB=flight_warehouse\nPOSTGRES_USER=flight_app\n"
        "POSTGRES_PASSWORD=REPLACE_WITH_A_RANDOM_PASSWORD\nPOSTGRES_PORT=5433\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-placeholder"):
        read_env(destination)


def test_invalid_port_and_duplicate_settings_are_rejected(tmp_path: Path) -> None:
    destination = tmp_path / ".env"
    bootstrap_env(destination)
    lines = destination.read_text(encoding="utf-8")
    destination.write_text(lines.replace("POSTGRES_PORT=5433", "POSTGRES_PORT=0"), encoding="utf-8")
    with pytest.raises(ValueError, match="between 1024"):
        read_env(destination)
    destination.write_text(lines + "POSTGRES_DB=another_database\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate setting"):
        read_env(destination)


def test_compose_and_dbt_configuration_do_not_embed_secrets() -> None:
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    profile = (root / "dbt/profiles.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:${POSTGRES_PORT:-5433}:5432" in compose
    assert "postgres_data:/var/lib/postgresql/data" in compose
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in compose
    assert "env_var('POSTGRES_PASSWORD')" in profile
    assert "REPLACE_WITH_A_RANDOM_PASSWORD" not in compose + profile


def test_initialization_defines_required_schemas() -> None:
    root = Path(__file__).resolve().parents[1]
    sql = (root / "docker/postgres/init/001_create_schemas.sql").read_text(encoding="utf-8")
    for name in ("silver", "staging", "intermediate", "gold", "marts", "audit"):
        assert f"CREATE SCHEMA IF NOT EXISTS {name}" in sql
    assert "audit.bootstrap_info" in sql
