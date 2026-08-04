from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.studio_card import StudioCard
from app.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Gestione Turni")
        self.setMinimumSize(950, 620)
        self.resize(1100, 680)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        title_label = QLabel("GESTIONE TURNI")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Sistema di gestione turni")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.studio1_card = StudioCard("Studio 1")
        self.studio2_card = StudioCard("Studio 2")

        studios_layout = QHBoxLayout()
        studios_layout.setSpacing(24)
        studios_layout.addWidget(self.studio1_card)
        studios_layout.addWidget(self.studio2_card)

        self.display_button = QPushButton("Apri display TV")
        self.display_button.setObjectName("displayButton")
        self.display_button.setMinimumHeight(62)

        self.settings_button = QPushButton("⚙ Impostazioni")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setMinimumHeight(62)

        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setSpacing(16)
        bottom_buttons_layout.addStretch()
        bottom_buttons_layout.addWidget(self.display_button)
        bottom_buttons_layout.addWidget(self.settings_button)
        bottom_buttons_layout.addStretch()

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(38, 26, 38, 26)
        main_layout.setSpacing(14)
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addSpacing(8)
        main_layout.addLayout(studios_layout, stretch=1)
        main_layout.addSpacing(6)
        main_layout.addLayout(bottom_buttons_layout)

        self.setStyleSheet(APP_STYLE)