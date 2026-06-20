# side_panel.py
import json
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, 
    QLabel, QScrollArea, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QFont
from style_manager import NORMAL_BUTTON, get_panel_style

from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence

class QuickJumpPopup(QWidget):
    """Floating popup to jump to any side panel button by number."""
    
    def __init__(self, main_window):
        super().__init__(main_window, Qt.Popup | Qt.FramelessWindowHint)
        self.main_window = main_window
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._setup_ui()

    def _setup_ui(self):
        from PyQt5.QtWidgets import QLineEdit, QListWidget, QListWidgetItem
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        title = QLabel(tr.get("jum_to_button", "Jump to button (type number or label):"))
        #title = QLabel("Jump to button (type number or label):")
        title.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(title)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("e.g. 14 or 'cite'")
        self.search_field.textChanged.connect(self._filter_list)
        self.search_field.installEventFilter(self)
        layout.addWidget(self.search_field)

        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(200)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.list_widget.installEventFilter(self)
        layout.addWidget(self.list_widget)

        hint = QLabel("Enter / double-click to activate  •  Esc to close")
        hint.setStyleSheet("color: #888; font-size: 9px;")
        layout.addWidget(hint)

        self.setFixedWidth(320)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.hide()
                return True
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                current = self.list_widget.currentItem()
                if current:
                    self._on_item_activated(current)
                return True
            if obj == self.search_field and event.key() == Qt.Key_Down:
                self.list_widget.setFocus()
                self.list_widget.setCurrentRow(0)
                return True
            if obj == self.list_widget and event.key() == Qt.Key_Up:
                if self.list_widget.currentRow() == 0:
                    self.search_field.setFocus()
                    return True
        return super().eventFilter(obj, event)

    def _populate_list(self):
        from PyQt5.QtWidgets import QListWidgetItem
        self.list_widget.clear()
        panel = self.main_window.side_panel
        active_idx = 0  # index among visible buttons
        for i, cmd in enumerate(panel.commands):
            label = cmd.get("label", "").strip()
            latex = cmd.get("latex", "").strip()
            if not label or not latex:
                continue
            active_idx += 1
            shortcut = cmd.get("shortcut", "").strip()
            sc_hint = f"  [{shortcut}]" if shortcut else ""
            item = QListWidgetItem(f"{active_idx:3d}.  {label:<12} {latex[:35]}{sc_hint}")
            item.setData(Qt.UserRole, i)   # store original command index
            self.list_widget.addItem(item)

        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _filter_list(self, text):
        text = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())
        # Select first visible item
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.list_widget.setCurrentItem(item)
                break

    def _on_item_activated(self, item):
        cmd_index = item.data(Qt.UserRole)
        self.hide()
        panel = self.main_window.side_panel
        # Find the corresponding button in self.buttons
        btn_index = 0
        for i, cmd in enumerate(panel.commands):
            if not cmd.get("label", "").strip() or not cmd.get("latex", "").strip():
                continue
            if i == cmd_index:
                if btn_index < len(panel.buttons):
                    panel.buttons[btn_index].click()
                return
            btn_index += 1

    def show_centered(self):
        self._populate_list()
        self.search_field.clear()
        self.adjustSize()
        # Center over the main window
        mw = self.main_window
        x = mw.x() + (mw.width() - self.width()) // 2
        y = mw.y() + (mw.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.search_field.setFocus()
        
class HoverScrollButton(QPushButton):
    """Scroll button that appears only on hover of its area."""
    def __init__(self, text, height=20):
        super().__init__(text)
        self.setFixedHeight(height)
        self.setEnabled(True)
        # Default colors — overridden by set_theme_colors()
        self._btn_bg     = "#e0e0e0"
        self._btn_border = "#cccccc"
        self._btn_hover  = "#d0d0d0"
        self.hide_button()

    def set_theme_colors(self, bg, border, hover):
        """Update colors to match the active theme."""
        self._btn_bg     = bg
        self._btn_border = border
        self._btn_hover  = hover

    def hide_button(self):
        self.setFlat(True)
        self.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: transparent;
            }
        """)

    def show_button(self):
        self.setFlat(False)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._btn_bg};
                border: 1px solid {self._btn_border};
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {self._btn_hover};
            }}
        """)

    def enterEvent(self, event):
        if self.isEnabled():
            self.show_button()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_button()
        super().leaveEvent(event)

