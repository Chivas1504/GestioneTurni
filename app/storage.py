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

LOCK_TIMEOUT_SECONDS = 8.0
LOCK_RETRY_SECONDS = 0.05

FILE_OPERATION_ATTEMPTS = 20
FILE_OPERATION_RETRY_SECONDS = 0.10

_active_storage_profile: str | None = None


def set_active_storage_profile(
    profile: str | None,
) -> None:
    global _active_storage_profile

    if profile is not None and not str(profile).strip():
        raise ValueError(f"Profilo di salvataggio non valido: {profile}")

    _active_storage_profile = profile


def get_active_storage_profile() -> str | None:
    return _active_storage_profile


def get_turns_file() -> Path:
    return resolve_turns_file(_active_storage_profile)


def get_turns_lock_file() -> Path:
    return resolve_turns_lock_file(_active_storage_profile)


def load_turns() -> dict[str, int]:
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
    result: dict[str, int] = {}
    for key, value in turns.items():
        doctor_id = str(key).strip()
        if doctor_id:
            result[doctor_id] = _safe_number(value)
    if _active_storage_profile and _active_storage_profile not in result:
        result[_active_storage_profile] = 0
    return result


def _default_turns() -> dict[str, int]:
    if _active_storage_profile:
        return {_active_storage_profile: 0}
    return {}

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
