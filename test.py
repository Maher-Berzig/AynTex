#!/usr/bin/env python3
"""
PyQt5 Mini Text Editor with Spell Checking (English/Arabic)
Requires: PyQt5, pyspellchecker
Install: pip install PyQt5 pyspellchecker
"""

import sys
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QToolBar, QAction, 
    QFileDialog, QMessageBox, QFontDialog, QColorDialog,
    QComboBox, QLabel, QStatusBar, QMenu, QInputDialog,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog,
    QListWidget, QListWidgetItem, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer, QRegExp
from PyQt5.QtGui import (
    QTextCharFormat, QColor, QFont, QSyntaxHighlighter, 
    QTextCursor, QKeySequence, QIcon, QPalette
)
from spellchecker import SpellChecker


class SpellHighlighter(QSyntaxHighlighter):
    """Custom syntax highlighter for misspelled words"""
    
    def __init__(self, parent, spell_checker):
        super().__init__(parent)
        self.spell_checker = spell_checker
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor(231, 76, 60))
        self.error_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.error_format.setForeground(QColor(231, 76, 60))
        
        # Word boundary patterns for different languages
        self.english_pattern = QRegExp(r"\b[a-zA-Z']+\b")
        self.arabic_pattern = QRegExp(r"[\u0600-\u06FF]+")
        
    def set_spell_checker(self, spell_checker):
        self.spell_checker = spell_checker
        self.rehighlight()
        
    def highlightBlock(self, text):
        if not self.spell_checker:
            return
            
        # Check English words using QRegExp
        pos = 0
        while True:
            pos = self.english_pattern.indexIn(text, pos)
            if pos == -1:
                break
            length = self.english_pattern.matchedLength()
            word = self.english_pattern.cap(0)
            
            if len(word) > 1:
                word_lower = word.lower()
                # Check if word is misspelled
                if word_lower not in self.spell_checker.known([word_lower]):
                    correction = self.spell_checker.correction(word_lower)
                    if correction != word_lower:
                        self.setFormat(pos, length, self.error_format)
            
            pos += length
            
        # Check Arabic words
        pos = 0
        while True:
            pos = self.arabic_pattern.indexIn(text, pos)
            if pos == -1:
                break
            length = self.arabic_pattern.matchedLength()
            word = self.arabic_pattern.cap(0)
            
            if len(word) > 1:
                # Arabic spell checking
                if word not in self.spell_checker.known([word]):
                    correction = self.spell_checker.correction(word)
                    if correction != word:
                        self.setFormat(pos, length, self.error_format)
            
            pos += length


