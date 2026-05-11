"""
errors_manager.py – Robust crash logging + freeze detection for PyQt5

Key design decisions
--------------------
* No automatic popups.  All errors and freezes are silently logged; the user
  opens the viewer on demand via Help → View Error Log (or any menu action
  connected to ErrorsManager.open_log_viewer).
* Uses logging.RotatingFileHandler – buffered, size-capped, with automatic
  backup rotation.
* time.monotonic() is used throughout so system-clock adjustments don't
  produce false positives.
* stderr is buffered per-line to avoid one logger call per character.
* KeyboardInterrupt is left alone in the exception hook.
* Log file is truncated once at startup; old content rolls into .log.1 etc.
* has_errors() returns True if any WARNING/ERROR/CRITICAL was logged this
  session – handy for adding a ⚠ badge to the menu item.

Typical usage
-------------
    # In your MainWindow.__init__, after QApplication is created:
    ErrorsManager.setup(
        app_name="Ayntex",
        enable_freeze_detection=True,
        freeze_timeout=120.0,
    )

    # Build the Help menu:
    help_menu = menubar.addMenu("Help")
    log_action = QAction("View Error Log", self)
    log_action.triggered.connect(lambda: ErrorsManager.open_log_viewer(parent=self))
    help_menu.addAction(log_action)

    # Optional: refresh the label when the menu is about to show, so the ⚠
    # badge appears as soon as something goes wrong:
    help_menu.aboutToShow.connect(lambda: log_action.setText(
        "View Error Log  ⚠" if ErrorsManager.has_errors() else "View Error Log"
    ))
"""

import os
import sys
import builtins
import traceback as tb
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


# ---------------------------------------------------------------------------
# ErrorsManager
# ---------------------------------------------------------------------------

