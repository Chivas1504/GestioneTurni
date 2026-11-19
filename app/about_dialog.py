from __future__ import annotations

from app.styles import DIALOG_STYLE

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.resources import app_icon
from app.version import (
    APP_AUTHOR,
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle(f"Informazioni su {APP_NAME}")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setFixedSize(460, 390)

        icon_label = QLabel()
        icon_label.setPixmap(app_icon().pixmap(96, 96))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(APP_NAME)
        title_label.setObjectName("aboutTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version_label = QLabel(f"Versione {APP_VERSION}")
        version_label.setObjectName("aboutVersion")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description_label = QLabel(APP_DESCRIPTION)
        description_label.setObjectName("aboutDescription")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        author_label = QLabel(f"Sviluppato da {APP_AUTHOR}\n{APP_COPYRIGHT}")
        author_label.setObjectName("aboutAuthor")
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        close_button = QPushButton("Chiudi")
        close_button.setObjectName("aboutCloseButton")
        close_button.setMinimumHeight(46)
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 26, 36, 26)
        layout.setSpacing(14)
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addWidget(description_label)
        layout.addWidget(author_label)
        layout.addStretch()
        layout.addWidget(close_button)

        self.setStyleSheet(DIALOG_STYLE)
