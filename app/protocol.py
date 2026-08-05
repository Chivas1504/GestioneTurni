from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import Any


PROTOCOL_NAME = "gestione_turni"
PROTOCOL_VERSION = 1

DOCTOR_IDS = (
    "doctor1",
    "doctor2",
)


class MessageType(str, Enum):
    """
    Tipi di messaggio applicativi supportati.
    """

    DOCTOR_UPDATE = "doctor_update"
    COMPLETE_STATE = "complete_state"
    REQUEST_STATE = "request_state"
    PEER_DISCONNECT = "peer_disconnect"


def create_doctor_update(
    doctor_state: dict[str, Any],
) -> dict[str, Any]:
    normalised_doctor = normalise_doctor_state(
        doctor_state
    )

    return create_message(
        MessageType.DOCTOR_UPDATE,
        {
            "doctor": normalised_doctor,
        },
    )


def create_complete_state(
    state: dict[str, Any],
) -> dict[str, Any]:
    normalised_state = normalise_complete_state(
        state
    )

    return create_message(
        MessageType.COMPLETE_STATE,
        {
            "state": normalised_state,
        },
    )


def create_state_request(
    doctor_id: str,
) -> dict[str, Any]:
    validate_doctor_id(doctor_id)

    return create_message(
        MessageType.REQUEST_STATE,
        {
            "doctor_id": doctor_id,
        },
    )


def create_peer_disconnect(
    doctor_id: str,
) -> dict[str, Any]:
    validate_doctor_id(doctor_id)

    return create_message(
        MessageType.PEER_DISCONNECT,
        {
            "doctor_id": doctor_id,
        },
    )


def create_message(
    message_type: MessageType,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        message_type,
        MessageType,
    ):
        raise ValueError(
            "Tipo di messaggio non valido."
        )

    if not isinstance(payload, dict):
        raise ValueError(
            "Il payload deve essere un dizionario."
        )

    return {
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "type": message_type.value,
        "payload": deepcopy(payload),
    }


def validate_message(
    message: object,
) -> bool:
    if not isinstance(message, dict):
        return False

    if message.get("protocol") != PROTOCOL_NAME:
        return False

    if message.get("version") != PROTOCOL_VERSION:
        return False

    raw_type = message.get("type")

    try:
        MessageType(str(raw_type))
    except ValueError:
        return False

    payload = message.get("payload")

    if not isinstance(payload, dict):
        return False

    return True


def get_message_type(
    message: object,
) -> MessageType | None:
    if not validate_message(message):
        return None

    assert isinstance(message, dict)

    try:
        return MessageType(
            str(message["type"])
        )
    except ValueError:
        return None


def get_payload(
    message: object,
) -> dict[str, Any] | None:
    if not validate_message(message):
        return None

    assert isinstance(message, dict)

    payload = message.get("payload")

    if not isinstance(payload, dict):
        return None

    return deepcopy(payload)


def normalise_complete_state(
    state: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not isinstance(state, dict):
        raise ValueError(
            "Lo stato completo deve essere un dizionario."
        )

    result: dict[str, dict[str, Any]] = {}

    for doctor_id in DOCTOR_IDS:
        raw_doctor = state.get(doctor_id)

        if isinstance(raw_doctor, dict):
            result[doctor_id] = (
                normalise_doctor_state(
                    raw_doctor,
                    expected_doctor_id=doctor_id,
                )
            )
        else:
            result[doctor_id] = (
                create_empty_doctor_state(
                    doctor_id
                )
            )

    return result


def normalise_doctor_state(
    doctor_state: dict[str, Any],
    *,
    expected_doctor_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(doctor_state, dict):
        raise ValueError(
            "Lo stato del medico deve essere un dizionario."
        )

    doctor_id = str(
        expected_doctor_id
        or doctor_state.get("doctor_id", "")
    )

    validate_doctor_id(doctor_id)

    doctor_name = str(
        doctor_state.get(
            "doctor_name",
            "",
        )
    ).strip()

    try:
        number = max(
            0,
            int(
                doctor_state.get(
                    "number",
                    0,
                )
            ),
        )
    except (TypeError, ValueError):
        number = 0

    try:
        updated_at = max(
            0.0,
            float(
                doctor_state.get(
                    "updated_at",
                    0.0,
                )
            ),
        )
    except (TypeError, ValueError):
        updated_at = 0.0

    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "number": number,
        "queue_active": bool(
            doctor_state.get(
                "queue_active",
                False,
            )
        ),
        "online": bool(
            doctor_state.get(
                "online",
                False,
            )
        ),
        "updated_at": updated_at,
    }


def create_empty_doctor_state(
    doctor_id: str,
) -> dict[str, Any]:
    validate_doctor_id(doctor_id)

    return {
        "doctor_id": doctor_id,
        "doctor_name": "",
        "number": 0,
        "queue_active": False,
        "online": False,
        "updated_at": 0.0,
    }


def validate_doctor_id(
    doctor_id: str,
) -> None:
    if doctor_id not in DOCTOR_IDS:
        raise ValueError(
            f"Identificativo medico non valido: "
            f"{doctor_id}"
        )