class ErrorsManager:
    # ── class-level state ────────────────────────────────────────────────────
    _instance:              Optional["ErrorsManager"] = None
    _log_path:              Optional[str]             = None
    _logger:                Optional[logging.Logger]  = None

    _original_print                                   = None
    _original_excepthook                              = None
    _original_stderr                                  = None

    _main_thread_id:        Optional[int]             = None

    # True the first time a WARNING or above is logged this session
    _has_errors:            bool                      = False

    # freeze detection
    _freeze_running:        bool                      = False
    _freeze_detected_flag:  bool                      = False
    _freeze_timeout:        float                     = 120.0
    _last_heartbeat:        Optional[float]           = None   # monotonic

    _heartbeat_timer:       Optional[QTimer]          = None
    _freeze_thread:         Optional[threading.Thread] = None

    # ── public API ───────────────────────────────────────────────────────────

    @classmethod
    def setup(
        cls,
        app_name:                str   = "Ayntex",
        redirect_stderr:         bool  = True,
        enable_freeze_detection: bool  = False,
        freeze_timeout:          float = 120.0,
        max_log_bytes:           int   = 2 * 1024 * 1024,  # 2 MB per file
        backup_count:            int   = 3,                 # keep .log.1–.3
    ) -> None:
        """
        Call once – ideally right after QApplication is created.
        Safe to call multiple times (subsequent calls are no-ops).
        """
        if cls._instance is not None:
            return

        cls._instance       = cls()
        cls._main_thread_id = threading.current_thread().ident
        cls._freeze_timeout = freeze_timeout

        log_path = cls._init_log_path(app_name)
        cls._setup_logger(log_path, max_log_bytes, backup_count)
        cls._patch_print()
        cls._install_excepthook()

        if redirect_stderr:
            cls._redirect_stderr()

        if enable_freeze_detection:
            cls.start_freeze_detection()

    @classmethod
    def open_log_viewer(cls, parent=None) -> None:
        """
        Open the log viewer dialog on demand.
        Connect this to your Help menu action:

            log_action.triggered.connect(
                lambda: ErrorsManager.open_log_viewer(parent=self)
            )
        """
        if not QApplication.instance():
            return
        LogViewer(cls, parent).exec_()

    @classmethod
    def has_errors(cls) -> bool:
        """
        Returns True if at least one WARNING, ERROR, or CRITICAL was logged
        this session.  Use this to show a visual hint on the menu item:

            help_menu.aboutToShow.connect(lambda: log_action.setText(
                "View Error Log  ⚠" if ErrorsManager.has_errors() else "View Error Log"
            ))
        """
        return cls._has_errors

    @classmethod
    def stop_freeze_detection(cls) -> None:
        """Cleanly shut down the watchdog (call before QApplication exits)."""
        cls._freeze_running = False
        if cls._heartbeat_timer:
            cls._heartbeat_timer.stop()
        if cls._freeze_thread:
            cls._freeze_thread.join(timeout=2.0)

    @classmethod
    def get_log_content(cls) -> str:
        try:
            with open(cls.get_log_path(), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "No log file found yet."
        except Exception as exc:
            return f"Could not read log file:\n{exc}"

    @classmethod
    def get_log_path(cls, app_name: str = "Ayntex") -> str:
        if cls._log_path is None:
            cls._log_path = cls._init_log_path(app_name)
        return cls._log_path

    # ── internal: paths ──────────────────────────────────────────────────────

    @classmethod
    def _get_config_dir(cls, app_name: str) -> str:
        plat = sys.platform.lower()
        if plat.startswith("win"):
            base = os.environ.get("APPDATA") or os.path.join(
                os.path.expanduser("~"), "AppData", "Roaming"
            )
        elif plat.startswith("darwin"):
            base = os.path.join(
                os.path.expanduser("~"), "Library", "Application Support"
            )
        else:
            base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
                os.path.expanduser("~"), ".config"
            )
        config_dir = os.path.join(base, app_name)
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    @classmethod
    def _init_log_path(cls, app_name: str = "Ayntex") -> str:
        if cls._log_path is None:
            cls._log_path = os.path.join(
                cls._get_config_dir(app_name), "errors.log"
            )
        return cls._log_path

    # ── internal: logger ─────────────────────────────────────────────────────

    @classmethod
    def _setup_logger(cls, log_path: str, max_bytes: int, backup_count: int) -> None:
        # Truncate at startup; RotatingFileHandler takes over from here.
        try:
            with open(log_path, "w", encoding="utf-8"):
                pass
        except OSError:
            pass

        cls._logger = logging.getLogger("ErrorsManager")
        cls._logger.setLevel(logging.DEBUG)
        cls._logger.propagate = False

        handler = RotatingFileHandler(
            log_path,
            mode="a",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
            delay=False,
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-8s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        cls._logger.addHandler(handler)
        cls._logger.info("=== Session started (pid %d) ===", os.getpid())

    @classmethod
    def _log(cls, msg: str, level: int = logging.DEBUG) -> None:
        if cls._logger:
            cls._logger.log(level, msg)
            if level >= logging.WARNING:
                cls._has_errors = True

    # ── internal: print patch ────────────────────────────────────────────────

    @classmethod
    def _patch_print(cls) -> None:
        cls._original_print = builtins.print

        def _custom_print(*args, sep: str = " ", end: str = "\n",
                          file=None, flush: bool = False) -> None:
            cls._original_print(*args, sep=sep, end=end, file=file, flush=flush)
            if file is None:   # only intercept stdout prints
                try:
                    cls._log(sep.join(str(a) for a in args))
                except Exception:
                    pass

        builtins.print = _custom_print

    # ── internal: stderr redirect ─────────────────────────────────────────────

    @classmethod
    def _redirect_stderr(cls) -> None:
        cls._original_stderr = sys.stderr
        logger = cls._logger

        class _TeeStderr:
            """Mirrors stderr to the logger, one log entry per line."""
            def __init__(self, original):
                self._orig = original
                self._buf  = ""

            def write(self, msg: str) -> None:
                self._orig.write(msg)
                self._buf += msg
                if "\n" in self._buf:
                    lines = self._buf.split("\n")
                    for line in lines[:-1]:
                        stripped = line.rstrip()
                        if stripped and logger:
                            logger.error(stripped)
                            cls._has_errors = True
                    self._buf = lines[-1]

            def flush(self) -> None:
                if self._buf.strip() and logger:
                    logger.error(self._buf.rstrip())
                    cls._has_errors = True
                    self._buf = ""
                self._orig.flush()

            def __getattr__(self, name):
                return getattr(self._orig, name)

        sys.stderr = _TeeStderr(cls._original_stderr)

    # ── internal: exception hook ──────────────────────────────────────────────

    @classmethod
    def _install_excepthook(cls) -> None:
        cls._original_excepthook = sys.excepthook

        def _hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return

            error_text = "".join(tb.format_exception(exc_type, exc_value, exc_tb))
            cls._logger.critical("UNHANDLED EXCEPTION\n%s", error_text)
            cls._has_errors = True

            # Propagate to the original hook (may terminate the process)
            if cls._original_excepthook:
                cls._original_excepthook(exc_type, exc_value, exc_tb)

        sys.excepthook = _hook

    # ── internal: freeze detection ────────────────────────────────────────────

    @classmethod
    def start_freeze_detection(cls) -> None:
        """
        Architecture
        ────────────
        • A QTimer (_heartbeat_timer) ticks every 500 ms in the main thread,
          updating _last_heartbeat (monotonic clock).
        • A daemon watchdog thread checks the heartbeat every second.
          When the heartbeat is stale by more than freeze_timeout seconds it
          writes the main-thread stack trace to the log and sets _has_errors
          so the menu badge appears as soon as the UI recovers.
          The watchdog thread never touches Qt objects.
        """
        if cls._freeze_thread is not None and cls._freeze_thread.is_alive():
            return

        if not QApplication.instance():
            raise RuntimeError(
                "QApplication must be created before start_freeze_detection()."
            )

        cls._last_heartbeat       = time.monotonic()
        cls._freeze_running       = True
        cls._freeze_detected_flag = False

        cls._heartbeat_timer = QTimer()
        cls._heartbeat_timer.setTimerType(Qt.CoarseTimer)
        cls._heartbeat_timer.timeout.connect(cls._update_heartbeat)
        cls._heartbeat_timer.start(500)

        cls._freeze_thread = threading.Thread(
            target=cls._watchdog_loop,
            daemon=True,
            name="FreezeWatchdog",
        )
        cls._freeze_thread.start()

    @classmethod
    def _update_heartbeat(cls) -> None:
        cls._last_heartbeat = time.monotonic()

    @classmethod
    def _watchdog_loop(cls) -> None:
        """Runs in a daemon thread; never touches Qt objects."""
        while cls._freeze_running:
            time.sleep(1.0)
            if cls._last_heartbeat is None:
                continue
            elapsed = time.monotonic() - cls._last_heartbeat
            if elapsed > cls._freeze_timeout and not cls._freeze_detected_flag:
                cls._freeze_detected_flag = True
                cls._log_freeze_snapshot()

    @classmethod
    def _log_freeze_snapshot(cls) -> None:
        """Thread-safe: writes the freeze report via the logger (no Qt)."""
        frames     = sys._current_frames()
        main_frame = frames.get(cls._main_thread_id)
        stack_text = (
            "".join(tb.format_stack(main_frame))
            if main_frame
            else "(main-thread frame unavailable)"
        )
        cls._logger.critical(
            "UI FREEZE DETECTED (unresponsive for > %.0f s)\n"
            "Main-thread stack at time of freeze:\n%s",
            cls._freeze_timeout,
            stack_text,
        )
        cls._has_errors = True


# ---------------------------------------------------------------------------
# LogViewer dialog
# ---------------------------------------------------------------------------

class LogViewer(QDialog):
    def __init__(self, manager_class, parent=None):
        super().__init__(parent)
        self.manager_class = manager_class

        self.setWindowTitle("Ayntex – Error Log")
        self.resize(750, 500)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── log text area ──
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(9)
        self._text_edit.setFont(mono)
        self._text_edit.setPlainText(self.manager_class.get_log_content())
        self._scroll_to_bottom()
        layout.addWidget(self._text_edit)

        # ── button row ──
        btn_layout = QHBoxLayout()
        for label, slot in (
            ("Refresh",         self._refresh_log),
            ("Copy Log",        self._copy_log),
            ("Open Log Folder", self._open_log_folder),
            ("Close",           self.accept),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _refresh_log(self) -> None:
        pos = self._text_edit.verticalScrollBar().value()
        self._text_edit.setPlainText(self.manager_class.get_log_content())
        self._text_edit.verticalScrollBar().setValue(pos)

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self._text_edit.toPlainText())
        QMessageBox.information(self, "Copied", "Log content copied to clipboard.")

    def _open_log_folder(self) -> None:
        folder = os.path.dirname(self.manager_class.get_log_path())
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)                     # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not open folder:\n{exc}")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _scroll_to_bottom(self) -> None:
        sb = self._text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())