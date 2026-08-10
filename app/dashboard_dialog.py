from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.history_statistics import get_personal_dashboard


from app.resources import app_icon

class StatisticCard(QFrame):

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        *,
        accent: bool = False,
    ) -> None:
        super().__init__()

        self.setObjectName(
            "dashboardAccentCard"
            if accent
            else "dashboardCard"
        )

        self.title_label = QLabel(title)
        self.title_label.setObjectName(
            "dashboardCardTitle"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.title_label.setWordWrap(True)

        self.value_label = QLabel(value)
        self.value_label.setObjectName(
            "dashboardCardValue"
        )
        self.value_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.value_label.setWordWrap(True)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName(
            "dashboardCardSubtitle"
        )
        self.subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.subtitle_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        layout.setSpacing(8)

        layout.addWidget(
            self.title_label
        )
        layout.addStretch()
        layout.addWidget(
            self.value_label
        )
        layout.addWidget(
            self.subtitle_label
        )
        layout.addStretch()

    def update_content(
        self,
        *,
        value: str,
        subtitle: str = "",
    ) -> None:
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)


class DashboardDialog(QDialog):

    def __init__(
        self,
        *,
        controller,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowIcon(app_icon())

        self.controller = controller

        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        self.setWindowTitle(
            "Dashboard personale"
        )
        self.setMinimumSize(
            1050,
            720,
        )
        self.resize(
            1180,
            800,
        )

        self._build_interface()
        self._apply_style()
        self._connect_controller()
        self.refresh_dashboard()

    def _build_interface(self) -> None:
        title_label = QLabel(
            "DASHBOARD PERSONALE"
        )
        title_label.setObjectName(
            "dashboardTitle"
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.doctor_label = QLabel(
            self.controller.doctor_name
        )
        self.doctor_label.setObjectName(
            "dashboardDoctor"
        )
        self.doctor_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.queue_status_label = QLabel()
        self.queue_status_label.setObjectName(
            "dashboardQueueStatus"
        )
        self.queue_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        today_section = QLabel(
            "OGGI"
        )
        today_section.setObjectName(
            "dashboardSection"
        )

        self.current_number_card = StatisticCard(
            "Numero attuale",
            "0",
            accent=True,
        )

        self.today_patients_card = StatisticCard(
            "Pazienti serviti",
            "0",
        )

        self.today_duration_card = StatisticCard(
            "Durata complessiva",
            "0 min",
        )

        self.today_rate_card = StatisticCard(
            "Media pazienti/ora",
            "—",
        )

        self.today_patient_time_card = StatisticCard(
            "Tempo medio per paziente",
            "—",
        )

        today_grid = QGridLayout()
        today_grid.setHorizontalSpacing(16)
        today_grid.setVerticalSpacing(16)

        today_grid.addWidget(
            self.current_number_card,
            0,
            0,
        )
        today_grid.addWidget(
            self.today_patients_card,
            0,
            1,
        )
        today_grid.addWidget(
            self.today_duration_card,
            0,
            2,
        )
        today_grid.addWidget(
            self.today_rate_card,
            0,
            3,
        )
        today_grid.addWidget(
            self.today_patient_time_card,
            1,
            0,
            1,
            2,
        )

        month_section = QLabel(
            "QUESTO MESE"
        )
        month_section.setObjectName(
            "dashboardSection"
        )

        self.month_patients_card = StatisticCard(
            "Pazienti totali",
            "0",
        )

        self.month_average_card = StatisticCard(
            "Media giornaliera",
            "0",
        )

        self.month_days_card = StatisticCard(
            "Giorni di attività",
            "0",
        )

        self.best_day_card = StatisticCard(
            "Giorno migliore",
            "—",
        )

        month_grid = QGridLayout()
        month_grid.setHorizontalSpacing(16)
        month_grid.setVerticalSpacing(16)

        month_grid.addWidget(
            self.month_patients_card,
            0,
            0,
        )
        month_grid.addWidget(
            self.month_average_card,
            0,
            1,
        )
        month_grid.addWidget(
            self.month_days_card,
            0,
            2,
        )
        month_grid.addWidget(
            self.best_day_card,
            0,
            3,
        )

        last_session_section = QLabel(
            "ULTIMA SESSIONE"
        )
        last_session_section.setObjectName(
            "dashboardSection"
        )

        self.last_session_frame = QFrame()
        self.last_session_frame.setObjectName(
            "dashboardLastSession"
        )

        self.last_session_date_label = QLabel(
            "Nessuna sessione completata"
        )
        self.last_session_date_label.setObjectName(
            "dashboardLastDate"
        )

        self.last_session_time_label = QLabel()
        self.last_session_time_label.setObjectName(
            "dashboardLastDetail"
        )

        self.last_session_patients_label = QLabel()
        self.last_session_patients_label.setObjectName(
            "dashboardLastDetail"
        )

        self.last_session_rate_label = QLabel()
        self.last_session_rate_label.setObjectName(
            "dashboardLastDetail"
        )

        last_session_layout = QVBoxLayout(
            self.last_session_frame
        )
        last_session_layout.setContentsMargins(
            24,
            20,
            24,
            20,
        )
        last_session_layout.setSpacing(8)

        last_session_layout.addWidget(
            self.last_session_date_label
        )
        last_session_layout.addWidget(
            self.last_session_time_label
        )
        last_session_layout.addWidget(
            self.last_session_patients_label
        )
        last_session_layout.addWidget(
            self.last_session_rate_label
        )

        self.refresh_button = QPushButton(
            "Aggiorna"
        )
        self.refresh_button.setObjectName(
            "dashboardSecondaryButton"
        )
        self.refresh_button.clicked.connect(
            self.refresh_dashboard
        )

        self.history_button = QPushButton(
            "Storico completo"
        )
        self.history_button.setObjectName(
            "dashboardPrimaryButton"
        )
        self.history_button.clicked.connect(
            lambda: self.controller.open_history(
                self
            )
        )

        self.close_button = QPushButton(
            "Chiudi"
        )
        self.close_button.setObjectName(
            "dashboardSecondaryButton"
        )
        self.close_button.clicked.connect(
            self.close
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.addStretch()
        buttons_layout.addWidget(
            self.refresh_button
        )
        buttons_layout.addWidget(
            self.history_button
        )
        buttons_layout.addWidget(
            self.close_button
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            30,
            24,
            30,
            26,
        )
        main_layout.setSpacing(15)

        main_layout.addWidget(
            title_label
        )
        main_layout.addWidget(
            self.doctor_label
        )
        main_layout.addWidget(
            self.queue_status_label
        )

        main_layout.addSpacing(4)
        main_layout.addWidget(
            today_section
        )
        main_layout.addLayout(
            today_grid
        )

        main_layout.addSpacing(6)
        main_layout.addWidget(
            month_section
        )
        main_layout.addLayout(
            month_grid
        )

        main_layout.addSpacing(6)
        main_layout.addWidget(
            last_session_section
        )
        main_layout.addWidget(
            self.last_session_frame
        )

        main_layout.addStretch()
        main_layout.addLayout(
            buttons_layout
        )

    def _connect_controller(self) -> None:
        self.controller.state_changed.connect(
            self._on_controller_state_changed
        )

        self.controller.settings_changed.connect(
            self._on_settings_changed
        )

    def refresh_dashboard(self) -> None:
        dashboard = get_personal_dashboard(
            doctor_id=self.controller.doctor_id,
            current_number=(
                self.controller.get_local_number()
            ),
            queue_active=(
                self.controller.queue_active
            ),
        )

        self.doctor_label.setText(
            self.controller.doctor_name
        )

        self._update_queue_status(
            bool(
                dashboard.get(
                    "queue_active",
                    False,
                )
            )
        )

        self.current_number_card.update_content(
            value=str(
                self._safe_int(
                    dashboard.get(
                        "current_number",
                        0,
                    )
                )
            ),
            subtitle=(
                "Coda attiva"
                if dashboard.get(
                    "queue_active",
                    False,
                )
                else "Coda non attiva"
            ),
        )

        today = dashboard.get(
            "today",
            {},
        )

        if not isinstance(today, dict):
            today = {}

        today_patients = self._safe_int(
            today.get(
                "patients_served",
                0,
            )
        )

        today_duration = self._safe_int(
            today.get(
                "duration_minutes",
                0,
            )
        )

        today_rate = today.get(
            "patients_per_hour"
        )

        today_sessions = self._safe_int(
            today.get(
                "sessions",
                0,
            )
        )

        self.today_patients_card.update_content(
            value=str(today_patients),
            subtitle=(
                f"{today_sessions} sessioni"
                if today_sessions != 1
                else "1 sessione"
            ),
        )

        self.today_duration_card.update_content(
            value=self._format_duration(
                today_duration
            ),
            subtitle="Tempo totale registrato",
        )

        self.today_rate_card.update_content(
            value=self._format_rate(
                today_rate
            ),
            subtitle="Pazienti ogni ora",
        )

        timed_patients = self._safe_int(
            today.get("timed_patients", 0)
        )
        average_patient_seconds = today.get(
            "average_patient_seconds"
        )
        self.today_patient_time_card.update_content(
            value=self._format_seconds(average_patient_seconds),
            subtitle=(
                f"{timed_patients} pazienti cronometrati"
                if timed_patients != 1
                else "1 paziente cronometrato"
            ),
        )

        month = dashboard.get(
            "month",
            {},
        )

        if not isinstance(month, dict):
            month = {}

        month_patients = self._safe_int(
            month.get(
                "patients_served",
                0,
            )
        )

        month_active_days = self._safe_int(
            month.get(
                "active_days",
                0,
            )
        )

        month_average = month.get(
            "daily_average",
            0.0,
        )

        best_day_date = str(
            month.get(
                "best_day_date",
                "",
            )
        )

        best_day_patients = self._safe_int(
            month.get(
                "best_day_patients",
                0,
            )
        )

        self.month_patients_card.update_content(
            value=str(month_patients),
            subtitle="Totale del mese",
        )

        self.month_average_card.update_content(
            value=self._format_decimal(
                month_average
            ),
            subtitle="Pazienti per giorno attivo",
        )

        self.month_days_card.update_content(
            value=str(month_active_days),
            subtitle=(
                "Giorni registrati"
            ),
        )

        if best_day_date:
            best_day_text = (
                self._format_date(
                    best_day_date
                )
            )
            best_day_subtitle = (
                f"{best_day_patients} pazienti"
            )
        else:
            best_day_text = "—"
            best_day_subtitle = (
                "Nessun dato disponibile"
            )

        self.best_day_card.update_content(
            value=best_day_text,
            subtitle=best_day_subtitle,
        )

        self._update_last_session(
            dashboard.get(
                "last_session"
            )
        )

    def _update_queue_status(
        self,
        queue_active: bool,
    ) -> None:
        if queue_active:
            self.queue_status_label.setText(
                "● Coda attualmente attiva"
            )
            self.queue_status_label.setProperty(
                "active",
                True,
            )
        else:
            self.queue_status_label.setText(
                "● Coda attualmente non attiva"
            )
            self.queue_status_label.setProperty(
                "active",
                False,
            )

        self.queue_status_label.style().unpolish(
            self.queue_status_label
        )
        self.queue_status_label.style().polish(
            self.queue_status_label
        )

    def _update_last_session(
        self,
        last_session: object,
    ) -> None:
        if not isinstance(
            last_session,
            dict,
        ):
            self.last_session_date_label.setText(
                "Nessuna sessione completata"
            )
            self.last_session_time_label.setText(
                ""
            )
            self.last_session_patients_label.setText(
                ""
            )
            self.last_session_rate_label.setText(
                ""
            )
            return

        session_date = self._format_date(
            str(
                last_session.get(
                    "date",
                    "",
                )
            )
        )

        started_at = self._short_time(
            last_session.get(
                "started_at"
            )
        )

        ended_at = self._short_time(
            last_session.get(
                "ended_at"
            )
        )

        patients = self._safe_int(
            last_session.get(
                "patients_served",
                0,
            )
        )

        duration = self._safe_int(
            last_session.get(
                "duration_minutes",
                0,
            )
        )

        rate = last_session.get(
            "patients_per_hour"
        )

        self.last_session_date_label.setText(
            session_date
        )

        self.last_session_time_label.setText(
            f"Orario: {started_at} - {ended_at}"
        )

        self.last_session_patients_label.setText(
            f"Pazienti serviti: {patients} · "
            f"Durata: {self._format_duration(duration)}"
        )

        self.last_session_rate_label.setText(
            "Media: "
            f"{self._format_rate(rate)} "
            "pazienti/ora"
        )

    def _on_controller_state_changed(
        self,
        complete_state: object,
    ) -> None:
        self.refresh_dashboard()

    def _on_settings_changed(
        self,
        config: object,
    ) -> None:
        self.doctor_label.setText(
            self.controller.doctor_name
        )
        self.refresh_dashboard()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #eef3f8;
            }

            QLabel#dashboardTitle {
                color: #16324a;
                font-size: 30px;
                font-weight: 900;
                letter-spacing: 2px;
            }

            QLabel#dashboardDoctor {
                color: #2c6088;
                font-size: 21px;
                font-weight: 800;
            }

            QLabel#dashboardQueueStatus {
                color: #7b8b98;
                font-size: 16px;
                font-weight: 800;
            }

            QLabel#dashboardQueueStatus[active="true"] {
                color: #218b5d;
            }

            QLabel#dashboardSection {
                color: #2c6088;
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 2px;
            }

            QFrame#dashboardCard,
            QFrame#dashboardAccentCard {
                background-color: white;
                border: 1px solid #d6e1ea;
                border-radius: 18px;
                min-height: 145px;
            }

            QFrame#dashboardAccentCard {
                border-top: 7px solid #218b5d;
            }

            QLabel#dashboardCardTitle {
                color: #60758a;
                font-size: 14px;
                font-weight: 800;
            }

            QLabel#dashboardCardValue {
                color: #16324a;
                font-size: 32px;
                font-weight: 900;
            }

            QLabel#dashboardCardSubtitle {
                color: #7b8b98;
                font-size: 13px;
                font-weight: 600;
            }

            QFrame#dashboardLastSession {
                background-color: white;
                border: 1px solid #d6e1ea;
                border-radius: 16px;
            }

            QLabel#dashboardLastDate {
                color: #16324a;
                font-size: 20px;
                font-weight: 900;
            }

            QLabel#dashboardLastDetail {
                color: #526b7d;
                font-size: 15px;
                font-weight: 600;
            }

            QPushButton {
                border: none;
                border-radius: 11px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: 700;
                min-height: 28px;
            }

            QPushButton#dashboardPrimaryButton {
                background-color: #218b5d;
                color: white;
            }

            QPushButton#dashboardPrimaryButton:hover {
                background-color: #19794f;
            }

            QPushButton#dashboardSecondaryButton {
                background-color: #dfe7ee;
                color: #334b5d;
            }

            QPushButton#dashboardSecondaryButton:hover {
                background-color: #d2dde6;
            }
            """
        )

    @staticmethod
    def _safe_int(
        value: object,
    ) -> int:
        try:
            return max(
                0,
                int(value),
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _format_seconds(value: object) -> str:
        if value is None:
            return "—"
        try:
            seconds = max(0, int(value))
        except (TypeError, ValueError):
            return "—"
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_duration(
        minutes: int,
    ) -> str:
        safe_minutes = max(
            0,
            int(minutes),
        )

        hours, remaining_minutes = divmod(
            safe_minutes,
            60,
        )

        if hours <= 0:
            return f"{remaining_minutes} min"

        return (
            f"{hours} h "
            f"{remaining_minutes:02d} min"
        )

    @staticmethod
    def _format_rate(
        value: object,
    ) -> str:
        if value is None:
            return "—"

        try:
            return f"{float(value):.2f}"
        except (
            TypeError,
            ValueError,
        ):
            return "—"

    @staticmethod
    def _format_decimal(
        value: object,
    ) -> str:
        try:
            number = float(value)

            if number.is_integer():
                return str(int(number))

            return f"{number:.2f}"

        except (
            TypeError,
            ValueError,
        ):
            return "0"

    @staticmethod
    def _format_date(
        iso_date: str,
    ) -> str:
        try:
            return datetime.strptime(
                iso_date,
                "%Y-%m-%d",
            ).strftime(
                "%d/%m/%Y"
            )
        except ValueError:
            return iso_date or "—"

    @staticmethod
    def _short_time(
        value: object,
    ) -> str:
        if value is None:
            return "—"

        clean_value = str(
            value
        ).strip()

        if not clean_value:
            return "—"

        return clean_value[:5]
