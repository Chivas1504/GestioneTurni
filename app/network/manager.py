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
SERVER_RECONCILE_INTERVAL_SECONDS = 2.5


class NetworkManager(QObject):
    role_changed = Signal(str)
    status_changed = Signal(str)
    server_address_changed = Signal(str)


    message_received = Signal(object)
    account_records_received = Signal(object)

    def __init__(
        self,
        doctor_id: str,
    ) -> None:
        super().__init__()

        self.doctor_id = doctor_id

        self._role = "starting"
        self._server_address = ""

        self._stop_event = threading.Event()
        self._outbox_event = threading.Event()
        self._state_lock = threading.RLock()
        self._outbox_lock = threading.Lock()

        self._main_thread: threading.Thread | None = None
        self._discovery_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None

        self._discovery_socket: socket.socket | None = None
        self._heartbeat_socket: socket.socket | None = None


        self._outbox: list[dict[str, Any]] = []
        self._peer_addresses: set[str] = set()
        self._latest_complete_state: dict[str, Any] | None = None
        self._account_store = None

    def set_account_store(self, account_store: object) -> None:
        self._account_store = account_store

    def publish_account_record(self, record: dict[str, Any]) -> None:
        if not isinstance(record, dict):
            return
        if self.role == "server":
            store = self._account_store
            if store is not None and hasattr(store, "merge_records"):
                store.merge_records([record])
            return
        self.send_message({"type": "__account_record", "record": dict(record)})

    @property
    def role(self) -> str:
        with self._state_lock:
            return self._role

    @property
    def server_address(self) -> str:
        with self._state_lock:
            return self._server_address

    @property
    def local_address(self) -> str:
        return self._get_local_ip()

    @property
    def peer_addresses(self) -> list[str]:
        with self._state_lock:
            return sorted(self._peer_addresses)

    def start(self) -> None:
        if (
            self._main_thread
            and self._main_thread.is_alive()
        ):
            return

        self._stop_event.clear()
        self._outbox_event.clear()

        self._main_thread = threading.Thread(
            target=self._run,
            name="gestione-turni-network-manager",
            daemon=True,
        )
        self._main_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._outbox_event.set()
        self._close_server_sockets()

    def send_message(
        self,
        message: object,
    ) -> None:
        if not isinstance(message, dict):
            return

        safe_message = dict(message)

        if safe_message.get("type") == "complete_state" and self.role == "server":
            with self._outbox_lock:
                self._latest_complete_state = safe_message
            return

        with self._outbox_lock:
            if safe_message.get("type") == "complete_state":
                self._outbox = [m for m in self._outbox if m.get("type") != "complete_state"]
            self._outbox.append(safe_message)

        # Se questo PC è il Client, risveglia subito il ciclo di
        # comunicazione. L'aggiornamento non deve attendere il
        # successivo heartbeat periodico.
        self._outbox_event.set()

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


        base_delay = random.uniform(0.25, 0.85)

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

            # Anche se due PC diventano Server quasi nello stesso istante,
            # convergono automaticamente su un unico Server canonico.
            self._run_server_reconciliation()
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
                connection, sender = (
                    heartbeat_socket.accept()
                )

            except socket.timeout:
                continue

            except OSError:
                break

            peer_address = str(sender[0]).strip()
            if peer_address and peer_address != "127.0.0.1":
                with self._state_lock:
                    self._peer_addresses.add(peer_address)

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

                request_type = request.get("type")
                if request_type in {"GESTIONE_TURNI_ACCOUNTS_LIST", "GESTIONE_TURNI_ACCOUNT_AUTH", "GESTIONE_TURNI_ACCOUNT_CREATE", "GESTIONE_TURNI_ACCOUNT_DELETE"}:
                    response = self._handle_account_rpc(request)
                    try:
                        connection.sendall(json.dumps(response).encode("utf-8"))
                    except OSError:
                        pass
                    continue

                if request_type != HEARTBEAT_MESSAGE:
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
                        if not isinstance(message, dict):
                            continue
                        if message.get("type") == "__account_record":
                            store = self._account_store
                            if store is not None and hasattr(store, "merge_records"):
                                record = message.get("record")
                                store.merge_records([record])
                                self.account_records_received.emit([record])
                            continue
                        self.message_received.emit(message)

                with self._outbox_lock:
                    latest = dict(self._latest_complete_state) if self._latest_complete_state else None
                records = []
                store = self._account_store
                if store is not None and hasattr(store, "export_records"):
                    records = store.export_records()
                response = {
                    "type": HEARTBEAT_RESPONSE,
                    "doctor_id": self.doctor_id,
                    "messages": [latest] if latest else [],
                    "account_records": records,
                }

                try:
                    connection.sendall(
                        json.dumps(response).encode(
                            "utf-8"
                        )
                    )

                except OSError:
                    continue

    def _handle_account_rpc(self, request: dict[str, Any]) -> dict[str, Any]:
        store = self._account_store
        request_type = str(request.get("type", ""))
        if store is None:
            return {"type": request_type + "_RESPONSE", "ok": False, "error": "Archivio account non disponibile."}
        try:
            if request_type == "GESTIONE_TURNI_ACCOUNTS_LIST":
                return {"type": "GESTIONE_TURNI_ACCOUNTS_LIST_RESPONSE", "ok": True, "accounts": store.list_public()}
            if request_type == "GESTIONE_TURNI_ACCOUNT_AUTH":
                account = store.verify(str(request.get("doctor_id", "")), str(request.get("password", "")))
                return {"type": "GESTIONE_TURNI_ACCOUNT_AUTH_RESPONSE", "ok": account is not None, "account": account}
            if request_type == "GESTIONE_TURNI_ACCOUNT_CREATE":
                account = store.create(str(request.get("doctor_name", "")), str(request.get("password", "")))
                return {"type": "GESTIONE_TURNI_ACCOUNT_CREATE_RESPONSE", "ok": True, "account": account}
            if request_type == "GESTIONE_TURNI_ACCOUNT_DELETE":
                record = store.delete(
                    str(request.get("doctor_id", "")),
                    str(request.get("password", "")),
                )
                self.account_records_received.emit([record])
                return {
                    "type": "GESTIONE_TURNI_ACCOUNT_DELETE_RESPONSE",
                    "ok": True,
                    "record": record,
                }
        except ValueError as exc:
            return {"type": request_type + "_RESPONSE", "ok": False, "error": str(exc)}
        return {"type": request_type + "_RESPONSE", "ok": False}

    @classmethod
    def discover_server_once(cls) -> str | None:
        request = {"type": DISCOVERY_MESSAGE, "doctor_id": "launcher"}
        encoded = json.dumps(request).encode("utf-8")
        candidates: set[str] = set()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(0.8)

                for destination in (
                    ("255.255.255.255", DISCOVERY_PORT),
                    ("127.0.0.1", DISCOVERY_PORT),
                ):
                    try:
                        sock.sendto(encoded, destination)
                    except OSError:
                        pass

                deadline = time.monotonic() + 0.8
                while time.monotonic() < deadline:
                    try:
                        raw, sender = sock.recvfrom(4096)
                    except socket.timeout:
                        break

                    response = cls._decode_message(raw)
                    if response.get("type") != DISCOVERY_RESPONSE:
                        continue

                    if sender[0] == "127.0.0.1":
                        candidates.add("127.0.0.1")
                    else:
                        address = str(response.get("server_ip") or sender[0]).strip()
                        if address:
                            candidates.add(address)
        except OSError:
            return None

        if not candidates:
            return None

        return min(candidates, key=cls._server_sort_key)

    @classmethod
    def account_rpc(cls, request: dict[str, Any], server_address: str | None = None) -> dict[str, Any] | None:
        address = server_address or cls.discover_server_once()
        if not address:
            return None
        try:
            with socket.create_connection((address, HEARTBEAT_PORT), timeout=1.5) as connection:
                connection.settimeout(1.5)
                connection.sendall(json.dumps(request).encode("utf-8"))
                return cls._decode_message(connection.recv(65536))
        except OSError:
            return None

    def _discover_server(
        self,
        *,
        exclude_addresses: set[str] | None = None,
        include_loopback: bool = True,
    ) -> str | None:
        request = {
            "type": DISCOVERY_MESSAGE,
            "doctor_id": self.doctor_id,
        }
        encoded_request = json.dumps(request).encode("utf-8")
        excluded = {str(value).strip() for value in (exclude_addresses or set()) if str(value).strip()}
        candidates: set[str] = set()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as discovery_socket:
                discovery_socket.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_BROADCAST,
                    1,
                )
                discovery_socket.settimeout(DISCOVERY_TIMEOUT_SECONDS)

                destinations = [("255.255.255.255", DISCOVERY_PORT)]
                if include_loopback:
                    destinations.append(("127.0.0.1", DISCOVERY_PORT))

                for destination in destinations:
                    try:
                        discovery_socket.sendto(encoded_request, destination)
                    except OSError:
                        continue

                deadline = time.monotonic() + DISCOVERY_TIMEOUT_SECONDS
                while (
                    not self._stop_event.is_set()
                    and time.monotonic() < deadline
                ):
                    try:
                        raw_response, sender = discovery_socket.recvfrom(4096)
                    except socket.timeout:
                        break
                    except OSError:
                        return None

                    response = self._decode_message(raw_response)
                    if response.get("type") != DISCOVERY_RESPONSE:
                        continue

                    if sender[0] == "127.0.0.1":
                        if not include_loopback:
                            continue
                        server_ip = "127.0.0.1"
                    else:
                        server_ip = str(response.get("server_ip") or sender[0]).strip()

                    if not server_ip or server_ip in excluded:
                        continue
                    candidates.add(server_ip)

        except OSError:
            return None

        if not candidates:
            return None

        # Se per una partenza simultanea rispondono più Server, tutti i PC
        # scelgono lo stesso in modo deterministico invece del primo pacchetto
        # UDP arrivato. Questo evita due display TV indipendenti sulla LAN.
        return min(candidates, key=self._server_sort_key)

    def _run_server_reconciliation(self) -> None:
        local_address = self._get_local_ip()

        while not self._stop_event.is_set() and self.role == "server":
            if self._stop_event.wait(SERVER_RECONCILE_INTERVAL_SECONDS):
                return

            other_server = self._discover_server(
                exclude_addresses={local_address, "127.0.0.1"},
                include_loopback=False,
            )
            if not other_server:
                continue

            # Regola stabile: tra più Server sopravvive quello con IP più
            # basso. Il/i Server con IP maggiore diventano Client e quindi
            # tutti i medici confluiscono nello stesso stato condiviso.
            if self._server_sort_key(other_server) >= self._server_sort_key(local_address):
                continue

            self.status_changed.emit(
                "Rilevato un altro server di rete. "
                "Unificazione automatica del display..."
            )
            self._close_server_sockets()
            time.sleep(0.15)
            self._run_as_client(other_server)
            return

    @staticmethod
    def _server_sort_key(address: str) -> tuple[int, ...]:
        clean = str(address or "").strip()
        try:
            return tuple(int(part) for part in clean.split("."))
        except (TypeError, ValueError):
            return (999, 999, 999, 999)

    def _run_as_client(
        self,
        server_address: str,
    ) -> None:
        with self._state_lock:
            if server_address and server_address != "127.0.0.1":
                self._peer_addresses.add(server_address)

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
            # Si azzera prima dello scambio: se un nuovo messaggio
            # arriva mentre la comunicazione è in corso, l'evento
            # resta impostato e provoca immediatamente un altro giro.
            self._outbox_event.clear()

            response = self._exchange_with_server(
                server_address
            )

            if response is not None:
                if missed_heartbeats:
                    self.status_changed.emit(
                        "Connessione al server ripristinata."
                    )

                missed_heartbeats = 0

                account_records = response.get("account_records", [])
                if isinstance(account_records, list) and account_records:
                    self.account_records_received.emit(account_records)

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

            # Normalmente il prossimo controllo avviene al ritmo
            # dell'heartbeat. Un aggiornamento locale del Client
            # interrompe però subito l'attesa tramite _outbox_event.
            self._outbox_event.wait(
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
