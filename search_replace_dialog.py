# search_replace_dialog.py
"""
Search and Replace Dialog - Provides enhanced search and replace functionality
"""
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QGridLayout, QGroupBox, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor


class SearchReplaceDialog(QDialog):
    def __init__(self, main_window, editor_manager=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.parent_window = main_window
        self.editor_manager = editor_manager
        self.last_search_position = 0
        self.current_highlights = []

        # Get translation dictionary
        lang = self.main_window.menu_language
        self.tr = self.main_window.translations[lang]

        self.setup_ui()
        self.setup_connections()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def setup_ui(self):
        tr = self.tr

        self.setWindowTitle(tr.get("search_replace_title", "Find and Replace"))
        self.setModal(False)
        self.resize(560, 380)

        layout = QVBoxLayout()

        # Search section
        search_group = QGroupBox(tr.get("search_group", "Search"))
        search_layout = QGridLayout()
        self.find_label = QLabel(tr.get("find_label", "Find:"))
        search_layout.addWidget(self.find_label, 0, 0)
        self.search_line_edit = QLineEdit()
        search_layout.addWidget(self.search_line_edit, 0, 1)
        self.replace_label = QLabel(tr.get("replace_with_label", "Replace with:"))
        search_layout.addWidget(self.replace_label, 1, 0)
        self.replace_line_edit = QLineEdit()
        search_layout.addWidget(self.replace_line_edit, 1, 1)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # Scope section
        scope_group = QGroupBox(tr.get("scope_group", "Scope"))
        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel(tr.get("search_in_label", "Search in:")))
        self.scope_combo = QComboBox()
        self.scope_combo.addItems([
            tr.get("scope_entire_document", "Entire Document"),
            tr.get("scope_selection_only", "Selection Only"),
            tr.get("scope_from_cursor_down", "From Cursor Down"),
            tr.get("scope_from_cursor_up", "From Cursor Up")
        ])
        scope_layout.addWidget(self.scope_combo)
        scope_layout.addStretch()
        scope_group.setLayout(scope_layout)
        layout.addWidget(scope_group)

        # Options section
        options_group = QGroupBox(tr.get("options_group", "Options"))
        options_layout = QHBoxLayout()
        self.case_sensitive_checkbox = QCheckBox(tr.get("case_sensitive", "Case sensitive"))
        self.whole_words_checkbox    = QCheckBox(tr.get("whole_words_only", "Whole words only"))
        self.regex_checkbox          = QCheckBox(tr.get("regular_expressions", "Regular expressions"))
        self.wrap_around_checkbox    = QCheckBox(tr.get("wrap_around", "Wrap around"))
        self.wrap_around_checkbox.setChecked(True)
        self.highlight_checkbox      = QCheckBox(tr.get("highlight_all", "Highlight all occurrences"))
        for cb in (self.case_sensitive_checkbox, self.whole_words_checkbox,
                   self.regex_checkbox, self.wrap_around_checkbox,
                   self.highlight_checkbox):
            options_layout.addWidget(cb)
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Buttons – row 1: Find actions
        self.find_next_button     = QPushButton(tr.get("find_next", "Find Next"))
        self.find_previous_button = QPushButton(tr.get("find_previous", "Find Previous"))
        self.find_all_button      = QPushButton(tr.get("find_all", "Find All"))

        btn_row1 = QHBoxLayout()
        for btn in (self.find_next_button, self.find_previous_button, self.find_all_button):
            btn_row1.addWidget(btn)
        btn_row1.addStretch()
        layout.addLayout(btn_row1)

        # Buttons – row 2: Replace actions + Close
        self.replace_next_button     = QPushButton(tr.get("replace_next", "Replace Next"))
        self.replace_previous_button = QPushButton(tr.get("replace_previous", "Replace Previous"))
        self.replace_all_button      = QPushButton(tr.get("replace_all", "Replace All"))
        self.close_button            = QPushButton(tr.get("close", "Close"))

        btn_row2 = QHBoxLayout()
        for btn in (self.replace_next_button, self.replace_previous_button,
                    self.replace_all_button):
            btn_row2.addWidget(btn)
        btn_row2.addStretch()
        btn_row2.addWidget(self.close_button)
        layout.addLayout(btn_row2)

        # Standardise all button sizes
        self._standardize_buttons(
            self.find_next_button, self.find_previous_button, self.find_all_button,
            self.replace_next_button, self.replace_previous_button,
            self.replace_all_button, self.close_button
        )

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        
    @staticmethod
    def _standardize_buttons(*buttons):
        """Give all buttons the same fixed width (widest label + padding)."""
        # Let Qt compute the natural size first, then align to the maximum
        max_width = max(btn.sizeHint().width() for btn in buttons)
        max_width = max(max_width, 130)          # floor of 130 px
        for btn in buttons:
            btn.setFixedWidth(max_width)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------
    def setup_connections(self):
        self.find_next_button.clicked.connect(self.find_next)
        self.find_previous_button.clicked.connect(self.find_previous)
        self.find_all_button.clicked.connect(self.find_all)
        self.replace_next_button.clicked.connect(self.replace_next)
        self.replace_previous_button.clicked.connect(self.replace_previous)
        self.replace_all_button.clicked.connect(self.replace_all)
        self.close_button.clicked.connect(self.close)

        self.search_line_edit.returnPressed.connect(self.find_next)
        self.replace_line_edit.returnPressed.connect(self.replace_next)

        self.case_sensitive_checkbox.toggled.connect(self.on_options_changed)
        self.whole_words_checkbox.toggled.connect(self.on_options_changed)
        self.regex_checkbox.toggled.connect(self.on_options_changed)
        self.scope_combo.currentIndexChanged.connect(self.on_options_changed)
        self.highlight_checkbox.toggled.connect(self._on_highlight_toggled)


    def refresh_translations(self):
        """Update all UI strings to the current language."""
        lang = self.main_window.menu_language
        self.tr = self.main_window.translations[lang]
        tr = self.tr

        self.setWindowTitle(tr.get("search_replace_title", "Find and Replace"))

        # Update search group
        self.findChildren(QGroupBox)[0].setTitle(tr.get("search_group", "Search"))
        self.find_label.setText(tr.get("find_label", "Find:"))
        self.replace_label.setText(tr.get("replace_with_label", "Replace with:"))

        # Update scope group
        scope_group = self.findChildren(QGroupBox)[1]
        scope_group.setTitle(tr.get("scope_group", "Scope"))
        for label in scope_group.findChildren(QLabel):
            label.setText(tr.get("search_in_label", "Search in:"))
            break

        # Update combo box items
        current_scope = self.scope_combo.currentText()
        original_map = {
            "Entire Document": 0,
            "Selection Only": 1,
            "From Cursor Down": 2,
            "From Cursor Up": 3
        }
        self.scope_combo.clear()
        self.scope_combo.addItems([
            tr.get("scope_entire_document", "Entire Document"),
            tr.get("scope_selection_only", "Selection Only"),
            tr.get("scope_from_cursor_down", "From Cursor Down"),
            tr.get("scope_from_cursor_up", "From Cursor Up")
        ])
        idx = original_map.get(current_scope, 0)
        self.scope_combo.setCurrentIndex(idx)

        # Update options group
        options_group = self.findChildren(QGroupBox)[2]
        options_group.setTitle(tr.get("options_group", "Options"))
        self.case_sensitive_checkbox.setText(tr.get("case_sensitive", "Case sensitive"))
        self.whole_words_checkbox.setText(tr.get("whole_words_only", "Whole words only"))
        self.regex_checkbox.setText(tr.get("regular_expressions", "Regular expressions"))
        self.wrap_around_checkbox.setText(tr.get("wrap_around", "Wrap around"))
        self.highlight_checkbox.setText(tr.get("highlight_all", "Highlight all occurrences"))

        # Update buttons
        self.find_next_button.setText(tr.get("find_next", "Find Next"))
        self.find_previous_button.setText(tr.get("find_previous", "Find Previous"))
        self.find_all_button.setText(tr.get("find_all", "Find All"))
        self.replace_next_button.setText(tr.get("replace_next", "Replace Next"))
        self.replace_previous_button.setText(tr.get("replace_previous", "Replace Previous"))
        self.replace_all_button.setText(tr.get("replace_all", "Replace All"))
        self.close_button.setText(tr.get("close", "Close"))

        self._standardize_buttons(
            self.find_next_button, self.find_previous_button, self.find_all_button,
            self.replace_next_button, self.replace_previous_button,
            self.replace_all_button, self.close_button
        )

        self.status_label.setText("")
    
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def on_options_changed(self):
        self.clear_highlights()
        self.last_search_position = 0
        self.status_label.setText("")

    def _on_highlight_toggled(self, checked):
        if not checked:
            self.clear_highlights()

    def get_current_editor(self):
        if self.editor_manager:
            return self.editor_manager.get_current_editor()
        return None

    def get_search_flags(self):
        flags = 0
        if not self.case_sensitive_checkbox.isChecked():
            flags |= re.IGNORECASE
        return flags

    def create_search_pattern(self, text):
        """Build a regex pattern from the search text.

        In non-regex mode re.escape() makes every character literal,
        including backslashes, so LaTeX commands like \\textit work fine.
        Word boundaries are only added when the text has no backslash.
        """
        if self.regex_checkbox.isChecked():
            return text
        pattern = re.escape(text)
        if self.whole_words_checkbox.isChecked() and '\\' not in text:
            pattern = r'\b' + pattern + r'\b'
        return pattern

    def validate_pattern(self, pattern):
        try:
            re.compile(pattern)
            return True, None
        except re.error as e:
            return False, str(e)

    def _safe_replace(self, pattern, replace_text, source, flags):
        """Call re.sub() safely.

        In non-regex mode use a lambda so that backslashes in replace_text
        are never interpreted as regex escape sequences (\\t, \\1, etc.).
        In regex mode pass the string directly so back-references work.
        """
        if self.regex_checkbox.isChecked():
            return re.sub(pattern, replace_text, source, flags=flags)
        else:
            return re.sub(pattern, lambda m: replace_text, source, flags=flags)

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------
    def get_search_scope(self):
        """Return (full_content, scope_start, scope_end) or (None, 0, 0)."""
        tr = self.tr
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return None, 0, 0

        content = editor.toPlainText()
        cursor  = editor.textCursor()
        scope   = self.scope_combo.currentText()

        if scope == tr.get("scope_selection_only", "Selection Only"):
            if not cursor.hasSelection():
                self.status_label.setText(tr.get("status_no_selection_using_entire", "No selection – using Entire Document"))
                self.scope_combo.setCurrentIndex(0)
                return content, 0, len(content)
            return content, cursor.selectionStart(), cursor.selectionEnd()

        if scope == tr.get("scope_from_cursor_down", "From Cursor Down"):
            return content, cursor.position(), len(content)

        if scope == tr.get("scope_from_cursor_up", "From Cursor Up"):
            return content, 0, cursor.position()

        return content, 0, len(content)   # Entire Document

    # ------------------------------------------------------------------
    # Core find
    # ------------------------------------------------------------------
    def find_text(self, text, start_pos, forward, scope_start, scope_end):
        """Return (match_start, match_end) or None."""
        tr = self.tr
        editor = self.get_current_editor()
        if not editor or not text:
            return None

        content = editor.toPlainText()

        try:
            pattern = self.create_search_pattern(text)
            valid, error = self.validate_pattern(pattern)
            if not valid:
                self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(error))
                return None

            flags     = self.get_search_flags()
            start_pos = max(scope_start, min(start_pos, scope_end))

            if forward:
                m = re.search(pattern, content[start_pos:scope_end], flags)
                if m:
                    return start_pos + m.start(), start_pos + m.end()
                if self.wrap_around_checkbox.isChecked() and start_pos > scope_start:
                    m = re.search(pattern, content[scope_start:start_pos], flags)
                    if m:
                        return scope_start + m.start(), scope_start + m.end()
            else:
                ms = list(re.finditer(pattern, content[scope_start:start_pos], flags))
                if ms:
                    m = ms[-1]
                    return scope_start + m.start(), scope_start + m.end()
                if self.wrap_around_checkbox.isChecked():
                    ms = list(re.finditer(pattern, content[start_pos:scope_end], flags))
                    if ms:
                        m = ms[-1]
                        return start_pos + m.start(), start_pos + m.end()

        except re.error as e:
            self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(e))

        return None

    def _select_match(self, editor, start, end):
        cursor = editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()

    # ------------------------------------------------------------------
    # Highlighting
    # ------------------------------------------------------------------
    def highlight_all_occurrences(self, search_text, scope_start, scope_end):
        editor = self.get_current_editor()
        if not editor:
            return
        self.clear_highlights()
        try:
            pattern = self.create_search_pattern(search_text)
            flags   = self.get_search_flags()
            content = editor.toPlainText()
            hl_fmt  = QTextCharFormat()
            hl_fmt.setBackground(QColor(255, 255, 0))
            cursor  = editor.textCursor()
            for m in re.finditer(pattern, content[scope_start:scope_end], flags):
                a = scope_start + m.start()
                b = scope_start + m.end()
                cursor.setPosition(a)
                cursor.setPosition(b, QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(hl_fmt)
                self.current_highlights.append((a, b))
        except re.error:
            pass

    def clear_highlights(self):
        editor = self.get_current_editor()
        if not editor or not self.current_highlights:
            return
        clear_fmt = QTextCharFormat()
        clear_fmt.setBackground(QColor(0, 0, 0, 0))
        cursor = editor.textCursor()
        for start, end in self.current_highlights:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(clear_fmt)
        self.current_highlights = []

    def _maybe_highlight(self, search_text, scope_start, scope_end):
        if self.highlight_checkbox.isChecked():
            self.highlight_all_occurrences(search_text, scope_start, scope_end)

    # ------------------------------------------------------------------
    # Find actions
    # ------------------------------------------------------------------
    def find_next(self):
        tr = self.tr
        search_text = self.search_line_edit.text()
        if not search_text:
            self.status_label.setText(tr.get("status_enter_text", "Enter text to search"))
            return
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return
        content, s0, s1 = self.get_search_scope()
        if content is None:
            return
        pos    = editor.textCursor().position()
        result = self.find_text(search_text, pos, True, s0, s1)
        if result:
            a, b = result
            self._select_match(editor, a, b)
            self.last_search_position = b
            self.status_label.setText(tr.get("status_found_at_position", "Found at position {}").format(a))
            self._maybe_highlight(search_text, s0, s1)
        else:
            self.status_label.setText(tr.get("status_text_not_found", "Text not found"))

    def find_previous(self):
        tr = self.tr
        search_text = self.search_line_edit.text()
        if not search_text:
            self.status_label.setText(tr.get("status_enter_text", "Enter text to search"))
            return
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return
        content, s0, s1 = self.get_search_scope()
        if content is None:
            return
        cursor = editor.textCursor()
        pos    = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        result = self.find_text(search_text, pos, False, s0, s1)
        if result:
            a, b = result
            self._select_match(editor, a, b)
            self.last_search_position = a
            self.status_label.setText(tr.get("status_found_at_position", "Found at position {}").format(a))
            self._maybe_highlight(search_text, s0, s1)
        else:
            self.status_label.setText(tr.get("status_text_not_found", "Text not found"))

    def find_all(self):
        tr = self.tr
        search_text = self.search_line_edit.text()
        if not search_text:
            self.status_label.setText(tr.get("status_enter_text", "Enter text to search"))
            return
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return
        content, s0, s1 = self.get_search_scope()
        if content is None:
            return
        try:
            pattern = self.create_search_pattern(search_text)
            valid, error = self.validate_pattern(pattern)
            if not valid:
                self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(error))
                return
            flags   = self.get_search_flags()
            matches = list(re.finditer(pattern, content[s0:s1], flags))
            if matches:
                self.status_label.setText(tr.get("status_found_occurrences", "Found {} occurrence(s)").format(len(matches)))
                self._maybe_highlight(search_text, s0, s1)
            else:
                self.clear_highlights()
                self.status_label.setText(tr.get("status_text_not_found", "Text not found"))
        except re.error as e:
            self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(e))

    # ------------------------------------------------------------------
    # Replace helpers
    # ------------------------------------------------------------------
    def _replace_selected(self, editor, search_text, replace_text):
        """Replace the current selection if it matches. Returns True on success."""
        tr = self.tr
        cursor        = editor.textCursor()
        selected_text = cursor.selectedText()
        try:
            pattern = self.create_search_pattern(search_text)
            flags   = self.get_search_flags()
            if re.fullmatch(pattern, selected_text, flags):
                replacement = self._safe_replace(pattern, replace_text, selected_text, flags)
                cursor.insertText(replacement)
                self.clear_highlights()
                return True
            self.status_label.setText(tr.get("status_selection_no_match", "Selection does not match search text"))
            return False
        except re.error as e:
            self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(e))
            return False

    # ------------------------------------------------------------------
    # Replace actions
    # ------------------------------------------------------------------
    def replace_next(self):
        tr = self.tr
        search_text  = self.search_line_edit.text()
        replace_text = self.replace_line_edit.text()
        if not search_text:
            self.status_label.setText(tr.get("status_enter_text", "Enter text to search"))
            return
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return
        if not editor.textCursor().hasSelection():
            self.find_next()
        if not editor.textCursor().hasSelection():
            return
        if self._replace_selected(editor, search_text, replace_text):
            self.status_label.setText(tr.get("status_replaced_one", "Replaced 1 occurrence"))
            self.find_next()

    def replace_previous(self):
        tr = self.tr
        search_text  = self.search_line_edit.text()
        replace_text = self.replace_line_edit.text()
        if not search_text:
            self.status_label.setText(tr.get("status_enter_text", "Enter text to search"))
            return
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return
        if not editor.textCursor().hasSelection():
            self.find_previous()
        if not editor.textCursor().hasSelection():
            return
        if self._replace_selected(editor, search_text, replace_text):
            self.status_label.setText(tr.get("status_replaced_one", "Replaced 1 occurrence"))
            self.find_previous()

    def replace_all(self):
        tr = self.tr
        search_text  = self.search_line_edit.text()
        replace_text = self.replace_line_edit.text()
        if not search_text:
            self.status_label.setText(tr.get("status_enter_text", "Enter text to search"))
            return
        editor = self.get_current_editor()
        if not editor:
            self.status_label.setText(tr.get("status_no_active_editor", "No active editor"))
            return
        content, s0, s1 = self.get_search_scope()
        if content is None:
            return
        try:
            pattern = self.create_search_pattern(search_text)
            valid, error = self.validate_pattern(pattern)
            if not valid:
                self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(error))
                return
            flags   = self.get_search_flags()
            matches = list(re.finditer(pattern, content[s0:s1], flags))
            if not matches:
                self.status_label.setText(tr.get("status_text_not_found", "Text not found"))
                return
            reply = QMessageBox.question(
                self, tr.get("replace_all_title", "Replace All"),
                tr.get("replace_all_confirm", "Replace {} occurrence(s)?").format(len(matches)),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                self.status_label.setText(tr.get("status_replace_cancelled", "Replace all cancelled"))
                return

            # ── KEY FIX ──────────────────────────────────────────────
            # _safe_replace uses a lambda in non-regex mode so backslashes
            # in replace_text (e.g. \text) are never mis-interpreted.
            before    = content[:s0]
            in_scope  = content[s0:s1]
            after     = content[s1:]
            new_scope = self._safe_replace(pattern, replace_text, in_scope, flags)
            new_content = before + new_scope + after
            # ─────────────────────────────────────────────────────────

            cursor = editor.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.insertText(new_content)
            self.clear_highlights()
            self.status_label.setText(tr.get("status_replaced_occurrences", "Replaced {} occurrence(s)").format(len(matches)))

        except re.error as e:
            self.status_label.setText(tr.get("status_invalid_regex", "Invalid regular expression: {}").format(e))

    # ------------------------------------------------------------------
    # Public helpers called from main_window.py
    # ------------------------------------------------------------------
    def show_for_search(self):
        self.search_line_edit.setFocus()
        self.search_line_edit.selectAll()
        self.show()

    def show_for_replace(self):
        self.search_line_edit.setFocus()
        self.search_line_edit.selectAll()
        self.show()

    def set_search_text(self, text):
        self.search_line_edit.setText(text)

    def closeEvent(self, event):
        self.clear_highlights()
        self.hide()
        event.ignore()