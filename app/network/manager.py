from __future__ import annotations

import json
import random
import socket
import threading
import time
from typing import Any

from PySide6.QtCore import QObject, Signal


DISCOVERY_PORT = 50555
HEARTBEAT_PORT = 50556

DISCOVERY_MESSAGE = "GESTIONE_TURNI_DISCOVER"
DISCOVERY_RESPONSE = "GESTIONE_TURNI_SERVER"

HEARTBEAT_MESSAGE = "GESTIONE_TURNI_HEARTBEAT"
HEARTBEAT_RESPONSE = "GESTIONE_TURNI_ALIVE"

DISCOVERY_TIMEOUT_SECONDS = 1.5
HEARTBEAT_TIMEOUT_SECONDS = 1.5
HEARTBEAT_INTERVAL_SECONDS = 1.5
MAX_MISSED_HEARTBEATS = 3


class NetworkManager(QObject):
    role_changed = Signal(str)
    status_changed = Signal(str)
    server_address_changed = Signal(str)

    # Invia a SyncManager un messaggio ricevuto dalla rete.
    message_received = Signal(object)

    def __init__(
        self,
        doctor_id: str,
    ) -> None:
        super().__init__()

        self.doctor_id = doctor_id

        self._role = "starting"
        self._server_address = ""

        self._stop_event = threading.Event()
        self._state_lock = threading.RLock()
        self._outbox_lock = threading.Lock()

        self._main_thread: threading.Thread | None = None
        self._discovery_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None

        self._discovery_socket: socket.socket | None = None
        self._heartbeat_socket: socket.socket | None = None

        # Contiene i messaggi preparati da SyncManager
        # che devono essere inviati all'altro computer.
        self._outbox: list[dict[str, Any]] = []

    @property
    def role(self) -> str:
        with self._state_lock:
            return self._role

    @property
    def server_address(self) -> str:
        with self._state_lock:
            return self._server_address

    def start(self) -> None:
        if (
            self._main_thread
            and self._main_thread.is_alive()
        ):
            return

        self._stop_event.clear()

        self._main_thread = threading.Thread(
            target=self._run,
            name="gestione-turni-network-manager",
            daemon=True,
        )
        self._main_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._close_server_sockets()

    def send_message(
        self,
        message: object,
    ) -> None:
        """
        Riceve un messaggio da SyncManager e lo inserisce
        nella coda dei messaggi da inviare.
        """
        if not isinstance(message, dict):
            return

        safe_message = dict(message)

        with self._outbox_lock:
            # Lo stato completo sostituisce eventuali stati
            # completi precedenti non ancora inviati.
            if safe_message.get("type") == "complete_state":
                self._outbox = [
                    queued_message
                    for queued_message in self._outbox
                    if queued_message.get("type")
                    != "complete_state"
                ]

            self._outbox.append(safe_message)

    def _run(self) -> None:
        self.status_changed.emit(
            "Ricerca del server in corso..."
        )

        server_address = self._discover_server()

        if server_address:
            self._run_as_client(server_address)
            return

        self._elect_server()

    def _elect_server(self) -> None:
        if self._stop_event.is_set():
            return

        # Medico 1 ha una leggera precedenza soltanto
        # quando entrambi partono quasi nello stesso momento.
        base_delay = (
            0.25
            if self.doctor_id == "doctor1"
            else 0.85
        )

        time.sleep(
            base_delay
            + random.uniform(0.05, 0.20)
        )

        if self._stop_event.is_set():
            return

        server_address = self._discover_server()

        if server_address:
            self._run_as_client(server_address)
            return

        if self._start_server_services():
            self._set_role(
                "server",
                self._get_local_ip(),
            )

            self.status_changed.emit(
                "Questo computer gestisce temporaneamente "
                "la condivisione."
            )
            return

        self.status_changed.emit(
            "Un altro server è in avvio. Nuova ricerca..."
        )

        time.sleep(0.8)

        server_address = self._discover_server()

        if server_address:
            self._run_as_client(server_address)

        elif not self._stop_event.is_set():
            self._elect_server()

    def _start_server_services(self) -> bool:
        heartbeat_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        try:
            heartbeat_socket.bind(
                ("", HEARTBEAT_PORT)
            )
            heartbeat_socket.listen(8)
            heartbeat_socket.settimeout(1.0)

        except OSError:
            heartbeat_socket.close()
            return False

        discovery_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        try:
            discovery_socket.bind(
                ("", DISCOVERY_PORT)
            )
            discovery_socket.settimeout(1.0)

        except OSError:
            heartbeat_socket.close()
            discovery_socket.close()
            return False

        self._heartbeat_socket = (
            heartbeat_socket
        )
        self._discovery_socket = (
            discovery_socket
        )

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_server_loop,
            name="gestione-turni-heartbeat-server",
            daemon=True,
        )
        self._heartbeat_thread.start()

        self._discovery_thread = threading.Thread(
            target=self._discovery_server_loop,
            name="gestione-turni-discovery-server",
            daemon=True,
        )
        self._discovery_thread.start()

        return True

    def _discovery_server_loop(self) -> None:
        discovery_socket = (
            self._discovery_socket
        )

        if discovery_socket is None:
            return

        while not self._stop_event.is_set():
            try:
                raw_request, sender = (
                    discovery_socket.recvfrom(4096)
                )

            except socket.timeout:
                continue

            except OSError:
                break

            request = self._decode_message(
                raw_request
            )

            if (
                request.get("type")
                != DISCOVERY_MESSAGE
            ):
                continue

            response = {
                "type": DISCOVERY_RESPONSE,
                "doctor_id": self.doctor_id,
                "server_ip": self._get_local_ip(),
                "heartbeat_port": HEARTBEAT_PORT,
            }

            try:
                discovery_socket.sendto(
                    json.dumps(response).encode(
                        "utf-8"
                    ),
                    sender,
                )

            except OSError:
                continue

    def _heartbeat_server_loop(self) -> None:
        heartbeat_socket = (
            self._heartbeat_socket
        )

        if heartbeat_socket is None:
            return

        while not self._stop_event.is_set():
            try:
                connection, _ = (
                    heartbeat_socket.accept()
                )

            except socket.timeout:
                continue

            except OSError:
                break

            with connection:
                connection.settimeout(
                    HEARTBEAT_TIMEOUT_SECONDS
                )

                try:
                    raw_request = (
                        connection.recv(65536)
                    )

                except OSError:
                    continue

                request = self._decode_message(
                    raw_request
                )

                if (
                    request.get("type")
                    != HEARTBEAT_MESSAGE
                ):
                    continue

                incoming_messages = request.get(
                    "messages",
                    [],
                )

                if isinstance(
                    incoming_messages,
                    list,
                ):
                    for message in incoming_messages:
                        if isinstance(message, dict):
                            self.message_received.emit(
                                message
                            )

                response = {
                    "type": HEARTBEAT_RESPONSE,
                    "doctor_id": self.doctor_id,
                    "messages": (
                        self._take_outbox_messages()
                    ),
                }

                try:
                    connection.sendall(
                        json.dumps(response).encode(
                            "utf-8"
                        )
                    )

                except OSError:
                    continue

    def _discover_server(
        self,
    ) -> str | None:
        request = {
            "type": DISCOVERY_MESSAGE,
            "doctor_id": self.doctor_id,
        }

        encoded_request = json.dumps(
            request
        ).encode("utf-8")

        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
            ) as discovery_socket:
                discovery_socket.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_BROADCAST,
                    1,
                )

                discovery_socket.settimeout(
                    DISCOVERY_TIMEOUT_SECONDS
                )

                destinations = [
                    (
                        "255.255.255.255",
                        DISCOVERY_PORT,
                    ),
                    (
                        "127.0.0.1",
                        DISCOVERY_PORT,
                    ),
                ]

                for destination in destinations:
                    try:
                        discovery_socket.sendto(
                            encoded_request,
                            destination,
                        )

                    except OSError:
                        continue

                deadline = (
                    time.monotonic()
                    + DISCOVERY_TIMEOUT_SECONDS
                )

                while (
                    not self._stop_event.is_set()
                    and time.monotonic() < deadline
                ):
                    try:
                        raw_response, sender = (
                            discovery_socket.recvfrom(
                                4096
                            )
                        )

                    except socket.timeout:
                        break

                    except OSError:
                        return None

                    response = (
                        self._decode_message(
                            raw_response
                        )
                    )

                    if (
                        response.get("type")
                        != DISCOVERY_RESPONSE
                    ):
                        continue

                    server_ip = str(
                        response.get("server_ip")
                        or sender[0]
                    )

                    if sender[0] == "127.0.0.1":
                        return "127.0.0.1"

                    return server_ip

        except OSError:
            return None

        return None

    def _run_as_client(
        self,
        server_address: str,
    ) -> None:
        self._set_role(
            "client",
            server_address,
        )

        self.status_changed.emit(
            "Connesso al computer che gestisce "
            "la condivisione."
        )

        missed_heartbeats = 0

        while not self._stop_event.is_set():
            response = self._exchange_with_server(
                server_address
            )

            if response is not None:
                if missed_heartbeats:
                    self.status_changed.emit(
                        "Connessione al server ripristinata."
                    )

                missed_heartbeats = 0

                incoming_messages = response.get(
                    "messages",
                    [],
                )

                if isinstance(
                    incoming_messages,
                    list,
                ):
                    for message in incoming_messages:
                        if isinstance(message, dict):
                            self.message_received.emit(
                                message
                            )

            else:
                missed_heartbeats += 1

                self.status_changed.emit(
                    "Server non raggiungibile: "
                    f"tentativo {missed_heartbeats}/"
                    f"{MAX_MISSED_HEARTBEATS}"
                )

            if (
                missed_heartbeats
                >= MAX_MISSED_HEARTBEATS
            ):
                self.status_changed.emit(
                    "Server disconnesso. "
                    "Passaggio automatico in corso..."
                )

                replacement_server = (
                    self._discover_server()
                )

                if replacement_server:
                    server_address = (
                        replacement_server
                    )

                    self._set_role(
                        "client",
                        server_address,
                    )

                    missed_heartbeats = 0
                    continue

                self._elect_server()
                return

            self._stop_event.wait(
                HEARTBEAT_INTERVAL_SECONDS
            )

    def _exchange_with_server(
        self,
        server_address: str,
    ) -> dict[str, Any] | None:
        request = {
            "type": HEARTBEAT_MESSAGE,
            "doctor_id": self.doctor_id,
            "messages": (
                self._take_outbox_messages()
            ),
        }

        try:
            with socket.create_connection(
                (
                    server_address,
                    HEARTBEAT_PORT,
                ),
                timeout=(
                    HEARTBEAT_TIMEOUT_SECONDS
                ),
            ) as connection:
                connection.settimeout(
                    HEARTBEAT_TIMEOUT_SECONDS
                )

                connection.sendall(
                    json.dumps(request).encode(
                        "utf-8"
                    )
                )

                raw_response = (
                    connection.recv(65536)
                )

                response = (
                    self._decode_message(
                        raw_response
                    )
                )

                if (
                    response.get("type")
                    != HEARTBEAT_RESPONSE
                ):
                    return None

                return response

        except OSError:
            # Se l'invio fallisce, rimettiamo i messaggi
            # nella coda per il tentativo successivo.
            outgoing_messages = request.get(
                "messages",
                [],
            )

            if isinstance(
                outgoing_messages,
                list,
            ):
                self._restore_outbox_messages(
                    outgoing_messages
                )

            return None

    def _take_outbox_messages(
        self,
    ) -> list[dict[str, Any]]:
        with self._outbox_lock:
            messages = list(self._outbox)
            self._outbox.clear()

        return messages

    def _restore_outbox_messages(
        self,
        messages: list[Any],
    ) -> None:
        valid_messages = [
            dict(message)
            for message in messages
            if isinstance(message, dict)
        ]

        if not valid_messages:
            return

        with self._outbox_lock:
            self._outbox = (
                valid_messages
                + self._outbox
            )

    def _set_role(
        self,
        role: str,
        server_address: str,
    ) -> None:
        with self._state_lock:
            self._role = role
            self._server_address = (
                server_address
            )

        self.role_changed.emit(role)
        self.server_address_changed.emit(
            server_address
        )

    def _close_server_sockets(self) -> None:
        discovery_socket = (
            self._discovery_socket
        )
        heartbeat_socket = (
            self._heartbeat_socket
        )

        self._discovery_socket = None
        self._heartbeat_socket = None

        for current_socket in (
            discovery_socket,
            heartbeat_socket,
        ):
            if current_socket is None:
                continue

            try:
                current_socket.close()

            except OSError:
                pass

    @staticmethod
    def _decode_message(
        raw_message: bytes,
    ) -> dict[str, Any]:
        try:
            decoded = json.loads(
                raw_message.decode("utf-8")
            )

            if isinstance(decoded, dict):
                return decoded

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            pass

        return {}

    @staticmethod
    def _get_local_ip() -> str:
        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
            ) as ip_socket:
                ip_socket.connect(
                    ("8.8.8.8", 80)
                )

                return str(
                    ip_socket.getsockname()[0]
                )

        except OSError:
            return "127.0.0.1"