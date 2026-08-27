from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)

from app.auth import validate_new_password
from app.resources import app_icon


class AccountEntryDialog(QDialog):
    def __init__(
        self,
        accounts: list[dict[str, Any]],
        authenticate: Callable[[str, str], dict[str, Any] | None],
        create_account: Callable[[str, str], dict[str, Any]],
    ) -> None:
        super().__init__()
        self.accounts = accounts
        self.authenticate_callback = authenticate
        self.create_callback = create_account
        self.selected_account: dict[str, Any] | None = None
        self.setWindowIcon(app_icon())
        self.setWindowTitle("Gestione Turni - Account")
        self.setModal(True)
        self.setFixedSize(500, 420)

        title = QLabel("GESTIONE TURNI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:26px;font-weight:800;color:#16324a;")
        subtitle = QLabel("Accedi a un account medico esistente oppure creane uno nuovo.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.login_button = QPushButton("Accedi")
        self.login_button.setMinimumHeight(58)
        self.login_button.clicked.connect(self._open_login)
        self.create_button = QPushButton("Crea account")
        self.create_button.setMinimumHeight(58)
        self.create_button.clicked.connect(self._open_create)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 34, 34, 34)
        layout.setSpacing(20)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.login_button)
        layout.addWidget(self.create_button)
        layout.addStretch()

    def _open_login(self) -> None:
        if not self.accounts:
            QMessageBox.information(self, "Nessun account", "Non risultano account disponibili sulla rete. Crea il primo account medico.")
            return
        dialog = LoginAccountDialog(self.accounts, self.authenticate_callback, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.account is not None:
            self.selected_account = dialog.account
            self.accept()

    def _open_create(self) -> None:
        dialog = CreateAccountDialog(self.create_callback, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.account is not None:
            self.selected_account = dialog.account
            self.accept()


class LoginAccountDialog(QDialog):
    def __init__(self, accounts, authenticate, parent=None):
        super().__init__(parent)
        self.authenticate = authenticate
        self.account = None
        self.setWindowTitle("Accedi")
        self.setModal(True)
        self.resize(470, 260)
        self.account_combo = QComboBox()
        for account in accounts:
            self.account_combo.addItem(str(account.get("doctor_name", "Medico")), str(account.get("doctor_id", "")))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.returnPressed.connect(self._accept_login)
        button = QPushButton("Accedi")
        button.clicked.connect(self._accept_login)
        form = QFormLayout()
        form.addRow("Account:", self.account_combo)
        form.addRow("Password:", self.password)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(button)

    def _accept_login(self):
        doctor_id = str(self.account_combo.currentData() or "")
        account = self.authenticate(doctor_id, self.password.text())
        if account is None:
            QMessageBox.warning(self, "Accesso negato", "Password non corretta.")
            self.password.selectAll(); self.password.setFocus(); return
        self.account = account
        self.accept()


class CreateAccountDialog(QDialog):
    def __init__(self, create_account, parent=None):
        super().__init__(parent)
        self.create_account = create_account
        self.account = None
        self.setWindowTitle("Crea account")
        self.setModal(True)
        self.resize(470, 330)
        self.name = QLineEdit(); self.name.setPlaceholderText("Es. Dott.ssa Rossi")
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        button = QPushButton("Crea account")
        button.clicked.connect(self._create)
        form = QFormLayout(); form.addRow("Nome medico:", self.name); form.addRow("Password:", self.password); form.addRow("Conferma:", self.confirm)
        layout = QVBoxLayout(self); layout.addLayout(form); layout.addWidget(button)

    def _create(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Nome mancante", "Inserisci il nome del medico o dello studio."); return
        error = validate_new_password(self.password.text())
        if error:
            QMessageBox.warning(self, "Password non valida", error); return
        if self.password.text() != self.confirm.text():
            QMessageBox.warning(self, "Password diverse", "Le due password non coincidono."); return
        try:
            self.account = self.create_account(name, self.password.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Impossibile creare l'account", str(exc)); return
        self.accept()
