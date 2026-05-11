# file_watcher.py
"""
File Watcher - Detects external modifications to open editor files.

Integrates with EditorManager via QFileSystemWatcher.
When a watched file changes on disk, the user is prompted to
reload (accept) or keep their in-editor version (ignore).
"""

import os
from PyQt5.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox


class FileWatcher(QObject):
    """
    Watches all files currently open in the editor and notifies
    the user when an external change is detected.

    Usage
    -----
    In EditorManager.__init__:
        self.file_watcher = FileWatcher(self)

    Then call:
        self.file_watcher.watch(path)      # when a file is opened
        self.file_watcher.unwatch(path)    # when a file is closed
        self.file_watcher.pause(path)      # before saving (avoid self-trigger)
        self.file_watcher.resume(path)     # after saving
        self.file_watcher.unwatch_all()    # on close all / app exit
    """

    # Emitted when the user chooses to reload a file
    file_reloaded = pyqtSignal(str)

    def __init__(self, editor_manager):
        super().__init__()
        self._em = editor_manager
        self._mw = editor_manager.main_window

        # Qt filesystem watcher (uses inotify on Linux, FSEvents on macOS,
        # ReadDirectoryChangesW on Windows)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)

        # Paths currently suppressed (we just saved them ourselves)
        self._suppressed: set = set()

        # Paths for which a dialog is already open (avoid duplicates)
        self._dialog_open: set = set()

        # Debounce timers keyed by path.
        # Some editors write files in two steps (truncate then write);
        # we wait 350 ms before prompting to collapse those into one event.
        self._pending: dict = {}
        self._pending_changes = set()
        self._poll_paths = set()
        self._mtimes = {}
        self._last_prompt_time = {}
        
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_files)
        self._poll_timer.start(1000)  

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # def watch(self, path: str):
        # """Start watching *path*. Watches any file open in the editor."""
        # if path and os.path.isfile(path):
            # self._watcher.addPath(path)
            
    def watch(self, path: str):
        if path and os.path.isfile(path):
            self._watcher.addPath(path)
            
            # 🔥 Only poll non-tex files
            if not path.lower().endswith(".tex"):
                self._poll_paths.add(path)
                self._mtimes[path] = os.path.getmtime(path)

    def unwatch(self, path: str):
        """Stop watching *path*."""
        if path:
            self._watcher.removePath(path)
            self._cancel_pending(path)
            self._suppressed.discard(path)
            self._dialog_open.discard(path)
            
            self._poll_paths.discard(path)
            self._mtimes.pop(path, None)

    def watch_all(self):
        """Watch every file currently open in the editor manager."""
        for path in self._em.editor_files:
            self.watch(path)

    def pause(self, path: str):
        """
        Suppress the next change notification for *path*.
        Call this immediately before writing the file yourself.
        """
        self._suppressed.add(os.path.normcase(os.path.abspath(path)))

    def resume(self, path: str):
        """
        Re-arm watching after a self-save.
        QFileSystemWatcher sometimes drops the watch after an atomic
        file replace, so we re-add the path here.
        """
        self._suppressed.discard(os.path.normcase(os.path.abspath(path)))
        if path and os.path.isfile(path):
            if path not in self._watcher.files():
                self._watcher.addPath(path)

    def unwatch_all(self):
        """Remove all watches (call on close-all / application exit)."""
        files = list(self._watcher.files())
        if files:
            self._watcher.removePaths(files)
        for path in list(self._pending):
            self._cancel_pending(path)
        self._suppressed.clear()
        self._dialog_open.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    # def _poll_files(self):
        # for path in list(self._em.editor_files):
            # if not os.path.isfile(path):
                # continue

            # try:
                # mtime = os.path.getmtime(path)
            # except OSError:
                # continue

            # if path not in self._mtimes:
                # self._mtimes[path] = mtime
                # continue

            # if mtime != self._mtimes[path]:
                # self._mtimes[path] = mtime

                # print("POLL DETECTED:", path)

                # self._on_file_changed(path)

    def _poll_files(self):
        for path in list(self._poll_paths):
            if not os.path.isfile(path):
                continue

            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue

            if path not in self._mtimes:
                self._mtimes[path] = mtime
                continue

            if mtime != self._mtimes[path]:
                self._mtimes[path] = mtime

                #print("POLL DETECTED:", path)

                self._on_file_changed(path)


    # def set_compilation_active(self, active: bool):
        # """Suppress all reload prompts while LaTeX is compiling."""
        # self._compiling = active
        # if not active:
            # # Discard any events that queued up during compilation
            # for path in list(self._pending):
                # self._cancel_pending(path)

    def set_compilation_active(self, active: bool):
        """Suppress all reload prompts while LaTeX is compiling.
        When deactivating, keeps suppression for a short grace period to
        absorb late-arriving OS notifications for files LaTeX just rewrote
        (e.g. the .log file if it is open in the editor)."""
        if active:
            self._compiling = True
            # Cancel any timers that were pending before compilation started
            for path in list(self._pending):
                self._cancel_pending(path)
        else:
            # Cancel timers queued during compilation
            for path in list(self._pending):
                self._cancel_pending(path)

            # Keep suppression alive for 1.5 s so that late OS notifications
            # (from _rearm callbacks firing after the process exits) are ignored.
            if not hasattr(self, '_grace_timer'):
                self._grace_timer = QTimer(self)
                self._grace_timer.setSingleShot(True)
                self._grace_timer.timeout.connect(self._end_grace_period)

            self._compiling = True          # stay suppressed during grace period
            self._grace_timer.start(1500)   # ms

    def _end_grace_period(self):
        """Called when the post-compilation grace period expires."""
        self._compiling = False
        
        # 🔥 process delayed changes
        for path in list(self._pending_changes):
            self._prompt_user(path)

        self._pending_changes.clear()
        
        # Discard any timers that crept in during the grace period
        for path in list(self._pending):
            self._cancel_pending(path)

    def _cancel_pending(self, path: str):
        """Stop and discard any debounce timer for *path*."""
        timer = self._pending.pop(path, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _resolve_path(self, path: str):
        """
        Return the editor_files key that matches *path*, or None.

        Handles Windows backslash / forward-slash differences and
        case-insensitive file systems by normalising both sides with
        os.path.normcase + os.path.abspath before comparing.
        """
        needle = os.path.normcase(os.path.abspath(path))
        for key in self._em.editor_files:
            if os.path.normcase(os.path.abspath(key)) == needle:
                return key
        return None

    def _rearm(self, path: str):
        """Re-add *path* to the watcher if the file still exists."""
        if os.path.isfile(path) and path not in self._watcher.files():
            self._watcher.addPath(path)

    # ------------------------------------------------------------------
    # Slots / event flow
    # ------------------------------------------------------------------

    def _on_file_changed(self, path: str):
        """Slot called by QFileSystemWatcher when *path* changes on disk."""

        # Ignore if we triggered the write ourselves
        normalised = os.path.normcase(os.path.abspath(path))
        if normalised in self._suppressed:
            self._suppressed.discard(normalised)
            # Re-arm in case the OS dropped the watch on atomic replace
            QTimer.singleShot(150, lambda p=path: self._rearm(p))
            return

        # Only react to files actually open in the editor
        if self._resolve_path(path) is None:
            return

        # Re-arm: vim/emacs do atomic renames which can drop the inode watch
        QTimer.singleShot(150, lambda p=path: self._rearm(p))

        # Debounce: cancel any existing timer for this path, start fresh
        self._cancel_pending(path)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda p=path: self._prompt_user(p))
        timer.start(350)  # ms
        self._pending[path] = timer

    def _prompt_user(self, path: str):
        """Show a non-blocking reload dialog for *path*."""
