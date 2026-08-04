from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import load_config, save_config
from app.storage import load_turns, save_turns
from app.studio_card import StudioCard
from app.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.config = load_config()
        self.doctor_id = str(self.config["doctor_id"])
        self.doctor_name = str(self.config["doctor_name"])
        self.queue_active = bool(self.config.get("queue_active", False))

        turns = load_turns()
        current_number = turns.get(self.doctor_id, 0)

        self.setWindowTitle("Gestione Turni")
        self.setMinimumSize(650, 760)
        self.resize(760, 840)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        title_label = QLabel("GESTIONE TURNI")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Sistema di gestione turni")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.doctor_card = StudioCard(
            self.doctor_name,
            current_number,
        )
        self.doctor_card.number_changed.connect(
            self.save_current_turn
        )

        self.queue_status_label = QLabel()
        self.queue_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.queue_button = QPushButton()
        self.queue_button.setMinimumHeight(62)
        self.queue_button.clicked.connect(self.toggle_queue)

        self.settings_button = QPushButton("⚙ Impostazioni")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setMinimumHeight(58)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(48, 30, 48, 30)
        main_layout.setSpacing(16)
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.doctor_card, stretch=1)
        main_layout.addSpacing(4)
        main_layout.addWidget(self.queue_status_label)
        main_layout.addWidget(self.queue_button)
        main_layout.addWidget(self.settings_button)

        self.setStyleSheet(APP_STYLE)
        self.update_queue_ui()

    def save_current_turn(self) -> None:
        turns = load_turns()
        turns[self.doctor_id] = self.doctor_card.number
        save_turns(turns)

    def toggle_queue(self) -> None:
        self.queue_active = not self.queue_active

        self.config["queue_active"] = self.queue_active
        save_config(self.config)

        self.update_queue_ui()

    def update_queue_ui(self) -> None:
        if self.queue_active:
            self.queue_status_label.setText("● Coda attiva")
            self.queue_status_label.setObjectName("queueStatusActive")

            self.queue_button.setText("Termina coda")
            self.queue_button.setObjectName("queueStopButton")
        else:
            self.queue_status_label.setText("● Coda non attiva")
            self.queue_status_label.setObjectName("queueStatusInactive")

            self.queue_button.setText("Inizia coda")
            self.queue_button.setObjectName("queueStartButton")

        self.queue_status_label.style().unpolish(
            self.queue_status_label
        )
        self.queue_status_label.style().polish(
            self.queue_status_label
        )

        self.queue_button.style().unpolish(self.queue_button)
        self.queue_button.style().polish(self.queue_button)
