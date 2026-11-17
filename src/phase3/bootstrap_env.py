"""Generate the ignored local PostgreSQL configuration if absent."""

from __future__ import annotations

from .config import PROJECT_ROOT, bootstrap_env, read_env


def main() -> None:
    target = PROJECT_ROOT / ".env"
    created = bootstrap_env(target)
    read_env(target)
    action = "Created" if created else "Retained existing"
    print(f"{action} local PostgreSQL configuration: {target}")
    print("Credentials are not displayed and must not be committed.")


if __name__ == "__main__":
    main()
