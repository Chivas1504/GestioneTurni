from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
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

        self.current_network_role = (
            "Inizializzazione"
        )
        self.current_sync_status = (
            "Sincronizzazione in corso"
        )
        self.current_server_address = ""

        self.setWindowTitle(
            "Gestione Turni"
        )

        self.setMinimumSize(
            700,
            760,
        )
        self.resize(
            820,
            850,
        )

        central_widget = QWidget()
        central_widget.setObjectName(
            "centralWidget"
        )
        self.setCentralWidget(
            central_widget
        )

        self._build_header()
        self._build_doctor_card(
            current_number
        )
        self._build_queue_controls()
        self._build_action_controls()
        self._build_network_area()
        self._build_settings_button()
        self._build_layout(
            central_widget
        )

        self.setStyleSheet(
            APP_STYLE
            + self._additional_style()
        )

        self.update_queue_ui()
        self._update_network_summary()
        self._connect_controller()

    def _build_header(self) -> None:
        self.title_label = QLabel(
            "GESTIONE TURNI"
        )
        self.title_label.setObjectName(
            "titleLabel"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.subtitle_label = QLabel(
            "Sistema di gestione turni"
        )
        self.subtitle_label.setObjectName(
            "subtitleLabel"
        )
        self.subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

    def _build_doctor_card(
        self,
        current_number: int,
    ) -> None:
        self.doctor_card = StudioCard(
            self.doctor_name,
            current_number,
        )

        self.doctor_card.number_changed.connect(
            self.controller.set_number
        )

    def _build_queue_controls(self) -> None:
        self.queue_status_label = QLabel()
        self.queue_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.queue_status_label.setFixedHeight(
            24
        )

        self.queue_button = QPushButton()
        self.queue_button.setFixedHeight(
            56
        )
        self.queue_button.clicked.connect(
            self.controller.toggle_queue
        )

    def _build_action_controls(self) -> None:
        self.display_button = QPushButton(
            "🖥  Display sala d'attesa"
        )
        self.display_button.setObjectName(
            "displayCompactButton"
        )
        self.display_button.setFixedHeight(
            46
        )
        self.display_button.clicked.connect(
            self.controller.open_display
        )

        self.dashboard_button = QPushButton(
            "Dashboard"
        )
        self.dashboard_button.setObjectName(
            "dashboardCompactButton"
        )
        self.dashboard_button.setFixedHeight(
            46
        )
        self.dashboard_button.clicked.connect(
            lambda: self.controller.open_dashboard(
                self
            )
        )

        self.history_button = QPushButton(
            "Storico"
        )
        self.history_button.setObjectName(
            "historyCompactButton"
        )
        self.history_button.setFixedHeight(
            46
        )
        self.history_button.clicked.connect(
            lambda: self.controller.open_history(
                self
            )
        )

        self.secondary_buttons_layout = (
            QHBoxLayout()
        )
        self.secondary_buttons_layout.setSpacing(
            12
        )

        self.secondary_buttons_layout.addWidget(
            self.dashboard_button,
            stretch=1,
        )
        self.secondary_buttons_layout.addWidget(
            self.history_button,
            stretch=1,
        )

    def _build_network_area(self) -> None:
        self.network_separator = QFrame()
        self.network_separator.setObjectName(
            "networkSeparator"
        )
        self.network_separator.setFrameShape(
            QFrame.Shape.HLine
        )

        self.network_summary_label = QLabel()
        self.network_summary_label.setObjectName(
            "networkSummary"
        )
        self.network_summary_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.network_summary_label.setFixedHeight(
            26
        )

    def _build_settings_button(self) -> None:
        self.settings_button = QPushButton(
            "⚙  Impostazioni"
        )
        self.settings_button.setObjectName(
            "settingsButton"
        )
        self.settings_button.setFixedHeight(
            46
        )
        self.settings_button.clicked.connect(
            lambda: self.controller.open_settings(
                self
            )
        )

    def _build_layout(
        self,
        central_widget: QWidget,
    ) -> None:
        main_layout = QVBoxLayout(
            central_widget
        )

        main_layout.setContentsMargins(
            36,
            18,
            36,
            20,
        )
        main_layout.setSpacing(
            8
        )

        main_layout.addWidget(
            self.title_label
        )
        main_layout.addWidget(
            self.subtitle_label
        )

        main_layout.addSpacing(4)

        main_layout.addWidget(
            self.doctor_card
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
        main_layout.addLayout(
            self.secondary_buttons_layout
        )

        main_layout.addWidget(
            self.network_separator
        )
        main_layout.addWidget(
            self.network_summary_label
        )
        main_layout.addWidget(
            self.settings_button
        )

        main_layout.addStretch()

    def _connect_controller(self) -> None:
        self.controller.state_changed.connect(
            self.on_shared_state_changed
        )

        self.controller.network_role_changed.connect(
            self.update_network_role
        )

        self.controller.network_status_changed.connect(
            self.update_network_status
        )

        self.controller.sync_status_changed.connect(
            self.update_sync_status
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
            self.queue_active = queue_active
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
            self.current_network_role = "Server"
        elif role == "client":
            self.current_network_role = "Client"
        else:
            self.current_network_role = (
                "Inizializzazione"
            )

        self._update_network_summary()

    def update_network_status(
        self,
        status: str,
    ) -> None:
        self._update_network_summary()

    def update_sync_status(
        self,
        status: str,
    ) -> None:
        clean_status = str(status).strip()

        if clean_status:
            self.current_sync_status = clean_status

        self._update_network_summary()

    def update_server_address(
        self,
        server_address: str,
    ) -> None:
        self.current_server_address = str(
            server_address
        ).strip()

        self._update_network_summary()

    def _update_network_summary(self) -> None:
        sync_text = self._simplify_sync_status(
            self.current_sync_status
        )

        parts = [
            self.current_network_role,
            sync_text,
        ]

        if (
            self.current_network_role == "Client"
            and self.current_server_address
        ):
            parts.append(
                self.current_server_address
            )

        self.network_summary_label.setText(
            "  •  ".join(parts)
        )

    @staticmethod
    def _simplify_sync_status(
        status: str,
    ) -> str:
        clean_status = str(status).strip()
        lowered = clean_status.lower()

        if (
            "completata" in lowered
            or "collegato" in lowered
            or "gestito da questo computer"
            in lowered
        ):
            return "Sincronizzato"

        return "Sincronizzazione in corso"

    @staticmethod
    def _safe_number(
        value: Any,
    ) -> int:
        try:
            return max(0, int(value))
        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _refresh_widget_style(
        widget: QWidget,
    ) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @staticmethod
    def _additional_style() -> str:
        return """
        QPushButton#displayCompactButton {
            background-color: #dce8f1;
            color: #234f6e;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
        }

        QPushButton#dashboardCompactButton {
            background-color: #2c6088;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
        }

        QPushButton#historyCompactButton {
            background-color: #dfe7ee;
            color: #29485e;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
        }

        QFrame#networkSeparator {
            background-color: #ccd9e3;
            border: none;
            min-height: 1px;
            max-height: 1px;
        }

        QLabel#networkSummary {
            color: #176b9c;
            font-size: 14px;
            font-weight: 700;
        }
        """

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.controller.close()
        event.accept()