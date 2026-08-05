from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_NAME = "GestioneTurni"


def _source_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _default_user_data_root() -> Path:
    override = os.environ.get("GESTIONE_TURNI_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / "GestioneTurniData"


SOURCE_ROOT = _source_root()
LEGACY_DATA_DIR = SOURCE_ROOT / "data"
DATA_ROOT = _default_user_data_root()
CONFIG_DIR = DATA_ROOT / "config"
QUEUE_DIR = DATA_ROOT / "queue"
HISTORY_DIR = DATA_ROOT / "history"
DISPLAY_DIR = DATA_ROOT / "display"
HISTORY_FILE = HISTORY_DIR / "history.json"
HISTORY_LOCK_FILE = HISTORY_DIR / "history.lock"

LEGACY_FILE_DESTINATIONS: dict[str, Path] = {
    "config.json": CONFIG_DIR / "config.json",
    "config_doctor1.json": CONFIG_DIR / "config_doctor1.json",
    "config_doctor2.json": CONFIG_DIR / "config_doctor2.json",
    "turns.json": QUEUE_DIR / "turns.json",
    "turns_doctor1.json": QUEUE_DIR / "turns_doctor1.json",
    "turns_doctor2.json": QUEUE_DIR / "turns_doctor2.json",
    "history.json": HISTORY_FILE,
}


def ensure_data_directories() -> None:
    for directory in (DATA_ROOT, CONFIG_DIR, QUEUE_DIR, HISTORY_DIR, DISPLAY_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def migrate_legacy_data() -> list[tuple[Path, Path]]:
    ensure_data_directories()
    if not LEGACY_DATA_DIR.exists():
        return []

    migrated: list[tuple[Path, Path]] = []
    for legacy_name, destination in LEGACY_FILE_DESTINATIONS.items():
        source = LEGACY_DATA_DIR / legacy_name
        if not source.is_file() or destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        migrated.append((source, destination))
    return migrated


def initialise_data_storage() -> list[tuple[Path, Path]]:
    ensure_data_directories()
    return migrate_legacy_data()


def get_config_file(profile: str | None) -> Path:
    filename = "config.json" if profile is None else f"config_{profile}.json"
    return CONFIG_DIR / filename


def get_turns_file(profile: str | None) -> Path:
    filename = "turns.json" if profile is None else f"turns_{profile}.json"
    return QUEUE_DIR / filename


def get_turns_lock_file(profile: str | None) -> Path:
    filename = "turns.lock" if profile is None else f"turns_{profile}.lock"
    return QUEUE_DIR / filename
