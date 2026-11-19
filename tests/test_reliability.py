"""Regression tests use temporary data only; no patient/account data is loaded."""
from __future__ import annotations

import json
import io
import os
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request
from contextlib import contextmanager
from queue import Queue, Empty

socket.setdefaulttimeout(3)

_TEST_ROOT = Path(__file__).resolve().parents[1] / ".tools" / "tests"
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TEST_ROOT)
_TEST_HOME = tempfile.TemporaryDirectory(prefix="GestioneTurni_tests_", dir=_TEST_ROOT)
os.environ["GESTIONE_TURNI_DATA_DIR"] = _TEST_HOME.name
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app import storage
from app.accounts import AccountStore
from app.network.manager import NetworkManager, HEARTBEAT_MESSAGE, HEARTBEAT_RESPONSE
from app.network.transport import client_exchange, send_json, receive_json

from app.protocol import validate_message, create_doctor_update
from app.shared_state import SharedState
from app.sync_manager import SyncManager
from app.web_display_server import WebDisplayServer
from app.version import APP_VERSION

APP = QApplication.instance() or QApplication([])


@contextmanager
def memory_socketpair():
    """Bounded duplex byte stream: tests transport even when loopback is blocked."""
    class Stream:
        def __init__(self): self.incoming = Queue(); self.pending = b""; self.closed = False
        def settimeout(self, value): pass
        def sendall(self, data): self.peer.incoming.put(bytes(data))
        def recv(self, size):
            if not self.pending:
                try: self.pending = self.incoming.get(timeout=3)
                except Empty as exc: raise TimeoutError("stream timed out") from exc
            result, self.pending = self.pending[:size], self.pending[size:]
            return result
        def close(self):
            if not self.closed:
                self.closed = True
                self.peer.incoming.put(b"")
        def __enter__(self): return self
        def __exit__(self, *args): self.close()
    a, b = Stream(), Stream()
    a.peer, b.peer = b, a
    try: yield a, b
    finally: a.close(); b.close()


