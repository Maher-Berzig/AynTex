"""
Arabic Command Dialog - For inserting Arabic LaTeX commands
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QTextEdit, QPushButton, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ArabicCommandDialog(QDialog):
    def __init__(self, main_window, language="en"):
        super().__init__(main_window)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)   
        self.main_window = main_window
        self.language = language
        self.latex_command = ""
        
        self.setWindowTitle(
            main_window.translations[language]["insert_arabic_command"]
        )
        self.setModal(True)
        self.setFixedSize(450, 350)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Arabic Text Input Group
        text_group = QGroupBox(
            self.main_window.translations[self.language]["arabic_text_label"]
        )
        text_layout = QVBoxLayout(text_group)
        
        self.arabic_text = QLineEdit()
        self.arabic_text.setPlaceholderText(
            self.main_window.translations[self.language]["arabic_text_placeholder"]
        )
        self.arabic_text.setFont(QFont("Amiri", 12))
        self.arabic_text.setAlignment(Qt.AlignRight)
        self.arabic_text.textChanged.connect(self.update_preview)
        text_layout.addWidget(self.arabic_text)
        
        layout.addWidget(text_group)
        
        # Command Selection Group
        command_group = QGroupBox(
            self.main_window.translations[self.language]["command_label"]
        )
        command_layout = QVBoxLayout(command_group)
        
        # Predefined commands dropdown
        self.command_combo = QComboBox()
        self.populate_command_combo()
        self.command_combo.currentTextChanged.connect(self.on_command_changed)
        command_layout.addWidget(self.command_combo)
        
        # Custom command input
        self.custom_command = QLineEdit()
        self.custom_command.setPlaceholderText(
            self.main_window.translations[self.language]["command_placeholder"]
        )
        self.custom_command.textChanged.connect(self.update_preview)
        command_layout.addWidget(self.custom_command)
        
        layout.addWidget(command_group)
        
        # Preview Group
        preview_group = QGroupBox(
            self.main_window.translations[self.language]["preview_label"]
        )
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(80)
        self.preview_text.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_command)
        self.ok_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Set focus to Arabic text input
        self.arabic_text.setFocus()
        
    def populate_command_combo(self):
        """Populate the command combo box with common Arabic LaTeX commands"""
        commands = [
            ("Custom", ""),
            ("\\textarabic{}", "\\textarabic{}"),
            ("\\foreignlanguage{arabic}{}", "\\foreignlanguage{arabic}{}"),
            ("\\textRL{}", "\\textRL{}"),
            ("\\LR{}", "\\LR{}"),
            ("\\RL{}", "\\RL{}"),
            ("\\begin{Arabic}", "\\begin{Arabic}\n\n\\end{Arabic}"),
            ("\\begin{arab}", "\\begin{arab}\n\n\\end{arab}"),
            ("\\begin{RLtext}", "\\begin{RLtext}\n\n\\end{RLtext}"),
            ("\\Arb{}", "\\Arb{}"),
            ("\\arab{}", "\\arab{}")
        ]
        
        for display_text, command in commands:
            self.command_combo.addItem(display_text, command)
    
    def on_command_changed(self, text):
        """Handle command combo box change"""
        if text == "Custom":
            self.custom_command.setEnabled(True)
            self.custom_command.clear()
        else:
            self.custom_command.setEnabled(False)
            command = self.command_combo.currentData()
            if command:
                self.custom_command.setText(command)
        
        self.update_preview()
    
    def update_preview(self):
        """Update the preview of the LaTeX command"""
        arabic_text = self.arabic_text.text().strip()
        
        # Get command from combo or custom input
        if self.command_combo.currentText() == "Custom":
            command_template = self.custom_command.text().strip()
        else:
            command_template = self.command_combo.currentData() or ""
        
        if not command_template:
            self.preview_text.clear()
            return
        
        # Generate preview
        if arabic_text:
            if "{}" in command_template:
                # Single placeholder command
                preview = command_template.replace("{}", "{" + arabic_text + "}")
            elif "\\begin{" in command_template and "\\end{" in command_template:
                # Environment command
                lines = command_template.split('\n')
                if len(lines) >= 3:
                    lines[1] = arabic_text
                    preview = '\n'.join(lines)
                else:
                    preview = command_template.replace("\n\n", f"\n{arabic_text}\n")
            else:
                # Command without placeholder
                preview = f"{command_template}{{{arabic_text}}}"
        else:
            preview = command_template
        
        self.preview_text.setPlainText(preview)
        self.latex_command = preview
    
    def accept_command(self):
        """Accept and validate the command"""
        lang = self.main_window.menu_language
        
        tr = self.main_window.translations[lang]                                    
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
            
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        
        arabic_text = self.arabic_text.text().strip()
        command_template = ""
        
        if self.command_combo.currentText() == "Custom":
            command_template = self.custom_command.text().strip()
        else:
            command_template = self.command_combo.currentData() or ""
        
        if not command_template:
            QMessageBox.warning(
                self, 
                self.main_window.translations[self.language]["arabic_command_error"],
                self.main_window.translations[self.language]["arabic_command_error_msg"]
            )
            return
        
        self.update_preview()  # Ensure latest preview is generated
        self.accept()
    
    def get_latex_command(self):
        """Get the generated LaTeX command"""
        return self.latex_command
    
    # def get_preset_commands(self):
        # """Get list of preset commands for external use"""
        # presets = []
        # for i in range(1, self.command_combo.count()):  # Skip "Custom"
            # display_text = self.command_combo.itemText(i)
            # command = self.command_combo.itemData(i)
            # presets.append((display_text, command))
        # return presets
    
    # def set_arabic_text(self, text):
        # """Set Arabic text programmatically"""
        # self.arabic_text.setText(text)
        # self.update_preview()
    
    # def set_command(self, command):
        # """Set command programmatically"""
        # # Try to find the command in the combo box
        # for i in range(self.command_combo.count()):
            # if self.command_combo.itemData(i) == command:
                # self.command_combo.setCurrentIndex(i)
                # return
        
        # # If not found, set as custom
        # self.command_combo.setCurrentIndex(0)  # Custom
        # self.custom_command.setText(command)
        # self.update_preview()
    
    # def load_recent_commands(self):
        # """Load recently used commands (could be enhanced with config integration)"""
        # # This could be enhanced to load from configuration manager
        # # For now, just ensure the most common commands are available
        # pass
    
    # def save_recent_command(self, command):
        # """Save a recently used command (could be enhanced with config integration)"""
        # # This could be enhanced to save to configuration manager
        # # For now, just pass
        # pass
    
    def show_error(self, title, message):
        """Show error message dialog"""
        QMessageBox.critical(self.main_window, title, message)
