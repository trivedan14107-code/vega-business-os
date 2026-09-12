"""Create local platform secrets without displaying them."""

import secrets
from pathlib import Path

from businessflow_ai.services.token_vault import TokenVault


def _append_secret(env_path: Path, name: str, value: str) -> bool:
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    for line in existing.splitlines():
        if line.strip().startswith(f"{name}=") and line.split("=", 1)[1].strip():
            return False

    separator = "" if not existing or existing.endswith("\n") else "\n"
    with env_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{separator}{name}={value}\n")
    return True


def ensure_local_secrets(env_path: Path = Path(".env.local")) -> list[str]:
    created = []
    if _append_secret(env_path, "TOKEN_ENCRYPTION_KEY", TokenVault.generate_key()):
        created.append("token encryption")
    if _append_secret(env_path, "SESSION_SECRET", secrets.token_urlsafe(48)):
        created.append("session signing")
    return created


def main() -> None:
    created = ensure_local_secrets()
    if created:
        print(f"Local security configured: {', '.join(created)}.")
    else:
        print("Local security already configured.")


if __name__ == "__main__":
    main()
