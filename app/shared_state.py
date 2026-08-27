from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any
from PySide6.QtCore import QObject, Signal
from app.protocol import normalise_doctor_state, validate_doctor_id


class SharedState(QObject):
    state_changed = Signal(object)
    local_state_changed = Signal(object)

    def __init__(self, local_doctor_id: str, local_doctor_name: str, local_queue_prefix: str = "", local_number: int = 0, local_queue_active: bool = False) -> None:
        super().__init__()
        validate_doctor_id(local_doctor_id)
        self.local_doctor_id = local_doctor_id
        self._lock = threading.RLock()
        self._state: dict[str, dict[str, Any]] = {}
        self._state[local_doctor_id] = normalise_doctor_state({
            "doctor_id": local_doctor_id,
            "doctor_name": local_doctor_name,
            "queue_prefix": local_queue_prefix,
            "number": local_number,
            "queue_active": local_queue_active,
            "online": True,
            "updated_at": time.time(),
        })

    def get_all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return deepcopy(self._state)

    def get_doctor(self, doctor_id: str) -> dict[str, Any]:
        validate_doctor_id(doctor_id)
        with self._lock:
            return deepcopy(self._state.get(doctor_id, {
                "doctor_id": doctor_id, "doctor_name": "", "queue_prefix": "", "number": 0,
                "queue_active": False, "online": False, "updated_at": 0.0,
            }))

    def get_local_doctor(self) -> dict[str, Any]:
        return self.get_doctor(self.local_doctor_id)

    def update_local(self, *, doctor_name: str | None = None, queue_prefix: str | None = None, number: int | None = None, queue_active: bool | None = None, online: bool | None = None) -> None:
        with self._lock:
            current = self.get_doctor(self.local_doctor_id)
            if doctor_name is not None:
                clean = str(doctor_name).strip()
                if not clean:
                    raise ValueError("Il nome del medico non può essere vuoto.")
                current["doctor_name"] = clean
            if queue_prefix is not None:
                current["queue_prefix"] = queue_prefix
            if number is not None:
                current["number"] = max(0, int(number))
            if queue_active is not None:
                current["queue_active"] = bool(queue_active)
            if online is not None:
                current["online"] = bool(online)
            current["updated_at"] = time.time()
            self._state[self.local_doctor_id] = normalise_doctor_state(current, expected_doctor_id=self.local_doctor_id)
            local_copy = deepcopy(self._state[self.local_doctor_id])
            all_copy = deepcopy(self._state)
        self.local_state_changed.emit(local_copy)
        self.state_changed.emit(all_copy)

    def apply_remote_doctor(self, doctor_state: dict[str, Any]) -> None:
        doctor_id = str(doctor_state.get("doctor_id", "")).strip()
        validate_doctor_id(doctor_id)
        incoming = normalise_doctor_state(doctor_state, expected_doctor_id=doctor_id)
        with self._lock:
            current = self._state.get(doctor_id)
            if current is not None and float(incoming.get("updated_at", 0.0)) < float(current.get("updated_at", 0.0)):
                return
            self._state[doctor_id] = incoming
            all_copy = deepcopy(self._state)
        self.state_changed.emit(all_copy)

    def apply_complete_state(self, complete_state: dict[str, Any]) -> None:
        changed = False
        with self._lock:
            for doctor_id, raw in complete_state.items():
                if not isinstance(raw, dict):
                    continue
                doctor_id = str(doctor_id).strip()
                if not doctor_id:
                    continue
                incoming = normalise_doctor_state(raw, expected_doctor_id=doctor_id)
                current = self._state.get(doctor_id)
                if current is not None and float(incoming.get("updated_at", 0.0)) < float(current.get("updated_at", 0.0)):
                    continue
                if incoming != current:
                    self._state[doctor_id] = incoming
                    changed = True
            all_copy = deepcopy(self._state)
        if changed:
            self.state_changed.emit(all_copy)

    def remove_doctor(self, doctor_id: str) -> None:
        doctor_id = str(doctor_id).strip()
        if not doctor_id:
            return
        with self._lock:
            if doctor_id not in self._state:
                return
            del self._state[doctor_id]
            all_copy = deepcopy(self._state)
        self.state_changed.emit(all_copy)

    def mark_doctor_offline(self, doctor_id: str) -> None:
        # Un account può essere aperto da più PC contemporaneamente: la chiusura
        # di una singola sessione non rende offline l'account condiviso.
        return

    def mark_local_offline(self) -> None:
        return
