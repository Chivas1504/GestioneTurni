import json
from typing import Any


from app.paths import CONFIG_DIR, get_config_file as resolve_config_file

_active_profile: str | None = None

DEFAULT_CONFIG = {
    "configured": False,
    "doctor_id": "",
    "doctor_name": "",
    "queue_active": False,
    "display_fullscreen": False,
    "display_show_clock": True,
}


def set_active_profile(
    profile: str | None,
) -> None:
    global _active_profile

    if profile not in {
        None,
        "doctor1",
        "doctor2",
    }:
        raise ValueError(
            f"Profilo non valido: {profile}"
        )

    _active_profile = profile


def get_active_profile() -> str | None:
    return _active_profile


def get_config_file():
    return resolve_config_file(_active_profile)


def load_config() -> dict[str, Any]:
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    config_file = get_config_file()

    if not config_file.exists():
        default_config = DEFAULT_CONFIG.copy()

        if _active_profile is not None:
            default_config["doctor_id"] = (
                _active_profile
            )

        return default_config

    try:
        with config_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Configurazione non valida."
            )

        doctor_id = str(
            data.get("doctor_id", "")
        )

        if _active_profile is not None:
            doctor_id = _active_profile

        return {
            "configured": bool(
                data.get("configured", False)
            ),
            "doctor_id": doctor_id,
            "doctor_name": str(
                data.get("doctor_name", "")
            ).strip(),
            "queue_active": bool(
                data.get("queue_active", False)
            ),
            "display_fullscreen": bool(
                data.get(
                    "display_fullscreen",
                    False,
                )
            ),
            "display_show_clock": bool(
                data.get(
                    "display_show_clock",
                    True,
                )
            ),
        }

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        fallback = DEFAULT_CONFIG.copy()

        if _active_profile is not None:
            fallback["doctor_id"] = (
                _active_profile
            )

        return fallback


def save_config(
    config: dict[str, Any],
) -> None:
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    doctor_id = str(
        config.get("doctor_id", "")
    )

    if _active_profile is not None:
        doctor_id = _active_profile

    if doctor_id not in {
        "doctor1",
        "doctor2",
    }:
        raise ValueError(
            "Identificativo medico non valido."
        )

    safe_config = {
        "configured": bool(
            config.get("configured", False)
        ),
        "doctor_id": doctor_id,
        "doctor_name": str(
            config.get("doctor_name", "")
        ).strip(),
        "queue_active": bool(
            config.get("queue_active", False)
        ),
        "display_fullscreen": bool(
            config.get(
                "display_fullscreen",
                False,
            )
        ),
        "display_show_clock": bool(
            config.get(
                "display_show_clock",
                True,
            )
        ),
    }

    config_file = get_config_file()

    temporary_file = config_file.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            safe_config,
            file,
            ensure_ascii=False,
            indent=4,
        )

    temporary_file.replace(config_file)
