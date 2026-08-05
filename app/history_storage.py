from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator


from app.paths import HISTORY_DIR, HISTORY_FILE, HISTORY_LOCK_FILE

DOCTOR_IDS = {
    "doctor1",
    "doctor2",
}

LOCK_TIMEOUT_SECONDS = 8.0
LOCK_RETRY_SECONDS = 0.05

FILE_REPLACE_ATTEMPTS = 20
FILE_REPLACE_RETRY_SECONDS = 0.10


def load_history() -> list[dict[str, Any]]:
    """
    Carica e normalizza tutto lo storico.

    L'accesso è protetto da un lock condiviso tra processi,
    così due istanze dell'applicazione non leggono il file
    mentre un'altra lo sta sostituendo.
    """
    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with _history_file_lock():
            return _load_history_unlocked()

    except (
        OSError,
        TimeoutError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return []


def save_history(
    history: list[dict[str, Any]],
) -> None:
    """
    Salva lo storico in modo sicuro.

    Usa:
    - un lock condiviso tra processi;
    - un file temporaneo univoco;
    - più tentativi di sostituzione per tollerare
      i blocchi temporanei causati da Windows o OneDrive.
    """
    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _history_file_lock():
        _save_history_unlocked(history)


def start_daily_queue(
    *,
    doctor_id: str,
    doctor_name: str,
    starting_number: int,
) -> dict[str, Any]:
    """
    Apre una nuova sessione giornaliera.

    Se esiste già una sessione aperta per lo stesso medico
    nella giornata corrente, aggiorna e riutilizza quella.
    """
    _validate_doctor_id(doctor_id)

    clean_name = _clean_doctor_name(
        doctor_name
    )
    safe_number = _safe_number(
        starting_number
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _history_file_lock():
        history = _load_history_unlocked()
        today = date.today().isoformat()

        existing_entry = _find_open_entry(
            history=history,
            doctor_id=doctor_id,
            entry_date=today,
        )

        if existing_entry is not None:
            existing_entry["doctor_name"] = (
                clean_name
            )
            existing_entry["last_number"] = (
                safe_number
            )

            _update_statistics(
                existing_entry
            )
            _save_history_unlocked(
                history
            )

            return dict(
                existing_entry
            )

        entry = {
            "date": today,
            "doctor_id": doctor_id,
            "doctor_name": clean_name,
            "starting_number": safe_number,
            "last_number": safe_number,
            "patients_served": 0,
            "started_at": _current_time(),
            "ended_at": None,
            "duration_minutes": None,
            "patients_per_hour": None,
        }

        history.append(entry)
        _save_history_unlocked(history)

        return dict(entry)


def update_daily_queue(
    *,
    doctor_id: str,
    doctor_name: str,
    current_number: int,
) -> dict[str, Any]:
    """
    Aggiorna il numero raggiunto nella sessione aperta.

    Tutta l'operazione lettura-modifica-scrittura avviene
    mantenendo il lock, evitando che un altro processo
    sovrascriva gli aggiornamenti.
    """
    _validate_doctor_id(doctor_id)

    clean_name = _clean_doctor_name(
        doctor_name
    )
    safe_number = _safe_number(
        current_number
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _history_file_lock():
        history = _load_history_unlocked()
        today = date.today().isoformat()

        entry = _find_open_entry(
            history=history,
            doctor_id=doctor_id,
            entry_date=today,
        )

        if entry is None:
            entry = {
                "date": today,
                "doctor_id": doctor_id,
                "doctor_name": clean_name,
                "starting_number": safe_number,
                "last_number": safe_number,
                "patients_served": 0,
                "started_at": _current_time(),
                "ended_at": None,
                "duration_minutes": None,
                "patients_per_hour": None,
            }

            history.append(entry)

        else:
            entry["doctor_name"] = (
                clean_name
            )
            entry["last_number"] = (
                safe_number
            )

        _update_statistics(entry)
        _save_history_unlocked(history)

        return dict(entry)


def end_daily_queue(
    *,
    doctor_id: str,
    doctor_name: str,
    final_number: int,
) -> dict[str, Any] | None:
    """
    Chiude la sessione aperta e calcola le statistiche.
    """
    _validate_doctor_id(doctor_id)

    clean_name = _clean_doctor_name(
        doctor_name
    )
    safe_number = _safe_number(
        final_number
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _history_file_lock():
        history = _load_history_unlocked()
        today = date.today().isoformat()

        entry = _find_open_entry(
            history=history,
            doctor_id=doctor_id,
            entry_date=today,
        )

        if entry is None:
            return None

        entry["doctor_name"] = clean_name
        entry["last_number"] = safe_number
        entry["ended_at"] = _current_time()

        _update_statistics(entry)
        _save_history_unlocked(history)

        return dict(entry)


def get_history_for_doctor(
    doctor_id: str,
) -> list[dict[str, Any]]:
    """
    Restituisce esclusivamente lo storico del medico
    richiesto, dal più recente al più vecchio.
    """
    _validate_doctor_id(
        doctor_id
    )

    personal_history = [
        entry
        for entry in load_history()
        if entry.get("doctor_id")
        == doctor_id
    ]

    return sorted(
        personal_history,
        key=lambda entry: (
            str(
                entry.get(
                    "date",
                    "",
                )
            ),
            str(
                entry.get(
                    "started_at",
                    "",
                )
            ),
        ),
        reverse=True,
    )


def clear_history_for_doctor(
    doctor_id: str,
) -> None:
    """
    Cancella soltanto lo storico del medico indicato.
    I dati dell'altro medico vengono conservati.
    """
    _validate_doctor_id(
        doctor_id
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _history_file_lock():
        history = _load_history_unlocked()

        remaining_history = [
            entry
            for entry in history
            if entry.get("doctor_id")
            != doctor_id
        ]

        _save_history_unlocked(
            remaining_history
        )


def _load_history_unlocked(
) -> list[dict[str, Any]]:
    """
    Legge il file senza acquisire il lock.

    Deve essere chiamata soltanto quando il chiamante
    possiede già il lock oppure durante operazioni isolate.
    """
    if not HISTORY_FILE.exists():
        return []

    raw_history: Any = None

    for attempt in range(
        FILE_REPLACE_ATTEMPTS
    ):
        try:
            with HISTORY_FILE.open(
                "r",
                encoding="utf-8",
            ) as file:
                raw_history = json.load(
                    file
                )

            break

        except PermissionError:
            if (
                attempt
                == FILE_REPLACE_ATTEMPTS - 1
            ):
                raise

            time.sleep(
                FILE_REPLACE_RETRY_SECONDS
            )

    if not isinstance(
        raw_history,
        list,
    ):
        raise ValueError(
            "Formato dello storico non valido."
        )

    history: list[
        dict[str, Any]
    ] = []

    for raw_entry in raw_history:
        if not isinstance(
            raw_entry,
            dict,
        ):
            continue

        try:
            history.append(
                _normalise_entry(
                    raw_entry
                )
            )
        except ValueError:
            continue

    return history


def _save_history_unlocked(
    history: list[dict[str, Any]],
) -> None:
    """
    Salva senza acquisire il lock.

    Deve essere chiamata esclusivamente mentre il lock
    dello storico è già attivo.
    """
    safe_history: list[
        dict[str, Any]
    ] = []

    for raw_entry in history:
        if not isinstance(
            raw_entry,
            dict,
        ):
            continue

        try:
            safe_history.append(
                _normalise_entry(
                    raw_entry
                )
            )
        except ValueError:
            continue

    temporary_file = (
        HISTORY_DIR
        / (
            "history_"
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
                safe_history,
                file,
                ensure_ascii=False,
                indent=4,
            )

            file.flush()
            os.fsync(
                file.fileno()
            )

        _replace_with_retries(
            temporary_file,
            HISTORY_FILE,
        )

    finally:
        if temporary_file.exists():
            try:
                temporary_file.unlink()
            except OSError:
                pass


def _replace_with_retries(
    source: Path,
    destination: Path,
) -> None:
    """
    Sostituisce il file effettuando più tentativi.

    OneDrive, antivirus o indicizzazione di Windows possono
    mantenere il file occupato per pochi millisecondi.
    """
    last_error: OSError | None = None

    for attempt in range(
        FILE_REPLACE_ATTEMPTS
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
                == FILE_REPLACE_ATTEMPTS - 1
            ):
                break

            time.sleep(
                FILE_REPLACE_RETRY_SECONDS
            )

    if last_error is not None:
        raise last_error


@contextmanager
def _history_file_lock(
) -> Iterator[None]:
    """
    Lock semplice tra processi basato sulla creazione
    esclusiva di un file.

    Solo un'istanza alla volta può eseguire operazioni
    di lettura-modifica-scrittura sullo storico.
    """
    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    deadline = (
        time.monotonic()
        + LOCK_TIMEOUT_SECONDS
    )

    lock_descriptor: int | None = None

    while lock_descriptor is None:
        try:
            lock_descriptor = os.open(
                HISTORY_LOCK_FILE,
                (
                    os.O_CREAT
                    | os.O_EXCL
                    | os.O_WRONLY
                ),
            )

            lock_data = (
                f"pid={os.getpid()}\n"
                f"thread={threading.get_ident()}\n"
                f"created={time.time()}\n"
            ).encode("utf-8")

            os.write(
                lock_descriptor,
                lock_data,
            )

        except FileExistsError:
            _remove_stale_lock_if_needed()

            if (
                time.monotonic()
                >= deadline
            ):
                raise TimeoutError(
                    "Impossibile ottenere "
                    "il lock dello storico."
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
            HISTORY_LOCK_FILE.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _remove_stale_lock_if_needed(
) -> None:
    """
    Rimuove un lock rimasto dopo una chiusura anomala.

    Un lock più vecchio del timeout viene considerato
    abbandonato.
    """
    try:
        lock_age = (
            time.time()
            - HISTORY_LOCK_FILE.stat().st_mtime
        )

    except (
        FileNotFoundError,
        OSError,
    ):
        return

    if lock_age <= LOCK_TIMEOUT_SECONDS:
        return

    try:
        HISTORY_LOCK_FILE.unlink()
    except (
        FileNotFoundError,
        OSError,
    ):
        pass


def _update_statistics(
    entry: dict[str, Any],
) -> None:
    starting_number = _safe_number(
        entry.get(
            "starting_number",
            0,
        )
    )

    last_number = _safe_number(
        entry.get(
            "last_number",
            0,
        )
    )

    patients_served = max(
        0,
        last_number - starting_number,
    )

    entry["patients_served"] = (
        patients_served
    )

    duration_minutes = (
        _calculate_duration_minutes(
            entry_date=str(
                entry.get(
                    "date",
                    "",
                )
            ),
            started_at=entry.get(
                "started_at"
            ),
            ended_at=entry.get(
                "ended_at"
            ),
        )
    )

    entry["duration_minutes"] = (
        duration_minutes
    )

    if (
        duration_minutes is None
        or duration_minutes <= 0
    ):
        entry["patients_per_hour"] = None
        return

    patients_per_hour = (
        patients_served
        / duration_minutes
        * 60
    )

    entry["patients_per_hour"] = round(
        patients_per_hour,
        2,
    )


def _calculate_duration_minutes(
    *,
    entry_date: str,
    started_at: object,
    ended_at: object,
) -> int | None:
    if ended_at is None:
        return None

    start_time = _normalise_optional_time(
        started_at
    )
    end_time = _normalise_optional_time(
        ended_at
    )

    if (
        start_time is None
        or end_time is None
    ):
        return None

    try:
        session_date = (
            date.fromisoformat(
                entry_date
            )
        )

        start_datetime = (
            datetime.combine(
                session_date,
                datetime.strptime(
                    start_time,
                    "%H:%M:%S",
                ).time(),
            )
        )

        end_datetime = (
            datetime.combine(
                session_date,
                datetime.strptime(
                    end_time,
                    "%H:%M:%S",
                ).time(),
            )
        )

        if (
            end_datetime
            < start_datetime
        ):
            end_datetime += timedelta(
                days=1
            )

        duration_seconds = (
            end_datetime
            - start_datetime
        ).total_seconds()

        return max(
            0,
            round(
                duration_seconds / 60
            ),
        )

    except ValueError:
        return None


def _find_open_entry(
    *,
    history: list[dict[str, Any]],
    doctor_id: str,
    entry_date: str,
) -> dict[str, Any] | None:
    for entry in reversed(
        history
    ):
        if (
            entry.get("doctor_id")
            != doctor_id
        ):
            continue

        if (
            entry.get("date")
            != entry_date
        ):
            continue

        if (
            entry.get("ended_at")
            is not None
        ):
            continue

        return entry

    return None


def _normalise_entry(
    raw_entry: dict[str, Any],
) -> dict[str, Any]:
    doctor_id = str(
        raw_entry.get(
            "doctor_id",
            "",
        )
    )

    _validate_doctor_id(
        doctor_id
    )

    entry_date = str(
        raw_entry.get(
            "date",
            "",
        )
    )

    try:
        date.fromisoformat(
            entry_date
        )

    except ValueError as error:
        raise ValueError(
            "Data dello storico "
            "non valida."
        ) from error

    started_at = (
        _normalise_optional_time(
            raw_entry.get(
                "started_at"
            )
        )
    )

    ended_at = (
        _normalise_optional_time(
            raw_entry.get(
                "ended_at"
            )
        )
    )

    if started_at is None:
        raise ValueError(
            "Ora di inizio mancante."
        )

    entry = {
        "date": entry_date,
        "doctor_id": doctor_id,
        "doctor_name": (
            _clean_doctor_name(
                raw_entry.get(
                    "doctor_name",
                    "",
                )
            )
        ),
        "starting_number": (
            _safe_number(
                raw_entry.get(
                    "starting_number",
                    0,
                )
            )
        ),
        "last_number": (
            _safe_number(
                raw_entry.get(
                    "last_number",
                    0,
                )
            )
        ),
        "patients_served": 0,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_minutes": None,
        "patients_per_hour": None,
    }

    _update_statistics(
        entry
    )

    return entry


def _normalise_optional_time(
    value: object,
) -> str | None:
    if value is None:
        return None

    clean_value = str(
        value
    ).strip()

    if not clean_value:
        return None

    try:
        datetime.strptime(
            clean_value,
            "%H:%M:%S",
        )

    except ValueError as error:
        raise ValueError(
            "Orario dello storico "
            "non valido."
        ) from error

    return clean_value


def _validate_doctor_id(
    doctor_id: str,
) -> None:
    if doctor_id not in DOCTOR_IDS:
        raise ValueError(
            "Identificativo medico "
            f"non valido: {doctor_id}"
        )


def _clean_doctor_name(
    doctor_name: object,
) -> str:
    clean_name = str(
        doctor_name
    ).strip()

    if not clean_name:
        raise ValueError(
            "Il nome del medico "
            "non può essere vuoto."
        )

    return clean_name


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


def _current_time() -> str:
    return datetime.now().strftime(
        "%H:%M:%S"
    )