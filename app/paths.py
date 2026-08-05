from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_NAME = "GestioneTurni"


def _source_root() -> Path:
    """
    Restituisce la cartella principale del progetto
    oppure la cartella contenente l'eseguibile.
    """
    if getattr(sys, "frozen", False):
        return Path(
            sys.executable
        ).resolve().parent

    return Path(
        __file__
    ).resolve().parent.parent


def _default_user_data_root() -> Path:
    """
    Restituisce la cartella usata per i dati persistenti.

    Il percorso predefinito sarà:

    C:\\Users\\<utente>\\GestioneTurniData

    È possibile cambiarlo impostando la variabile
    d'ambiente GESTIONE_TURNI_DATA_DIR.
    """
    override = os.environ.get(
        "GESTIONE_TURNI_DATA_DIR",
        "",
    ).strip()

    if override:
        return Path(
            override
        ).expanduser().resolve()

    return (
        Path.home()
        / "GestioneTurniData"
    )


SOURCE_ROOT = _source_root()

# Vecchia cartella dati presente nel progetto.
LEGACY_DATA_DIR = (
    SOURCE_ROOT
    / "data"
)

# Nuova cartella persistente fuori da OneDrive
# e dalla directory di installazione.
DATA_ROOT = _default_user_data_root()

CONFIG_DIR = (
    DATA_ROOT
    / "config"
)

QUEUE_DIR = (
    DATA_ROOT
    / "queue"
)

HISTORY_DIR = (
    DATA_ROOT
    / "history"
)

DISPLAY_DIR = (
    DATA_ROOT
    / "display"
)

HISTORY_FILE = (
    HISTORY_DIR
    / "history.json"
)

HISTORY_LOCK_FILE = (
    HISTORY_DIR
    / "history.lock"
)


LEGACY_FILE_DESTINATIONS: dict[
    str,
    Path,
] = {
    "config.json": (
        CONFIG_DIR
        / "config.json"
    ),
    "config_doctor1.json": (
        CONFIG_DIR
        / "config_doctor1.json"
    ),
    "config_doctor2.json": (
        CONFIG_DIR
        / "config_doctor2.json"
    ),
    "turns.json": (
        QUEUE_DIR
        / "turns.json"
    ),
    "turns_doctor1.json": (
        QUEUE_DIR
        / "turns_doctor1.json"
    ),
    "turns_doctor2.json": (
        QUEUE_DIR
        / "turns_doctor2.json"
    ),
    "history.json": HISTORY_FILE,
}


def ensure_data_directories() -> None:
    """
    Crea tutte le cartelle richieste
    per il salvataggio dei dati.
    """
    directories = (
        DATA_ROOT,
        CONFIG_DIR,
        QUEUE_DIR,
        HISTORY_DIR,
        DISPLAY_DIR,
    )

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def migrate_legacy_data(
) -> list[tuple[Path, Path]]:
    """
    Copia i vecchi file dalla cartella data del progetto
    nella nuova cartella persistente.

    I file già presenti nella nuova posizione
    non vengono sovrascritti.

    I vecchi file non vengono cancellati e rimangono
    disponibili come backup.
    """
    ensure_data_directories()

    if not LEGACY_DATA_DIR.exists():
        return []

    migrated: list[
        tuple[Path, Path]
    ] = []

    for (
        legacy_name,
        destination,
    ) in LEGACY_FILE_DESTINATIONS.items():
        source = (
            LEGACY_DATA_DIR
            / legacy_name
        )

        if not source.is_file():
            continue

        if destination.exists():
            continue

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        migrated.append(
            (
                source,
                destination,
            )
        )

    return migrated


def initialise_data_storage(
) -> list[tuple[Path, Path]]:
    """
    Inizializza la struttura dati e migra
    gli eventuali file della vecchia versione.
    """
    ensure_data_directories()

    return migrate_legacy_data()


def get_config_file(
    profile: str | None,
) -> Path:
    """
    Restituisce il file di configurazione
    associato al profilo richiesto.
    """
    if profile is None:
        return (
            CONFIG_DIR
            / "config.json"
        )

    return (
        CONFIG_DIR
        / f"config_{profile}.json"
    )


def get_turns_file(
    profile: str | None,
) -> Path:
    """
    Restituisce il file dei numeri
    associato al profilo richiesto.
    """
    if profile is None:
        return (
            QUEUE_DIR
            / "turns.json"
        )

    return (
        QUEUE_DIR
        / f"turns_{profile}.json"
    )


def get_turns_lock_file(
    profile: str | None,
) -> Path:
    """
    Restituisce il file di lock
    associato al profilo richiesto.
    """
    if profile is None:
        return (
            QUEUE_DIR
            / "turns.lock"
        )

    return (
        QUEUE_DIR
        / f"turns_{profile}.lock"
    )