from __future__ import annotations

from app.styles import DIALOG_STYLE

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.history_storage import (
    clear_history_for_doctor,
    get_history_for_doctor,
)


from app.resources import app_icon

class SortableTableItem(QTableWidgetItem):

    def __init__(
        self,
        text: str,
        sort_value: object,
    ) -> None:
        super().__init__(text)

        self.sort_value = sort_value

    def __lt__(
        self,
        other: QTableWidgetItem,
    ) -> bool:
        if isinstance(
            other,
            SortableTableItem,
        ):
            return self.sort_value < other.sort_value

        return super().__lt__(other)


class HistoryDialog(QDialog):
    def __init__(
        self,
        *,
        doctor_id: str,
        doctor_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowIcon(app_icon())

        self.doctor_id = doctor_id
        self.doctor_name = doctor_name
        self.history: list[dict[str, Any]] = []
        self.filtered_history: list[
            dict[str, Any]
        ] = []

        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        self.setWindowTitle(
            "Storico visite"
        )
        self.setMinimumSize(1050, 620)
        self.resize(1200, 720)

        self._build_interface()
        self._apply_style()
        self.refresh_history()

    def _build_interface(self) -> None:
        title_label = QLabel(
            "Storico visite"
        )
        title_label.setObjectName(
            "historyTitle"
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
        )

        self.doctor_label = QLabel(
            self.doctor_name
        )
        self.doctor_label.setObjectName(
            "historyDoctor"
        )
        self.doctor_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Cerca per data o cognome del paziente"
        )
        self.search_input.setClearButtonEnabled(
            True
        )
        self.search_input.setMinimumHeight(44)
        self.search_input.textChanged.connect(
            self.apply_filter
        )

        self.summary_label = QLabel()
        self.summary_label.setObjectName(
            "historySummary"
        )

        search_layout = QHBoxLayout()
        search_layout.setSpacing(14)
        search_layout.addWidget(
            QLabel("Ricerca:")
        )
        search_layout.addWidget(
            self.search_input,
            stretch=1,
        )
        search_layout.addWidget(
            self.summary_label
        )

        self.table = QTableWidget()
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Data",
                "Inizio",
                "Fine",
                "N. iniziale",
                "Ultimo n.",
                "Pazienti",
                "Durata",
                "Pazienti/ora",
            ]
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        # Evita il rettangolo di focus disegnato sopra il testo
        # della cella selezionata (in particolare sulla colonna Data).
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setAlternatingRowColors(
            True
        )
        self.table.setSortingEnabled(
            True
        )
        self.table.verticalHeader().setVisible(
            False
        )
        self.table.itemSelectionChanged.connect(
            self.update_patient_details
        )

        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(84)
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.patient_details_title = QLabel(
            "PAZIENTI DELLA SESSIONE"
        )
        self.patient_details_title.setObjectName(
            "patientDetailsTitle"
        )

        self.patient_details_hint = QLabel(
            "Seleziona una sessione per vedere la durata di ogni paziente."
        )
        self.patient_details_hint.setObjectName(
            "patientDetailsHint"
        )

        self.patient_table = QTableWidget()
        self.patient_table.setShowGrid(False)
        self.patient_table.verticalHeader().setDefaultSectionSize(42)
        self.patient_table.setColumnCount(2)
        self.patient_table.setHorizontalHeaderLabels(
            ["Paziente", "Durata"]
        )
        self.patient_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.patient_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.patient_table.setAlternatingRowColors(True)
        self.patient_table.verticalHeader().setVisible(False)
        self.patient_table.setMaximumHeight(190)
        patient_header = self.patient_table.horizontalHeader()
        patient_header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.refresh_button = QPushButton(
            "Aggiorna"
        )
        self.refresh_button.setObjectName(
            "historySecondaryButton"
        )
        self.refresh_button.clicked.connect(
            self.refresh_history
        )

        self.export_button = QPushButton(
            "Esporta CSV"
        )
        self.export_button.setObjectName(
            "historyPrimaryButton"
        )
        self.export_button.clicked.connect(
            self.export_csv
        )

        self.clear_button = QPushButton(
            "Cancella storico"
        )
        self.clear_button.setObjectName(
            "historyDangerButton"
        )
        self.clear_button.clicked.connect(
            self.confirm_clear_history
        )

        self.close_button = QPushButton(
            "Chiudi"
        )
        self.close_button.setObjectName(
            "historySecondaryButton"
        )
        self.close_button.clicked.connect(
            self.close
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.addWidget(
            self.clear_button
        )
        buttons_layout.addStretch()
        buttons_layout.addWidget(
            self.refresh_button
        )
        buttons_layout.addWidget(
            self.export_button
        )
        buttons_layout.addWidget(
            self.close_button
        )

        self.empty_label = QLabel()
        self.empty_label.setObjectName("historyEmpty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setMinimumHeight(140)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            32,
            28,
            32,
            22,
        )
        main_layout.setSpacing(16)
        main_layout.addWidget(title_label)
        main_layout.addWidget(
            self.doctor_label
        )
        main_layout.addLayout(
            search_layout
        )
        main_layout.addWidget(
            self.table,
            stretch=1,
        )
        main_layout.addWidget(self.empty_label, 1)
        main_layout.addWidget(
            self.patient_details_title
        )
        main_layout.addWidget(
            self.patient_details_hint
        )
        main_layout.addWidget(
            self.patient_table
        )
        main_layout.addLayout(
            buttons_layout
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(DIALOG_STYLE)

    def refresh_history(self) -> None:
        self.history = get_history_for_doctor(
            self.doctor_id
        )
        self.apply_filter()

    def apply_filter(self) -> None:
        search_text = (
            self.search_input.text()
            .strip()
            .lower()
        )

        if not search_text:
            self.filtered_history = list(
                self.history
            )
        else:
            self.filtered_history = [
                entry
                for entry in self.history
                if self._entry_matches(
                    entry,
                    search_text,
                )
            ]

        self.populate_table()
        self.update_summary()

    def _entry_matches(
        self,
        entry: dict[str, Any],
        search_text: str,
    ) -> bool:
        iso_date = str(
            entry.get("date", "")
        )

        display_date = self._format_date(
            iso_date
        )

        patient_visits = entry.get("patient_visits", [])
        patient_text = self._format_patient_visits(patient_visits)

        searchable_values = [
            iso_date.lower(),
            display_date.lower(),
            str(
                entry.get("started_at", "")
            ).lower(),
            str(
                entry.get("ended_at", "")
            ).lower(),
            patient_text.lower(),
        ]

        return any(
            search_text in value
            for value in searchable_values
        )

    def populate_table(self) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(
            len(self.filtered_history)
        )

        for row, entry in enumerate(
            self.filtered_history
        ):
            iso_date = str(
                entry.get("date", "")
            )
            started_at = self._short_time(
                entry.get("started_at")
            )
            ended_at = self._short_time(
                entry.get("ended_at")
            )

            starting_number = self._safe_int(
                entry.get(
                    "starting_number",
                    0,
                )
            )
            last_number = self._safe_int(
                entry.get(
                    "last_number",
                    0,
                )
            )
            patients_served = self._safe_int(
                entry.get(
                    "patients_served",
                    0,
                )
            )

            duration_minutes = entry.get(
                "duration_minutes"
            )
            patients_per_hour = entry.get(
                "patients_per_hour"
            )

            values = [
                SortableTableItem(
                    self._format_date(
                        iso_date
                    ),
                    iso_date,
                ),
                SortableTableItem(
                    started_at,
                    started_at,
                ),
                SortableTableItem(
                    ended_at,
                    ended_at,
                ),
                SortableTableItem(
                    str(starting_number),
                    starting_number,
                ),
                SortableTableItem(
                    str(last_number),
                    last_number,
                ),
                SortableTableItem(
                    str(patients_served),
                    patients_served,
                ),
                SortableTableItem(
                    self._format_duration(
                        duration_minutes
                    ),
                    self._numeric_or_negative(
                        duration_minutes
                    ),
                ),
                SortableTableItem(
                    self._format_rate(
                        patients_per_hour
                    ),
                    self._numeric_or_negative(
                        patients_per_hour
                    ),
                ),
            ]

            for column, item in enumerate(
                values
            ):
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    entry,
                )
                self.table.setItem(
                    row,
                    column,
                    item,
                )

        self.table.setSortingEnabled(True)
        has_rows = bool(self.filtered_history)
        self.empty_label.setText("Nessuna visita registrata\nLe sessioni dello studio compariranno qui." if not self.history
                                 else "Nessun risultato\nProva un’altra data o un altro cognome.")
        self.empty_label.setVisible(not has_rows)
        for widget in (self.table, self.patient_table, self.patient_details_title, self.patient_details_hint):
            widget.setVisible(has_rows)
        self.export_button.setEnabled(has_rows)
        self.clear_button.setEnabled(bool(self.history))

        if self.table.rowCount() > 0:
            self.table.selectRow(0)
        else:
            self.update_patient_details()


    def update_patient_details(self) -> None:
        selected_items = self.table.selectedItems()

        if not selected_items:
            self.patient_table.setRowCount(0)
            self.patient_details_hint.setText(
                "Seleziona una sessione per vedere la durata di ogni paziente."
            )
            return

        entry = selected_items[0].data(
            Qt.ItemDataRole.UserRole
        )

        if not isinstance(entry, dict):
            self.patient_table.setRowCount(0)
            return

        visits = entry.get("patient_visits", [])
        if not isinstance(visits, list):
            visits = []

        valid_visits = [
            visit
            for visit in visits
            if isinstance(visit, dict)
        ]

        self.patient_table.setRowCount(
            len(valid_visits)
        )

        if not valid_visits:
            self.patient_details_hint.setText(
                "Per questa sessione non sono presenti tempi paziente registrati."
            )
            return

        self.patient_details_hint.setText(
            f"{len(valid_visits)} pazienti con durata registrata"
        )

        for row, visit in enumerate(valid_visits):
            ticket = str(
                visit.get("ticket", "")
            ).strip()

            if not ticket:
                prefix = str(
                    visit.get("queue_prefix", "")
                ).strip().upper()
                number = self._safe_int(
                    visit.get("number", 0)
                )
                ticket = f"{prefix}{number}"

            duration = self._format_patient_duration(
                visit.get("duration_seconds", 0)
            )

            ticket_item = QTableWidgetItem(ticket or "—")
            duration_item = QTableWidgetItem(duration)

            ticket_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            duration_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self.patient_table.setItem(
                row, 0, ticket_item
            )
            self.patient_table.setItem(
                row, 1, duration_item
            )

    @staticmethod
    def _format_patient_duration(value: object) -> str:
        try:
            seconds = max(0, int(value))
        except (TypeError, ValueError):
            seconds = 0

        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

        return f"{minutes:02d}:{secs:02d}"

    def update_summary(self) -> None:
        total_sessions = len(
            self.filtered_history
        )

        total_patients = sum(
            self._safe_int(
                entry.get(
                    "patients_served",
                    0,
                )
            )
            for entry in self.filtered_history
        )

        self.summary_label.setText(
            f"{total_sessions} sessioni · "
            f"{total_patients} pazienti"
        )

    def export_csv(self) -> None:
        if not self.filtered_history:
            QMessageBox.information(
                self,
                "Nessun dato",
                "Non ci sono dati da esportare.",
            )
            return

        safe_doctor_name = "".join(
            character
            if character.isalnum()
            else "_"
            for character in self.doctor_name
        ).strip("_")

        default_filename = (
            f"Storico_{safe_doctor_name}_"
            f"{datetime.now():%Y-%m-%d}.csv"
        )

        selected_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Esporta storico personale",
                str(
                    Path.home()
                    / default_filename
                ),
                "File CSV (*.csv)",
            )
        )

        if not selected_path:
            return

        output_path = Path(
            selected_path
        )

        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(
                ".csv"
            )

        try:
            with output_path.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                writer = csv.writer(
                    csv_file,
                    delimiter=";",
                )

                writer.writerow(
                    [
                        "Data",
                        "Medico",
                        "Ora inizio",
                        "Ora fine",
                        "N. iniziale",
                        "Ultimo n.",
                        "Pazienti serviti",
                        "Durata minuti",
                        "Pazienti per ora",
                        "Tempi pazienti",
                    ]
                )

                for entry in (
                    self.filtered_history
                ):
                    writer.writerow(
                        [
                            self._format_date(
                                str(
                                    entry.get(
                                        "date",
                                        "",
                                    )
                                )
                            ),
                            self.doctor_name,
                            self._short_time(
                                entry.get(
                                    "started_at"
                                )
                            ),
                            self._short_time(
                                entry.get(
                                    "ended_at"
                                )
                            ),
                            self._safe_int(
                                entry.get(
                                    "starting_number",
                                    0,
                                )
                            ),
                            self._safe_int(
                                entry.get(
                                    "last_number",
                                    0,
                                )
                            ),
                            self._safe_int(
                                entry.get(
                                    "patients_served",
                                    0,
                                )
                            ),
                            entry.get(
                                "duration_minutes"
                            )
                            or "",
                            entry.get(
                                "patients_per_hour"
                            )
                            or "",
                            self._format_patient_visits(
                                entry.get("patient_visits", [])
                            ),
                        ]
                    )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Errore esportazione",
                (
                    "Non è stato possibile "
                    "salvare il file.\n\n"
                    f"{error}"
                ),
            )
            return

        QMessageBox.information(
            self,
            "Esportazione completata",
            (
                "Lo storico personale è stato "
                "esportato correttamente."
            ),
        )

    def confirm_clear_history(self) -> None:
        if not self.history:
            return

        answer = QMessageBox.warning(
            self,
            "Cancella storico",
            (
                "Vuoi cancellare definitivamente "
                "tutto il tuo storico personale?\n\n"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        clear_history_for_doctor(
            self.doctor_id
        )
        self.refresh_history()

    @staticmethod
    def _format_patient_visits(value: object) -> str:
        if not isinstance(value, list) or not value:
            return "—"

        parts: list[str] = []
        for visit in value:
            if not isinstance(visit, dict):
                continue
            ticket = str(visit.get("ticket", "")).strip()
            try:
                seconds = max(0, int(visit.get("duration_seconds", 0)))
            except (TypeError, ValueError):
                seconds = 0
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            if hours > 0:
                duration = f"{hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                duration = f"{minutes:02d}:{secs:02d}"
            parts.append(f"{ticket or '?'} {duration}")

        return " · ".join(parts) if parts else "—"

    @staticmethod
    def _format_date(
        iso_date: str,
    ) -> str:
        try:
            return datetime.strptime(
                iso_date,
                "%Y-%m-%d",
            ).strftime("%d/%m/%Y")
        except ValueError:
            return iso_date

    @staticmethod
    def _short_time(
        value: object,
    ) -> str:
        if value is None:
            return "In corso"

        clean_value = str(value).strip()

        if not clean_value:
            return "In corso"

        return clean_value[:5]

    @staticmethod
    def _format_duration(
        value: object,
    ) -> str:
        if value is None:
            return "In corso"

        minutes = HistoryDialog._safe_int(
            value
        )

        hours, remaining_minutes = divmod(
            minutes,
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
    def _safe_int(
        value: object,
    ) -> int:
        try:
            return max(0, int(value))
        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _numeric_or_negative(
        value: object,
    ) -> float:
        if value is None:
            return -1.0

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return -1.0
