from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import load_config, save_config
from app.network import NetworkManager
from app.storage import load_turns, save_turns
from app.studio_card import StudioCard
from app.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.config = load_config()
        self.doctor_id = str(self.config["doctor_id"])
        self.doctor_name = str(self.config["doctor_name"])
        self.queue_active = bool(
            self.config.get("queue_active", False)
        )

        turns = load_turns()
        current_number = turns.get(self.doctor_id, 0)

        self.setWindowTitle("Gestione Turni")
        self.setMinimumSize(650, 800)
        self.resize(760, 880)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        title_label = QLabel("GESTIONE TURNI")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        subtitle_label = QLabel(
            "Sistema di gestione turni"
        )
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.doctor_card = StudioCard(
            self.doctor_name,
            current_number,
        )
        self.doctor_card.number_changed.connect(
            self.save_current_turn
        )

        self.queue_status_label = QLabel()
        self.queue_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.queue_button = QPushButton()
        self.queue_button.setMinimumHeight(62)
        self.queue_button.clicked.connect(
            self.toggle_queue
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

        self.settings_button = QPushButton(
            "⚙ Impostazioni"
        )
        self.settings_button.setObjectName(
            "settingsButton"
        )
        self.settings_button.setMinimumHeight(58)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(48, 30, 48, 30)
        main_layout.setSpacing(14)
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addSpacing(8)
        main_layout.addWidget(
            self.doctor_card,
            stretch=1,
        )
        main_layout.addWidget(
            self.queue_status_label
        )
        main_layout.addWidget(self.queue_button)
        main_layout.addSpacing(2)
        main_layout.addWidget(
            self.network_role_label
        )
        main_layout.addWidget(
            self.network_status_label
        )
        main_layout.addWidget(
            self.settings_button
        )

        self.setStyleSheet(APP_STYLE)
        self.update_queue_ui()

        self.network_manager = NetworkManager(
            self.doctor_id
        )
        self.network_manager.role_changed.connect(
            self.update_network_role
        )
        self.network_manager.status_changed.connect(
            self.network_status_label.setText
        )
        self.network_manager.server_address_changed.connect(
            self.update_server_address
        )
        self.network_manager.start()

    def save_current_turn(self) -> None:
        turns = load_turns()
        turns[self.doctor_id] = (
            self.doctor_card.number
        )
        save_turns(turns)

    def toggle_queue(self) -> None:
        self.queue_active = not self.queue_active

        self.config["queue_active"] = (
            self.queue_active
        )
        save_config(self.config)

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

    def update_network_role(self, role: str) -> None:
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
                "Ruolo rete: inizializzazione..."
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

        self.network_status_label.setText(
            f"{current_status}\n"
            f"Indirizzo server: {server_address}"
        )

    @staticmethod
    def _refresh_widget_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.network_manager.stop()
        event.accept()
