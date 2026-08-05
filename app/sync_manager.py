from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from app.protocol import (
    MessageType,
    create_complete_state,
    create_doctor_update,
    create_peer_disconnect,
    create_state_request,
    get_message_type,
    get_payload,
)
from app.shared_state import SharedState


class SyncManager(QObject):

    outbound_message = Signal(object)
    sync_status_changed = Signal(str)

    def __init__(
        self,
        shared_state: SharedState,
    ) -> None:
        super().__init__()

        self.shared_state = shared_state
        self._network_role = "starting"

        self.shared_state.local_state_changed.connect(
            self._on_local_state_changed
        )

    @property
    def network_role(self) -> str:
        return self._network_role

    def set_network_role(
        self,
        role: str,
    ) -> None:
        if role not in {
            "starting",
            "server",
            "client",
        }:
            role = "starting"

        if role == self._network_role:
            return

        self._network_role = role

        if role == "server":
            self.sync_status_changed.emit(
                "Sincronizzazione: stato condiviso "
                "gestito da questo computer."
            )


            self._emit_complete_state()

        elif role == "client":
            self.sync_status_changed.emit(
                "Sincronizzazione: collegato al Server."
            )


            self._emit_local_state()


            self.request_full_synchronisation()

        else:
            self.sync_status_changed.emit(
                "Sincronizzazione: inizializzazione..."
            )

    def handle_network_message(
        self,
        message: object,
    ) -> None:
        message_type = get_message_type(message)
        payload = get_payload(message)

        if message_type is None or payload is None:
            self.sync_status_changed.emit(
                "Sincronizzazione: messaggio non valido ignorato."
            )
            return

        if message_type == MessageType.DOCTOR_UPDATE:
            self._handle_doctor_update(payload)

        elif message_type == MessageType.COMPLETE_STATE:
            self._handle_complete_state(payload)

        elif message_type == MessageType.REQUEST_STATE:
            self._handle_state_request()

        elif message_type == MessageType.PEER_DISCONNECT:
            self._handle_peer_disconnect(payload)

    def request_full_synchronisation(self) -> None:
        if self._network_role != "client":
            return

        message = create_state_request(
            self.shared_state.local_doctor_id
        )

        self.outbound_message.emit(message)

    def notify_local_disconnect(self) -> None:
        if self._network_role not in {
            "server",
            "client",
        }:
            return

        message = create_peer_disconnect(
            self.shared_state.local_doctor_id
        )

        self.outbound_message.emit(message)

    def _on_local_state_changed(
        self,
        local_doctor_state: object,
    ) -> None:
        if not isinstance(
            local_doctor_state,
            dict,
        ):
            return

        try:
            message = create_doctor_update(
                local_doctor_state
            )
        except ValueError:
            self.sync_status_changed.emit(
                "Sincronizzazione: stato locale non valido."
            )
            return

        if self._network_role == "client":
            self.outbound_message.emit(message)

        elif self._network_role == "server":


            self._emit_complete_state()

    def _handle_doctor_update(
        self,
        payload: dict[str, Any],
    ) -> None:
        doctor_state = payload.get("doctor")

        if not isinstance(doctor_state, dict):
            return

        try:
            self.shared_state.apply_remote_doctor(
                doctor_state
            )
        except ValueError:
            self.sync_status_changed.emit(
                "Sincronizzazione: aggiornamento medico "
                "non valido ignorato."
            )
            return

        if self._network_role == "server":
            self._emit_complete_state()

    def _handle_complete_state(
        self,
        payload: dict[str, Any],
    ) -> None:
        complete_state = payload.get("state")

        if not isinstance(complete_state, dict):
            return

        try:
            self.shared_state.apply_complete_state(
                complete_state
            )
        except ValueError:
            self.sync_status_changed.emit(
                "Sincronizzazione: stato completo "
                "non valido ignorato."
            )
            return

        self.sync_status_changed.emit(
            "Sincronizzazione completata."
        )

    def _handle_state_request(self) -> None:
        if self._network_role != "server":
            return

        self._emit_complete_state()

    def _handle_peer_disconnect(
        self,
        payload: dict[str, Any],
    ) -> None:
        doctor_id = str(
            payload.get("doctor_id", "")
        )

        if doctor_id not in {
            "doctor1",
            "doctor2",
        }:
            return

        self.shared_state.mark_doctor_offline(
            doctor_id
        )

        if self._network_role == "server":
            self._emit_complete_state()

    def _emit_local_state(self) -> None:
        local_state = (
            self.shared_state.get_local_doctor()
        )

        try:
            message = create_doctor_update(
                local_state
            )
        except ValueError:
            return

        self.outbound_message.emit(message)

    def _emit_complete_state(self) -> None:
        complete_state = (
            self.shared_state.get_all()
        )

        try:
            message = create_complete_state(
                complete_state
            )
        except ValueError:
            return

        self.outbound_message.emit(message)
