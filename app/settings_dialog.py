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

from app.about_dialog import AboutDialog
from app.password_dialogs import ChangePasswordDialog
from app.resources import app_icon
from app.version import APP_VERSION


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_config: dict[str, Any],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.saved_settings: dict[str, Any] | None = None
        self._password_record: dict[str, object] | None = None
        self.current_config = dict(current_config)

        self.setWindowTitle("Impostazioni")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumSize(560, 560)
        self.resize(600, 600)

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

        self.queue_prefix_input = QLineEdit()
        self.queue_prefix_input.setPlaceholderText("Es. A")
        self.queue_prefix_input.setMaxLength(1)
        self.queue_prefix_input.setMinimumHeight(46)
        self.queue_prefix_input.setText(
            str(current_config.get("queue_prefix", "")).upper()
        )
        doctor_form.addRow(
            "Lettera della coda:",
            self.queue_prefix_input,
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

        section_security = QLabel("SICUREZZA")
        section_security.setObjectName("settingsSection")

        self.change_password_button = QPushButton("Cambia password")
        self.change_password_button.setObjectName("settingsPasswordButton")
        self.change_password_button.setMinimumHeight(46)
        self.change_password_button.clicked.connect(
            self._change_password
        )

        self.version_label = QLabel(
            f"Gestione Turni · Versione {APP_VERSION}"
        )
        self.version_label.setObjectName(
            "settingsVersion"
        )
        self.version_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.about_button = QPushButton(
            "Informazioni"
        )
        self.about_button.setObjectName(
            "settingsAboutButton"
        )
        self.about_button.setMinimumHeight(50)
        self.about_button.clicked.connect(
            lambda: AboutDialog(self).exec()
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
        buttons_layout.addWidget(
            self.about_button
        )
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

        main_layout.addSpacing(12)
        main_layout.addWidget(section_security)
        main_layout.addWidget(self.change_password_button)

        main_layout.addStretch()
        main_layout.addWidget(self.version_label)
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

            QLabel#settingsVersion {
                color: #60758a;
                font-size: 13px;
                font-weight: 700;
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

            QPushButton#settingsAboutButton,
            QPushButton#settingsPasswordButton {
                background-color: #dce8f1;
                color: #234f6e;
            }

            QPushButton#settingsAboutButton:hover,
            QPushButton#settingsPasswordButton:hover {
                background-color: #cfdee9;
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

    def _change_password(self) -> None:
        dialog = ChangePasswordDialog(
            current_config=self.current_config,
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
            or dialog.password_record is None
        ):
            return

        self._password_record = dialog.password_record
        self.current_config.update(dialog.password_record)
        QMessageBox.information(
            self,
            "Password aggiornata",
            "La nuova password verrà salvata insieme alle impostazioni.",
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

        prefix = self.queue_prefix_input.text().strip().upper()
        if prefix and (len(prefix) != 1 or not ("A" <= prefix <= "Z")):
            QMessageBox.warning(
                self,
                "Lettera non valida",
                "Inserisci una sola lettera da A a Z, oppure lascia il campo vuoto.",
            )
            self.queue_prefix_input.setFocus()
            return

        self.saved_settings = {
            "doctor_name": doctor_name,
            "queue_prefix": prefix,
            "display_fullscreen": (
                self.fullscreen_checkbox.isChecked()
            ),
            "display_show_clock": (
                self.clock_checkbox.isChecked()
            ),
        }

        if self._password_record is not None:
            self.saved_settings.update(self._password_record)

        self.accept()
