import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_ROOT / "data"

_active_storage_profile: str | None = None

DEFAULT_TURNS = {
    "doctor1": 0,
    "doctor2": 0,
}


def set_active_storage_profile(
    profile: str | None,
) -> None:
    global _active_storage_profile

    if profile not in {
        None,
        "doctor1",
        "doctor2",
    }:
        raise ValueError(
            f"Profilo non valido: {profile}"
        )

    _active_storage_profile = profile


def get_turns_file() -> Path:
    if _active_storage_profile is None:
        return DATA_DIRECTORY / "turns.json"

    return (
        DATA_DIRECTORY
        / f"turns_{_active_storage_profile}.json"
    )


def load_turns() -> dict[str, int]:
    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    turns_file = get_turns_file()

    if not turns_file.exists():
        save_turns(DEFAULT_TURNS)
        return DEFAULT_TURNS.copy()

    try:
        with turns_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            data: Any = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Formato dati non valido."
            )

        return {
            "doctor1": _safe_number(
                data.get("doctor1", 0)
            ),
            "doctor2": _safe_number(
                data.get("doctor2", 0)
            ),
        }

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        save_turns(DEFAULT_TURNS)
        return DEFAULT_TURNS.copy()


def save_turns(
    turns: dict[str, int],
) -> None:
    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_turns = {
        "doctor1": _safe_number(
            turns.get("doctor1", 0)
        ),
        "doctor2": _safe_number(
            turns.get("doctor2", 0)
        ),
    }

    turns_file = get_turns_file()

    temporary_file = turns_file.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            safe_turns,
            file,
            ensure_ascii=False,
            indent=4,
        )

    temporary_file.replace(turns_file)


def _safe_number(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0