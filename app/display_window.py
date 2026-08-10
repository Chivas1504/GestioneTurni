from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.shared_state import SharedState


from app.resources import app_icon

class DoctorDisplayCard(QFrame):
    def __init__(
        self,
        doctor_id: str,
        doctor_name: str,
        number: int,
        queue_prefix: str = "",
    ) -> None:
        super().__init__()

        self.doctor_id = doctor_id
        self._number = number
        self._queue_prefix = self._clean_prefix(queue_prefix)

        self.setObjectName(
            "doctorCard1"
            if doctor_id == "doctor1"
            else "doctorCard2"
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.name_label = QLabel(doctor_name)
        self.name_label.setObjectName("displayDoctorName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)

        self.called_label = QLabel("NUMERO ATTUALMENTE CHIAMATO")
        self.called_label.setObjectName("displayCalledLabel")
        self.called_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.number_label = QLabel(self._formatted_number())
        self.number_label.setObjectName("displayDoctorNumber")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.status_label = QLabel("Recarsi presso lo studio indicato")
        self.status_label.setObjectName("displayDoctorStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(34, 30, 34, 30)
        card_layout.setSpacing(10)
        card_layout.addWidget(self.name_label)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.called_label)
        card_layout.addStretch()
        card_layout.addWidget(self.number_label, stretch=1)
        card_layout.addStretch()
        card_layout.addWidget(self.status_label)

        self._apply_shadow()

    def update_doctor(
        self,
        doctor_name: str,
        number: int,
        queue_prefix: str = "",
    ) -> None:
        self.name_label.setText(doctor_name)
        clean_prefix = self._clean_prefix(queue_prefix)

        if number == self._number and clean_prefix == self._queue_prefix:
            return

        self._number = number
        self._queue_prefix = clean_prefix
        self.number_label.setText(self._formatted_number())

    def _formatted_number(self) -> str:
        return f"{self._queue_prefix}{self._number}"

    @staticmethod
    def _clean_prefix(value: object) -> str:
        text = str(value or "").strip().upper()
        if not text:
            return ""
        first = text[0]
        return first if "A" <= first <= "Z" else ""

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 85))
        self.setGraphicsEffect(shadow)


