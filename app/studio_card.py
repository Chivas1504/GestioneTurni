from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class StudioCard(QFrame):

    number_changed = Signal(int, str)
    surname_changed = Signal(str)

    def __init__(
        self,
        studio_name: str,
        number: int = 0,
        queue_prefix: str = "",
        queue_mode: str = "number",
        current_surname: str = "",
    ) -> None:
        super().__init__()

        self._number = self._safe_number(number)
        self._queue_prefix = self._clean_prefix(queue_prefix)
        self._queue_mode = self._clean_queue_mode(queue_mode)
        self._surname = self._clean_surname(current_surname)

        self.setObjectName("studioCard")
        self._compact_mode = False

        self.setMinimumHeight(310)
        self.setMaximumHeight(350)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._build_interface(studio_name)
        self._refresh_mode_ui()
        self._apply_style()

    @property
    def number(self) -> int:
        return self._number

    @property
    def surname(self) -> str:
        return self._surname

    @property
    def queue_mode(self) -> str:
        return self._queue_mode

    def _build_interface(self, studio_name: str) -> None:
        self.name_label = QLabel(self._clean_studio_name(studio_name))
        self.name_label.setObjectName("studioCardName")
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(36)
        self.mode_badge = QLabel()
        self.mode_badge.setObjectName("studioModeBadge")
        self.mode_badge.setFixedHeight(30)
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header = QHBoxLayout()
        header.addWidget(self.name_label, 1)
        header.addWidget(self.mode_badge)
        self.value_caption = QLabel()
        self.value_caption.setObjectName("studioValueCaption")
        self.value_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_caption.setFixedHeight(22)
        self.number_label = QLabel()
        self.number_label.setObjectName("studioCardNumber")
        self.number_label.setTextFormat(Qt.TextFormat.PlainText)
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_label.setWordWrap(True)
        self.number_label.setMinimumHeight(94)
        self.number_label.setMaximumHeight(132)
        self.number_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.decrement_button = QPushButton("Precedente  −1")
        self.decrement_button.setObjectName("studioDecrementButton")
        self.decrement_button.setFixedHeight(46)
        self.decrement_button.setToolTip("Diminuisci il numero chiamato di uno")
        self.decrement_button.clicked.connect(self.decrement)
        self.increment_button = QPushButton("Chiama successivo  +1")
        self.increment_button.setObjectName("studioIncrementButton")
        self.increment_button.setFixedHeight(46)
        self.increment_button.clicked.connect(self.increment)
        numbers = QHBoxLayout()
        numbers.setSpacing(10)
        numbers.addWidget(self.decrement_button, 1)
        numbers.addWidget(self.increment_button, 2)

        self.manual_number_input = QLineEdit()
        self.manual_number_input.setObjectName("studioManualNumberInput")
        self.manual_number_input.setPlaceholderText("Numero manuale")
        self.manual_number_input.setValidator(QIntValidator(0, 999999, self))
        self.manual_number_input.setFixedHeight(36)
        self.manual_number_input.returnPressed.connect(self.set_manual_number)
        self.manual_number_button = QPushButton("Imposta")
        self.manual_number_button.setObjectName("studioManualNumberButton")
        self.manual_number_button.setFixedSize(88, 36)
        self.manual_number_button.clicked.connect(self.set_manual_number)

        self.surname_input = QLineEdit()
        self.surname_input.setObjectName("studioSurnameInput")
        self.surname_input.setPlaceholderText("Cognome del paziente")
        self.surname_input.setMaxLength(60)
        self.surname_input.setFixedHeight(46)
        self.surname_input.returnPressed.connect(self.call_surname)
        self.surname_button = QPushButton("Chiama paziente")
        self.surname_button.setObjectName("studioSurnameButton")
        self.surname_button.setFixedHeight(46)
        self.surname_button.clicked.connect(self.call_surname)
        surnames = QHBoxLayout()
        surnames.setSpacing(10)
        surnames.addWidget(self.surname_input, 2)
        surnames.addWidget(self.surname_button, 1)
        self.reset_button = QPushButton()
        self.reset_button.setObjectName("studioResetButton")
        self.reset_button.setFixedHeight(36)
        self.reset_button.clicked.connect(self.confirm_reset)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addWidget(self.manual_number_input, 1)
        footer.addWidget(self.manual_number_button)
        footer.addStretch()
        footer.addWidget(self.reset_button)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 18)
        self.main_layout.setSpacing(12)
        self.main_layout.addLayout(header)
        self.main_layout.addSpacing(4)
        self.main_layout.addWidget(self.value_caption)
        self.main_layout.addWidget(self.number_label, 1)
        self.main_layout.addSpacing(2)
        self.main_layout.addLayout(numbers)
        self.main_layout.addLayout(surnames)
        self.main_layout.addLayout(footer)

    def increment(self) -> None:
        if self._queue_mode != "number":
            return
        self._set_number_from_user(self._number + 1, action="increment")

    def decrement(self) -> None:
        if self._queue_mode != "number":
            return
        self._set_number_from_user(max(0, self._number - 1), action="decrement")

    def set_manual_number(self) -> None:
        if self._queue_mode != "number":
            return
        text = self.manual_number_input.text().strip()
        if not text:
            self.manual_number_input.setFocus()
            return
        self._set_number_from_user(self._safe_number(text), action="set")
        self.manual_number_input.clear()

    def call_surname(self) -> None:
        if self._queue_mode != "surname":
            return
        surname = self._clean_surname(self.surname_input.text())
        if not surname:
            self.surname_input.setFocus()
            return
        self._surname = surname
        self.number_label.setText(self._formatted_value())
        self._fit_value_font()
        self.surname_input.clear()
        self.surname_changed.emit(self._surname)

    def confirm_reset(self) -> None:
        if self._queue_mode == "surname":
            if not self._surname:
                return
            message = "Vuoi davvero cancellare il cognome attualmente chiamato?"
        else:
            if self._number == 0:
                return
            message = "Vuoi davvero azzerare il numero della coda?"

        answer = QMessageBox.question(
            self,
            "Conferma reset",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.reset()

    def reset(self) -> None:
        if self._queue_mode == "surname":
            self._surname = ""
            self.number_label.setText(self._formatted_value())
            self._fit_value_font()
            self.surname_changed.emit("")
            return
        self._set_number_from_user(0, action="reset")

    def set_number(self, number: int) -> None:
        safe_number = self._safe_number(number)
        if safe_number == self._number:
            return
        self._number = safe_number
        if self._queue_mode == "number":
            self.number_label.setText(self._formatted_value())
        self._fit_value_font()

    def set_surname(self, surname: str) -> None:
        clean_surname = self._clean_surname(surname)
        if clean_surname == self._surname:
            return
        self._surname = clean_surname
        if self._queue_mode == "surname":
            self.number_label.setText(self._formatted_value())
        self._fit_value_font()

    def set_queue_prefix(self, queue_prefix: str) -> None:
        clean_prefix = self._clean_prefix(queue_prefix)
        if clean_prefix == self._queue_prefix:
            return
        self._queue_prefix = clean_prefix
        if self._queue_mode == "number":
            self.number_label.setText(self._formatted_value())
        self._fit_value_font()

    def set_queue_mode(self, queue_mode: str) -> None:
        clean_mode = self._clean_queue_mode(queue_mode)
        if clean_mode == self._queue_mode:
            return
        self._queue_mode = clean_mode
        self._refresh_mode_ui()
        self._apply_style()

    def set_studio_name(self, studio_name: str) -> None:
        self.name_label.setText(self._clean_studio_name(studio_name))

    def _set_number_from_user(self, number: int, *, action: str) -> None:
        safe_number = self._safe_number(number)
        if safe_number == self._number:
            return
        self._number = safe_number
        self.number_label.setText(self._formatted_value())
        self._fit_value_font()
        self.number_changed.emit(self._number, action)

    def _refresh_mode_ui(self) -> None:
        surname_mode = self._queue_mode == "surname"
        self.decrement_button.setVisible(not surname_mode)
        self.increment_button.setVisible(not surname_mode)
        self.manual_number_input.setVisible(not surname_mode)
        self.manual_number_button.setVisible(not surname_mode)
        self.surname_input.setVisible(surname_mode)
        self.surname_button.setVisible(surname_mode)
        self.reset_button.setText("Cancella chiamata" if surname_mode else "Azzera numero")
        self.value_caption.setText("PAZIENTE CHIAMATO" if surname_mode else "NUMERO CHIAMATO")
        self.mode_badge.setText("Appuntamenti" if surname_mode else "Numeri")
        self.number_label.setText(self._formatted_value())
        self._fit_value_font()

    def set_compact_mode(self, compact: bool) -> None:
        compact = bool(compact)
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        self.setMinimumHeight(282 if compact else 310)
        self.setMaximumHeight(310 if compact else 350)
        self.number_label.setMinimumHeight(78 if compact else 94)
        self.number_label.setMaximumHeight(112 if compact else 132)
        self.main_layout.setContentsMargins(18 if compact else 24, 16 if compact else 20,
                                           18 if compact else 24, 14 if compact else 18)
        self.main_layout.setSpacing(8 if compact else 12)
        self._apply_style()
        self.updateGeometry()

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QFrame#studioCard { background: #ffffff; border: 1px solid #dfe7ec; border-radius: 14px; }
            QLabel#studioCardName { color: #294653; font-size: 20px; font-weight: 600; }
            QLabel#studioModeBadge { color: #6c828e; background: #f0f5f7; border-radius: 8px; padding: 4px 10px; font-size: 11px; }
            QLabel#studioValueCaption { color: #8a9aa4; font-size: 11px; font-weight: 600; }
            QLabel#studioCardNumber { color: #173d4c; font-weight: 600; padding: 0; margin: 0; }
            QPushButton { border-radius: 8px; font-size: 14px; font-weight: 600; padding: 7px 12px; }
            QPushButton#studioDecrementButton { background: #f3f6f8; color: #536c7a; border: 1px solid #dfe7ec; }
            QPushButton#studioDecrementButton:hover { background: #e8f0f3; }
            QPushButton#studioIncrementButton, QPushButton#studioSurnameButton { background: #147d75; color: #ffffff; border: 1px solid #147d75; }
            QPushButton#studioIncrementButton:hover, QPushButton#studioSurnameButton:hover { background: #106c65; }
            QPushButton#studioIncrementButton:pressed, QPushButton#studioSurnameButton:pressed { background: #0c5b55; }
            QLineEdit { background: #ffffff; color: #234653; border: 1px solid #d7e1e7; border-radius: 8px; padding: 6px 10px; font-size: 14px; }
            QLineEdit:focus { border-color: #147d75; }
            QPushButton#studioManualNumberButton { background: #ffffff; color: #5b737f; border: 1px solid #dfe7ec; font-size: 12px; }
            QPushButton#studioManualNumberButton:hover { background: #f0f6f7; }
            QPushButton#studioResetButton { background: transparent; color: #a46961; border: 1px solid transparent; font-size: 12px; padding: 5px 8px; }
            QPushButton#studioResetButton:hover { background: #fcf1ef; color: #a14a43; }
        """)
        self._fit_value_font()

    def _fit_value_font(self) -> None:
        size = (38 if self._compact_mode else 48) if self._queue_mode == "surname" else (76 if self._compact_mode else 94)
        available_width = max(100, self.number_label.width() - 8)
        available_height = max(60, self.number_label.height() - 4)
        while size > 20:
            font = QFont("Segoe UI")
            font.setPixelSize(size)
            font.setWeight(QFont.Weight.DemiBold)
            bounds = QFontMetrics(font).boundingRect(0, 0, available_width, 1000,
                int(Qt.TextFlag.TextWordWrap), self._formatted_value())
            if bounds.width() <= available_width and bounds.height() <= available_height:
                break
            size -= 2
        self.number_label.setStyleSheet(f"font-size:{size}px;")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "number_label"):
            self._fit_value_font()

    def _formatted_value(self) -> str:
        if self._queue_mode == "surname":
            return self._surname.upper() if self._surname else "—"
        return f"{self._queue_prefix}{self._number}"

    @staticmethod
    def _clean_queue_mode(value: object) -> str:
        return "surname" if str(value or "").strip().lower() == "surname" else "number"

    @staticmethod
    def _clean_surname(value: object) -> str:
        return " ".join(str(value or "").strip().split())[:60]

    @staticmethod
    def _clean_prefix(value: object) -> str:
        text = str(value or "").strip().upper()
        if not text:
            return ""
        first = text[0]
        return first if "A" <= first <= "Z" else ""

    @staticmethod
    def _safe_number(value: object) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _clean_studio_name(value: object) -> str:
        clean_name = str(value).strip()
        return clean_name if clean_name else "Medico"
