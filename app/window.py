from __future__ import annotations

from typing import Any
import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.about_dialog import AboutDialog
from app.patient_time_warning_dialog import PatientTimeWarningDialog
from app.controller import AppController
from app.resources import app_icon
from app.version import APP_NAME, APP_VERSION
from app.web_display_server import WEB_DISPLAY_PORT
from app.studio_card import StudioCard
from app.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: AppController,
    ) -> None:
        super().__init__()

        self.controller = controller

        local_state = (
            self.controller.get_local_state()
        )

        self.doctor_id = str(
            local_state.get(
                "doctor_id",
                "",
            )
        )

        self.doctor_name = str(
            local_state.get(
                "doctor_name",
                "",
            )
        ).strip()

        self.queue_active = bool(
            local_state.get(
                "queue_active",
                False,
            )
        )

        current_number = self._safe_number(
            local_state.get(
                "number",
                0,
            )
        )

        self.current_network_role = (
            "Inizializzazione"
        )
        self.current_sync_status = (
            "Sincronizzazione in corso"
        )
        self.current_server_address = ""

        # Stato dell'avviso a schermo intero. La chiave identifica
        # il singolo paziente/avvio timer, così l'avviso compare
        # una sola volta per paziente dopo che viene confermato.
        self._patient_warning_dialog = None
        self._patient_warning_key = None
        self._patient_warning_acknowledged_key = None
        self._patient_warning_sound_key = None

        self.setWindowTitle(
            f"{APP_NAME} {APP_VERSION} - {self.doctor_name}"
        )
        self.setWindowIcon(app_icon())

        self.setMinimumSize(
            700,
            650,
        )
        self.resize(
            900,
            800,
        )

        central_widget = QWidget()
        central_widget.setObjectName(
            "centralWidget"
        )
        self.setCentralWidget(
            central_widget
        )

        self._build_header()
        self._build_doctor_card(
            current_number
        )
        self._build_patient_timer()
        self._build_queue_controls()
        self._build_action_controls()
        self._build_network_area()
        self._build_settings_button()
        self._build_shortcuts()
        self._build_layout(
            central_widget
        )
        self._apply_responsive_layout(self.height())

        self.setStyleSheet(
            APP_STYLE
            + self._additional_style()
        )

        self.update_queue_ui()
        self._update_network_summary()
        self._connect_controller()

    def _build_header(self) -> None:
        self.title_label = QLabel(
            "GESTIONE TURNI"
        )
        self.title_label.setObjectName(
            "titleLabel"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.subtitle_label = QLabel(
            "Sistema di gestione turni"
        )
        self.subtitle_label.setObjectName(
            "subtitleLabel"
        )
        self.subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

    def _build_doctor_card(
        self,
        current_number: int,
    ) -> None:
        self.doctor_card = StudioCard(
            self.doctor_name,
            current_number,
            queue_prefix=self.controller.queue_prefix,
        )

        self.doctor_card.number_changed.connect(
            self.controller.set_number
        )

    def _build_patient_timer(self) -> None:
        self.patient_timer_label = QLabel()
        self.patient_timer_label.setObjectName(
            "patientTimerLabel"
        )
        self.patient_timer_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.patient_timer_label.setFixedHeight(34)

        self.patient_pause_button = QPushButton("⏸ Pausa timer")
        self.patient_pause_button.setObjectName("patientPauseButton")
        self.patient_pause_button.setFixedHeight(34)
        self.patient_pause_button.setFixedWidth(150)
        self.patient_pause_button.setEnabled(False)
        self.patient_pause_button.clicked.connect(
            self.controller.toggle_patient_timer_pause
        )

        self.patient_timer_layout = QHBoxLayout()
        self.patient_timer_layout.setContentsMargins(0, 0, 0, 0)
        self.patient_timer_layout.setSpacing(8)
        self.patient_timer_layout.addWidget(self.patient_timer_label, stretch=1)
        self.patient_timer_layout.addWidget(self.patient_pause_button)

        self.patient_timer = QTimer(self)
        self.patient_timer.setInterval(1000)
        self.patient_timer.timeout.connect(
            self.update_patient_timer
        )
        self.patient_timer.start()
        self.update_patient_timer()

    def update_patient_timer(self, *_args) -> None:
        timer_state = self.controller.get_current_patient_timer()

        if not timer_state.get("active", False):
            self._reset_patient_warning_state()
            self.patient_timer_label.setText(
                "Tempo paziente: —"
            )
            self.patient_timer_label.setProperty("active", False)
            self.patient_timer_label.setProperty("warning", False)
            self.patient_pause_button.setEnabled(False)
            self.patient_pause_button.setText("⏸ Pausa timer")
            self.patient_pause_button.setProperty("paused", False)
            self._refresh_widget_style(self.patient_pause_button)
            self._refresh_widget_style(
                self.patient_timer_label
            )
            return

        try:
            started_at = float(timer_state.get("started_at", 0.0))
        except (TypeError, ValueError):
            started_at = time.time()

        paused = bool(timer_state.get("paused", False))
        try:
            paused_at = float(timer_state.get("paused_at", 0.0))
        except (TypeError, ValueError):
            paused_at = 0.0
        effective_now = paused_at if paused and paused_at > 0 else time.time()
        elapsed = max(0, int(effective_now - started_at))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        ticket = str(timer_state.get("ticket", "")).strip()
        elapsed_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # La combinazione ticket + timestamp di avvio distingue anche
        # due pazienti con lo stesso numero in sessioni differenti.
        warning_key = f"{ticket}|{started_at:.6f}"
        if warning_key != self._patient_warning_key:
            self._close_patient_warning_dialog()
            self._patient_warning_key = warning_key
            self._patient_warning_acknowledged_key = None
            self._patient_warning_sound_key = None

        warning_enabled = bool(
            self.controller.config.get("patient_time_warning_enabled", False)
        )
        try:
            warning_minutes = int(
                self.controller.config.get("patient_time_warning_minutes", 15)
            )
        except (TypeError, ValueError):
            warning_minutes = 15
        warning_minutes = max(1, min(warning_minutes, 240))
        warning_active = (
            warning_enabled
            and not paused
            and elapsed >= warning_minutes * 60
        )

        if paused:
            self._close_patient_warning_dialog()

        if warning_active:
            if (
                bool(self.controller.config.get("patient_time_warning_sound_enabled", False))
                and self._patient_warning_sound_key != warning_key
            ):
                self._play_patient_warning_alarm()
                self._patient_warning_sound_key = warning_key
            self.patient_timer_label.setText(
                f"⚠ Tempo paziente {ticket}: "
                f"{elapsed_text} · "
                f"Soglia {warning_minutes} min superata"
            )
            self._show_patient_time_warning(
                warning_key=warning_key,
                ticket=ticket,
                elapsed_text=elapsed_text,
                warning_minutes=warning_minutes,
            )
        else:
            suffix = " · IN PAUSA" if paused else ""
            self.patient_timer_label.setText(
                f"Tempo paziente {ticket}: "
                f"{elapsed_text}{suffix}"
            )

        self.patient_pause_button.setEnabled(True)
        self.patient_pause_button.setText(
            "▶ Riprendi timer" if paused else "⏸ Pausa timer"
        )
        self.patient_pause_button.setProperty("paused", paused)
        self._refresh_widget_style(self.patient_pause_button)
        self.patient_timer_label.setProperty("active", True)
        self.patient_timer_label.setProperty("warning", warning_active)
        self._refresh_widget_style(
            self.patient_timer_label
        )

    def _play_patient_warning_alarm(self) -> None:
        """Riproduce un allarme ben udibile senza bloccare l'interfaccia."""

        def _worker() -> None:
            try:
                import winsound

                # Sequenza alternata, più riconoscibile di QApplication.beep().
                # Viene eseguita una sola volta per paziente.
                for _ in range(3):
                    winsound.Beep(1050, 240)
                    winsound.Beep(1450, 240)
                    time.sleep(0.10)
            except Exception:
                # Fallback per ambienti/non-Windows in cui winsound non è disponibile.
                for _ in range(3):
                    QApplication.beep()
                    time.sleep(0.20)

        threading.Thread(
            target=_worker,
            name="patient-warning-alarm",
            daemon=True,
        ).start()

    def _show_patient_time_warning(
        self,
        warning_key: str,
        ticket: str,
        elapsed_text: str,
        warning_minutes: int,
    ) -> None:
        if self._patient_warning_acknowledged_key == warning_key:
            return

        if self._patient_warning_dialog is not None:
            return

        dialog = PatientTimeWarningDialog(
            ticket=ticket,
            elapsed_text=elapsed_text,
            threshold_minutes=warning_minutes,
            parent=self,
        )
        self._patient_warning_dialog = dialog
        dialog.finished.connect(
            lambda _result, key=warning_key, dlg=dialog:
                self._on_patient_warning_finished(key, dlg)
        )
        dialog.show_warning()

    def _on_patient_warning_finished(
        self,
        warning_key: str,
        dialog: PatientTimeWarningDialog,
    ) -> None:
        if self._patient_warning_dialog is dialog:
            self._patient_warning_dialog = None
        self._patient_warning_acknowledged_key = warning_key

    def _close_patient_warning_dialog(self) -> None:
        dialog = self._patient_warning_dialog
        self._patient_warning_dialog = None
        if dialog is None:
            return

        dialog._allow_close = True
        dialog.close()

    def _reset_patient_warning_state(self) -> None:
        self._close_patient_warning_dialog()
        self._patient_warning_key = None
        self._patient_warning_acknowledged_key = None
        self._patient_warning_sound_key = None

    def _build_queue_controls(self) -> None:
        self.queue_status_label = QLabel()
        self.queue_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.queue_status_label.setFixedHeight(
            24
        )

        self.queue_button = QPushButton()
        self.queue_button.setFixedHeight(
            56
        )
        self.queue_button.clicked.connect(
            self.controller.toggle_queue
        )

    def _build_action_controls(self) -> None:
        self.display_button = QPushButton(
            "🖥  Display sala d'attesa"
        )
        self.display_button.setObjectName(
            "displayCompactButton"
        )
        self.display_button.setFixedHeight(
            46
        )
        self.display_button.clicked.connect(
            self.controller.open_display
        )

        self.dashboard_button = QPushButton(
            "Dashboard"
        )
        self.dashboard_button.setObjectName(
            "dashboardCompactButton"
        )
        self.dashboard_button.setFixedHeight(
            46
        )
        self.dashboard_button.clicked.connect(
            lambda: self.controller.open_dashboard(
                self
            )
        )

        self.history_button = QPushButton(
            "Storico"
        )
        self.history_button.setObjectName(
            "historyCompactButton"
        )
        self.history_button.setFixedHeight(
            46
        )
        self.history_button.clicked.connect(
            lambda: self.controller.open_history(
                self
            )
        )

        self.secondary_buttons_layout = (
            QHBoxLayout()
        )
        self.secondary_buttons_layout.setSpacing(
            12
        )

        self.secondary_buttons_layout.addWidget(
            self.dashboard_button,
            stretch=1,
        )
        self.secondary_buttons_layout.addWidget(
            self.history_button,
            stretch=1,
        )

    def _build_network_area(self) -> None:
        self.network_separator = QFrame()
        self.network_separator.setObjectName(
            "networkSeparator"
        )
        self.network_separator.setFrameShape(
            QFrame.Shape.HLine
        )

        self.network_summary_label = QLabel()
        self.network_summary_label.setObjectName(
            "networkSummary"
        )
        self.network_summary_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.network_summary_label.setFixedHeight(
            26
        )

    def _build_settings_button(self) -> None:
        self.settings_button = QPushButton(
            "⚙  Impostazioni"
        )
        self.settings_button.setObjectName(
            "settingsButton"
        )
        self.settings_button.setFixedHeight(46)
        self.settings_button.clicked.connect(
            lambda: self.controller.open_settings(self)
        )

        self.about_button = QPushButton(
            f"Informazioni · v{APP_VERSION}"
        )
        self.about_button.setObjectName(
            "aboutButton"
        )
        self.about_button.setFixedHeight(46)
        self.about_button.clicked.connect(
            self.open_about
        )

        self.bottom_buttons_layout = QHBoxLayout()
        self.bottom_buttons_layout.setSpacing(12)
        self.bottom_buttons_layout.addWidget(
            self.settings_button,
            stretch=2,
        )
        self.bottom_buttons_layout.addWidget(
            self.about_button,
            stretch=1,
        )

    def _build_shortcuts(self) -> None:
        self.dashboard_shortcut = QShortcut(
            QKeySequence("Ctrl+D"),
            self,
        )
        self.dashboard_shortcut.activated.connect(
            lambda: self.controller.open_dashboard(self)
        )

        self.history_shortcut = QShortcut(
            QKeySequence("Ctrl+H"),
            self,
        )
        self.history_shortcut.activated.connect(
            lambda: self.controller.open_history(self)
        )

        self.settings_shortcut = QShortcut(
            QKeySequence("Ctrl+S"),
            self,
        )
        self.settings_shortcut.activated.connect(
            lambda: self.controller.open_settings(self)
        )

    def open_about(self) -> None:
        AboutDialog(self).exec()

    def _build_layout(
        self,
        central_widget: QWidget,
    ) -> None:
        self.main_layout = QVBoxLayout(
            central_widget
        )

        self.main_layout.setContentsMargins(
            36,
            18,
            36,
            20,
        )
        self.main_layout.setSpacing(
            8
        )

        self.main_layout.addWidget(
            self.title_label
        )
        self.main_layout.addWidget(
            self.subtitle_label
        )

        self.main_layout.addSpacing(4)

        self.main_layout.addWidget(
            self.doctor_card
        )
        self.main_layout.addLayout(
            self.patient_timer_layout
        )

        self.main_layout.addWidget(
            self.queue_status_label
        )
        self.main_layout.addWidget(
            self.queue_button
        )
        self.main_layout.addWidget(
            self.display_button
        )
        self.main_layout.addLayout(
            self.secondary_buttons_layout
        )

        self.main_layout.addWidget(
            self.network_separator
        )
        self.main_layout.addWidget(
            self.network_summary_label
        )
        self.main_layout.addLayout(
            self.bottom_buttons_layout
        )

        self.main_layout.addStretch()

    def _apply_responsive_layout(self, height: int) -> None:
        """Adatta l'interfaccia all'altezza realmente disponibile.

        Windows può ridurre parecchio lo spazio utile quando usa scaling DPI,
        barra delle applicazioni o finestre massimizzate. Sotto i 900 px
        passiamo automaticamente a una variante compatta, senza sovrapporre
        timer e controlli.
        """
        compact = int(height) < 900

        self.doctor_card.set_compact_mode(compact)

        if compact:
            self.main_layout.setContentsMargins(28, 10, 28, 12)
            self.main_layout.setSpacing(5)
            self.title_label.setStyleSheet(
                "font-size: 28px; font-weight: 800; letter-spacing: 2px;"
            )
            self.subtitle_label.setStyleSheet("font-size: 15px;")
            self.patient_timer_label.setFixedHeight(30)
            self.patient_pause_button.setFixedHeight(30)
            self.patient_pause_button.setFixedWidth(135)
            self.queue_status_label.setFixedHeight(22)
            self.queue_button.setFixedHeight(50)
            self.display_button.setFixedHeight(40)
            self.dashboard_button.setFixedHeight(40)
            self.history_button.setFixedHeight(40)
            self.network_summary_label.setFixedHeight(24)
            self.settings_button.setFixedHeight(40)
            self.about_button.setFixedHeight(40)
        else:
            self.main_layout.setContentsMargins(36, 18, 36, 20)
            self.main_layout.setSpacing(8)
            self.title_label.setStyleSheet("")
            self.subtitle_label.setStyleSheet("")
            self.patient_timer_label.setFixedHeight(34)
            self.patient_pause_button.setFixedHeight(34)
            self.patient_pause_button.setFixedWidth(150)
            self.queue_status_label.setFixedHeight(24)
            self.queue_button.setFixedHeight(56)
            self.display_button.setFixedHeight(46)
            self.dashboard_button.setFixedHeight(46)
            self.history_button.setFixedHeight(46)
            self.network_summary_label.setFixedHeight(26)
            self.settings_button.setFixedHeight(46)
            self.about_button.setFixedHeight(46)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "main_layout") and hasattr(self, "doctor_card"):
            self._apply_responsive_layout(event.size().height())

    def _connect_controller(self) -> None:
        self.controller.state_changed.connect(
            self.on_shared_state_changed
        )

        self.controller.network_role_changed.connect(
            self.update_network_role
        )

        self.controller.network_status_changed.connect(
            self.update_network_status
        )

        self.controller.sync_status_changed.connect(
            self.update_sync_status
        )

        self.controller.server_address_changed.connect(
            self.update_server_address
        )

        self.controller.patient_timer_changed.connect(
            self.update_patient_timer
        )

    def on_shared_state_changed(
        self,
        complete_state: object,
    ) -> None:
        if not isinstance(
            complete_state,
            dict,
        ):
            return

        local_state: Any = (
            complete_state.get(
                self.doctor_id
            )
        )

        if not isinstance(
            local_state,
            dict,
        ):
            return

        doctor_name = str(
            local_state.get(
                "doctor_name",
                self.doctor_name,
            )
        ).strip()

        number = self._safe_number(
            local_state.get(
                "number",
                self.doctor_card.number,
            )
        )

        queue_prefix = str(
            local_state.get(
                "queue_prefix",
                self.controller.queue_prefix,
            )
        ).strip().upper()

        queue_active = bool(
            local_state.get(
                "queue_active",
                self.queue_active,
            )
        )

        if doctor_name:
            self.doctor_name = doctor_name
            self.setWindowTitle(
                f"{APP_NAME} {APP_VERSION} - {doctor_name}"
            )
            self.doctor_card.set_studio_name(
                doctor_name
            )

        self.doctor_card.set_queue_prefix(queue_prefix)

        if number != self.doctor_card.number:
            self.doctor_card.set_number(
                number
            )

        if queue_active != self.queue_active:
            self.queue_active = queue_active
            self.update_queue_ui()

    def update_queue_ui(self) -> None:
        if self.queue_active:
            self.queue_status_label.setText(
                "● Coda attiva"
            )
            self.queue_status_label.setObjectName(
                "queueStatusActive"
            )

            self.queue_button.setText(
                "Termina coda"
            )
            self.queue_button.setObjectName(
                "queueStopButton"
            )

        else:
            self.queue_status_label.setText(
                "● Coda non attiva"
            )
            self.queue_status_label.setObjectName(
                "queueStatusInactive"
            )

            self.queue_button.setText(
                "Inizia coda"
            )
            self.queue_button.setObjectName(
                "queueStartButton"
            )

        self._refresh_widget_style(
            self.queue_status_label
        )
        self._refresh_widget_style(
            self.queue_button
        )

    def update_network_role(
        self,
        role: str,
    ) -> None:
        if role == "server":
            self.current_network_role = "Server"
        elif role == "client":
            self.current_network_role = "Client"
        else:
            self.current_network_role = (
                "Inizializzazione"
            )

        self._update_network_summary()

    def update_network_status(
        self,
        status: str,
    ) -> None:
        self._update_network_summary()

    def update_sync_status(
        self,
        status: str,
    ) -> None:
        clean_status = str(status).strip()

        if clean_status:
            self.current_sync_status = clean_status

        self._update_network_summary()

    def update_server_address(
        self,
        server_address: str,
    ) -> None:
        self.current_server_address = str(
            server_address
        ).strip()

        self._update_network_summary()

    def _update_network_summary(self) -> None:
        sync_text = self._simplify_sync_status(
            self.current_sync_status
        )

        parts = [
            self.current_network_role,
            sync_text,
        ]

        if self.current_server_address:
            if self.current_network_role == "Client":
                parts.append(self.current_server_address)

            parts.append(
                "TV: "
                f"http://{self.current_server_address}:"
                f"{WEB_DISPLAY_PORT}"
            )

        self.network_summary_label.setText(
            "  •  ".join(parts)
        )

    @staticmethod
    def _simplify_sync_status(
        status: str,
    ) -> str:
        clean_status = str(status).strip()
        lowered = clean_status.lower()

        if (
            "completata" in lowered
            or "collegato" in lowered
            or "gestito da questo computer"
            in lowered
        ):
            return "Sincronizzato"

        return "Sincronizzazione in corso"

    @staticmethod
    def _safe_number(
        value: Any,
    ) -> int:
        try:
            return max(0, int(value))
        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _refresh_widget_style(
        widget: QWidget,
    ) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @staticmethod
    def _additional_style() -> str:
        return """
        QPushButton#displayCompactButton {
            background-color: #dce8f1;
            color: #234f6e;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
        }

        QPushButton#dashboardCompactButton {
            background-color: #2c6088;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
        }

        QPushButton#historyCompactButton {
            background-color: #dfe7ee;
            color: #29485e;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
        }

        QFrame#networkSeparator {
            background-color: #ccd9e3;
            border: none;
            min-height: 1px;
            max-height: 1px;
        }

        QPushButton#aboutButton {
            background-color: #dfe7ee;
            color: #29485e;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 800;
        }

        QPushButton#aboutButton:hover {
            background-color: #d2dde6;
        }

        QLabel#patientTimerLabel {
            color: #60758a;
            font-size: 16px;
            font-weight: 800;
            padding: 4px;
        }

        QLabel#patientTimerLabel[active="true"] {
            color: #17689c;
        }

        QLabel#patientTimerLabel[warning="true"] {
            color: #b42318;
            background-color: #fee4e2;
            border: 1px solid #fda29b;
            border-radius: 8px;
        }

        QPushButton#patientPauseButton {
            background-color: #dce8f1;
            color: #234f6e;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 800;
            padding: 2px 10px;
        }

        QPushButton#patientPauseButton:hover {
            background-color: #cfdee9;
        }

        QPushButton#patientPauseButton[paused="true"] {
            background-color: #fff0c2;
            color: #7a4d00;
        }

        QPushButton#patientPauseButton:disabled {
            background-color: #edf2f6;
            color: #9aa9b5;
        }

        QLabel#networkSummary {
            color: #176b9c;
            font-size: 14px;
            font-weight: 700;
        }
        """

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.controller.close()
        event.accept()
