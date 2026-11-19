"""Bounded JSON stream transport for automatic LAN sharing, without pairing.

Reads complete JSON objects across TCP fragments, including the original app's
messages without a final newline. New messages end in a newline for clarity.
"""
from __future__ import annotations

import json
import socket
from typing import Any

MAX_MESSAGE_BYTES = 4 * 1024 * 1024


def send_json(connection: socket.socket, payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(raw) + 1 > MAX_MESSAGE_BYTES:
        raise ValueError("Messaggio di rete troppo grande.")
    connection.sendall(raw + b"\n")


def _reject_constant(value: str) -> None:
    raise ValueError("Valore JSON non valido: " + value)


def receive_json(connection: socket.socket) -> dict[str, Any]:
    decoder = json.JSONDecoder(parse_constant=_reject_constant)
    raw = bytearray()
    while True:
        chunk = connection.recv(min(65536, MAX_MESSAGE_BYTES + 1 - len(raw)))
        if not chunk:
            raise ConnectionError("Messaggio di rete incompleto.")
        raw.extend(chunk)
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ValueError("Messaggio di rete troppo grande.")
        try:
            text = raw.decode("utf-8").lstrip()
        except UnicodeDecodeError as exc:
            if exc.reason == "unexpected end of data":
                continue
            raise ValueError("Codifica del messaggio non valida.") from exc
        if not text:
            continue
        if not text.startswith("{"):
            raise ValueError("Il messaggio deve essere un oggetto JSON.")
        try:
            result, end = decoder.raw_decode(text)
        except json.JSONDecodeError:
            continue
        except RecursionError as exc:
            raise ValueError("Messaggio JSON troppo complesso.") from exc
        if text[end:].strip() or not isinstance(result, dict):
            raise ValueError("Messaggio di rete non valido.")
        return result


def client_exchange(connection: socket.socket, request: dict[str, Any]) -> dict[str, Any]:
    send_json(connection, request)
    return receive_json(connection)
