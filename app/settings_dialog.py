from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_config: dict[str, Any],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.saved_settings: dict[str, Any] | None = None

        self.setWindowTitle("Impostazioni")
        self.setModal(True)
        self.setMinimumSize(540, 430)
        self.resize(580, 470)

        title_label = QLabel("Impostazioni")
        title_label.setObjectName("settingsTitle")
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        description_label = QLabel(
            "Personalizza il medico e il comportamento "
            "del display condiviso."
        )
        description_label.setObjectName(
            "settingsDescription"
        )
        description_label.setWordWrap(True)
        description_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        section_doctor = QLabel("MEDICO")
        section_doctor.setObjectName("settingsSection")

        self.doctor_name_input = QLineEdit()
        self.doctor_name_input.setPlaceholderText(
            "Es. Dott.ssa Rossi"
        )
        self.doctor_name_input.setMaxLength(60)
        self.doctor_name_input.setMinimumHeight(46)
        self.doctor_name_input.setText(
            str(
                current_config.get(
                    "doctor_name",
                    "",
                )
            )
        )

        doctor_form = QFormLayout()
        doctor_form.setVerticalSpacing(14)
        doctor_form.addRow(
            "Nome visualizzato:",
            self.doctor_name_input,
        )

        section_display = QLabel("DISPLAY")
        section_display.setObjectName("settingsSection")

        self.fullscreen_checkbox = QCheckBox(
            "Apri automaticamente il display "
            "a schermo intero"
        )
        self.fullscreen_checkbox.setChecked(
            bool(
                current_config.get(
                    "display_fullscreen",
                    False,
                )
            )
        )

        self.clock_checkbox = QCheckBox(
            "Mostra l'orologio sul display"
        )
        self.clock_checkbox.setChecked(
            bool(
                current_config.get(
                    "display_show_clock",
                    True,
                )
            )
        )

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.setObjectName(
            "settingsCancelButton"
        )
        self.cancel_button.setMinimumHeight(50)
        self.cancel_button.clicked.connect(
            self.reject
        )

        self.save_button = QPushButton(
            "Salva impostazioni"
        )
        self.save_button.setObjectName(
            "settingsSaveButton"
        )
        self.save_button.setMinimumHeight(50)
        self.save_button.clicked.connect(
            self.save_and_accept
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(14)
        buttons_layout.addStretch()
        buttons_layout.addWidget(
            self.cancel_button
        )
        buttons_layout.addWidget(
            self.save_button
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            34,
            28,
            34,
            28,
        )
        main_layout.setSpacing(16)

        main_layout.addWidget(title_label)
        main_layout.addWidget(description_label)
        main_layout.addSpacing(8)

        main_layout.addWidget(section_doctor)
        main_layout.addLayout(doctor_form)

        main_layout.addSpacing(12)
        main_layout.addWidget(section_display)
        main_layout.addWidget(
            self.fullscreen_checkbox
        )
        main_layout.addWidget(
            self.clock_checkbox
        )

        main_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #eef3f8;
            }

            QLabel#settingsTitle {
                color: #16324a;
                font-size: 28px;
                font-weight: 800;
            }

            QLabel#settingsDescription {
                color: #60758a;
                font-size: 15px;
            }

            QLabel#settingsSection {
                color: #2c6088;
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            QLineEdit {
                background-color: white;
                color: #213d53;
                border: 1px solid #cbd8e3;
                border-radius: 10px;
                padding: 9px 12px;
                font-size: 16px;
            }

            QLineEdit:focus {
                border: 2px solid #218b5d;
            }

            QCheckBox {
                color: #2f4d63;
                font-size: 16px;
                spacing: 10px;
                padding: 5px 0;
            }

            QCheckBox::indicator {
                width: 22px;
                height: 22px;
            }

            QPushButton {
                border: none;
                border-radius: 12px;
                padding: 10px 22px;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#settingsCancelButton {
                background-color: #dfe7ee;
                color: #334b5d;
            }

            QPushButton#settingsCancelButton:hover {
                background-color: #d2dde6;
            }

            QPushButton#settingsSaveButton {
                background-color: #218b5d;
                color: white;
            }

            QPushButton#settingsSaveButton:hover {
                background-color: #19794f;
            }
            """
        )

    def save_and_accept(self) -> None:
        doctor_name = (
            self.doctor_name_input.text().strip()
        )

        if not doctor_name:
            QMessageBox.warning(
                self,
                "Nome mancante",
                "Inserisci il nome del medico "
                "o dello studio.",
            )
            self.doctor_name_input.setFocus()
            return

        self.saved_settings = {
            "doctor_name": doctor_name,
            "display_fullscreen": (
                self.fullscreen_checkbox.isChecked()
            ),
            "display_show_clock": (
                self.clock_checkbox.isChecked()
            ),
        }

        self.accept()
