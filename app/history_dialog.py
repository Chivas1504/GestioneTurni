from __future__ import annotations

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


class SortableTableItem(QTableWidgetItem):
    """
    Elemento della tabella con un valore separato
    utilizzato per l'ordinamento.
    """

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
            "Storico personale"
        )
        self.setMinimumSize(1050, 620)
        self.resize(1200, 720)

        self._build_interface()
        self._apply_style()
        self.refresh_history()

    def _build_interface(self) -> None:
        title_label = QLabel(
            "STORICO PERSONALE"
        )
        title_label.setObjectName(
            "historyTitle"
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.doctor_label = QLabel(
            self.doctor_name
        )
        self.doctor_label.setObjectName(
            "historyDoctor"
        )
        self.doctor_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Cerca per data, ad esempio 05/08/2026"
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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Data",
                "Inizio",
                "Fine",
                "Numero iniziale",
                "Ultimo numero",
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
        self.table.setAlternatingRowColors(
            True
        )
        self.table.setSortingEnabled(
            True
        )
        self.table.verticalHeader().setVisible(
            False
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            30,
            24,
            30,
            26,
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
        main_layout.addLayout(
            buttons_layout
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #eef3f8;
            }

            QLabel#historyTitle {
                color: #16324a;
                font-size: 30px;
                font-weight: 900;
                letter-spacing: 2px;
            }

            QLabel#historyDoctor {
                color: #2c6088;
                font-size: 20px;
                font-weight: 700;
            }

            QLabel#historySummary {
                color: #60758a;
                font-size: 15px;
                font-weight: 700;
            }

            QLineEdit {
                background-color: white;
                color: #213d53;
                border: 1px solid #cbd8e3;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 15px;
            }

            QLineEdit:focus {
                border: 2px solid #218b5d;
            }

            QTableWidget {
                background-color: white;
                alternate-background-color: #f4f7fa;
                color: #213d53;
                border: 1px solid #d4dfe8;
                border-radius: 12px;
                gridline-color: #dfe7ee;
                font-size: 14px;
            }

            QTableWidget::item {
                padding: 10px;
            }

            QTableWidget::item:selected {
                background-color: #cde8dc;
                color: #173e2d;
            }

            QHeaderView::section {
                background-color: #16324a;
                color: white;
                border: none;
                padding: 12px 8px;
                font-size: 14px;
                font-weight: 800;
            }

            QPushButton {
                border: none;
                border-radius: 11px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: 700;
                min-height: 24px;
            }

            QPushButton#historyPrimaryButton {
                background-color: #218b5d;
                color: white;
            }

            QPushButton#historyPrimaryButton:hover {
                background-color: #19794f;
            }

            QPushButton#historySecondaryButton {
                background-color: #dfe7ee;
                color: #334b5d;
            }

            QPushButton#historySecondaryButton:hover {
                background-color: #d2dde6;
            }

            QPushButton#historyDangerButton {
                background-color: #f7e4e2;
                color: #a43c34;
            }

            QPushButton#historyDangerButton:hover {
                background-color: #f1d2cf;
            }
            """
        )

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

        searchable_values = [
            iso_date.lower(),
            display_date.lower(),
            str(
                entry.get("started_at", "")
            ).lower(),
            str(
                entry.get("ended_at", "")
            ).lower(),
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
                self.table.setItem(
                    row,
                    column,
                    item,
                )

        self.table.setSortingEnabled(True)

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
                        "Numero iniziale",
                        "Ultimo numero",
                        "Pazienti serviti",
                        "Durata minuti",
                        "Pazienti per ora",
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