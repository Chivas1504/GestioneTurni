from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.controller import AppController
from app.studio_card import StudioCard
from app.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: AppController,
    ) -> None:
        super().__init__()

        self.controller = controller

        local_state = (
            self.controller.get_local_state()
        )

        self.doctor_id = str(
            local_state.get(
                "doctor_id",
                "",
            )
        )

        self.doctor_name = str(
            local_state.get(
                "doctor_name",
                "",
            )
        ).strip()

        self.queue_active = bool(
            local_state.get(
                "queue_active",
                False,
            )
        )

        current_number = self._safe_number(
            local_state.get(
                "number",
                0,
            )
        )

        self.setWindowTitle(
            "Gestione Turni"
        )
        self.setMinimumSize(650, 890)
        self.resize(760, 970)

        central_widget = QWidget()
        central_widget.setObjectName(
            "centralWidget"
        )
        self.setCentralWidget(
            central_widget
        )

        title_label = QLabel(
            "GESTIONE TURNI"
        )
        title_label.setObjectName(
            "titleLabel"
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        subtitle_label = QLabel(
            "Sistema di gestione turni"
        )
        subtitle_label.setObjectName(
            "subtitleLabel"
        )
        subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.doctor_card = StudioCard(
            self.doctor_name,
            current_number,
        )

        self.doctor_card.number_changed.connect(
            self.controller.set_number
        )

        self.queue_status_label = QLabel()
        self.queue_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.queue_button = QPushButton()
        self.queue_button.setMinimumHeight(62)
        self.queue_button.clicked.connect(
            self.controller.toggle_queue
        )

        self.display_button = QPushButton(
            "Apri display"
        )
        self.display_button.setObjectName(
            "displayButton"
        )
        self.display_button.setMinimumHeight(62)
        self.display_button.clicked.connect(
            self.controller.open_display
        )

        self.network_role_label = QLabel(
            "Ruolo rete: inizializzazione..."
        )
        self.network_role_label.setObjectName(
            "networkRoleStarting"
        )
        self.network_role_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.network_status_label = QLabel(
            "Ricerca del server in corso..."
        )
        self.network_status_label.setObjectName(
            "networkStatus"
        )
        self.network_status_label.setWordWrap(True)
        self.network_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.sync_status_label = QLabel(
            "Sincronizzazione: "
            "inizializzazione..."
        )
        self.sync_status_label.setObjectName(
            "networkStatus"
        )
        self.sync_status_label.setWordWrap(True)
        self.sync_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.settings_button = QPushButton(
            "⚙ Impostazioni"
        )
        self.settings_button.setObjectName(
            "settingsButton"
        )
        self.settings_button.setMinimumHeight(58)

        self.settings_button.clicked.connect(
            lambda: self.controller.open_settings(self)
        )

        main_layout = QVBoxLayout(
            central_widget
        )
        main_layout.setContentsMargins(
            48,
            30,
            48,
            30,
        )
        main_layout.setSpacing(12)

        main_layout.addWidget(
            title_label
        )
        main_layout.addWidget(
            subtitle_label
        )
        main_layout.addSpacing(8)

        main_layout.addWidget(
            self.doctor_card,
            stretch=1,
        )

        main_layout.addWidget(
            self.queue_status_label
        )
        main_layout.addWidget(
            self.queue_button
        )
        main_layout.addWidget(
            self.display_button
        )

        main_layout.addSpacing(2)

        main_layout.addWidget(
            self.network_role_label
        )
        main_layout.addWidget(
            self.network_status_label
        )
        main_layout.addWidget(
            self.sync_status_label
        )

        main_layout.addWidget(
            self.settings_button
        )

        self.setStyleSheet(APP_STYLE)
        self.update_queue_ui()

        self._connect_controller()

    def _connect_controller(self) -> None:
        self.controller.state_changed.connect(
            self.on_shared_state_changed
        )

        self.controller.network_role_changed.connect(
            self.update_network_role
        )

        self.controller.network_status_changed.connect(
            self.network_status_label.setText
        )

        self.controller.sync_status_changed.connect(
            self.sync_status_label.setText
        )

        self.controller.server_address_changed.connect(
            self.update_server_address
        )

    def on_shared_state_changed(
        self,
        complete_state: object,
    ) -> None:
        if not isinstance(
            complete_state,
            dict,
        ):
            return

        local_state: Any = (
            complete_state.get(
                self.doctor_id
            )
        )

        if not isinstance(
            local_state,
            dict,
        ):
            return

        doctor_name = str(
            local_state.get(
                "doctor_name",
                self.doctor_name,
            )
        ).strip()

        number = self._safe_number(
            local_state.get(
                "number",
                self.doctor_card.number,
            )
        )

        queue_active = bool(
            local_state.get(
                "queue_active",
                self.queue_active,
            )
        )

        if doctor_name:
            self.doctor_name = doctor_name

            self.doctor_card.set_studio_name(
                doctor_name
            )

        if number != self.doctor_card.number:
            self.doctor_card.set_number(
                number
            )

        if queue_active != self.queue_active:
            self.queue_active = (
                queue_active
            )
            self.update_queue_ui()

    def update_queue_ui(self) -> None:
        if self.queue_active:
            self.queue_status_label.setText(
                "● Coda attiva"
            )
            self.queue_status_label.setObjectName(
                "queueStatusActive"
            )

            self.queue_button.setText(
                "Termina coda"
            )
            self.queue_button.setObjectName(
                "queueStopButton"
            )
        else:
            self.queue_status_label.setText(
                "● Coda non attiva"
            )
            self.queue_status_label.setObjectName(
                "queueStatusInactive"
            )

            self.queue_button.setText(
                "Inizia coda"
            )
            self.queue_button.setObjectName(
                "queueStartButton"
            )

        self._refresh_widget_style(
            self.queue_status_label
        )
        self._refresh_widget_style(
            self.queue_button
        )

    def update_network_role(
        self,
        role: str,
    ) -> None:
        if role == "server":
            self.network_role_label.setText(
                "Ruolo rete: Server"
            )
            self.network_role_label.setObjectName(
                "networkRoleServer"
            )
        elif role == "client":
            self.network_role_label.setText(
                "Ruolo rete: Client"
            )
            self.network_role_label.setObjectName(
                "networkRoleClient"
            )
        else:
            self.network_role_label.setText(
                "Ruolo rete: "
                "inizializzazione..."
            )
            self.network_role_label.setObjectName(
                "networkRoleStarting"
            )

        self._refresh_widget_style(
            self.network_role_label
        )

    def update_server_address(
        self,
        server_address: str,
    ) -> None:
        if not server_address:
            return

        current_status = (
            self.network_status_label.text()
        )

        address_line = (
            f"Indirizzo server: "
            f"{server_address}"
        )

        if address_line in current_status:
            return

        self.network_status_label.setText(
            f"{current_status}\n"
            f"{address_line}"
        )

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

    @staticmethod
    def _refresh_widget_style(
        widget: QWidget,
    ) -> None:
        widget.style().unpolish(
            widget
        )
        widget.style().polish(
            widget
        )

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.controller.close()
        event.accept()