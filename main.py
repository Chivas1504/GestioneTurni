import json
import logging
import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.account_dialog import AccountEntryDialog
from app.accounts import AccountStore
from app.config import load_config, save_config, set_active_profile
from app.controller import AppController
from app.logging_config import configure_logging, install_exception_hook
from app.network import NetworkManager
from app.paths import CONFIG_DIR, ensure_data_directories, migrate_legacy_data
from app.resources import app_icon
from app.storage import set_active_storage_profile
from app.version import APP_NAME, APP_VERSION
from app.window import MainWindow


def migrate_legacy_accounts(store: AccountStore) -> None:
    for legacy_id in ("doctor1", "doctor2"):
        path = CONFIG_DIR / f"config_{legacy_id}.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or not data.get("configured"):
            continue
        name = str(data.get("doctor_name", "")).strip()
        if not name or not data.get("password_hash") or not data.get("password_salt"):
            continue
        record = {
            "doctor_id": legacy_id,
            "doctor_name": name,
            "queue_prefix": str(data.get("queue_prefix", "")).strip().upper()[:1],
            "password_salt": str(data.get("password_salt", "")),
            "password_hash": str(data.get("password_hash", "")),
            "password_iterations": int(data.get("password_iterations", 390000) or 390000),
            "patient_time_warning_enabled": bool(data.get("patient_time_warning_enabled", False)),
            "patient_time_warning_minutes": int(data.get("patient_time_warning_minutes", 15) or 15),
            "patient_time_warning_sound_enabled": bool(data.get("patient_time_warning_sound_enabled", False)),
            "updated_at": 1.0,
        }
        store.import_record(record)


def select_account(store: AccountStore) -> dict | None:
    server = NetworkManager.discover_server_once()
    remote_accounts = []
    if server:
        response = NetworkManager.account_rpc({"type": "GESTIONE_TURNI_ACCOUNTS_LIST"}, server)
        if response and response.get("ok") and isinstance(response.get("accounts"), list):
            remote_accounts = response["accounts"]

    accounts_by_id = {str(a.get("doctor_id", "")): a for a in store.list_public()}
    for account in remote_accounts:
        if isinstance(account, dict) and account.get("doctor_id"):
            accounts_by_id[str(account["doctor_id"])] = account

    def authenticate(doctor_id: str, password: str):
        if server:
            response = NetworkManager.account_rpc({
                "type": "GESTIONE_TURNI_ACCOUNT_AUTH",
                "doctor_id": doctor_id,
                "password": password,
            }, server)
            if response and response.get("ok") and isinstance(response.get("account"), dict):
                account = dict(response["account"])
                store.import_record(account)
                return account
        return store.verify(doctor_id, password)

    def create_account(name: str, password: str):
        if server:
            response = NetworkManager.account_rpc({
                "type": "GESTIONE_TURNI_ACCOUNT_CREATE",
                "doctor_name": name,
                "password": password,
            }, server)
            if response and response.get("ok") and isinstance(response.get("account"), dict):
                account = dict(response["account"])
                store.import_record(account)
                return account
            if response and response.get("error"):
                raise ValueError(str(response["error"]))
        return store.create(name, password)

    dialog = AccountEntryDialog(list(accounts_by_id.values()), authenticate, create_account)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_account


def prepare_account_config(account: dict) -> None:
    doctor_id = str(account.get("doctor_id", "")).strip()
    set_active_profile(doctor_id)
    set_active_storage_profile(doctor_id)
    config = load_config()
    config.update({
        "configured": True,
        "doctor_id": doctor_id,
        "doctor_name": str(account.get("doctor_name", "")).strip(),
        "queue_prefix": str(account.get("queue_prefix", config.get("queue_prefix", ""))).strip().upper()[:1],
        "password_salt": str(account.get("password_salt", "")),
        "password_hash": str(account.get("password_hash", "")),
        "password_iterations": int(account.get("password_iterations", 390000) or 390000),
        "patient_time_warning_enabled": bool(account.get("patient_time_warning_enabled", config.get("patient_time_warning_enabled", False))),
        "patient_time_warning_minutes": int(account.get("patient_time_warning_minutes", config.get("patient_time_warning_minutes", 15)) or 15),
        "patient_time_warning_sound_enabled": bool(account.get("patient_time_warning_sound_enabled", config.get("patient_time_warning_sound_enabled", False))),
    })
    save_config(config)


def main() -> None:
    ensure_data_directories()
    configure_logging()
    install_exception_hook()
    logging.info("Avvio %s %s", APP_NAME, APP_VERSION)
    migrate_legacy_data()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(app_icon())

    account_store = AccountStore()
    migrate_legacy_accounts(account_store)
    account = select_account(account_store)
    if account is None:
        sys.exit(0)

    prepare_account_config(account)
    controller = AppController(account_store=account_store)
    window = MainWindow(controller)
    window.show()
    controller.start()

    exit_code = app.exec()
    logging.info("Chiusura applicazione con codice %s", exit_code)
    logging.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
