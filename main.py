import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.config import load_config, set_active_profile
from app.controller import AppController
from app.paths import ensure_data_directories, migrate_legacy_data
from app.profile_selection_dialog import ProfileSelectionDialog
from app.setup_dialog import SetupDialog
from app.storage import set_active_storage_profile
from app.window import MainWindow


VALID_PROFILES = {
    "doctor1",
    "doctor2",
}


def read_profile_argument() -> str | None:
    if len(sys.argv) < 2:
        return None

    requested_profile = sys.argv[1].strip().lower()

    if requested_profile not in VALID_PROFILES:
        print(
            "Profilo non valido.\n"
            "Usa uno dei seguenti comandi:\n"
            "  python main.py\n"
            "  python main.py doctor1\n"
            "  python main.py doctor2"
        )
        sys.exit(1)

    return requested_profile


def load_available_profiles() -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []

    for profile_id, default_label in (
        ("doctor1", "Medico 1"),
        ("doctor2", "Medico 2"),
    ):
        set_active_profile(profile_id)
        config = load_config()

        configured = bool(
            config.get(
                "configured",
                False,
            )
        )

        doctor_name = str(
            config.get(
                "doctor_name",
                "",
            )
        ).strip()

        profiles.append(
            {
                "doctor_id": profile_id,
                "doctor_name": (
                    doctor_name
                    if doctor_name
                    else default_label
                ),
                "configured": configured,
            }
        )

    set_active_profile(None)

    return profiles


def choose_profile() -> str | None:
    dialog = ProfileSelectionDialog(
        profiles=load_available_profiles()
    )

    if (
        dialog.exec()
        != QDialog.DialogCode.Accepted
    ):
        return None

    return dialog.selected_profile


def main() -> None:
    ensure_data_directories()
    migrate_legacy_data()

    app = QApplication(sys.argv)

    profile = read_profile_argument()

    if profile is None:
        profile = choose_profile()

        if profile is None:
            sys.exit(0)

    set_active_profile(profile)
    set_active_storage_profile(profile)

    config = load_config()

    if not config["configured"]:
        setup_dialog = SetupDialog(
            forced_doctor_id=profile
        )

        if (
            setup_dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            sys.exit(0)

    controller = AppController()
    window = MainWindow(controller)

    window.show()
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
