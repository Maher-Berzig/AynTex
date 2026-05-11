# settings_manager.py (new version)
"""
Settings Manager - Enhanced with Font Selection and Configuration Integration
Handles settings dialog and saves settings to configuration file
"""
import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QGroupBox, QFrame,
    QDialog, QTextEdit, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal
from PyQt5.QtGui import QDrag, QFont, QPixmap, QPainter

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame, QColorDialog,
    QSpinBox, QCheckBox, QPushButton, QGroupBox, QGridLayout, QApplication,
    QTabWidget, QWidget, QFontComboBox, QLineEdit, QScrollArea,
    QDialogButtonBox, QTextEdit, QFormLayout, QListWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QColor
from cwl_manager import CWLManager
from completion_settings_widget import CompletionSettingsWidget
from toolbar_manager import DocumentTreeWidget

# class DraggableButtonRow(QFrame):
    # """A draggable row representing a side panel button configuration"""
    # orderChanged = pyqtSignal()

    # def __init__(self, index, label_text="", latex_text="", shortcut_text="", parent=None):
        # super().__init__(parent)
        # self.index = index
        # self.parent_widget = parent
        # self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        # self.setAcceptDrops(True)
        # self.setMinimumHeight(95)

        # layout = QHBoxLayout(self)
        # layout.setContentsMargins(5, 5, 5, 5)

        # # Drag handle
        # self.drag_handle = QLabel("⋮⋮")
        # self.drag_handle.setFixedWidth(20)                                                      
        # self.drag_handle.setCursor(Qt.OpenHandCursor)
        # layout.addWidget(self.drag_handle)

        # # Index label
        # self.index_label = QLabel(f"{index + 1}.")
        # self.index_label.setFixedWidth(25)
        # layout.addWidget(self.index_label)

        # # Input fields container
        # fields_layout = QVBoxLayout()

        # # Label input             
        # label_row = QHBoxLayout()
        # label_row.addWidget(QLabel("Label:"))
        # self.label_field = QLineEdit(label_text)
        # self.label_field.setPlaceholderText("Button text")
        # self.label_field.setMaxLength(10)
        # label_row.addWidget(self.label_field)
        # fields_layout.addLayout(label_row)

        # # LaTeX input
        # latex_row = QHBoxLayout()
        # latex_row.addWidget(QLabel("LaTeX:"))
        # self.latex_field = QLineEdit(latex_text)
        # self.latex_field.setPlaceholderText("LaTeX command (use 'cursor' for cursor position)")
        # latex_row.addWidget(self.latex_field)
        # fields_layout.addLayout(latex_row)

        # layout.addLayout(fields_layout, stretch=1)

        # # After the latex_row block, add:
        # shortcut_row = QHBoxLayout()
        # sc_label = QLabel("Shortcut:")
        # sc_label.setFixedWidth(55)
        # shortcut_row.addWidget(sc_label)
        # self.shortcut_field = QLineEdit(shortcut_text)
        # self.shortcut_field.setPlaceholderText("e.g. Ctrl+Shift+B  (optional)")
        # self.shortcut_field.setMaxLength(25)
        # shortcut_row.addWidget(self.shortcut_field)
        # fields_layout.addLayout(shortcut_row)


        # # ✅ Apply theme-aware styles on construction
        # self.refresh_theme()

        # self._drag_start_pos = None
class DraggableButtonRow(QFrame):
    orderChanged = pyqtSignal()

    def __init__(self, index, label_text="", latex_text="", shortcut_text="", parent=None, tr=None):
        super().__init__(parent)
        self.index = index
        self.parent_widget = parent
        self.tr = tr if tr is not None else {}
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setAcceptDrops(True)
        self.setMinimumHeight(95)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.drag_handle = QLabel("⋮⋮")
        self.drag_handle.setFixedWidth(20)
        self.drag_handle.setCursor(Qt.OpenHandCursor)
        layout.addWidget(self.drag_handle)

        self.index_label = QLabel(f"{index + 1}.")
        self.index_label.setFixedWidth(25)
        layout.addWidget(self.index_label)

        fields_layout = QVBoxLayout()

        # Label row
        label_row = QHBoxLayout()
        label_row.addWidget(QLabel(self.tr.get("sidepanel_label_label", "Label:")))
        self.label_field = QLineEdit(label_text)
        self.label_field.setPlaceholderText(self.tr.get("sidepanel_button_text_placeholder", "Button text"))
        self.label_field.setMaxLength(10)
        label_row.addWidget(self.label_field)
        fields_layout.addLayout(label_row)

        # LaTeX row
        latex_row = QHBoxLayout()
        latex_row.addWidget(QLabel(self.tr.get("sidepanel_latex_label", "LaTeX:")))
        self.latex_field = QLineEdit(latex_text)
        self.latex_field.setPlaceholderText(self.tr.get("sidepanel_latex_placeholder", "LaTeX command (use 'cursor' for cursor position)"))
        latex_row.addWidget(self.latex_field)
        fields_layout.addLayout(latex_row)

        # Shortcut row
        shortcut_row = QHBoxLayout()
        sc_label = QLabel(self.tr.get("sidepanel_shortcut_label", "Shortcut:"))
        sc_label.setFixedWidth(55)
        shortcut_row.addWidget(sc_label)
        self.shortcut_field = QLineEdit(shortcut_text)
        self.shortcut_field.setPlaceholderText(self.tr.get("sidepanel_shortcut_placeholder", "e.g. Ctrl+Shift+B  (optional)"))
        self.shortcut_field.setMaxLength(25)
        shortcut_row.addWidget(self.shortcut_field)
        fields_layout.addLayout(shortcut_row)

        layout.addLayout(fields_layout, stretch=1)
        self.refresh_theme()
        self._drag_start_pos = None

    # ... rest of DraggableButtonRow unchanged (refresh_theme, etc.)
    # ── Theme helpers ─────────────────────────────────────────────────────────
    def refresh_theme(self):
        """Re-apply all inline stylesheets to match the current application theme."""
        self._apply_row_style()
        self._apply_handle_style()

    def _apply_row_style(self):
        """Apply the normal (non-drag) row stylesheet."""
        from style_manager import get_draggable_row_style
        s = get_draggable_row_style()
        self.setStyleSheet(f"""
            DraggableButtonRow {{
                background-color: {s['row_bg']};
                border: 1px solid {s['row_border']};
                border-radius: 4px;
                margin: 2px;
            }}
            DraggableButtonRow:hover {{
                border-color: {s['row_hover_border']};
                background-color: {s['row_hover_bg']};
            }}
        """)

    def _apply_drag_over_style(self):
        """Apply the drag-enter highlight stylesheet."""
        from style_manager import get_draggable_row_style
        s = get_draggable_row_style()
        self.setStyleSheet(f"""
            DraggableButtonRow {{
                background-color: {s['drag_over_bg']};
                border: 2px dashed {s['drag_over_border']};
                border-radius: 4px;
                margin: 2px;
            }}
        """)

    def _apply_handle_style(self):
        """Apply the drag handle label stylesheet."""
        from style_manager import get_draggable_row_style
        s = get_draggable_row_style()
        self.drag_handle.setStyleSheet(f"""
            QLabel {{
                color: {s['handle_color']};
                font-size: 16px;
                font-weight: bold;
            }}
            QLabel:hover {{
                color: {s['handle_hover']};
            }}
        """)

    # ── Data access ───────────────────────────────────────────────────────────

    def get_data(self):
        return {
            "label":    self.label_field.text().strip(),
            "latex":    self.latex_field.text().strip(),
            "shortcut": self.shortcut_field.text().strip(),
        }

    def set_data(self, label, latex, shortcut=""):
        self.label_field.setText(label)
        self.latex_field.setText(latex)
        self.shortcut_field.setText(shortcut)

    # ── Mouse / drag events ───────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
                                                       
            if self.drag_handle.geometry().contains(event.pos()):
                                                 
                self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None:
            if (event.pos() - self._drag_start_pos).manhattanLength() > 10:
                self.start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def start_drag(self):
                                      
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.index))
        drag.setMimeData(mime_data)

                                                             
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(self._drag_start_pos)

        self._drag_start_pos = None
        drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self._apply_drag_over_style()   # ✅ theme-aware highlight
                                    
    def dragLeaveEvent(self, event):
        self._apply_row_style()             # ✅ restore on leave
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        source_index = int(event.mimeData().text())
        target_index = self.index

        if source_index != target_index and self.parent_widget:
            self.parent_widget.move_row(source_index, target_index)

        self._apply_row_style()             # ✅ restore after drop
                                
        event.acceptProposedAction()


# class SidePanelSettingsWidget(QWidget):
    # """Widget for managing side panel button configurations"""
    # commandsChanged = pyqtSignal(list)
    
    # def __init__(self, main_window, parent=None):
        # super().__init__(parent)

        # self.main_window = main_window
        # self.rows = []
        # self._setup_ui()
        # self._load_commands()
        # self.refresh_theme() 
    
    # def _setup_ui(self):
        # layout = QVBoxLayout(self)
        
        # # Header
        # header_label = QLabel("Customize Side Panel Buttons (up to 100):")
        # header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        # layout.addWidget(header_label)
        
        # # Add/Remove buttons row
        # button_row = QHBoxLayout()
        
        # self.add_button = QPushButton("+ Add Button")
        # self.add_button.setToolTip("Add a new button (max 100)")
        # self.add_button.clicked.connect(self.add_new_button)
        # button_row.addWidget(self.add_button)
        
        # self.remove_button = QPushButton("- Remove Last")
        # self.remove_button.setToolTip("Remove the last button (cannot remove first 17)")
        # self.remove_button.clicked.connect(self.remove_last_button)
        # button_row.addWidget(self.remove_button)
        
        # self.button_count_label = QLabel("Buttons: 17")
        # button_row.addWidget(self.button_count_label)
        
        # button_row.addStretch()
        # layout.addLayout(button_row)
        
        # # Scrollable area for button configurations
        # self.scroll = QScrollArea()
        # self.scroll.setWidgetResizable(True)
        # self.scroll.setMinimumHeight(400)
        
        # self.scroll_widget = QWidget()
        # self.scroll_layout = QVBoxLayout(self.scroll_widget)
        # self.scroll_layout.setSpacing(5)
        # self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # self.scroll.setWidget(self.scroll_widget)
        # layout.addWidget(self.scroll, stretch=1)
        
        # # Action buttons
        # action_row = QHBoxLayout()
        
        # default_button = QPushButton("Reset to Default")
        # default_button.setToolTip("Reset all buttons to default LaTeX commands")
        # default_button.clicked.connect(self.reset_to_default)
        # action_row.addWidget(default_button)
        
        # preview_button = QPushButton("Preview Commands")
        # preview_button.setToolTip("Preview how the commands will look")
        # preview_button.clicked.connect(self.preview_commands)
        # action_row.addWidget(preview_button)
        
        # action_row.addStretch()
        # layout.addLayout(action_row)
        
        # # Help text
        # help_text = QLabel(
            # "💡 Tips:\n"
            # "• Drag ⋮⋮ handle to reorder buttons\n"
            # "• Use 'cursor' to mark cursor position\n"
            # "• Use '\\n' in the LaTeX field to insert line breaks (will be converted to real newlines)\n"
            # "• Leave fields empty to hide the button\n"
            # "• First 17 buttons cannot be removed (but can be emptied)\n"
            # "• Keep labels short (10 chars max)\n\n"
            # "📘 Example – Enumerated list with three items:\n"
            # "   Label:   enum\n"
            # "   LaTeX:   \\begin{enumerate}\\n\\item cursor\\n\\item\\n\\item\\n\\end{enumerate}\\n\n"
            # "→ Result:\n"
            # "   \\begin{enumerate}\n"
            # "   \\item |\n"
            # "   \\item\n"
            # "   \\item\n"
            # "   \\end{enumerate}\n"
        # )        

        # help_text.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        # help_text.setWordWrap(True)
        # layout.addWidget(help_text)

class SidePanelSettingsWidget(QWidget):
    commandsChanged = pyqtSignal(list)

    def __init__(self, main_window, tr, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.tr = tr
        self.rows = []
        self._setup_ui()
        self._load_commands()
        self.refresh_theme()

    def _setup_ui(self):
        tr = self.tr
        layout = QVBoxLayout(self)

        header_label = QLabel(tr.get("sidepanel_header", "Customize Side Panel Buttons (up to 100):"))
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header_label)

        button_row = QHBoxLayout()
        self.add_button = QPushButton(tr.get("sidepanel_add_button", "+ Add Button"))
        self.add_button.setToolTip(tr.get("sidepanel_add_tooltip", "Add a new button (max 100)"))
        self.add_button.clicked.connect(self.add_new_button)
        button_row.addWidget(self.add_button)

        self.remove_button = QPushButton(tr.get("sidepanel_remove_button", "- Remove Last"))
        self.remove_button.setToolTip(tr.get("sidepanel_remove_tooltip", "Remove the last button (cannot remove first 17)"))
        self.remove_button.clicked.connect(self.remove_last_button)
        button_row.addWidget(self.remove_button)

        self.button_count_label = QLabel(tr.get("sidepanel_buttons_count_prefix", "Buttons: ") + "17")
        button_row.addWidget(self.button_count_label)

        button_row.addStretch()
        layout.addLayout(button_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(400)

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(5)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)

        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll, stretch=1)

        action_row = QHBoxLayout()
        default_button = QPushButton(tr.get("sidepanel_reset_default", "Reset to Default"))
        default_button.setToolTip(tr.get("sidepanel_reset_tooltip", "Reset all buttons to default LaTeX commands"))
        default_button.clicked.connect(self.reset_to_default)
        action_row.addWidget(default_button)

        preview_button = QPushButton(tr.get("sidepanel_preview_commands", "Preview Commands"))
        preview_button.setToolTip(tr.get("sidepanel_preview_tooltip", "Preview how the commands will look"))
        preview_button.clicked.connect(self.preview_commands)
        action_row.addWidget(preview_button)

        action_row.addStretch()
        layout.addLayout(action_row)

        help_text = QLabel(tr.get("sidepanel_tips", "💡 Tips:\n• Drag ⋮⋮ handle to reorder buttons\n• Use 'cursor' to mark cursor position\n• Use '\\n' in the LaTeX field to insert line breaks (will be converted to real newlines)\n• Leave fields empty to hide the button\n• First 17 buttons cannot be removed (but can be emptied)\n• Keep labels short (10 chars max)\n\n📘 Example – Enumerated list with three items:\n   Label:   enum\n   LaTeX:   \\begin{enumerate}\\n\\item cursor\\n\\item\\n\\item\\n\\end{enumerate}\\n\n→ Result:\n   \\begin{enumerate}\n   \\item |\n   \\item\n   \\item\n   \\end{enumerate}\n"))
        help_text.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

    

    def _create_rows(self, commands):
        for row in self.rows:
            row.deleteLater()
        self.rows.clear()

        while len(commands) < self.main_window.side_panel.DEFAULT_BUTTON_COUNT:
            commands.append({"label": "", "latex": "", "shortcut": ""})

        for i, cmd in enumerate(commands):
            row = DraggableButtonRow(
                i,
                cmd.get("label", ""),
                cmd.get("latex", ""),
                cmd.get("shortcut", ""),
                parent=self,
                tr=self.tr
            )
            self.scroll_layout.addWidget(row)
            self.rows.append(row)

        self.scroll_layout.addStretch()
        self._update_button_count()
        self._update_remove_button_state()

    
    def refresh_theme(self):
        """Re-style static text widgets to match the active application theme."""
        from style_manager import get_settings_panel_style
        sp = get_settings_panel_style()

        # Help text label at the bottom of the widget
        for label in self.findChildren(QLabel):
            if label.wordWrap():  # targets the Tips / Example block
                label.setStyleSheet(
                    f"color: {sp['help_color']}; font-size: 10px; padding: 5px;"
                )

        # Header label
        for label in self.findChildren(QLabel):
            text = label.text()
            if "Customize Side Panel" in text:
                label.setStyleSheet(
                    f"font-weight: bold; font-size: 12px; color: {sp['header_color']};"
                )
                
        for row in self.rows:
            row.refresh_theme()        
    
    def _load_commands(self):
        """Load commands from the side panel"""
        commands = self.main_window.side_panel.commands
        self._create_rows(commands)
    
    # def _create_rows(self, commands):
        # """Create draggable rows for each command"""
        # # Clear existing rows
        # for row in self.rows:
            # row.deleteLater()
        # self.rows.clear()
        
        # # Ensure we have at least DEFAULT_BUTTON_COUNT rows
        # while len(commands) < self.main_window.side_panel.DEFAULT_BUTTON_COUNT:
            # commands.append({"label": "", "latex": ""})
        
        # # Create rows
        # for i, cmd in enumerate(commands):
            # row = DraggableButtonRow(
                # i, 
                # cmd.get("label", ""), 
                # cmd.get("latex", ""),
                # cmd.get("shortcut", ""),
                # parent=self
            # )
            # self.scroll_layout.addWidget(row)
            # self.rows.append(row)
        
        # self.scroll_layout.addStretch()
        # self._update_button_count()
        # self._update_remove_button_state()
    
    def _update_button_count(self):
        """Update the button count label"""
        tr = self.tr
        self.button_count_label.setText(
            f"{tr.get('sidepanel_buttons_count_prefix', 'Buttons:')} {len(self.rows)}"
        )

    
    def _update_remove_button_state(self):
        """Enable/disable remove button based on button count"""
        can_remove = len(self.rows) > self.main_window.side_panel.DEFAULT_BUTTON_COUNT
        self.remove_button.setEnabled(can_remove)
        
        can_add = len(self.rows) < self.main_window.side_panel.MAX_BUTTONS
        self.add_button.setEnabled(can_add)
    
    def move_row(self, from_index, to_index):
        """Move a row from one position to another"""
        if from_index == to_index:
            return
        
        # Get current commands
        commands = self.get_commands()
        
        # Move the command
        cmd = commands.pop(from_index)
        commands.insert(to_index, cmd)
        
        # Recreate rows
        self._create_rows(commands)
        
        # Emit change signal
        self.commandsChanged.emit(commands)
    
    def add_new_button(self):
        """Add a new button row"""
        if len(self.rows) >= self.main_window.side_panel.MAX_BUTTONS:
            QMessageBox.warning(self, "Limit Reached", 
                              f"Maximum of {self.main_window.side_panel.MAX_BUTTONS} buttons allowed.")
            return
        
        # Remove the stretch if it exists
        last_item = self.scroll_layout.itemAt(self.scroll_layout.count() - 1)
        if last_item and last_item.spacerItem():
            self.scroll_layout.removeItem(last_item)
        
        # Add new row
        index = len(self.rows)
        row = DraggableButtonRow(index, "New", "", parent=self)
        self.scroll_layout.addWidget(row)
        self.rows.append(row)
        
        # Add stretch back
        self.scroll_layout.addStretch()
        
        self._update_button_count()
        self._update_remove_button_state()
        
        # Scroll to bottom to show new button
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
        
        # Emit change signal
        self.commandsChanged.emit(self.get_commands())
    
    def remove_last_button(self):
        """Remove the last button row (only if > 17 buttons)"""
        if len(self.rows) <= self.main_window.side_panel.DEFAULT_BUTTON_COUNT:
            QMessageBox.warning(self, "Cannot Remove", 
                              "Cannot remove the first 17 buttons. You can empty them instead.")
            return
        
        # Remove last row
        row = self.rows.pop()
        self.scroll_layout.removeWidget(row)
        row.deleteLater()
        
        self._update_button_count()
        self._update_remove_button_state()
        
        # Emit change signal
        self.commandsChanged.emit(self.get_commands())
    
    def get_commands(self):
        """Get all commands from the UI"""
        commands = []
        for row in self.rows:
            data = row.get_data()
            commands.append(data)
        return commands
    
    def reset_to_default(self):
        """Reset to default commands"""
        reply = QMessageBox.question(
            self, "Reset to Default",
            "This will reset all button configurations to defaults. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            default_commands = self.main_window.side_panel.default_commands.copy()
            self._create_rows(default_commands)
            self.commandsChanged.emit(default_commands)
    
    def preview_commands(self):
        """Show preview dialog"""
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Side Panel Commands Preview")
        preview_dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(preview_dialog)
        
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        
        commands = self.get_commands()
        preview_content = "Side Panel Button Configuration:\n\n"
        
        active_count = 0
        for i, cmd in enumerate(commands):
            if cmd["label"].strip() and cmd["latex"].strip():
                preview_content += f"{i+1:3d}. [{cmd['label']:10s}] → {cmd['latex']}\n"
                active_count += 1
        
        preview_content += f"\n--- Total active buttons: {active_count} ---"
        
        if not any(cmd["label"].strip() for cmd in commands):
            preview_content += "\nNo buttons configured (all will be hidden)"
        
        preview_text.setPlainText(preview_content)
        preview_text.setFont(QFont("Consolas", 10))
        
        layout.addWidget(preview_text)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_button)
        
        preview_dialog.exec_()
class SettingsDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)        
        self.main_window = main_window
        self.setWindowTitle(main_window.translations[main_window.menu_language]["settings_dialog"])
        self.setModal(True)
        self.setFixedSize(750, 650)  # Increased size for font options

        # ADD these new widget references
        self.completion_enabled_check = None
        self.fuzzy_matching_check = None
        self.min_prefix_spin = None
        self.show_mode_indicators_check = None
        self.auto_enable_includes_check = None
        self.cwl_dir_edit = None
        self.cwl_settings_widget = None
        self.completion_stats_label = None
        
        
        # Initialize ALL tab references to None
        self.tab_widget = None
        self.switch_combo = None
        self.editor_layout_combo = None
        self.pdf_layout_combo = None
                
        self.menu_lang_combo = None
        self.rtl_check = None
        self.auto_load_check = None
        self.recent_list = None
        
        
        self._loading_settings = False   # new flag

        self.output_visible_check = None
        self.symbols_visible_check = None
        self.commands_visible_check = None
        self.tree_visible_check = None        
        self.bookmarks_visible_check = None  
        self.terminal_visible_check = None  
        self.line_numbers_check = None    
        self.fold_marker_check = None  
        
        self.output_tab_visible = None
        self.symbols_tab_visible = None
        self.commands_tab_visible = None
        self.tree_tab_visible = None
        self.bookmarks_tab_visible = None
        self.terminal_tab_visible = None
        self.is_line_numbers_visible = None
        self.is_fold_markers_visible = None
        
        # Command option widgets
        self.engine_combo = None
        self.command_text = None
        self.backmatter_combo = None
        self.backmatter_command_text = None
        
        # Default commands
        self.default_latex_commands = {
            "pdflatex": "pdflatex -synctex=1 -interaction=nonstopmode -shell-escape",
            "xelatex": "xelatex -synctex=1 -interaction=nonstopmode -shell-escape",
            "lualatex": "lualatex -synctex=1 -interaction=nonstopmode -shell-escape",
            "custom": ""  # Empty by default for custom
        }
        
        # Enhanced default backmatter commands with more options
        self.default_backmatter_commands = {
            "bibtex": "bibtex %b",
            "biber": "biber %b", 
            "makeindex": "makeindex %b.idx",
            "xindy": "xindy -M texindy -L english %b.idx",
            "makeglossaries": "makeglossaries %b",
            "custom": ""  # Empty by default for custom
        }

        # Connect to the visibility signal
        self.main_window.output_tabs_visibility_changed.connect(
            self._sync_output_checkbox
        )
        
        # Color/Highlighting widgets
        self.color_widgets = {}        
        
        self.setup_ui()
        


    # def setup_ui(self):
        # layout = QVBoxLayout(self)
        # self.tab_widget = QTabWidget()
        # self._tabs_initialized = set()

        # self._tab_loaders = {
            # "Fonts":        self._load_font_settings,
            # "Compiler":     self._load_compiler_settings,
            # "Layout":       self._load_layout_settings,
            # "UI":           self._load_ui_settings,
            # "Side Panel":   lambda: None,
            # "Colors":       self.load_color_settings,
            # "Completion":   self.load_completion_settings,
            # "AI Assistant": self._load_ai_settings,
        # }

        # tab_configs = [
            # ("Fonts",       self.create_font_tab),
            # ("Compiler",    self.create_compiler_tab),
            # ("Layout",      self.create_layout_tab),
            # ("UI",          self.create_ui_tab),
            # ("Side Panel",  self.create_side_panel_tab),
            # ("Colors",      self.create_color_tab),
            # ("Completion",  self.create_completion_tab),
            # ("AI Assistant",self.create_ai_tab),
        # ]

        # self._tab_builders = {}
        # for label, builder in tab_configs:
            # placeholder = QWidget()
            # self.tab_widget.addTab(placeholder, label)
            # self._tab_builders[label] = builder

        # self.tab_widget.currentChanged.connect(self._on_tab_selected)
        # layout.addWidget(self.tab_widget)


        # # Buttons
        # button_layout = QHBoxLayout()
        # self.ok_button = QPushButton("OK")
        # self.ok_button.clicked.connect(self.accept)
        # self.cancel_button = QPushButton("Cancel")
        # self.cancel_button.clicked.connect(self.reject)
        # self.apply_button = QPushButton("Apply")
        # self.apply_button.clicked.connect(self.apply_settings)
        # button_layout.addStretch()
        # button_layout.addWidget(self.ok_button)
        # button_layout.addWidget(self.cancel_button)
        # button_layout.addWidget(self.apply_button)
        # layout.addLayout(button_layout)

        # # ← Defer first tab build until after the dialog is painted
        # from PyQt5.QtCore import QTimer
        # QTimer.singleShot(0, lambda: self._build_tab(0))

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        self._tabs_initialized = set()

        # Get the current translations
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        # Define each tab: English key, translation key, builder method, loader method
        tab_info = [
            ("Fonts",       "tab_fonts",       self.create_font_tab,       self._load_font_settings),
            ("Compiler",    "tab_compiler",    self.create_compiler_tab,    self._load_compiler_settings),
            ("Layout",      "tab_layout",      self.create_layout_tab,      self._load_layout_settings),
            ("UI",          "tab_ui",          self.create_ui_tab,          self._load_ui_settings),
            ("Side Panel",  "tab_side_panel",  self.create_side_panel_tab,  lambda: None),
            ("Colors",      "tab_colors",      self.create_color_tab,       self.load_color_settings),
            ("Completion",  "tab_completion",  self.create_completion_tab,  self.load_completion_settings),
            ("AI Assistant","tab_ai_assistant",self.create_ai_tab,          self._load_ai_settings),
        ]

        self._tab_loaders = {}
        self._tab_builders = {}
        self._eng_to_trans = {}   # optional, for reference

        for eng_key, trans_key, builder, loader in tab_info:
            # Get the translated tab title; fallback to English key if missing
            translated_label = tr.get(trans_key, eng_key)
            # Create a placeholder widget
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, translated_label)
            # Store builders and loaders keyed by the *translated* label
            self._tab_builders[translated_label] = builder
            self._tab_loaders[translated_label] = loader
            self._eng_to_trans[eng_key] = translated_label

        self.tab_widget.currentChanged.connect(self._on_tab_selected)
        layout.addWidget(self.tab_widget)

        # Buttons (unchanged)
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(tr.get("ok_button", "OK"))
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(tr.get("cancel_button", "Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton(tr.get("apply_button", "Apply"))
        self.apply_button.clicked.connect(self.apply_settings)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

        # Defer first tab build until after the dialog is painted
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._build_tab(0))

    def _load_ai_settings(self):
        cfg = self.main_window.config_manager
        ai_mode = cfg.get_config_value('ai', 'mode', 'offline')
        index = self.ai_mode_combo.findData(ai_mode)
        if index >= 0:
            self.ai_mode_combo.setCurrentIndex(index)

        ai_provider = cfg.get_config_value('ai', 'provider', 'groq')
        index = self.ai_provider_combo.findData(ai_provider)
        if index >= 0:
            self.ai_provider_combo.setCurrentIndex(index)

        self.ai_api_key.setText(cfg.get_config_value('ai', 'api_key', ''))

        ai_model = cfg.get_config_value('ai', 'model', '')
        if ai_model:
            idx = self.ai_model_combo.findText(ai_model)
            if idx >= 0:
                self.ai_model_combo.setCurrentIndex(idx)

    def _load_compiler_settings(self):
        # self.engine_combo.setCurrentText(self.main_window.latex_engine)
        # self.backmatter_combo.setCurrentText(self.main_window.backmatter_engine)
        idx = self.engine_combo.findData(self.main_window.latex_engine)
        self.engine_combo.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.backmatter_combo.findData(self.main_window.backmatter_engine)
        self.backmatter_combo.setCurrentIndex(idx if idx >= 0 else 0)        
        
        
        self.encoding_combo.setCurrentText(self.main_window.output_encoding)
        engine = self.engine_combo.currentText()
        self.engine_combo.currentTextChanged.connect(
            self.main_window.toolbar_manager.update_compile_button_text)
        cmd = getattr(self.main_window, f'{engine}_option', None)
        self.command_text.setText(cmd or self.default_latex_commands.get(engine, ''))
        bm = self.backmatter_combo.currentText()
        bm_cmd = getattr(self.main_window, f'{bm}_option', None)
        self.backmatter_command_text.setText(
            bm_cmd or self.default_backmatter_commands.get(bm, ''))

    def _load_layout_settings(self):
        if self.switch_combo and hasattr(self.main_window, 'layout_manager'):
            layout = getattr(self.main_window.layout_manager, 'current_layout', 'editor_left')
            self.switch_combo.setCurrentText(layout)
        if self.editor_layout_combo and hasattr(self.main_window, 'editor_manager'):
            self.editor_layout_combo.setCurrentText(
                getattr(self.main_window.editor_manager, 'editor_layout_mode', 'tabbed'))
        if self.pdf_layout_combo and hasattr(self.main_window, 'pdf_manager'):
            self.pdf_layout_combo.setCurrentText(
                getattr(self.main_window.pdf_manager, 'pdf_layout_mode', 'tabbed'))
        if hasattr(self, 'recent_list'):
            recent = self.main_window.config_manager.get_recent_files()
            self.recent_list.clear()
            for path in recent:
                self.recent_list.addItem(os.path.basename(path))

    def _load_ui_settings(self):
        self._loading_settings = True
        try:
            if self.menu_lang_combo:
                self.menu_lang_combo.setCurrentText(self.main_window.menu_language)
            if self.rtl_check:
                self.rtl_check.setChecked(self.main_window.is_rtl)
            if self.auto_load_check:
                val = self.main_window.config_manager.get_config_value(
                    'ui', 'auto_load_last_file', 'True').lower() == 'true'
                self.auto_load_check.setChecked(val)
            if self.output_visible_check:
                ov = self.main_window.get_actual_output_state()
                self.output_visible_check.setChecked(ov)
                self.symbols_visible_check.setChecked(self.main_window.get_actual_symbols_state())
                self.commands_visible_check.setChecked(self.main_window.get_actual_commands_state())
                self.tree_visible_check.setChecked(self.main_window.get_actual_tree_state())
                self.bookmarks_visible_check.setChecked(self.main_window.get_actual_bookmarks_state())
                self.terminal_visible_check.setChecked(self.main_window.get_actual_terminal_state())
                self._update_sub_tab_states(ov)
            if self.line_numbers_check:
                self.line_numbers_check.setChecked(
                    getattr(self.main_window, 'is_line_numbers_visible', True))
            if self.fold_marker_check:
                self.fold_marker_check.setChecked(
                    getattr(self.main_window, 'is_fold_markers_visible', True))
        finally:
            self._loading_settings = False

    def _load_font_settings(self):
        fonts = self.main_window.get_current_font_settings()
        family = fonts.get('editor_font_family', 'Consolas')
        idx = self.editor_font_combo.findText(family)
        if idx >= 0:
            self.editor_font_combo.setCurrentIndex(idx)
        else:
            self.editor_font_combo.setCurrentFont(QFont(family))
        self.editor_font_spin.setValue(int(fonts.get('editor_font_size', 11)))
        ui_family = fonts.get('ui_font_family', 'Arial')
        idx = self.ui_font_combo.findText(ui_family)
        if idx >= 0:
            self.ui_font_combo.setCurrentIndex(idx)
        else:
            self.ui_font_combo.setCurrentFont(QFont(ui_family))
        self.toolbar_font_spin.setValue(int(fonts.get('toolbar_font_size', 10)))
    

    def _on_tab_selected(self, index):
        self._build_tab(index)

    def _build_tab(self, index):
        label = self.tab_widget.tabText(index)
        if label in self._tabs_initialized:
            return
        self._tabs_initialized.add(label)
        builder = self._tab_builders.get(label)
        if builder:
            built_widget = builder()
            # Replace the placeholder with the real widget
            if built_widget is not None:
                self.tab_widget.removeTab(index)
                self.tab_widget.insertTab(index, built_widget, label)
                self.tab_widget.setCurrentIndex(index)
            # Load settings for this tab immediately after building it
            loader = self._tab_loaders.get(label)
            if loader:
                loader()


    def _make_scrollable(self, inner_widget):
        """Wrap a widget in a QScrollArea so every tab is scrollable"""
        scroll = QScrollArea()
        scroll.setWidget(inner_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        return scroll

###
    # def create_ai_tab(self):
        # """Create AI configuration tab with Fetch Models and Custom Provider support"""
        # ai_tab = QWidget()
        # layout = QVBoxLayout(ai_tab)
        # layout.setContentsMargins(15, 15, 15, 15)
        # layout.setSpacing(10)

        # # Title
        # title = QLabel("AI Assistant Configuration")
        # title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        # layout.addWidget(title)

        # # Mode selection
        # mode_group = QGroupBox("AI Mode")
        # mode_layout = QVBoxLayout(mode_group)
        # self.ai_mode_combo = QComboBox()
        # self.ai_mode_combo.addItem("Offline (Rule-based, no internet)", "offline")
        # self.ai_mode_combo.addItem("Online (AI-powered, requires internet)", "online")
        # self.ai_mode_combo.currentIndexChanged.connect(self._on_ai_mode_changed)
        # mode_layout.addWidget(self.ai_mode_combo)
        # layout.addWidget(mode_group)

        # # Online AI settings (initially hidden)
        # self.online_ai_group = QGroupBox("Online AI Settings")
        # online_layout = QFormLayout(self.online_ai_group)

        # # Provider selection with Add Custom button
        # provider_layout = QHBoxLayout()
        # self.ai_provider_combo = QComboBox()
        # self._populate_default_providers()
        # self.ai_provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        # provider_layout.addWidget(self.ai_provider_combo, 1)

        # add_provider_btn = QPushButton("➕ Add Provider")
        # add_provider_btn.setMaximumWidth(120)
        # add_provider_btn.setToolTip("Add a custom AI provider not in the list")
        # add_provider_btn.clicked.connect(self._add_custom_provider)
        # provider_layout.addWidget(add_provider_btn)

        # online_layout.addRow("Provider:", provider_layout)

        # # API Key
        # self.ai_api_key = QLineEdit()
        # self.ai_api_key.setEchoMode(QLineEdit.Password)
        # self.ai_api_key.setPlaceholderText("Enter API key")
        # online_layout.addRow("API Key:", self.ai_api_key)

        # # Show/Hide API key button
        # key_btn_layout = QHBoxLayout()
        # self.show_key_btn = QPushButton("👁 Show")
        # self.show_key_btn.setMaximumWidth(80)
        # self.show_key_btn.clicked.connect(self._toggle_api_key_visibility)
        # key_btn_layout.addWidget(self.show_key_btn)
        # key_btn_layout.addStretch()
        # online_layout.addRow("", key_btn_layout)

        # # API Base URL (for custom providers)
        # self.ai_base_url = QLineEdit()
        # self.ai_base_url.setPlaceholderText("Custom API base URL (optional)")
        # self.ai_base_url.setToolTip("Override the default API endpoint URL")
        # online_layout.addRow("API Base URL:", self.ai_base_url)

        # # Fetch Models button + Model selection
        # model_layout = QHBoxLayout()
        # self.ai_model_combo = QComboBox()
        # self.ai_model_combo.setEditable(True)  # Allow manual model entry
        # self.ai_model_combo.setToolTip("Select a model or type a custom model name")
        # model_layout.addWidget(self.ai_model_combo, 1)

        # fetch_models_btn = QPushButton("🔄 Fetch Models")
        # fetch_models_btn.setMaximumWidth(120)
        # fetch_models_btn.setToolTip("Download current list of available models from the AI provider")
        # fetch_models_btn.clicked.connect(self._fetch_models)
        # model_layout.addWidget(fetch_models_btn)

        # online_layout.addRow("Model:", model_layout)

        # # Test connection button
        # test_btn = QPushButton("🔗 Test Connection")
        # test_btn.clicked.connect(self._test_ai_connection)
        # online_layout.addRow("", test_btn)

        # # Status label
        # self.ai_status_label = QLabel("Not configured")
        # self.ai_status_label.setStyleSheet("color: #666; padding: 5px;")
        # online_layout.addRow("Status:", self.ai_status_label)

        # layout.addWidget(self.online_ai_group)

        # # AI Assistant Setup group - for manual/custom setup
        # setup_group = QGroupBox("AI Assistant Setup (Manual)")
        # setup_layout = QFormLayout(setup_group)

        # setup_info = QLabel(
            # "Use this section to manually configure a custom AI provider\n"
            # "that is not in the predefined list above."
        # )
        # setup_info.setWordWrap(True)
        # setup_info.setStyleSheet("color: #555; font-style: italic; padding: 5px;")
        # setup_layout.addRow(setup_info)

        # self.custom_provider_name = QLineEdit()
        # self.custom_provider_name.setPlaceholderText("e.g., My Local LLM")
        # setup_layout.addRow("Provider Name:", self.custom_provider_name)

        # self.custom_api_url = QLineEdit()
        # self.custom_api_url.setPlaceholderText("e.g., http://localhost:11434/v1/chat/completions")
        # setup_layout.addRow("API Endpoint:", self.custom_api_url)

        # self.custom_api_key = QLineEdit()
        # self.custom_api_key.setEchoMode(QLineEdit.Password)
        # self.custom_api_key.setPlaceholderText("API key (if required)")
        # setup_layout.addRow("API Key:", self.custom_api_key)

        # self.custom_model_name = QLineEdit()
        # self.custom_model_name.setPlaceholderText("e.g., llama3, mistral, etc.")
        # setup_layout.addRow("Model Name:", self.custom_model_name)

        # add_custom_btn = QPushButton("➕ Add as New Provider")
        # add_custom_btn.setStyleSheet("""
            # QPushButton {
                # background-color: #4caf50; color: white;
                # border: none; border-radius: 4px; padding: 8px 16px;
            # }
            # QPushButton:hover { background-color: #45a049; }
        # """)
        # add_custom_btn.clicked.connect(self._add_manual_provider)
        # setup_layout.addRow("", add_custom_btn)

        # layout.addWidget(setup_group)

        # # Info section
        # info_group = QGroupBox("ℹ Information")
        # info_layout = QVBoxLayout(info_group)
        # info_text = QLabel(
            # "<b>Get API Keys:</b><br>"
            # "• Groq (Free): <a href='https://console.groq.com'>console.groq.com</a><br>"
            # "• Qwen: <a href='https://dashscope.console.aliyun.com'>dashscope.console.aliyun.com</a><br>"
            # "• DeepSeek: <a href='https://platform.deepseek.com'>platform.deepseek.com</a><br>"
            # "• OpenAI: <a href='https://platform.openai.com/api-keys'>platform.openai.com</a><br>"
            # "• HuggingFace: <a href='https://huggingface.co/settings/tokens'>huggingface.co/settings/tokens</a><br>"
            # "• Anthropic: <a href='https://console.anthropic.com'>console.anthropic.com</a><br>"
            # "• Google Gemini: <a href='https://aistudio.google.com/app/apikey'>aistudio.google.com</a><br>"
            # "• Mistral: <a href='https://console.mistral.ai'>console.mistral.ai</a><br>"
            # "• Cohere: <a href='https://dashboard.cohere.com/api-keys'>dashboard.cohere.com</a>"
        # )
        # info_text.setWordWrap(True)
        # info_text.setOpenExternalLinks(True)
        # self._apply_ai_info_style
        # info_layout.addWidget(info_text)
        # layout.addWidget(info_group)

        # layout.addStretch()

        # # Initially hide online settings
        # self.online_ai_group.setVisible(False)

        # scrollable = self._make_scrollable(ai_tab)
        # #self.tab_widget.addTab(scrollable, "AI Assistant")
        # return scrollable

    def create_ai_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        ai_tab = QWidget()
        layout = QVBoxLayout(ai_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(tr.get("ai_title", "AI Assistant Configuration"))
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(title)

        # Mode selection
        mode_group = QGroupBox(tr.get("ai_mode_group", "AI Mode"))
        mode_layout = QVBoxLayout(mode_group)
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItem(tr.get("ai_mode_offline", "Offline (Rule-based, no internet)"), "offline")
        self.ai_mode_combo.addItem(tr.get("ai_mode_online", "Online (AI-powered, requires internet)"), "online")
        self.ai_mode_combo.currentIndexChanged.connect(self._on_ai_mode_changed)
        mode_layout.addWidget(self.ai_mode_combo)
        layout.addWidget(mode_group)

        # Online AI settings
        self.online_ai_group = QGroupBox(tr.get("ai_online_group", "Online AI Settings"))
        online_layout = QFormLayout(self.online_ai_group)

        provider_layout = QHBoxLayout()
        self.ai_provider_combo = QComboBox()
        self._populate_default_providers()
        self.ai_provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.ai_provider_combo, 1)

        add_provider_btn = QPushButton(tr.get("ai_add_provider", "➕ Add Provider"))
        add_provider_btn.setMaximumWidth(120)
        add_provider_btn.setToolTip(tr.get("ai_add_provider_tooltip", "Add a custom AI provider not in the list"))
        add_provider_btn.clicked.connect(self._add_custom_provider)
        provider_layout.addWidget(add_provider_btn)

        online_layout.addRow(tr.get("ai_provider_label", "Provider:"), provider_layout)

        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.Password)
        self.ai_api_key.setPlaceholderText(tr.get("ai_api_key_label", "Enter API key"))
        online_layout.addRow(tr.get("ai_api_key_label", "API Key:"), self.ai_api_key)

        key_btn_layout = QHBoxLayout()
        self.show_key_btn = QPushButton(tr.get("ai_show_key", "👁 Show"))
        self.show_key_btn.setMaximumWidth(80)
        self.show_key_btn.clicked.connect(self._toggle_api_key_visibility)
        key_btn_layout.addWidget(self.show_key_btn)
        key_btn_layout.addStretch()
        online_layout.addRow("", key_btn_layout)

        self.ai_base_url = QLineEdit()
        self.ai_base_url.setPlaceholderText(tr.get("ai_base_url_label", "Custom API base URL (optional)"))
        self.ai_base_url.setToolTip(tr.get("ai_base_url_tooltip", "Override the default API endpoint URL"))
        online_layout.addRow(tr.get("ai_base_url_label", "API Base URL:"), self.ai_base_url)

        model_layout = QHBoxLayout()
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.setEditable(True)
        self.ai_model_combo.setToolTip(tr.get("ai_model_tooltip", "Select a model or type a custom model name"))
        model_layout.addWidget(self.ai_model_combo, 1)

        fetch_models_btn = QPushButton(tr.get("ai_fetch_models", "🔄 Fetch Models"))
        fetch_models_btn.setMaximumWidth(120)
        fetch_models_btn.setToolTip(tr.get("ai_fetch_models_tooltip", "Download current list of available models from the AI provider"))
        fetch_models_btn.clicked.connect(self._fetch_models)
        model_layout.addWidget(fetch_models_btn)

        online_layout.addRow(tr.get("ai_model_label", "Model:"), model_layout)

        test_btn = QPushButton(tr.get("ai_test_connection", "Test Connection"))
        test_btn.clicked.connect(self._test_ai_connection)
        online_layout.addRow("", test_btn)

        self.ai_status_label = QLabel(tr.get("ai_status_not_configured", "Not configured"))
        self.ai_status_label.setStyleSheet("color: #666; padding: 5px;")
        online_layout.addRow(tr.get("ai_status_label", "Status:"), self.ai_status_label)

        layout.addWidget(self.online_ai_group)

        # Manual setup group
        setup_group = QGroupBox(tr.get("ai_manual_group", "AI Assistant Setup (Manual)"))
        setup_layout = QFormLayout(setup_group)

        setup_info = QLabel(tr.get("ai_manual_info", "Use this section to manually configure a custom AI provider\nthat is not in the predefined list above."))
        setup_info.setWordWrap(True)
        setup_info.setStyleSheet("color: #555; font-style: italic; padding: 5px;")
        setup_layout.addRow(setup_info)

        self.custom_provider_name = QLineEdit()
        self.custom_provider_name.setPlaceholderText(tr.get("ai_custom_provider_name", "e.g., My Local LLM"))
        setup_layout.addRow(tr.get("ai_custom_provider_name", "Provider Name:"), self.custom_provider_name)

        self.custom_api_url = QLineEdit()
        self.custom_api_url.setPlaceholderText(tr.get("ai_custom_api_url", "e.g., http://localhost:11434/v1/chat/completions"))
        setup_layout.addRow(tr.get("ai_custom_api_url", "API Endpoint:"), self.custom_api_url)

        self.custom_api_key = QLineEdit()
        self.custom_api_key.setEchoMode(QLineEdit.Password)
        self.custom_api_key.setPlaceholderText(tr.get("ai_custom_api_key", "API key (if required)"))
        setup_layout.addRow(tr.get("ai_custom_api_key", "API Key:"), self.custom_api_key)

        self.custom_model_name = QLineEdit()
        self.custom_model_name.setPlaceholderText(tr.get("ai_custom_model", "e.g., llama3, mistral, etc."))
        setup_layout.addRow(tr.get("ai_custom_model", "Model Name:"), self.custom_model_name)

        add_custom_btn = QPushButton(tr.get("ai_add_manual_provider", "➕ Add as New Provider"))
        add_custom_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white;
                border: none; border-radius: 4px; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        add_custom_btn.clicked.connect(self._add_manual_provider)
        setup_layout.addRow("", add_custom_btn)

        layout.addWidget(setup_group)

        # Info group
        info_group = QGroupBox(tr.get("ai_info_group", "ℹ Information"))
        info_layout = QVBoxLayout(info_group)
        info_text = QLabel(tr.get("ai_info_text", "<b>Get API Keys:</b><br>• Groq (Free): <a href='https://console.groq.com'>console.groq.com</a><br>• Qwen: <a href='https://dashscope.console.aliyun.com'>dashscope.console.aliyun.com</a><br>• DeepSeek: <a href='https://platform.deepseek.com'>platform.deepseek.com</a><br>• OpenAI: <a href='https://platform.openai.com/api-keys'>platform.openai.com</a><br>• HuggingFace: <a href='https://huggingface.co/settings/tokens'>huggingface.co/settings/tokens</a><br>• Anthropic: <a href='https://console.anthropic.com'>console.anthropic.com</a><br>• Google Gemini: <a href='https://aistudio.google.com/app/apikey'>aistudio.google.com</a><br>• Mistral: <a href='https://console.mistral.ai'>console.mistral.ai</a><br>• Cohere: <a href='https://dashboard.cohere.com/api-keys'>dashboard.cohere.com</a>"))
        info_text.setWordWrap(True)
        info_text.setOpenExternalLinks(True)
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)

        layout.addStretch()
        self.online_ai_group.setVisible(False)

        scrollable = self._make_scrollable(ai_tab)
        return scrollable

    def _apply_ai_info_style(self):
        """Apply the current theme's colors to the AI info section label."""
        if not hasattr(self, 'ai_info_text'):
            return
        from style_manager import get_settings_panel_style
        sp = get_settings_panel_style()
        self.ai_info_text.setStyleSheet(
            f"padding: 10px;"
            f"background: {sp['info_bg']};"
            f"color: {sp['info_color']};"
            f"border: 1px solid {sp['info_border']};"
            f"border-radius: 4px;"
        )
        

    def _populate_default_providers(self):
        """Populate provider combo with default + extended providers"""
        providers = [
            ("Groq (Fast & Free)", "groq"),
            ("Qwen - Alibaba Cloud (Paid)", "qwen"),
            ("DeepSeek (Paid)", "deepseek"),
            ("OpenAI ChatGPT (Paid)", "openai"),
            ("Hugging Face (Free, no key needed)", "huggingface"),
            ("Anthropic Claude (Paid)", "anthropic"),
            ("Google Gemini (Paid)", "google"),
            ("Mistral AI (Paid)", "mistral"),
            ("Cohere (Free tier available)", "cohere"),
            ("Together AI (Free tier)", "together"),
            ("OpenRouter (Multi-provider)", "openrouter"),
            ("Ollama (Local)", "ollama"),
        ]
        self.ai_provider_combo.clear()
        for name, key in providers:
            self.ai_provider_combo.addItem(name, key)

        # Load any custom providers from config
        try:
            custom_providers = self.main_window.config_manager.get_config_value(
                'ai', 'custom_providers', '[]')
            if isinstance(custom_providers, str):
                import json
                custom_providers = json.loads(custom_providers)
            for cp in custom_providers:
                self.ai_provider_combo.addItem(
                    f"{cp['name']} (Custom)", f"custom_{cp['id']}")
        except Exception:
            pass

    def _on_ai_mode_changed(self, index):
        mode = self.ai_mode_combo.currentData()
        self.online_ai_group.setVisible(mode == "online")
        if mode == "online":
            self._update_models_list()

    def _on_provider_changed(self, index):
        self._update_models_list()
        self._update_api_key_requirement()

    def _update_models_list(self):
        """Update available models based on provider"""
        provider = self.ai_provider_combo.currentData()
        if provider is None:
            return

        models = {
            "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768",
                      "llama-3.1-8b-instant", "gemma2-9b-it"],
            "qwen": ["qwen-turbo", "qwen-plus", "qwen-max",
                      "qwen-turbo-latest", "qwen-plus-latest"],
            "deepseek": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo",
                        "gpt-4-turbo", "o1-mini", "o1-preview"],
            "huggingface": ["microsoft/DialoGPT-large", "google/flan-t5-xxl",
                            "mistralai/Mistral-7B-Instruct-v0.2"],
            "anthropic": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229",
                          "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"],
            "google": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            "mistral": ["mistral-large-latest", "mistral-medium-latest",
                        "mistral-small-latest", "open-mistral-nemo"],
            "cohere": ["command-r-plus", "command-r", "command-light"],
            "together": ["meta-llama/Llama-3-70b-chat-hf",
                         "mistralai/Mixtral-8x7B-Instruct-v0.1"],
            "openrouter": ["openai/gpt-4o", "anthropic/claude-3-opus",
                           "google/gemini-pro", "meta-llama/llama-3-70b-instruct"],
            "ollama": ["llama3", "mistral", "codellama", "phi3"],
        }

        # Save current model text before clearing
        current_model = self.ai_model_combo.currentText()

        self.ai_model_combo.clear()
        provider_models = models.get(provider, [])
        self.ai_model_combo.addItems(provider_models)

        # Restore if it was in the list
        if current_model:
            idx = self.ai_model_combo.findText(current_model)
            if idx >= 0:
                self.ai_model_combo.setCurrentIndex(idx)

    def _update_api_key_requirement(self):
        provider = self.ai_provider_combo.currentData()
        no_key_providers = ["huggingface", "ollama"]
        if provider in no_key_providers:
            self.ai_api_key.setPlaceholderText("Optional (better rate limits)")
            self.ai_api_key.setStyleSheet("")
        else:
            self.ai_api_key.setPlaceholderText("Required")
            self.ai_api_key.setStyleSheet("border: 1px solid #ff6b6b;")

    def _toggle_api_key_visibility(self):
        if self.ai_api_key.echoMode() == QLineEdit.Password:
            self.ai_api_key.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText("🔒 Hide")
        else:
            self.ai_api_key.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText("👁 Show")

    def _fetch_models(self):
        """Fetch available models from the AI provider's API"""
        provider = self.ai_provider_combo.currentData()
        api_key = self.ai_api_key.text().strip()
        base_url = self.ai_base_url.text().strip() if hasattr(self, 'ai_base_url') else ""

        if not api_key and provider not in ("huggingface", "ollama"):
            QMessageBox.warning(self, "Missing API Key",
                "Please enter your API key first to fetch models.")
            return

        self.ai_status_label.setText("⏳ Fetching models...")
        self.ai_status_label.setStyleSheet("color: #ff9800;")
        QApplication.processEvents()

        try:
            import requests

            # Define model list endpoints per provider
            endpoints = {
                "groq": "https://api.groq.com/openai/v1/models",
                "openai": "https://api.openai.com/v1/models",
                "deepseek": "https://api.deepseek.com/v1/models",
                "mistral": "https://api.mistral.ai/v1/models",
                "together": "https://api.together.xyz/v1/models",
                "openrouter": "https://openrouter.ai/api/v1/models",
                "ollama": "http://localhost:11434/api/tags",
                "anthropic": None,  # No list endpoint
                "google": None,
                "qwen": None,
                "huggingface": None,
                "cohere": None,
            }

            url = base_url if base_url else endpoints.get(provider)

            if not url:
                QMessageBox.information(self, "Not Supported",
                    f"Automatic model fetching is not supported for {provider}.\n"
                    "You can type a model name manually in the Model field.")
                self.ai_status_label.setText("ℹ Manual model entry required")
                self.ai_status_label.setStyleSheet("color: #666;")
                return

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                QMessageBox.warning(self, "Fetch Failed",
                    f"Failed to fetch models.\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text[:200]}")
                self.ai_status_label.setText(f"❌ Fetch failed: {response.status_code}")
                self.ai_status_label.setStyleSheet("color: #f44336;")
                return

            result = response.json()
            model_ids = []

            # Parse response based on provider format
            if provider == "ollama":
                # Ollama uses different format
                models_data = result.get("models", [])
                model_ids = [m.get("name", "") for m in models_data if m.get("name")]
            elif provider == "openrouter":
                models_data = result.get("data", [])
                model_ids = [m.get("id", "") for m in models_data if m.get("id")]
            else:
                # OpenAI-compatible format (groq, openai, deepseek, mistral, together)
                models_data = result.get("data", [])
                model_ids = [m.get("id", "") for m in models_data if m.get("id")]

            if not model_ids:
                QMessageBox.information(self, "No Models",
                    "No models were returned by the API.")
                self.ai_status_label.setText("⚠ No models found")
                self.ai_status_label.setStyleSheet("color: #ff9800;")
                return

            # Sort alphabetically
            model_ids.sort()

            # Save current selection
            current_model = self.ai_model_combo.currentText()

            # Update combo
            self.ai_model_combo.clear()
            self.ai_model_combo.addItems(model_ids)

            # Try to restore selection
            if current_model:
                idx = self.ai_model_combo.findText(current_model)
                if idx >= 0:
                    self.ai_model_combo.setCurrentIndex(idx)

            self.ai_status_label.setText(f"✅ Fetched {len(model_ids)} models")
            self.ai_status_label.setStyleSheet("color: #4caf50;")

            QMessageBox.information(self, "Models Fetched",
                f"Successfully fetched {len(model_ids)} models from {provider}.")

        except ImportError:
            QMessageBox.critical(self, "Missing Dependency",
                "The 'requests' library is required.\nInstall it: pip install requests")
        except requests.exceptions.ConnectionError:
            QMessageBox.warning(self, "Connection Error",
                "Could not connect to the API endpoint.\nCheck your internet connection.")
            self.ai_status_label.setText("❌ Connection error")
            self.ai_status_label.setStyleSheet("color: #f44336;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch models:\n{str(e)}")
            self.ai_status_label.setText(f"❌ Error: {str(e)[:50]}")
            self.ai_status_label.setStyleSheet("color: #f44336;")

    def _add_custom_provider(self):
        """Quick-add a custom provider via dialog"""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom AI Provider")
        dialog.setMinimumWidth(450)
        form = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., My Custom Provider")
        form.addRow("Provider Name:", name_edit)

        url_edit = QLineEdit()
        url_edit.setPlaceholderText("e.g., https://api.example.com/v1/chat/completions")
        form.addRow("API Endpoint:", url_edit)

        key_edit = QLineEdit()
        key_edit.setEchoMode(QLineEdit.Password)
        key_edit.setPlaceholderText("API key (leave empty if not needed)")
        form.addRow("API Key:", key_edit)

        model_edit = QLineEdit()
        model_edit.setPlaceholderText("e.g., my-model-v1")
        form.addRow("Default Model:", model_edit)

        models_url_edit = QLineEdit()
        models_url_edit.setPlaceholderText("e.g., https://api.example.com/v1/models (optional)")
        form.addRow("Models List URL:", models_url_edit)

        info = QLabel("The provider will use OpenAI-compatible API format.\n"
                      "You can fetch models later using the Fetch Models button.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-style: italic;")
        form.addRow(info)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            url = url_edit.text().strip()
            model = model_edit.text().strip()

            if not name:
                QMessageBox.warning(self, "Error", "Provider name is required.")
                return
            if not url:
                QMessageBox.warning(self, "Error", "API endpoint URL is required.")
                return

            # Generate unique ID
            import hashlib
            provider_id = hashlib.md5(name.encode()).hexdigest()[:8]

            # Save to config
            try:
                custom_providers = self.main_window.config_manager.get_config_value(
                    'ai', 'custom_providers', '[]')
                if isinstance(custom_providers, str):
                    import json
                    custom_providers = json.loads(custom_providers)

                custom_providers.append({
                    'id': provider_id,
                    'name': name,
                    'url': url,
                    'api_key': key_edit.text().strip(),
                    'model': model,
                    'models_url': models_url_edit.text().strip(),
                })

                import json
                self.main_window.config_manager.set_config_value(
                    'ai', 'custom_providers', json.dumps(custom_providers))

                # Add to combo
                combo_key = f"custom_{provider_id}"
                self.ai_provider_combo.addItem(f"{name} (Custom)", combo_key)
                # Select it
                idx = self.ai_provider_combo.findData(combo_key)
                if idx >= 0:
                    self.ai_provider_combo.setCurrentIndex(idx)

                # Set fields
                self.ai_api_key.setText(key_edit.text().strip())
                self.ai_base_url.setText(url)
                if model:
                    self.ai_model_combo.clear()
                    self.ai_model_combo.addItem(model)

                QMessageBox.information(self, "Success",
                    f"Provider '{name}' added successfully!")

            except Exception as e:
                QMessageBox.critical(self, "Error",
                    f"Failed to save custom provider:\n{str(e)}")

    def _add_manual_provider(self):
        """Add provider from the manual setup section"""
        name = self.custom_provider_name.text().strip()
        url = self.custom_api_url.text().strip()
        api_key = self.custom_api_key.text().strip()
        model = self.custom_model_name.text().strip()

        if not name:
            QMessageBox.warning(self, "Error", "Provider name is required.")
            return
        if not url:
            QMessageBox.warning(self, "Error", "API endpoint URL is required.")
            return

        import hashlib
        provider_id = hashlib.md5(name.encode()).hexdigest()[:8]

        try:
            custom_providers = self.main_window.config_manager.get_config_value(
                'ai', 'custom_providers', '[]')
            if isinstance(custom_providers, str):
                import json
                custom_providers = json.loads(custom_providers)

            custom_providers.append({
                'id': provider_id,
                'name': name,
                'url': url,
                'api_key': api_key,
                'model': model,
                'models_url': '',
            })

            import json
            self.main_window.config_manager.set_config_value(
                'ai', 'custom_providers', json.dumps(custom_providers))

            combo_key = f"custom_{provider_id}"
            self.ai_provider_combo.addItem(f"{name} (Custom)", combo_key)
            idx = self.ai_provider_combo.findData(combo_key)
            if idx >= 0:
                self.ai_provider_combo.setCurrentIndex(idx)

            self.ai_api_key.setText(api_key)
            self.ai_base_url.setText(url)
            if model:
                self.ai_model_combo.clear()
                self.ai_model_combo.addItem(model)

            # Clear the manual setup fields
            self.custom_provider_name.clear()
            self.custom_api_url.clear()
            self.custom_api_key.clear()
            self.custom_model_name.clear()

            QMessageBox.information(self, "Success",
                f"Provider '{name}' added and selected!")

        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to save custom provider:\n{str(e)}")

    def _test_ai_connection(self):
        """Test AI connection"""
        mode = self.ai_mode_combo.currentData()
        if mode == "offline":
            QMessageBox.information(self, "Offline Mode",
                "Offline mode doesn't require connection.")
            return

        provider = self.ai_provider_combo.currentData()
        api_key = self.ai_api_key.text().strip()

        if not api_key and provider not in ("huggingface", "ollama"):
            QMessageBox.warning(self, "Missing API Key",
                "Please enter your API key.")
            return

        self.ai_status_label.setText("Testing connection...")
        self.ai_status_label.setStyleSheet("color: #ff9800;")
        QApplication.processEvents()

        try:
            from online_ai_provider import OnlineAIProvider
            provider_obj = OnlineAIProvider()
            provider_obj.set_provider(provider, api_key,
                                      self.ai_model_combo.currentText())
            response, error = provider_obj.query("Hello", max_tokens=10)
            if error:
                self.ai_status_label.setText(f"❌ Failed: {error}")
                self.ai_status_label.setStyleSheet("color: #f44336;")
                QMessageBox.warning(self, "Connection Failed", f"Error: {error}")
            else:
                self.ai_status_label.setText("✅ Connected successfully")
                self.ai_status_label.setStyleSheet("color: #4caf50;")
                QMessageBox.information(self, "Success", "Connection successful!")
        except Exception as e:
            self.ai_status_label.setText(f"❌ Error: {str(e)}")
            self.ai_status_label.setStyleSheet("color: #f44336;")
            QMessageBox.critical(self, "Error", str(e))
