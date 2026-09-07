from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


# =========================================================
# GESTIONE TURNI - AGGIORNAMENTI
# =========================================================

CURRENT_VERSION = "1.8.8"

GITHUB_OWNER = "Chivas1504"
GITHUB_REPO = "GestioneTurni"

LATEST_RELEASE_API = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)

USER_AGENT = f"GestioneTurni/{CURRENT_VERSION}"

INSTALLER_PATTERN = re.compile(
    r"^Setup_GestioneTurni_v(\d+(?:\.\d+)*)\.exe$",
    re.IGNORECASE,
)


def version_tuple(version: str) -> tuple[int, ...]:
    version = str(version).strip().lstrip("vV")

    result = []

    for part in version.split("."):
        match = re.match(r"(\d+)", part)

        if not match:
            break

        result.append(int(match.group(1)))

    return tuple(result) if result else (0,)


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_tuple = version_tuple(candidate)
    current_tuple = version_tuple(current)

    size = max(len(candidate_tuple), len(current_tuple))

    candidate_tuple += (0,) * (size - len(candidate_tuple))
    current_tuple += (0,) * (size - len(current_tuple))

    return candidate_tuple > current_tuple


class UpdateChecker(QObject):

    update_available = Signal(object)
    no_update = Signal()
    check_failed = Signal(str)

    download_progress = Signal(int)
    installer_ready = Signal(str)
    download_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.release = None

    # =====================================================
    # CONTROLLO RELEASE
    # =====================================================

    def check_async(self, show_no_update=False):

        def worker():

            try:
                request = urllib.request.Request(
                    LATEST_RELEASE_API,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": USER_AGENT,
                    },
                )

                with urllib.request.urlopen(
                    request,
                    timeout=10,
                ) as response:
                    data = json.loads(
                        response.read().decode("utf-8")
                    )

                tag = str(
                    data.get("tag_name", "")
                ).strip()

                if not tag:
                    raise ValueError(
                        "La release GitHub non contiene "
                        "un numero di versione valido."
                    )

                if not is_newer_version(
                    tag,
                    CURRENT_VERSION,
                ):
                    if show_no_update:
                        self.no_update.emit()

                    return

                installer = None

                for asset in data.get("assets", []):

                    if not isinstance(asset, dict):
                        continue

                    name = str(
                        asset.get("name", "")
                    )

                    download_url = str(
                        asset.get(
                            "browser_download_url",
                            "",
                        )
                    )

                    if (
                        INSTALLER_PATTERN.match(name)
                        and download_url
                    ):
                        installer = {
                            "name": name,
                            "url": download_url,
                            "size": int(
                                asset.get("size", 0) or 0
                            ),
                        }

                        break

                if installer is None:
                    raise ValueError(
                        f"È disponibile {tag}, ma nella "
                        f"GitHub Release non è presente "
                        f"l'installer "
                        f"Setup_GestioneTurni_vX.X.X.exe."
                    )

                release = {
                    "version": tag.lstrip("vV"),
                    "tag": tag,
                    "name": str(
                        data.get("name") or tag
                    ),
                    "notes": str(
                        data.get("body") or ""
                    ).strip(),
                    "installer": installer,
                }

                self.release = release

                self.update_available.emit(
                    release
                )

            except urllib.error.HTTPError as error:

                if error.code == 404:
                    self.check_failed.emit(
                        "Non è stata ancora pubblicata "
                        "nessuna GitHub Release."
                    )

                else:
                    self.check_failed.emit(
                        f"Errore GitHub HTTP "
                        f"{error.code}."
                    )

            except urllib.error.URLError:

                self.check_failed.emit(
                    "Connessione Internet "
                    "non disponibile."
                )

            except Exception as error:

                self.check_failed.emit(
                    str(error)
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    # =====================================================
    # DOWNLOAD INSTALLER
    # =====================================================

    def download_async(self, release=None):

        release = release or self.release

        if not isinstance(release, dict):
            self.download_failed.emit(
                "Informazioni aggiornamento non disponibili."
            )
            return

        installer = release.get("installer")

        if not installer:
            self.download_failed.emit(
                "Installer non disponibile."
            )
            return

        url = installer["url"]
        filename = installer["name"]

        def worker():

            max_attempts = 3

            retryable_http_codes = {
                502,
                503,
                504,
            }

            last_error = None

            for attempt in range(
                1,
                max_attempts + 1,
            ):

                update_dir = None

                try:
                    update_dir = Path(
                        tempfile.mkdtemp(
                            prefix="GestioneTurni_Update_"
                        )
                    )

                    destination = (
                        update_dir
                        / filename
                    )

                    request = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": USER_AGENT,
                            "Accept": "application/octet-stream",
                        },
                    )

                    with urllib.request.urlopen(
                        request,
                        timeout=120,
                    ) as response:

                        total = int(
                            response.headers.get(
                                "Content-Length",
                                0,
                            )
                            or 0
                        )

                        downloaded = 0

                        with destination.open(
                            "wb"
                        ) as file:

                            while True:

                                chunk = response.read(
                                    256 * 1024
                                )

                                if not chunk:
                                    break

                                file.write(chunk)

                                downloaded += len(
                                    chunk
                                )

                                if total > 0:
                                    percent = int(
                                        downloaded
                                        * 100
                                        / total
                                    )

                                    self.download_progress.emit(
                                        min(
                                            percent,
                                            99,
                                        )
                                    )

                            file.flush()
                            os.fsync(
                                file.fileno()
                            )

                    if (
                        total > 0
                        and downloaded < total
                    ):
                        raise IOError(
                            "Download incompleto: "
                            f"{downloaded} byte "
                            f"ricevuti su "
                            f"{total} previsti."
                        )

                    if not destination.exists():
                        raise FileNotFoundError(
                            "Installer scaricato "
                            "non trovato."
                        )

                    if (
                        destination.stat().st_size
                        <= 0
                    ):
                        raise IOError(
                            "L'installer scaricato "
                            "è vuoto."
                        )

                    self.download_progress.emit(
                        100
                    )

                    self.installer_ready.emit(
                        str(destination)
                    )

                    return

                except urllib.error.HTTPError as error:

                    last_error = error

                    if update_dir is not None:
                        shutil.rmtree(
                            update_dir,
                            ignore_errors=True,
                        )

                    if (
                        error.code
                        not in retryable_http_codes
                    ):
                        break

                except (
                    urllib.error.URLError,
                    TimeoutError,
                ) as error:

                    last_error = error

                    if update_dir is not None:
                        shutil.rmtree(
                            update_dir,
                            ignore_errors=True,
                        )

                except Exception as error:

                    last_error = error

                    if update_dir is not None:
                        shutil.rmtree(
                            update_dir,
                            ignore_errors=True,
                        )

                    break

                if attempt < max_attempts:
                    time.sleep(
                        3 * attempt
                    )

            if isinstance(
                last_error,
                urllib.error.HTTPError,
            ):
                self.download_failed.emit(
                    (
                        "GitHub non ha risposto "
                        "correttamente dopo "
                        f"{max_attempts} tentativi.\n\n"
                        f"HTTP Error "
                        f"{last_error.code}: "
                        f"{last_error.reason}"
                    )
                )

            else:
                self.download_failed.emit(
                    (
                        "Impossibile scaricare "
                        "l'aggiornamento dopo "
                        f"{max_attempts} tentativi.\n\n"
                        f"{last_error}"
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()


class UpdateManager(QObject):

    def __init__(
        self,
        parent_window,
    ):
        super().__init__(
            parent_window
        )

        self.parent_window = (
            parent_window
        )

        self.checker = UpdateChecker(
            self
        )

        self.automatic_check = True
        self.download_message = None

        self.checker.update_available.connect(
            self.on_update_available
        )

        self.checker.no_update.connect(
            self.on_no_update
        )

        self.checker.check_failed.connect(
            self.on_check_failed
        )

        self.checker.download_progress.connect(
            self.on_download_progress
        )

        self.checker.installer_ready.connect(
            self.on_installer_ready
        )

        self.checker.download_failed.connect(
            self.on_download_failed
        )

    # =====================================================
    # CONTROLLO
    # =====================================================

    def check_for_updates(
        self,
        manual=False,
    ):

        self.automatic_check = (
            not manual
        )

        self.checker.check_async(
            show_no_update=manual
        )

    # =====================================================
    # UPDATE TROVATO
    # =====================================================

    def on_update_available(
        self,
        release,
    ):

        version = release[
            "version"
        ]

        notes = release.get(
            "notes",
            "",
        )

        message = (
            f"È disponibile una nuova "
            f"versione di Gestione Turni.\n\n"
            f"Versione installata: "
            f"{CURRENT_VERSION}\n"
            f"Nuova versione: "
            f"{version}"
        )

        if notes:

            if len(notes) > 600:
                notes = (
                    notes[:600]
                    + "..."
                )

            message += (
                "\n\nNovità:\n"
                + notes
            )

        message += (
            "\n\nVuoi aggiornare adesso?"
        )

        answer = QMessageBox.question(
            self.parent_window,
            "Aggiornamento disponibile",
            message,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.download_message = (
            QMessageBox(
                self.parent_window
            )
        )

        self.download_message.setWindowTitle(
            "Aggiornamento"
        )

        self.download_message.setText(
            "Download aggiornamento "
            "in corso..."
        )

        self.download_message.setStandardButtons(
            QMessageBox.StandardButton.NoButton
        )

        self.download_message.show()

        self.checker.download_async(
            release
        )

    # =====================================================
    # NESSUN UPDATE
    # =====================================================

    def on_no_update(self):

        QMessageBox.information(
            self.parent_window,
            "Aggiornamenti",
            (
                f"Gestione Turni "
                f"{CURRENT_VERSION} "
                f"è già aggiornato."
            ),
        )

    # =====================================================
    # ERRORE CONTROLLO
    # =====================================================

    def on_check_failed(
        self,
        message,
    ):

        if self.automatic_check:
            return

        QMessageBox.warning(
            self.parent_window,
            "Controllo aggiornamenti",
            message,
        )

    # =====================================================
    # PROGRESSO DOWNLOAD
    # =====================================================

    def on_download_progress(
        self,
        percent,
    ):

        if self.download_message:
            self.download_message.setText(
                f"Download aggiornamento "
                f"in corso... {percent}%"
            )

    # =====================================================
    # INSTALLER PRONTO
    # =====================================================

    def on_installer_ready(
        self,
        installer_path,
    ):

        if self.download_message:
            self.download_message.close()
            self.download_message.deleteLater()
            self.download_message = None

        installer = Path(
            installer_path
        )

        if not installer.exists():
            QMessageBox.warning(
                self.parent_window,
                "Aggiornamento",
                "Installer non trovato.",
            )
            return

        try:

            if sys.platform == "win32":
                os.startfile(
                    str(installer)
                )

            else:
                subprocess.Popen(
                    [str(installer)]
                )

        except Exception as error:

            QMessageBox.critical(
                self.parent_window,
                "Aggiornamento",
                (
                    "Impossibile avviare "
                    "l'installer:\n\n"
                    f"{error}"
                ),
            )

            return

        QApplication.closeAllWindows()

        QTimer.singleShot(
            100,
            QApplication.quit,
        )

    # =====================================================
    # DOWNLOAD FALLITO
    # =====================================================

    def on_download_failed(
        self,
        message,
    ):

        if self.download_message:
            self.download_message.close()
            self.download_message.deleteLater()
            self.download_message = None

        QMessageBox.warning(
            self.parent_window,
            "Aggiornamento",
            (
                "Impossibile scaricare "
                "l'aggiornamento.\n\n"
                f"{message}"
            ),
        )