def require_loopback():
    """Restricted hosts can deny connects, even to 127.0.0.1."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        try:
            with socket.create_connection(listener.getsockname(), timeout=1): pass
        except PermissionError as exc:
            raise unittest.SkipTest("Il sandbox blocca le connessioni loopback") from exc


class TransportTests(unittest.TestCase):
    def test_large_fragmented_json_roundtrip(self):
        payload = {"surname": "Rossi", "data": "é" * 100000}
        errors = []
        with memory_socketpair() as (client, server):
            class Fragmented:
                def __init__(self, sock): self.sock = sock
                def recv(self, size): return self.sock.recv(min(size, 317))
                def sendall(self, raw):
                    for index in range(0, len(raw), 521):
                        self.sock.sendall(raw[index:index + 521])
            def respond():
                try:
                    incoming = receive_json(Fragmented(server))
                    self.assertEqual(incoming, payload)
                    send_json(Fragmented(server), {"ok": True, "payload": incoming})
                except BaseException as exc: errors.append(exc)
            worker = threading.Thread(target=respond)
            worker.start()
            response = client_exchange(Fragmented(client), payload)
            worker.join(4)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(response["payload"], payload)

    def test_legacy_json_without_newline_and_invalid_messages(self):
        with memory_socketpair() as (a, b):
            a.sendall(b'{"type":"legacy","number":7}')
            self.assertEqual(receive_json(b)["number"], 7)
        for raw in [b'[]', b'{"value":NaN}', b'{}garbage', b'\xff']:
            with memory_socketpair() as (a, b):
                a.sendall(raw)
                with self.assertRaises(ValueError): receive_json(b)

    def test_size_limit_and_incomplete_stream(self):
        with memory_socketpair() as (a, b), patch("app.network.transport.MAX_MESSAGE_BYTES", 64):
            a.sendall(b'{"data":"' + b'x' * 70)
            with self.assertRaises(ValueError): receive_json(b)
            with self.assertRaises(ValueError): send_json(a, {"data": "x" * 70})
        with memory_socketpair() as (a, b):
            a.sendall(b'{"partial":')
            a.close()
            with self.assertRaises(ConnectionError): receive_json(b)


class PersistenceTests(unittest.TestCase):
    def test_installer_checksum_rejects_modified_or_unverified_files(self):
        from app.updater import verify_installer
        import hashlib
        with tempfile.TemporaryDirectory() as home:
            path = Path(home) / "installer.exe"
            path.write_bytes(b"test installer")
            digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            verify_installer(path, path.stat().st_size, digest)
            for expected_size, checksum in [(1, digest), (0, ""), (0, "sha256:" + "0" * 64)]:
                with self.assertRaises(OSError): verify_installer(path, expected_size, checksum)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = "regression"
        self.path = Path(self.temp.name) / "turns.json"
        self.patches = [patch.object(storage, "QUEUE_DIR", Path(self.temp.name)),
                        patch.object(storage, "get_turns_file", return_value=self.path),
                        patch.object(storage, "get_turns_lock_file", return_value=self.path.with_suffix(".lock"))]
        for item in self.patches: item.start(); self.addCleanup(item.stop)
        storage.set_active_storage_profile(self.profile)
        self.addCleanup(storage.set_active_storage_profile, None)

    def test_missing_file_is_new_queue_and_roundtrip(self):
        self.assertEqual(storage.load_turns(), {self.profile: 0})
        storage.save_turns({self.profile: 42})
        self.assertEqual(storage.load_turns(), {self.profile: 42})

    def test_corrupt_queue_is_not_reset_or_overwritten(self):
        self.path.write_text('{"unfinished":', encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(OSError): storage.load_turns()
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_replace_preserves_saved_data(self):
        storage.save_turns({self.profile: 42})
        with patch.object(storage.os, "replace", side_effect=PermissionError("locked")), \
             patch.object(storage, "FILE_OPERATION_ATTEMPTS", 1):
            with self.assertRaises(OSError): storage.save_turns({self.profile: 43})
        self.assertEqual(storage.load_turns(), {self.profile: 42})


class NetworkTests(unittest.TestCase):
    def test_four_pcs_discover_server_without_pairing_even_with_old_key_file(self):
        from app.network.manager import DISCOVERY_MESSAGE, DISCOVERY_RESPONSE
        old_key = Path(_TEST_HOME.name) / "network.key"
        old_key.write_text("unused old pairing data", encoding="ascii")
        managers = [NetworkManager(doctor) for doctor in ["doctor1", "doctor2", "doctor1", "doctor2"]]
        class DiscoverySocket:
            def __init__(self): self.responses = []; self.requested = False
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def setsockopt(self, *args): pass
            def settimeout(self, *args): pass
            def sendto(self, data, destination):
                request = json.loads(data)
                if request.get("type") != DISCOVERY_MESSAGE or "mac" in request:
                    raise AssertionError("Discovery must not require a pairing code")
                if not self.requested:
                    self.requested = True
                    for number in [40, 30, 10, 20]:
                        address = f"192.168.1.{number}"
                        response = {"type": DISCOVERY_RESPONSE, "server_ip": address}
                        if number == 10: response["nonce"] = request["nonce"]
                        self.responses.append((json.dumps(response).encode(), (address, 50555)))
            def recvfrom(self, size):
                if self.responses: return self.responses.pop(0)
                raise socket.timeout()
        with patch("app.network.manager.socket.socket", return_value=DiscoverySocket()):
            self.assertEqual(NetworkManager.discover_server_once(), "192.168.1.10")
        self.assertEqual(len(managers), 4)
        self.assertEqual(old_key.read_text(), "unused old pairing data")

    def test_account_entry_has_only_login_and_create_buttons(self):
        from app.account_dialog import AccountEntryDialog
        from PySide6.QtWidgets import QPushButton
        dialog = AccountEntryDialog([], lambda *args: None, lambda *args: {})
        self.addCleanup(dialog.close)
        self.assertEqual([button.text() for button in dialog.findChildren(QPushButton)], ["Accedi", "Crea account"])

    def test_server_processes_update_before_ack_and_deduplicates_retries(self):
        manager = NetworkManager("doctor1")
        manager._role = "server"
        shared = SharedState("doctor1", "Medico 1")
        sync = SyncManager(shared)
        sync.outbound_message.connect(manager.send_message)
        sync.set_network_role("server")
        from PySide6.QtCore import Qt
        manager.message_received.connect(sync.handle_network_message, Qt.ConnectionType.BlockingQueuedConnection)
        class Listener:
            def __init__(self): self.queue = Queue()
            def accept(self):
                try: return self.queue.get(timeout=.05), ("127.0.0.1", 123)
                except Empty: raise socket.timeout()
            def close(self): pass
        listener = Listener()
        manager._heartbeat_socket = listener
        server = threading.Thread(target=manager._heartbeat_server_loop, daemon=True)
        server.start()
        message = create_doctor_update({"doctor_id": "doctor2", "doctor_name": "Medico 2", "number": 17})
        message["delivery_id"] = "c" * 32
        request = {"type": HEARTBEAT_MESSAGE, "doctor_id": "doctor2", "messages": [message]}
        received = []
        shared.state_changed.connect(lambda state: received.append(state))
        responses, errors = [], []
        try:
            for _ in range(2):
                with memory_socketpair() as (client, peer):
                    listener.queue.put(peer)
                    def exchange():
                        try: responses.append(client_exchange(client, request))
                        except BaseException as exc: errors.append(exc)
                    worker = threading.Thread(target=exchange)
                    worker.start()
                    deadline = time.monotonic() + 4
                    while worker.is_alive() and time.monotonic() < deadline:
                        APP.processEvents()
                        worker.join(.005)
                    self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(len(responses), 2)
            self.assertEqual(len(received), 1)
            snapshot = responses[0]["messages"][0]["payload"]["state"]
            self.assertEqual(snapshot["doctor2"]["number"], 17)
        finally:
            manager.stop()
            server.join(1)
        self.assertFalse(server.is_alive())

    def test_invalid_protocol_versions_never_raise(self):
        for value in ["invalid", None, [], {}, True, 2.0, float("nan")]:
            self.assertFalse(validate_message({"protocol": "gestione_turni", "version": value,
                                              "type": "doctor_update", "payload": {}}))

    def test_outbox_restored_on_invalid_response(self):
        manager = NetworkManager("doctor1")
        manager.send_message({"type": "test", "number": 3})
        with patch("app.network.manager.socket.create_connection") as connect, \
             patch("app.network.manager.client_exchange", return_value={"type": "wrong"}):
            self.assertIsNone(manager._exchange_with_server("127.0.0.1"))
        pending = manager._take_outbox_messages()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["number"], 3)
        self.assertEqual(len(pending[0]["delivery_id"]), 32)

    def test_outbox_batch_leaves_unsent_messages(self):
        manager = NetworkManager("doctor1")
        for number in range(1005): manager.send_message({"type": "test", "number": number})
        self.assertEqual(len(manager._take_outbox_messages()), 1000)
        self.assertEqual(len(manager._take_outbox_messages()), 5)

    def test_account_snapshot_is_not_rewritten_when_unchanged(self):
        with tempfile.TemporaryDirectory() as home, patch("app.accounts.ACCOUNTS_FILE", Path(home) / "accounts.json"):
            store = AccountStore()
            record = store.create("Medico test", "test-password")
            with patch.object(store, "_save_unlocked") as save:
                store.merge_records([record], authoritative=True)
                save.assert_not_called()

    def test_real_lan_server_and_deduplication(self):
        require_loopback()
        manager = NetworkManager("doctor1")
        # Bind just the heartbeat service on an ephemeral loopback port.
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        listener.settimeout(.1)
        manager._heartbeat_socket = listener
        thread = threading.Thread(target=manager._heartbeat_server_loop, daemon=True)
        thread.start()
        received = []
        from PySide6.QtCore import Qt
        manager.message_received.connect(received.append, Qt.ConnectionType.DirectConnection)
        message = create_doctor_update({"doctor_id": "doctor2", "number": 7})
        message["delivery_id"] = "a" * 32
        request = {"type": HEARTBEAT_MESSAGE, "doctor_id": "doctor2", "messages": [message]}
        try:
            for _ in range(2):
                with socket.create_connection(listener.getsockname(), timeout=2) as connection:
                    result = client_exchange(connection, request)
                    self.assertEqual(result["type"], HEARTBEAT_RESPONSE)
            self.assertEqual(len(received), 1)
            # A malformed message must not terminate the server loop.
            with socket.create_connection(listener.getsockname(), timeout=2) as connection:
                connection.sendall(b"[]")
                self.assertEqual(connection.recv(1), b"")
            # Server remains operational after the rejected request.
            with socket.create_connection(listener.getsockname(), timeout=2) as connection:
                self.assertEqual(client_exchange(connection, request)["type"], HEARTBEAT_RESPONSE)
        finally:
            manager.stop()
            thread.join(2)
        self.assertFalse(thread.is_alive())


class WebTests(unittest.TestCase):
    def test_http_handlers_without_network_permissions(self):
        server = WebDisplayServer(state_provider=lambda: {"doctor1": {"number": 8}},
            role_provider=lambda: "server", server_address_provider=lambda: "127.0.0.1",
            local_address_provider=lambda: "127.0.0.1", peer_addresses_provider=lambda: [], port=8080)
        handler = server._build_handler_class()
        class Request:
            def __init__(self, path):
                self.input = io.BytesIO(("GET " + path + " HTTP/1.0\r\n\r\n").encode())
                self.output = bytearray()
            def makefile(self, *args): return self.input
            def sendall(self, data): self.output.extend(data)
        request = Request("/")
        handler(request, ("127.0.0.1", 1), server)
        self.assertIn(("Display " + APP_VERSION).encode(), request.output)
        self.assertNotIn(b"__APP_VERSION__", request.output)
        request = Request("/api/state")
        handler(request, ("127.0.0.1", 1), server)
        payload = json.loads(bytes(request.output).split(b"\r\n\r\n", 1)[1])
        self.assertEqual(payload["state"]["doctor1"]["number"], 8)
        self.assertLess(abs(payload["server_epoch_ms"] - time.time() * 1000), 3000)
    def test_display_http_version_state_and_clock(self):
        require_loopback()
        server = WebDisplayServer(state_provider=lambda: {"doctor1": {"number": 8}},
            role_provider=lambda: "server", server_address_provider=lambda: "127.0.0.1",
            local_address_provider=lambda: "127.0.0.1", peer_addresses_provider=lambda: [], port=0)
        server.start()
        self.addCleanup(server.stop)
        base = "http://127.0.0.1:" + str(server._http_server.server_port)
        with urllib.request.urlopen(base + "/") as response:
            html = response.read().decode()
            self.assertIn("Display " + APP_VERSION, html)
            self.assertNotIn("__APP_VERSION__", html)
        with urllib.request.urlopen(base + "/api/state") as response:
            payload = json.load(response)
            self.assertEqual(payload["state"]["doctor1"]["number"], 8)
            self.assertLess(abs(payload["server_epoch_ms"] - time.time() * 1000), 3000)
            self.assertIsInstance(payload["utc_offset_minutes"], int)


class ControllerTests(unittest.TestCase):
    def make_controller(self, mode="number"):
        from main import prepare_account_config
        from app.controller import AppController
        store = AccountStore()
        account = store.create("Timer test", "test-password")
        account = store.update_account(account["doctor_id"], {"queue_mode": mode})
        prepare_account_config(account)
        controller = AppController(account_store=store)
        self.addCleanup(controller.close)
        return controller

    def test_start_queue_starts_visible_timer_and_next_patient_resets_it(self):
        from app.window import MainWindow
        controller = self.make_controller()
        controller.set_number(4)
        window = MainWindow(controller)
        self.addCleanup(window.close)
        base = 1795000000.0
        with patch("app.controller.time.time", return_value=base):
            window.queue_button.click()
        self.assertTrue(controller.get_current_patient_timer()["active"])
        self.assertEqual(controller.get_current_patient_timer()["number"], 4)
        with patch("app.window.time.time", return_value=base + 5):
            window.update_patient_timer()
            self.assertIn("00:00:05", window.patient_timer_label.text())
            window.doctor_card.increment_button.click()
            window.update_patient_timer()
            self.assertIn("00:00:00", window.patient_timer_label.text())
        self.assertEqual(controller.get_current_patient_timer()["number"], 5)
        window.queue_button.click()
        self.assertFalse(controller.get_current_patient_timer()["active"])
        self.assertTrue(window.patient_timer_label.text().startswith("Tempo paziente:"))
        self.assertFalse(window.patient_pause_button.isEnabled())

    def test_paused_timer_survives_restart_and_excludes_pause_duration(self):
        from app.controller import AppController
        controller = self.make_controller()
        base = 1795000000.0
        with patch("app.controller.time.time", return_value=base):
            controller.set_queue_active(True)
            controller.set_number(1, action="increment")
        with patch("app.controller.time.time", return_value=base + 5):
            controller.toggle_patient_timer_pause()
        reloaded = AppController(account_store=controller.account_store)
        self.addCleanup(reloaded.close)
        self.assertTrue(reloaded.get_current_patient_timer()["paused"])
        self.assertEqual(reloaded.get_current_patient_timer()["paused_at"], base + 5)
        with patch("app.controller.time.time", return_value=base + 25):
            reloaded.toggle_patient_timer_pause()
        self.assertFalse(reloaded.get_current_patient_timer()["paused"])
        self.assertEqual(reloaded.get_current_patient_timer()["started_at"], base + 20)

    def test_timer_retries_a_transient_config_file_lock(self):
        controller = self.make_controller()
        original_replace = Path.replace
        attempts = []
        def replace_with_transient_lock(source, target):
            attempts.append(source)
            if len(attempts) == 1:
                raise PermissionError("temporary lock")
            return original_replace(source, target)
        with patch.object(Path, "replace", autospec=True, side_effect=replace_with_transient_lock), \
             patch("app.config.time.sleep"):
            controller.set_queue_active(True)
        self.assertGreaterEqual(len(attempts), 2)
        self.assertTrue(controller.get_current_patient_timer()["active"])

    def test_surname_timer_waits_for_call_and_restarts_for_same_surname(self):
        controller = self.make_controller("surname")
        base = 1795000000.0
        controller.set_queue_active(True)
        self.assertFalse(controller.get_current_patient_timer()["active"])
        with patch("app.controller.time.time", return_value=base):
            controller.set_surname("Rossi")
        self.assertTrue(controller.get_current_patient_timer()["active"])
        with patch("app.controller.time.time", return_value=base + 10):
            controller.set_surname("Rossi")
        self.assertEqual(controller.get_current_patient_timer()["started_at"], base + 10)
        controller.set_surname("")
        self.assertFalse(controller.get_current_patient_timer()["active"])

    def test_number_queue_and_patient_timer(self):
        from main import prepare_account_config
        from app.controller import AppController
        store = AccountStore()
        account = store.create("Smoke test", "test-password")
        prepare_account_config(account)
        controller = AppController(account_store=store)
        self.addCleanup(controller.close)
        controller.set_number(4)
        controller.set_queue_active(True)
        controller.set_number(5, action="increment")
        self.assertEqual(controller.get_local_number(), 5)
        timer = controller.get_current_patient_timer()
        self.assertTrue(timer["active"])
        self.assertEqual(timer["number"], 5)
        with patch("app.controller.load_turns", side_effect=OSError("locked")), \
             patch("app.controller.QMessageBox.warning") as warning:
            controller.set_number(6, action="increment")
            warning.assert_called_once()
        self.assertEqual(controller.get_local_number(), 5)
        self.assertEqual(controller.get_current_patient_timer()["number"], 5)
        controller.set_queue_active(False)
        self.assertFalse(controller.get_current_patient_timer()["active"])


if __name__ == "__main__": unittest.main()
