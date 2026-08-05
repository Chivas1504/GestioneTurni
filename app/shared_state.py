from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any

from PySide6.QtCore import QObject, Signal


DOCTOR_IDS = ("doctor1", "doctor2")


class SharedState(QObject):
    """
    Mantiene una copia coerente dello stato dei due medici.

    Questo componente non comunica direttamente sulla rete:
    - la GUI aggiorna lo stato locale;
    - NetworkManager legge e invia lo stato;
    - NetworkManager applica gli aggiornamenti ricevuti;
    - la GUI riceve il segnale state_changed.
    """

    state_changed = Signal(object)
    local_state_changed = Signal(object)

    def __init__(
        self,
        local_doctor_id: str,
        local_doctor_name: str,
        local_number: int = 0,
        local_queue_active: bool = False,
    ) -> None:
        super().__init__()

        if local_doctor_id not in DOCTOR_IDS:
            raise ValueError(
                f"Identificativo medico non valido: "
                f"{local_doctor_id}"
            )

        self.local_doctor_id = local_doctor_id
        self._lock = threading.RLock()

        self._state: dict[str, dict[str, Any]] = {
            "doctor1": self._empty_doctor_state("doctor1"),
            "doctor2": self._empty_doctor_state("doctor2"),
        }

        self._state[local_doctor_id] = self._normalise_doctor_state(
            {
                "doctor_id": local_doctor_id,
                "doctor_name": local_doctor_name,
                "number": local_number,
                "queue_active": local_queue_active,
                "online": True,
                "updated_at": time.time(),
            },
            expected_doctor_id=local_doctor_id,
        )

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Restituisce una copia completa dello stato condiviso."""
        with self._lock:
            return deepcopy(self._state)

    def get_doctor(
        self,
        doctor_id: str,
    ) -> dict[str, Any]:
        """Restituisce una copia dello stato di un medico."""
        self._validate_doctor_id(doctor_id)

        with self._lock:
            return deepcopy(self._state[doctor_id])

    def get_local_doctor(self) -> dict[str, Any]:
        """Restituisce lo stato del medico di questo computer."""
        return self.get_doctor(self.local_doctor_id)

    def update_local(
        self,
        *,
        doctor_name: str | None = None,
        number: int | None = None,
        queue_active: bool | None = None,
        online: bool | None = None,
    ) -> None:
        """
        Aggiorna lo stato del medico locale.

        Emette:
        - local_state_changed: serve alla rete per inviare l’update;
        - state_changed: serve alla GUI e agli altri componenti.
        """
        with self._lock:
            current = self._state[self.local_doctor_id].copy()

            if doctor_name is not None:
                clean_name = str(doctor_name).strip()

                if not clean_name:
                    raise ValueError(
                        "Il nome del medico non può essere vuoto."
                    )

                current["doctor_name"] = clean_name

            if number is not None:
                current["number"] = max(0, int(number))

            if queue_active is not None:
                current["queue_active"] = bool(queue_active)

            if online is not None:
                current["online"] = bool(online)

            current["updated_at"] = time.time()

            self._state[self.local_doctor_id] = (
                self._normalise_doctor_state(
                    current,
                    expected_doctor_id=self.local_doctor_id,
                )
            )

            local_copy = deepcopy(
                self._state[self.local_doctor_id]
            )
            complete_copy = deepcopy(self._state)

        self.local_state_changed.emit(local_copy)
        self.state_changed.emit(complete_copy)

    def apply_remote_doctor(
        self,
        doctor_state: dict[str, Any],
    ) -> None:
        """
        Applica lo stato ricevuto dalla rete per un singolo medico.

        Non sovrascrive il medico locale con dati più vecchi.
        """
        doctor_id = str(
            doctor_state.get("doctor_id", "")
        )

        self._validate_doctor_id(doctor_id)

        normalised = self._normalise_doctor_state(
            doctor_state,
            expected_doctor_id=doctor_id,
        )

        with self._lock:
            current = self._state[doctor_id]

            current_timestamp = float(
                current.get("updated_at", 0.0)
            )
            incoming_timestamp = float(
                normalised.get("updated_at", 0.0)
            )

            if incoming_timestamp < current_timestamp:
                return

            self._state[doctor_id] = normalised
            complete_copy = deepcopy(self._state)

        self.state_changed.emit(complete_copy)

    def apply_complete_state(
        self,
        complete_state: dict[str, Any],
    ) -> None:
        """
        Applica una copia completa ricevuta dal Server.

        Per ogni medico viene mantenuta la versione con
        updated_at più recente.
        """
        changed = False

        with self._lock:
            for doctor_id in DOCTOR_IDS:
                raw_doctor = complete_state.get(doctor_id)

                if not isinstance(raw_doctor, dict):
                    continue

                normalised = self._normalise_doctor_state(
                    raw_doctor,
                    expected_doctor_id=doctor_id,
                )

                current_timestamp = float(
                    self._state[doctor_id].get(
                        "updated_at",
                        0.0,
                    )
                )
                incoming_timestamp = float(
                    normalised.get("updated_at", 0.0)
                )

                if incoming_timestamp < current_timestamp:
                    continue

                if normalised != self._state[doctor_id]:
                    self._state[doctor_id] = normalised
                    changed = True

            complete_copy = deepcopy(self._state)

        if changed:
            self.state_changed.emit(complete_copy)

    def mark_doctor_offline(
        self,
        doctor_id: str,
    ) -> None:
        """Segna un medico come non connesso."""
        self._validate_doctor_id(doctor_id)

        with self._lock:
            current = self._state[doctor_id].copy()

            if not current["online"]:
                return

            current["online"] = False
            current["updated_at"] = time.time()

            self._state[doctor_id] = (
                self._normalise_doctor_state(
                    current,
                    expected_doctor_id=doctor_id,
                )
            )

            complete_copy = deepcopy(self._state)

        self.state_changed.emit(complete_copy)

    def mark_local_offline(self) -> None:
        """Segna come offline il medico di questo computer."""
        self.update_local(online=False)

    @staticmethod
    def _empty_doctor_state(
        doctor_id: str,
    ) -> dict[str, Any]:
        return {
            "doctor_id": doctor_id,
            "doctor_name": "",
            "number": 0,
            "queue_active": False,
            "online": False,
            "updated_at": 0.0,
        }

    @staticmethod
    def _normalise_doctor_state(
        doctor_state: dict[str, Any],
        *,
        expected_doctor_id: str,
    ) -> dict[str, Any]:
        doctor_name = str(
            doctor_state.get("doctor_name", "")
        ).strip()

        try:
            number = max(
                0,
                int(doctor_state.get("number", 0)),
            )
        except (TypeError, ValueError):
            number = 0

        try:
            updated_at = float(
                doctor_state.get("updated_at", 0.0)
            )
        except (TypeError, ValueError):
            updated_at = 0.0

        return {
            "doctor_id": expected_doctor_id,
            "doctor_name": doctor_name,
            "number": number,
            "queue_active": bool(
                doctor_state.get(
                    "queue_active",
                    False,
                )
            ),
            "online": bool(
                doctor_state.get("online", False)
            ),
            "updated_at": max(0.0, updated_at),
        }

    @staticmethod
    def _validate_doctor_id(
        doctor_id: str,
    ) -> None:
        if doctor_id not in DOCTOR_IDS:
            raise ValueError(
                f"Identificativo medico non valido: "
                f"{doctor_id}"
            )