###
    # Add this method to the SettingsDialog class
    # def create_completion_tab(self):
        # """Create the CWL completion settings tab"""
        # tab = QWidget()
        # layout = QVBoxLayout(tab)
        # layout.setContentsMargins(10, 10, 10, 10)
        
        # # Header
        # header = QLabel("<b>LaTeX Autocompletion Settings</b>")
        # header.setStyleSheet("font-size: 12px; padding: 5px;")
        # layout.addWidget(header)
        
        # # General completion settings group
        # general_group = QGroupBox("General Settings")
        # general_layout = QGridLayout(general_group)
        
        # # Enable completion checkbox
        # self.completion_enabled_check = QCheckBox("Enable LaTeX autocompletion")
        # self.completion_enabled_check.setChecked(True)
        # self.completion_enabled_check.setToolTip("Enable or disable autocompletion globally")
        # general_layout.addWidget(self.completion_enabled_check, 0, 0, 1, 2)
        
        # # Fuzzy matching checkbox
        # self.fuzzy_matching_check = QCheckBox("Enable fuzzy matching (VS Code style)")
        # self.fuzzy_matching_check.setChecked(True)
        # self.fuzzy_matching_check.setToolTip("Allow partial matches like 'frc' matching '\\frac'")
        # general_layout.addWidget(self.fuzzy_matching_check, 1, 0, 1, 2)
        
        # # Minimum prefix length
        # prefix_label = QLabel("Minimum prefix length:")
        # self.min_prefix_spin = QSpinBox()
        # self.min_prefix_spin.setRange(1, 5)
        # self.min_prefix_spin.setValue(2)
        # self.min_prefix_spin.setToolTip("Number of characters after \\ before showing completions")
        # general_layout.addWidget(prefix_label, 2, 0)
        # general_layout.addWidget(self.min_prefix_spin, 2, 1)
        
        # # Show mode indicators
        # self.show_mode_indicators_check = QCheckBox("Show mode indicators ([m] for math, [t] for text)")
        # self.show_mode_indicators_check.setChecked(True)
        # general_layout.addWidget(self.show_mode_indicators_check, 3, 0, 1, 2)
        
        # # Auto-enable includes
        # self.auto_enable_includes_check = QCheckBox("Automatically enable #include dependencies")
        # self.auto_enable_includes_check.setChecked(True)
        # self.auto_enable_includes_check.setToolTip("When enabling a .cwl file, also enable files it includes")
        # general_layout.addWidget(self.auto_enable_includes_check, 4, 0, 1, 2)
        
        # layout.addWidget(general_group)
        
        # # CWL Files selection group
        # files_group = QGroupBox("Completion Files (.cwl)")
        # files_layout = QVBoxLayout(files_group)
        
        # # Defer the heavy CWL widget until needed
        # self._cwl_widget_placeholder = layout
        # QTimer.singleShot(0, self._load_cwl_widget)
        
        # scrollable = self._make_scrollable(tab)
        # #self.tab_widget.addTab(scrollable, "Completion")  
        # return scrollable           

    def create_completion_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        header = QLabel(f"<b>{tr.get('completion_header', 'LaTeX Autocompletion Settings')}</b>")
        header.setStyleSheet("font-size: 12px; padding: 5px;")
        layout.addWidget(header)

        general_group = QGroupBox(tr.get("completion_general_group", "General Settings"))
        general_layout = QGridLayout(general_group)

        self.completion_enabled_check = QCheckBox(tr.get("completion_enable", "Enable LaTeX autocompletion"))
        self.completion_enabled_check.setChecked(True)
        self.completion_enabled_check.setToolTip(tr.get("completion_enable_tooltip", "Enable or disable autocompletion globally"))
        general_layout.addWidget(self.completion_enabled_check, 0, 0, 1, 2)

        self.fuzzy_matching_check = QCheckBox(tr.get("completion_fuzzy", "Enable fuzzy matching (VS Code style)"))
        self.fuzzy_matching_check.setChecked(True)
        self.fuzzy_matching_check.setToolTip(tr.get("completion_fuzzy_tooltip", "Allow partial matches like 'frc' matching '\\frac'"))
        general_layout.addWidget(self.fuzzy_matching_check, 1, 0, 1, 2)

        prefix_label = QLabel(tr.get("completion_min_prefix", "Minimum prefix length:"))
        self.min_prefix_spin = QSpinBox()
        self.min_prefix_spin.setRange(1, 5)
        self.min_prefix_spin.setValue(2)
        self.min_prefix_spin.setToolTip(tr.get("completion_min_prefix_tooltip", "Number of characters after \\ before showing completions"))
        general_layout.addWidget(prefix_label, 2, 0)
        general_layout.addWidget(self.min_prefix_spin, 2, 1)

        self.show_mode_indicators_check = QCheckBox(tr.get("completion_mode_indicators", "Show mode indicators ([m] for math, [t] for text)"))
        self.show_mode_indicators_check.setChecked(True)
        general_layout.addWidget(self.show_mode_indicators_check, 3, 0, 1, 2)

        self.auto_enable_includes_check = QCheckBox(tr.get("completion_auto_includes", "Automatically enable #include dependencies"))
        self.auto_enable_includes_check.setChecked(True)
        self.auto_enable_includes_check.setToolTip(tr.get("completion_auto_includes_tooltip", "When enabling a .cwl file, also enable files it includes"))
        general_layout.addWidget(self.auto_enable_includes_check, 4, 0, 1, 2)

        layout.addWidget(general_group)

        files_group = QGroupBox(tr.get("completion_files_group", "Completion Files (.cwl)"))
        files_layout = QVBoxLayout(files_group)
        layout.addWidget(files_group)

        self._cwl_widget_placeholder = files_layout
        QTimer.singleShot(0, self._load_cwl_widget)

        scrollable = self._make_scrollable(tab)
        return scrollable
        
    def _load_cwl_widget(self):
        if not hasattr(self.main_window, 'cwl_manager'):
            from cwl_manager import CWLManager
            self.main_window.cwl_manager = CWLManager()
        self.cwl_settings_widget = CompletionSettingsWidget(
            self.main_window.cwl_manager
        )
        self._cwl_widget_placeholder.addWidget(self.cwl_settings_widget)

    def _on_cwl_completion_changed(self):
        """Handle changes to CWL completion settings"""
        self._update_completion_stats()
        if hasattr(self, 'on_setting_changed'):
            self.on_setting_changed()


    def _update_completion_stats(self):
        """Update completion statistics display"""
        if self.completion_stats_label is None:
            return
        
        if hasattr(self.main_window, 'cwl_manager'):
            cwl_mgr = self.main_window.cwl_manager
            cmd_count = cwl_mgr.get_command_count()
            file_count = cwl_mgr.get_enabled_file_count()
            total_files = len(cwl_mgr.available_files())
            
            self.completion_stats_label.setText(
                f"Commands: {cmd_count} | Enabled Files: {file_count}/{total_files}"
            )
        else:
            self.completion_stats_label.setText("Commands: 0 | Enabled Files: 0")
        
    def load_completion_settings(self):
        """Load completion settings from config into UI"""
        # Check if widgets exist first
        if self.completion_enabled_check is None:
            #print("⚠️ Completion widgets not yet created, skipping load")
            return
        
        if not hasattr(self.main_window, 'config_manager'):
            return
        
        config_mgr = self.main_window.config_manager
        
        try:
            enabled = config_mgr.get_config_value('cwl_completion', 'enabled', 'True').lower() == 'true'
            self.completion_enabled_check.setChecked(enabled)
        except Exception as e:
            print(f"Error loading completion_enabled: {e}")
        
        try:
            if self.fuzzy_matching_check is not None:
                fuzzy = config_mgr.get_config_value('cwl_completion', 'fuzzy_matching', 'True').lower() == 'true'
                self.fuzzy_matching_check.setChecked(fuzzy)
        except Exception as e:
            print(f"Error loading fuzzy_matching: {e}")
        
        try:
            if self.min_prefix_spin is not None:
                prefix_len = int(config_mgr.get_config_value('cwl_completion', 'min_prefix_length', '2'))
                self.min_prefix_spin.setValue(prefix_len)
        except (ValueError, Exception) as e:
            if self.min_prefix_spin is not None:
                self.min_prefix_spin.setValue(2)
        
        try:
            if self.show_mode_indicators_check is not None:
                show_mode = config_mgr.get_config_value('cwl_completion', 'show_mode_indicators', 'True').lower() == 'true'
                self.show_mode_indicators_check.setChecked(show_mode)
        except Exception as e:
            print(f"Error loading show_mode_indicators: {e}")
        
        try:
            if self.auto_enable_includes_check is not None:
                auto_includes = config_mgr.get_config_value('cwl_completion', 'auto_enable_includes', 'True').lower() == 'true'
                self.auto_enable_includes_check.setChecked(auto_includes)
        except Exception as e:
            print(f"Error loading auto_enable_includes: {e}")
        
        self._update_completion_stats()
    
    def _apply_completion_enabled_state(self, enabled):
        """Apply completion enabled/disabled state to all editors immediately"""
        if not hasattr(self.main_window, 'editor_manager'):
            return
        
        if hasattr(self.main_window.editor_manager, 'editor_files'):
            for file_path, editor_data in self.main_window.editor_manager.editor_files.items():
                editor = editor_data.get('editor')
                if editor:
                    # Disable/enable the completer
                    if hasattr(editor, '_cwl_completer') and editor._cwl_completer:
                        if enabled:
                            editor._cwl_completer.enable()
                        else:
                            editor._cwl_completer.disable()
                            editor._cwl_completer.hide_popup()
                        
    def save_completion_settings(self):
        """Save completion settings to config"""
        if self.completion_enabled_check is None:
            return
        
        if not hasattr(self.main_window, 'config_manager'):
            return
        
        config_mgr = self.main_window.config_manager
        
        if not config_mgr.config.has_section('cwl_completion'):
            config_mgr.config.add_section('cwl_completion')
        
        try:
            # Save enabled state
            enabled = self.completion_enabled_check.isChecked()
            config_mgr.set_config_value('cwl_completion', 'enabled', str(enabled))
            
            # ✅ IMMEDIATELY apply to all editors
            self._apply_completion_enabled_state(enabled)
        
            if self.completion_enabled_check is not None:
                config_mgr.set_config_value('cwl_completion', 'enabled', 
                                           str(self.completion_enabled_check.isChecked()))
            
            if self.fuzzy_matching_check is not None:
                config_mgr.set_config_value('cwl_completion', 'fuzzy_matching',
                                           str(self.fuzzy_matching_check.isChecked()))
            
            if self.min_prefix_spin is not None:
                config_mgr.set_config_value('cwl_completion', 'min_prefix_length',
                                           str(self.min_prefix_spin.value()))
            
            if self.show_mode_indicators_check is not None:
                config_mgr.set_config_value('cwl_completion', 'show_mode_indicators',
                                           str(self.show_mode_indicators_check.isChecked()))
            
            if self.auto_enable_includes_check is not None:
                config_mgr.set_config_value('cwl_completion', 'auto_enable_includes',
                                           str(self.auto_enable_includes_check.isChecked()))
            
            # Save enabled files
            if hasattr(self.main_window, 'cwl_manager'):
                cwl_mgr = self.main_window.cwl_manager
                config_mgr.set_config_value('cwl_completion', 'enabled_files',
                                           ','.join(cwl_mgr.enabled_files))
            
            self._apply_completion_settings_to_editors()
            
        except Exception as e:
            print(f"Error saving completion settings: {e}")


    def _apply_completion_settings_to_editors(self):
        """Apply completion settings to all open editors"""
        if not hasattr(self.main_window, 'editor_manager'):
            return
        
        fuzzy = self.fuzzy_matching_check.isChecked() if self.fuzzy_matching_check else True
        min_prefix = self.min_prefix_spin.value() if self.min_prefix_spin else 2
        enabled = self.completion_enabled_check.isChecked() if self.completion_enabled_check else True
        
        if hasattr(self.main_window.editor_manager, 'editor_files'):
            for file_path, editor_data in self.main_window.editor_manager.editor_files.items():
                editor = editor_data.get('editor')
                if editor:
                    if hasattr(editor, 'set_completion_enabled'):
                        editor.set_completion_enabled(enabled)
                    
                    if hasattr(editor, 'latex_completer') and editor.latex_completer:
                        editor.latex_completer.set_fuzzy_matching(fuzzy)
                        editor.latex_completer.set_min_prefix_length(min_prefix)
                        editor.latex_completer.refresh()
                    
