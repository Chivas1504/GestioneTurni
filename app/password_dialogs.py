from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth import (
    create_password_record,
    validate_new_password,
    verify_password,
)
from app.resources import app_icon


class LoginDialog(QDialog):
    def __init__(
        self,
        *,
        doctor_name: str,
        config: dict[str, Any],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.config = config
        self.authenticated = False

        self.setWindowTitle("Accesso - Gestione Turni")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setFixedSize(430, 270)

        title = QLabel("ACCESSO")
        title.setObjectName("passwordTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        doctor = QLabel(doctor_name or "Medico")
        doctor.setObjectName("passwordDoctor")
        doctor.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setMaxLength(128)
        self.password_input.setMinimumHeight(46)
        self.password_input.returnPressed.connect(self._authenticate)

        cancel_button = QPushButton("Annulla")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)

        login_button = QPushButton("Accedi")
        login_button.setObjectName("primaryButton")
        login_button.clicked.connect(self._authenticate)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(login_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(doctor)
        layout.addWidget(self.password_input)
        layout.addStretch()
        layout.addLayout(buttons)

        self._apply_style()
        self.password_input.setFocus()

    def _authenticate(self) -> None:
        password = self.password_input.text()

        if verify_password(password, self.config):
            self.authenticated = True
            self.accept()
            return

        self.password_input.clear()
        self.password_input.setFocus()
        QMessageBox.warning(
            self,
            "Password errata",
            "La password inserita non è corretta.",
        )

    def _apply_style(self) -> None:
        _apply_common_style(self)


class SetPasswordDialog(QDialog):
    def __init__(
        self,
        *,
        doctor_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.password_record: dict[str, object] | None = None

        self.setWindowTitle("Crea password - Gestione Turni")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setFixedSize(470, 330)

        title = QLabel("CREA PASSWORD")
        title.setObjectName("passwordTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(
            f"Imposta la password personale per {doctor_name or 'questo medico'}."
        )
        description.setObjectName("passwordDescription")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setMaxLength(128)
        self.new_password_input.setMinimumHeight(44)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setMaxLength(128)
        self.confirm_password_input.setMinimumHeight(44)
        self.confirm_password_input.returnPressed.connect(self._save)

        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.addRow("Nuova password:", self.new_password_input)
        form.addRow("Conferma password:", self.confirm_password_input)

        cancel_button = QPushButton("Annulla")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Salva password")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(form)
        layout.addStretch()
        layout.addLayout(buttons)

        self._apply_style()
        self.new_password_input.setFocus()

    def _save(self) -> None:
        password = self.new_password_input.text()
        confirmation = self.confirm_password_input.text()

        error = validate_new_password(password)
        if error is not None:
            QMessageBox.warning(self, "Password non valida", error)
            self.new_password_input.setFocus()
            return

        if password != confirmation:
            QMessageBox.warning(
                self,
                "Password diverse",
                "Le due password non coincidono.",
            )
            self.confirm_password_input.clear()
            self.confirm_password_input.setFocus()
            return

        self.password_record = create_password_record(password)
        self.accept()

    def _apply_style(self) -> None:
        _apply_common_style(self)


class ChangePasswordDialog(QDialog):
    def __init__(
        self,
        *,
        current_config: dict[str, Any],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.current_config = current_config
        self.password_record: dict[str, object] | None = None

        self.setWindowTitle("Cambia password")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setFixedSize(500, 390)

        title = QLabel("CAMBIA PASSWORD")
        title.setObjectName("passwordTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setMaxLength(128)
        self.current_password_input.setMinimumHeight(44)

        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setMaxLength(128)
        self.new_password_input.setMinimumHeight(44)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setMaxLength(128)
        self.confirm_password_input.setMinimumHeight(44)
        self.confirm_password_input.returnPressed.connect(self._save)

        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.addRow("Password attuale:", self.current_password_input)
        form.addRow("Nuova password:", self.new_password_input)
        form.addRow("Conferma nuova:", self.confirm_password_input)

        cancel_button = QPushButton("Annulla")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Cambia password")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addStretch()
        layout.addLayout(buttons)

        self._apply_style()
        self.current_password_input.setFocus()

    def _save(self) -> None:
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirmation = self.confirm_password_input.text()

        if not verify_password(current_password, self.current_config):
            QMessageBox.warning(
                self,
                "Password errata",
                "La password attuale non è corretta.",
            )
            self.current_password_input.clear()
            self.current_password_input.setFocus()
            return

        error = validate_new_password(new_password)
        if error is not None:
            QMessageBox.warning(self, "Password non valida", error)
            self.new_password_input.setFocus()
            return

        if new_password != confirmation:
            QMessageBox.warning(
                self,
                "Password diverse",
                "La nuova password e la conferma non coincidono.",
            )
            self.confirm_password_input.clear()
            self.confirm_password_input.setFocus()
            return

        self.password_record = create_password_record(new_password)
        self.accept()

    def _apply_style(self) -> None:
        _apply_common_style(self)


def _apply_common_style(dialog: QDialog) -> None:
    dialog.setStyleSheet(
        """
        QDialog {
            background-color: #eef3f8;
        }

        QLabel#passwordTitle {
            color: #16324a;
            font-size: 25px;
            font-weight: 900;
            letter-spacing: 1px;
        }

        QLabel#passwordDoctor {
            color: #218b5d;
            font-size: 20px;
            font-weight: 800;
        }

        QLabel#passwordDescription {
            color: #60758a;
            font-size: 15px;
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

        QPushButton {
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-size: 15px;
            font-weight: 700;
        }

        QPushButton#primaryButton {
            background-color: #218b5d;
            color: white;
        }

        QPushButton#primaryButton:hover {
            background-color: #19794f;
        }

        QPushButton#secondaryButton {
            background-color: #dfe7ee;
            color: #334b5d;
        }

        QPushButton#secondaryButton:hover {
            background-color: #d2dde6;
        }
        """
    )
