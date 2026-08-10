from __future__ import annotations

import logging
import time

from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog

from app.config import load_config, save_config
from app.history_storage import (
    end_daily_queue,
    record_patient_visit,
    start_daily_queue,
    update_daily_queue,
)
from app.network import NetworkManager
from app.settings_dialog import SettingsDialog
from app.shared_state import SharedState
from app.storage import load_turns, save_turns
from app.sync_manager import SyncManager
from app.web_display_server import WebDisplayServer


LOGGER = logging.getLogger(__name__)


class AppController(QObject):

    state_changed = Signal(object)

    network_role_changed = Signal(str)
    network_status_changed = Signal(str)
    server_address_changed = Signal(str)
    sync_status_changed = Signal(str)

    settings_changed = Signal(object)
    patient_timer_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()

        self.config = load_config()

        self.doctor_id = str(
            self.config.get(
                "doctor_id",
                "",
            )
        )

        self.doctor_name = str(
            self.config.get(
                "doctor_name",
                "",
            )
        ).strip()

        self.queue_prefix = self._clean_queue_prefix(
            self.config.get("queue_prefix", "")
        )

        self.queue_active = bool(
            self.config.get(
                "queue_active",
                False,
            )
        )

        self._patient_started_at = self._safe_timestamp(
            self.config.get("patient_started_at")
        )
        self._patient_number = self._safe_optional_number(
            self.config.get("patient_number")
        )
        self._patient_prefix = self._clean_queue_prefix(
            self.config.get("patient_prefix", "")
        )

        if not self.queue_active:
            self._clear_patient_timer_state(save=True)

        turns = load_turns()

        current_number = self._safe_number(
            turns.get(
                self.doctor_id,
                0,
            )
        )

        self.shared_state = SharedState(
            local_doctor_id=self.doctor_id,
            local_doctor_name=self.doctor_name,
            local_queue_prefix=self.queue_prefix,
            local_number=current_number,
            local_queue_active=self.queue_active,
        )

        self.sync_manager = SyncManager(
            self.shared_state
        )

        self.network_manager = NetworkManager(
            self.doctor_id
        )

        self.web_display_server = WebDisplayServer(
            state_provider=self.shared_state.get_all,
            role_provider=lambda: self.network_manager.role,
            server_address_provider=(
                lambda: self.network_manager.server_address
            ),
            local_address_provider=(
                lambda: self.network_manager.local_address
            ),
            peer_addresses_provider=(
                lambda: self.network_manager.peer_addresses
            ),
        )

        self.display_window = None
        self.history_window = None
        self.dashboard_window = None

        self._connect_components()

        if self.queue_active:
            self._ensure_history_started()

    def _connect_components(self) -> None:
        self.shared_state.state_changed.connect(
            self._on_shared_state_changed
        )

        self.sync_manager.outbound_message.connect(
            self.network_manager.send_message
        )

        self.sync_manager.sync_status_changed.connect(
            self.sync_status_changed.emit
        )

        self.network_manager.message_received.connect(
            self.sync_manager.handle_network_message
        )

        self.network_manager.role_changed.connect(
            self.sync_manager.set_network_role
        )

        self.network_manager.role_changed.connect(
            self.network_role_changed.emit
        )

        self.network_manager.status_changed.connect(
            self.network_status_changed.emit
        )

        self.network_manager.server_address_changed.connect(
            self.server_address_changed.emit
        )

    def start(self) -> None:
        LOGGER.info("Avvio rete per il profilo %s", self.doctor_id)
        self.web_display_server.start()
        self.network_manager.start()

    def close(self) -> None:
        LOGGER.info("Chiusura controller per il profilo %s", self.doctor_id)
        self.sync_manager.notify_local_disconnect()
        self.shared_state.mark_local_offline()
        self.network_manager.stop()
        self.web_display_server.stop()

        if self.display_window is not None:
            self.display_window.close()
            self.display_window = None

        if self.history_window is not None:
            self.history_window.close()
            self.history_window = None

        if self.dashboard_window is not None:
            self.dashboard_window.close()
            self.dashboard_window = None

    def open_dashboard(
        self,
        parent=None,
    ) -> None:
        from app.dashboard_dialog import DashboardDialog

        if self.dashboard_window is None:
            self.dashboard_window = DashboardDialog(
                controller=self,
                parent=parent,
            )

            self.dashboard_window.destroyed.connect(
                self._on_dashboard_destroyed
            )
        else:
            self.dashboard_window.refresh_dashboard()

        self.dashboard_window.show()
        self.dashboard_window.raise_()
        self.dashboard_window.activateWindow()

    def _on_dashboard_destroyed(self) -> None:
        self.dashboard_window = None

    def open_history(
        self,
        parent=None,
    ) -> None:
        from app.history_dialog import HistoryDialog

        if self.history_window is None:
            self.history_window = HistoryDialog(
                doctor_id=self.doctor_id,
                doctor_name=self.doctor_name,
                parent=parent,
            )

            self.history_window.destroyed.connect(
                self._on_history_destroyed
            )
        else:
            self.history_window.doctor_name = (
                self.doctor_name
            )

            self.history_window.doctor_label.setText(
                self.doctor_name
            )

            self.history_window.refresh_history()

        self.history_window.show()
        self.history_window.raise_()
        self.history_window.activateWindow()

    def _on_history_destroyed(self) -> None:
        self.history_window = None

    def open_settings(
        self,
        parent=None,
    ) -> None:
        dialog = SettingsDialog(
            current_config=self.config,
            parent=parent,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.saved_settings is None:
            return

        settings = dialog.saved_settings

        new_name = str(
            settings.get(
                "doctor_name",
                self.doctor_name,
            )
        ).strip()

        new_prefix = self._clean_queue_prefix(
            settings.get("queue_prefix", self.queue_prefix)
        )

        self.config.update(settings)
        self.config["queue_prefix"] = new_prefix
        save_config(self.config)

        if new_name != self.doctor_name:
            self.doctor_name = new_name

            self.shared_state.update_local(
                doctor_name=new_name
            )

            if self.queue_active:
                update_daily_queue(
                    doctor_id=self.doctor_id,
                    doctor_name=self.doctor_name,
                    current_number=(
                        self.get_local_number()
                    ),
                )

        if new_prefix != self.queue_prefix:
            self.queue_prefix = new_prefix
            self.shared_state.update_local(
                queue_prefix=self.queue_prefix
            )

        self.settings_changed.emit(
            dict(self.config)
        )

        if self.display_window is not None:
            self.display_window.apply_preferences(
                show_clock=bool(
                    self.config.get(
                        "display_show_clock",
                        True,
                    )
                )
            )

        if self.history_window is not None:
            self.history_window.doctor_name = (
                self.doctor_name
            )

            self.history_window.doctor_label.setText(
                self.doctor_name
            )

            self.history_window.refresh_history()

        if self.dashboard_window is not None:
            self.dashboard_window.refresh_dashboard()

    def open_display(self) -> None:
        from app.display_window import DisplayWindow

        if self.display_window is None:
            self.display_window = DisplayWindow(
                self.shared_state
            )

            self.display_window.destroyed.connect(
                self._on_display_destroyed
            )

        self.display_window.apply_preferences(
            show_clock=bool(
                self.config.get(
                    "display_show_clock",
                    True,
                )
            )
        )

        if bool(
            self.config.get(
                "display_fullscreen",
                False,
            )
        ):
            self.display_window.showFullScreen()
        else:
            self.display_window.showNormal()

        self.display_window.raise_()
        self.display_window.activateWindow()

    def _on_display_destroyed(self) -> None:
        self.display_window = None

    def get_local_state(
        self,
    ) -> dict[str, Any]:
        return self.shared_state.get_local_doctor()

    def get_complete_state(
        self,
    ) -> dict[str, dict[str, Any]]:
        return self.shared_state.get_all()

    def set_number(
        self,
        number: int,
        action: str = "set",
    ) -> None:
        safe_number = self._safe_number(number)
        old_number = self.get_local_number()
        clean_action = str(action or "set").strip().lower()

        valid_increment = (
            clean_action == "increment"
            and safe_number == old_number + 1
        )

        if self.queue_active and valid_increment:
            self._finish_current_patient()

        if clean_action == "reset":
            self._finish_current_patient()

        LOGGER.info(
            "Aggiornamento numero %s: %s (%s)",
            self.doctor_id,
            safe_number,
            clean_action,
        )

        turns = load_turns()
        turns[self.doctor_id] = safe_number
        save_turns(turns)

        self.shared_state.update_local(
            number=safe_number
        )

        if self.queue_active:
            update_daily_queue(
                doctor_id=self.doctor_id,
                doctor_name=self.doctor_name,
                current_number=safe_number,
            )

        if self.queue_active and valid_increment:
            self._start_patient_timer(safe_number)

        if self.history_window is not None:
            self.history_window.refresh_history()

        if self.dashboard_window is not None:
            self.dashboard_window.refresh_dashboard()

    def get_local_number(self) -> int:
        return self._safe_number(
            self.get_local_state().get(
                "number",
                0,
            )
        )

    def set_queue_active(
        self,
        queue_active: bool,
    ) -> None:
        new_queue_active = bool(
            queue_active
        )

        if new_queue_active == self.queue_active:
            return

        LOGGER.info(
            "Stato coda %s: %s",
            self.doctor_id,
            "attiva" if new_queue_active else "terminata",
        )

        current_number = (
            self.get_local_number()
        )

        if new_queue_active:
            start_daily_queue(
                doctor_id=self.doctor_id,
                doctor_name=self.doctor_name,
                starting_number=current_number,
            )
        else:
            self._finish_current_patient()
            end_daily_queue(
                doctor_id=self.doctor_id,
                doctor_name=self.doctor_name,
                final_number=current_number,
            )

        self.queue_active = new_queue_active

        self.config["queue_active"] = (
            self.queue_active
        )
        save_config(self.config)

        self.shared_state.update_local(
            queue_active=self.queue_active
        )

        if self.history_window is not None:
            self.history_window.refresh_history()

        if self.dashboard_window is not None:
            self.dashboard_window.refresh_dashboard()

    def get_current_patient_timer(self) -> dict[str, Any]:
        active = (
            self._patient_started_at is not None
            and self._patient_number is not None
        )
        return {
            "active": active,
            "started_at": self._patient_started_at,
            "number": self._patient_number,
            "queue_prefix": self._patient_prefix,
            "ticket": (
                f"{self._patient_prefix}{self._patient_number}"
                if active
                else ""
            ),
        }

    def _start_patient_timer(self, patient_number: int) -> None:
        self._patient_started_at = time.time()
        self._patient_number = self._safe_number(patient_number)
        self._patient_prefix = self.queue_prefix
        self._save_patient_timer_state()
        self.patient_timer_changed.emit(
            self.get_current_patient_timer()
        )

    def _finish_current_patient(self) -> None:
        if (
            self._patient_started_at is None
            or self._patient_number is None
        ):
            return

        ended_at = time.time()
        try:
            record_patient_visit(
                doctor_id=self.doctor_id,
                doctor_name=self.doctor_name,
                queue_prefix=self._patient_prefix,
                patient_number=self._patient_number,
                started_at_epoch=self._patient_started_at,
                ended_at_epoch=ended_at,
            )
        except (OSError, ValueError, TypeError):
            LOGGER.exception(
                "Impossibile registrare la durata del paziente %s",
                self._patient_number,
            )

        self._clear_patient_timer_state(save=True)
        self.patient_timer_changed.emit(
            self.get_current_patient_timer()
        )

    def _save_patient_timer_state(self) -> None:
        self.config["patient_started_at"] = self._patient_started_at
        self.config["patient_number"] = self._patient_number
        self.config["patient_prefix"] = self._patient_prefix
        save_config(self.config)

    def _clear_patient_timer_state(self, *, save: bool) -> None:
        self._patient_started_at = None
        self._patient_number = None
        self._patient_prefix = ""
        self.config.pop("patient_started_at", None)
        self.config.pop("patient_number", None)
        self.config.pop("patient_prefix", None)
        if save:
            save_config(self.config)

    def toggle_queue(self) -> None:
        self.set_queue_active(
            not self.queue_active
        )

    def _ensure_history_started(self) -> None:
        try:
            start_daily_queue(
                doctor_id=self.doctor_id,
                doctor_name=self.doctor_name,
                starting_number=(
                    self.get_local_number()
                ),
            )
        except ValueError:
            return

    def _on_shared_state_changed(
        self,
        complete_state: object,
    ) -> None:
        if not isinstance(
            complete_state,
            dict,
        ):
            return

        local_state = complete_state.get(
            self.doctor_id
        )

        if isinstance(
            local_state,
            dict,
        ):
            self.doctor_name = str(
                local_state.get(
                    "doctor_name",
                    self.doctor_name,
                )
            ).strip()

            self.queue_active = bool(
                local_state.get(
                    "queue_active",
                    self.queue_active,
                )
            )

        self.state_changed.emit(
            complete_state
        )

    @staticmethod
    def _clean_queue_prefix(value: object) -> str:
        text = str(value or "").strip().upper()
        if not text:
            return ""
        first = text[0]
        return first if "A" <= first <= "Z" else ""

    @staticmethod
    def _safe_timestamp(value: object) -> float | None:
        if value is None:
            return None
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return None
        if timestamp <= 0:
            return None
        return timestamp

    @staticmethod
    def _safe_optional_number(value: object) -> int | None:
        if value is None:
            return None
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_number(
        value: Any,
    ) -> int:
        try:
            return max(
                0,
                int(value),
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0
