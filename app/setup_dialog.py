from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.auth import create_password_record, validate_new_password
from app.config import save_config


from app.resources import app_icon

class SetupDialog(QDialog):
    def __init__(
        self,
        forced_doctor_id: str | None = None,
    ) -> None:
        super().__init__()

        self.setWindowIcon(app_icon())

        self.forced_doctor_id = (
            forced_doctor_id
        )
        self.saved_config: (
            dict[str, object] | None
        ) = None

        self.setWindowTitle(
            "Configurazione iniziale"
        )
        self.setModal(True)
        self.setFixedSize(500, 460)

        title_label = QLabel(
            "Benvenuto in Gestione Turni"
        )
        title_label.setObjectName("setupTitle")
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        description_label = QLabel(
            "Configura questo computer. "
            "Queste informazioni potranno essere "
            "cambiate in seguito."
        )
        description_label.setObjectName(
            "setupDescription"
        )
        description_label.setWordWrap(True)
        description_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.doctor_id_combo = QComboBox()
        self.doctor_id_combo.addItem(
            "Medico 1",
            "doctor1",
        )
        self.doctor_id_combo.addItem(
            "Medico 2",
            "doctor2",
        )
        self.doctor_id_combo.setMinimumHeight(46)

        if forced_doctor_id is not None:
            index = (
                self.doctor_id_combo.findData(
                    forced_doctor_id
                )
            )

            if index >= 0:
                self.doctor_id_combo.setCurrentIndex(
                    index
                )

            self.doctor_id_combo.setEnabled(False)

        self.doctor_name_input = QLineEdit()
        self.doctor_name_input.setPlaceholderText(
            "Es. Dott.ssa Rossi"
        )
        self.doctor_name_input.setMaxLength(60)
        self.doctor_name_input.setMinimumHeight(46)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password personale")
        self.password_input.setMaxLength(128)
        self.password_input.setMinimumHeight(46)

        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm_input.setPlaceholderText("Ripeti la password")
        self.password_confirm_input.setMaxLength(128)
        self.password_confirm_input.setMinimumHeight(46)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(18)
        form_layout.addRow(
            "Identificativo:",
            self.doctor_id_combo,
        )
        form_layout.addRow(
            "Nome visualizzato:",
            self.doctor_name_input,
        )
        form_layout.addRow(
            "Password:",
            self.password_input,
        )
        form_layout.addRow(
            "Conferma password:",
            self.password_confirm_input,
        )

        self.save_button = QPushButton(
            "Salva e continua"
        )
        self.save_button.setObjectName(
            "setupSaveButton"
        )
        self.save_button.setMinimumHeight(54)
        self.save_button.clicked.connect(
            self.save_and_accept
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            32,
            28,
            32,
            28,
        )
        main_layout.setSpacing(18)
        main_layout.addWidget(title_label)
        main_layout.addWidget(
            description_label
        )
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        main_layout.addWidget(
            self.save_button
        )

        self.setStyleSheet(
            """
            QDialog {
                background-color: #eef3f8;
            }

            QLabel#setupTitle {
                color: #16324a;
                font-size: 25px;
                font-weight: 800;
            }

            QLabel#setupDescription {
                color: #60758a;
                font-size: 15px;
            }

            QLineEdit,
            QComboBox {
                background-color: white;
                color: #213d53;
                border: 1px solid #cbd8e3;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 16px;
            }

            QComboBox:disabled {
                background-color: #e5ecf2;
                color: #566b7d;
            }

            QLineEdit:focus,
            QComboBox:focus {
                border: 2px solid #218b5d;
            }

            QPushButton#setupSaveButton {
                background-color: #218b5d;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 17px;
                font-weight: 700;
            }

            QPushButton#setupSaveButton:hover {
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

        password = self.password_input.text()
        password_confirmation = self.password_confirm_input.text()

        password_error = validate_new_password(password)
        if password_error is not None:
            QMessageBox.warning(
                self,
                "Password non valida",
                password_error,
            )
            self.password_input.setFocus()
            return

        if password != password_confirmation:
            QMessageBox.warning(
                self,
                "Password diverse",
                "Le due password non coincidono.",
            )
            self.password_confirm_input.clear()
            self.password_confirm_input.setFocus()
            return

        doctor_id = (
            self.forced_doctor_id
            or self.doctor_id_combo.currentData()
        )

        config = {
            "configured": True,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "queue_prefix": "",
            "queue_active": False,
            "display_fullscreen": False,
            "display_show_clock": True,
        }
        config.update(create_password_record(password))

        save_config(config)
        self.saved_config = config
        self.accept()