###
    # def create_color_tab(self):
        # """Create the syntax highlighting color settings tab"""
        # color_tab = QWidget()
        # layout = QVBoxLayout(color_tab)
        # desc_label = QLabel("Customize LaTeX syntax highlighting colors:")
        # desc_label.setWordWrap(True)
        # layout.addWidget(desc_label)

        # scroll = QScrollArea()
        # scroll.setWidgetResizable(True)
        # scroll_widget = QWidget()
        # scroll_layout = QFormLayout(scroll_widget)

        # color_categories = [
            # ("command", "Commands (\\section, \\textbf, etc.)", QColor(0, 0, 139)),
            # ("environment", "Environments (\\begin{}, \\end{})", QColor(139, 0, 139)),
            # ("inline_math", "Inline Math ($...$)", QColor(0, 100, 0)),
            # ("display_math", "Display Math (\\[...\\], $$...$$)", QColor(0, 128, 0)),
            # ("brace", "Braces and Brackets ({}, [])", QColor(139, 0, 0)),
            # ("paren",       "Parentheses (())",  QColor(70, 200, 200)),  # ← add this            
            # ("parameter", "Parameters ({content})", QColor(255, 140, 0)),
            # ("optional", "Optional Parameters ([content])", QColor(184, 134, 11)),
            # ("comment", "Comments (% ...)", QColor(128, 128, 128)),
            # ("special", "Special Characters (\\&, \\$, etc.)", QColor(128, 0, 128)),
            # ("reference", "Labels & References (\\ref, \\cite)", QColor(25, 25, 112)),
        # ]

        # bg_categories = [
            # ("inline_math_bg", "Inline Math Background", QColor(0, 0, 0, 0)),
            # ("display_math_bg", "Display Math Background", QColor(0, 0, 0, 0)),
        # ]

        # for key, label, default_color in color_categories:
            # color_button = QPushButton()
            # color_button.setFixedSize(100, 30)
            # # Remove the plain setStyleSheet – the _apply_color_button_style will handle it
            # self._apply_color_button_style(color_button, default_color)

            # self.color_widgets[key] = {
                # 'button': color_button,
                # 'color': default_color,
                # 'type': 'foreground'
            # }
            # # ✅ Connect button to open color dialog
            # color_button.clicked.connect(lambda checked, k=key, btn=color_button: self.choose_color(k, btn))
            # scroll_layout.addRow(label + ":", color_button)

        # separator = QFrame()
        # separator.setFrameShape(QFrame.HLine)
        # scroll_layout.addRow(separator)

        # for key, label, default_color in bg_categories:
            # color_button = QPushButton()
            # color_button.setFixedSize(100, 30)
            # self._apply_color_button_style(color_button, default_color)
            # self.color_widgets[key] = {
                # 'button': color_button,
                # 'color': default_color,
                # 'type': 'background'
            # }
            # color_button.clicked.connect(lambda checked, k=key, btn=color_button: self.choose_color(k, btn))
            # scroll_layout.addRow(label + ":", color_button)

        # scroll.setWidget(scroll_widget)
        # layout.addWidget(scroll)

        # reset_layout = QHBoxLayout()
        # reset_button = QPushButton("Reset to Defaults")
        # reset_button.clicked.connect(self.reset_colors_to_default)
        # reset_layout.addStretch()
        # reset_layout.addWidget(reset_button)
        # layout.addLayout(reset_layout)

        # scrollable = self._make_scrollable(color_tab)
        # #self.tab_widget.addTab(scrollable, "Colors")
        # return scrollable  

    def create_color_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        color_tab = QWidget()
        layout = QVBoxLayout(color_tab)
        desc_label = QLabel(tr.get("colors_description", "Customize LaTeX syntax highlighting colors:"))
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QFormLayout(scroll_widget)

        # The keys below must match those used in the translation file
        color_categories = [
            ("command",      "colors_command",      QColor(0, 0, 139)),
            ("environment",  "colors_environment",  QColor(139, 0, 139)),
            ("inline_math",  "colors_inline_math",  QColor(0, 100, 0)),
            ("display_math", "colors_display_math", QColor(0, 128, 0)),
            ("brace",        "colors_brace",        QColor(139, 0, 0)),
            ("paren",        "colors_paren",        QColor(70, 200, 200)),
            ("parameter",    "colors_parameter",    QColor(255, 140, 0)),
            ("optional",     "colors_optional",     QColor(184, 134, 11)),
            ("comment",      "colors_comment",      QColor(128, 128, 128)),
            ("special",      "colors_special",      QColor(128, 0, 128)),
            ("reference",    "colors_reference",    QColor(25, 25, 112)),
        ]

        bg_categories = [
            ("inline_math_bg",  "colors_inline_math_bg",  QColor(0, 0, 0, 0)),
            ("display_math_bg", "colors_display_math_bg", QColor(0, 0, 0, 0)),
        ]

        for key, trans_key, default_color in color_categories:
            color_button = QPushButton()
            color_button.setFixedSize(100, 30)
            self._apply_color_button_style(color_button, default_color)
            self.color_widgets[key] = {
                'button': color_button,
                'color': default_color,
                'type': 'foreground'
            }
            color_button.clicked.connect(lambda checked, k=key, btn=color_button: self.choose_color(k, btn))
            scroll_layout.addRow(tr.get(trans_key, key) + ":", color_button)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        scroll_layout.addRow(separator)

        for key, trans_key, default_color in bg_categories:
            color_button = QPushButton()
            color_button.setFixedSize(100, 30)
            self._apply_color_button_style(color_button, default_color)
            self.color_widgets[key] = {
                'button': color_button,
                'color': default_color,
                'type': 'background'
            }
            color_button.clicked.connect(lambda checked, k=key, btn=color_button: self.choose_color(k, btn))
            scroll_layout.addRow(tr.get(trans_key, key) + ":", color_button)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        reset_layout = QHBoxLayout()
        reset_button = QPushButton(tr.get("colors_reset_defaults", "Reset to Defaults"))
        reset_button.clicked.connect(self.reset_colors_to_default)
        reset_layout.addStretch()
        reset_layout.addWidget(reset_button)
        layout.addLayout(reset_layout)

        scrollable = self._make_scrollable(color_tab)
        return scrollable        
    
    def choose_color(self, key, button):
        current_color = self.color_widgets[key]['color']

        if self.color_widgets[key]['type'] == 'background':
            msg = QMessageBox(self)
            msg.setWindowTitle(f"Color for {key}")
            msg.setText("Choose a background color or set it to transparent.")
            transparent_btn = msg.addButton("Transparent", QMessageBox.ActionRole)
            pick_btn = msg.addButton("Pick Color…", QMessageBox.ActionRole)
            msg.addButton("Cancel", QMessageBox.RejectRole)
            msg.exec_()
            clicked = msg.clickedButton()

            if clicked == transparent_btn:
                color = QColor(0, 0, 0, 0)
                self.color_widgets[key]['color'] = color
                self._apply_color_button_style(button, color)
                return
            elif clicked == pick_btn:
                # If current color is transparent, start the picker with
                # a visible default so the user can actually see and pick a color
                picker_start_color = (
                    #QColor(240, 255, 240)  # default light green
                    QColor(0, 0, 0, 0)
                    if current_color.alpha() == 0
                    else current_color
                )
                color = QColorDialog.getColor(
                    picker_start_color, self, f"Choose Color for {key}",
                    QColorDialog.ShowAlphaChannel
                )
                if color.isValid():
                    self.color_widgets[key]['color'] = color
                    self._apply_color_button_style(button, color)
                return
            else:
                return  # Cancel

        # Foreground colors
        color = QColorDialog.getColor(current_color, self, f"Choose Color for {key}")
        if color.isValid():
            self.color_widgets[key]['color'] = color
            self._apply_color_button_style(button, color)
            self._colors_dirty = True   # mark as changed

            
    def _apply_color_button_style(self, button, color: QColor):
        name = f"color_btn_{id(button)}"
        button.setObjectName(name)

        is_transparent = (color.alpha() == 0)

        if is_transparent:
            button.setText("transparent")
            bg_css = "background-color: #ffffff;"
            text_css = "color: #aaaaaa; font-style: italic;"
        else:
            button.setText("")
            bg_css = f"background-color: {color.name()};"
            text_css = ""

        button.blockSignals(True)
        try:
            button.setStyleSheet(
                f"QPushButton#{name} {{"
                f" {bg_css}"
                f" {text_css}"
                f" border: 1px solid #888888;"
                f" border-radius: 3px;"
                f"}}"
                f"QPushButton#{name}:hover {{"
                f" border: 2px solid #333333;"
                f"}}"
            )
        finally:
            button.blockSignals(False)

    def _is_current_theme_dark(self):
        """Return True if the current application theme is a dark variant."""
        theme = getattr(self.main_window, 'app_theme', 'default')
        return theme in ('dark', 'midnight')

    def reset_colors_to_default(self):
        """Reset all colours to their default values based on the active theme."""
        is_dark = self._is_current_theme_dark()
        LIGHT_COLORS = {
            "command":         QColor(0, 0, 139),
            "environment":     QColor(139, 0, 139),
            "inline_math":     QColor(0, 100, 0),
            "display_math":    QColor(0, 128, 0),
            "brace":           QColor(139, 0, 0),
            "paren":           QColor(70, 200, 200),
            "parameter":       QColor(255, 140, 0),
            "optional":        QColor(184, 134, 11),
            "comment":         QColor(128, 128, 128),
            "special":         QColor(128, 0, 128),
            "reference":       QColor(25, 25, 112),
            "inline_math_bg":  QColor(0, 0, 0, 0),
            "display_math_bg": QColor(0, 0, 0, 0),
        }
        DARK_COLORS = {
            "command":         QColor(173, 216, 255),
            "environment":     QColor(221, 160, 221),
            "inline_math":     QColor(144, 238, 144),
            "display_math":    QColor(0, 255, 0),
            "brace":           QColor(255, 182, 193),
            "paren":           QColor(70, 200, 200),
            "parameter":       QColor(255, 165, 0),
            "optional":        QColor(218, 165, 32),
            "comment":         QColor(169, 169, 169),
            "special":         QColor(218, 112, 214),
            "reference":       QColor(135, 206, 250),
            "inline_math_bg":  QColor(0, 0, 0, 0),
            "display_math_bg": QColor(0, 0, 0, 0),
        }

        defaults = DARK_COLORS if is_dark else LIGHT_COLORS

        # ✅ Always apply directly to highlighters regardless of whether
        # the Colors tab has been built yet
        self._apply_colors_to_highlighters_directly(defaults)

        # ✅ Also update the UI widgets if the Colors tab has been built
        if self.color_widgets:
            for key, color in defaults.items():
                if key in self.color_widgets:
                    self.color_widgets[key]['color'] = color
                    self._apply_color_button_style(
                        self.color_widgets[key]['button'], color
                    )

        # ✅ Mark dirty so apply_colors_to_highlighter() won't skip
        self._colors_dirty = True


    def _apply_colors_to_highlighters_directly(self, color_map: dict):
        """Apply a color map directly to all open editor highlighters.
        Used when color_widgets may not be built yet (lazy tab loading)."""
        if hasattr(self.main_window, 'editor_manager') and \
           hasattr(self.main_window.editor_manager, 'editor_files'):
            for file_path, editor_data in self.main_window.editor_manager.editor_files.items():
                editor = editor_data.get('editor')
                if editor and hasattr(editor, 'highlighter') and editor.highlighter:
                    try:
                        editor.highlighter.update_colors(color_map)
                        editor.highlighter.rehighlight()
                    except Exception as e:
                        print(f"⚠️ Error applying colors to {file_path}: {e}")

        if hasattr(self.main_window, 'editor') and self.main_window.editor:
            if hasattr(self.main_window.editor, 'highlighter') and \
               self.main_window.editor.highlighter:
                try:
                    self.main_window.editor.highlighter.update_colors(color_map)
                    self.main_window.editor.highlighter.rehighlight()
                except Exception as e:
                    print(f"⚠️ Error applying colors to main editor: {e}")                

    def load_color_settings(self):
        """Load color settings from config, falling back to theme defaults."""
        config = self.main_window.config_manager.config
        if config.has_section('colors') and any(
            config.has_option('colors', key) for key in self.color_widgets
        ):
            for key in self.color_widgets:
                if config.has_option('colors', key):
                    color = QColor(config.get('colors', key))
                    if color.isValid():
                        self.color_widgets[key]['color'] = color
                        self._apply_color_button_style(
                            self.color_widgets[key]['button'], color)
        else:
            # ✅ No saved colors — apply theme-appropriate defaults
            self.reset_colors_to_default()
        
    def save_color_settings(self):
            config = self.main_window.config_manager.config
            if not config.has_section('colors'):
                config.add_section('colors')
            for key, widget_data in self.color_widgets.items():
                color = widget_data['color']
                config.set('colors', key, color.name(QColor.HexArgb))  # ← preserves alpha
            self.main_window.config_manager.save_config()

    def apply_colors_to_highlighter(self):
        """Apply the color settings to ALL active highlighters"""
        if not getattr(self, '_colors_dirty', False):
            return
        self._colors_dirty = False

        # ✅ If Colors tab hasn't been built, color_widgets is empty —
        # nothing to apply here (already handled by reset_colors_to_default)
        if not self.color_widgets:
            return

        color_map = {key: data['color'] for key, data in self.color_widgets.items()}
        self._apply_colors_to_highlighters_directly(color_map)
        
        
