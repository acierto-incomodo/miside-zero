./Clear.ps1
cp main.py launcher_win.py
python -m PyInstaller --onefile --windowed --noconsole --icon=miside-zero.ico launcher_win.py
echo v1.0.4 > version_win_launcher.txt
python -m PyInstaller --onefile --windowed --noconsole --icon=miside-zero.ico installer_updater.py