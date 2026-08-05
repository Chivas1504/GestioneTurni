from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.shared_state import SharedState


class DoctorDisplayCard(QFrame):
    def __init__(
        self,
        doctor_name: str,
        number: int,
        object_name: str,
    ) -> None:
        super().__init__()

        self.setObjectName(object_name)

        self.name_label = QLabel(doctor_name)
        self.name_label.setObjectName(
            "displayDoctorName"
        )
        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.name_label.setWordWrap(True)

        self.number_label = QLabel(str(number))
        self.number_label.setObjectName(
            "displayDoctorNumber"
        )
        self.number_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            30,
            30,
            30,
            30,
        )
        layout.setSpacing(18)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.number_label)
        layout.addStretch()

    def update_doctor(
        self,
        doctor_name: str,
        number: int,
    ) -> None:
        self.name_label.setText(doctor_name)
        self.number_label.setText(str(number))


class DisplayWindow(QMainWindow):
    """
    Finestra destinata alla sala d'attesa.

    Con due code attive, ogni medico occupa metà schermo.
    Con una sola coda attiva, il medico occupa tutto lo spazio.
    """

    def __init__(
        self,
        shared_state: SharedState,
    ) -> None:
        super().__init__()

        self.shared_state = shared_state

        self.setWindowTitle(
            "Gestione Turni - Display"
        )
        self.setMinimumSize(900, 600)
        self.resize(1200, 720)

        central_widget = QWidget()
        central_widget.setObjectName(
            "displayCentralWidget"
        )
        self.setCentralWidget(
            central_widget
        )

        self.title_label = QLabel(
            "GESTIONE TURNI"
        )
        self.title_label.setObjectName(
            "displayTitle"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_label = QLabel(
            "Nessuna coda attiva"
        )
        self.empty_label.setObjectName(
            "displayEmpty"
        )
        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(
            self.cards_container
        )
        self.cards_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.cards_layout.setSpacing(24)

        main_layout = QVBoxLayout(
            central_widget
        )
        main_layout.setContentsMargins(
            36,
            28,
            36,
            36,
        )
        main_layout.setSpacing(24)
        main_layout.addWidget(
            self.title_label
        )
        main_layout.addWidget(
            self.empty_label,
            stretch=1,
        )
        main_layout.addWidget(
            self.cards_container,
            stretch=1,
        )

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #071a2a;
            }

            QWidget#displayCentralWidget {
                background-color: #071a2a;
            }

            QLabel#displayTitle {
                color: white;
                font-size: 44px;
                font-weight: 800;
                letter-spacing: 3px;
            }

            QLabel#displayEmpty {
                color: #bddbf2;
                font-size: 38px;
                font-weight: 700;
            }

            QFrame#doctorCard1,
            QFrame#doctorCard2 {
                background-color: white;
                border-radius: 28px;
            }

            QFrame#doctorCard1 {
                border-top: 14px solid #2e7db8;
            }

            QFrame#doctorCard2 {
                border-top: 14px solid #2a9b6c;
            }

            QLabel#displayDoctorName {
                color: #274760;
                font-size: 38px;
                font-weight: 800;
            }

            QLabel#displayDoctorNumber {
                color: #145f91;
                font-size: 220px;
                font-weight: 900;
            }
            """
        )

        self.shared_state.state_changed.connect(
            self.update_display
        )

        self.update_display(
            self.shared_state.get_all()
        )

    def update_display(
        self,
        complete_state: object,
    ) -> None:
        if not isinstance(
            complete_state,
            dict,
        ):
            return

        active_doctors: list[
            dict[str, Any]
        ] = []

        for doctor_id in (
            "doctor1",
            "doctor2",
        ):
            doctor_state = complete_state.get(
                doctor_id
            )

            if not isinstance(
                doctor_state,
                dict,
            ):
                continue

            if not bool(
                doctor_state.get(
                    "online",
                    False,
                )
            ):
                continue

            if not bool(
                doctor_state.get(
                    "queue_active",
                    False,
                )
            ):
                continue

            active_doctors.append(
                {
                    "doctor_id": doctor_id,
                    "doctor_name": str(
                        doctor_state.get(
                            "doctor_name",
                            "Medico",
                        )
                    ).strip()
                    or "Medico",
                    "number": self._safe_number(
                        doctor_state.get(
                            "number",
                            0,
                        )
                    ),
                }
            )

        self._clear_cards()

        if not active_doctors:
            self.empty_label.show()
            self.cards_container.hide()
            return

        self.empty_label.hide()
        self.cards_container.show()

        for index, doctor in enumerate(
            active_doctors
        ):
            card = DoctorDisplayCard(
                doctor_name=doctor[
                    "doctor_name"
                ],
                number=doctor["number"],
                object_name=(
                    "doctorCard1"
                    if index == 0
                    else "doctorCard2"
                ),
            )

            self.cards_layout.addWidget(
                card,
                stretch=1,
            )

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

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