import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_ROOT / "data"
TURNS_FILE = DATA_DIRECTORY / "turns.json"

DEFAULT_TURNS = {
    "doctor1": 0,
    "doctor2": 0,
}


def load_turns() -> dict[str, int]:
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not TURNS_FILE.exists():
        save_turns(DEFAULT_TURNS)
        return DEFAULT_TURNS.copy()

    try:
        with TURNS_FILE.open("r", encoding="utf-8") as file:
            data: Any = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Formato dati non valido.")

        return {
            "doctor1": max(0, int(data.get("doctor1", 0))),
            "doctor2": max(0, int(data.get("doctor2", 0))),
        }

    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        save_turns(DEFAULT_TURNS)
        return DEFAULT_TURNS.copy()


def save_turns(turns: dict[str, int]) -> None:
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    safe_turns = {
        "doctor1": max(0, int(turns.get("doctor1", 0))),
        "doctor2": max(0, int(turns.get("doctor2", 0))),
    }

    temporary_file = TURNS_FILE.with_suffix(".json.tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            safe_turns,
            file,
            ensure_ascii=False,
            indent=4,
        )

    temporary_file.replace(TURNS_FILE)