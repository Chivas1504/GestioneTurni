from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.auth import create_password_record, verify_password
from app.paths import DATA_ROOT

ACCOUNTS_FILE = DATA_ROOT / "accounts.json"
ACCOUNTS_LOCK = threading.RLock()


class AccountStore:
    def __init__(self) -> None:
        self._lock = ACCOUNTS_LOCK
        self._accounts: dict[str, dict[str, Any]] = {}
        self._load()

    def import_record(self, record: dict[str, Any]) -> None:
        doctor_id = str(record.get("doctor_id", "")).strip()
        doctor_name = str(record.get("doctor_name", "")).strip()
        if not doctor_id or not doctor_name:
            return
        incoming = dict(record)
        incoming.setdefault("updated_at", time.time())
        self.merge_records([incoming])

    def list_public(self) -> list[dict[str, Any]]:
        with self._lock:
            result = [
                self._public(account)
                for account in self._accounts.values()
                if not bool(account.get("deleted", False))
            ]
        return sorted(result, key=lambda item: str(item.get("doctor_name", "")).casefold())

    def export_records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(account) for account in self._accounts.values()]

    def get(self, doctor_id: str) -> dict[str, Any] | None:
        with self._lock:
            account = self._accounts.get(str(doctor_id).strip())
            if not account or bool(account.get("deleted", False)):
                return None
            return dict(account)

    def get_record(self, doctor_id: str) -> dict[str, Any] | None:
        """Restituisce anche gli eventuali tombstone di account eliminati."""
        with self._lock:
            account = self._accounts.get(str(doctor_id).strip())
            return dict(account) if account else None

    def create(self, doctor_name: str, password: str) -> dict[str, Any]:
        clean_name = str(doctor_name).strip()
        if not clean_name:
            raise ValueError("Inserisci il nome del medico o dello studio.")
        record = {
            "doctor_id": str(uuid.uuid4()),
            "doctor_name": clean_name,
            "queue_prefix": "",
            "patient_time_warning_enabled": False,
            "patient_time_warning_minutes": 15,
            "patient_time_warning_sound_enabled": False,
            "updated_at": time.time(),
            "deleted": False,
        }
        record.update(create_password_record(password))
        with self._lock:
            self._accounts[record["doctor_id"]] = record
            self._save_unlocked()
        return dict(record)

    def verify(self, doctor_id: str, password: str) -> dict[str, Any] | None:
        account = self.get(doctor_id)
        if account is None or not verify_password(password, account):
            return None
        return account

    def delete(self, doctor_id: str, password: str) -> dict[str, Any]:
        clean_id = str(doctor_id).strip()
        account = self.get(clean_id)
        if account is None:
            raise ValueError("Account non trovato o già eliminato.")
        if not verify_password(password, account):
            raise ValueError("Password non corretta.")

        # Manteniamo solo un tombstone tecnico anonimo: serve a propagare
        # l'eliminazione agli altri PC e a impedire che un client rimasto
        # offline ripristini accidentalmente l'account quando si ricollega.
        # Nome, password e tutte le altre informazioni dell'account vengono
        # invece rimosse definitivamente.
        tombstone = {
            "doctor_id": clean_id,
            "deleted": True,
            "updated_at": time.time(),
        }
        with self._lock:
            self._accounts[clean_id] = tombstone
            self._save_unlocked()

        self._purge_local_profile_data(clean_id)
        return dict(tombstone)

    def update_account(self, doctor_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            current = self._accounts.get(str(doctor_id).strip())
            if current is None:
                return None
            updated = dict(current)
            if "doctor_name" in values:
                name = str(values.get("doctor_name", "")).strip()
                if name:
                    updated["doctor_name"] = name
            if "queue_prefix" in values:
                updated["queue_prefix"] = self._clean_prefix(values.get("queue_prefix", ""))
            for key in (
                "patient_time_warning_enabled",
                "patient_time_warning_sound_enabled",
            ):
                if key in values:
                    updated[key] = bool(values.get(key))
            if "patient_time_warning_minutes" in values:
                try:
                    updated["patient_time_warning_minutes"] = max(1, min(int(values[key]), 240))
                except (TypeError, ValueError):
                    pass
            for key in ("password_salt", "password_hash", "password_iterations"):
                if key in values:
                    updated[key] = values[key]
            updated["updated_at"] = time.time()
            self._accounts[doctor_id] = updated
            self._save_unlocked()
            return dict(updated)

    def merge_records(self, records: object) -> None:
        if not isinstance(records, list):
            return
        changed = False
        with self._lock:
            for raw in records:
                if not isinstance(raw, dict):
                    continue
                doctor_id = str(raw.get("doctor_id", "")).strip()
                doctor_name = str(raw.get("doctor_name", "")).strip()
                is_deleted = bool(raw.get("deleted", False))
                if not doctor_id or (not doctor_name and not is_deleted):
                    continue
                try:
                    incoming_ts = float(raw.get("updated_at", 0.0) or 0.0)
                except (TypeError, ValueError):
                    incoming_ts = 0.0
                current = self._accounts.get(doctor_id)
                try:
                    current_ts = float(current.get("updated_at", 0.0) or 0.0) if current else -1.0
                except (TypeError, ValueError):
                    current_ts = -1.0
                if current is not None and incoming_ts < current_ts:
                    continue
                self._accounts[doctor_id] = dict(raw)
                changed = True
                if is_deleted:
                    self._purge_local_profile_data(doctor_id)
            if changed:
                self._save_unlocked()

    @staticmethod
    def _purge_local_profile_data(doctor_id: str) -> None:
        """Rimuove dal PC tutti i dati persistenti associati all'account."""
        try:
            from app.history_storage import clear_history_for_doctor
            clear_history_for_doctor(doctor_id)
        except (OSError, TimeoutError, ValueError):
            pass

        try:
            from app.paths import get_config_file, get_turns_file, get_turns_lock_file
            paths = (
                get_config_file(doctor_id),
                get_turns_file(doctor_id),
                get_turns_lock_file(doctor_id),
            )
            for path in paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        except (OSError, ValueError):
            pass

    @staticmethod
    def _public(account: dict[str, Any]) -> dict[str, Any]:
        return {
            "doctor_id": str(account.get("doctor_id", "")),
            "doctor_name": str(account.get("doctor_name", "")).strip(),
        }

    @staticmethod
    def _clean_prefix(value: object) -> str:
        text = str(value or "").strip().upper()
        if not text:
            return ""
        return text[0] if "A" <= text[0] <= "Z" else ""

    def _load(self) -> None:
        ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            self._accounts = {
                str(key): dict(value)
                for key, value in data.items()
                if isinstance(value, dict)
            }

    def _save_unlocked(self) -> None:
        ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = ACCOUNTS_FILE.with_name(f"accounts_{os.getpid()}.tmp")
        temp.write_text(json.dumps(self._accounts, ensure_ascii=False, indent=4), encoding="utf-8")
        os.replace(temp, ACCOUNTS_FILE)
