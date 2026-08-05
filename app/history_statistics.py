from __future__ import annotations

from datetime import date
from typing import Any

from app.history_storage import get_history_for_doctor


def get_personal_dashboard(
    doctor_id: str,
    current_number: int,
    queue_active: bool,
) -> dict[str, Any]:
    """
    Costruisce tutti i dati necessari alla dashboard personale.

    Lo storico viene già filtrato dal metodo
    get_history_for_doctor(), quindi vengono utilizzate
    esclusivamente le sessioni del medico locale.
    """
    history = get_history_for_doctor(doctor_id)

    today = date.today()
    today_iso = today.isoformat()
    current_month = today.strftime("%Y-%m")

    today_sessions = [
        entry
        for entry in history
        if str(entry.get("date", "")) == today_iso
    ]

    month_sessions = [
        entry
        for entry in history
        if str(entry.get("date", "")).startswith(
            current_month
        )
    ]

    today_patients = sum(
        _safe_int(
            entry.get("patients_served", 0)
        )
        for entry in today_sessions
    )

    today_duration_minutes = sum(
        _safe_optional_int(
            entry.get("duration_minutes")
        )
        or 0
        for entry in today_sessions
    )

    today_rate = _calculate_rate(
        patients=today_patients,
        duration_minutes=today_duration_minutes,
    )

    month_patients = sum(
        _safe_int(
            entry.get("patients_served", 0)
        )
        for entry in month_sessions
    )

    daily_totals = _group_patients_by_date(
        month_sessions
    )

    active_days = len(daily_totals)

    if active_days > 0:
        month_daily_average = round(
            month_patients / active_days,
            2,
        )
    else:
        month_daily_average = 0.0

    best_day_date = ""
    best_day_patients = 0

    if daily_totals:
        best_day_date, best_day_patients = max(
            daily_totals.items(),
            key=lambda item: item[1],
        )

    last_session = _find_last_completed_session(
        history
    )

    return {
        "doctor_id": doctor_id,
        "current_number": max(
            0,
            int(current_number),
        ),
        "queue_active": bool(queue_active),
        "today": {
            "patients_served": today_patients,
            "duration_minutes": today_duration_minutes,
            "patients_per_hour": today_rate,
            "sessions": len(today_sessions),
        },
        "month": {
            "patients_served": month_patients,
            "active_days": active_days,
            "daily_average": month_daily_average,
            "best_day_date": best_day_date,
            "best_day_patients": best_day_patients,
        },
        "last_session": last_session,
    }


def _group_patients_by_date(
    sessions: list[dict[str, Any]],
) -> dict[str, int]:
    totals: dict[str, int] = {}

    for entry in sessions:
        entry_date = str(
            entry.get("date", "")
        )

        if not entry_date:
            continue

        totals[entry_date] = (
            totals.get(entry_date, 0)
            + _safe_int(
                entry.get(
                    "patients_served",
                    0,
                )
            )
        )

    return totals


def _find_last_completed_session(
    history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for entry in history:
        if entry.get("ended_at") is None:
            continue

        return {
            "date": str(
                entry.get("date", "")
            ),
            "started_at": str(
                entry.get("started_at", "")
            ),
            "ended_at": str(
                entry.get("ended_at", "")
            ),
            "patients_served": _safe_int(
                entry.get(
                    "patients_served",
                    0,
                )
            ),
            "duration_minutes": (
                _safe_optional_int(
                    entry.get(
                        "duration_minutes"
                    )
                )
            ),
            "patients_per_hour": (
                _safe_optional_float(
                    entry.get(
                        "patients_per_hour"
                    )
                )
            ),
        }

    return None


def _calculate_rate(
    *,
    patients: int,
    duration_minutes: int,
) -> float | None:
    if duration_minutes <= 0:
        return None

    return round(
        patients / duration_minutes * 60,
        2,
    )


def _safe_int(
    value: object,
) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_optional_int(
    value: object,
) -> int | None:
    if value is None:
        return None

    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _safe_optional_float(
    value: object,
) -> float | None:
    if value is None:
        return None

    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None