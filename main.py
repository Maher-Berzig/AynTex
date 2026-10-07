# main.py
"""
Main - Main Application Entry Point
"""
import sys
import os

# ─────────────────────────────────────────────────────────────────────────
# CRITICAL: anchor the working directory to the application's own folder.
#
# The app locates its "icons" folder (and many other assets) using paths
# that are relative to the current working directory (e.g. "icons/...").
# That only happens to work when the app is launched by double-clicking
# the .exe itself, because Windows then sets the working directory to the
# .exe's own folder.
#
# When the app is launched through a file association (e.g. double-clicking
# a .tex file whose "Open with" is set to this app), Windows instead starts
# the process with the working directory set to wherever that document
# lives (or, in some launch contexts, a system folder). That mismatch is
# what causes:
#   - a stray, empty "icons" folder appearing in random document folders
#     (IconsManager tries to create "icons" relative to the wrong cwd),
#   - toolbar/menu icons failing to load or disappearing (icons are looked
#     up relative to the wrong cwd), and
#   - the "PermissionError: [WinError 5] Access refused: 'icons'" crash on
#     Windows 10, when the wrong cwd happens to be a folder the app isn't
#     allowed to write to.
#
# Forcing the working directory back to the app's own folder, as the very
# first thing this script does, makes the app behave the same way no
# matter how it was launched.
if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built .exe: sys.executable is the real
    # on-disk location of the .exe (NOT the temporary _MEIPASS extraction
    # folder that __file__ would point to for a onefile build).
    _APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # Running from source (e.g. "python main.py").
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    os.chdir(_APP_DIR)
except OSError:
    # If we somehow can't chdir there, don't crash the app over it -
    # icons_manager.py's own guard will fall back gracefully.
    pass
# ─────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QApplication, QPushButton
from main_window import MainWindow
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt5.QtCore import  Qt, QTimer

from style_manager import apply_theme
from PyQt5.QtWidgets import QProxyStyle, QStyle, QStyleOptionMenuItem
from PyQt5.QtCore import QRect
from single_instance import ensure_single_instance
import logging

logging.basicConfig(level=logging.WARNING)

import app_info
APP_ORG = app_info.APP_ORGANIZATION
APP_NAME = app_info.APP_NAME
APP_VER = app_info.APP_VERSION
APP_AUT = app_info.APP_AUTHOR

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setApplicationVersion(APP_VER)


    #app.setWindowIcon(QIcon("icons/ayntexlogo.svg"))    
    app.setWindowIcon(QIcon("icons/ayntexlogo.ico"))
    
    # Must be called after QApplication but before showing the window
    _instance_guard = ensure_single_instance(app_info.APP_NAME)

    # Wire up "open file from second instance" if your app supports it
    def _on_args_received(args: list):
        if args and os.path.isfile(args[0]):  # `os` is imported at the top of this file
            main_window.editor_manager.open_specific_file(args[0])
        main_window.raise_()          # bring window to front
        main_window.activateWindow()

    _instance_guard.args_received.connect(_on_args_received)
    
    
    
    main_window = MainWindow()

    # After QApplication is created and config is loaded:
    saved_theme = main_window.config_manager.get_config_value('ui', 'app_theme', 'default')
    apply_theme(app, saved_theme)
    
    main_window.show()
    main_window.showMaximized()
    
    # Keep _instance_guard alive for the whole session
    app.aboutToQuit.connect(_instance_guard.close)


    if len(sys.argv) > 1:
        # Queue it — will run after the current event-loop cycle,
        # by which time mark_ui_ready() has fired.
        QTimer.singleShot(
            0,
            lambda p=sys.argv[1]: main_window.editor_manager.open_specific_file(p)
        )

    
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()
