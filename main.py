import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.config import load_config, set_active_profile
from app.controller import AppController
from app.paths import ensure_data_directories, migrate_legacy_data
from app.setup_dialog import SetupDialog
from app.storage import set_active_storage_profile
from app.window import MainWindow


VALID_TEST_PROFILES = {
    "doctor1",
    "doctor2",
}


def read_profile_argument() -> str | None:
    if len(sys.argv) < 2:
        return None

    requested_profile = (
        sys.argv[1].strip().lower()
    )

    if requested_profile not in VALID_TEST_PROFILES:
        print(
            "Profilo non valido.\n"
            "Usa uno dei seguenti comandi:\n"
            "  python main.py\n"
            "  python main.py doctor1\n"
            "  python main.py doctor2"
        )
        sys.exit(1)

    return requested_profile


def main() -> None:
    ensure_data_directories()
    migrate_legacy_data()

    profile = read_profile_argument()

    set_active_profile(profile)
    set_active_storage_profile(profile)

    app = QApplication(sys.argv)

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