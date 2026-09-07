from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


# =========================================================
# GESTIONE TURNI - AGGIORNAMENTO AUTOMATICO
# =========================================================

CURRENT_VERSION = "1.7.10"

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

                # Nessun aggiornamento
                if not is_newer_version(
                    tag,
                    CURRENT_VERSION,
                ):

                    if show_no_update:
                        self.no_update.emit()

                    return

                # Cerchiamo l'installer allegato alla release
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

            import time

            destination = (
                Path(tempfile.gettempdir())
                / filename
            )

            partial = destination.with_suffix(
                ".exe.part"
            )

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

                try:

                    if partial.exists():
                        partial.unlink()

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

                        with partial.open("wb") as file:

                            while True:

                                chunk = response.read(
                                    256 * 1024
                                )

                                if not chunk:
                                    break

                                file.write(chunk)

                                downloaded += len(chunk)

                                if total > 0:

                                    percent = int(
                                        downloaded
                                        * 100
                                        / total
                                    )

                                    self.download_progress.emit(
                                        min(percent, 100)
                                    )

                    if destination.exists():
                        destination.unlink()

                    partial.replace(destination)

                    self.installer_ready.emit(
                        str(destination)
                    )

                    return

                except urllib.error.HTTPError as error:

                    last_error = error

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

                except Exception as error:

                    last_error = error
                    break

                if attempt < max_attempts:
                    time.sleep(3 * attempt)

            try:
                partial.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

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

        # Se è il controllo automatico
        # non disturbiamo il medico.
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

        import os
        import subprocess

        if self.download_message:
            self.download_message.close()
            self.download_message = None

        installer = Path(installer_path)

        if not installer.exists():

            QMessageBox.warning(
                self.parent_window,
                "Aggiornamento",
                "Installer non trovato.",
            )

            return

        QMessageBox.information(
            self.parent_window,
            "Aggiornamento pronto",
            (
                "L'aggiornamento è stato scaricato.\n\n"
                "Gestione Turni verrà chiuso e "
                "l'installazione partirà automaticamente."
            ),
        )

        if sys.platform != "win32":

            try:

                subprocess.Popen(
                    [str(installer)]
                )

                QApplication.quit()

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

        try:

            current_pid = os.getpid()

            # PowerShell esterno:
            # 1. aspetta che Gestione Turni termini;
            # 2. se dopo 15 secondi è ancora aperto, lo termina;
            # 3. avvia l'installer soltanto dopo.
            escaped_installer = (
                str(installer)
                .replace("'", "''")
            )

            powershell_script = (
                f"$pidDaAttendere = {current_pid}; "
                f"$installer = '{escaped_installer}'; "
                "$timeout = 15; "
                "$elapsed = 0; "

                "while ("
                "Get-Process -Id $pidDaAttendere "
                "-ErrorAction SilentlyContinue"
                ") { "

                "if ($elapsed -ge $timeout) { "
                "Stop-Process "
                "-Id $pidDaAttendere "
                "-Force "
                "-ErrorAction SilentlyContinue; "
                "break; "
                "} "

                "Start-Sleep -Seconds 1; "
                "$elapsed++; "
                "} "

                "Start-Sleep -Seconds 1; "

                "Start-Process "
                "-FilePath $installer"
            )

            creation_flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
            )

            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    powershell_script,
                ],
                creationflags=creation_flags,
                close_fds=True,
            )

        except Exception as error:

            QMessageBox.critical(
                self.parent_window,
                "Aggiornamento",
                (
                    "Impossibile preparare "
                    "l'aggiornamento:\n\n"
                    f"{error}"
                ),
            )

            return

        QApplication.closeAllWindows()

        QTimer.singleShot(
            100,
            QApplication.quit,
        )