class SidePanel(QWidget):
    MAX_BUTTONS = 100
    DEFAULT_BUTTON_COUNT = 17
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.buttons = []
        self.button_height = 30
        self.spacing = 3
        self._saving_enabled = True  # Flag to prevent save during load
        self._quick_jump = None   # lazy init
        
        # Default commands (17 buttons)
        self.default_commands = [
            {"label": "α",        "latex": r"\alpha"},
            {"label": "β",        "latex": r"\beta"},
            {"label": "a/b",      "latex": r"\frac{cursor}{#}"},
            {"label": "a^b",      "latex": r"^{cursor}"},
            {"label": "a_b",      "latex": r"_{cursor}"},
            {"label": "√",        "latex": r"\sqrt{cursor}"},
            {"label": "∑",        "latex": r"\sum_{cursor}^{#}"},
            {"label": "∫",        "latex": r"\int_{cursor}^{#}"},
            {"label": "→",        "latex": r"\to"},
            {"label": "∞",        "latex": r"\infty"},
            {"label": "≠",        "latex": r"\neq"},
            {"label": "≤",        "latex": r"\leq"},
            {"label": "π",        "latex": r"\pi"},
            {"label": "section",  "latex": r"\section{cursor}"},
            {"label": "eqref",    "latex": r"\eqref{cursor}"},
            {"label": "cite",     "latex": r"\cite{cursor}"},
            {"label": "item",     "latex": r"\item cursor"}
        ]
        self.commands = self.default_commands.copy()
        self._position = "left"
        
        self._setup_ui()
        self._create_buttons()
        # ✅ Apply UI font after setup
        self.update_font()
        
    
    def _setup_ui(self):
        """Setup the UI layout with hover scroll buttons"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 5, 2, 5)
        self.main_layout.setSpacing(0)

        self.btn_up = HoverScrollButton("▲", 20)
        self.btn_up.setFixedWidth(70)
        self.main_layout.addWidget(self.btn_up, alignment=Qt.AlignCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(self.spacing)
        self.scroll_area.setWidget(self.buttons_container)
        self.main_layout.addWidget(self.scroll_area, stretch=1)

        self.btn_down = HoverScrollButton("▼", 20)
        self.btn_down.setFixedWidth(70)
        self.main_layout.addWidget(self.btn_down, alignment=Qt.AlignCenter)

        self.btn_up.clicked.connect(self.scroll_up)
        self.btn_down.clicked.connect(self.scroll_down)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.update_scroll_buttons)

        self.setFixedWidth(85)
        self.setMinimumHeight(200)

        # ✅ Theme-aware background
        self._apply_panel_background()

        self.update_scroll_buttons()

        # ── Right-click context menu ──────────────────────────────────────
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.scroll_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll_area.customContextMenuRequested.connect(self._show_context_menu)
        self.buttons_container.setContextMenuPolicy(Qt.CustomContextMenu)
        self.buttons_container.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        """Right-click context menu for the side panel."""
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        
        action = self.main_window.menu_manager.toggle_visibility_action
        is_visible = action.isChecked()
        text = "Hide Side Panel (F9)" if is_visible else "Show Side Panel (F9)"
        
        hide_action = QAction(text, self)
        hide_action.triggered.connect(lambda: action.trigger())
        menu.addAction(hide_action)
        menu.exec_(self.mapToGlobal(pos))
       
    def show_quick_jump(self):
        if self._quick_jump is None:
            self._quick_jump = QuickJumpPopup(self.main_window)
        self._quick_jump.show_centered()


    def _apply_panel_background(self):
        """Apply theme-aware background to the panel and scroll buttons."""
        from style_manager import get_panel_style
        p = get_panel_style()
        bg = p['bg_btn']

        # ✅ Use objectName-scoped rule to avoid cascading to ALL QWidgets
        self.setObjectName("SidePanel")
        self.setStyleSheet(f"""
            QWidget#SidePanel {{
                background-color: {bg};
                border: none;
            }}
            QScrollArea {{
                border: none;
                background-color: {bg};
            }}
        """)

        # ✅ These three must all match — they are the layers between panel and buttons
        self.scroll_area.setStyleSheet(f"background-color: {bg}; border: none;")
        self.scroll_area.viewport().setStyleSheet(f"background-color: {bg};")
        self.buttons_container.setStyleSheet(f"background-color: {bg}; border: none;")

        # Update scroll button colors
        self.btn_up.set_theme_colors(
            p['scroll_btn_bg'], p['scroll_btn_border'], p['scroll_btn_hover']
        )
        self.btn_down.set_theme_colors(
            p['scroll_btn_bg'], p['scroll_btn_border'], p['scroll_btn_hover']
        )    
    def update_font(self):
        """Update side panel font to match interface font"""
        # Get font settings from main window
        if hasattr(self.main_window, 'get_current_font_settings'):
            current_fonts = self.main_window.get_current_font_settings()
            ui_font_family = current_fonts.get('ui_font_family', 'Arial')
            ui_font_size = current_fonts.get('toolbar_font_size', 10)
        else:
            ui_font_family = getattr(self.main_window, 'ui_font_family', 'Arial')
            ui_font_size = getattr(self.main_window, 'toolbar_font_size', 10)

        ui_font = QFont(ui_font_family, ui_font_size)

        # Apply to scroll buttons
        if hasattr(self, 'btn_up'):
            self.btn_up.setFont(ui_font)
        if hasattr(self, 'btn_down'):
            self.btn_down.setFont(ui_font)

        # Apply to all command buttons
        for btn in self.buttons:
            btn.setFont(ui_font)

        #print(f"Side panel font updated: {ui_font_family}, size {ui_font_size}")

    
    def scroll_up(self):
        bar = self.scroll_area.verticalScrollBar()
        new_value = bar.value() - (self.button_height + self.spacing)
        bar.setValue(max(new_value, 0))
    
    def scroll_down(self):
        bar = self.scroll_area.verticalScrollBar()
        new_value = bar.value() + (self.button_height + self.spacing)
        bar.setValue(min(new_value, bar.maximum()))
    
    def update_scroll_buttons(self):
        """Show/hide scroll buttons based on scroll position."""
        bar = self.scroll_area.verticalScrollBar()
        
        if bar.value() > 0:
            self.btn_up.setEnabled(True)
            self.btn_up.show()
        else:
            self.btn_up.setEnabled(False)
            self.btn_up.hide()
        
        if bar.value() < bar.maximum():
            self.btn_down.setEnabled(True)
            self.btn_down.show()
        else:
            self.btn_down.setEnabled(False)
            self.btn_down.hide()

    def _create_buttons(self):
        """Create buttons from commands"""
        self._clear_buttons()
        self.buttons = []

        if hasattr(self.main_window, 'get_current_font_settings'):
            current_fonts = self.main_window.get_current_font_settings()
            ui_font_family = current_fonts.get('ui_font_family', 'Arial')
            ui_font_size = current_fonts.get('toolbar_font_size', 10)
        else:
            ui_font_family = getattr(self.main_window, 'ui_font_family', 'Arial')
            ui_font_size = getattr(self.main_window, 'toolbar_font_size', 10)

        ui_font = QFont(ui_font_family, ui_font_size)

        from style_manager import NORMAL_BUTTON

        # ✅ Override horizontal padding for the narrow side panel
        base_style = NORMAL_BUTTON()
        panel_btn_style = base_style.replace(
            "padding: 4px 8px",
            "padding: 4px 3px"          # less horizontal padding so text isn't clipped
        )

        for cmd in self.commands:
            if not cmd.get("label", "").strip() or not cmd.get("latex", "").strip():
                continue

            btn = QPushButton(cmd["label"])
            btn.setFixedWidth(75)                         # ← was 70, now 86
            btn.setFixedHeight(self.button_height)
            btn.setStyleSheet(panel_btn_style)
            btn.setToolTip(cmd["latex"])
            btn.setFont(ui_font)

            latex_code = cmd["latex"].replace('\\n', '\n')

            if hasattr(self.main_window, 'editor_manager') and self.main_window.editor_manager:
                btn.clicked.connect(
                    lambda checked, code=latex_code:
                    self.main_window.editor_manager.insert_latex_command(code)
                )
            elif hasattr(self.main_window, 'latex_insert_callback'):
                btn.clicked.connect(
                    lambda checked, code=latex_code:
                    self.main_window.latex_insert_callback(code)
                )
            else:
                btn.clicked.connect(
                    lambda checked, code=latex_code: self.fallback_insert(code)
                )

            self.buttons_layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self.buttons.append(btn)

        self.buttons_layout.addStretch()

        # ✅ Re-apply container background after recreating buttons
        self._apply_panel_background()

        QTimer.singleShot(100, self.update_scroll_buttons)

    def refresh_button_styles(self):
        """Re-apply current theme styles to all side panel buttons and background."""
        from style_manager import get_button_style
        base_style = get_button_style("normal")
        panel_btn_style = base_style.replace("padding: 4px 8px", "padding: 4px 3px")
        for btn in self.buttons:
            btn.setStyleSheet(panel_btn_style)
        self._apply_panel_background()   # ← updates container bg + scroll button colors
    
    def _clear_buttons(self):
        """Clear all existing buttons from layout"""
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def fallback_insert(self, latex_code):
        """Fallback method if text handler not available"""
        if not hasattr(self.main_window, 'editor_manager'):
            return
        editor = self.main_window.editor_manager.get_current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        text = latex_code.replace("cursor", "")
        cursor.insertText(text)
    
    def _set_commands_internal(self, commands):
        """Set commands without triggering save (used during load)"""
        self._saving_enabled = False
        try:
            self.commands = commands[:self.MAX_BUTTONS] if commands else self.default_commands.copy()
            self._create_buttons()
        finally:
            self._saving_enabled = True
    
    def set_commands(self, commands, save=True):
        self.commands = commands[:self.MAX_BUTTONS] if commands else []
        self._create_buttons()
        if save and self._saving_enabled:
            self._save_commands()
        # Re-register custom shortcuts whenever commands change
        if hasattr(self.main_window, '_register_side_panel_shortcuts'):
            self.main_window._register_side_panel_shortcuts()
    
    def _save_commands(self):
        """Save current commands to config"""
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.save_side_panel_commands(self.commands)
        elif hasattr(self.main_window, 'save_side_panel_commands'):
            self.main_window.save_side_panel_commands()
    
    def get_commands(self):
        """Get current commands"""
        return self.commands.copy()
    
    def reset_to_default(self):
        """Reset side panel to default commands"""
        self.commands = self.default_commands.copy()
        self._create_buttons()
        self._save_commands()
    
    
    def set_position(self, position="left"):
        """Set side panel position: 'left' or 'right'"""
        self._position = position
    
    def load_from_config(self):
        """Load commands from config manager"""
        if hasattr(self.main_window, 'config_manager'):
            commands = self.main_window.config_manager.get_side_panel_commands()
            if commands:
                self._set_commands_internal(commands)
                #print(f"Loaded {len(self.commands)} commands from config")
                return True
        return False
    
    @property
    def position(self):
        return getattr(self, '_position', 'left')
