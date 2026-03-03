#!/usr/bin/env python3
import sys
import os
import shutil
import zipfile
import subprocess
from pathlib import Path
from threading import Thread

import requests
from PySide6 import QtCore, QtWidgets, QtGui

# Integración con la barra de tareas de Windows
if sys.platform.startswith("win"):
    try:
        from PySide6.QtWinExtras import QWinTaskbarButton
    except ImportError:
        QWinTaskbarButton = None
else:
    QWinTaskbarButton = None

# ---------------- CONFIG ------------------

LAUNCHER_VERSION = "1.0.4"

# Windows build is split into two parts
BUILD_URL_WIN_PART1 = "https://github.com/acierto-incomodo/miside-zero/releases/latest/download/Build.zip"
BUILD_URL_LINUX = "https://github.com/acierto-incomodo/miside-zero/releases/latest/download/Build.zip"
VERSION_URL = "https://github.com/acierto-incomodo/miside-zero/releases/latest/download/version.txt"
RELEASE_NOTES_URL = "https://github.com/acierto-incomodo/miside-zero/releases/latest/download/ReleaseNotes.txt"
ALPHA_CONTENT_URL_ZIP = "https://github.com/acierto-incomodo/miside-zero/releases/latest/download/AlphaContent.zip"
ALPHA_CONTENT_URL_VERSION = "https://github.com/acierto-incomodo/miside-zero/releases/latest/download/versionAlphaContent.txt"

EXE_NAME_WIN   = "Build/MiSide Zero.exe"
EXE_NAME_LINUX = "Build/MiSide Zero.exe"

DOWNLOAD_DIR = Path.cwd() / "downloads"
GAME_DIR     = Path.cwd() / "game"
VERSION_FILE = GAME_DIR / "version.txt"
BUILD_DIR    = GAME_DIR / "Build"
ALPHA_CONTENT_DIR = GAME_DIR / "AlphaContent"
ALPHA_CONTENT_VERSION_FILE = GAME_DIR / "versionAlphaContent.txt"
ALPHA_SETTING_FILE = Path.cwd() / "AlphaContent.txt"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
GAME_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- Utils -------------------

def download_file(url: str, dest: Path, progress_callback=None, chunk_size=8192):
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    total = resp.headers.get("content-length")
    total = int(total) if total and total.isdigit() else None

    with open(dest, "wb") as f:
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)
            if progress_callback:
                progress_callback(downloaded, total)

    return dest


def extract_zip(zip_path: Path, to_dir: Path, clear: bool = True):
    if clear and to_dir.exists():
        shutil.rmtree(to_dir)
    to_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(path=to_dir)


def start_game_process():
    if sys.platform.startswith("win"):
        exe = BUILD_DIR / EXE_NAME_WIN
    else:
        exe = BUILD_DIR / EXE_NAME_LINUX

    if not exe.exists():
        raise FileNotFoundError(f"Ejecutable no encontrado:\n{exe}")

    if not sys.platform.startswith("win"):
        exe.chmod(0o755)

    if sys.platform.startswith("win"):
        os.startfile(str(exe))
    else:
        subprocess.Popen([str(exe)], cwd=str(exe.parent))

# --------------- GUI ----------------------

