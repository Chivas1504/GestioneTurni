from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


from app.paths import (
    QUEUE_DIR,
    get_turns_file as resolve_turns_file,
    get_turns_lock_file as resolve_turns_lock_file,
)

VALID_PROFILES = {
    "doctor1",
    "doctor2",
}

LOCK_TIMEOUT_SECONDS = 8.0
LOCK_RETRY_SECONDS = 0.05

FILE_OPERATION_ATTEMPTS = 20
FILE_OPERATION_RETRY_SECONDS = 0.10

_active_storage_profile: str | None = None


def set_active_storage_profile(
    profile: str | None,
) -> None:
    """
    Imposta il profilo usato per il salvataggio dei numeri.

    Durante i test:
    - doctor1 usa turns_doctor1.json;
    - doctor2 usa turns_doctor2.json.

    Senza profilo esplicito viene usato turns.json.
    """
    global _active_storage_profile

    if profile not in {
        None,
        "doctor1",
        "doctor2",
    }:
        raise ValueError(
            f"Profilo di salvataggio non valido: {profile}"
        )

    _active_storage_profile = profile


def get_active_storage_profile() -> str | None:
    return _active_storage_profile


def get_turns_file() -> Path:
    """Restituisce il file JSON utilizzato dal profilo attivo."""
    return resolve_turns_file(_active_storage_profile)


def get_turns_lock_file() -> Path:
    """Restituisce il file di lock relativo al profilo attivo."""
    return resolve_turns_lock_file(_active_storage_profile)


def load_turns() -> dict[str, int]:
    """
    Carica i numeri salvati.

    Se il file non esiste o è temporaneamente illeggibile,
    restituisce una struttura valida con entrambi i medici.
    """
    QUEUE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with _turns_file_lock():
            return _load_turns_unlocked()

    except (
        OSError,
        TimeoutError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return _default_turns()


def save_turns(
    turns: dict[str, Any],
) -> None:
    """
    Salva i numeri in modo sicuro.

    La scrittura è protetta da:
    - lock tra processi;
    - file temporaneo univoco;
    - tentativi automatici in caso di blocco di OneDrive.
    """
    QUEUE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_turns = _normalise_turns(
        turns
    )

    with _turns_file_lock():
        _save_turns_unlocked(
            safe_turns
        )


def _load_turns_unlocked() -> dict[str, int]:
    """
    Legge il file senza acquisire il lock.

    Deve essere chiamato soltanto quando il chiamante
    possiede già il lock.
    """
    turns_file = get_turns_file()

    if not turns_file.exists():
        return _default_turns()

    last_error: OSError | None = None

    for attempt in range(
        FILE_OPERATION_ATTEMPTS
    ):
        try:
            with turns_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                raw_turns = json.load(file)

            if not isinstance(
                raw_turns,
                dict,
            ):
                raise ValueError(
                    "Formato dei turni non valido."
                )

            return _normalise_turns(
                raw_turns
            )

        except PermissionError as error:
            last_error = error

            if (
                attempt
                == FILE_OPERATION_ATTEMPTS - 1
            ):
                break

            time.sleep(
                FILE_OPERATION_RETRY_SECONDS
            )

    if last_error is not None:
        raise last_error

    return _default_turns()


def _save_turns_unlocked(
    turns: dict[str, int],
) -> None:
    """
    Scrive il file senza acquisire il lock.

    Deve essere chiamato soltanto quando il chiamante
    possiede già il lock.
    """
    turns_file = get_turns_file()

    temporary_file = (
        QUEUE_DIR
        / (
            f"{turns_file.stem}_"
            f"{os.getpid()}_"
            f"{threading.get_ident()}.tmp"
        )
    )

    try:
        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                turns,
                file,
                ensure_ascii=False,
                indent=4,
            )

            file.flush()
            os.fsync(
                file.fileno()
            )

        _replace_with_retries(
            source=temporary_file,
            destination=turns_file,
        )

    finally:
        if temporary_file.exists():
            try:
                temporary_file.unlink()
            except OSError:
                pass


def _replace_with_retries(
    *,
    source: Path,
    destination: Path,
) -> None:
    """
    Sostituisce il file con più tentativi.

    OneDrive, Windows Defender o l'indicizzazione possono
    bloccare momentaneamente il file di destinazione.
    """
    last_error: OSError | None = None

    for attempt in range(
        FILE_OPERATION_ATTEMPTS
    ):
        try:
            os.replace(
                source,
                destination,
            )
            return

        except (
            PermissionError,
            OSError,
        ) as error:
            last_error = error

            if (
                attempt
                == FILE_OPERATION_ATTEMPTS - 1
            ):
                break

            time.sleep(
                FILE_OPERATION_RETRY_SECONDS
            )

    if last_error is not None:
        raise last_error


@contextmanager
def _turns_file_lock() -> Iterator[None]:
    """
    Impedisce a due processi di modificare contemporaneamente
    lo stesso file dei turni.
    """
    QUEUE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_file = get_turns_lock_file()

    deadline = (
        time.monotonic()
        + LOCK_TIMEOUT_SECONDS
    )

    lock_descriptor: int | None = None

    while lock_descriptor is None:
        try:
            lock_descriptor = os.open(
                lock_file,
                (
                    os.O_CREAT
                    | os.O_EXCL
                    | os.O_WRONLY
                ),
            )

            lock_information = (
                f"pid={os.getpid()}\n"
                f"thread={threading.get_ident()}\n"
                f"created={time.time()}\n"
            ).encode("utf-8")

            os.write(
                lock_descriptor,
                lock_information,
            )

        except FileExistsError:
            _remove_stale_lock_if_needed(
                lock_file
            )

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Impossibile ottenere il lock "
                    "del file dei turni."
                )

            time.sleep(
                LOCK_RETRY_SECONDS
            )

    try:
        yield

    finally:
        if lock_descriptor is not None:
            try:
                os.close(
                    lock_descriptor
                )
            except OSError:
                pass

        try:
            lock_file.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _remove_stale_lock_if_needed(
    lock_file: Path,
) -> None:
    """
    Elimina un lock rimasto dopo una chiusura anomala.
    """
    try:
        lock_age = (
            time.time()
            - lock_file.stat().st_mtime
        )

    except (
        FileNotFoundError,
        OSError,
    ):
        return

    if lock_age <= LOCK_TIMEOUT_SECONDS:
        return

    try:
        lock_file.unlink()
    except (
        FileNotFoundError,
        OSError,
    ):
        pass


def _normalise_turns(
    turns: dict[str, Any],
) -> dict[str, int]:
    """
    Converte i valori in numeri interi non negativi.

    Mantiene sempre entrambe le chiavi, anche se il profilo
    locale usa normalmente soltanto una di esse.
    """
    return {
        "doctor1": _safe_number(
            turns.get(
                "doctor1",
                0,
            )
        ),
        "doctor2": _safe_number(
            turns.get(
                "doctor2",
                0,
            )
        ),
    }


def _default_turns() -> dict[str, int]:
    return {
        "doctor1": 0,
        "doctor2": 0,
    }


def _safe_number(
    value: object,
) -> int:
    try:
        return max(
            0,
            int(value),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0