###

    # def create_font_tab(self):
        # """Create font settings tab with reset buttons"""
        # tab = QWidget()
        # layout = QVBoxLayout(tab)

        # # Define default values as class attributes for easy access
        # self.default_editor_font_family = "Consolas"
        # self.default_editor_font_size = 11
        # self.default_ui_font_family = "Calibri"
        # self.default_ui_font_size = 9

        # # ========== Editor Font Settings ==========
        # editor_group = QGroupBox("Editor Font")
        # editor_layout = QGridLayout(editor_group)

        # # Editor Font Family
        # editor_font_label = QLabel("Font Family:")
        # self.editor_font_combo = QFontComboBox()
        # self.editor_font_combo.setToolTip("Choose font for the code editor")
        # editor_layout.addWidget(editor_font_label, 0, 0)
        # editor_layout.addWidget(self.editor_font_combo, 0, 1)

        # # Only monospace checkbox for editor
        # self.monospace_only = QCheckBox("Show only monospace fonts")
        # self.monospace_only.setChecked(True)
        # self.monospace_only.toggled.connect(self.filter_editor_fonts)
        # editor_layout.addWidget(self.monospace_only, 1, 0, 1, 2)

        # # Editor Font Size
        # editor_size_label = QLabel("Font Size:")
        # self.editor_font_spin = QSpinBox()
        # self.editor_font_spin.setRange(8, 24)
        # self.editor_font_spin.setToolTip("Size of the editor font")
        # editor_layout.addWidget(editor_size_label, 2, 0)
        # editor_layout.addWidget(self.editor_font_spin, 2, 1)

        # # Reset Editor Font Button
        # self.reset_editor_font_btn = QPushButton("Reset to Default")
        # self.reset_editor_font_btn.setToolTip(f"Reset to {self.default_editor_font_family}, size {self.default_editor_font_size}")
        # self.reset_editor_font_btn.clicked.connect(self.reset_editor_font)
        # editor_layout.addWidget(self.reset_editor_font_btn, 3, 0, 1, 2, Qt.AlignRight)

        # layout.addWidget(editor_group)

        # # ========== Interface Font Settings ==========
        # ui_group = QGroupBox("Interface Font")
        # ui_layout = QGridLayout(ui_group)

        # # UI Font Family
        # ui_font_label = QLabel("Font Family:")
        # self.ui_font_combo = QFontComboBox()
        # self.ui_font_combo.setToolTip("Choose font for menus and UI elements")
        # ui_layout.addWidget(ui_font_label, 0, 0)
        # ui_layout.addWidget(self.ui_font_combo, 0, 1)

        # # UI Font Size
        # ui_size_label = QLabel("Font Size:")
        # self.toolbar_font_spin = QSpinBox()
        # self.toolbar_font_spin.setRange(8, 18)
        # self.toolbar_font_spin.setToolTip("Size of toolbar and UI fonts")
        # ui_layout.addWidget(ui_size_label, 1, 0)
        # ui_layout.addWidget(self.toolbar_font_spin, 1, 1)

        # # Reset UI Font Button
        # self.reset_ui_font_btn = QPushButton("Reset to Default")
        # self.reset_ui_font_btn.setToolTip(f"Reset to {self.default_ui_font_family}, size {self.default_ui_font_size}")
        # self.reset_ui_font_btn.clicked.connect(self.reset_ui_font)
        # ui_layout.addWidget(self.reset_ui_font_btn, 2, 0, 1, 2, Qt.AlignRight)

        # layout.addWidget(ui_group)

        # # ========== Preview and Reset All Buttons ==========
        # buttons_layout = QHBoxLayout()
        # buttons_layout.addStretch()

        # # Preview Fonts Button
        # self.preview_button = QPushButton("Preview Fonts")
        # self.preview_button.clicked.connect(self.preview_fonts)
        # self.preview_button.setFixedWidth(150)
        # buttons_layout.addWidget(self.preview_button)

        # # Reset All Fonts Button
        # self.reset_all_fonts_btn = QPushButton("Reset All Fonts")
        # self.reset_all_fonts_btn.setToolTip("Reset all font settings to default values")
        # self.reset_all_fonts_btn.clicked.connect(self.reset_all_fonts)
        # self.reset_all_fonts_btn.setFixedWidth(150)
        # buttons_layout.addWidget(self.reset_all_fonts_btn)

        # buttons_layout.addStretch()
        # layout.addLayout(buttons_layout)

        # # ========== Font Recommendations ==========
        # self.font_recommendations = QLabel()
        # self.font_recommendations.setWordWrap(True)
        # self.font_recommendations.setStyleSheet(
            # "color: #666; font-size: 11px; padding: 10px; "
            # "border: 1px solid #ddd; border-radius: 4px;"
        # )
        # layout.addWidget(self.font_recommendations)

        # # Connect signals to update recommendations
        # self.editor_font_combo.currentFontChanged.connect(self.update_font_recommendations)
        # self.ui_font_combo.currentFontChanged.connect(self.update_font_recommendations)

        # layout.addStretch()
        # scrollable = self._make_scrollable(tab)
        # self.tab_widget.addTab(scrollable, "Fonts")

        # # Initial font filtering
        # self.filter_editor_fonts()
        # return scrollable
        
    def create_font_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.default_editor_font_family = "Consolas"
        self.default_editor_font_size = 11
        self.default_ui_font_family = "Calibri"
        self.default_ui_font_size = 9

        # Editor Font Settings
        editor_group = QGroupBox(tr.get("font_editor_group", "Editor Font"))
        editor_layout = QGridLayout(editor_group)

        editor_font_label = QLabel(tr.get("font_family_label", "Font Family:"))
        self.editor_font_combo = QFontComboBox()
        self.editor_font_combo.setToolTip(tr.get("font_editor_tooltip", "Choose font for the code editor"))
        editor_layout.addWidget(editor_font_label, 0, 0)
        editor_layout.addWidget(self.editor_font_combo, 0, 1)

        self.monospace_only = QCheckBox(tr.get("font_monospace_only", "Show only monospace fonts"))
        self.monospace_only.setChecked(True)
        self.monospace_only.toggled.connect(self.filter_editor_fonts)
        editor_layout.addWidget(self.monospace_only, 1, 0, 1, 2)

        editor_size_label = QLabel(tr.get("font_size_label", "Font Size:"))
        self.editor_font_spin = QSpinBox()
        self.editor_font_spin.setRange(8, 24)
        self.editor_font_spin.setToolTip(tr.get("font_editor_size_tooltip", "Size of the editor font"))
        editor_layout.addWidget(editor_size_label, 2, 0)
        editor_layout.addWidget(self.editor_font_spin, 2, 1)

        self.reset_editor_font_btn = QPushButton(tr.get("font_reset_editor", "Reset to Default"))
        self.reset_editor_font_btn.setToolTip(tr.get("font_reset_editor_tooltip", f"Reset to {self.default_editor_font_family}, size {self.default_editor_font_size}"))
        self.reset_editor_font_btn.clicked.connect(self.reset_editor_font)
        editor_layout.addWidget(self.reset_editor_font_btn, 3, 0, 1, 2, Qt.AlignRight)

        layout.addWidget(editor_group)

        # Interface Font Settings
        ui_group = QGroupBox(tr.get("font_ui_group", "Interface Font"))
        ui_layout = QGridLayout(ui_group)

        ui_font_label = QLabel(tr.get("font_family_label", "Font Family:"))
        self.ui_font_combo = QFontComboBox()
        self.ui_font_combo.setToolTip(tr.get("font_ui_tooltip", "Choose font for menus and UI elements"))
        ui_layout.addWidget(ui_font_label, 0, 0)
        ui_layout.addWidget(self.ui_font_combo, 0, 1)

        ui_size_label = QLabel(tr.get("font_size_label", "Font Size:"))
        self.toolbar_font_spin = QSpinBox()
        self.toolbar_font_spin.setRange(8, 18)
        self.toolbar_font_spin.setToolTip(tr.get("font_ui_size_tooltip", "Size of toolbar and UI fonts"))
        ui_layout.addWidget(ui_size_label, 1, 0)
        ui_layout.addWidget(self.toolbar_font_spin, 1, 1)

        self.reset_ui_font_btn = QPushButton(tr.get("font_reset_ui", "Reset to Default"))
        self.reset_ui_font_btn.setToolTip(tr.get("font_reset_ui_tooltip", f"Reset to {self.default_ui_font_family}, size {self.default_ui_font_size}"))
        self.reset_ui_font_btn.clicked.connect(self.reset_ui_font)
        ui_layout.addWidget(self.reset_ui_font_btn, 2, 0, 1, 2, Qt.AlignRight)

        layout.addWidget(ui_group)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.preview_button = QPushButton(tr.get("font_preview_button", "Preview Fonts"))
        self.preview_button.clicked.connect(self.preview_fonts)
        self.preview_button.setFixedWidth(150)
        buttons_layout.addWidget(self.preview_button)

        self.reset_all_fonts_btn = QPushButton(tr.get("font_reset_all", "Reset All Fonts"))
        self.reset_all_fonts_btn.setToolTip(tr.get("font_reset_all_tooltip", "Reset all font settings to default values"))
        self.reset_all_fonts_btn.clicked.connect(self.reset_all_fonts)
        self.reset_all_fonts_btn.setFixedWidth(150)
        buttons_layout.addWidget(self.reset_all_fonts_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Recommendations label (dynamic, but initial placeholder)
        self.font_recommendations = QLabel()
        self.font_recommendations.setWordWrap(True)
        self.font_recommendations.setStyleSheet(
            "color: #666; font-size: 11px; padding: 10px; "
            "border: 1px solid #ddd; border-radius: 4px;"
        )
        layout.addWidget(self.font_recommendations)

        self.editor_font_combo.currentFontChanged.connect(self.update_font_recommendations)
        self.ui_font_combo.currentFontChanged.connect(self.update_font_recommendations)

        layout.addStretch()
        scrollable = self._make_scrollable(tab)
        self.tab_widget.addTab(scrollable, tr.get("tab_fonts", "Fonts"))
        self.filter_editor_fonts()
        return scrollable        
    
    def reset_editor_font(self):
        """Reset editor font settings to default values"""
        # Reset font family
        # First, make sure we can find the font in the filtered list
        if self.monospace_only.isChecked():
            index = self.editor_font_combo.findText(self.default_editor_font_family)
            if index >= 0:
                self.editor_font_combo.setCurrentIndex(index)
            else:
                # If Consolas not found, try other common monospace fonts
                fallbacks = ["Consolas", "Courier New", "DejaVu Sans Mono", "Liberation Mono"]
                for fallback in fallbacks:
                    index = self.editor_font_combo.findText(fallback)
                    if index >= 0:
                        self.editor_font_combo.setCurrentIndex(index)
                        break
        else:
            self.editor_font_combo.setCurrentFont(QFont(self.default_editor_font_family))
        
        # Reset font size
        self.editor_font_spin.setValue(self.default_editor_font_size)
        
        # Update recommendations display
        self.update_font_recommendations()
        
        #print(f"Editor font reset to: {self.default_editor_font_family}, size {self.default_editor_font_size}")


    def reset_ui_font(self):
        """Reset interface font settings to default values"""
        # Reset font family
        index = self.ui_font_combo.findText(self.default_ui_font_family)
        if index >= 0:
            self.ui_font_combo.setCurrentIndex(index)
        else:
            # Try fallback fonts
            fallbacks = ["Calibri", "Arial", "Helvetica", "Segoe UI", "DejaVu Sans"]
            for fallback in fallbacks:
                index = self.ui_font_combo.findText(fallback)
                if index >= 0:
                    self.ui_font_combo.setCurrentIndex(index)
                    break
            else:
                # If none found, just set it directly
                self.ui_font_combo.setCurrentFont(QFont(self.default_ui_font_family))
        
        # Reset font size
        self.toolbar_font_spin.setValue(self.default_ui_font_size)
        
        #print(f"Interface font reset to: {self.default_ui_font_family}, size {self.default_ui_font_size}")


    def reset_all_fonts(self):
        """Reset all font settings to default values"""
        self.reset_editor_font()
        self.reset_ui_font()
        
        # Show confirmation message
        from PyQt5.QtWidgets import QToolTip
        QToolTip.showText(
            self.reset_all_fonts_btn.mapToGlobal(self.reset_all_fonts_btn.rect().center()),
            "All fonts reset to defaults!",
            self.reset_all_fonts_btn,
            self.reset_all_fonts_btn.rect(),
            2000  # Show for 2 seconds
        )
    
    def filter_editor_fonts(self):
        from PyQt5.QtWidgets import QFontComboBox
        if self.monospace_only.isChecked():
            self.editor_font_combo.setFontFilters(
                QFontComboBox.MonospacedFonts
            )
        else:
            self.editor_font_combo.setFontFilters(
                QFontComboBox.AllFonts
            )

    def update_font_recommendations(self):
        """Update font recommendations based on current selections"""
        editor_font = self.editor_font_combo.currentFont().family()
        
        recommendations = []
        
        # Check if editor font is monospace
        font_db = QFontDatabase()
        if not font_db.isFixedPitch(editor_font):
            recommendations.append("⚠️ Editor font is not monospace - code alignment may be poor")
        
        # Font-specific recommendations
        good_fonts = ["Consolas", "Monaco", "Menlo", "Source Code Pro", "Fira Code", "JetBrains Mono"]
        if editor_font in good_fonts:
            recommendations.append("✅ Excellent choice for LaTeX typing!")
        elif font_db.isFixedPitch(editor_font):
            recommendations.append("✅ Good monospace font for LaTeX typing")
        
        if len(recommendations) == 0:
            recommendations.append("💡 Consider using a LaTeX font like Consolas or Monaco")
        
        self.font_recommendations.setText("\n".join(recommendations))

    def preview_fonts(self):
        """Show a preview dialog with selected fonts"""
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Font Preview")
        preview_dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(preview_dialog)
        
        # Editor font preview
        editor_label = QLabel("Editor Font Preview:")
        layout.addWidget(editor_label)
        
        editor_preview = QTextEdit()
        editor_font = QFont(self.editor_font_combo.currentFont().family(), 
                          self.editor_font_spin.value())
        editor_preview.setFont(editor_font)
        editor_preview.setPlainText("""\\documentclass{article}
\\usepackage{amsmath}
\\usepackage{fontspec}
\\setmainfont{Amiri}

\\begin{document}
\\title{Sample LaTeX Document}
\\author{Your Name}
\\maketitle

This is how your LaTeX code will look in the editor.
Numbers and symbols: 1234567890 !@#$%^&*()_+-=
Brackets and braces: [] {} () <> 

\\begin{equation}
    E = mc^2 \\quad \\text{and} \\quad F = ma
\\end{equation}

\\section{مقدمة}
Text in Arabic: هذا نص تجريبي بالللغة العربية

\\end{document}""")
        editor_preview.setMaximumHeight(600)
        layout.addWidget(editor_preview)
        
        # UI font preview
        ui_label = QLabel("UI Font Preview:")
        layout.addWidget(ui_label)
        
        ui_preview = QLabel()
        ui_font = QFont(self.ui_font_combo.currentFont().family(), 
                       self.toolbar_font_spin.value())
        ui_preview.setFont(ui_font)
        ui_preview.setText("""Menu items: File  Edit  View  Insert  Tools  Help
Toolbar buttons: New  Open  Save  Compile  Settings
Status text: Ready | Editor Layout | No files | LTR | English""")
        ui_preview.setStyleSheet("border: 1px solid #ccc; padding: 15px; background: #f9f9f9;")
        layout.addWidget(ui_preview)
        
        # Close button
        close_button = QPushButton("Close Preview")
        close_button.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_button)
        
        preview_dialog.exec_()
        
    # def create_compiler_tab(self):
        # """Create compiler settings tab with customizable command options"""
        # tab = QWidget()
        # layout = QVBoxLayout(tab)
        
        # # LaTeX Compiler Group (existing code)
        # latex_group = QGroupBox("LaTeX Compiler")
        # latex_layout = QGridLayout(latex_group)
        
        # engine_label = QLabel("LaTeX Engine:")
        # self.engine_combo = QComboBox()
        # self.engine_combo.addItems(["pdflatex", "xelatex", "lualatex", "custom"])
        # self.engine_combo.currentTextChanged.connect(self.on_latex_engine_changed)
        
        # latex_layout.addWidget(engine_label, 0, 0)
        # latex_layout.addWidget(self.engine_combo, 0, 1)
        
        # command_label = QLabel("Compilation Command:")
        # self.command_text = QLineEdit()
        # self.command_text.setPlaceholderText("Enter custom compilation command...")
        
        # latex_layout.addWidget(command_label, 1, 0)
        # latex_layout.addWidget(self.command_text, 1, 1)
        
        # # Help label for LaTeX custom commands
        # self.custom_help_label = QLabel(
            # "For custom commands, use full command chains. Available placeholders:\n"
            # "• %f = full filename (e.g., document.tex)\n"
            # "• %b = basename without extension (e.g., document)\n" 
            # "• %d = directory path\n\n"
            # "Examples:\n"
            # "• latex %f && dvips %b.dvi && ps2pdf %b.ps\n"
            # "• pdflatex %f && bibtex %b && pdflatex %f && pdflatex %f"
        # )
        # self.custom_help_label.setStyleSheet("color: #666; font-size: 10px; background-color: #f5f5f5; padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        # self.custom_help_label.setWordWrap(True)
        # self.custom_help_label.setVisible(False)
        
        # latex_layout.addWidget(self.custom_help_label, 2, 0, 1, 2)
        
        # self.reset_latex_button = QPushButton("Reset to Default")
        # self.reset_latex_button.clicked.connect(self.reset_latex_command)
        # latex_layout.addWidget(self.reset_latex_button, 3, 1, Qt.AlignRight)
        
        # layout.addWidget(latex_group)
        
        # # Enhanced Backmatter Compiler Group with custom support
        # backmatter_group = QGroupBox("Backmatter Compiler")
        # backmatter_layout = QGridLayout(backmatter_group)
        
        # backmatter_label = QLabel("Backmatter Engine:")
        # self.backmatter_combo = QComboBox()
        # # Extended list with more options including custom
        # self.backmatter_combo.addItems(["bibtex", "biber", "makeindex", "xindy", "makeglossaries", "custom"])
        # self.backmatter_combo.currentTextChanged.connect(self.on_backmatter_engine_changed)
        
        # backmatter_layout.addWidget(backmatter_label, 0, 0)
        # backmatter_layout.addWidget(self.backmatter_combo, 0, 1)
        
        # backmatter_command_label = QLabel("Backmatter Command:")
        # self.backmatter_command_text = QLineEdit()
        # self.backmatter_command_text.setPlaceholderText("Enter custom backmatter command...")
        
        # backmatter_layout.addWidget(backmatter_command_label, 1, 0)
        # backmatter_layout.addWidget(self.backmatter_command_text, 1, 1)
        
        # # Help label for backmatter custom commands
        # self.backmatter_custom_help_label = QLabel(
            # "Custom backmatter commands support the same placeholders:\n"
            # "• %f = full filename (e.g., document.tex)\n"
            # "• %b = basename without extension (e.g., document)\n"
            # "• %d = directory path\n\n"
            # "Examples:\n"
            # "• biber %b\n"
            # "• xindy -M texindy -L english %b.idx\n"
            # "• custom-bibliography-processor %b.aux"
        # )
        # self.backmatter_custom_help_label.setStyleSheet("color: #666; font-size: 10px; background-color: #f0f8ff; padding: 8px; border: 1px solid #cce7ff; border-radius: 4px;")
        # self.backmatter_custom_help_label.setWordWrap(True)
        # self.backmatter_custom_help_label.setVisible(False)
        
        # backmatter_layout.addWidget(self.backmatter_custom_help_label, 2, 0, 1, 2)
        
        # self.reset_backmatter_button = QPushButton("Reset to Default")
        # self.reset_backmatter_button.clicked.connect(self.reset_backmatter_command)
        # backmatter_layout.addWidget(self.reset_backmatter_button, 3, 1, Qt.AlignRight)
        
        # layout.addWidget(backmatter_group)
        
        # # Encoding group (existing code)
        # encoding_group = QGroupBox("Output Encoding")
        # encoding_layout = QGridLayout(encoding_group)
        
        # encoding_label = QLabel("Encoding:")
        # self.encoding_combo = QComboBox()
        # self.encoding_combo.addItems(["utf-8", "latin-1", "cp1252"])
        
        # encoding_layout.addWidget(encoding_label, 0, 0)
        # encoding_layout.addWidget(self.encoding_combo, 0, 1)
        
        # layout.addWidget(encoding_group)
        # layout.addStretch()
        
        # scrollable = self._make_scrollable(tab)
        # #self.tab_widget.addTab(scrollable, "Compiler")
        # return scrollable

    def create_compiler_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # LaTeX Compiler Group
        latex_group = QGroupBox(tr.get("compiler_latex_group", "LaTeX Compiler"))
        latex_layout = QGridLayout(latex_group)

        engine_label = QLabel(tr.get("compiler_engine_label", "LaTeX Engine:"))
        self.engine_combo = QComboBox()
        # self.engine_combo.addItems([
            # tr.get("compiler_engine_pdflatex", "pdflatex"),
            # tr.get("compiler_engine_xelatex", "xelatex"),
            # tr.get("compiler_engine_lualatex", "lualatex"),
            # tr.get("compiler_engine_custom", "custom")
        # ])
        for key, label_key, default in [
            ("pdflatex", "compiler_engine_pdflatex", "pdflatex"),
            ("xelatex",  "compiler_engine_xelatex",  "xelatex"),
            ("lualatex", "compiler_engine_lualatex",  "lualatex"),
            ("custom",   "compiler_engine_custom",    "custom"),
        ]:
            self.engine_combo.addItem(tr.get(label_key, default), key)        
        self.engine_combo.currentTextChanged.connect(self.on_latex_engine_changed)

        latex_layout.addWidget(engine_label, 0, 0)
        latex_layout.addWidget(self.engine_combo, 0, 1)

        command_label = QLabel(tr.get("compiler_command_label", "Compilation Command:"))
        self.command_text = QLineEdit()
        self.command_text.setPlaceholderText(tr.get("compiler_command_placeholder", "Enter custom compilation command..."))

        latex_layout.addWidget(command_label, 1, 0)
        latex_layout.addWidget(self.command_text, 1, 1)

        self.custom_help_label = QLabel(tr.get("compiler_custom_help", "For custom commands, use full command chains. Available placeholders:\n• %f = full filename (e.g., document.tex)\n• %b = basename without extension (e.g., document)\n• %d = directory path\n\nExamples:\n• latex %f && dvips %b.dvi && ps2pdf %b.ps\n• pdflatex %f && bibtex %b && pdflatex %f && pdflatex %f"))
        self.custom_help_label.setStyleSheet("color: #666; font-size: 10px; background-color: #f5f5f5; padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        self.custom_help_label.setWordWrap(True)
        self.custom_help_label.setVisible(False)
        latex_layout.addWidget(self.custom_help_label, 2, 0, 1, 2)

        self.reset_latex_button = QPushButton(tr.get("compiler_reset_latex", "Reset to Default"))
        self.reset_latex_button.clicked.connect(self.reset_latex_command)
        latex_layout.addWidget(self.reset_latex_button, 3, 1, Qt.AlignRight)

        layout.addWidget(latex_group)

        # Backmatter Compiler Group
        backmatter_group = QGroupBox(tr.get("compiler_backmatter_group", "Backmatter Compiler"))
        backmatter_layout = QGridLayout(backmatter_group)

        backmatter_label = QLabel(tr.get("compiler_backmatter_label", "Backmatter Engine:"))
        self.backmatter_combo = QComboBox()
        # self.backmatter_combo.addItems([
            # tr.get("compiler_backmatter_bibtex", "bibtex"),
            # tr.get("compiler_backmatter_biber", "biber"),
            # tr.get("compiler_backmatter_makeindex", "makeindex"),
            # tr.get("compiler_backmatter_xindy", "xindy"),
            # tr.get("compiler_backmatter_makeglossaries", "makeglossaries"),
            # tr.get("compiler_backmatter_custom", "custom")
        # ])
        for key, label_key, default in [
            ("bibtex",          "compiler_backmatter_bibtex",          "bibtex"),
            ("biber",           "compiler_backmatter_biber",           "biber"),
            ("makeindex",       "compiler_backmatter_makeindex",       "makeindex"),
            ("xindy",           "compiler_backmatter_xindy",           "xindy"),
            ("makeglossaries",  "compiler_backmatter_makeglossaries",  "makeglossaries"),
            ("custom",          "compiler_backmatter_custom",          "custom"),
        ]:
            self.backmatter_combo.addItem(tr.get(label_key, default), key)
        
        self.backmatter_combo.currentTextChanged.connect(self.on_backmatter_engine_changed)

        backmatter_layout.addWidget(backmatter_label, 0, 0)
        backmatter_layout.addWidget(self.backmatter_combo, 0, 1)

        backmatter_command_label = QLabel(tr.get("compiler_backmatter_command_label", "Backmatter Command:"))
        self.backmatter_command_text = QLineEdit()
        self.backmatter_command_text.setPlaceholderText(tr.get("compiler_backmatter_placeholder", "Enter custom backmatter command..."))

        backmatter_layout.addWidget(backmatter_command_label, 1, 0)
        backmatter_layout.addWidget(self.backmatter_command_text, 1, 1)

        self.backmatter_custom_help_label = QLabel(tr.get("compiler_backmatter_custom_help", "Custom backmatter commands support the same placeholders:\n• %f = full filename (e.g., document.tex)\n• %b = basename without extension (e.g., document)\n• %d = directory path\n\nExamples:\n• biber %b\n• xindy -M texindy -L english %b.idx\n• custom-bibliography-processor %b.aux"))
        self.backmatter_custom_help_label.setStyleSheet("color: #666; font-size: 10px; background-color: #f0f8ff; padding: 8px; border: 1px solid #cce7ff; border-radius: 4px;")
        self.backmatter_custom_help_label.setWordWrap(True)
        self.backmatter_custom_help_label.setVisible(False)
        backmatter_layout.addWidget(self.backmatter_custom_help_label, 2, 0, 1, 2)

        self.reset_backmatter_button = QPushButton(tr.get("compiler_reset_backmatter", "Reset to Default"))
        self.reset_backmatter_button.clicked.connect(self.reset_backmatter_command)
        backmatter_layout.addWidget(self.reset_backmatter_button, 3, 1, Qt.AlignRight)

        layout.addWidget(backmatter_group)

        # Encoding Group
        encoding_group = QGroupBox(tr.get("compiler_encoding_group", "Output Encoding"))
        encoding_layout = QGridLayout(encoding_group)

        encoding_label = QLabel(tr.get("compiler_encoding_label", "Encoding:"))
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems([
            tr.get("compiler_encoding_utf8", "utf-8"),
            tr.get("compiler_encoding_latin1", "latin-1"),
            tr.get("compiler_encoding_cp1252", "cp1252")
        ])

        encoding_layout.addWidget(encoding_label, 0, 0)
        encoding_layout.addWidget(self.encoding_combo, 0, 1)

        layout.addWidget(encoding_group)
        layout.addStretch()

        scrollable = self._make_scrollable(tab)
        return scrollable
        
    def on_latex_engine_changed(self):
        current_engine = self.engine_combo.currentData()
        
        # Show/hide help text for custom engine
        if hasattr(self, 'custom_help_label'):
            self.custom_help_label.setVisible(current_engine == "custom")
        
        # Enable/disable command text based on engine selection
        if current_engine == "custom":
            self.command_text.setEnabled(True)
            self.command_text.setPlaceholderText("Enter full compilation command chain (use %f for filename, %b for basename)")
            # Load custom command from settings
            custom_command = getattr(self.main_window, 'custom_option', '')
            self.command_text.setText(custom_command)
            # Enable the command text field for editing
            self.command_text.setReadOnly(False)
        else:
            self.command_text.setEnabled(True)
            self.command_text.setReadOnly(False)  # Allow editing of standard commands too
            if current_engine in self.default_latex_commands:
                custom_command = getattr(self.main_window, f'{current_engine}_option', None)
                if custom_command:
                    self.command_text.setText(custom_command)
                else:
                    self.command_text.setText(self.default_latex_commands[current_engine])

# Enhanced backmatter engine change handler
    def on_backmatter_engine_changed(self):
        """Handle backmatter engine combo box change with custom support"""
        current_engine = self.backmatter_combo.currentData()
        
        # Show/hide help label for custom commands
        if hasattr(self, 'backmatter_custom_help_label'):
            self.backmatter_custom_help_label.setVisible(current_engine == "custom")
        
        if current_engine == "custom":
            self.backmatter_command_text.setEnabled(True)
            self.backmatter_command_text.setPlaceholderText("Enter custom backmatter command (use %f, %b, %d placeholders)")
            # Load existing custom command if available
            custom_command = getattr(self.main_window, 'backmatter_custom_option', '')
            self.backmatter_command_text.setText(custom_command)
            self.backmatter_command_text.setReadOnly(False)
        else:
            self.backmatter_command_text.setEnabled(True)
            self.backmatter_command_text.setReadOnly(False)
            
            if current_engine in self.default_backmatter_commands:
                # Check for saved custom command for this engine
                custom_command = getattr(self.main_window, f'backmatter_{current_engine}_option', None)
                if custom_command:
                    self.backmatter_command_text.setText(custom_command)
                else:
                    self.backmatter_command_text.setText(self.default_backmatter_commands[current_engine])

    def reset_latex_command(self):
        current_engine = self.engine_combo.currentText()
        if current_engine == "custom":
            self.command_text.setText("")
        else:
            default_command = self.default_latex_commands.get(current_engine, "")
            self.command_text.setText(default_command)

    def reset_backmatter_command(self):
        """Reset backmatter command to default"""
        current_engine = self.backmatter_combo.currentText()
        if current_engine in self.default_backmatter_commands:
            self.backmatter_command_text.setText(self.default_backmatter_commands[current_engine])
                
        
    # def create_layout_tab(self):
        # """Create layout settings tab"""
        # tab = QWidget()
        # layout = QVBoxLayout(tab)
        
        # # Main Layout Group
        # main_group = QGroupBox("Main Layout")
        # main_layout = QGridLayout(main_group)
        
        # # Switch Mode
        # switch_label = QLabel("Default Position:")
        # self.switch_combo = QComboBox()
        # self.switch_combo.addItems(["editor_left", "pdf_left"])
        # main_layout.addWidget(switch_label, 0, 0)
        # main_layout.addWidget(self.switch_combo, 0, 1)
        
        # layout.addWidget(main_group)
        
        # # Set initial value
        # current_layout = self.main_window.editor_manager.editor_layout_mode
        # self.switch_combo.setCurrentText(current_layout)
        
        
        # # Editor Layout Group
        # editor_group = QGroupBox("Editor Layout")
        # editor_layout = QGridLayout(editor_group)
        
        # editor_label = QLabel("Editor Mode:")
        # self.editor_layout_combo = QComboBox()
        # self.editor_layout_combo.addItems(["tabbed", "horizontal", "vertical"])
        # editor_layout.addWidget(editor_label, 0, 0)
        # editor_layout.addWidget(self.editor_layout_combo, 0, 1)
        
        # layout.addWidget(editor_group)
        
        # # Set initial value
        # current_mode = self.main_window.editor_manager.editor_layout_mode
        # self.editor_layout_combo.setCurrentText(current_mode)

        
        # # PDF Layout Group
        # pdf_group = QGroupBox("PDF Layout")
        # pdf_layout = QGridLayout(pdf_group)        
        # pdf_label = QLabel("PDF Mode:")
        # self.pdf_layout_combo = QComboBox()
        # self.pdf_layout_combo.addItems(["tabbed", "horizontal", "vertical"])
        # pdf_layout.addWidget(pdf_label, 0, 0)
        # pdf_layout.addWidget(self.pdf_layout_combo, 0, 1)        
        
        # layout.addWidget(pdf_group)
        
        # current_mode = self.main_window.pdf_manager.pdf_layout_mode
        # self.pdf_layout_combo.setCurrentText(current_mode)
        
        
        # # Recent Files Group
        # recent_group = QGroupBox("Recent Files")
        # recent_layout = QVBoxLayout(recent_group)
        
        
        # self.recent_list = QListWidget()
        # self.recent_list.setMaximumHeight(200)
        # recent_layout.addWidget(self.recent_list)
        
        # recent_files_btn_layout = QHBoxLayout()
        # recent_layout.addLayout(recent_files_btn_layout)
        
        # clear_recent_btn = QPushButton("Clear Recent Files")
        # clear_recent_btn.clicked.connect(self.clear_recent_files)
        # clear_recent_btn.clicked.connect(self.main_window.editor_manager.close_all_files)
        # clear_recent_btn.setFixedWidth(150)
        # recent_files_btn_layout.addWidget(clear_recent_btn,alignment=Qt.AlignRight)
        

        # open_all_recent_btn = QPushButton("Open All Recent Files")
        # open_all_recent_btn.clicked.connect(self.main_window.menu_manager.open_all_recent_files)
        # open_all_recent_btn.setFixedWidth(150)
        # recent_files_btn_layout.addWidget(open_all_recent_btn,alignment=Qt.AlignLeft)
               
        # layout.addWidget(recent_group)
        
        # layout.addStretch()
        
        # scrollable = self._make_scrollable(tab)
        # #self.tab_widget.addTab(scrollable, "Layout")
        # return scrollable   

    def create_layout_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Main Layout Group
        main_group = QGroupBox(tr.get("layout_main_group", "Main Layout"))
        main_layout = QGridLayout(main_group)

        switch_label = QLabel(tr.get("layout_default_position", "Default Position:"))
        self.switch_combo = QComboBox()
        self.switch_combo.addItems([
            tr.get("layout_editor_left", "editor_left"),
            tr.get("layout_pdf_left", "pdf_left")
        ])
        main_layout.addWidget(switch_label, 0, 0)
        main_layout.addWidget(self.switch_combo, 0, 1)

        layout.addWidget(main_group)

        # Editor Layout Group
        editor_group = QGroupBox(tr.get("layout_editor_group", "Editor Layout"))
        editor_layout = QGridLayout(editor_group)

        editor_label = QLabel(tr.get("layout_editor_mode", "Editor Mode:"))
        self.editor_layout_combo = QComboBox()
        self.editor_layout_combo.addItems([
            tr.get("layout_tabbed", "tabbed"),
            tr.get("layout_horizontal", "horizontal"),
            tr.get("layout_vertical", "vertical")
        ])
        editor_layout.addWidget(editor_label, 0, 0)
        editor_layout.addWidget(self.editor_layout_combo, 0, 1)

        layout.addWidget(editor_group)

        # PDF Layout Group
        pdf_group = QGroupBox(tr.get("layout_pdf_group", "PDF Layout"))
        pdf_layout = QGridLayout(pdf_group)
        pdf_label = QLabel(tr.get("layout_pdf_mode", "PDF Mode:"))
        self.pdf_layout_combo = QComboBox()
        self.pdf_layout_combo.addItems([
            tr.get("layout_tabbed", "tabbed"),
            tr.get("layout_horizontal", "horizontal"),
            tr.get("layout_vertical", "vertical")
        ])
        pdf_layout.addWidget(pdf_label, 0, 0)
        pdf_layout.addWidget(self.pdf_layout_combo, 0, 1)

        layout.addWidget(pdf_group)

        # Recent Files Group
        recent_group = QGroupBox(tr.get("layout_recent_group", "Recent Files"))
        recent_layout = QVBoxLayout(recent_group)

        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(200)
        recent_layout.addWidget(self.recent_list)

        recent_files_btn_layout = QHBoxLayout()
        recent_layout.addLayout(recent_files_btn_layout)

        clear_recent_btn = QPushButton(tr.get("layout_clear_recent", "Clear Recent Files"))
        clear_recent_btn.clicked.connect(self.clear_recent_files)
        clear_recent_btn.clicked.connect(self.main_window.editor_manager.close_all_files)
        clear_recent_btn.setFixedWidth(150)
        recent_files_btn_layout.addWidget(clear_recent_btn, alignment=Qt.AlignRight)

        open_all_recent_btn = QPushButton(tr.get("layout_open_all_recent", "Open All Recent Files"))
        open_all_recent_btn.clicked.connect(self.main_window.menu_manager.open_all_recent_files)
        open_all_recent_btn.setFixedWidth(150)
        recent_files_btn_layout.addWidget(open_all_recent_btn, alignment=Qt.AlignLeft)

        layout.addWidget(recent_group)
        layout.addStretch()

        scrollable = self._make_scrollable(tab)
        return scrollable

    def load_recent_files_display(self):
        """Load and display recent files in the settings dialog"""
        try:
            if hasattr(self.main_window, 'config_manager') and hasattr(self, 'recent_list'):
                recent_files = self.main_window.config_manager.get_recent_files()
                self.recent_list.clear()
                if recent_files:
                    for path in recent_files:
                        filename = os.path.basename(path)
                        self.recent_list.addItem(filename)
                    #print(f"📋 Updated recent files display: {len(recent_files)} total files")
                else:
                    self.recent_list.addItem("No recent files")
        except Exception as e:
            print(f"❌ Error loading recent files display: {e}")
    

    def clear_recent_files(self):
        """Clear recent files list"""
        config_manager = self.main_window.config_manager

        # Clear recent files
        for section in ['recent_files', 'session_files']:
            if config_manager.config.has_section(section):
                config_manager.config.remove_section(section)
            config_manager.config.add_section(section)  # ensure section exists

        # Save using the correct method
            if hasattr(config_manager, 'recent_files'):
                config_manager.save_session_files(open_files)
                #print(f"💾 Session saved on close with {len(open_files)} files")
            else:
                print("⚠️  save_session_files method not found")
        # Save using the correct method
            if hasattr(config_manager, 'session_files'):
                config_manager.save_session_files(open_files)
                #print(f"💾 Session saved on close with {len(open_files)} files")
            else:
                print("⚠️  save_session_files method not found")

        # Update display
        if self.recent_list:
            self.recent_list.clear()
            self.recent_list.addItem("Recent files cleared")

        

    def on_setting_changed(self):
        """Handle any setting change - optional for immediate preview"""
        # This is called when any setting changes
        # You can add immediate preview logic here if needed
        pass
        
    def _sync_output_checkbox(self, visible: bool):
        """Update checkbox to match current output visibility"""
        if hasattr(self, "_loading_settings") and self._loading_settings:
            return  # prevent recursion
        if self.output_visible_check:
            self._loading_settings = True
            self.output_visible_check.setChecked(visible)
            self._loading_settings = False


    def showEvent(self, event):
        """Ensure checkbox is synced when dialog opens"""
        super().showEvent(event)
        if self.output_visible_check:
            self._loading_settings = True
            self.output_visible_check.setChecked(self.main_window.output_tabs_visible)
            self._loading_settings = False
    
    # def create_ui_tab(self):
        # """Create UI settings tab"""
        # tab = QWidget()
        # layout = QVBoxLayout(tab)
        
        # # Language & Startup Settings
        # lang_group = QGroupBox("Language and Startup")
        # lang_layout = QGridLayout(lang_group)
        
        # # Menu Language
        # menu_lang_label = QLabel("Menu Language:")
        # self.menu_lang_combo = QComboBox()
        # self.menu_lang_combo.addItems(["en", "ar"])
        # self.menu_lang_combo.currentTextChanged.connect(self.on_setting_changed)
        # lang_layout.addWidget(menu_lang_label, 0, 0)
        # lang_layout.addWidget(self.menu_lang_combo, 0, 1)
        # current_menu_lang = self.main_window.menu_language
        # self.menu_lang_combo.setCurrentText(current_menu_lang)
        
        # # RTL Support
        # self.rtl_check = QCheckBox("Right-to-Left text direction")
        # self.rtl_check.stateChanged.connect(self.on_setting_changed)
        # lang_layout.addWidget(self.rtl_check, 1, 0, 1, 2)
        # new_rtl = self.main_window.is_rtl
        # self.rtl_check.setChecked(new_rtl)
        
        # # Auto-load setting
        # self.auto_load_check = QCheckBox("Load last open files on startup")
        # self.auto_load_check.stateChanged.connect(self.on_setting_changed)
        # lang_layout.addWidget(self.auto_load_check, 2, 0, 1, 2)
        
        # layout.addWidget(lang_group)

        # # ── Application Theme ─────────────────────────────────────────────────
        # theme_group = QGroupBox("Application Theme")
        # theme_layout = QGridLayout(theme_group)

        # theme_label = QLabel("Theme:")
        # self.theme_combo = QComboBox()

        # # Populate from AVAILABLE_THEMES; mark qdarkstyle entries if missing
        # from style_manager import AVAILABLE_THEMES
        # try:
            # import qdarkstyle
            # _has_qdarkstyle = True
        # except ImportError:
            # _has_qdarkstyle = False

        # self._theme_keys = []
        # for key, display in AVAILABLE_THEMES.items():
            # needs_pkg = key in ("dark", "light")
            # if needs_pkg and not _has_qdarkstyle:
                # self.theme_combo.addItem(f"{display}  (pip install qdarkstyle)")
            # else:
                # self.theme_combo.addItem(display)
            # self._theme_keys.append(key)

        # current_theme = getattr(self.main_window, 'app_theme', 'default')
        # if current_theme in self._theme_keys:
            # self.theme_combo.setCurrentIndex(self._theme_keys.index(current_theme))

        # self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        # theme_layout.addWidget(theme_label, 0, 0)
        # theme_layout.addWidget(self.theme_combo, 0, 1)

        # if not _has_qdarkstyle:
            # hint = QLabel(
                # "Install <b>qdarkstyle</b> to unlock Dark and Light themes: "
                # "<code>pip install qdarkstyle</code>"
            # )
            # hint.setWordWrap(True)
            # hint.setStyleSheet("color: gray; font-size: 11px;")
            # theme_layout.addWidget(hint, 1, 0, 1, 2)

        # layout.addWidget(theme_group)

        # # ── rest of the method unchanged from here ────────────────────────────

        
        # # Output Tabs Group
        # output_group = QGroupBox("Output Tabs Configuration")
        # output_layout = QGridLayout(output_group)  # Use QGridLayout to match original
        
        # # Main output checkbox
        # self.output_visible_check = QCheckBox("Show Output/Error tabs")
        # self.output_visible_check.setToolTip("Main output container with Output and Error tabs")
        # output_layout.addWidget(self.output_visible_check, 0, 0, 1, 2)  # Row 0, spans 2 columns
        
        # #self.output_visible_check.toggled.connect(self.main_window.set_output_visibility)
        
        # # Sub-tabs (dependent on main output)
        # sub_tabs_label = QLabel("Additional tabs (require Output/Error to be visible):")
        # sub_tabs_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        # output_layout.addWidget(sub_tabs_label, 1, 0, 1, 2)  # Row 1, spans 2 columns
        
        # # Create sub-tab checkboxes with indentation using grid positions
        # self.symbols_visible_check = QCheckBox("Show Symbols tab")
        # self.commands_visible_check = QCheckBox("Show Commands tab")
        # self.tree_visible_check = QCheckBox("Show Tree tab")
        # self.bookmarks_visible_check = QCheckBox("Show Bookmarks tab")
        # self.terminal_visible_check = QCheckBox("Show Terminal tab")
        
        # # Add checkboxes to grid with indentation (column 1 for indentation effect)
        # output_layout.addWidget(self.symbols_visible_check, 2, 0)
        # output_layout.addWidget(self.commands_visible_check, 3, 0)
        # output_layout.addWidget(self.tree_visible_check, 4, 0)
        # output_layout.addWidget(self.bookmarks_visible_check, 5, 0)
        # output_layout.addWidget(self.terminal_visible_check, 6, 0)
        
        # # Add some spacing to the right column if needed
        # output_layout.setColumnStretch(1, 1)
        
        # # Connect signals for synchronization
        # self.output_visible_check.toggled.connect(self.on_output_toggled)
        # self.symbols_visible_check.toggled.connect(self.on_sub_tab_toggled)
        # self.commands_visible_check.toggled.connect(self.on_sub_tab_toggled)
        # self.tree_visible_check.toggled.connect(self.on_sub_tab_toggled)
        # self.bookmarks_visible_check.toggled.connect(self.on_sub_tab_toggled)
        # self.terminal_visible_check.toggled.connect(self.on_sub_tab_toggled)
        
        # layout.addWidget(output_group)
        


        # # show_line_numbers and show_fold_markers
        # line_fold_group = QGroupBox("Line numbers and fold markers")
        # line_fold_layout = QGridLayout(line_fold_group)

        # # Line numbers checkbox
        # self.line_numbers_check = QCheckBox("Show line numbers")
        # self.line_numbers_check.toggled.connect(self._on_line_numbers_toggled)
        # line_fold_layout.addWidget(self.line_numbers_check, 0, 0, 1, 2)

        # # Fold markers checkbox  
        # self.fold_marker_check = QCheckBox("Show fold markers")
        # self.fold_marker_check.toggled.connect(self._on_fold_markers_toggled)
        # line_fold_layout.addWidget(self.fold_marker_check, 1, 0, 1, 2)

        # layout.addWidget(line_fold_group)      
        
        # layout.addStretch()

        
        # # Add tab to tab widget
        # if hasattr(self, 'tab_widget'):            
            # scrollable = self._make_scrollable(tab)
            # self.tab_widget.addTab(scrollable, "UI")

        # return scrollable   


    def create_ui_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Language & Startup Group
        lang_group = QGroupBox(tr.get("ui_lang_group", "Language and Startup"))
        lang_layout = QGridLayout(lang_group)

        menu_lang_label = QLabel(tr.get("ui_menu_language", "Menu Language:"))
        self.menu_lang_combo = QComboBox()
        self.menu_lang_combo.addItems([
            tr.get("ui_lang_en", "en"),
            tr.get("ui_lang_ar", "ar")
        ])
        self.menu_lang_combo.currentTextChanged.connect(self.on_setting_changed)
        lang_layout.addWidget(menu_lang_label, 0, 0)
        lang_layout.addWidget(self.menu_lang_combo, 0, 1)
        current_menu_lang = self.main_window.menu_language
        self.menu_lang_combo.setCurrentText(current_menu_lang)

        self.rtl_check = QCheckBox(tr.get("ui_rtl_check", "Right-to-Left text direction"))
        self.rtl_check.stateChanged.connect(self.on_setting_changed)
        lang_layout.addWidget(self.rtl_check, 1, 0, 1, 2)
        self.rtl_check.setChecked(self.main_window.is_rtl)

        self.auto_load_check = QCheckBox(tr.get("ui_auto_load_check", "Load last open files on startup"))
        self.auto_load_check.stateChanged.connect(self.on_setting_changed)
        lang_layout.addWidget(self.auto_load_check, 2, 0, 1, 2)

        layout.addWidget(lang_group)

        # Application Theme Group
        theme_group = QGroupBox(tr.get("ui_theme_group", "Application Theme"))
        theme_layout = QGridLayout(theme_group)

        theme_label = QLabel(tr.get("ui_theme_label", "Theme:"))
        self.theme_combo = QComboBox()
        from style_manager import AVAILABLE_THEMES, AVAILABLE_THEMES_AR
        try:
            import qdarkstyle
            _has_qdarkstyle = True
        except ImportError:
            _has_qdarkstyle = False

        self._theme_keys = []
        if lang == "en":
            for key, display in AVAILABLE_THEMES.items():
                needs_pkg = key in ("dark", "light")
                if needs_pkg and not _has_qdarkstyle:
                    self.theme_combo.addItem(f"{display}  (pip install qdarkstyle)")
                else:
                    self.theme_combo.addItem(display)
                self._theme_keys.append(key)

        if lang == "ar":
            for key, display in AVAILABLE_THEMES_AR.items():
                needs_pkg = key in ("dark", "light")
                if needs_pkg and not _has_qdarkstyle:
                    self.theme_combo.addItem(f"{display}  (pip install qdarkstyle)")
                else:
                    self.theme_combo.addItem(display)
                self._theme_keys.append(key)                

        current_theme = getattr(self.main_window, 'app_theme', 'default')
        if current_theme in self._theme_keys:
            self.theme_combo.setCurrentIndex(self._theme_keys.index(current_theme))

        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        theme_layout.addWidget(theme_label, 0, 0)
        theme_layout.addWidget(self.theme_combo, 0, 1)
        layout.addWidget(theme_group)

        # Output Tabs Group
        output_group = QGroupBox(tr.get("ui_output_group", "Output Tabs Configuration"))
        output_layout = QGridLayout(output_group)

        self.output_visible_check = QCheckBox(tr.get("ui_output_visible", "Show Output/Error tabs"))
        self.output_visible_check.setToolTip(tr.get("ui_output_tooltip", "Main output container with Output and Error tabs"))
        output_layout.addWidget(self.output_visible_check, 0, 0, 1, 2)

        sub_tabs_label = QLabel(tr.get("ui_subtabs_label", "Additional tabs (require Output/Error to be visible):"))
        sub_tabs_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        output_layout.addWidget(sub_tabs_label, 1, 0, 1, 2)

        self.symbols_visible_check = QCheckBox(tr.get("ui_symbols_tab", "Show Symbols tab"))
        self.commands_visible_check = QCheckBox(tr.get("ui_commands_tab", "Show Commands tab"))
        self.tree_visible_check = QCheckBox(tr.get("ui_tree_tab", "Show Tree tab"))
        self.bookmarks_visible_check = QCheckBox(tr.get("ui_bookmarks_tab", "Show Bookmarks tab"))
        self.terminal_visible_check = QCheckBox(tr.get("ui_terminal_tab", "Show Terminal tab"))

        output_layout.addWidget(self.symbols_visible_check, 2, 0)
        output_layout.addWidget(self.commands_visible_check, 3, 0)
        output_layout.addWidget(self.tree_visible_check, 4, 0)
        output_layout.addWidget(self.bookmarks_visible_check, 5, 0)
        output_layout.addWidget(self.terminal_visible_check, 6, 0)

        output_layout.setColumnStretch(1, 1)

        self.output_visible_check.toggled.connect(self.on_output_toggled)
        self.symbols_visible_check.toggled.connect(self.on_sub_tab_toggled)
        self.commands_visible_check.toggled.connect(self.on_sub_tab_toggled)
        self.tree_visible_check.toggled.connect(self.on_sub_tab_toggled)
        self.bookmarks_visible_check.toggled.connect(self.on_sub_tab_toggled)
        self.terminal_visible_check.toggled.connect(self.on_sub_tab_toggled)

        layout.addWidget(output_group)

        # Line numbers and fold markers
        line_fold_group = QGroupBox(tr.get("ui_line_fold_group", "Line numbers and fold markers"))
        line_fold_layout = QGridLayout(line_fold_group)

        self.line_numbers_check = QCheckBox(tr.get("ui_line_numbers", "Show line numbers"))
        self.line_numbers_check.toggled.connect(self._on_line_numbers_toggled)
        line_fold_layout.addWidget(self.line_numbers_check, 0, 0, 1, 2)

        self.fold_marker_check = QCheckBox(tr.get("ui_fold_markers", "Show fold markers"))
        self.fold_marker_check.toggled.connect(self._on_fold_markers_toggled)
        line_fold_layout.addWidget(self.fold_marker_check, 1, 0, 1, 2)

        layout.addWidget(line_fold_group)
        layout.addStretch()

        scrollable = self._make_scrollable(tab)
        return scrollable

    def _on_theme_changed(self, index):
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from style_manager import apply_theme, get_completer_stylesheet

        theme_key = self._theme_keys[index]
        app = QApplication.instance()
        if not app:
            return

        success = apply_theme(app, theme_key)
        if not success:
            QMessageBox.warning(
                self, "Missing dependency",
                "This theme requires qdarkstyle.\n\n"
                "Install it with:\n    pip install qdarkstyle\n\n"
                "Then restart the application."
            )
            current = getattr(self.main_window, 'app_theme', 'default')
            if current in self._theme_keys:
                self.theme_combo.blockSignals(True)
                self.theme_combo.setCurrentIndex(self._theme_keys.index(current))
                self.theme_combo.blockSignals(False)
            return

        self.main_window.app_theme = theme_key
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value('ui', 'app_theme', theme_key)

        # ✅ Refresh all themed buttons
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.refresh_button_styles()
        if hasattr(self.main_window, 'side_panel'):
            self.main_window.side_panel.refresh_button_styles()
            
        # After refreshing toolbar_manager and side_panel, add:
        if hasattr(self.main_window, '_tools_tabs'):
            for tools_tab in self.main_window._tools_tabs:
                if hasattr(tools_tab, 'refresh_button_styles'):
                    tools_tab.refresh_button_styles()      
 
##
        # Refresh DocumentTreeWidget — finds it anywhere in the hierarchy
        from toolbar_manager import DocumentTreeWidget
        for tree in self.main_window.findChildren(DocumentTreeWidget):
            tree.refresh_theme()
##
 
        # After refreshing toolbar_manager, side_panel, tools_tabs — add:
        if hasattr(self.main_window, '_todo_tabs'):
            for todo_app in self.main_window._todo_tabs:
                if hasattr(todo_app, 'refresh_styles'):
                    todo_app.refresh_styles()               
                    
        # Refresh all open editors' line number areas
        if hasattr(self.main_window.editor_manager, 'get_all_editors'):
            for editor in self.main_window.editor_manager.get_all_editors():
                if hasattr(editor, 'lineNumberArea'):
                    editor.lineNumberArea.update()
                if hasattr(editor, 'highlightCurrentLine'):
                    editor.highlightCurrentLine()
                if hasattr(editor, 'viewport'):
                    editor.viewport().update()            
                    
        # Refresh welcome pages (they are recreated on next open,
        # but refresh any currently visible ones)
        if hasattr(self.main_window, 'layout_manager'):
            lm = self.main_window.layout_manager
            # Refresh editor welcome if visible
            for obj_name in ("editor_welcome_outer_frame", "pdf_welcome_outer_frame"):
                from style_manager import get_welcome_style
                w = get_welcome_style()
                widgets = self.main_window.findChildren(QFrame, obj_name)
                for frame in widgets:
                    frame.setStyleSheet(f"""
                        QFrame#{obj_name} {{
                            background-color: {w['outer_bg']};
                            border: 1px solid {w['outer_border']};
                        }}
                    """)

        # Refresh annotation toolbar in all open PDF viewers
        if hasattr(self.main_window, 'pdf_manager'):
            pm = self.main_window.pdf_manager
            if hasattr(pm, 'pdf_viewers'):
                for viewer in pm.pdf_viewers.values():
                    if hasattr(viewer, '_apply_annotation_toolbar_theme'):
                        viewer._apply_annotation_toolbar_theme()     

###
        # ✅ SAFE: Restyle welcome pages in place, never rebuild or switch layouts
        if hasattr(self.main_window, 'layout_manager'):
            self.main_window.layout_manager.refresh_welcome_pages()

        # ✅ SAFE: Restyle PDF welcome if visible, never call _show_pdf_welcome_tab
        if hasattr(self.main_window, 'pdf_manager'):
            pm = self.main_window.pdf_manager
            if hasattr(pm, 'pdf_tabs') and pm.pdf_tabs:
                from style_manager import get_welcome_style
                w = get_welcome_style()
                pm.pdf_tabs.setStyleSheet(f"""
                    QTabWidget::pane {{
                        border: none;
                        background-color: {w['tab_pane_bg']};
                    }}
                """)
                for i in range(pm.pdf_tabs.count()):
                    widget = pm.pdf_tabs.widget(i)
                    if widget and widget.objectName() == "pdf_welcome_widget":
                        self.main_window.layout_manager._restyle_welcome_frame(
                            widget, w, "pdf"
                        )
                        break
####

            # ✅ Adapt syntax highlight colors to the new theme
            self.reset_colors_to_default()
            self.apply_colors_to_highlighter()      

            # ✅ Refresh settings dialog widgets that have inline stylesheets
            self._apply_ai_info_style()

            # Refresh side panel settings widget if it's open
            for tab_idx in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(tab_idx)
                # unwrap scrollarea if needed
                inner = widget
                if hasattr(widget, 'widget'):
                    inner = widget.widget()
                if isinstance(inner, SidePanelSettingsWidget):
                    inner.refresh_theme()
                         
            # Refresh AI Assistant tabs
            if hasattr(self.main_window, '_ai_tabs'):
                for ai_tab in self.main_window._ai_tabs:
                    if hasattr(ai_tab, 'refresh_styles'):
                        try:
                            ai_tab.refresh_styles()
                        except RuntimeError:
                            pass  # Widget may have been closed            
                            
            # Refresh completer popups on all open editors
            if hasattr(self.main_window, 'editor_manager'):
                em = self.main_window.editor_manager
                if hasattr(em, 'get_all_editors'):
                    for editor in em.get_all_editors():
                        cwl = getattr(editor, '_cwl_completer', None)
                        if cwl:
                            cwl.completer.popup().setStyleSheet(get_completer_stylesheet("cwl"))
                        ref = getattr(editor, '_refcite_completer', None)
                        if ref:
                            ref.completer.popup().setStyleSheet(get_completer_stylesheet("ref"))


            if hasattr(self.main_window, '_tools_tabs'):
                for tools_tab in self.main_window._tools_tabs:
                    if hasattr(tools_tab, 'refresh_styles'):
                        tools_tab.refresh_styles()
                        
            if hasattr(self.main_window, 'errors_text'):
                self.main_window._apply_error_text_style()
                        
                
    def load_recent_files_display(self):
        """Load and display recent files in the settings dialog"""
        try:
            if hasattr(self.main_window, 'config_manager') and hasattr(self, 'recent_list'):
                recent_files = self.main_window.config_manager.get_recent_files()
                self.recent_list.clear()
                if recent_files:
                    for path in recent_files:
                        filename = os.path.basename(path)
                        self.recent_list.addItem(filename)
                    #print(f"📋 Updated recent files display: {len(recent_files)} total files")
                else:
                    self.recent_list.addItem("No recent files")
        except Exception as e:
            print(f"❌ Error loading recent files display: {e}")
    

    def clear_recent_files(self):
        """Clear recent files list"""
        config_manager = self.main_window.config_manager

        # Clear recent files
        for section in ['recent_files', 'session_files']:
            if config_manager.config.has_section(section):
                config_manager.config.remove_section(section)
            config_manager.config.add_section(section)  # ensure section exists

        # Save using the correct method
            if hasattr(config_manager, 'recent_files'):
                config_manager.save_session_files(open_files)
                #print(f"💾 Session saved on close with {len(open_files)} files")
            else:
                print("⚠️  save_session_files method not found")
        # Save using the correct method
            if hasattr(config_manager, 'session_files'):
                config_manager.save_session_files(open_files)
                #print(f"💾 Session saved on close with {len(open_files)} files")
            else:
                print("⚠️  save_session_files method not found")

        # Update display
        if self.recent_list:
            self.recent_list.clear()
            self.recent_list.addItem("Recent files cleared")

                    
    def _on_line_numbers_toggled(self, checked):
        """Handle line numbers checkbox toggle"""
        if self._loading_settings:
            return
        #print(f"Settings: line_numbers_check toggled to {checked}")
        if hasattr(self.main_window, 'menu_manager'):
            self.main_window.menu_manager.toggle_line_numbers(checked)

    def _on_fold_markers_toggled(self, checked):
        """Handle fold markers checkbox toggle"""
        if self._loading_settings:
            return
        #print(f"Settings: fold_marker_check toggled to {checked}")
        if hasattr(self.main_window, 'menu_manager'):
            self.main_window.menu_manager.toggle_fold_markers(checked)    
            
    def on_output_toggled(self, checked):
        """Handle main output checkbox toggle"""
        if self._loading_settings:
            return
            
        # Update sub-tab states
        self._update_sub_tab_states(checked)
        
        # Call on_setting_changed if it exists
        if hasattr(self, 'on_setting_changed'):
            self.on_setting_changed()

    def on_sub_tab_toggled(self, checked):
        """Handle sub-tab checkbox toggle"""
        if self._loading_settings:
            return
            
        # If any sub-tab is checked, ensure output is checked
        if checked and not self.output_visible_check.isChecked():
            self.output_visible_check.blockSignals(True)
            self.output_visible_check.setChecked(True)
            self.output_visible_check.blockSignals(False)
            
        # Call on_setting_changed if it exists
        if hasattr(self, 'on_setting_changed'):
            self.on_setting_changed()

    def _update_sub_tab_states(self, output_enabled):
        """Update sub-tab checkbox states and enabled status"""
        sub_boxes = [
            self.symbols_visible_check,
            self.commands_visible_check,
            self.tree_visible_check,
            self.bookmarks_visible_check,
            self.terminal_visible_check,
        ]
        
        if output_enabled:
            # Enable all sub-tabs
            for box in sub_boxes:
                box.setEnabled(True)
        else:
            # Disable and uncheck all sub-tabs
            for box in sub_boxes:
                box.blockSignals(True)
                box.setChecked(False)
                box.setEnabled(False)
                box.blockSignals(False)
        

    def load_current_settings(self):
        """Load current settings from main window into dialog controls"""
        try:
            # Load AI settings
            ai_mode = self.main_window.config_manager.get_config_value('ai', 'mode', 'offline')
            ai_provider = self.main_window.config_manager.get_config_value('ai', 'provider', 'groq')
            ai_api_key = self.main_window.config_manager.get_config_value('ai', 'api_key', '')
            ai_model = self.main_window.config_manager.get_config_value('ai', 'model', '')
            
            # Set AI mode
            index = self.ai_mode_combo.findData(ai_mode)
            if index >= 0:
                self.ai_mode_combo.setCurrentIndex(index)
            
            # Set provider
            index = self.ai_provider_combo.findData(ai_provider)
            if index >= 0:
                self.ai_provider_combo.setCurrentIndex(index)
            
            # Set API key
            self.ai_api_key.setText(ai_api_key)
            
            # Set model
            if ai_model:
                index = self.ai_model_combo.findText(ai_model)
                if index >= 0:
                    self.ai_model_combo.setCurrentIndex(index)
            # Load engine selection
            #self.engine_combo.setCurrentText(self.main_window.latex_engine)
            #self.backmatter_combo.setCurrentText(self.main_window.backmatter_engine)
            idx = self.engine_combo.findData(self.main_window.latex_engine)
            self.engine_combo.setCurrentIndex(idx if idx >= 0 else 0)
            idx = self.backmatter_combo.findData(self.main_window.backmatter_engine)
            self.backmatter_combo.setCurrentIndex(idx if idx >= 0 else 0)            
            
            self.encoding_combo.setCurrentText(self.main_window.output_encoding)
            
            # Connect to toolbar update
            current_latex_engine = self.engine_combo.currentText()
            self.engine_combo.currentTextChanged.connect(self.main_window.toolbar_manager.update_compile_button_text)
            
            # Load latex command
            latex_command = getattr(self.main_window, f'{current_latex_engine}_option', None)
            if latex_command:
                self.command_text.setText(latex_command)
            else:
                self.command_text.setText(self.default_latex_commands.get(current_latex_engine, ""))
            
            # Load backmatter command
            current_backmatter_engine = self.backmatter_combo.currentText()
            backmatter_command = getattr(self.main_window, f'{current_backmatter_engine}_option', None)
            if backmatter_command:
                self.backmatter_command_text.setText(backmatter_command)
            else:
                self.backmatter_command_text.setText(self.default_backmatter_commands.get(current_backmatter_engine, ""))

            
            # Get actual states from main window
            output_visible = self.main_window.get_actual_output_state()
            symbols_visible = self.main_window.get_actual_symbols_state()
            commands_visible = self.main_window.get_actual_commands_state()
            tree_visible = self.main_window.get_actual_tree_state()
            bookmarks_visible = self.main_window.get_actual_bookmarks_state()
            terminal_visible = self.main_window.get_actual_terminal_state()
            
            #print(f"Loading settings - Output: {output_visible}, Symbols: {symbols_visible}, Commands: {commands_visible}, Tree: {tree_visible}, Bookmarks: {bookmarks_visible}")
            
            # Set checkbox states
            if self.output_visible_check:
                self.output_visible_check.setChecked(output_visible)
            if self.symbols_visible_check:
                self.symbols_visible_check.setChecked(symbols_visible)
            if self.commands_visible_check:
                self.commands_visible_check.setChecked(commands_visible)
            if self.tree_visible_check:
                self.tree_visible_check.setChecked(tree_visible)
            if self.bookmarks_visible_check:
                self.bookmarks_visible_check.setChecked(bookmarks_visible)
            if self.terminal_visible_check:
                self.terminal_visible_check.setChecked(terminal_visible)
            
            # Update sub-tab enabled states
            self._update_sub_tab_states(output_visible)
            

            
            # Load layout settings
            if self.switch_combo and hasattr(self.main_window, 'layout_manager'):
                current_layout = getattr(self.main_window.layout_manager, 'current_layout', 'editor_left')
                index = self.switch_combo.findText(current_layout)
                if index >= 0:
                    self.switch_combo.setCurrentIndex(index)
                #print(f"  Switch layout: {current_layout}")
            
            if self.editor_layout_combo and hasattr(self.main_window, 'editor_manager'):
                editor_mode = getattr(self.main_window.editor_manager, 'editor_layout_mode', 'tabbed')
                index = self.editor_layout_combo.findText(editor_mode)
                if index >= 0:
                    self.editor_layout_combo.setCurrentIndex(index)
                #print(f"  Editor layout: {editor_mode}")
            
            if self.pdf_layout_combo and hasattr(self.main_window, 'pdf_manager'):
                pdf_mode = getattr(self.main_window.pdf_manager, 'pdf_layout_mode', 'tabbed')
                index = self.pdf_layout_combo.findText(pdf_mode)
                if index >= 0:
                    self.pdf_layout_combo.setCurrentIndex(index)
                #print(f"  PDF layout: {pdf_mode}")
            
           
            # Load UI settings
            if self.menu_lang_combo and hasattr(self.main_window, 'menu_language'):
                current_lang = self.main_window.menu_language
                index = self.menu_lang_combo.findText(current_lang)
                if index >= 0:
                    self.menu_lang_combo.setCurrentIndex(index)
                #print(f"  Language: {current_lang}")
            
            if self.rtl_check and hasattr(self.main_window, 'is_rtl'):
                self.rtl_check.setChecked(self.main_window.is_rtl)
                #print(f"  RTL: {self.main_window.is_rtl}")



            # Load line numbers and fold markers
            if self.line_numbers_check:
                is_visible = getattr(self.main_window, 'is_line_numbers_visible', True)
                #print(f"Loading line_numbers_check: {is_visible}")
                self.line_numbers_check.setChecked(is_visible)
            
            if self.fold_marker_check:
                is_visible = getattr(self.main_window, 'is_fold_markers_visible', True)
                #print(f"Loading fold_marker_check: {is_visible}")
                self.fold_marker_check.setChecked(is_visible)
            
            
            # Load auto-load setting from config
            if self.auto_load_check and hasattr(self.main_window, 'config_manager'):
                auto_load_str = self.main_window.config_manager.get_config_value('ui', 'auto_load_last_file', 'True')
                auto_load = str(auto_load_str).lower() == 'true'
                self.auto_load_check.setChecked(auto_load)
                #print(f"  Auto-load: {auto_load}")
            
            # Load recent files for display
            if hasattr(self.main_window, 'config_manager') and hasattr(self, 'recent_list'):
                recent_files = self.main_window.config_manager.get_recent_files()
                self.recent_list.clear()
                if recent_files:
                    for path in recent_files:
                        filename = os.path.basename(path)
                        self.recent_list.addItem(filename)
                    #print(f"?? Updated recent files display: {len(recent_files)} total files")
                else:
                    self.recent_list.addItem("No recent files")
            # Load color settings
            self.load_color_settings()
            
            self._loading_settings = False

            # ADD THIS SECTION - Load font settings
            # Get current font settings from main window
            current_fonts = self.main_window.get_current_font_settings()
            
            # Set editor font family
            editor_font_family = current_fonts.get('editor_font_family', 'Consolas')
            index = self.editor_font_combo.findText(editor_font_family)
            if index >= 0:
                self.editor_font_combo.setCurrentIndex(index)
            else:
                # If exact match not found, try to set it directly
                self.editor_font_combo.setCurrentFont(QFont(editor_font_family))
            
            # Set editor font size
            editor_font_size = current_fonts.get('editor_font_size', 11)
            self.editor_font_spin.setValue(int(editor_font_size))
            
            # Set UI font family
            ui_font_family = current_fonts.get('ui_font_family', 'Arial')
            index = self.ui_font_combo.findText(ui_font_family)
            if index >= 0:
                self.ui_font_combo.setCurrentIndex(index)
            else:
                self.ui_font_combo.setCurrentFont(QFont(ui_font_family))
            
            # Set toolbar/UI font size
            toolbar_font_size = current_fonts.get('toolbar_font_size', 10)
            self.toolbar_font_spin.setValue(int(toolbar_font_size))
            
            #print(f"Loaded font settings: Editor={editor_font_family}/{editor_font_size}, UI={ui_font_family}/{toolbar_font_size}")


            # ADD this at the end before the final except block:
            # Load completion settings
            self.load_completion_settings()
            
            self._loading_settings = False
            
            #print("=== Current Settings Loaded ===")
            
        except Exception as e:
            self._loading_settings = False  # ✅ Always reset flag
            print(f"❌ Error loading current settings: {e}")
            import traceback
            traceback.print_exc()


        
    # def create_side_panel_tab(self):
        # """Create the side panel configuration tab"""
        # self.side_panel_widget = SidePanelSettingsWidget(self.main_window)
        
        # # Connect change signal to enable immediate apply
        # self.side_panel_widget.commandsChanged.connect(self._on_side_panel_changed)
        
        # scrollable = self._make_scrollable(self.side_panel_widget)
        # #self.tab_widget.addTab(scrollable, "Side Panel")

        # return scrollable   
        
    def create_side_panel_tab(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        self.side_panel_widget = SidePanelSettingsWidget(self.main_window, tr)
        self.side_panel_widget.commandsChanged.connect(self._on_side_panel_changed)
        scrollable = self._make_scrollable(self.side_panel_widget)
        return scrollable        

    def _on_side_panel_changed(self, commands):
        self.main_window.side_panel.set_commands(commands)
        self.main_window._register_side_panel_shortcuts()  # ← ADD THIS    
                
    def accept(self):
        """Override accept to apply settings before closing"""
        #print("Accept button clicked")
        # Just save settings - save_settings() handles everything
        self.save_settings()
        super().accept()

    def apply_settings(self):
        """Apply settings without closing dialog"""
        #print("Apply button clicked")
        
        # Apply side panel settings immediately
        if hasattr(self, 'side_panel_widget'):
            commands = self.side_panel_widget.get_commands()
            # Apply to side panel (this will also save)
            self.main_window.side_panel.set_commands(commands, save=True)
            #print(f"Applied {len(commands)} commands to side panel")

        # Just save settings - save_settings() handles everything
        self.save_settings()


    def _apply_tab_visibility_changes(self, layout_settings):
        """Apply tab visibility changes to the main window and sync with toolbar"""
        # Apply output visibility first
        if 'output_tabs_visible' in layout_settings:
            current_output_state = self.main_window.get_actual_output_state()
            new_output_state = layout_settings['output_tabs_visible']
            
            if current_output_state != new_output_state:
                #print(f"Changing output visibility: {current_output_state} -> {new_output_state}")
                self.main_window.toggle_output_tabs(force_state=new_output_state)
        
        # Apply sub-tab visibility only if output is visible
        if layout_settings.get('output_tabs_visible', False):
            # Apply symbols tab
            if 'symbols_tab_visible' in layout_settings:
                current_state = self.main_window.get_actual_symbols_state()
                new_state = layout_settings['symbols_tab_visible']
                if current_state != new_state:
                    #print(f"Changing symbols visibility: {current_state} -> {new_state}")
                    self.main_window.toggle_symbols_tab(force_state=new_state)
                    # Sync toolbar button
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.symbols_tab_visible = new_state
                        if hasattr(self.main_window.toolbar_manager, 'symbols_action'):
                            self.main_window.toolbar_manager.symbols_action.setChecked(new_state)
            
            # Apply commands tab
            if 'commands_tab_visible' in layout_settings:
                current_state = self.main_window.get_actual_commands_state()
                new_state = layout_settings['commands_tab_visible']
                if current_state != new_state:
                    #print(f"Changing commands visibility: {current_state} -> {new_state}")
                    self.main_window.toggle_commands_tab(force_state=new_state)
                    # Sync toolbar button
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.commands_tab_visible = new_state
                        if hasattr(self.main_window.toolbar_manager, 'commands_action'):
                            self.main_window.toolbar_manager.commands_action.setChecked(new_state)
            
            # Apply tree tab
            if 'tree_tab_visible' in layout_settings:
                current_state = self.main_window.get_actual_tree_state()
                new_state = layout_settings['tree_tab_visible']
                if current_state != new_state:
                    #print(f"Changing tree visibility: {current_state} -> {new_state}")
                    self.main_window.toggle_tree_tab(force_state=new_state)
                    # Sync toolbar button
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.tree_tab_visible = new_state
                        if hasattr(self.main_window.toolbar_manager, 'tree_action'):
                            self.main_window.toolbar_manager.tree_action.setChecked(new_state)
            
            # Apply bookmarks tab
            if 'bookmarks_tab_visible' in layout_settings:
                current_state = self.main_window.get_actual_bookmarks_state()
                new_state = layout_settings['bookmarks_tab_visible']
                if current_state != new_state:
                    #print(f"Changing bookmarks visibility: {current_state} -> {new_state}")
                    self.main_window.toggle_bookmarks_tab()
                    # Sync toolbar button
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.bookmarks_tab_visible = new_state
                        if hasattr(self.main_window.toolbar_manager, 'bookmarks_action'):
                            self.main_window.toolbar_manager.bookmarks_action.setChecked(new_state)
            
            
            # Apply Terminal tab
            if 'terminal_tab_visible' in layout_settings:
                current_state = self.main_window.get_actual_terminal_state()
                new_state = layout_settings['terminal_tab_visible']
                if current_state != new_state:
                    #print(f"Changing terminal visibility: {current_state} -> {new_state}")
                    self.main_window.toolbar_manager.toggle_terminal_tab()
                    # Sync toolbar button
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.terminal_tab_visible = new_state
                        if hasattr(self.main_window.toolbar_manager, 'terminal_action'):
                            self.main_window.toolbar_manager.terminal_action.setChecked(new_state)

        else:
            # If output is not visible, hide all sub-tabs and update toolbar
            for tab_type in ['symbols', 'commands', 'tree', 'bookmarks', 'terminal']:
                setattr(self.main_window, f'{tab_type}_tab_visible', False)
                if hasattr(self.main_window, 'toolbar_manager'):
                    setattr(self.main_window.toolbar_manager, f'{tab_type}_tab_visible', False)
                    action_attr = f'{tab_type}_action'
                    if hasattr(self.main_window.toolbar_manager, action_attr):
                        getattr(self.main_window.toolbar_manager, action_attr).setChecked(False)
 
    def save_settings(self):
        """Save and apply all settings from the dialog - COMPLETELY REWRITTEN"""
        #print("=== SAVE SETTINGS DEBUG ===")
        try:
            # ADD THIS SECTION at the beginning - Collect and apply font settings
            font_settings = {
                'editor_font_family': self.editor_font_combo.currentFont().family(),
                'editor_font_size': self.editor_font_spin.value(),
                'ui_font_family': self.ui_font_combo.currentFont().family(),
                'toolbar_font_size': self.toolbar_font_spin.value()
            }
            
            #print(f"Saving font settings: {font_settings}")
            
            # Apply font settings to main window
            self.main_window.apply_font_settings(font_settings)
            
            # Save font settings to config
            if hasattr(self.main_window, 'config_manager'):
                config_mgr = self.main_window.config_manager
                config_mgr.set_config_value('ui', 'editor_font_family', font_settings['editor_font_family'])
                config_mgr.set_config_value('ui', 'editor_font_size', str(font_settings['editor_font_size']))
                config_mgr.set_config_value('ui', 'ui_font_family', font_settings['ui_font_family'])
                config_mgr.set_config_value('ui', 'toolbar_font_size', str(font_settings['toolbar_font_size']))


            
            # Save and apply AI settings
            ai_mode = self.ai_mode_combo.currentData()
            ai_provider = self.ai_provider_combo.currentData()
            ai_api_key = self.ai_api_key.text().strip()
            ai_model = self.ai_model_combo.currentText()
            
            self.main_window.config_manager.set_config_value('ai', 'mode', ai_mode)
            self.main_window.config_manager.set_config_value('ai', 'provider', ai_provider)
            self.main_window.config_manager.set_config_value('ai', 'api_key', ai_api_key)
            self.main_window.config_manager.set_config_value('ai', 'model', ai_model)
            
            # Apply to all open AI tabs
            if hasattr(self.main_window, '_ai_tabs') and self.main_window._ai_tabs:
                for ai_widget in self.main_window._ai_tabs:
                    if hasattr(ai_widget, 'set_online_mode'):
                        ai_widget.set_online_mode(
                            enabled=(ai_mode == "online"),
                            provider=ai_provider,
                            api_key=ai_api_key if ai_api_key else None,
                            model=ai_model
                        )                                
            # Apply color settings
            self.save_color_settings()
            self.apply_colors_to_highlighter()
            
            # ADD this section before the final config save:
            # Save completion settings
            self.save_completion_settings()
                        
            # --- Collect Layout Settings ---
            layout_settings = {}
            
            if self.switch_combo:
                layout_settings['current_layout'] = self.switch_combo.currentText()
            
            if self.editor_layout_combo:
                layout_settings['editor_layout_mode'] = self.editor_layout_combo.currentText()
            
            if self.pdf_layout_combo:
                layout_settings['pdf_layout_mode'] = self.pdf_layout_combo.currentText()
            
           # Collect layout settings
            layout_settings = {}
            
            # Get visibility states from checkboxes
            output_visible = self.output_visible_check.isChecked() if self.output_visible_check else True
            symbols_visible = self.symbols_visible_check.isChecked() if self.symbols_visible_check else False
            commands_visible = self.commands_visible_check.isChecked() if self.commands_visible_check else False
            tree_visible = self.tree_visible_check.isChecked() if self.tree_visible_check else False
            bookmarks_visible = self.bookmarks_visible_check.isChecked() if self.bookmarks_visible_check else False
            terminal_visible = self.terminal_visible_check.isChecked() if self.terminal_visible_check else False

           
            layout_settings['output_tabs_visible'] = output_visible
            layout_settings['symbols_tab_visible'] = symbols_visible
            layout_settings['commands_tab_visible'] = commands_visible
            layout_settings['tree_tab_visible'] = tree_visible
            layout_settings['bookmarks_tab_visible'] = bookmarks_visible
            layout_settings['terminal_tab_visible'] = terminal_visible

           
            #print(f"Saving settings: {layout_settings}")
            
            # Apply changes to main window
            self._apply_tab_visibility_changes(layout_settings)
 
             # Save to config
            if hasattr(self.main_window, 'config_manager'):
                config_mgr = self.main_window.config_manager
                
                # Save layout settings
                for key, value in layout_settings.items():
                    config_mgr.set_config_value('layout', key, str(value))
                

            
            # --- Collect UI Settings ---
            ui_settings = {}
            
            if self.menu_lang_combo:
                ui_settings['menu_language'] = self.menu_lang_combo.currentText()
            
            if self.rtl_check:
                ui_settings['is_rtl'] = self.rtl_check.isChecked()

            # Collect UI settings properly
            if self.line_numbers_check:
                ui_settings['is_line_numbers_visible'] = self.line_numbers_check.isChecked()

            if self.fold_marker_check:
                ui_settings['is_fold_markers_visible'] = self.fold_marker_check.isChecked()


            
            if self.auto_load_check:
                ui_settings['auto_load_last_file'] = self.auto_load_check.isChecked()
            
            #print(f"Layout settings from dialog: {layout_settings}")
            #print(f"UI settings: {ui_settings}")
            
            # --- Apply Layout Settings (with debugging) ---
            if 'current_layout' in layout_settings and hasattr(self.main_window, 'layout_manager'):
                old_layout = getattr(self.main_window.layout_manager, 'current_layout', 'editor_left')
                new_layout = layout_settings['current_layout']
                self.main_window.layout_manager.current_layout = new_layout
                
                if old_layout != new_layout:
                    #print(f"Applied main layout change: {old_layout} -> {new_layout}")
                    # Try to apply the layout change
                    for method_name in ['set_current_layout', 'apply_layout', 'switch_layout']:
                        if hasattr(self.main_window.layout_manager, method_name):
                            try:
                                getattr(self.main_window.layout_manager, method_name)(new_layout)
                                #print(f"  Called {method_name}({new_layout})")
                                break
                            except Exception as e:
                                print(f"  Error calling {method_name}: {e}")
            
            if 'editor_layout_mode' in layout_settings and hasattr(self.main_window, 'editor_manager'):
                old_mode = getattr(self.main_window.editor_manager, 'editor_layout_mode', 'tabbed')
                new_mode = layout_settings['editor_layout_mode']
                self.main_window.editor_manager.editor_layout_mode = new_mode
                
                if old_mode != new_mode:
                    #print(f"Applied editor layout change: {old_mode} -> {new_mode}")
                    # Try to apply the layout change
                    for method_name in ['set_layout_mode', 'toggle_layout', 'apply_editor_layout']:
                        if hasattr(self.main_window.editor_manager, method_name):
                            try:
                                getattr(self.main_window.editor_manager, method_name)(new_mode)
                                #print(f"  Called editor_manager.{method_name}({new_mode})")
                                break
                            except Exception as e:
                                print(f"  Error calling editor {method_name}: {e}")
            
            if 'pdf_layout_mode' in layout_settings and hasattr(self.main_window, 'pdf_manager'):
                old_mode = getattr(self.main_window.pdf_manager, 'pdf_layout_mode', 'tabbed')
                new_mode = layout_settings['pdf_layout_mode']
                self.main_window.pdf_manager.pdf_layout_mode = new_mode
                
                if old_mode != new_mode:
                    #print(f"Applied PDF layout change: {old_mode} -> {new_mode}")
                    # Try to apply the layout change
                    for method_name in ['set_layout_mode', 'toggle_layout', 'apply_pdf_layout']:
                        if hasattr(self.main_window.pdf_manager, method_name):
                            try:
                                getattr(self.main_window.pdf_manager, method_name)(new_mode)
                                #print(f"  Called pdf_manager.{method_name}({new_mode})")
                                break
                            except Exception as e:
                                print(f"  Error calling pdf {method_name}: {e}")
            
            # --- Apply UI Settings ---
            old_lang = getattr(self.main_window, 'menu_language', 'en')
            if 'menu_language' in ui_settings:
                new_lang = ui_settings['menu_language']
                self.main_window.menu_language = new_lang
                #if old_lang != new_lang:
                #    print(f"Language changed from {old_lang} to {new_lang}")
            
            if 'is_rtl' in ui_settings:
                old_rtl = getattr(self.main_window, 'is_rtl', False)
                new_rtl = ui_settings['is_rtl']
                self.main_window.is_rtl = new_rtl
                #if old_rtl != new_rtl:
                #    print(f"RTL changed from {old_rtl} to {new_rtl}")
            
            if 'auto_load_last_file' in ui_settings:
                self.main_window.auto_load_last_file = ui_settings['auto_load_last_file']
            
            # --- Apply Output Visibility - CRITICAL ---
            if 'output_tabs_visible' in layout_settings:
                current_state = self.main_window.get_actual_output_state()
                new_state = layout_settings['output_tabs_visible']
                if current_state != new_state:
                    #print(f"Output visibility needs change: {current_state} -> {new_state}")
                    self.main_window.toggle_output_tabs(force_state=new_state)
                    #
                    if 'symbols_tabs_visible' in layout_settings:
                        current_symbol_state = self.main_window.get_actual_symbols_state()
                        new_symbol_state = layout_settings['symbols_tab_visible']
                        if current_symbols_state != new_symbols_state:
                            #print(f"Output visibility needs change: {new_symbols_state} -> {new_symbols_state}")
                            self.main_window.symbols(force_state=new_symbols_state)
                        #else:
                        #    print(f"Symbols visibility unchanged: {new_symbols_state}")
                    #
                    if 'commands_tab_visible' in layout_settings:
                        current_commands_state = self.main_window.get_actual_commands_state()
                        new_symbol_state = layout_settings['commands_tab_visible']
                        if current_commands_state != new_commands_state:
                            #print(f"Output visibility needs change: {new_commands_state} -> {new_commands_state}")
                            self.main_window.toggle_commands_tab(force_state=new_commands_state)
                        #else:
                        #    print(f"Commands visibility unchanged: {new_commands_state}")
                    #
                    if 'tree_tab_visible' in layout_settings:
                        current_tree_state = self.main_window.get_actual_tree_state()
                        new_tree_state = layout_settings['tree_tab_visible']
                        if current_tree_state != new_tree_state:
                            #print(f"Tree visibility needs change: {new_tree_state} -> {new_tree_state}")
                            self.main_window.toggle_tree_tab(force_state=new_tree_state)
                        #else:
                        #    print(f"Tree visibility unchanged: {new_tree_state}")
                    #
                    if 'bookmarks_tab_visible' in layout_settings:
                        current_bookmarks_state = self.main_window.get_actual_bookmarks_state()
                        new_bookmarks_state = layout_settings['bookmarks_tab_visible']
                        if current_bookmarks_state != new_bookmarks_state:
                            #print(f"Bookmarks visibility needs change: {new_bookmarks_state} -> {new_bookmarks_state}")
                            self.main_window.toggle_bookmarks_tab(force_state=new_bookmarks_state)
                        #else:
                        #    print(f"Boomarks visibility unchanged: {new_bookmarks_state}")
                    
                    if 'terminal_tab_visible' in layout_settings:
                        current_bookmarks_state = self.main_window.get_actual_terminal_state()
                        new_terminal_state = layout_settings['terminal_tab_visible']
                        if current_terminal_state != new_terminal_state:
                            #print(f"Terminal visibility needs change: {new_terminal_state} -> {new_terminal_state}")
                            self.main_window.toolbar_manager.toggle_terminal_tab(force_state=new_terminal_state)
                        #else:
                        #    print(f"Terminal visibility unchanged: {new_terminal_state}")



                #else:
                #    print(f"Output visibility unchanged: {current_state}")

            # Validate custom command if custom engine is selected
            current_engine = self.engine_combo.currentData()
            if current_engine == "custom":
                command = self.command_text.text()
                if hasattr(self.main_window, 'compilation_manager'):
                    is_valid, message = self.main_window.compilation_manager.validate_custom_command(command)
                    if not is_valid:
                        QMessageBox.warning(self, "Invalid Custom Command", f"Custom command validation failed:\n\n{message}")
                        return

            
            # Get the old engine to check if it changed
            old_engine = getattr(self.main_window, 'latex_engine', 'pdflatex')
            
            # Save engine selections
            self.main_window.latex_engine = self.engine_combo.currentData()
            self.main_window.backmatter_engine = self.backmatter_combo.currentData()
            self.main_window.output_encoding = self.encoding_combo.currentText()
            
            # Save command for current engine
            command_attr = f'{current_engine}_option'
            setattr(self.main_window, command_attr, self.command_text.text())
            
            # Save backmatter command
            current_backmatter = self.backmatter_combo.currentData()
            backmatter_attr = f'{current_backmatter}_option'
            setattr(self.main_window, backmatter_attr, self.backmatter_command_text.text())
            
            # Save to config if available
            if hasattr(self.main_window, 'config_manager'):
                config_mgr = self.main_window.config_manager
                config_mgr.set_config_value('compiler', 'latex_engine', self.main_window.latex_engine)
                config_mgr.set_config_value('compiler', 'backmatter_engine', self.main_window.backmatter_engine)
                config_mgr.set_config_value('encoding', 'output_encoding', self.main_window.output_encoding)
                config_mgr.set_config_value('compiler', command_attr, self.command_text.text())
                config_mgr.set_config_value('compiler', backmatter_attr, self.backmatter_command_text.text())
                
            
            
            # Update toolbar button if engine changed
            new_engine = self.main_window.latex_engine
            if old_engine != new_engine and hasattr(self.main_window, 'toolbar_manager'):
                self.main_window.toolbar_manager.update_engine_in_button(new_engine)
        
            
            # Save settings to config file
            if hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.save_current_settings()

            if hasattr(self, 'side_panel_widget'):
                commands = self.side_panel_widget.get_commands()
                # Apply to side panel
                self.main_window.side_panel.set_commands(commands)
                # Save to config
                if hasattr(self.main_window, 'config_manager'):
                    import json
                    self.main_window.config_manager.set_config_value(
                        'ui', 'side_panel_commands', json.dumps(commands)
                    )         

                    
            # --- Save all to config_manager ---
            config_mgr = self.main_window.config_manager
            
            # Save layout settings
            for key, value in layout_settings.items():
                config_mgr.set_config_value('layout', key, str(value))
            
            # Save UI settings
            for key, value in ui_settings.items():
                config_mgr.set_config_value('ui', key, str(value))
            
            #print("Config saved to latex_editor_config.ini")
            
            # --- SAFE UI Updates (NO menu recreation) ---
            
            # NEVER call update_menu_language - it destroys menus
            # Only update the output toggle action text
            if hasattr(self.main_window, 'menu_manager'):
                self.main_window.menu_manager._update_output_toggle_action()
            
            # Apply RTL text direction if needed and method exists
            if ('is_rtl' in ui_settings and ui_settings['is_rtl'] and 
                hasattr(self.main_window, 'apply_text_direction_to_editors')):
                self.main_window.apply_text_direction_to_editors()
                
            
            
            # ✅ Apply line numbers visibility (FIXED)
            if 'is_line_numbers_visible' in ui_settings:
                new_state = ui_settings['is_line_numbers_visible']
                self.main_window.is_line_numbers_visible = new_state
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager.toggle_line_numbers(new_state)

            # ✅ Apply fold markers visibility (FIXED)
            if 'is_fold_markers_visible' in ui_settings:
                new_state = ui_settings['is_fold_markers_visible']
                self.main_window.is_fold_markers_visible = new_state
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager.toggle_fold_markers(new_state)
        
            # Persist config to file
            config_mgr.save_config()

            
            #print("Settings saved and applied successfully")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to apply settings:\n{str(e)}")
        

            
    @staticmethod
    def load_settings_from_config(main_window):
        """Enhanced settings loading with backmatter custom commands"""
        if not hasattr(main_window, 'config_manager'):
            #print("No config manager available")
            return
        
        try:
            config_mgr = main_window.config_manager
            
            # Load compiler settings
            main_window.latex_engine = config_mgr.get_config_value('compiler', 'latex_engine', 'xelatex')
            main_window.backmatter_engine = config_mgr.get_config_value('compiler', 'backmatter_engine', 'bibtex')
            main_window.output_encoding = config_mgr.get_config_value('encoding', 'output_encoding', 'utf-8')
            
            # Load LaTeX engine options
            latex_engines = ['pdflatex', 'xelatex', 'lualatex', 'custom']
            default_latex_commands = {
                "pdflatex": "pdflatex -synctex=1 -interaction=nonstopmode -shell-escape",
                "xelatex": "xelatex -synctex=1 -interaction=nonstopmode -shell-escape",
                "lualatex": "lualatex -synctex=1 -interaction=nonstopmode -shell-escape"
            }
            
            for engine in latex_engines:
                option_attr = f'{engine}_option'
                default_cmd = default_latex_commands.get(engine, "")
                command = config_mgr.get_config_value('compiler', option_attr, default_cmd)
                setattr(main_window, option_attr, command)
            
            # Load backmatter engine options (enhanced)
            backmatter_engines = ['bibtex', 'biber', 'makeindex', 'xindy', 'makeglossaries', 'custom']
            default_backmatter_commands = {
                "bibtex": "bibtex %b",
                "biber": "biber %b",
                "makeindex": "makeindex %b.idx", 
                "xindy": "xindy -M texindy -L english %b.idx",
                "makeglossaries": "makeglossaries %b"
            }
            
            for engine in backmatter_engines:
                option_attr = f'backmatter_{engine}_option'
                default_cmd = default_backmatter_commands.get(engine, "")
                command = config_mgr.get_config_value('compiler', option_attr, default_cmd)
                setattr(main_window, option_attr, command)
            
            
            # Load layout settings
            if hasattr(main_window, 'layout_manager'):
                current_layout = config_mgr.get_config_value('layout', 'current_layout', 'editor_left')
                main_window.layout_manager.current_layout = current_layout
                switch_mode = config_mgr.get_config_value('layout', 'switch_mode', 'pdf_left')
                main_window.layout_manager.switch_mode = switch_mode
                editor_layout_mode = config_mgr.get_config_value('layout', 'editor_layout_mode', 'tabbed')
                main_window.layout_manager.editor_layout_mode = editor_layout_mode
                output_tabs_visible = config_mgr.get_config_value('layout', 'output_tabs_visible', 'True')
                main_window.layout_manager.output_tabs_visible = output_tabs_visible
                pdf_layout_mode = config_mgr.get_config_value('layout', 'pdf_layout_mode', 'tabbed')
                main_window.layout_manager.pdf_layout_mode = pdf_layout_mode
                symbols_tab_visible = config_mgr.get_config_value('layout', 'symbols_tab_visible', 'False')
                main_window.layout_manager.symbols_tab_visible = symbols_tab_visible
                commands_tab_visible = config_mgr.get_config_value('layout', 'commands_tab_visible', 'False')
                main_window.layout_manager.commands_tab_visible = commands_tab_visible
                tree_tab_visible = config_mgr.get_config_value('layout', 'tree_tab_visible', 'False')
                main_window.layout_manager.tree_tab_visible = tree_tab_visible
                bookmarks_tab_visible = config_mgr.get_config_value('layout', 'bookmarks_tab_visible', 'False')
                main_window.layout_manager.bookmarks_tab_visible = bookmarks_tab_visible
                terminal_tab_visible = config_mgr.get_config_value('layout', 'terminal_tab_visible', 'False')
                main_window.layout_manager.terminal_tab_visible = terminal_tab_visible


            
            if hasattr(main_window, 'editor_manager'):
                editor_layout_mode = config_mgr.get_config_value('layout', 'editor_layout_mode', 'tabbed')
                main_window.editor_manager.editor_layout_mode = editor_layout_mode
                if hasattr(main_window.editor_manager, 'set_layout_mode'):
                    main_window.editor_manager.set_layout_mode(editor_layout_mode)
            
            if hasattr(main_window, 'pdf_manager'):
                pdf_layout_mode = config_mgr.get_config_value('layout', 'pdf_layout_mode', 'tabbed')
                main_window.pdf_manager.pdf_layout_mode = pdf_layout_mode
                if hasattr(main_window.pdf_manager, 'set_layout_mode'):
                    main_window.pdf_manager.set_layout_mode(pdf_layout_mode)
            
            # Load output visibility and apply it
            output_tabs_visible = config_mgr.get_config_value('layout', 'output_tabs_visible', 'True').lower() == 'true'
            main_window.output_tabs_visible = output_tabs_visible
            symbols_tab_visible = config_mgr.get_config_value('layout', 'symbols_tab_visible', 'True').lower() == 'true'
            main_window.symbols_tab_visible = symbols_tab_visible
            commands_tab_visible = config_mgr.get_config_value('layout', 'commands_tab_visible', 'True').lower() == 'true'
            main_window.commands_tab_visible = commands_tab_visible
            tree_tab_visible = config_mgr.get_config_value('layout', 'tree_tab_visible', 'True').lower() == 'true'
            main_window.tree_tab_visible = tree_tab_visible
            bookmarks_tab_visible = config_mgr.get_config_value('layout', 'bookmarks_tab_visible', 'True').lower() == 'true'
            main_window.bookmarks_tab_visible = bookmarks_tab_visible
            terminal_tab_visible = config_mgr.get_config_value('layout', 'terminal_tab_visible', 'True').lower() == 'true'
            main_window.terminal_tab_visible = terminal_tab_visible

            
            # Apply output visibility to UI
            if hasattr(main_window.layout_manager, 'output_container') and main_window.layout_manager.output_container:
                main_window.layout_manager.output_container.setVisible(output_tabs_visible)
                if hasattr(main_window.layout_manager, 'symbols_tab_visible') and main_window.layout_manager.symbols_tab_visible:                    
                    self.main_window.toggle_symbols_tab()
                if hasattr(main_window.layout_manager, 'commands_tab_visible') and main_window.layout_manager.commands_tab_visible:                    
                    self.main_window.toggle_commands_tab()
                if hasattr(main_window.layout_manager, 'tree_tab_visible') and main_window.layout_manager.tree_tab_visible:                    
                    self.main_window.toggle_tree_tab()
                if hasattr(main_window.layout_manager, 'bookmarks_tab_visible') and main_window.layout_manager.bookmarks_tab_visible:
                    self.main_window.toggle_bookmarks_tab()    
                if hasattr(main_window.layout_manager, 'terminal_tab_visible') and main_window.layout_manager.terminal_tab_visible:                    
                    self.main_window.toolbar_manager.toggle_terminal_tab()    
            
            # Load UI settings
            main_window.menu_language = config_mgr.get_config_value('ui', 'menu_language', 'en')
            is_rtl = config_mgr.get_config_value('ui', 'is_rtl', 'False').lower() == 'true'
            main_window.is_rtl = is_rtl

            # Load line numbers and fold markers visibility
            is_line_numbers_visible = config_mgr.get_config_value('ui', 'is_line_numbers_visible', 'True').lower() == 'true'
            main_window.is_line_numbers_visible = is_line_numbers_visible

            is_fold_markers_visible = config_mgr.get_config_value('ui', 'is_fold_markers_visible', 'True').lower() == 'true'
            main_window.is_fold_markers_visible = is_fold_markers_visible

            #print(f"Loaded visibility settings - Line numbers: {is_line_numbers_visible}, Fold markers: {is_fold_markers_visible}")

            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.apply_visibility_settings)
            
            # Load auto-load setting
            auto_load = config_mgr.get_config_value('ui', 'auto_load_last_file', 'True').lower() == 'true'
            main_window.auto_load_last_file = auto_load
            
            # Load font settings
            main_window.editor_font_size = int(config_mgr.get_config_value('ui', 'editor_font_size', '11'))
            main_window.toolbar_font_size = int(config_mgr.get_config_value('ui', 'toolbar_font_size', '10'))
            
            # Apply language settings if method exists
            if hasattr(main_window, 'apply_language_settings'):
                main_window.apply_language_settings()
            
            # Update menu after loading settings
            if hasattr(main_window, 'menu_manager'):
                main_window.menu_manager._update_output_toggle_action()
                #main_window.menu_manager.toggle_line_numbers(is_line_numbers_visible)
                #main_window.menu_manager.toggle_fold_markers(is_fold_markers_visible)
                
            # ADD this section for CWL completion:
            # Initialize and load CWL completion settings
            if not hasattr(main_window, 'cwl_manager'):
                from cwl_manager import CWLManager
                main_window.cwl_manager = CWLManager()
            
            # Load CWL settings from config
            cwl_dir = config_mgr.get_config_value('cwl_completion', 'cwl_directory', '')
            if cwl_dir and os.path.exists(cwl_dir):
                main_window.cwl_manager.set_cwl_directory(cwl_dir)
            
            enabled_files_str = config_mgr.get_config_value('cwl_completion', 'enabled_files', '')
            if enabled_files_str:
                enabled_files = [f.strip() for f in enabled_files_str.split(',') if f.strip()]
                main_window.cwl_manager.set_enabled_files(enabled_files)
            
            #print("CWL completion settings loaded")

            
            #print("Settings loaded successfully from configuration")
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            import traceback
            traceback.print_exc()
            # Apply default settings on error
            apply_default_settings(main_window)
    @staticmethod

    def apply_visibility_settings():
        if hasattr(main_window, 'menu_manager'):
            # Update menu checkboxes
            if hasattr(main_window.menu_manager, 'line_numbers_action'):
                main_window.menu_manager.line_numbers_action.setChecked(is_line_numbers_visible)
            if hasattr(main_window.menu_manager, 'fold_markers_action'):
                main_window.menu_manager.fold_markers_action.setChecked(is_fold_markers_visible)
            if hasattr(main_window.menu_manager, 'folding_menu'):
                main_window.menu_manager.folding_menu.setEnabled(is_fold_markers_visible)
            
            # Apply to editors
            main_window.menu_manager.toggle_line_numbers(is_line_numbers_visible)
            main_window.menu_manager.toggle_fold_markers(is_fold_markers_visible)

    def apply_default_settings(main_window):
        """Apply default settings to main window"""
        try:
            # Default compiler settings
            main_window.latex_engine = 'xelatex'
            main_window.backmatter_engine = 'bibtex'
            main_window.output_encoding = 'utf-8'
            
            # Set default commands for all engines
            main_window.pdflatex_option = "pdflatex -synctex=1 -interaction=nonstopmode -shell-escape"
            main_window.xelatex_option = "xelatex -synctex=1 -interaction=nonstopmode -shell-escape"
            main_window.lualatex_option = "lualatex -synctex=1 -interaction=nonstopmode -shell-escape"
            main_window.custom_option = ""

            
            # Default layout settings
            if hasattr(main_window, 'layout_manager'):
                main_window.layout_manager.current_layout = 'editor_left'
            
            if hasattr(main_window, 'editor_manager'):
                main_window.editor_manager.editor_layout_mode = 'tabbed'
            
            if hasattr(main_window, 'pdf_manager'):
                main_window.pdf_manager.pdf_layout_mode = 'tabbed'
            
            # Default UI settings
            main_window.menu_language = 'en'
            main_window.is_rtl = False
            main_window.is_line_numbers_visible = True
            main_window.is_fold_markers_visible = True
            main_window.output_tabs_visible = True
            main_window.auto_load_last_file = True
            main_window.editor_font_size = 11
            main_window.toolbar_font_size = 10
            
            # Apply output visibility
            if hasattr(main_window.layout_manager, 'output_container') and main_window.layout_manager.output_container:
                main_window.layout_manager.output_container.setVisible(True)
            
            #print("Default settings applied")
            
        except Exception as e:
            print(f"Error applying default settings: {e}")




    # Utility functions for font management
    def get_available_monospace_fonts():
        """Get list of available monospace fonts"""
        font_db = QFontDatabase()
        monospace_fonts = []
        
        for family in font_db.families():
            if font_db.isFixedPitch(family):
                monospace_fonts.append(family)
        
        # Add common programming fonts that might not be detected
        common_fonts = [
            "Consolas", "Monaco", "Menlo", "Courier New", "DejaVu Sans Mono",
            "Liberation Mono", "Ubuntu Mono", "Source Code Pro", "Fira Code",
            "JetBrains Mono", "Cascadia Code", "SF Mono", "Roboto Mono"
        ]
        
        for font_name in common_fonts:
            if font_name not in monospace_fonts:
                # Check if font actually exists
                test_font = QFont(font_name)
                if test_font.exactMatch():
                    monospace_fonts.append(font_name)
        
        return sorted(set(monospace_fonts))


    def validate_font_settings(font_settings):
        """Validate font settings and provide fallbacks"""
        validated = {}
        
        # Validate editor font
        editor_font = QFont(font_settings.get('editor_font_family', 'Consolas'))
        if not editor_font.exactMatch():
            # Try common monospace fonts as fallbacks
            fallbacks = ['Consolas', 'Monaco', 'Courier New', 'DejaVu Sans Mono']
            for fallback in fallbacks:
                test_font = QFont(fallback)
                if test_font.exactMatch():
                    validated['editor_font_family'] = fallback
                    break
            else:
                validated['editor_font_family'] = 'Courier New'  # System default
        else:
            validated['editor_font_family'] = font_settings.get('editor_font_family', 'Consolas')
        
        # Validate UI font
        ui_font = QFont(font_settings.get('ui_font_family', 'Arial'))
        if not ui_font.exactMatch():
            # Try common UI fonts as fallbacks
            fallbacks = ['Arial', 'Helvetica', 'Segoe UI', 'DejaVu Sans']
            for fallback in fallbacks:
                test_font = QFont(fallback)
                if test_font.exactMatch():
                    validated['ui_font_family'] = fallback
                    break
            else:
                validated['ui_font_family'] = QFont().defaultFamily()  # System default
        else:
            validated['ui_font_family'] = font_settings.get('ui_font_family', 'Arial')
        
        # Validate font sizes
        editor_size = font_settings.get('editor_font_size', 11)
        validated['editor_font_size'] = max(8, min(24, int(editor_size)))
        
        toolbar_size = font_settings.get('toolbar_font_size', 10)
        validated['toolbar_font_size'] = max(8, min(18, int(toolbar_size)))
        
        return validated

    def open_settings(self): # from settings_manager.py
        """Open settings dialog with enhanced error handling"""
        try:
            # Ensure main window has required managers
            required_managers = ['config_manager', 'layout_manager', 'editor_manager', 'pdf_manager']
            missing_managers = [m for m in required_managers if not hasattr(self.main_window, m)]            
            #if missing_managers:
            #    print(f"Warning: Missing managers: {missing_managers}")            
            self.dialog = SettingsDialog(self.main_window)
            result = self.dialog.exec_()            
            if result == SettingsDialog.Accepted:
                #print("Settings applied successfully")
                # SAFE: Only update output toggle action, don't recreate menus
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager._update_output_toggle_action()
            #else:
            #    print("Settings cancelled")            
            return result
        except Exception as e:
            print(f"Error opening settings dialog: {e}")
            import traceback
            traceback.print_exc()
            return None



class SettingsManager:
    """Enhanced settings manager with better error handling"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.dialog = None
    
    def open_settings(self):
        """Open settings dialog with enhanced error handling"""
        try:
            # Ensure main window has required managers
            required_managers = ['config_manager', 'layout_manager', 'editor_manager', 'pdf_manager']
            missing_managers = [m for m in required_managers if not hasattr(self.main_window, m)]
            
            #if missing_managers:
            #    print(f"Warning: Missing managers: {missing_managers}")
            
            self.dialog = SettingsDialog(self.main_window)
            result = self.dialog.exec_()
            
            if result == SettingsDialog.Accepted:
                #print("Settings applied successfully")
                # SAFE: Only update output toggle action, don't recreate menus
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager._update_output_toggle_action()
            #else:
            #    print("Settings cancelled")
            
            return result
            
        except Exception as e:
            print(f"Error opening settings dialog: {e}")
            import traceback
            traceback.print_exc()
            return None

    def open_settings_to_ai_tab(self):
        """Open settings dialog and switch directly to the AI Assistant tab"""
        try:
            required_managers = ['config_manager', 'layout_manager', 'editor_manager', 'pdf_manager']
            missing_managers = [m for m in required_managers if not hasattr(self.main_window, m)]
            #if missing_managers:
                #print(f"Warning: Missing managers: {missing_managers}")

            self.dialog = SettingsDialog(self.main_window)

            # Find the AI Assistant tab and switch to it
            ai_tab_index = -1
            for i in range(self.dialog.tab_widget.count()):
                if self.dialog.tab_widget.tabText(i) == "AI Assistant":
                    ai_tab_index = i
                    break

            if ai_tab_index >= 0:
                self.dialog.tab_widget.setCurrentIndex(ai_tab_index)
            else:
                print("Warning: AI Assistant tab not found in settings dialog")

            result = self.dialog.exec_()

            if result == SettingsDialog.Accepted:
                #print("AI Settings applied successfully")
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager._update_output_toggle_action()
            #else:
            #    print("AI Settings cancelled")

            return result

        except Exception as e:
            print(f"Error opening settings dialog to AI tab: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # def load_settings(self):
        # """Load settings from configuration"""
        # load_settings_from_config(self.main_window)
    
    # def apply_defaults(self):
        # """Apply default settings"""
        # apply_default_settings(self.main_window)
    
    # def create_shortcut(self):
        # """Create keyboard shortcut for settings"""
        # if hasattr(self.main_window, 'addAction'):
            # from PyQt5.QtWidgets import QAction
            # from PyQt5.QtGui import QKeySequence
            
            # settings_action = QAction("Settings", self.main_window)
            # #settings_action.setShortcut(QKeySequence("Ctrl+,"))
            # settings_action.triggered.connect(self.open_settings)
            
            # self.main_window.addAction(settings_action)
            # return settings_action
        # return None
    
    def get_current_font_settings(self):
        """Get current font settings as dict"""
        return {
            'editor_font_family': getattr(self.main_window, 'editor_font_family', 'Consolas'),
            'ui_font_family': getattr(self.main_window, 'ui_font_family', 'Arial'),
            'editor_font_size': getattr(self.main_window, 'editor_font_size', 11),
            'toolbar_font_size': getattr(self.main_window, 'toolbar_font_size', 10)
        }
    
    # def validate_settings(self):
        # """Validate current settings and fix any issues"""
        # try:
            # # Validate output_tabs_visible state
            # if not hasattr(self.main_window, 'output_tabs_visible'):
                # self.main_window.output_tabs_visible = True
            
            # # Validate language setting
            # if not hasattr(self.main_window, 'menu_language'):
                # self.main_window.menu_language = 'en'
            # elif self.main_window.menu_language not in ['en', 'ar']:
                # self.main_window.menu_language = 'en'
            
            # # Validate layout managers
            # managers_to_check = [
                # ('layout_manager', 'current_layout', 'editor_left'),
                # ('editor_manager', 'editor_layout_mode', 'tabbed'),
                # ('pdf_manager', 'pdf_layout_mode', 'tabbed')
            # ]
            
            # for manager_name, attr_name, default_value in managers_to_check:
                # if hasattr(self.main_window, manager_name):
                    # manager = getattr(self.main_window, manager_name)
                    # if not hasattr(manager, attr_name):
                        # setattr(manager, attr_name, default_value)
            
            # print("Settings validation completed")
            
        # except Exception as e:
            # print(f"Error validating settings: {e}")


    def open_settings_dialog(main_window):
        """Open settings dialog - standalone function for compatibility"""
        settings_manager = SettingsManager(main_window)
        return settings_manager.open_settings()


    def get_available_monospace_fonts():
        """Get list of available monospace fonts"""
        try:
            from PyQt5.QtGui import QFontDatabase
            font_db = QFontDatabase()
            fonts = font_db.families()
            
            # Common monospace fonts to check for
            monospace_fonts = []
            common_mono = ['Consolas', 'Courier New', 'Liberation Mono', 'DejaVu Sans Mono', 
                          'Source Code Pro', 'Fira Code', 'Monaco', 'Menlo']
            
            for font in common_mono:
                if font in fonts:
                    monospace_fonts.append(font)
            
            # Add any other fonts that are likely monospace
            for font in fonts:
                if any(keyword in font.lower() for keyword in ['mono', 'code', 'console', 'typewriter']):
                    if font not in monospace_fonts:
                        monospace_fonts.append(font)
            
            return monospace_fonts if monospace_fonts else ['Courier New']  # fallback
            
        except Exception as e:
            print(f"Error getting monospace fonts: {e}")
            return ['Courier New', 'Consolas', 'Monaco']


    def validate_font_settings(font_settings):
        """Validate font settings dictionary"""
        try:
            # Required keys with defaults
            defaults = {
                'editor_font_family': 'Consolas',
                'ui_font_family': 'Arial',
                'editor_font_size': 11,
                'toolbar_font_size': 10
            }
            
            # Ensure all required keys exist
            for key, default in defaults.items():
                if key not in font_settings:
                    font_settings[key] = default
            
            # Validate font sizes
            for size_key in ['editor_font_size', 'toolbar_font_size']:
                try:
                    size = int(font_settings[size_key])
                    if size < 6 or size > 72:  # Reasonable font size range
                        font_settings[size_key] = defaults[size_key]
                    else:
                        font_settings[size_key] = size
                except (ValueError, TypeError):
                    font_settings[size_key] = defaults[size_key]
            
            return font_settings
            
        except Exception as e:
            print(f"Error validating font settings: {e}")
            return defaults

# Additional imports needed
try:
    from PyQt5.QtWidgets import (QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, 
                                QTabWidget, QWidget, QGroupBox, QGridLayout, 
                                QLabel, QComboBox, QCheckBox, QPushButton, QMenu, 
                                QAction, QSpinBox, QFontComboBox)
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QFont, QKeySequence
    import configparser
except ImportError as e:
    print(f"Import error: {e}")


# Export main functions
__all__ = [
    'MainWindow',           # Updated MainWindow class with get_actual_output_state
    'MenuManager',          # Safe MenuManager class  
    'ConfigManager',        # Updated ConfigManager class
    'SettingsDialog',       # Completely rewritten SettingsDialog class
    'SettingsManager',      # Safe SettingsManager class
    'load_settings_from_config',     # Enhanced load function
    'apply_default_settings',        # Enhanced defaults function    
    'open_settings_dialog',          # Utility function
    'get_available_monospace_fonts', # Utility function
    'validate_font_settings'         # Utility function
]