class LauncherWindow(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiSide Zero - Launcher")
        self.setMinimumSize(520, 420)
        self.setMaximumSize(520, 420)
        self.setWindowIcon(QtGui.QIcon.fromTheme("applications-games"))

        self.taskbar_button = None
        self.taskbar_progress = None

        self.setup_ui()
        self.load_extra_content_setting()
        self.refresh_version_display()
        self.load_release_notes()
        self.update_extra_content_ui()

        self.on_check()

    def showEvent(self, event):
        # Este método se llama cuando el widget se muestra.
        # Es un buen lugar para inicializar cosas que dependen de un "handle" de ventana.
        super().showEvent(event)
        if sys.platform.startswith("win") and QWinTaskbarButton and not self.taskbar_button:
            # Inicializar la integración con la barra de tareas una vez que la ventana se muestra
            self.taskbar_button = QWinTaskbarButton(self)
            self.taskbar_button.setWindow(self.windowHandle())
            self.taskbar_progress = self.taskbar_button.progress()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("MiSide Zero")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:bold;")
        layout.addWidget(title)

        self.status = QtWidgets.QLabel("Listo.")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status)

        # botones principales
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_check  = QtWidgets.QPushButton("Buscar actualización")
        self.btn_update = QtWidgets.QPushButton("Actualizar")
        self.btn_start  = QtWidgets.QPushButton("Iniciar juego")

        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_start)

        layout.addLayout(btn_layout)

        # ------------ NUEVOS BOTONES -------------
        tools_layout = QtWidgets.QHBoxLayout()

        self.btn_open_folder = QtWidgets.QPushButton("Abrir ubicación")
        self.btn_delete_data = QtWidgets.QPushButton("Eliminar datos")

        tools_layout.addWidget(self.btn_open_folder)
        tools_layout.addWidget(self.btn_delete_data)

        layout.addLayout(tools_layout)

        # ------------ CONTENIDO EXTRA -------------
        extra_layout = QtWidgets.QHBoxLayout()
        self.cb_extra_content = QtWidgets.QCheckBox("Contenido Extra")
        self.btn_open_extra = QtWidgets.QPushButton("Abrir Contenido Extra")
        self.btn_delete_extra = QtWidgets.QPushButton("Eliminar Contenido Extra")

        extra_layout.addWidget(self.cb_extra_content)
        extra_layout.addStretch()
        extra_layout.addWidget(self.btn_open_extra)
        extra_layout.addWidget(self.btn_delete_extra)

        layout.addLayout(extra_layout)

        # ------------------------------------------

        # barra de progreso
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()
        
        
        # ----- Release notes -----
        self.release_notes_box = QtWidgets.QTextEdit()
        self.release_notes_box.setReadOnly(True)
        self.release_notes_box.setMinimumHeight(100)
        self.release_notes_box.setStyleSheet(
            "padding:6px; font-size:13px;"
        )
        layout.addWidget(self.release_notes_box)


        # versión al fondo
        self.version_display = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.version_display.setStyleSheet("font-weight:bold; font-size:14px; margin-bottom:8px;")
        layout.addWidget(self.version_display)
        # version_layout = QtWidgets.QHBoxLayout()
        
        # self.version_display = QtWidgets.Qlabel("", alignment=QtCore.Qt.AlingCenter)
        # self.version_display.setStyleSheet("font-weight:bold; font-size:14px;")
        
        # self.launcher_version_label = QtWidgets.QLabel(f"Launcher v{LAUNCHER_VERSION}")
        # self.launcher_version_label.setStyleSheet("font-size:14px; color: gray; margin-left:10px;")
        
        # version_layout.addStretch()
        # version_layout.addWidget(self.version_display)
        # version_layout.addWidget(self.launcher_version_label)
        # version_layout.addStretch()
        
        # layout.addLayout(version_layout)

        # señales
        self.btn_check.clicked.connect(self.on_check)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_start.clicked.connect(self.on_start)

        # nuevas señales
        self.btn_open_folder.clicked.connect(self.open_location)
        self.btn_delete_data.clicked.connect(self.delete_data)

        # señales de contenido extra
        self.btn_open_extra.clicked.connect(self.open_extra_location)
        self.btn_delete_extra.clicked.connect(self.delete_extra_data)
        self.cb_extra_content.toggled.connect(self.on_extra_content_toggled)

        self.btn_update.setEnabled(False)

    def set_status(self, text):
        self.status.setText(text)

    def refresh_version_display(self):
        if VERSION_FILE.exists():
            try:
                content = VERSION_FILE.read_text(encoding="utf-8").strip()
                self.version_display.setText(content or "Necesitas descargar el juego")
            except:
                self.version_display.setText("Necesitas descargar el juego")
        else:
            self.version_display.setText("Necesitas descargar el juego")

    # ------------ NUEVA FUNCIÓN: ABRIR UBICACIÓN ------------

    def open_location(self):
        folder = str(Path.cwd())
        if sys.platform.startswith("win"):
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    # ------------ NUEVA FUNCIÓN: ELIMINAR DATOS ------------

    def delete_data(self):
        try:
            if DOWNLOAD_DIR.exists():
                shutil.rmtree(DOWNLOAD_DIR)
            if GAME_DIR.exists():
                shutil.rmtree(GAME_DIR)

            DOWNLOAD_DIR.mkdir(exist_ok=True)
            GAME_DIR.mkdir(exist_ok=True)

            self.refresh_version_display()
            self.set_status("Carpetas eliminadas.")

        except Exception as e:
            self.set_status(f"Error: {e}")

    # ------------ GESTIÓN CONTENIDO EXTRA ------------

    def update_extra_content_ui(self):
        has_extra_content = ALPHA_CONTENT_DIR.exists() and ALPHA_CONTENT_VERSION_FILE.exists()
        self.btn_open_extra.setVisible(has_extra_content)
        self.btn_delete_extra.setVisible(has_extra_content)

    def open_extra_location(self):
        folder = str(ALPHA_CONTENT_DIR)
        if not ALPHA_CONTENT_DIR.exists():
            self.set_status("La carpeta de contenido extra no existe.")
            return
        if sys.platform.startswith("win"):
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    def delete_extra_data(self, prompt=True):
        if prompt:
            reply = QtWidgets.QMessageBox.question(self, 'Confirmar',
                                                   "¿Seguro que quieres eliminar el contenido extra? Esta acción no se puede deshacer.",
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No:
                return
        
        # Si se está eliminando, el checkbox debe reflejarlo
        if self.cb_extra_content.isChecked():
            self.cb_extra_content.setChecked(False)

        try:
            if ALPHA_CONTENT_DIR.exists():
                shutil.rmtree(ALPHA_CONTENT_DIR)
            if ALPHA_CONTENT_VERSION_FILE.exists():
                ALPHA_CONTENT_VERSION_FILE.unlink()
            self.set_status("Contenido extra eliminado.")
            self.update_extra_content_ui()
        except Exception as e:
            self.set_status(f"Error al eliminar: {e}")

    def load_extra_content_setting(self):
        if not ALPHA_SETTING_FILE.exists():
            ALPHA_SETTING_FILE.write_text("no")
        
        try:
            should_be_enabled = ALPHA_SETTING_FILE.read_text(encoding="utf-8").strip().lower() == "si"
            self.cb_extra_content.setChecked(should_be_enabled)
        except Exception as e:
            print(f"No se pudo leer la configuración de contenido extra: {e}")
            self.cb_extra_content.setChecked(False)

    @QtCore.Slot(bool)
    def on_extra_content_toggled(self, checked):
        try:
            state_to_save = "si" if checked else "no"
            ALPHA_SETTING_FILE.write_text(state_to_save, encoding="utf-8")
        except Exception as e:
            self.set_status(f"No se pudo guardar la configuración: {e}")
            return
        
        if checked:
            self.on_update_alpha_content()
        else:
            # Eliminar el contenido extra sin preguntar
            self.delete_extra_data(prompt=False)

    def on_update_alpha_content(self):
        self.cb_extra_content.setEnabled(False)
        self.btn_delete_extra.setEnabled(False)
        self.btn_check.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_delete_data.setEnabled(False)

        self.progress.setVisible(True)
        self.progress.setValue(0)
        if self.taskbar_progress:
            self.taskbar_progress.setVisible(True)
            self.taskbar_progress.setRange(0, 100)
            self.taskbar_progress.setValue(0)

        self.set_status("Comprobando contenido extra...")
        Thread(target=self._update_alpha_thread, daemon=True).start()

    def _update_alpha_thread(self):
        try:
            try:
                remote_version = requests.get(ALPHA_CONTENT_URL_VERSION, timeout=30).text.strip()
            except Exception as e:
                raise Exception(f"No se pudo obtener la versión remota del contenido extra: {e}")

            local_version = None
            if ALPHA_CONTENT_VERSION_FILE.exists():
                local_version = ALPHA_CONTENT_VERSION_FILE.read_text(encoding="utf-8").strip()

            if local_version == remote_version and ALPHA_CONTENT_DIR.exists():
                self.set_status("El contenido extra ya está actualizado.")
                QtCore.QMetaObject.invokeMethod(self, "on_alpha_update_done", QtCore.Qt.QueuedConnection)
                return

            self.set_status("Descargando Contenido Extra...")
            zip_path = DOWNLOAD_DIR / "AlphaContent.zip"
            download_file(ALPHA_CONTENT_URL_ZIP, zip_path, self._progress_callback)

            self.set_status("Extrayendo Contenido Extra...")
            if self.taskbar_progress:
                QtCore.QMetaObject.invokeMethod(self.taskbar_progress, "setRange", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, 0), QtCore.Q_ARG(int, 0))

            extract_zip(zip_path, ALPHA_CONTENT_DIR, clear=True)
            zip_path.unlink()

            if self.taskbar_progress:
                QtCore.QMetaObject.invokeMethod(self.taskbar_progress, "setRange", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, 0), QtCore.Q_ARG(int, 100))

            ALPHA_CONTENT_VERSION_FILE.write_text(remote_version, encoding="utf-8")
            
            self.set_status("Contenido extra instalado/actualizado.")
            QtCore.QMetaObject.invokeMethod(self, "on_alpha_update_done", QtCore.Qt.QueuedConnection)

        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self, "on_alpha_update_error", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, str(e)))

    # ------------ CHECK ----------

    def on_check(self):
        self.set_status("Comprobando versión remota...")
        self.btn_check.setEnabled(False)
        Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        try:
            resp = requests.get(VERSION_URL, timeout=30)
            resp.raise_for_status()
            latest = resp.text.strip()
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self, "on_check_failed",
                                            QtCore.Qt.QueuedConnection,
                                            QtCore.Q_ARG(str, str(e)))
            return

        local = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0"
        update_available = (local != latest)

        QtCore.QMetaObject.invokeMethod(
            self, "on_check_done", QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(bool, update_available),
            QtCore.Q_ARG(str, latest)
        )

    @QtCore.Slot(bool, str)
    def on_check_done(self, update_available, latest):
        self.btn_check.setEnabled(True)  # opcional: ocultar botones
        self.btn_update.setEnabled(True)
        
        if update_available or not self.game_installed():
            self.set_status(f"Nueva versión disponible: {latest}. Actualizando automáticamente...")
            self.on_update()  # llama directamente al update
        else:
            self.set_status("Tu juego está actualizado.")

    @QtCore.Slot(str)
    def on_check_failed(self, err):
        self.btn_check.setEnabled(True)
        self.set_status(f"Error: {err}")

    # ------------ UPDATE ----------

    def on_update(self):
        # Deshabilitar botones mientras se actualiza
        self.btn_check.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_delete_data.setEnabled(False)
        self.cb_extra_content.setEnabled(False)

        if self.taskbar_progress:
            self.taskbar_progress.setVisible(True)
            self.taskbar_progress.setRange(0, 100)
            self.taskbar_progress.setValue(0)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.set_status("Descargando versión...")
        download_extra = self.cb_extra_content.isChecked()
        Thread(target=self._update_thread, args=(download_extra,), daemon=True).start()

    def _progress_callback(self, downloaded, total):
        percent = int(downloaded * 100 / total) if total else 0
        QtCore.QMetaObject.invokeMethod(
            self.progress, "setValue",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(int, percent)
        )
        if self.taskbar_progress:
            QtCore.QMetaObject.invokeMethod(
                self.taskbar_progress, "setValue",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(int, percent)
            )

    def _update_thread(self, download_extra: bool):
        try:
            if sys.platform.startswith("win"):
                downloads = [
                    (BUILD_URL_WIN_PART1, "Build.zip"),
                ]
            else:
                downloads = [
                    (BUILD_URL_LINUX, "BuildLinux.zip"),
                ]

            for idx, (url, zip_name) in enumerate(downloads):
                zip_path = DOWNLOAD_DIR / zip_name
                self.set_status(f"Descargando {zip_name}...")
                download_file(url, zip_path, self._progress_callback)

                self.set_status(f"Extrayendo {zip_name}...")
                # Poner la barra de tareas en modo "cargando" (indeterminado)
                if self.taskbar_progress:
                    QtCore.QMetaObject.invokeMethod(self.taskbar_progress, "setRange", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, 0), QtCore.Q_ARG(int, 0))

                # clear BUILD_DIR on first part, keep files on subsequent parts
                extract_zip(zip_path, BUILD_DIR, clear=(idx == 0))

                # Volver al modo normal para la siguiente descarga
                if self.taskbar_progress:
                    QtCore.QMetaObject.invokeMethod(self.taskbar_progress, "setRange", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, 0), QtCore.Q_ARG(int, 100))

                # eliminar archivo zip descargado
                try:
                    zip_path.unlink()
                except Exception:
                    pass

            # --- Descargar contenido extra si está marcado ---
            if download_extra:
                self.set_status("Descargando Contenido Extra...")
                zip_path = DOWNLOAD_DIR / "AlphaContent.zip"
                download_file(ALPHA_CONTENT_URL_ZIP, zip_path, self._progress_callback)

                self.set_status("Extrayendo Contenido Extra...")
                # Poner la barra de tareas en modo "cargando" (indeterminado)
                if self.taskbar_progress:
                    QtCore.QMetaObject.invokeMethod(self.taskbar_progress, "setRange", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, 0), QtCore.Q_ARG(int, 0))

                extract_zip(zip_path, ALPHA_CONTENT_DIR, clear=True)
                zip_path.unlink()

                # Volver al modo normal
                if self.taskbar_progress:
                    QtCore.QMetaObject.invokeMethod(self.taskbar_progress, "setRange", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, 0), QtCore.Q_ARG(int, 100))

                self.set_status("Descargando versionAlphaContent.txt...")
                version_alpha = requests.get(ALPHA_CONTENT_URL_VERSION, timeout=30).text.strip()
                ALPHA_CONTENT_VERSION_FILE.write_text(version_alpha, encoding="utf-8")

            self.set_status("Descargando version.txt...")
            version = requests.get(VERSION_URL, timeout=30).text.strip()
            VERSION_FILE.write_text(version, encoding="utf-8")

            # Eliminar archivos descargados en DOWNLOAD_DIR al terminar la actualización
            try:
                for p in DOWNLOAD_DIR.iterdir():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
            except Exception:
                pass

            QtCore.QMetaObject.invokeMethod(
                self, "on_update_done",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, version)
            )

        except Exception as e:
            QtCore.QMetaObject.invokeMethod(
                self, "on_update_error",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, str(e))
            )

    @QtCore.Slot(str)
    def on_update_done(self, version):
        if self.taskbar_progress:
            self.taskbar_progress.setVisible(False)
        self.progress.setVisible(False)
        self.set_status("Instalación completada." if not self.game_installed() else "Actualización completada.")
        
        # Habilitar botones nuevamente
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_delete_data.setEnabled(True)
        self.cb_extra_content.setEnabled(True)
        
        self.refresh_version_display()
        self.load_release_notes()
        self.update_extra_content_ui()


    @QtCore.Slot(str)
    def on_update_error(self, err):
        if self.taskbar_progress:
            self.taskbar_progress.setVisible(False)
        self.progress.setVisible(False)
        self.set_status(f"Error: {err}")
        
        # Habilitar botones nuevamente
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_delete_data.setEnabled(True)
        self.cb_extra_content.setEnabled(True)

    @QtCore.Slot()
    def on_alpha_update_done(self):
        if self.taskbar_progress:
            self.taskbar_progress.setVisible(False)
        self.progress.setVisible(False)

        self.cb_extra_content.setEnabled(True)
        self.btn_delete_extra.setEnabled(True)
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_delete_data.setEnabled(True)

        self.update_extra_content_ui()

    @QtCore.Slot(str)
    def on_alpha_update_error(self, err):
        if self.taskbar_progress:
            self.taskbar_progress.setVisible(False)
        self.progress.setVisible(False)
        self.set_status(f"Error Contenido Extra: {err}")

        # Re-enable everything
        self.cb_extra_content.setEnabled(True)
        self.btn_delete_extra.setEnabled(True)
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_delete_data.setEnabled(True)

    # ------------ START ----------

    def on_start(self):
        try:
            start_game_process()
            # Cerrar el launcher
            QtWidgets.QApplication.quit()
        except Exception as e:
            self.set_status(f"Error al iniciar: {e}")
            
    # --------- GAME INSTALLED CHECK -----------
    
    def game_installed(self):
        return VERSION_FILE.exists() and BUILD_DIR.exists()
    
    # ------------ LOAD RELEASE NOTES ------------
    
    def load_release_notes(self):
        try:
            resp = requests.get(RELEASE_NOTES_URL, timeout=20)
            resp.raise_for_status()
            notes = resp.text.strip()
        except:
            notes = "No hay notas de la versión disponibles."

        self.release_notes_box.setText(notes)



# --------------- MAIN ---------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = LauncherWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
