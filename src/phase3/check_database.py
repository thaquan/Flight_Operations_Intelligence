"""Verify PostgreSQL connectivity, expected schemas and bootstrap metadata."""

from __future__ import annotations

import json

from .config import PROJECT_ROOT, read_env


EXPECTED_SCHEMAS = {"silver", "staging", "intermediate", "gold", "marts", "audit"}


def inspect_database(settings: dict[str, str]) -> dict:
    import psycopg

    with psycopg.connect(
        host="127.0.0.1",
        port=int(settings["POSTGRES_PORT"]),
        dbname=settings["POSTGRES_DB"],
        user=settings["POSTGRES_USER"],
        password=settings["POSTGRES_PASSWORD"],
        connect_timeout=10,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, current_setting('server_version')")
            database, user, version = cursor.fetchone()
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name = ANY(%s)",
                (list(EXPECTED_SCHEMAS),),
            )
            schemas = {row[0] for row in cursor.fetchall()}
            if schemas != EXPECTED_SCHEMAS:
                raise ValueError(f"Missing warehouse schemas: {sorted(EXPECTED_SCHEMAS - schemas)}")
            cursor.execute("SELECT schema_version FROM audit.bootstrap_info WHERE bootstrap_id = 1")
            row = cursor.fetchone()
            if row is None or row[0] != 1:
                raise ValueError("Warehouse bootstrap metadata is missing or unexpected")
            cursor.execute("SHOW server_encoding")
            encoding = cursor.fetchone()[0]
            if encoding != "UTF8":
                raise ValueError(f"Unexpected PostgreSQL encoding: {encoding}")
    return {
        "status": "pass",
        "database": database,
        "user": user,
        "postgres_version": version,
        "encoding": encoding,
        "schemas": sorted(schemas),
        "bootstrap_schema_version": 1,
    }


def main() -> None:
    settings = read_env(PROJECT_ROOT / ".env")
    print(json.dumps(inspect_database(settings), indent=2))


if __name__ == "__main__":
    main()
