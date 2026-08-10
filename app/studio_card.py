from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class StudioCard(QFrame):

    number_changed = Signal(int, str)

    def __init__(
        self,
        studio_name: str,
        number: int = 0,
        queue_prefix: str = "",
    ) -> None:
        super().__init__()

        self._number = self._safe_number(number)
        self._queue_prefix = self._clean_prefix(queue_prefix)

        self.setObjectName("studioCard")

        self.setMinimumHeight(320)
        self.setMaximumHeight(350)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._build_interface(studio_name)
        self._apply_style()

    @property
    def number(self) -> int:
        return self._number

    def _build_interface(
        self,
        studio_name: str,
    ) -> None:
        self.name_label = QLabel(
            self._clean_studio_name(studio_name)
        )
        self.name_label.setObjectName(
            "studioCardName"
        )
        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(42)

        self.number_label = QLabel(
            self._formatted_number()
        )
        self.number_label.setObjectName(
            "studioCardNumber"
        )
        self.number_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.number_label.setMinimumHeight(105)
        self.number_label.setMaximumHeight(125)

        self.decrement_button = QPushButton(
            "−1"
        )
        self.decrement_button.setObjectName(
            "studioDecrementButton"
        )
        self.decrement_button.setFixedHeight(56)
        self.decrement_button.clicked.connect(
            self.decrement
        )

        self.increment_button = QPushButton(
            "+1"
        )
        self.increment_button.setObjectName(
            "studioIncrementButton"
        )
        self.increment_button.setFixedHeight(56)
        self.increment_button.clicked.connect(
            self.increment
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        buttons_layout.setSpacing(14)

        buttons_layout.addWidget(
            self.decrement_button,
            stretch=1,
        )
        buttons_layout.addWidget(
            self.increment_button,
            stretch=1,
        )

        self.reset_button = QPushButton(
            "Reset"
        )
        self.reset_button.setObjectName(
            "studioResetButton"
        )
        self.reset_button.setFixedHeight(42)
        self.reset_button.clicked.connect(
            self.confirm_reset
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            24,
            16,
            24,
            18,
        )
        main_layout.setSpacing(8)

        main_layout.addWidget(
            self.name_label
        )
        main_layout.addWidget(
            self.number_label
        )
        main_layout.addLayout(
            buttons_layout
        )
        main_layout.addWidget(
            self.reset_button
        )

    def increment(self) -> None:
        self._set_number_from_user(
            self._number + 1,
            action="increment",
        )

    def decrement(self) -> None:
        self._set_number_from_user(
            max(0, self._number - 1),
            action="decrement",
        )

    def confirm_reset(self) -> None:
        if self._number == 0:
            return

        answer = QMessageBox.question(
            self,
            "Conferma reset",
            (
                "Vuoi davvero azzerare "
                "il numero della coda?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.reset()

    def reset(self) -> None:
        self._set_number_from_user(
            0,
            action="reset",
        )

    def set_number(
        self,
        number: int,
    ) -> None:
        safe_number = self._safe_number(number)

        if safe_number == self._number:
            return

        self._number = safe_number
        self.number_label.setText(
            self._formatted_number()
        )

    def set_queue_prefix(self, queue_prefix: str) -> None:
        clean_prefix = self._clean_prefix(queue_prefix)
        if clean_prefix == self._queue_prefix:
            return
        self._queue_prefix = clean_prefix
        self.number_label.setText(self._formatted_number())

    def set_studio_name(
        self,
        studio_name: str,
    ) -> None:
        self.name_label.setText(
            self._clean_studio_name(
                studio_name
            )
        )

    def _set_number_from_user(
        self,
        number: int,
        *,
        action: str,
    ) -> None:
        safe_number = self._safe_number(number)

        if safe_number == self._number:
            return

        self._number = safe_number
        self.number_label.setText(
            self._formatted_number()
        )

        self.number_changed.emit(
            self._number,
            action,
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QFrame#studioCard {
                background-color: white;
                border: 1px solid #d3dfe8;
                border-radius: 22px;
            }

            QLabel#studioCardName {
                color: #183b56;
                font-size: 25px;
                font-weight: 900;
            }

            QLabel#studioCardNumber {
                color: #17689c;
                font-size: 94px;
                font-weight: 900;
                padding: 0;
                margin: 0;
            }

            QPushButton {
                border: none;
                border-radius: 13px;
                font-size: 21px;
                font-weight: 800;
            }

            QPushButton#studioDecrementButton {
                background-color: #dfe8f0;
                color: #294c64;
            }

            QPushButton#studioDecrementButton:hover {
                background-color: #d2dee8;
            }

            QPushButton#studioDecrementButton:pressed {
                background-color: #c5d4df;
            }

            QPushButton#studioIncrementButton {
                background-color: #218b5d;
                color: white;
            }

            QPushButton#studioIncrementButton:hover {
                background-color: #19794f;
            }

            QPushButton#studioIncrementButton:pressed {
                background-color: #126b43;
            }

            QPushButton#studioResetButton {
                background-color: #f7e3e1;
                color: #ad392f;
                font-size: 15px;
                font-weight: 800;
                border-radius: 11px;
            }

            QPushButton#studioResetButton:hover {
                background-color: #f1d4d1;
            }

            QPushButton#studioResetButton:pressed {
                background-color: #eac5c1;
            }
            """
        )

    def _formatted_number(self) -> str:
        return f"{self._queue_prefix}{self._number}"

    @staticmethod
    def _clean_prefix(value: object) -> str:
        text = str(value or "").strip().upper()
        if not text:
            return ""
        first = text[0]
        return first if "A" <= first <= "Z" else ""

    @staticmethod
    def _safe_number(
        value: object,
    ) -> int:
        try:
            return max(0, int(value))
        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _clean_studio_name(
        value: object,
    ) -> str:
        clean_name = str(value).strip()

        if clean_name:
            return clean_name

        return "Medico"
