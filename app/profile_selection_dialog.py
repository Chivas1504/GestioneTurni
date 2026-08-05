from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ProfileSelectionDialog(QDialog):
    def __init__(
        self,
        *,
        profiles: list[dict[str, object]],
    ) -> None:
        super().__init__()

        self.selected_profile: str | None = None

        self.setWindowTitle(
            "Seleziona medico"
        )
        self.setModal(True)
        self.setFixedSize(
            660,
            430,
        )

        title_label = QLabel(
            "GESTIONE TURNI"
        )
        title_label.setObjectName(
            "profileTitle"
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        subtitle_label = QLabel(
            "Seleziona il medico che utilizzerà questo computer"
        )
        subtitle_label.setObjectName(
            "profileSubtitle"
        )
        subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        subtitle_label.setWordWrap(True)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(18)

        for profile in profiles:
            cards_layout.addWidget(
                self._create_profile_card(
                    profile
                ),
                stretch=1,
            )

        cancel_button = QPushButton(
            "Chiudi"
        )
        cancel_button.setObjectName(
            "profileCancelButton"
        )
        cancel_button.setMinimumHeight(46)
        cancel_button.clicked.connect(
            self.reject
        )

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(
            cancel_button
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            34,
            28,
            34,
            26,
        )
        main_layout.setSpacing(18)

        main_layout.addWidget(
            title_label
        )
        main_layout.addWidget(
            subtitle_label
        )
        main_layout.addSpacing(4)
        main_layout.addLayout(
            cards_layout,
            stretch=1,
        )
        main_layout.addLayout(
            bottom_layout
        )

        self._apply_style()

    def _create_profile_card(
        self,
        profile: dict[str, object],
    ) -> QFrame:
        doctor_id = str(
            profile.get(
                "doctor_id",
                "",
            )
        )

        doctor_name = str(
            profile.get(
                "doctor_name",
                "",
            )
        ).strip()

        configured = bool(
            profile.get(
                "configured",
                False,
            )
        )

        card = QFrame()
        card.setObjectName(
            "profileCard"
        )

        icon_label = QLabel(
            "MEDICO"
        )
        icon_label.setObjectName(
            "profileIcon"
        )
        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        name_label = QLabel(
            doctor_name
        )
        name_label.setObjectName(
            "profileName"
        )
        name_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        name_label.setWordWrap(True)

        status_label = QLabel(
            "Profilo configurato"
            if configured
            else "Da configurare"
        )
        status_label.setObjectName(
            (
                "profileConfigured"
                if configured
                else "profileNotConfigured"
            )
        )
        status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        open_button = QPushButton(
            "Apri profilo"
            if configured
            else "Configura profilo"
        )
        open_button.setObjectName(
            "profileOpenButton"
        )
        open_button.setMinimumHeight(52)
        open_button.clicked.connect(
            lambda checked=False, value=doctor_id:
            self._select_profile(value)
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            22,
            22,
            22,
            22,
        )
        layout.setSpacing(12)

        layout.addWidget(
            icon_label
        )
        layout.addWidget(
            name_label
        )
        layout.addWidget(
            status_label
        )
        layout.addStretch()
        layout.addWidget(
            open_button
        )

        return card

    def _select_profile(
        self,
        profile_id: str,
    ) -> None:
        if profile_id not in {
            "doctor1",
            "doctor2",
        }:
            return

        self.selected_profile = profile_id
        self.accept()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #eef3f8;
            }

            QLabel#profileTitle {
                color: #16324a;
                font-size: 30px;
                font-weight: 900;
                letter-spacing: 2px;
            }

            QLabel#profileSubtitle {
                color: #60758a;
                font-size: 16px;
                font-weight: 600;
            }

            QFrame#profileCard {
                background-color: white;
                border: 1px solid #d3dfe8;
                border-radius: 18px;
            }

            QLabel#profileIcon {
                color: #2c6088;
                font-size: 15px;
                font-weight: 900;
                letter-spacing: 2px;
                padding: 10px;
            }

            QLabel#profileName {
                color: #183b56;
                font-size: 23px;
                font-weight: 900;
            }

            QLabel#profileConfigured {
                color: #218b5d;
                font-size: 14px;
                font-weight: 800;
            }

            QLabel#profileNotConfigured {
                color: #a46a21;
                font-size: 14px;
                font-weight: 800;
            }

            QPushButton#profileOpenButton {
                background-color: #218b5d;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 17px;
                font-weight: 800;
                padding: 10px 18px;
            }

            QPushButton#profileOpenButton:hover {
                background-color: #19794f;
            }

            QPushButton#profileOpenButton:pressed {
                background-color: #126b43;
            }

            QPushButton#profileCancelButton {
                background-color: #dfe7ee;
                color: #334b5d;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
                padding: 8px 22px;
            }

            QPushButton#profileCancelButton:hover {
                background-color: #d2dde6;
            }
            """
        )