class SpellTextEdit(QTextEdit):
    """Custom QTextEdit with spell checking context menu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spell_checker = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def set_spell_checker(self, spell_checker):
        self.spell_checker = spell_checker
        
    def get_word_at_cursor(self, pos):
        """Get the word at the given position"""
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText(), cursor
        
    def show_context_menu(self, pos):
        """Show context menu with spelling suggestions"""
        menu = QMenu(self)
        
        # Get word at click position
        word, cursor = self.get_word_at_cursor(pos)
        
        if word and self.spell_checker and len(word) > 1:
            word_lower = word.lower()
            # Check if word is misspelled
            if word_lower not in self.spell_checker.known([word_lower]):
                correction = self.spell_checker.correction(word_lower)
                if correction != word_lower:
                    # Get suggestions
                    suggestions = list(self.spell_checker.candidates(word_lower))[:5]
                    
                    if suggestions:
                        # Add suggestions to menu
                        suggestions_menu = menu.addMenu("Suggestions")
                        for suggestion in suggestions:
                            action = QAction(suggestion, self)
                            action.triggered.connect(lambda checked, s=suggestion, c=cursor: self.replace_word(c, s))
                            suggestions_menu.addAction(action)
                        
                        menu.addSeparator()
                        
                        # Add to dictionary option
                        add_action = QAction("Add to Dictionary", self)
                        add_action.triggered.connect(lambda: self.add_to_dictionary(word_lower))
                        menu.addAction(add_action)
                        menu.addSeparator()
        
        # Standard text edit actions
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo)
        undo_action.setEnabled(self.document().isUndoAvailable())
        menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo)
        redo_action.setEnabled(self.document().isRedoAvailable())
        menu.addAction(redo_action)
        
        menu.addSeparator()
        
        cut_action = QAction("Cut", self)
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(self.textCursor().hasSelection())
        menu.addAction(cut_action)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.textCursor().hasSelection())
        menu.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)
        
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)
        
        menu.exec_(self.mapToGlobal(pos))
        
    def replace_word(self, cursor, new_word):
        """Replace the word at cursor with the suggested word"""
        cursor.insertText(new_word)
        
    def add_to_dictionary(self, word):
        """Add word to spell checker dictionary"""
        if self.spell_checker:
            self.spell_checker.word_frequency[word] = 1
            # Rehighlight to remove red underline
            parent = self.parent()
            while parent:
                if hasattr(parent, 'highlighter'):
                    parent.highlighter.rehighlight()
                    break
                parent = parent.parent()


class SuggestionDialog(QDialog):
    """Dialog for word suggestions"""
    
    def __init__(self, word, suggestions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spelling Suggestions")
        self.setMinimumSize(300, 200)
        self.selected_word = None
        
        layout = QVBoxLayout()
        
        # Current word display
        layout.addWidget(QLabel(f"Current word: <b>{word}</b>"))
        
        # Suggestions list
        layout.addWidget(QLabel("Suggestions:"))
        self.list_widget = QListWidget()
        for suggestion in suggestions:
            QListWidgetItem(suggestion, self.list_widget)
        self.list_widget.itemDoubleClicked.connect(self.accept_suggestion)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.accept_suggestion)
        ignore_btn = QPushButton("Ignore")
        ignore_btn.clicked.connect(self.reject)
        add_btn = QPushButton("Add to Dictionary")
        add_btn.clicked.connect(self.add_to_dict)
        
        btn_layout.addWidget(replace_btn)
        btn_layout.addWidget(ignore_btn)
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def accept_suggestion(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_word = item.text()
        self.accept()
        
    def add_to_dict(self):
        self.selected_word = "__ADD__"
        self.accept()


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Text Editor with Spell Check")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize spell checkers
        self.current_language = "English"
        self.spell_checker = SpellChecker(language='en')
        self.arabic_dict = set()  # Simplified Arabic support
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create text editor (custom SpellTextEdit)
        self.text_edit = SpellTextEdit()
        self.text_edit.setFont(QFont("Segoe UI", 12))
        self.text_edit.setPlaceholderText("Start typing... (Misspelled words will be underlined in red. Right-click for suggestions)")
        layout.addWidget(self.text_edit)
        
        # Setup spell checking
        self.text_edit.set_spell_checker(self.spell_checker)
        self.highlighter = SpellHighlighter(self.text_edit.document(), self.spell_checker)
        
        # Setup UI components
        self.setup_toolbar()
        self.setup_menu()
        self.setup_statusbar()
        
        # Auto-check timer
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_spelling)
        self.check_timer.start(1000)  # Check every second
        
        # Current file path
        self.current_file = None
        
        # Apply modern stylesheet
        self.apply_styles()
        
    def setup_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Language selector
        toolbar.addWidget(QLabel("Language: "))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Arabic", "Auto-detect"])
        self.lang_combo.currentTextChanged.connect(self.change_language)
        toolbar.addWidget(self.lang_combo)
        
        toolbar.addSeparator()
        
        # Spell check button
        spell_action = QAction("📝 Check Spelling", self)
        spell_action.setShortcut(QKeySequence("F7"))
        spell_action.triggered.connect(self.manual_spell_check)
        toolbar.addAction(spell_action)
        
        toolbar.addSeparator()
        
        # Formatting buttons
        bold_action = QAction("𝐁 Bold", self)
        bold_action.setShortcut(QKeySequence.Bold)
        bold_action.triggered.connect(lambda: self.format_text('bold'))
        toolbar.addAction(bold_action)
        
        italic_action = QAction("𝐼 Italic", self)
        italic_action.setShortcut(QKeySequence.Italic)
        italic_action.triggered.connect(lambda: self.format_text('italic'))
        toolbar.addAction(italic_action)
        
        underline_action = QAction("U̲ Underline", self)
        underline_action.setShortcut(QKeySequence.Underline)
        underline_action.triggered.connect(lambda: self.format_text('underline'))
        toolbar.addAction(underline_action)
        
        toolbar.addSeparator()
        
        # Font and color
        font_action = QAction("🔤 Font", self)
        font_action.triggered.connect(self.change_font)
        toolbar.addAction(font_action)
        
        color_action = QAction("🎨 Color", self)
        color_action.triggered.connect(self.change_color)
        toolbar.addAction(color_action)
        
        toolbar.addSeparator()
        
        # Word count
        self.word_count_label = QLabel("Words: 0")
        toolbar.addWidget(self.word_count_label)
        
        # Update word count on text change
        self.text_edit.textChanged.connect(self.update_word_count)
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.text_edit.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.text_edit.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cut", self)
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.text_edit.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.text_edit.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.text_edit.paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("Find and Replace", self)
        find_action.setShortcut(QKeySequence("Ctrl+H"))
        find_action.triggered.connect(self.find_replace)
        edit_menu.addAction(find_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        spell_action = QAction("Spell Check", self)
        spell_action.setShortcut(QKeySequence("F7"))
        spell_action.triggered.connect(self.manual_spell_check)
        tools_menu.addAction(spell_action)
        
        add_dict_action = QAction("Add Word to Dictionary", self)
        add_dict_action.triggered.connect(self.add_word_to_dictionary)
        tools_menu.addAction(add_dict_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready - Right-click misspelled words for suggestions")
        
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 10px;
                selection-background-color: #74b9ff;
            }
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #dcdde1;
                padding: 5px;
                spacing: 10px;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #74b9ff;
            }
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QPushButton:hover {
                background-color: #f5f6fa;
                border-color: #74b9ff;
            }
            QLabel {
                color: #2d3436;
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #dcdde1;
            }
            QMenuBar::item:selected {
                background-color: #74b9ff;
                color: white;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                padding: 5px;
            }
            QMenu::item:selected {
                background-color: #74b9ff;
                color: white;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #dcdde1;
                color: #636e72;
            }
        """)
        
    def change_language(self, language):
        """Switch between English and Arabic spell checking"""
        self.current_language = language
        if language == "English":
            self.spell_checker = SpellChecker(language='en')
            self.statusbar.showMessage("Switched to English spell checking")
        elif language == "Arabic":
            self.spell_checker = SpellChecker(language='ar')
            self.statusbar.showMessage("Switched to Arabic spell checking (experimental)")
        else:
            self.spell_checker = SpellChecker(language='en')
            self.statusbar.showMessage("Auto-detect enabled (defaulting to English)")
            
        self.text_edit.set_spell_checker(self.spell_checker)
        self.highlighter.set_spell_checker(self.spell_checker)
        
    def check_spelling(self):
        """Trigger spell check highlighting"""
        pass
        
    def manual_spell_check(self):
        """Interactive spell checking"""
        text = self.text_edit.toPlainText()
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.Start)
        
        words_to_check = []
        
        # Collect all words
        if self.current_language == "English" or self.current_language == "Auto-detect":
            pattern = r"\b[a-zA-Z']+\b"
            for match in re.finditer(pattern, text):
                word = match.group()
                if len(word) > 1 and not self.spell_checker.correction(word.lower()) == word.lower():
                    if word.lower() not in self.spell_checker.known([word.lower()]):
                        words_to_check.append((match.start(), match.end(), word))
        
        if not words_to_check:
            QMessageBox.information(self, "Spell Check", "No spelling errors found!")
            return
            
        # Go through each misspelled word
        for start, end, word in words_to_check:
            # Select the word
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            self.text_edit.setTextCursor(cursor)
            
            # Get suggestions
            suggestions = list(self.spell_checker.candidates(word))[:5]
            if not suggestions:
                suggestions = ["No suggestions"]
                
            # Show suggestion dialog
            dialog = SuggestionDialog(word, suggestions, self)
            if dialog.exec_() == QDialog.Accepted:
                if dialog.selected_word == "__ADD__":
                    self.spell_checker.word_frequency[word.lower()] = 1
                elif dialog.selected_word:
                    cursor.insertText(dialog.selected_word)
                    
        cursor.clearSelection()
        self.text_edit.setTextCursor(cursor)
        self.statusbar.showMessage("Spell check complete")
        
    def add_word_to_dictionary(self):
        """Add current word or selected word to dictionary"""
        cursor = self.text_edit.textCursor()
        word = cursor.selectedText()
        
        if not word:
            word, ok = QInputDialog.getText(self, "Add to Dictionary", "Enter word:")
            if not ok or not word:
                return
                
        word = word.strip().lower()
        self.spell_checker.word_frequency[word] = 1
        self.highlighter.rehighlight()
        self.statusbar.showMessage(f"Added '{word}' to dictionary")
        
    def format_text(self, format_type):
        """Apply text formatting"""
        cursor = self.text_edit.textCursor()
        format = QTextCharFormat()
        
        if format_type == 'bold':
            if cursor.charFormat().fontWeight() == QFont.Bold:
                format.setFontWeight(QFont.Normal)
            else:
                format.setFontWeight(QFont.Bold)
        elif format_type == 'italic':
            format.setFontItalic(not cursor.charFormat().fontItalic())
        elif format_type == 'underline':
            format.setFontUnderline(not cursor.charFormat().fontUnderline())
            
        cursor.mergeCharFormat(format)
        self.text_edit.mergeCurrentCharFormat(format)
        
    def change_font(self):
        """Change font of selected text or entire document"""
        cursor = self.text_edit.textCursor()
        current_font = cursor.charFormat().font()
        
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            format = QTextCharFormat()
            format.setFont(font)
            cursor.mergeCharFormat(format)
            self.text_edit.mergeCurrentCharFormat(format)
            
    def change_color(self):
        """Change text color"""
        cursor = self.text_edit.textCursor()
        current_color = cursor.charFormat().foreground().color()
        
        color = QColorDialog.getColor(current_color, self)
        if color.isValid():
            format = QTextCharFormat()
            format.setForeground(color)
            cursor.mergeCharFormat(format)
            self.text_edit.mergeCurrentCharFormat(format)
            
    def update_word_count(self):
        """Update word count display"""
        text = self.text_edit.toPlainText()
        count = len(text.split())
        self.word_count_label.setText(f"Words: {count}")
        
    def new_file(self):
        """Create new file"""
        if self.text_edit.document().isModified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
                
        self.text_edit.clear()
        self.current_file = None
        self.setWindowTitle("Mini Text Editor with Spell Check")
        
    def open_file(self):
        """Open file dialog"""
        if self.text_edit.document().isModified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
                
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.text_edit.setPlainText(f.read())
                self.current_file = filename
                self.setWindowTitle(f"Mini Text Editor - {filename}")
                self.statusbar.showMessage(f"Opened {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
                
    def save_file(self):
        """Save file"""
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                self.text_edit.document().setModified(False)
                self.statusbar.showMessage(f"Saved {self.current_file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
        else:
            self.save_as_file()
            
    def save_as_file(self):
        """Save as dialog"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            self.current_file = filename
            self.save_file()
            self.setWindowTitle(f"Mini Text Editor - {filename}")
            
    def find_replace(self):
        """Simple find and replace dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Find and Replace")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Find
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        find_input = QLineEdit()
        find_layout.addWidget(find_input)
        layout.addLayout(find_layout)
        
        # Replace
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        replace_input = QLineEdit()
        replace_layout.addWidget(replace_input)
        layout.addLayout(replace_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        find_btn = QPushButton("Find Next")
        replace_btn = QPushButton("Replace")
        replace_all_btn = QPushButton("Replace All")
        btn_layout.addWidget(find_btn)
        btn_layout.addWidget(replace_btn)
        btn_layout.addWidget(replace_all_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        
        # Functionality
        def find_next():
            text = find_input.text()
            if not self.text_edit.find(text):
                cursor = self.text_edit.textCursor()
                cursor.movePosition(QTextCursor.Start)
                self.text_edit.setTextCursor(cursor)
                self.text_edit.find(text)
                
        def replace():
            cursor = self.text_edit.textCursor()
            if cursor.hasSelection():
                cursor.insertText(replace_input.text())
            find_next()
            
        def replace_all():
            text = find_input.text()
            replacement = replace_input.text()
            new_text = self.text_edit.toPlainText().replace(text, replacement)
            self.text_edit.setPlainText(new_text)
            
        find_btn.clicked.connect(find_next)
        replace_btn.clicked.connect(replace)
        replace_all_btn.clicked.connect(replace_all)
        
        dialog.exec_()
        
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Mini Text Editor",
            """<h2>Mini Text Editor with Spell Check</h2>
            <p>A lightweight text editor with spell checking support for English and Arabic.</p>
            <p><b>Features:</b></p>
            <ul>
                <li>Real-time spell checking with red underlines</li>
                <li>Right-click context menu with suggestions</li>
                <li>English and Arabic language support</li>
                <li>Manual spell check with suggestions (F7)</li>
                <li>Text formatting (Bold, Italic, Underline)</li>
                <li>Find and Replace functionality</li>
                <li>Custom dictionary support</li>
            </ul>
            <p>Built with PyQt5 and pyspellchecker</p>"""
        )
        
    def closeEvent(self, event):
        """Handle window close"""
        if self.text_edit.document().isModified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Mini Text Editor")
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    editor = TextEditor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()