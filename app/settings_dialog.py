from __future__ import annotations

from app.styles import DIALOG_STYLE

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QScrollArea,
    QWidget,
)

from app.about_dialog import AboutDialog
from app.password_dialogs import ChangePasswordDialog
from app.resources import app_icon
from app.version import APP_VERSION
from app.updater import UpdateManager

class SettingsDialog(QDialog):
    def __init__(
        self,
        current_config: dict[str, Any],
        delete_account_callback: Callable[[str], tuple[bool, str]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.saved_settings: dict[str, Any] | None = None
        self._password_record: dict[str, object] | None = None
        self.current_config = dict(current_config)
        self.delete_account_callback = delete_account_callback
        self.account_deleted = False

        self.setWindowTitle("Impostazioni")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumSize(560, 620)
        self.resize(650, 780)

        title_label = QLabel("Impostazioni")
        title_label.setObjectName("settingsTitle")
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
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
            Qt.AlignmentFlag.AlignLeft
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

        doctor_name_label = QLabel("Nome visualizzato:")
        doctor_name_label.setObjectName("settingsFormLabel")
        doctor_form.addRow(
            doctor_name_label,
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

        section_timer = QLabel("TEMPO PAZIENTE")
        section_timer.setObjectName("settingsSection")

        self.patient_warning_checkbox = QCheckBox(
            "Avvisa quando il tempo del paziente supera la soglia"
        )
        self.patient_warning_checkbox.setChecked(
            bool(current_config.get("patient_time_warning_enabled", False))
        )

        self.patient_warning_minutes = QSpinBox()
        self.patient_warning_minutes.setRange(1, 240)
        self.patient_warning_minutes.setSuffix(" min")
        self.patient_warning_minutes.setMinimumHeight(46)
        self.patient_warning_minutes.setValue(
            max(1, min(int(current_config.get("patient_time_warning_minutes", 15) or 15), 240))
        )
        self.patient_warning_minutes.setEnabled(
            self.patient_warning_checkbox.isChecked()
        )

        self.patient_warning_sound_checkbox = QCheckBox(
            "Riproduci anche un suono sul PC quando la soglia viene superata"
        )
        self.patient_warning_sound_checkbox.setChecked(
            bool(current_config.get("patient_time_warning_sound_enabled", False))
        )
        self.patient_warning_sound_checkbox.setEnabled(
            self.patient_warning_checkbox.isChecked()
        )
        self.patient_warning_checkbox.toggled.connect(self.patient_warning_minutes.setEnabled)
        self.patient_warning_checkbox.toggled.connect(self.patient_warning_sound_checkbox.setEnabled)

        timer_form = QFormLayout()
        timer_form.setVerticalSpacing(14)

        warning_threshold_label = QLabel("Soglia avviso:")
        warning_threshold_label.setObjectName("settingsFormLabel")
        timer_form.addRow(
            warning_threshold_label,
            self.patient_warning_minutes,
        )

        section_security = QLabel("SICUREZZA")
        section_security.setObjectName("settingsSection")

        self.change_password_button = QPushButton("Cambia password")
        self.change_password_button.setObjectName("settingsPasswordButton")
        self.change_password_button.setMinimumHeight(46)
        self.change_password_button.clicked.connect(
            self._change_password
        )

        self.delete_account_button = QPushButton("Elimina account e tutti i dati")
        self.delete_account_button.setObjectName("settingsDeleteAccountButton")
        self.delete_account_button.setMinimumHeight(46)
        self.delete_account_button.setEnabled(self.delete_account_callback is not None)
        self.delete_account_button.clicked.connect(self._delete_account)
        self.update_manager = UpdateManager(self)
        self.check_updates_button = QPushButton("🔄 Controlla aggiornamenti")
        self.check_updates_button.setObjectName("settingsUpdateButton")
        self.check_updates_button.setMinimumHeight(46)
        self.check_updates_button.clicked.connect(
            lambda: self.update_manager.check_for_updates(manual=True)
)
        self.version_label = QLabel(
            f"Gestione Turni · Versione {APP_VERSION}"
        )
        self.version_label.setObjectName(
            "settingsVersion"
        )
        self.version_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
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
            32,
            28,
            32,
            22,
        )
        main_layout.setSpacing(12)

        main_layout.addWidget(title_label)
        main_layout.addWidget(description_label)

        # Le impostazioni possono crescere nel tempo.
        # Le rendiamo scorrevoli, lasciando sempre visibili
        # versione e pulsanti di azione in basso.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        scroll_layout.setSpacing(14)

        scroll_layout.addWidget(section_doctor)
        scroll_layout.addLayout(doctor_form)

        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(section_display)
        scroll_layout.addWidget(self.fullscreen_checkbox)
        scroll_layout.addWidget(self.clock_checkbox)

        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(section_timer)
        scroll_layout.addWidget(self.patient_warning_checkbox)
        scroll_layout.addWidget(self.patient_warning_sound_checkbox)
        scroll_layout.addLayout(timer_form)

        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(section_security)
        scroll_layout.addWidget(self.change_password_button)
        scroll_layout.addWidget(self.delete_account_button)

        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(self.check_updates_button)

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        main_layout.addWidget(self.version_label)
        main_layout.addLayout(buttons_layout)

        self.setStyleSheet(DIALOG_STYLE)

    def _delete_account(self) -> None:
        if self.delete_account_callback is None:
            return

        doctor_name = str(self.current_config.get("doctor_name", "questo account")).strip()
        first = QMessageBox.warning(
            self,
            "Elimina account",
            f"Stai per eliminare definitivamente {doctor_name}.\n\n"
            "Verranno eliminati account, coda, impostazioni, storico e statistiche. "
            "L'operazione non può essere annullata.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if first != QMessageBox.StandardButton.Yes:
            return

        password, ok = QInputDialog.getText(
            self,
            "Conferma password",
            "Inserisci la password dell'account per confermare:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        second = QMessageBox.question(
            self,
            "Conferma eliminazione definitiva",
            f"Eliminare definitivamente {doctor_name} e tutti i suoi dati?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if second != QMessageBox.StandardButton.Yes:
            return

        success, message = self.delete_account_callback(password)
        if not success:
            QMessageBox.warning(self, "Eliminazione non riuscita", message)
            return

        self.account_deleted = True
        QMessageBox.information(
            self,
            "Account eliminato",
            "L'account e tutti i dati associati sono stati eliminati.",
        )
        self.accept()

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

        self.saved_settings = {
            "doctor_name": doctor_name,
            "display_fullscreen": (
                self.fullscreen_checkbox.isChecked()
            ),
            "display_show_clock": (
                self.clock_checkbox.isChecked()
            ),
            "patient_time_warning_enabled": (
                self.patient_warning_checkbox.isChecked()
            ),
            "patient_time_warning_minutes": (
                self.patient_warning_minutes.value()
            ),
            "patient_time_warning_sound_enabled": (
                self.patient_warning_sound_checkbox.isChecked()
            ),
        }

        if self._password_record is not None:
            self.saved_settings.update(self._password_record)

        self.accept()
