from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog

from app.config import load_config, save_config
from app.network import NetworkManager
from app.settings_dialog import SettingsDialog
from app.shared_state import SharedState
from app.storage import load_turns, save_turns
from app.sync_manager import SyncManager


class AppController(QObject):
    state_changed = Signal(object)

    network_role_changed = Signal(str)
    network_status_changed = Signal(str)
    server_address_changed = Signal(str)
    sync_status_changed = Signal(str)

    settings_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()

        self.config = load_config()

        self.doctor_id = str(
            self.config.get("doctor_id", "")
        )
        self.doctor_name = str(
            self.config.get("doctor_name", "")
        ).strip()
        self.queue_active = bool(
            self.config.get("queue_active", False)
        )

        turns = load_turns()
        current_number = self._safe_number(
            turns.get(self.doctor_id, 0)
        )

        self.shared_state = SharedState(
            local_doctor_id=self.doctor_id,
            local_doctor_name=self.doctor_name,
            local_number=current_number,
            local_queue_active=self.queue_active,
        )

        self.sync_manager = SyncManager(
            self.shared_state
        )

        self.network_manager = NetworkManager(
            self.doctor_id
        )

        self.display_window = None

        self._connect_components()

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
        self.network_manager.start()

    def close(self) -> None:
        self.sync_manager.notify_local_disconnect()
        self.shared_state.mark_local_offline()
        self.network_manager.stop()

        if self.display_window is not None:
            self.display_window.close()
            self.display_window = None

    def open_settings(self, parent=None) -> None:
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

        self.config.update(settings)
        save_config(self.config)

        if new_name != self.doctor_name:
            self.doctor_name = new_name

            self.shared_state.update_local(
                doctor_name=new_name
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

    def set_number(self, number: int) -> None:
        safe_number = self._safe_number(number)

        turns = load_turns()
        turns[self.doctor_id] = safe_number
        save_turns(turns)

        self.shared_state.update_local(
            number=safe_number
        )

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
        self.queue_active = bool(queue_active)

        self.config["queue_active"] = (
            self.queue_active
        )
        save_config(self.config)

        self.shared_state.update_local(
            queue_active=self.queue_active
        )

    def toggle_queue(self) -> None:
        self.set_queue_active(
            not self.queue_active
        )

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

        if isinstance(local_state, dict):
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
    def _safe_number(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0