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
    QScrollArea,
    QStackedWidget,
    QComboBox,
    QButtonGroup,
    QDialog,
    QLayout,
    QSizePolicy,
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


class _PageContainer(QWidget):
    def __init__(self, page: QWidget) -> None:
        super().__init__()
        self._page = page
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        layout.addWidget(page)

    def widget(self) -> QWidget:
        return self._page


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
        self.queue_mode = (
            "surname"
            if str(local_state.get("queue_mode", "number")).strip().lower() == "surname"
            else "number"
        )
        self.current_surname = " ".join(
            str(local_state.get("current_surname", "")).strip().split()
        )[:60]

        self.current_network_role = (
            "Inizializzazione"
        )
        self.current_sync_status = (
            "Sincronizzazione in corso"
        )
        self.current_server_address = ""
        self.current_network_status = ""
        self._tv_url = ""

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
            780,
            580,
        )
        self.resize(
            1100,
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
        self.title_label = QLabel("Ambulatorio")
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel("Chiamate e tempi di visita")
        self.subtitle_label.setObjectName("subtitleLabel")

    def _build_doctor_card(
        self,
        current_number: int,
    ) -> None:
        self.doctor_card = StudioCard(
            self.doctor_name,
            current_number,
            queue_prefix=self.controller.queue_prefix,
            queue_mode=self.queue_mode,
            current_surname=self.current_surname,
        )

        self.doctor_card.number_changed.connect(
            self.controller.set_number
        )
        self.doctor_card.surname_changed.connect(
            self.controller.set_surname
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

        self.patient_pause_button = QPushButton("Pausa timer")
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
            self.patient_pause_button.setText("Pausa timer")
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
            "Riprendi timer" if paused else "Pausa timer"
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
            "Display sala d'attesa"
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
            "Statistiche"
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
            "Storico visite"
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
            "Impostazioni"
        )
        self.settings_button.setObjectName(
            "settingsButton"
        )
        self.settings_button.setFixedHeight(46)
        self.settings_button.clicked.connect(
            lambda: self.controller.open_settings(self)
        )

        self.about_button = QPushButton(
            "Informazioni"
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

    def _build_layout(self, central_widget: QWidget) -> None:
        root = QHBoxLayout(central_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(204)
        nav = QVBoxLayout(self.sidebar)
        nav.setContentsMargins(18, 26, 18, 18)
        nav.setSpacing(5)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel("GT")
        mark.setObjectName("brandMark")
        mark.setFixedSize(40, 40)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_row.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(2)
        brand_name = QLabel("Gestione Turni")
        brand_name.setObjectName("brandName")
        brand_note = QLabel("STUDIO MEDICO")
        brand_note.setObjectName("brandSubtitle")
        brand_text.addWidget(brand_name)
        brand_text.addWidget(brand_note)
        brand_row.addLayout(brand_text)
        nav.addLayout(brand_row)
        nav.addSpacing(36)
        section = QLabel("ATTIVITÀ")
        section.setObjectName("navSection")
        nav.addWidget(section)
        nav.addSpacing(7)
        self.home_button = QPushButton("Ambulatorio")
        self.home_button.setObjectName("homeButton")
        self.home_button.clicked.connect(lambda: self.show_page("home"))
        nav.addWidget(self.home_button)
        nav.addWidget(self.dashboard_button)
        nav.addWidget(self.history_button)
        nav.addWidget(self.display_button)
        nav.addStretch()
        nav.addWidget(self.settings_button)
        nav.addWidget(self.about_button)
        version = QLabel(f"Versione {APP_VERSION}")
        version.setObjectName("versionLabel")
        version.setContentsMargins(14, 10, 0, 0)
        nav.addWidget(version)
        root.addWidget(self.sidebar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        workspace = QWidget()
        workspace.setObjectName("workspace")
        self.main_layout = QVBoxLayout(workspace)
        self.main_layout.setContentsMargins(32, 28, 32, 22)
        self.main_layout.setSpacing(16)
        header = QHBoxLayout()
        header.setSpacing(12)
        headings = QVBoxLayout()
        headings.setSpacing(4)
        headings.addWidget(self.title_label)
        headings.addWidget(self.subtitle_label)
        header.addLayout(headings, 1)
        header.addWidget(self.queue_status_label)
        header.addWidget(self.queue_button)
        self.main_layout.addLayout(header)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Modalità chiamata"))
        self.mode_group = QButtonGroup(self)
        self.mode_number_button = QPushButton("Numero")
        self.mode_surname_button = QPushButton("Cognome")
        for button, mode in ((self.mode_number_button, "number"), (self.mode_surname_button, "surname")):
            button.setObjectName("modeButton")
            button.setCheckable(True)
            button.setFixedHeight(36)
            self.mode_group.addButton(button)
            button.setChecked(self.queue_mode == mode)
            button.clicked.connect(lambda checked=False, value=mode: self.controller.set_queue_mode(value))
            mode_row.addWidget(button)
        mode_row.addSpacing(12)
        mode_row.addWidget(QLabel("Lettera"))
        self.queue_prefix_combo = QComboBox()
        self.queue_prefix_combo.setObjectName("homeQueueMode")
        self.queue_prefix_combo.addItem("Nessuna", "")
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            self.queue_prefix_combo.addItem(letter, letter)
        self.queue_prefix_combo.setCurrentIndex(max(0, self.queue_prefix_combo.findData(self.controller.queue_prefix)))
        self.queue_prefix_combo.setEnabled(self.queue_mode == "number")
        self.queue_prefix_combo.setMinimumHeight(36)
        self.queue_prefix_combo.setFixedWidth(110)
        self.queue_prefix_combo.setToolTip("Lettera prima del numero chiamato. Nessuna mostra solo il numero.")
        self.queue_prefix_combo.currentIndexChanged.connect(
            lambda: self.controller.set_queue_prefix(self.queue_prefix_combo.currentData()))
        mode_row.addWidget(self.queue_prefix_combo)
        mode_row.addStretch()
        self.main_layout.addLayout(mode_row)
        self.main_layout.addWidget(self.doctor_card, 1)

        timer_panel = QFrame()
        timer_panel.setObjectName("timerPanel")
        timer_row = QHBoxLayout(timer_panel)
        timer_row.setContentsMargins(20, 12, 20, 12)
        timer_labels = QVBoxLayout()
        timer_labels.setSpacing(3)
        timer_heading = QLabel("TEMPO DI VISITA")
        timer_heading.setObjectName("panelEyebrow")
        timer_labels.addWidget(timer_heading)
        timer_labels.addWidget(self.patient_timer_label)
        timer_row.addLayout(timer_labels, 1)
        timer_row.addWidget(self.patient_pause_button)
        self.main_layout.addWidget(timer_panel)

        tv_panel = QFrame()
        tv_panel.setObjectName("tvPanel")
        tv_row = QHBoxLayout(tv_panel)
        tv_row.setContentsMargins(20, 12, 20, 12)
        tv_labels = QVBoxLayout()
        tv_labels.setSpacing(4)
        tv_heading = QLabel("Display sala d'attesa")
        tv_heading.setObjectName("tvPanelTitle")
        self.tv_address_label = QLabel("Indirizzo disponibile all'avvio")
        self.tv_address_label.setObjectName("tvAddress")
        self.tv_address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.tv_address_label.setWordWrap(True)
        tv_labels.addWidget(tv_heading)
        tv_labels.addWidget(self.tv_address_label)
        tv_row.addLayout(tv_labels, 1)
        self.copy_tv_button = QPushButton("Copia indirizzo")
        self.copy_tv_button.setObjectName("copyTvButton")
        self.copy_tv_button.setEnabled(False)
        self.copy_tv_button.clicked.connect(self._copy_tv_address)
        tv_row.addWidget(self.copy_tv_button)
        self.main_layout.addWidget(tv_panel)
        self.network_summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.addWidget(self.network_summary_label)
        self.main_layout.addStretch()
        scroll.setWidget(workspace)
        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(scroll)
        self.pages = {"home": scroll}
        self.current_page = "home"
        root.addWidget(self.page_stack, 1)
        self._update_navigation()
        self.patient_timer_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.queue_button.setFixedWidth(144)
        self.queue_status_label.setMinimumWidth(104)

    def _update_navigation(self) -> None:
        for name, button in (("home", self.home_button), ("dashboard", self.dashboard_button),
                             ("history", self.history_button), ("settings", self.settings_button)):
            button.setProperty("selected", name == self.current_page)
            self._refresh_widget_style(button)

    def show_page(self, name: str) -> None:
        if name not in self.pages:
            if name == "dashboard":
                from app.dashboard_dialog import DashboardDialog
                page = DashboardDialog(controller=self.controller, parent=self)
                self.controller.dashboard_window = page
            elif name == "history":
                from app.history_dialog import HistoryDialog
                page = HistoryDialog(doctor_id=self.doctor_id, doctor_name=self.controller.doctor_name, parent=self)
                self.controller.history_window = page
            elif name == "settings":
                from app.settings_dialog import SettingsDialog
                page = SettingsDialog(self.controller.config, self.controller.delete_current_account, self)
                page.accepted.connect(lambda: self._settings_saved(page))
            else:
                return
            page.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
            page.setModal(False)
            page.setWindowFlags(Qt.WindowType.Widget)
            page.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
            page.setMinimumSize(0, 0)
            page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
            if name == "settings":
                page.rejected.connect(lambda: self._discard_settings())
            else:
                page.rejected.connect(lambda: self.show_page("home"))
            if name in {"dashboard", "history"}:
                page.close_button.clicked.disconnect()
                page.close_button.setText("Ambulatorio")
                page.close_button.clicked.connect(lambda: self.show_page("home"))
            scroll = _PageContainer(page)
            self.pages[name] = scroll
            self.page_stack.addWidget(scroll)
        scroll = self.pages[name]
        page = scroll.widget()
        if name == "dashboard":
            page.refresh_dashboard()
        elif name == "history":
            page.doctor_name = self.controller.doctor_name
            page.doctor_label.setText(page.doctor_name)
            page.refresh_history()
        self.page_stack.setCurrentWidget(scroll)
        if name != "home":
            page.show()
        self.current_page = name
        self._update_navigation()

    def _settings_saved(self, page: QDialog) -> None:
        if page.account_deleted:
            QTimer.singleShot(0, QApplication.closeAllWindows)
            return
        if page.saved_settings is not None:
            self.controller.apply_settings(page.saved_settings)
        self.show_page("home")
        self._discard_settings()

    def _discard_settings(self) -> None:
        self.show_page("home")
        scroll = self.pages.pop("settings")
        self.page_stack.removeWidget(scroll)
        scroll.deleteLater()

    def _copy_tv_address(self) -> None:
        if self._tv_url:
            QApplication.clipboard().setText(self._tv_url)

    def _apply_responsive_layout(self, height: int) -> None:
        compact = height < 740
        self.doctor_card.set_compact_mode(compact)
        self.sidebar.setFixedWidth(204)
        self.main_layout.setContentsMargins(22 if compact else 32, 18 if compact else 28,
                                           22 if compact else 32, 14 if compact else 22)
        self.main_layout.setSpacing(12 if compact else 16)
        self.title_label.setStyleSheet("font-size:24px;" if compact else "")
        self.patient_timer_label.setFixedHeight(30)
        self.patient_pause_button.setFixedSize(132, 36)
        self.queue_status_label.setFixedHeight(28)
        self.queue_button.setFixedHeight(42)
        for button in (self.display_button, self.dashboard_button, self.history_button,
                       self.settings_button, self.about_button):
            button.setFixedHeight(42)
        self.network_summary_label.setFixedHeight(24)

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

        queue_mode = (
            "surname"
            if str(local_state.get("queue_mode", self.queue_mode)).strip().lower() == "surname"
            else "number"
        )
        current_surname = " ".join(
            str(local_state.get("current_surname", self.current_surname)).strip().split()
        )[:60]

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

        self.queue_mode = queue_mode
        self.mode_number_button.setChecked(queue_mode == "number")
        self.mode_surname_button.setChecked(queue_mode == "surname")
        self.queue_prefix_combo.blockSignals(True)
        self.queue_prefix_combo.setCurrentIndex(max(0, self.queue_prefix_combo.findData(queue_prefix)))
        self.queue_prefix_combo.blockSignals(False)
        self.queue_prefix_combo.setEnabled(queue_mode == "number")
        self.current_surname = current_surname
        self.doctor_card.set_queue_prefix(queue_prefix)
        self.doctor_card.set_queue_mode(queue_mode)
        self.doctor_card.set_surname(current_surname)

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

    def update_network_status(self, status: str) -> None:
        self.current_network_status = str(status).strip()
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
        status = self.current_network_status.lower()
        sync = self.current_sync_status.lower()
        if "errore" in sync:
            caption, state = "Verificare la sincronizzazione", "error"
        elif any(word in status for word in ("non raggiungibile", "disconness", "tentativo", "passaggio")):
            caption, state = "Riconnessione alla rete dello studio…", "waiting"
        elif self.current_network_role in {"Server", "Client"}:
            caption, state = "Rete dello studio collegata", "online"
        else:
            caption, state = "Ricerca dei computer dello studio…", "waiting"
        self.network_summary_label.setText(caption)
        self.network_summary_label.setProperty("connection", state)
        details = " · ".join(filter(None, (self.current_network_role, self.current_sync_status,
                                           self.current_network_status)))
        self.network_summary_label.setToolTip(details)
        self._refresh_widget_style(self.network_summary_label)
        self._tv_url = (f"http://{self.current_server_address}:{WEB_DISPLAY_PORT}"
                        if self.current_server_address else "")
        if hasattr(self, "tv_address_label"):
            self.tv_address_label.setText(self._tv_url or "Indirizzo disponibile all'avvio")
            self.copy_tv_button.setEnabled(bool(self._tv_url))

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
        return ""

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.controller.close()
        event.accept()
