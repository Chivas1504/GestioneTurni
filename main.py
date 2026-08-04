import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.config import load_config
from app.setup_dialog import SetupDialog
from app.window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    config = load_config()

    if not config["configured"]:
        setup_dialog = SetupDialog()

        if setup_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

        config = load_config()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()