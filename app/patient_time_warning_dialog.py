from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.resources import app_icon


class PatientTimeWarningDialog(QDialog):
    """Avviso visivo a schermo intero per tempo paziente superato."""

    def __init__(
        self,
        ticket: str,
        elapsed_text: str,
        threshold_minutes: int,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._allow_close = False

        self.setWindowTitle("Avviso tempo paziente")
        self.setWindowIcon(app_icon())
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setObjectName("patientTimeWarningDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(70, 70, 70, 70)
        outer.addStretch(1)

        card = QFrame()
        card.setObjectName("warningCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(60, 55, 60, 55)
        card_layout.setSpacing(26)

        icon_label = QLabel("⚠")
        icon_label.setObjectName("warningIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("TEMPO PAZIENTE SUPERATO")
        title.setObjectName("warningTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        card_layout.addWidget(title)

        ticket_label = QLabel(ticket or "Paziente")
        ticket_label.setObjectName("warningTicket")
        ticket_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(ticket_label)

        elapsed_label = QLabel(elapsed_text)
        elapsed_label.setObjectName("warningElapsed")
        elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(elapsed_label)

        message = QLabel(
            f"È stata superata la soglia impostata di "
            f"{threshold_minutes} min."
        )
        message.setObjectName("warningMessage")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        card_layout.addWidget(message)

        self.ok_button = QPushButton("OK")
        self.ok_button.setObjectName("warningOkButton")
        self.ok_button.setMinimumHeight(76)
        self.ok_button.clicked.connect(self._acknowledge)
        card_layout.addWidget(self.ok_button)

        outer.addWidget(card)
        outer.addStretch(1)

        self.setStyleSheet(
            """
            QDialog#patientTimeWarningDialog {
                background-color: #7a1712;
            }

            QFrame#warningCard {
                background-color: #fff7f6;
                border: 4px solid #f04438;
                border-radius: 28px;
            }

            QLabel#warningIcon {
                color: #d92d20;
                font-size: 82px;
                font-weight: 900;
            }

            QLabel#warningTitle {
                color: #b42318;
                font-size: 42px;
                font-weight: 900;
            }

            QLabel#warningTicket {
                color: #12344d;
                font-size: 72px;
                font-weight: 900;
            }

            QLabel#warningElapsed {
                color: #b42318;
                font-size: 58px;
                font-weight: 900;
            }

            QLabel#warningMessage {
                color: #475467;
                font-size: 24px;
                font-weight: 700;
            }

            QPushButton#warningOkButton {
                background-color: #198754;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 28px;
                font-weight: 900;
                padding: 14px 36px;
            }

            QPushButton#warningOkButton:hover {
                background-color: #157347;
            }

            QPushButton#warningOkButton:pressed {
                background-color: #0f5f3b;
            }
            """
        )

    def show_warning(self) -> None:
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.ok_button.setFocus()

    def _acknowledge(self) -> None:
        self._allow_close = True
        self.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)
