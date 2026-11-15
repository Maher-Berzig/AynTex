# main.py
"""
Main - Main Application Entry Point
"""
import sys
import os

# ─────────────────────────────────────────────────────────────────────────
# EARLY CRASH PROTECTION & DIAGNOSTICS  (must run before anything else)
#
# A windowed PyInstaller .exe (console=False) differs from "python main.py"
# (e.g. run from Thonny) in three ways that can make it die with Windows'
# "AynTex.exe a cessé de fonctionner" dialog and NO explanation:
#
#   1. sys.stdout / sys.stderr are None, so any library code that does
#      sys.stderr.write(...) / sys.stdout.flush() raises AttributeError.
#   2. PyQt5 aborts the WHOLE process when a Python exception escapes from
#      a Qt callback (slot, timer, event handler, paintEvent...) and no
#      sys.excepthook is installed.  An IDE such as Thonny reports such an
#      exception and carries on; the .exe just disappears.
#   3. Native crashes and Qt's own fatal messages leave no trace at all.
#
# So we (a) give stdout/stderr a real target, (b) install an excepthook that
# LOGS instead of letting PyQt abort, (c) enable faulthandler for native
# crashes and (d) route Qt messages into the same log file.
#
# Log file:  %APPDATA%\\Ayntex\\startup.log   (falls back to %TEMP%)
# ─────────────────────────────────────────────────────────────────────────
#import time
import traceback

def _open_startup_log():
    for base in (os.environ.get("APPDATA"), os.environ.get("TEMP"),
                 os.path.expanduser("~")):
        if not base:
            continue
        try:
            folder = os.path.join(base, "Ayntex")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "startup.log")
            # keep the file small: start afresh once it grows beyond 1 MB
            mode = "w" if (os.path.exists(path) and os.path.getsize(path) > 1024 * 1024) else "a"
            return open(path, mode, buffering=1, encoding="utf-8", errors="replace")
        except Exception:
            continue
    return None

_LOG = _open_startup_log()

def _log(text):
    try:
        if _LOG:
            _LOG.write(text if text.endswith("\n") else text + "\n")
    except Exception:
        pass

# try:
    # import platform as _platform
    # _log("\n=== AynTex start %s | frozen=%s | Python %s | %s ===" % (
        # time.strftime("%Y-%m-%d %H:%M:%S"), getattr(sys, "frozen", False),
        # sys.version.split()[0], _platform.platform()))
# except Exception:
    # pass

# (1) windowed exe: make sure the standard streams exist
try:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = _LOG if _LOG else open(os.devnull, "w", encoding="utf-8")
except Exception:
    pass

# (2) never let an exception inside a Qt callback abort the whole application
def _excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    _log("UNHANDLED EXCEPTION:\n" + "".join(
        traceback.format_exception(exc_type, exc_value, exc_tb)))

sys.excepthook = _excepthook

try:
    import threading
    threading.excepthook = lambda a: _excepthook(a.exc_type, a.exc_value, a.exc_traceback)
except Exception:
    pass

# (3) native crashes (access violations, ...) -> stack dump in the log
try:
    import faulthandler
    if _LOG:
        faulthandler.enable(file=_LOG, all_threads=True)
except Exception:
    pass

# (4) clean, crash-free process exit
def _fast_exit(code=0):
    """Leave the process immediately, skipping Python/Qt/MuPDF teardown.

    On the Windows 7 32-bit build the application crashed with
    "AynTex.exe a cessé de fonctionner" *after* the window had been closed and
    everything had already been saved: the faulthandler log showed an access
    violation with "<no Python frame>", i.e. inside native destructors that run
    while the interpreter shuts down (QApplication / QThreadPool / MuPDF
    document destruction, DLL unloading...).  All persistent state (config,
    session, bookmarks, zoom ...) is written in MainWindow.closeEvent, so
    nothing is lost by ending the process here.  Set AYNTEX_NO_FAST_EXIT=1
    to disable this behaviour.
    """
    if isinstance(code, bool) or code is None:
        code = int(bool(code))
    elif not isinstance(code, int):
        code = 1
    #_log("exit: leaving the process (code %s)" % code)
    try:
        from PyQt5.QtCore import QThreadPool
        QThreadPool.globalInstance().clear()      # drop queued spell-check jobs
    except Exception:
        pass
    try:
        import logging
        logging.shutdown()
    except Exception:
        pass
    for _stream in (sys.stdout, sys.stderr, _LOG):
        try:
            _stream.flush()
        except Exception:
            pass
    os._exit(code)
# ─────────────────────────────────────────────────────────────────────────

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

# Route Qt's own warnings / fatal messages (e.g. "could not load platform
# plugin", "QtWebEngineProcess not found") into the startup log.
try:
    from PyQt5.QtCore import qInstallMessageHandler
    def _qt_message_handler(mode, context, message):
        _log("[Qt] %s" % message)
    qInstallMessageHandler(_qt_message_handler)
except Exception:
    pass

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

    # Wire up "open file from second instance" if your app supports it.
    # A second launch can arrive while MainWindow() is still being built
    # (startup is slow on old PCs): remember those requests and handle them
    # as soon as the window exists instead of failing with a NameError.
    main_window = None
    _pending_args = []

    def _on_args_received(args: list):
        if main_window is None:
            _pending_args.append(args)
            return
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

    # handle launches that arrived while the window was still being created
    while _pending_args:
        _on_args_received(_pending_args.pop(0))
    
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
    try:
        main()
    except SystemExit as _exit:
        # The shutdown crash happens both in the installed .exe ("AynTex.exe a cessé
        # de fonctionner") and when running from source on Windows, e.g. from Thonny
        # ("Python a cessé de fonctionner"), so the fast exit applies to both.
        if (getattr(sys, "frozen", False) or sys.platform == "win32") \
                and not os.environ.get("AYNTEX_NO_FAST_EXIT"):
            _fast_exit(_exit.code)
        raise
    except BaseException:
        err = traceback.format_exc()
        _log("FATAL ERROR DURING STARTUP:\n" + err)
        try:
            if sys.platform == "win32":
                import ctypes
                log_hint = getattr(_LOG, "name", "")
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "AynTex could not start.\n\n" + err[-1500:] +
                    ("\n\nDetails were saved to:\n" + log_hint if log_hint else ""),
                    "AynTex", 0x10)
        except Exception:
            pass
        sys.exit(1)