class DisplayWindow(QMainWindow):
    def __init__(
        self,
        shared_state: SharedState,
    ) -> None:
        super().__init__()

        self.setWindowIcon(app_icon())

        self.shared_state = shared_state
        self.doctor_cards: dict[str, DoctorDisplayCard] = {}

        self.setWindowTitle("Gestione Turni - Display")
        self.setMinimumSize(900, 600)
        self.resize(1280, 720)

        self._build_interface()
        self._apply_style()
        self._start_clock()

        self.shared_state.state_changed.connect(self.update_display)

        self.update_clock()
        self.update_display(self.shared_state.get_all())

    def _build_interface(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("displayCentralWidget")
        self.setCentralWidget(central_widget)

        self.brand_label = QLabel("STUDIO MEDICO")
        self.brand_label.setObjectName("displayBrand")
        self.brand_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.title_label = QLabel("GESTIONE TURNI")
        self.title_label.setObjectName("displayTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.clock_label = QLabel()
        self.clock_label.setObjectName("displayClock")
        self.clock_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(20)
        header_layout.addWidget(self.brand_label, stretch=1)
        header_layout.addWidget(self.title_label, stretch=2)
        header_layout.addWidget(self.clock_label, stretch=1)

        self.header_line = QFrame()
        self.header_line.setObjectName("displayHeaderLine")
        self.header_line.setFrameShape(QFrame.Shape.HLine)

        self.empty_container = QFrame()
        self.empty_container.setObjectName("emptyContainer")

        self.empty_title_label = QLabel("Nessuna coda attiva")
        self.empty_title_label.setObjectName("displayEmptyTitle")
        self.empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_message_label = QLabel(
            "Il servizio riprenderà quando uno studio "
            "avvierà la propria coda."
        )
        self.empty_message_label.setObjectName("displayEmptyMessage")
        self.empty_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_message_label.setWordWrap(True)

        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setContentsMargins(40, 40, 40, 40)
        empty_layout.setSpacing(18)
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_title_label)
        empty_layout.addWidget(self.empty_message_label)
        empty_layout.addStretch()

        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsContainer")

        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(28)

        self.footer_line = QFrame()
        self.footer_line.setObjectName("displayFooterLine")
        self.footer_line.setFrameShape(QFrame.Shape.HLine)

        self.footer_label = QLabel(
            "Attendere il proprio turno e controllare "
            "il numero sullo schermo"
        )
        self.footer_label.setObjectName("displayFooter")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setWordWrap(True)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(42, 24, 42, 26)
        main_layout.setSpacing(18)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.header_line)
        main_layout.addWidget(self.empty_container, stretch=1)
        main_layout.addWidget(self.cards_container, stretch=1)
        main_layout.addWidget(self.footer_line)
        main_layout.addWidget(self.footer_label)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #071a2a;
            }

            QWidget#displayCentralWidget {
                background-color: #071a2a;
            }

            QWidget#cardsContainer {
                background-color: transparent;
            }

            QLabel#displayBrand {
                color: #9fc6e4;
                font-size: 22px;
                font-weight: 700;
                letter-spacing: 2px;
            }

            QLabel#displayTitle {
                color: white;
                font-size: 42px;
                font-weight: 900;
                letter-spacing: 4px;
            }

            QLabel#displayClock {
                color: #dcecf8;
                font-size: 32px;
                font-weight: 800;
            }

            QFrame#displayHeaderLine,
            QFrame#displayFooterLine {
                background-color: rgba(255, 255, 255, 35);
                border: none;
                min-height: 1px;
                max-height: 1px;
            }

            QFrame#emptyContainer {
                background-color: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 28px;
            }

            QLabel#displayEmptyTitle {
                color: white;
                font-size: 48px;
                font-weight: 800;
            }

            QLabel#displayEmptyMessage {
                color: #bddbf2;
                font-size: 26px;
                font-weight: 500;
            }

            QFrame#doctorCard1,
            QFrame#doctorCard2 {
                background-color: #f7fafc;
                border-radius: 30px;
            }

            QFrame#doctorCard1 {
                border-top: 16px solid #2e7db8;
            }

            QFrame#doctorCard2 {
                border-top: 16px solid #2a9b6c;
            }

            QLabel#displayDoctorName {
                color: #183b56;
                font-size: 42px;
                font-weight: 900;
            }

            QLabel#displayCalledLabel {
                color: #6c8192;
                font-size: 17px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            QLabel#displayDoctorNumber {
                color: #145f91;
                font-size: 250px;
                font-weight: 900;
            }

            QFrame#doctorCard2 QLabel#displayDoctorNumber {
                color: #167449;
            }

            QLabel#displayDoctorStatus {
                color: #60758a;
                font-size: 20px;
                font-weight: 600;
            }

            QLabel#displayFooter {
                color: #dcecf8;
                font-size: 22px;
                font-weight: 600;
            }
            """
        )

    def _start_clock(self) -> None:
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

    def update_clock(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%H:%M"))

    def apply_preferences(
        self,
        *,
        show_clock: bool,
    ) -> None:
        self.clock_label.setVisible(bool(show_clock))

    def update_display(
        self,
        complete_state: object,
    ) -> None:
        if not isinstance(complete_state, dict):
            return

        active_doctors = self._extract_active_doctors(complete_state)

        if not active_doctors:
            self._show_empty_state()
            return

        self._show_active_queues(active_doctors)

    def _extract_active_doctors(
        self,
        complete_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        active_doctors: list[dict[str, Any]] = []

        for doctor_id in ("doctor1", "doctor2"):
            doctor_state = complete_state.get(doctor_id)

            if not isinstance(doctor_state, dict):
                continue

            if not bool(doctor_state.get("online", False)):
                continue

            if not bool(doctor_state.get("queue_active", False)):
                continue

            doctor_name = str(
                doctor_state.get("doctor_name", "Medico")
            ).strip()

            active_doctors.append(
                {
                    "doctor_id": doctor_id,
                    "doctor_name": doctor_name or "Medico",
                    "queue_prefix": str(
                        doctor_state.get("queue_prefix", "")
                    ).strip().upper()[:1],
                    "number": self._safe_number(
                        doctor_state.get("number", 0)
                    ),
                }
            )

        return active_doctors

    def _show_empty_state(self) -> None:
        self._clear_cards()
        self.cards_container.hide()
        self.footer_label.hide()
        self.footer_line.hide()
        self.empty_container.show()

    def _show_active_queues(
        self,
        active_doctors: list[dict[str, Any]],
    ) -> None:
        self.empty_container.hide()
        self.cards_container.show()
        self.footer_line.show()
        self.footer_label.show()

        active_ids = {
            str(doctor["doctor_id"])
            for doctor in active_doctors
        }

        for doctor_id in list(self.doctor_cards):
            if doctor_id in active_ids:
                continue

            card = self.doctor_cards.pop(doctor_id)
            self.cards_layout.removeWidget(card)
            card.deleteLater()

        for doctor in active_doctors:
            doctor_id = str(doctor["doctor_id"])
            doctor_name = str(doctor["doctor_name"])
            number = self._safe_number(doctor["number"])
            queue_prefix = str(doctor.get("queue_prefix", ""))

            existing_card = self.doctor_cards.get(doctor_id)

            if existing_card is None:
                card = DoctorDisplayCard(
                    doctor_id=doctor_id,
                    doctor_name=doctor_name,
                    number=number,
                    queue_prefix=queue_prefix,
                )
                self.doctor_cards[doctor_id] = card
                self.cards_layout.addWidget(card, stretch=1)
            else:
                existing_card.update_doctor(
                    doctor_name=doctor_name,
                    number=number,
                    queue_prefix=queue_prefix,
                )

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ) -> None:
        if event.key() in {
            Qt.Key.Key_Escape,
            Qt.Key.Key_F11,
        }:
            self.toggle_fullscreen()
            return

        super().keyPressEvent(event)

    def mouseDoubleClickEvent(
        self,
        event,
    ) -> None:
        self.toggle_fullscreen()
        super().mouseDoubleClickEvent(event)

    def _clear_cards(self) -> None:
        for card in self.doctor_cards.values():
            self.cards_layout.removeWidget(card)
            card.deleteLater()

        self.doctor_cards.clear()

    @staticmethod
    def _safe_number(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0
