from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import Any

PROTOCOL_NAME = "gestione_turni"
PROTOCOL_VERSION = 2


class MessageType(str, Enum):
    DOCTOR_UPDATE = "doctor_update"
    COMPLETE_STATE = "complete_state"
    REQUEST_STATE = "request_state"
    PEER_DISCONNECT = "peer_disconnect"


def validate_doctor_id(doctor_id: str) -> None:
    if not str(doctor_id).strip():
        raise ValueError("Identificativo medico non valido.")


def create_message(message_type: MessageType, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "type": message_type.value,
        "payload": deepcopy(payload),
    }


def create_doctor_update(doctor_state: dict[str, Any]) -> dict[str, Any]:
    return create_message(MessageType.DOCTOR_UPDATE, {"doctor": normalise_doctor_state(doctor_state)})


def create_complete_state(state: dict[str, Any]) -> dict[str, Any]:
    return create_message(MessageType.COMPLETE_STATE, {"state": normalise_complete_state(state)})


def create_state_request(doctor_id: str) -> dict[str, Any]:
    validate_doctor_id(doctor_id)
    return create_message(MessageType.REQUEST_STATE, {"doctor_id": doctor_id})


def create_peer_disconnect(doctor_id: str) -> dict[str, Any]:
    validate_doctor_id(doctor_id)
    return create_message(MessageType.PEER_DISCONNECT, {"doctor_id": doctor_id})


def validate_message(message: object) -> bool:
    return bool(
        isinstance(message, dict)
        and message.get("protocol") == PROTOCOL_NAME
        and int(message.get("version", 0) or 0) == PROTOCOL_VERSION
        and isinstance(message.get("type"), str)
        and isinstance(message.get("payload"), dict)
    )


def get_message_type(message: object) -> MessageType | None:
    if not validate_message(message):
        return None
    try:
        return MessageType(str(message["type"]))  # type: ignore[index]
    except ValueError:
        return None


def get_payload(message: object) -> dict[str, Any] | None:
    if not validate_message(message):
        return None
    payload = message.get("payload")  # type: ignore[union-attr]
    return deepcopy(payload) if isinstance(payload, dict) else None


def normalise_complete_state(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(state, dict):
        raise ValueError("Lo stato completo deve essere un dizionario.")
    result: dict[str, dict[str, Any]] = {}
    for doctor_id, raw in state.items():
        doctor_id = str(doctor_id).strip()
        if not doctor_id or not isinstance(raw, dict):
            continue
        result[doctor_id] = normalise_doctor_state(raw, expected_doctor_id=doctor_id)
    return result


def normalise_doctor_state(doctor_state: dict[str, Any], *, expected_doctor_id: str | None = None) -> dict[str, Any]:
    if not isinstance(doctor_state, dict):
        raise ValueError("Lo stato del medico deve essere un dizionario.")
    doctor_id = str(expected_doctor_id or doctor_state.get("doctor_id", "")).strip()
    validate_doctor_id(doctor_id)
    try:
        number = max(0, int(doctor_state.get("number", 0)))
    except (TypeError, ValueError):
        number = 0
    try:
        updated_at = max(0.0, float(doctor_state.get("updated_at", 0.0)))
    except (TypeError, ValueError):
        updated_at = 0.0
    patient_started_at = _normalise_optional_timestamp(doctor_state.get("patient_started_at"))
    patient_paused_at = _normalise_optional_timestamp(doctor_state.get("patient_paused_at"))
    patient_number = _normalise_optional_number(doctor_state.get("patient_number"))
    patient_prefix = clean_queue_prefix(doctor_state.get("patient_prefix", ""))

    # Un timer senza paziente/avvio non è valido. In quel caso puliamo anche
    # l'eventuale stato di pausa ricevuto dalla rete.
    if patient_started_at is None or patient_number is None:
        patient_started_at = None
        patient_paused_at = None
        patient_number = None
        patient_prefix = ""

    return {
        "doctor_id": doctor_id,
        "doctor_name": str(doctor_state.get("doctor_name", "")).strip(),
        "queue_prefix": clean_queue_prefix(doctor_state.get("queue_prefix", "")),
        "number": number,
        "queue_active": bool(doctor_state.get("queue_active", False)),
        "patient_started_at": patient_started_at,
        "patient_number": patient_number,
        "patient_prefix": patient_prefix,
        "patient_paused_at": patient_paused_at,
        "online": bool(doctor_state.get("online", True)),
        "updated_at": updated_at,
    }


def create_empty_doctor_state(doctor_id: str) -> dict[str, Any]:
    validate_doctor_id(doctor_id)
    return {
        "doctor_id": doctor_id, "doctor_name": "", "queue_prefix": "",
        "number": 0, "queue_active": False, "patient_started_at": None,
        "patient_number": None, "patient_prefix": "", "patient_paused_at": None,
        "online": False, "updated_at": 0.0,
    }


def _normalise_optional_timestamp(value: object) -> float | None:
    if value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None
    return timestamp if timestamp > 0 else None


def _normalise_optional_number(value: object) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def clean_queue_prefix(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    return text[0] if "A" <= text[0] <= "Z" else ""
