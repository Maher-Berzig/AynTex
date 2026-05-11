# todo_list.py
import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit, QCheckBox,  
    QInputDialog, QMessageBox, QStyledItemDelegate, QFileDialog,
    QLabel, QFrame, QSizePolicy, QHeaderView, QStyle, QComboBox, QTabBar
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QTextOption, QFontMetrics, QColor, QBrush, QIcon
import app_info

class ContentSizedTabBar(QTabBar):
    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)

        # Optional safety limits
        size.setWidth(size.width() + 20)   # extra breathing room
        # size.setWidth(min(size.width(), 300))  # optional max

        return size
class TaskDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """Set priority colors based on current theme."""
        from style_manager import _current_theme
        if _current_theme in ("dark", "midnight"):
            self.priority_colors = {
                'Urgent':   QColor(80, 30, 30),
                'Normal':   QColor(70, 55, 20),
                'Optional': QColor(20, 60, 30),
            }
            self.priority_text_colors = {
                'Urgent':   QColor(255, 100, 100),
                'Normal':   QColor(255, 180, 80),
                'Optional': QColor(80, 220, 80),
            }
        else:
            # default / light
            self.priority_colors = {
                'Urgent':   QColor(255, 235, 235),
                'Normal':   QColor(255, 245, 220),
                'Optional': QColor(235, 255, 235),
            }
            self.priority_text_colors = {
                'Urgent':   QColor(200, 0, 0),
                'Normal':   QColor(200, 100, 0),
                'Optional': QColor(0, 150, 0),
            }
            
    def sizeHint(self, option, index):
        if index.column() == 1:
            text = index.data(Qt.DisplayRole) or ""
            metrics = QFontMetrics(option.font)
            tree = self.parent()
            if tree and hasattr(tree, 'columnWidth'):
                rect_width = tree.columnWidth(1) - 30
            else:
                rect_width = option.rect.width() - 30 if option.rect.width() > 50 else 200
            if rect_width <= 0:
                rect_width = option.rect.width() - 30 if option.rect.width() > 50 else 200
            text_rect = metrics.boundingRect(0, 0, rect_width, 0, 
                                             Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, 
                                             text)
            height = max(35, text_rect.height() + 20)
            # Add extra height if item has a due date
            if tree:
                item = tree.itemFromIndex(index)
                if item and item.data(1, Qt.UserRole + 1):
                    height += 22
            return QSize(rect_width, height)
        return super().sizeHint(option, index)
    

    def paint(self, painter, option, index):
        if index.column() == 1:
            # Get the item and priority
            tree = self.parent()
            item = None
            priority = 'Normal'
            due_date = None
            
            if tree:
                item = tree.itemFromIndex(index)
                if item and item.data(1, Qt.UserRole):
                    priority = item.data(1, Qt.UserRole)
                if item and item.data(1, Qt.UserRole + 1):
                    due_date = item.data(1, Qt.UserRole + 1)
            
            # Draw background with priority color
            bg_color = self.priority_colors.get(priority, QColor(255, 255, 255))
            
            if option.state & QStyle.State_Selected:
                # Blend with selection color
                bg_color = QColor(
                    int(bg_color.red() * 0.7 + 227 * 0.3),
                    int(bg_color.green() * 0.7 + 242 * 0.3),
                    int(bg_color.blue() * 0.7 + 253 * 0.3)
                )
            elif option.state & QStyle.State_MouseOver:
                # Slightly darker on hover
                bg_color = bg_color.darker(105)
            
            painter.fillRect(option.rect, bg_color)
            
            # Get text
            text = index.data(Qt.DisplayRole) or ""
            painter.save()
            
            # Apply strikethrough and color if checked
            if item and item.checkState(0) == Qt.Checked:
                painter.setPen(QColor(136, 136, 136))
                font = painter.font()
                font.setStrikeOut(True)
                painter.setFont(font)
            else:
                # Use priority color for text
                text_color = self.priority_text_colors.get(priority, QColor(33, 33, 33))
                painter.setPen(text_color)
            
            # Draw main text with padding
            text_rect = option.rect.adjusted(8, 6, -6, -6)
            
            # If there's a due date, calculate space needed
            if due_date:
                # Draw main text
                main_font = painter.font()
                metrics = QFontMetrics(main_font)
                text_height = metrics.boundingRect(text_rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text).height()
                
                # Draw the task text
                task_rect = text_rect.adjusted(0, 0, 0, -20)  # Leave space for due date
                painter.drawText(task_rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text)
                
                # Draw due date in smaller, subtle font
                painter.restore()
                painter.save()
                
                due_font = painter.font()
                due_font.setPointSize(max(8, due_font.pointSize() - 2))
                due_font.setItalic(True)
                painter.setFont(due_font)
                
                # Parse and format the date
                from datetime import datetime
                try:
                    date_obj = datetime.fromisoformat(due_date)
                    today = datetime.now().date()
                    due_date_obj = date_obj.date()
                    
                    # Color code based on urgency
                    days_until = (due_date_obj - today).days
                    if days_until < 0:
                        painter.setPen(QColor(180, 0, 0))  # Overdue - dark red
                        date_text = f"📅 Due: {date_obj.strftime('%Y-%m-%d')} (OVERDUE)"
                    elif days_until == 0:
                        painter.setPen(QColor(200, 100, 0))  # Today - orange
                        date_text = f"📅 Due: TODAY"
                    elif days_until <= 3:
                        painter.setPen(QColor(200, 100, 0))  # Soon - orange
                        date_text = f"📅 Due: {date_obj.strftime('%Y-%m-%d')} ({days_until} day{'s' if days_until > 1 else ''})"
                    else:
                        painter.setPen(QColor(100, 100, 100))  # Normal - gray
                        date_text = f"📅 Due: {date_obj.strftime('%Y-%m-%d')}"
                except:
                    painter.setPen(QColor(100, 100, 100))
                    date_text = f"📅 Due: {due_date}"
                
                # Draw the due date
                due_rect = text_rect.adjusted(0, text_height + 5, 0, 0)
                painter.drawText(due_rect, Qt.AlignLeft | Qt.AlignTop, date_text)
                
                painter.restore()
            else:
                # No due date, just draw the text normally
                painter.drawText(text_rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text)
                painter.restore()
        else:
            super().paint(painter, option, index)


class TodoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
        self.update_button_state()
        self.refresh_styles()

    def setupUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Stats and priority selector in one row
        top_layout = QHBoxLayout()
        
        self.stats_label = QLabel("0 tasks")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                font-size: 8pt;
                padding: 5px;
            }
        """)
        top_layout.addWidget(self.stats_label)
        
        top_layout.addStretch()
        
        # Priority selector
        priority_frame = QFrame()
        self.priority_frame = priority_frame
        self.priority_frame.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 4px;
                padding: 0px;
            }
        """)
        priority_layout = QHBoxLayout(self.priority_frame)
        priority_layout.setContentsMargins(5, 2, 5, 2)
        priority_layout.addWidget(QLabel("Priority:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Urgent", "Normal", "Optional"])
        self.priority_combo.setCurrentIndex(1)  # Default to Normal
        self.priority_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 3px 8px;
                min-width: 80px;
            }
        """)
        priority_layout.addWidget(self.priority_combo)
        
        # Add separator
        priority_layout.addWidget(QLabel("  |  "))

        # Auto-open checkbox
        self.auto_open_checkbox = QCheckBox("Auto-open")
        self.auto_open_checkbox.setToolTip("Automatically open Todo List when application starts")
        self.auto_open_checkbox.setStyleSheet("""
            QCheckBox {
                padding: 3px;
            }
        """)
        self.auto_open_checkbox.stateChanged.connect(self.on_auto_open_changed)
        priority_layout.addWidget(self.auto_open_checkbox)


        top_layout.addWidget(self.priority_frame)
        main_layout.addLayout(top_layout)

        # Priority legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Priority Legend:"))
        
        urgent_label = QLabel("✅ Urgent")
        urgent_label.setStyleSheet("color: #c80000; font-weight: bold;")
        legend_layout.addWidget(urgent_label)
        
        normal_label = QLabel("✔ Normal")
        normal_label.setStyleSheet("color: #c86400; font-weight: bold;")
        legend_layout.addWidget(normal_label)
        
        optional_label = QLabel("☑ Optional")
        optional_label.setStyleSheet("color: #009600; font-weight: bold;")
        legend_layout.addWidget(optional_label)
        
        legend_layout.addStretch()
        main_layout.addLayout(legend_layout)

        # Separator
        self.separator_frame = QFrame()
        self.separator_frame.setFrameShape(QFrame.HLine)
        self.separator_frame.setFrameShadow(QFrame.Sunken)
        self.separator_frame.setStyleSheet("background-color: #ddd;")
        main_layout.addWidget(self.separator_frame)

        # Input area
        input_layout = QHBoxLayout()
        
        self.input = QTextEdit()
        self.input.setPlaceholderText("Enter new task... (Ctrl+Enter to add)")
        self.input.setMaximumHeight(100)
        self.input.setMinimumHeight(60)
        self.input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input.setTabChangesFocus(False)
        self.input.setAcceptRichText(False)
        self.input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-size: 9pt;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 2px solid #4CAF50;
            }
        """)
        
        self.input.installEventFilter(self)
        
        self.add_btn = QPushButton("Add Task")
        self.add_btn.setFixedWidth(100)
        self.add_btn.setMinimumHeight(60)
        self.add_btn.setMaximumHeight(100)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        input_layout.addWidget(self.input)
        input_layout.addWidget(self.add_btn)
        main_layout.addLayout(input_layout)

        # Control buttons
        self.control_frame = QFrame()
        self.control_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 4px;
                padding: 0px;
            }
        """)
        control_layout = QHBoxLayout(self.control_frame)
        control_layout.setSpacing(5)
        control_layout.setContentsMargins(5, 5, 5, 5)

        
        self.up_btn = QPushButton("↑ Up")
        self.down_btn = QPushButton("↓ Down")
        self.delete_btn = QPushButton("⌫ Delete")
        self.indent_btn = QPushButton("➡ Indent")
        self.outdent_btn = QPushButton("⬅ Outdent")
        self.edit_btn = QPushButton("✏ Edit")
        self.priority_btn = QPushButton("🎯 Change Priority")
        self.due_date_btn = QPushButton("📅 Set Due Date")
        
        for btn in [self.up_btn, self.down_btn, self.delete_btn, 
                   self.indent_btn, self.outdent_btn, self.edit_btn, self.priority_btn, self.due_date_btn]:
            btn.setFixedHeight(28)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 3px 6px;
                    font-size: 7pt;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:disabled {
                    background-color: #f0f0f0;
                    color: #999;
                }
            """)
            control_layout.addWidget(btn)
        
        control_layout.addStretch()
        main_layout.addWidget(self.control_frame)

        # Tree widget
       
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["☑", "Task"])
        self.tree.setIndentation(0)
        self.tree.setRootIsDecorated(False)
        
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        
        delegate = TaskDelegate(self.tree)
        self.tree.setItemDelegate(delegate)
        self.tree.setUniformRowHeights(False)
        
        # Configure header with resizable columns
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Make checkbox column manually resizable
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Make task column manually resizable
        header.setStretchLastSection(True)
        
        # Set initial column widths
        self.tree.setColumnWidth(0, 50)
        self.tree.setIndentation(20)
        #self.tree.setColumnWidth(1, 600)
        
        # Enable visual feedback for resizing
        header.setCascadingSectionResizes(False)
        header.setFixedHeight(30)

        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f9f9f9;
                font-size: 11pt;
                outline: none;
            }
            QTreeWidget::item {
                padding: 8px 2px;
                border-bottom: 1px solid #f0f0f0;
                min-height: 35px;
                margin-left: 0px;
            }
            QTreeWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.03);
            }
            QTreeWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.1);
                color: black;
            }
            QTreeWidget::branch {
                background: transparent;
                width: 0px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 4px;
                border: 1px solid #ddd;
                border-top: none;
                border-left: none;
                font-weight: bold;
                font-size: 11pt;
            }
            QHeaderView::section:first {
                border-left: none;
            }
        """)
        
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.tree, stretch=1)

        # Connect signals
        self.add_btn.clicked.connect(self.add_task)
        self.delete_btn.clicked.connect(self.delete_task)
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn.clicked.connect(self.move_down)
        self.indent_btn.clicked.connect(self.indent_task)
        self.outdent_btn.clicked.connect(self.outdent_task)
        self.edit_btn.clicked.connect(self.edit_task)
        self.priority_btn.clicked.connect(self.change_priority)
        self.due_date_btn.clicked.connect(self.set_due_date)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemSelectionChanged.connect(self.update_button_state)
        
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.update_all_row_heights)
        
        if hasattr(self.tree, 'viewport'):
            self.tree.viewport().installEventFilter(self)

    def refresh_styles(self):
        """Re-apply all theme-aware styles to TodoTab widgets."""
        from style_manager import get_button_style, get_panel_style, _current_theme
        p = get_panel_style()

        _THEME_COLORS = {
            "default":  {
                "input_bg": "#ffffff", "input_border": "#cccccc", "input_focus": "#4CAF50",
                "tree_bg": "#ffffff", "tree_alt_bg": "#f9f9f9",
                "tree_border": "#dddddd", "tree_item_border": "#f0f0f0",
                "tree_hover": "rgba(0,0,0,0.03)", "tree_selected": "rgba(33,150,243,0.1)",
                "tree_selected_text": "black",
                "header_bg": "#f5f5f5", "header_border": "#dddddd",
                "separator_bg": "#dddddd",
                "add_btn_bg": "#4CAF50", "add_btn_hover": "#45a049", "add_btn_pressed": "#3d8b40",
                "ctrl_btn_bg": "#ffffff", "ctrl_btn_border": "#cccccc",
                "ctrl_btn_hover": "#e0e0e0", "ctrl_btn_text": "#000000",
            },
            "dark": {
                "input_bg": "#2b2b2b", "input_border": "#555759", "input_focus": "#2ea043",
                "tree_bg": "#2b2b2b", "tree_alt_bg": "#313335",
                "tree_border": "#555759", "tree_item_border": "#3c3f41",
                "tree_hover": "rgba(255,255,255,0.05)", "tree_selected": "rgba(75,110,175,0.3)",
                "tree_selected_text": "#ffffff",
                "header_bg": "#3c3f41", "header_border": "#555759",
                "separator_bg": "#555759",
                "add_btn_bg": "#2d6e2d", "add_btn_hover": "#357a35", "add_btn_pressed": "#1a4d1a",
                "ctrl_btn_bg": "#3c3f41", "ctrl_btn_border": "#555759",
                "ctrl_btn_hover": "#4c5052", "ctrl_btn_text": "#bbbbbb",
            },
            "light": {
                "input_bg": "#ffffff", "input_border": "#c0c0c0", "input_focus": "#3d9e3d",
                "tree_bg": "#ffffff", "tree_alt_bg": "#f5f5f5",
                "tree_border": "#c0c0c0", "tree_item_border": "#e8e8e8",
                "tree_hover": "rgba(0,0,0,0.04)", "tree_selected": "rgba(30,130,210,0.15)",
                "tree_selected_text": "#000000",
                "header_bg": "#eeeeee", "header_border": "#c0c0c0",
                "separator_bg": "#c0c0c0",
                "add_btn_bg": "#3d9e3d", "add_btn_hover": "#2d8e2d", "add_btn_pressed": "#1d7e1d",
                "ctrl_btn_bg": "#f5f5f5", "ctrl_btn_border": "#c0c0c0",
                "ctrl_btn_hover": "#e0e0e0", "ctrl_btn_text": "#1a1a1a",
            },
            "midnight": {
                "input_bg": "#0d1117", "input_border": "#30363d", "input_focus": "#2ea043",
                "tree_bg": "#0d1117", "tree_alt_bg": "#161b22",
                "tree_border": "#30363d", "tree_item_border": "#21262d",
                "tree_hover": "rgba(255,255,255,0.04)", "tree_selected": "rgba(31,111,235,0.25)",
                "tree_selected_text": "#c9d1d9",
                "header_bg": "#161b22", "header_border": "#30363d",
                "separator_bg": "#30363d",
                "add_btn_bg": "#196c2e", "add_btn_hover": "#1a7f37", "add_btn_pressed": "#0f4a20",
                "ctrl_btn_bg": "#21262d", "ctrl_btn_border": "#30363d",
                "ctrl_btn_hover": "#30363d", "ctrl_btn_text": "#c9d1d9",
            },
        }
        c = _THEME_COLORS.get(_current_theme, _THEME_COLORS["default"])

        # Input field
        self.input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['input_bg']};
                color: {c['ctrl_btn_text']};
                border: 1px solid {c['input_border']};
                border-radius: 4px;
                padding: 8px;
                font-size: 9pt;
            }}
            QTextEdit:focus {{
                border: 2px solid {c['input_focus']};
            }}
        """)

        # Add Task button
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['add_btn_bg']};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 8pt;
            }}
            QPushButton:hover {{ background-color: {c['add_btn_hover']}; }}
            QPushButton:pressed {{ background-color: {c['add_btn_pressed']}; }}
            QPushButton:disabled {{ background-color: {c['ctrl_btn_border']}; }}
        """)

        # Control buttons (Up, Down, Delete, etc.)
        ctrl_style = f"""
            QPushButton {{
                background-color: {c['ctrl_btn_bg']};
                color: {c['ctrl_btn_text']};
                border: 1px solid {c['ctrl_btn_border']};
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 7pt;
            }}
            QPushButton:hover {{ background-color: {c['ctrl_btn_hover']}; }}
            QPushButton:disabled {{
                background-color: {p['bg']};
                color: {c['ctrl_btn_border']};
            }}
        """
        for btn in [self.up_btn, self.down_btn, self.delete_btn,
                    self.indent_btn, self.outdent_btn, self.edit_btn,
                    self.priority_btn, self.due_date_btn]:
            btn.setStyleSheet(ctrl_style)

        # Panel backgrounds
        self.stats_label.setStyleSheet(f"""
            QLabel {{
                color: {c['ctrl_btn_border']};
                font-style: italic;
                font-size: 8pt;
                padding: 5px;
            }}
        """)

        # Separator
        self.separator_frame.setStyleSheet(
            f"background-color: {c['separator_bg']};"
        )
        self.priority_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {p['bg']};
                border-radius: 4px;
                padding: 0px;
            }}
        """)
        self.control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {p['scroll_btn_bg']};
                border-radius: 4px;
                padding: 0px;
            }}
        """)
        # Tree widget
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {c['tree_border']};
                border-radius: 4px;
                background-color: {c['tree_bg']};
                alternate-background-color: {c['tree_alt_bg']};
                color: {c['ctrl_btn_text']};
                font-size: 11pt;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 8px 2px;
                border-bottom: 1px solid {c['tree_item_border']};
                min-height: 35px;
            }}
            QTreeWidget::item:hover {{
                background-color: {c['tree_hover']};
            }}
            QTreeWidget::item:selected {{
                background-color: {c['tree_selected']};
                color: {c['tree_selected_text']};
            }}
            QHeaderView::section {{
                background-color: {c['header_bg']};
                color: {c['ctrl_btn_text']};
                padding: 4px;
                border: 1px solid {c['header_border']};
                font-weight: bold;
                font-size: 11pt;
            }}
        """)

        # Priority combo
        self.priority_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c['input_bg']};
                color: {c['ctrl_btn_text']};
                border: 1px solid {c['ctrl_btn_border']};
                border-radius: 3px;
                padding: 3px 8px;
                min-width: 80px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['input_bg']};
                color: {c['ctrl_btn_text']};
                selection-background-color: {c['tree_selected']};
            }}
        """)

        # Auto-open checkbox and labels
        text_color = '#c9d1d9' if _current_theme in ('dark', 'midnight') else '#333333'
        self.auto_open_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {text_color};
                padding: 3px;
            }}
        """)

        # Also update priority colors in the delegate for dark themes
        delegate = self.tree.itemDelegate()
        if hasattr(delegate, '_apply_theme_colors'):
            delegate._apply_theme_colors()
        self.tree.viewport().update()

    def on_auto_open_changed(self, state):
        """Save state when auto-open checkbox changes"""
        # Find parent TodoApp and save
        parent = self.parent()
        while parent:
            if isinstance(parent, TodoApp):
                parent.save_state()
                break
            parent = parent.parent()

    def eventFilter(self, obj, event):
        # Handle Ctrl+Enter in input field
        if obj == self.input:
            if event.type() == event.KeyPress:
                if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
                    self.add_task()
                    return True
        
        # Handle tree viewport resize
        if hasattr(self, 'tree') and obj == self.tree.viewport():
            if event.type() == event.Resize:
                self.resize_timer.start(100)
        
        return super().eventFilter(obj, event)

    def update_all_row_heights(self):
        """Update heights for all rows in the tree"""
        def update_item_height(item):
            index = self.tree.indexFromItem(item, 1)
            if index.isValid():
                self.tree.update(index)
            
            for i in range(item.childCount()):
                update_item_height(item.child(i))
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            update_item_height(root.child(i))
        
        self.tree.scheduleDelayedItemsLayout()

    def add_task(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        
        priority = self.priority_combo.currentText()
        
        item = QTreeWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        item.setText(1, text)
        item.setData(1, Qt.UserRole, priority)  # Store priority
        
        selected = self.tree.selectedItems()
        if selected:
            parent = selected[0]
            parent.addChild(item)
            parent.setExpanded(True)
        else:
            self.tree.addTopLevelItem(item)
        
        self.input.clear()
        self.updateStats()
        
        QTimer.singleShot(10, self.update_all_row_heights)
        self._trigger_auto_save()
        
    def change_priority(self):
        """Change the priority of selected task"""
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        current_priority = item.data(1, Qt.UserRole) or 'Normal'
        
        priority, ok = QInputDialog.getItem(
            self, "Change Priority", "Select priority:",
            ["Urgent", "Normal", "Optional"], 
            ["Urgent", "Normal", "Optional"].index(current_priority),
            False
        )
        
        if ok:
            item.setData(1, Qt.UserRole, priority)
            QTimer.singleShot(10, self.update_all_row_heights)

    def set_due_date(self):
        """Set or clear the due date for selected task"""
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        current_due_date = item.data(1, Qt.UserRole + 1) or ""
        
        # Create a simple dialog
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDateEdit, QDialogButtonBox
        from PyQt5.QtCore import QDate
        from datetime import datetime
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Due Date")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Date picker
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        
        # Set current date or today
        if current_due_date:
            try:
                date_obj = datetime.fromisoformat(current_due_date)
                date_edit.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
            except:
                date_edit.setDate(QDate.currentDate())
        else:
            date_edit.setDate(QDate.currentDate())
        
        layout.addWidget(QLabel("Select due date:"))
        layout.addWidget(date_edit)
        
        # Buttons
        button_box = QDialogButtonBox()
        set_btn = button_box.addButton("Set Date", QDialogButtonBox.AcceptRole)
        clear_btn = button_box.addButton("Clear Date", QDialogButtonBox.ResetRole)
        cancel_btn = button_box.addButton(QDialogButtonBox.Cancel)
        
        layout.addWidget(button_box)
        
        result = [None]
        
        def on_set():
            date = date_edit.date()
            result[0] = date.toString("yyyy-MM-dd")
            dialog.accept()
        
        def on_clear():
            result[0] = ""
            dialog.accept()
        
        set_btn.clicked.connect(on_set)
        clear_btn.clicked.connect(on_clear)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec_() == QDialog.Accepted:
            if result[0] == "":
                item.setData(1, Qt.UserRole + 1, None)  # Clear due date
            elif result[0]:
                item.setData(1, Qt.UserRole + 1, result[0])  # Set due date
            QTimer.singleShot(10, self.update_all_row_heights)

    def edit_task(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        current_text = item.text(1)
        
        text, ok = QInputDialog.getMultiLineText(
            self, "Edit Task", "Edit task text:", current_text
        )
        
        if ok and text.strip():
            item.setText(1, text.strip())
            QTimer.singleShot(10, self.update_all_row_heights)

    def delete_task(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        parent = item.parent()
        
        if parent:
            parent.removeChild(item)
        else:
            index = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(index)
        
        self.updateStats()
        self._trigger_auto_save()

    def move_up(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        parent = item.parent()
        
        if parent:
            index = parent.indexOfChild(item)
            if index > 0:
                parent.takeChild(index)
                parent.insertChild(index - 1, item)
                self.tree.setCurrentItem(item)
        else:
            index = self.tree.indexOfTopLevelItem(item)
            if index > 0:
                self.tree.takeTopLevelItem(index)
                self.tree.insertTopLevelItem(index - 1, item)
                self.tree.setCurrentItem(item)

    def move_down(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        parent = item.parent()
        
        if parent:
            index = parent.indexOfChild(item)
            if index < parent.childCount() - 1:
                parent.takeChild(index)
                parent.insertChild(index + 1, item)
                self.tree.setCurrentItem(item)
        else:
            index = self.tree.indexOfTopLevelItem(item)
            if index < self.tree.topLevelItemCount() - 1:
                self.tree.takeTopLevelItem(index)
                self.tree.insertTopLevelItem(index + 1, item)
                self.tree.setCurrentItem(item)

    def clone_item_recursive(self, item):
        """Clone an item with all its data and children"""
        new_item = QTreeWidgetItem()
        new_item.setFlags(item.flags())
        
        # Copy all column data
        for col in range(self.tree.columnCount()):
            new_item.setText(col, item.text(col))
            new_item.setCheckState(col, item.checkState(col))
            # Copy user data (priority)
            data = item.data(col, Qt.UserRole)
            if data:
                new_item.setData(col, Qt.UserRole, data)
            # Copy due date
            due_date = item.data(col, Qt.UserRole + 1)
            if due_date:
                new_item.setData(col, Qt.UserRole + 1, due_date)
        
        # Recursively clone children
        for i in range(item.childCount()):
            child = item.child(i)
            new_child = self.clone_item_recursive(child)
            new_item.addChild(new_child)
        
        # Preserve expanded state
        new_item.setExpanded(item.isExpanded())
        
        return new_item

    def indent_task(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        parent = item.parent()
        
        if parent:
            index = parent.indexOfChild(item)
            if index > 0:
                new_parent = parent.child(index - 1)
                # Clone the item with all its children and data
                item_clone = self.clone_item_recursive(item)
                parent.takeChild(index)
                new_parent.addChild(item_clone)
                new_parent.setExpanded(True)
                self.tree.setCurrentItem(item_clone)
        else:
            index = self.tree.indexOfTopLevelItem(item)
            if index > 0:
                new_parent = self.tree.topLevelItem(index - 1)
                # Clone the item with all its children and data
                item_clone = self.clone_item_recursive(item)
                self.tree.takeTopLevelItem(index)
                new_parent.addChild(item_clone)
                new_parent.setExpanded(True)
                self.tree.setCurrentItem(item_clone)

    def outdent_task(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        parent = item.parent()
        
        if not parent:
            return
        
        grandparent = parent.parent()
        index = parent.indexOfChild(item)
        
        # Clone the item with all its children and data
        item_clone = self.clone_item_recursive(item)
        parent.takeChild(index)
        
        if grandparent:
            parent_index = grandparent.indexOfChild(parent)
            grandparent.insertChild(parent_index + 1, item_clone)
        else:
            parent_index = self.tree.indexOfTopLevelItem(parent)
            self.tree.insertTopLevelItem(parent_index + 1, item_clone)
        
        self.tree.setCurrentItem(item_clone)

    def on_item_changed(self, item, column):
        self.updateStats()
        if column == 0:
            QTimer.singleShot(10, self.update_all_row_heights)
        # Auto-save after changes
        self._trigger_auto_save()

    # ADD this new method to TodoTab class:
    def _trigger_auto_save(self):
        """Trigger auto-save with debounce"""
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._do_auto_save)
        self._save_timer.start(1000)  # Save after 1 second of inactivity

    def _do_auto_save(self):
        """Perform auto-save"""
        parent = self.parent()
        while parent:
            if isinstance(parent, TodoApp):
                parent.save_state()
                #print("DEBUG: Auto-saved")
                break
            parent = parent.parent()
        

    def update_button_state(self):
        has_selection = len(self.tree.selectedItems()) > 0
        self.delete_btn.setEnabled(has_selection)
        self.up_btn.setEnabled(has_selection)
        self.down_btn.setEnabled(has_selection)
        self.indent_btn.setEnabled(has_selection)
        self.outdent_btn.setEnabled(has_selection)
        self.edit_btn.setEnabled(has_selection)
        self.priority_btn.setEnabled(has_selection)
        self.due_date_btn.setEnabled(has_selection)

    def updateStats(self):
        total = self.count_items()
        completed = self.count_completed()
        remaining = total - completed
        
        # Count by priority
        urgent = self.count_by_priority('Urgent')
        normal = self.count_by_priority('Normal')
        optional = self.count_by_priority('Optional')
        
        if total == 0:
            self.stats_label.setText("0 tasks")
        else:
            self.stats_label.setText(
                f"{total} task{'s' if total != 1 else ''} "
                f"({completed} completed, {remaining} remaining) • "
                f"✅ {urgent} • ✔ {normal} • ☑ {optional}"
            )

    def count_items(self, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()
        
        count = parent.childCount()
        for i in range(parent.childCount()):
            count += self.count_items(parent.child(i))
        return count

    def count_completed(self, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()
        
        count = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.checkState(0) == Qt.Checked:
                count += 1
            count += self.count_completed(child)
        return count

    def count_by_priority(self, priority, parent=None):
        """Count tasks by priority level"""
        if parent is None:
            parent = self.tree.invisibleRootItem()
        
        count = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            item_priority = child.data(1, Qt.UserRole) or 'Normal'
            if item_priority == priority:
                count += 1
            count += self.count_by_priority(priority, child)
        return count

    def serialize(self, parent=None):
        """Serialize tree items to a list of dictionaries"""
        items = []
        if parent is None:
            parent = self.tree.invisibleRootItem()
        
        for i in range(parent.childCount()):
            item = parent.child(i)
            item_data = {
                "text": item.text(1),
                "checked": item.checkState(0) == Qt.Checked,
                "priority": item.data(1, Qt.UserRole) or 'Normal',
                "due_date": item.data(1, Qt.UserRole + 1) or None,  # Store due date
                "children": self.serialize(item)
            }
            items.append(item_data)
        
        return items

    def deserialize(self, items, parent=None):
        """Deserialize list of dictionaries to tree items"""
        for item_data in items:
            item = QTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
            item.setText(1, item_data.get("text", ""))
            item.setCheckState(0, Qt.Checked if item_data.get("checked") else Qt.Unchecked)
            item.setData(1, Qt.UserRole, item_data.get("priority", "Normal"))
            item.setData(1, Qt.UserRole + 1, item_data.get("due_date"))  # Load due date
            
            if parent:
                parent.addChild(item)
            else:
                self.tree.addTopLevelItem(item)
            
            if "children" in item_data:
                self.deserialize(item_data["children"], item)
                if item_data["children"]:
                    item.setExpanded(True)
        
        self.updateStats()
        QTimer.singleShot(50, self.update_all_row_heights)


class TodoApp(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Todo List")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(400, 300)
        self.setupUI()
        self.load_state()
        self.refresh_styles()

    def setupUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Tab widget
        self.tabs = QTabWidget()
        
        self.tabs.setTabBar(ContentSizedTabBar())
        
        self.tabs.tabBar().setDrawBase(False)
        
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.ElideNone) 
        
        
        # Get the tab bar and set expanding tabs
        tab_bar = self.tabs.tabBar()
        tab_bar.setExpanding(False)  # Don't force equal widths
        tab_bar.setElideMode(Qt.ElideNone)
        
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                
                padding: 6px 12px;
                height: 18px;        
                margin-right: 2px;                
                font-size: 8pt;
                min-width: 30px;
                max-width: 300px;
            }
            QTabBar::tab:selected {
                background: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #e0e0e0;
            }
        """)
        
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        self.tabs.tabBar().setElideMode(Qt.ElideNone)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.setUsesScrollButtons(True)
        
        
        main_layout.addWidget(self.tabs)

        # Bottom buttons
        self.button_frame = QFrame()
        self.button_frame.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 4px;
                padding: 0px;
            }
        """)
        button_layout = QHBoxLayout(self.button_frame)
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(5, 5, 5, 5)
        
        self.new_tab_btn = QPushButton("➕ New List")
        self.rename_tab_btn = QPushButton("✏️ Rename")
        self.export_btn = QPushButton("📤 Export")
        self.import_btn = QPushButton("📥 Import")
        
        button_style = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0a6ebd;
            }
        """
        
        for btn in [self.new_tab_btn, self.rename_tab_btn, self.export_btn, self.import_btn]:
            btn.setStyleSheet(button_style)
            btn.setFixedHeight(30)
            button_layout.addWidget(btn)
        
        button_layout.addStretch()
        
        self.clear_btn = QPushButton("🗑 Clear All")
        self.clear_btn.setFixedHeight(30)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(self.clear_btn)
        
        main_layout.addWidget(self.button_frame)

        # Connect signals
        self.new_tab_btn.clicked.connect(lambda: self.add_tab())
        self.rename_tab_btn.clicked.connect(self.rename_tab)
        self.export_btn.clicked.connect(self.export_data)
        self.import_btn.clicked.connect(self.import_data)
        self.clear_btn.clicked.connect(self.clear_all)


    def refresh_styles(self):
        """Re-apply all theme-aware styles to TodoApp widgets."""
        from style_manager import get_panel_style, _current_theme
        p = get_panel_style()

        _BTN_COLORS = {
            "default":  {"main": "#2196F3", "hover": "#0b7dda", "pressed": "#0a6ebd",
                         "clear": "#f44336", "clear_hover": "#da190b"},
            "dark":     {"main": "#1a4f8a", "hover": "#1a5fa0", "pressed": "#1450a0",
                         "clear": "#8b2020", "clear_hover": "#a02020"},
            "light":    {"main": "#1a7acc", "hover": "#1060aa", "pressed": "#0d50a0",
                         "clear": "#cc2200", "clear_hover": "#bb1100"},
            "midnight": {"main": "#0d419d", "hover": "#1158c7", "pressed": "#0a32a0",
                         "clear": "#8b1a1a", "clear_hover": "#cf222e"},
        }
        bc = _BTN_COLORS.get(_current_theme, _BTN_COLORS["default"])

        # Tab widget
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {p['scroll_btn_border']};
                border-radius: 4px;
                background: {p['bg']};
            }}
            QTabBar::tab {{
                background: {p['scroll_btn_bg']};
                color: {'#c9d1d9' if _current_theme in ('dark','midnight') else '#333333'};
                border: 1px solid {p['scroll_btn_border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                height: 18px;
                margin-right: 2px;
                font-size: 8pt;
                min-width: 30px;
            }}
            QTabBar::tab:selected {{
                background: {p['bg']};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background: {p['scroll_btn_hover']};
            }}
        """)

        self.button_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {p['scroll_btn_bg']};
                border-radius: 4px;
                padding: 0px;
            }}
        """)

        # Bottom action buttons
        btn_style = f"""
            QPushButton {{
                background-color: {bc['main']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 8pt;
            }}
            QPushButton:hover {{ background-color: {bc['hover']}; }}
            QPushButton:pressed {{ background-color: {bc['pressed']}; }}
        """
        for btn in [self.new_tab_btn, self.rename_tab_btn,
                    self.export_btn, self.import_btn]:
            btn.setStyleSheet(btn_style)

        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bc['clear']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 8pt;
            }}
            QPushButton:hover {{ background-color: {bc['clear_hover']}; }}
        """)

        # Refresh all child TodoTab instances
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, TodoTab):
                tab.refresh_styles()

    def todo_file_path(self):
        """Return the full path to the TodoList.json file using the app's config directory."""
        app_name = app_info.APP_NAME 
        system = sys.platform.lower()

        if system.startswith('win'):
            appdata = os.environ.get('APPDATA')
            if appdata:
                config_dir = os.path.join(appdata, app_name)
            else:
                config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', app_name)
        elif system.startswith('darwin'):
            config_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
        else:
            xdg = os.environ.get('XDG_CONFIG_HOME')
            if xdg:
                config_dir = os.path.join(xdg, app_name)
            else:
                config_dir = os.path.join(os.path.expanduser('~'), '.config', app_name)

        os.makedirs(config_dir, exist_ok=True)
        path = os.path.join(config_dir, "TodoList.json")
        #print(f"DEBUG: Todo file path = {path}")
        return path



    def add_tab(self, title=None):
        """Add a new tab to the todo list"""
        if title is None:
            title, ok = QInputDialog.getText(self, "New List", "Enter list title:")
            if not ok or not title.strip():
                return None
            title = title.strip()
        
        tab = TodoTab(self)  # Pass parent
        index = self.tabs.addTab(tab, title)
        self.tabs.setCurrentIndex(index)
        return tab
    

    def rename_tab(self):
        index = self.tabs.currentIndex()
        if index < 0:
            return

        current_title = self.tabs.tabText(index)
        title, ok = QInputDialog.getText(
            self, "Rename List", "Enter new title:",
            text=current_title
        )
        if ok and title.strip():
            self.tabs.setTabText(index, title.strip())

    def close_tab(self, index):
        if self.tabs.count() <= 1:
            QMessageBox.warning(self, "Cannot Close", "At least one tab must remain open.")
            return
        
        reply = QMessageBox.question(
            self, "Close Tab",
            f"Close '{self.tabs.tabText(index)}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.tabs.removeTab(index)

    def on_tab_changed(self, index):
        self.rename_tab_btn.setEnabled(index >= 0)

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Todo Lists", "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if path:
            data = self.get_all_data()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Export Successful", "Todo lists exported successfully!")

    def import_data(self):
        reply = QMessageBox.question(
            self, "Import Data",
            "This will replace all current data. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Todo Lists", "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Clear existing tabs
                while self.tabs.count() > 0:
                    self.tabs.removeTab(0)
                
                # Load imported tabs
                for tab_data in data.get("tabs", []):
                    tab = self.add_tab(tab_data.get("title", "Imported List"))
                    if tab:
                        tab.deserialize(tab_data.get("items", []))
                
                QMessageBox.information(self, "Import Successful", "Todo lists imported successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"Error importing data: {str(e)}")

    def clear_all(self):
        reply = QMessageBox.question(
            self, "Clear All",
            "This will remove all tasks from current tab. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            current_tab = self.tabs.currentWidget()
            if current_tab:
                current_tab.tree.clear()
                current_tab.updateStats()

    def get_all_data(self):
        data = {"tabs": [], "auto_open": False}
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab_title = self.tabs.tabText(i)
            tab_items = tab.serialize()
            data["tabs"].append({
                "title": tab_title,
                "items": tab_items
            })
            if hasattr(tab, 'auto_open_checkbox'):
                data["auto_open"] = tab.auto_open_checkbox.isChecked()
        return data
    
    
    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)

    def save_state(self):
        data = self.get_all_data()
        path = self.todo_file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving state: {e}")
            import traceback
            traceback.print_exc()
        

    def load_state(self):
        path = self.todo_file_path()
        if not os.path.exists(path):
            # No saved data, create default tab
            self.add_tab("My Tasks")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            tabs_data = data.get("tabs", [])
            auto_open = data.get("auto_open", False)
            
            if not tabs_data:
                # No tabs saved, create default
                self.add_tab("My Tasks")
                return
            
            for tab_data in tabs_data:
                title = tab_data.get("title", "List")
                tab = self.add_tab(title)
                if tab:
                    tab.deserialize(tab_data.get("items", []))
                    if hasattr(tab, 'auto_open_checkbox'):
                        tab.auto_open_checkbox.setChecked(auto_open)
            
        except Exception as e:
            print(f"Error loading state: {e}")
            import traceback
            traceback.print_exc()
            # On error, create default tab
            if self.tabs.count() == 0:
                self.add_tab("My Tasks")
            


def should_auto_open_todo(main_window=None):
    """Check if todo list should auto-open on startup."""
    try:
        if main_window and hasattr(main_window, 'config_manager'):
            config_dir = main_window.config_manager.config_dir
        else:
            config_dir = os.path.join(os.path.expanduser("~"), ".todolist_app")
        path = os.path.join(config_dir, "TodoList.json")
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("auto_open", False)
    except Exception:
        return False


def add_todo_tab_to_pdf_viewer(main_window):
    """Add the todo list tab to the PDF viewer"""
    lang = main_window.menu_language
    translations = main_window.translations
    tr = translations[lang]              
    try:
        if not hasattr(main_window, 'pdf_manager'):
            QMessageBox.warning(main_window, "Warning", "PDF manager not available!")
            return
        if not hasattr(main_window, 'layout_manager'):
            QMessageBox.warning(main_window, "Warning", "Layout manager not available!")
            return


        layout_manager = main_window.layout_manager
        pdf_manager = main_window.pdf_manager

        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info", 
                "Todo list tab is only available in tabbed mode.")
            return

        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
            from PyQt5.QtWidgets import QTabWidget
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(pdf_manager.close_pdf_tab)
            pdf_layout = layout_manager.pdf_container.layout()
            if pdf_layout:
                while pdf_layout.count():
                    item = pdf_layout.takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)
                pdf_layout.addWidget(pdf_manager.pdf_tabs)

        tab_widget = pdf_manager.pdf_tabs

        # Check if Todo tab already exists
        possible_labels = {
            tr["todo_list"] for tr in translations.values()
        }                        
            
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                tab_widget.setCurrentIndex(i)
                return

        # Create and add todo tab
        todo_tab = TodoApp(main_window)
        tab_name = tr.get("todo_list", "Todo List")
        tab_index = tab_widget.addTab(todo_tab, tab_name)    
        tab_widget.tabBar().setTabData(tab_index, "todo_list")   
        
        # ✅ Set SVG icon properly
        icon = QIcon("icons/todo.svg")
        tab_widget.setTabIcon(tab_index, icon)        
        

        # Store reference for theme refresh
        if not hasattr(main_window, '_todo_tabs'):
            main_window._todo_tabs = []
        main_window._todo_tabs.append(todo_tab)

        
        # ADD THIS: Connect tab close to save
        # def save_on_close(index):
            # widget = tab_widget.widget(index)
            # if isinstance(widget, TodoApp):
                # print("DEBUG: Saving todo on tab close")
                # widget.save_state()
        
        # Disconnect existing and reconnect with save
        try:
            tab_widget.tabCloseRequested.disconnect()
        except:
            pass
        
        def handle_tab_close(index):
            widget = tab_widget.widget(index)
            if isinstance(widget, TodoApp):
                widget.save_state()
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.close_pdf_tab(index)
            else:
                tab_widget.removeTab(index)
        
        tab_widget.tabCloseRequested.connect(handle_tab_close)        
        
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)

        tab_widget.show()

    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add todo tab:\n{str(e)}")
        import traceback
        traceback.print_exc()        