from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class StudioCard(QFrame):
    def __init__(self, studio_name: str, number: int = 0) -> None:
        super().__init__()

        self._number = max(0, number)

        self.setObjectName("studioCard")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.setMaximumHeight(430)

        self.name_label = QLabel(studio_name)
        self.name_label.setObjectName("studioName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.number_label = QLabel(str(self._number))
        self.number_label.setObjectName("studioNumber")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.previous_button = QPushButton("−1")
        self.previous_button.setObjectName("previousButton")
        self.previous_button.setMinimumHeight(78)

        self.next_button = QPushButton("+1")
        self.next_button.setObjectName("nextButton")
        self.next_button.setMinimumHeight(78)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("resetButton")
        self.reset_button.setMinimumHeight(52)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(16)
        buttons_layout.addWidget(self.previous_button)
        buttons_layout.addWidget(self.next_button)

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(28, 24, 28, 28)
        card_layout.setSpacing(12)
        card_layout.addWidget(self.name_label)
        card_layout.addWidget(self.number_label, stretch=1)
        card_layout.addLayout(buttons_layout)
        card_layout.addWidget(self.reset_button)

        self.previous_button.clicked.connect(self.previous_number)
        self.next_button.clicked.connect(self.next_number)
        self.reset_button.clicked.connect(self.reset_number)

    @property
    def number(self) -> int:
        return self._number

    def next_number(self) -> None:
        self.set_number(self._number + 1)

    def previous_number(self) -> None:
        self.set_number(max(0, self._number - 1))

    def reset_number(self) -> None:
        self.set_number(0)
        
    def set_number(self, value: int) -> None:
        self._number = max(0, value)
        self.number_label.setText(str(self._number))
        self.animate_number()

    def set_studio_name(self, studio_name: str) -> None:
        self.name_label.setText(studio_name)

    def animate_number(self) -> None:
        self.animation = QPropertyAnimation(
            self.number_label,
            b"windowOpacity",
            self,
        )
        self.animation.setDuration(260)
        self.animation.setStartValue(0.25)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()