###
        import time

        now = time.time()

        if path in self._last_prompt_time:
            if now - self._last_prompt_time[path] < 1.0:
                return  # ignore duplicate within 1 sec

        self._last_prompt_time[path] = now
###        
        # if getattr(self, '_compiling', False):
            # self._pending_changes.add(path)
            # return          
        if getattr(self, '_compiling', False) and path.lower().endswith(".tex"):
            return
            
        self._cancel_pending(path)
        

        # File may have been deleted externally
        if not os.path.isfile(path):
            self._handle_deleted(path)
            return

        # Resolve to the canonical key used in editor_files
        #canonical = self._resolve_path(path)
        #if canonical is None or canonical not in self._em.editor_files:
        #    return
        
        path = os.path.normcase(os.path.abspath(path))

        editor_paths = {
            os.path.normcase(os.path.abspath(p)): p
            for p in self._em.editor_files
        }

        canonical = editor_paths.get(path)

        if not canonical:
            return

        #print("CHANGED:", path)
        #print("RESOLVED:", canonical)

        # Avoid stacking dialogs for the same file
        if canonical in self._dialog_open:
            return

        self._dialog_open.add(canonical)

        filename = os.path.basename(canonical)
        data = self._em.editor_files[canonical]
        is_modified = data.get("modified", False)

        msg = QMessageBox(self._mw)
        msg.setWindowTitle("File Changed on Disk")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(f"<b>{filename}</b> has been modified by another program.")

        if is_modified:
            msg.setInformativeText(
                "You also have unsaved changes in the editor. "
                "Do you want to reload the file from disk "
                "(your changes will be <b>lost</b>), or keep your version?"
            )
        else:
            msg.setInformativeText(
                "Do you want to reload it from disk?"
            )

        reload_btn = msg.addButton("Reload from Disk", QMessageBox.AcceptRole)
        msg.addButton("Keep My Version", QMessageBox.RejectRole)
        msg.setDefaultButton(reload_btn)

        # Non-blocking: show() returns immediately; finished signal fires later
        msg.finished.connect(
            lambda result, p=canonical, rb=reload_btn:
                self._on_dialog_finished(p, msg.clickedButton(), rb)
        )
        msg.show()

    def _on_dialog_finished(self, path: str, clicked, reload_btn):
        """Handle the user's choice from the reload dialog."""
        self._dialog_open.discard(path)
        if clicked is reload_btn:
            self._reload_file(path)

    def _reload_file(self, path: str):
        """Reload *path* from disk into the editor, preserving cursor position."""
        if path not in self._em.editor_files:
            return

        data = self._em.editor_files[path]
        editor = data.get("editor")
        if not editor:
            return

        try:
            new_content = self._em._read_file_robust(path)
        except OSError as exc:
            QMessageBox.critical(
                self._mw,
                "Reload Failed",
                f"Could not read <b>{os.path.basename(path)}</b>:<br>{exc}",
            )
            return

        # Save cursor position by line + column (survives content-length changes
        # better than a raw character offset).
        cursor = editor.textCursor()
        saved_block = cursor.blockNumber()
        saved_col = cursor.columnNumber()

        # Load content without triggering modification tracking
        self._em._loading_file = True
        editor.blockSignals(True)
        try:
            if hasattr(editor, "loadFileContent"):
                editor.loadFileContent(new_content)
            else:
                editor.setPlainText(new_content)
        finally:
            editor.blockSignals(False)
            self._em._loading_file = False

        # Restore cursor as close as possible to original position
        doc = editor.document()
        block = doc.findBlockByNumber(saved_block)
        if not block.isValid():
            block = doc.lastBlock()
        restore_cursor = editor.textCursor()
        restore_cursor.setPosition(
            min(block.position() + saved_col,
                block.position() + max(block.length() - 1, 0))
        )
        editor.setTextCursor(restore_cursor)
        editor.ensureCursorVisible()

        # Mark as unmodified — disk version is now loaded
        data["saved_content"] = new_content
        data["modified"] = False
        self._em._update_tab_title(path, False)

        # Re-run syntax highlighting
        if hasattr(editor, "highlighter") and editor.highlighter:
            editor.highlighter.rehighlight()

        # Re-arm the watcher (atomic save may have replaced the inode)
        self.resume(path)

        # Update UI
        if hasattr(self._mw, "update_title"):
            self._mw.update_title()
        if hasattr(self._mw, "update_status_bar"):
            self._mw.update_status_bar(
                f"Reloaded: {os.path.basename(path)}", timeout=4000
            )

        self.file_reloaded.emit(path)

    def _handle_deleted(self, path: str):
        """Notify the user that an open file was deleted externally."""
        canonical = self._resolve_path(path)
        if canonical is None:
            return

        filename = os.path.basename(canonical)

        QMessageBox.warning(
            self._mw,
            "File Deleted on Disk",
            f"<b>{filename}</b> has been deleted from disk.\n\n"
            "It will remain open as an unsaved document.",
            QMessageBox.Ok,
        )

        # Mark modified so the user is prompted to save on close
        data = self._em.editor_files.get(canonical)
        if data:
            data["modified"] = True
            self._em._update_tab_title(canonical, True)
        if hasattr(self._mw, "update_title"):
            self._mw.update_title()