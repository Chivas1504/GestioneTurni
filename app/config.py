import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_ROOT / "data"
CONFIG_FILE = DATA_DIRECTORY / "config.json"

DEFAULT_CONFIG = {
    "configured": False,
    "doctor_id": "",
    "doctor_name": "",
    "queue_active": False,
}


def load_config() -> dict[str, Any]:
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Configurazione non valida.")

        return {
            "configured": bool(data.get("configured", False)),
            "doctor_id": str(data.get("doctor_id", "")),
            "doctor_name": str(data.get("doctor_name", "")).strip(),
            "queue_active": bool(data.get("queue_active", False)),
        }

    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    safe_config = {
        "configured": bool(config.get("configured", False)),
        "doctor_id": str(config.get("doctor_id", "")),
        "doctor_name": str(config.get("doctor_name", "")).strip(),
        "queue_active": bool(config.get("queue_active", False)),
    }

    temporary_file = CONFIG_FILE.with_suffix(".json.tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            safe_config,
            file,
            ensure_ascii=False,
            indent=4,
        )

    temporary_file.replace(CONFIG_FILE)
