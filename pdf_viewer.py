#pdf_viewer.py
"""
PDF Viewer - Handles PDF viewer creation, theme, and operations
"""

import sys
import os
import subprocess


from PyQt5.QtWidgets import (
    QDialog, QListWidget, QDialogButtonBox, QTextEdit, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QComboBox,
    QSpinBox, QApplication, QSizePolicy, QLineEdit, QToolButton, QHBoxLayout,
    QColorDialog, QInputDialog, QMessageBox, QFileDialog, QMenu, QAction
)
from PyQt5.QtCore import Qt, QRect, QProcess, QTimer,  QPoint, QEvent, QSize
from PyQt5.QtGui import (
    QIcon, QPixmap, QPainter, QPen, QCursor, QTextCursor, QColor, QBrush, QPixmap, QPainterPath
)    
try:
    from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
    PRINT_SUPPORT_AVAILABLE = True
except ImportError:
    PRINT_SUPPORT_AVAILABLE = False
import fitz

from icons_manager import IconsManager

class MultiLineTextDialog(QDialog):
    """Dialog for editing multi-line annotation text"""
    def __init__(self, parent=None, title="Edit Text", initial_text="", placeholder="Enter text..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Text edit widget
        from PyQt5.QtWidgets import QTextEdit
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(placeholder)
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setFocus()
        layout.addWidget(self.text_edit)
        
        # Buttons
        from PyQt5.QtWidgets import QDialogButtonBox
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_text(self):
        """Get the entered text"""
        return self.text_edit.toPlainText()

class MarginInputDialog(QDialog):
    """Dialog for entering margin values for 'Fit to text width' feature"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fit to Text Width - Margin Settings")
        self.setModal(True)
        self.setFixedSize(350, 150)
        
        layout = QVBoxLayout(self)
        
        # Instruction label
        info_label = QLabel("Enter the margin to exclude from each side:")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(info_label)
        
        # Margin input row
        margin_layout = QHBoxLayout()
        
        margin_label = QLabel("Margin:")
        margin_layout.addWidget(margin_label)
        
        # Input field
        self.margin_input = QLineEdit()
        self.margin_input.setText("2.5")  # Default value
        self.margin_input.setPlaceholderText("Enter margin value")
        self.margin_input.setFixedWidth(100)
        margin_layout.addWidget(self.margin_input)
        
        # Unit selector
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["cm", "pt", "in"])
        self.unit_combo.setCurrentIndex(0)  # Default to cm
        self.unit_combo.setFixedWidth(80)
        margin_layout.addWidget(self.unit_combo)
        
        margin_layout.addStretch()
        layout.addLayout(margin_layout)
        
        # Help text
        help_label = QLabel("This will zoom to fit the text width, excluding the specified margins.")
        help_label.setStyleSheet("color: #666; font-size: 10px; margin-top: 5px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Focus on input field
        self.margin_input.setFocus()
        self.margin_input.selectAll()
    
    def get_margin_in_points(self):
        """Get the margin value converted to PDF points (1/72 inch)"""
        try:
            value = float(self.margin_input.text())
            unit = self.unit_combo.currentText()
            
            # Convert to points based on unit
            if unit == "cm":
                # 1 cm = 28.35 points
                points = value * 28.35
            elif unit == "in":
                # 1 inch = 72 points
                points = value * 72.0
            elif unit == "pt":
                # Already in points
                points = value
            else:
                points = value * 28.35  # Default to cm
            
            return points
        except ValueError:
            # Return default 2.5 cm in points if invalid input
            return 2.5 * 28.35

class PDFViewer(QWidget):
    """Custom PDF viewer with scrolling, zoom, navigation, text selection, and SyncTeX reverse search"""
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.pdf_document = None
        self.current_pdf_path = None  # Track loaded PDF path
        # ✅ FIX: Load saved zoom factor BEFORE setup_ui
        if main_window and hasattr(main_window, 'config_manager'):
            self.zoom_factor = main_window.config_manager.get_pdf_zoom_factor(default=1.0)
            #print(f"📊 Loaded saved zoom factor: {self.zoom_factor}")
        else:
            self.zoom_factor = 1.0
        #self.zoom_factor = 1.0
        self.page_spacing = 10
        self.pages_per_line = 1  # Grid: number of pages per row (1 = default vertical scroll)
        self.page_labels = []
        self.current_page = 0
        self.total_pages = 0
        
        # ═══════════════════════════════════════════════════════════════════
        # ANNOTATION STATE VARIABLES
        # ═══════════════════════════════════════════════════════════════════
        self.annotation_tool = None
        self.annotation_color = QColor(Qt.magenta)
        self.annotation_pen_width = 2
        self.annotation_drawing = False
        self.annotation_ink_points = []
        self.annotation_start_pos = None
        self.annotation_temp_pixmap = None
        
        # Annotation selection/dragging state
        self.selected_annot_rect = None  # Tuple (x0, y0, x1, y1)
        self.selected_annot_type = None  # String: "Text", "FreeText", etc.
        self.selected_annot_page = -1
        self.dragging_annot = False
        self.drag_start = None  # fitz.Point
        self.last_drag_pos = None  # Tuple (dx, dy)
        
        # Track if document needs saving
        self.annotations_modified = False 

        
        # Selection variables
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        
        # ADD THESE LINES for tooltip support:
        self.tooltips_enabled = False  # Default: tooltips are enabled
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._show_link_tooltip)
        self.pending_tooltip_link = None
        self.pending_tooltip_pos = None


        # ✅ NEW: Navigation history for back/forward
        self.navigation_history = []  # List of (page_num, scroll_y) tuples
        self.history_index = -1  # Current position in history
        self.max_history_size = 50  # Maximum history entries
        self.is_navigating_history = False  # Flag to prevent adding to history during back/forward

        # ✅ NEW: Table of Contents storage
        self.toc_entries = []  # List of (level, title, page) tuples
        
        # SyncTeX variables
        self.synctex_available = self.check_synctex_available()
        
        self.setup_ui()
        
        # ADD THESE LINES:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()  # Force layout recalc
            

        # Magnifying glass variables
        self.magnifier_active = False
        self.magnifier_size = 250
        self.magnifier_zoom = 2.0
        self.magnifier_pos = None
        self.magnifier_quality_multiplier = 2.0

        # Pan and Select mode variables
        self.pan_mode = True  # Default mode is PAN (hand cursor)
        self.select_mode = False  # Select mode for text selection
        self.panning = False
        self.pan_start_pos = None
        self.pan_start_scroll_x = 0
        self.pan_start_scroll_y = 0
        
        # Search-related variables
        self.search_results = []
        self.current_search_index = -1
        self.search_text = ""
        self.search_toolbar_visible = False
        self.all_results_highlighted = False
        
        # NEW: Store references to all toolbar buttons for hiding/showing
        self.main_toolbar_buttons = []  # Will store all non-search buttons
        
        
   
    @property
    def is_valid(self):
        """Check if the PDF viewer is still valid"""
        try:
            return (self is not None and 
                    hasattr(self, 'content_layout') and 
                    self.content_layout is not None and
                    self.content_layout.parent() is not None)
        except RuntimeError:
            return False
        
            
    def check_synctex_available(self):
        """Check if SyncTeX is available on the system"""
        try:
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 5
            }
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = si

            result = subprocess.run(['synctex', '--version'], **kwargs)
            return result.returncode == 0
        except:
            return False


        
    def setup_ui(self):
        """Setup PDF viewer UI with proper size policies"""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ✅ FIX: Enable stylesheet border/background painting on plain QWidget
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        
        toolbar_layout = QHBoxLayout()
        BUTTON_HEIGHT = 25
        
        # ═══════════════════════════════════════════════════════════════════
        # MAIN TOOLBAR BUTTONS (will be hidden during search)
        # ═══════════════════════════════════════════════════════════════════
        
        # Create container widget for main toolbar buttons
        self.main_toolbar_widget = QWidget()
        main_toolbar_layout = QHBoxLayout(self.main_toolbar_widget)
        main_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        main_toolbar_layout.setSpacing(2)
        
        # First page button
        self.first_page_btn = QPushButton()
        #self.first_page_btn = first_page_btn
        self.main_window.icons_manager.apply_icon_to_button(self.first_page_btn, "first_page_btn")
        self.first_page_btn.setToolTip("First page")
        self.first_page_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.first_page_btn.setEnabled(False)
        main_toolbar_layout.addWidget(self.first_page_btn)
                
        # Page spinbox
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1)
        self.page_spinbox.setValue(1)
        self.page_spinbox.setEnabled(False)
        self.page_spinbox.setFixedSize(60, BUTTON_HEIGHT)
        self.page_spinbox.setToolTip("Current page (editable)")
        self.page_spinbox.valueChanged.connect(self.go_to_page_number)
        main_toolbar_layout.addWidget(self.page_spinbox)
        
        # Total pages label
        self.total_pages_label = QLabel("0")
        self.total_pages_label.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.total_pages_label.setAlignment(Qt.AlignCenter)
        #self.total_pages_label.setStyleSheet("background-color: #F0F0F0;")
        self.total_pages_label.setObjectName("Toolbar")
        self.total_pages_label.setToolTip("Total pages")
        main_toolbar_layout.addWidget(self.total_pages_label)
        
       
        # Last page
        self.last_page_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.last_page_btn, "last_page_btn")
        self.last_page_btn.setToolTip("Last page")
        self.last_page_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.last_page_btn.setEnabled(False)
        main_toolbar_layout.addWidget(self.last_page_btn)
        
        main_toolbar_layout.addSpacing(BUTTON_HEIGHT//4)
        
        # Zoom controls
        zoom_out_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(zoom_out_btn, "zoom_out")
        zoom_out_btn.setToolTip("Zoom Out (-)")
        zoom_out_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        zoom_out_btn.clicked.connect(self.zoom_out)
        main_toolbar_layout.addWidget(zoom_out_btn)
        
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setMinimum(10)
        self.zoom_spinbox.setMaximum(500)
        self.zoom_spinbox.setValue(100)
        self.zoom_spinbox.setSuffix("%")
        self.zoom_spinbox.setFixedSize(60, BUTTON_HEIGHT)
        self.zoom_spinbox.setToolTip("Zoom percentage (editable)")
        main_toolbar_layout.addWidget(self.zoom_spinbox)
        
        zoom_in_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(zoom_in_btn, "zoom_in")
        zoom_in_btn.setToolTip("Zoom In (+)")
        zoom_in_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        zoom_in_btn.clicked.connect(self.zoom_in)
        main_toolbar_layout.addWidget(zoom_in_btn)
        
        main_toolbar_layout.addSpacing(BUTTON_HEIGHT//4)
        
        # Select mode
        self.select_mode_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.select_mode_btn, "select_text")
        self.select_mode_btn.setToolTip("Text Selection Mode")
        self.select_mode_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.select_mode_btn.setCheckable(True)
        self.select_mode_btn.clicked.connect(self.toggle_select_mode)
        main_toolbar_layout.addWidget(self.select_mode_btn)
        
        # ✅ UPDATED: Three fit buttons
        # Fit Page Width button
        fit_page_width_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(fit_page_width_btn, "fit_width")
        fit_page_width_btn.setToolTip("Fit Page Width (fit entire page width)")
        fit_page_width_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        fit_page_width_btn.clicked.connect(self.fit_page_width)
        main_toolbar_layout.addWidget(fit_page_width_btn)
        
        # ✅ NEW: Fit to Text Width button
        fit_text_width_btn = QPushButton()
        try:
            self.main_window.icons_manager.apply_icon_to_button(fit_text_width_btn, "fit_text_width")
        except:
            fit_text_width_btn.setText("T")  # Fallback text
            fit_text_width_btn.setStyleSheet("font-weight: bold;")
        fit_text_width_btn.setToolTip("Fit to Text Width (exclude margins)")
        fit_text_width_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        fit_text_width_btn.clicked.connect(self.fit_to_text_width)
        main_toolbar_layout.addWidget(fit_text_width_btn)
        
        # ✅ NEW: Fit Page to Window button
        fit_page_to_window_btn = QPushButton()
        try:
            self.main_window.icons_manager.apply_icon_to_button(fit_page_to_window_btn, "fit_page")
        except:
            fit_page_to_window_btn.setText("□")  # Fallback: square icon
            fit_page_to_window_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        fit_page_to_window_btn.setToolTip("Fit Page to Window (view entire page)")
        fit_page_to_window_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        fit_page_to_window_btn.clicked.connect(self.fit_page_to_window)
        main_toolbar_layout.addWidget(fit_page_to_window_btn)

        # ═══════════════════════════════════════════════════════════════════
        # PAGES PER LINE (GRID VIEW) CONTROL
        # ═══════════════════════════════════════════════════════════════════
        main_toolbar_layout.addSpacing(BUTTON_HEIGHT // 4)

        self.pages_per_line_combo = QComboBox()
        for i in range(1, 11):
            self.pages_per_line_combo.addItem(str(i))
        self.pages_per_line_combo.setCurrentIndex(0)  # Default: 1 page per line
        self.pages_per_line_combo.setFixedSize(35, BUTTON_HEIGHT)
        self.pages_per_line_combo.setToolTip(
            "Pages per line: choose 1–10 pages displayed side by side"
        )
        self.pages_per_line_combo.currentTextChanged.connect(
            lambda _: (
                setattr(self, "pages_per_line",
                        int(self.pages_per_line_combo.currentText())),
                self.fit_page_width()
            )
        )
        
        main_toolbar_layout.addWidget(self.pages_per_line_combo)

        main_toolbar_layout.addSpacing(BUTTON_HEIGHT // 4)

        
        # Print
        self.print_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.print_btn, "print_pdf")
        self.print_btn.setToolTip("Print PDF (Ctrl+P)")
        self.print_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.print_btn.clicked.connect(self.print_pdf)
        main_toolbar_layout.addWidget(self.print_btn)
        
        main_toolbar_layout.addSpacing(BUTTON_HEIGHT//4)
        
        # Open in External Viewer
        self.open_external_btn = QPushButton()
        try:
            self.main_window.icons_manager.apply_icon_to_button(self.open_external_btn, "open_external")
        except:
            self.open_external_btn.setText("📂")  # Fallback emoji
        #self.main_window.icons_manager.apply_icon_to_button(self.open_external_btn, "open")  # Reuse existing open icon
        self.open_external_btn.setToolTip("Open in External PDF Viewer")
        self.open_external_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.open_external_btn.clicked.connect(self.open_in_external_viewer)
        self.open_external_btn.setEnabled(False)  # Initially disabled until PDF is loaded
        main_toolbar_layout.addWidget(self.open_external_btn)

        main_toolbar_layout.addSpacing(BUTTON_HEIGHT//4)
        
        # Navigation history
        self.back_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.back_btn, "back_nav")
        self.back_btn.setToolTip("Go back (Alt+Left)")
        self.back_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.back_btn.clicked.connect(self.navigate_back)
        self.back_btn.setEnabled(False)
        main_toolbar_layout.addWidget(self.back_btn)
        
        # Tooltip toggle
        self.tooltip_toggle_btn = QPushButton()
        self.tooltip_toggle_btn.setCheckable(True)
        self.tooltip_toggle_btn.setChecked(False)
        self.tooltip_toggle_btn.setToolTip("Toggle link tooltips")
        self.tooltip_toggle_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.tooltip_toggle_btn.clicked.connect(self.toggle_tooltips)
        if hasattr(self.main_window, 'icons_manager'):
            try:
                self.main_window.icons_manager.apply_icon_to_button(self.tooltip_toggle_btn, "tooltip_toggle")
            except:
                self.tooltip_toggle_btn.setText("💬")
        else:
            self.tooltip_toggle_btn.setText("💬")
        self._update_tooltip_button_style()
        main_toolbar_layout.addWidget(self.tooltip_toggle_btn)
        
        # Forward
        self.forward_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.forward_btn, "forward_nav")
        self.forward_btn.setToolTip("Go forward (Alt+Right)")
        self.forward_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.forward_btn.clicked.connect(self.navigate_forward)
        self.forward_btn.setEnabled(False)
        main_toolbar_layout.addWidget(self.forward_btn)
        
        main_toolbar_layout.addSpacing(BUTTON_HEIGHT//4)
        
        # Expand
        self.expand_btn = QPushButton()
        self.is_expanded = False
        self.main_window.icons_manager.apply_icon_to_button(self.expand_btn, "expand_width")
        self.expand_btn.setToolTip("Expand to full width")
        self.expand_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.expand_btn.clicked.connect(self.toggle_expand_width)
        main_toolbar_layout.addWidget(self.expand_btn)
        
        # SyncTeX
        if self.synctex_available:
            synctex_btn = QPushButton()
            self.synctex_btn = synctex_btn  # ✅ Store reference
            self.main_window.icons_manager.apply_icon_to_button(synctex_btn, "reverse")
            synctex_btn.setToolTip("Reverse Search (Ctrl+Click)")
            synctex_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
            synctex_btn.setCheckable(True)  # ✅ Make it checkable
            synctex_btn.clicked.connect(self.toggle_reverse_search_mode)
            main_toolbar_layout.addWidget(synctex_btn)
            
            # ═══════════════════════════════════════════════════════════════════
            # ANNOTATIONS TOGGLE BUTTON (add to main toolbar)
            # ═══════════════════════════════════════════════════════════════════
            main_toolbar_layout.addSpacing(BUTTON_HEIGHT // 4)
            
            self.annotations_btn = QPushButton()
            try:
                self.main_window.icons_manager.apply_icon_to_button(self.annotations_btn, "annotations")
            except:
                self.annotations_btn.setText("📝")
            self.annotations_btn.setToolTip("Toggle Annotations Toolbar")
            self.annotations_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
            self.annotations_btn.setCheckable(True)
            self.annotations_btn.clicked.connect(self._toggle_annotation_toolbar)
            main_toolbar_layout.addWidget(self.annotations_btn)
        
        
        main_toolbar_layout.addStretch()
        
        # Add main toolbar widget to toolbar
        toolbar_layout.addWidget(self.main_toolbar_widget)
        
        # ═══════════════════════════════════════════════════════════════════
        # SEARCH TOOLBAR (replaces main toolbar when active)
        # ═══════════════════════════════════════════════════════════════════
        # Search toggle button (always visible)
        self.search_toggle_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.search_toggle_btn, "search")
        self.search_toggle_btn.setToolTip("Search in PDF (Ctrl+F)")
        self.search_toggle_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.search_toggle_btn.setCheckable(True)
        self.search_toggle_btn.clicked.connect(self.toggle_search_toolbar)
        toolbar_layout.addWidget(self.search_toggle_btn)
        
        # ═══════════════════════════════════════════════════════════════════
        # SEARCH CONTROLS CONTAINER (hidden by default)
        # ═══════════════════════════════════════════════════════════════════
        self.search_container = QWidget()
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(2)
        
        # ✅ NEW: TOC/Signets label
        #toc_label = QLabel("📑")
        toc_label = QLabel("ToC")
        toc_label.setFixedHeight(BUTTON_HEIGHT)
        toc_label.setFixedWidth(BUTTON_HEIGHT)
        toc_label.setAlignment(Qt.AlignCenter)
        toc_label.setToolTip("Table of Contents")
        search_layout.addWidget(toc_label)
        
        # ✅ NEW: TOC/Signets ComboBox
        self.toc_combo = QComboBox()
        self.toc_combo.setFixedHeight(BUTTON_HEIGHT)
        self.toc_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toc_combo.setMinimumWidth(200)
        self.toc_combo.setPlaceholderText("Jump to section...")
        self.toc_combo.setToolTip("Select a section to navigate")
        self.toc_combo.currentIndexChanged.connect(self.on_toc_selected)
        search_layout.addWidget(self.toc_combo)
        
        # ✅ NEW: Separator between search and TOC
        separator = QLabel("|")
        separator.setFixedHeight(BUTTON_HEIGHT)
        separator.setAlignment(Qt.AlignCenter)
        separator.setStyleSheet("color: #999; font-size: 14px; padding: 0 5px;")
        search_layout.addWidget(separator)
        
        # Previous search result button
        self.prev_search_btn = QPushButton("◀")
        self.prev_search_btn.setToolTip("Previous result (Shift+F3)")
        self.prev_search_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.prev_search_btn.clicked.connect(self.search_previous)
        self.prev_search_btn.setEnabled(False)
        search_layout.addWidget(self.prev_search_btn)
        
        # Search text field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search in PDF...")
        self.search_field.setFixedHeight(BUTTON_HEIGHT)
        self.search_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_field.setMinimumWidth(150)
        self.search_field.returnPressed.connect(self.perform_search)
        self.search_field.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_field)
        
        # Next search result button  
        self.next_search_btn = QPushButton("▶")
        self.next_search_btn.setToolTip("Next result (F3 or Enter)")
        self.next_search_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.next_search_btn.clicked.connect(self.search_next)
        self.next_search_btn.setEnabled(False)
        search_layout.addWidget(self.next_search_btn)
        
        # Search results label
        self.search_results_label = QLabel("")
        self.search_results_label.setFixedHeight(BUTTON_HEIGHT)
        self.search_results_label.setFixedWidth(60)
        self.search_results_label.setAlignment(Qt.AlignCenter)
        self.search_results_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        search_layout.addWidget(self.search_results_label)
        
        
        # Close search button
        self.close_search_btn = QPushButton("✕")
        self.close_search_btn.setToolTip("Close search (Esc)")
        self.close_search_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.close_search_btn.setStyleSheet("font-weight: bold; color: #555;")
        self.close_search_btn.clicked.connect(self.hide_search_toolbar)
        search_layout.addWidget(self.close_search_btn)
        
        # Initially hide search container
        self.search_container.setVisible(False)
        toolbar_layout.addWidget(self.search_container)
        
        
        # Create toolbar widget
        toolbar_widget = QWidget()
        self.toolbar_widget = toolbar_widget
        toolbar_widget.setLayout(toolbar_layout)
        toolbar_widget.setFixedHeight(BUTTON_HEIGHT+2)
        toolbar_widget.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setContentsMargins(1, 1, 1, 1)
        toolbar_layout.setSpacing(2)
        
        # Set arrow cursor for toolbar
        toolbar_widget.setCursor(Qt.ArrowCursor)
        
        layout.addWidget(self.toolbar_widget)
        
        # ═══════════════════════════════════════════════════════════════════
        # ANNOTATION TOOLBAR (hidden by default)
        # ═══════════════════════════════════════════════════════════════════
        self.annotation_toolbar_widget = QWidget()
        annotation_toolbar_layout = QHBoxLayout(self.annotation_toolbar_widget)
        annotation_toolbar_layout.setContentsMargins(4, 2, 4, 2)
        annotation_toolbar_layout.setSpacing(3)
        
        # Tool actions dictionary
        self.annotation_tool_actions = {}
        
        # Define annotation tools with icons, names, and tooltips
        annotation_tools = [
            ("icons/select.svg", "🖱️", "select", "Select/Move annotations"),
            ("icons/note.svg", "📝", "text", "Add sticky note"),
            ("icons/textbox.svg", "T", "freetext", "Add text box"),
            ("icons/highlight.svg", "🖍️", "highlight", "Highlight area"),
            ("icons/rect.svg", "⬜", "rect", "Draw rectangle"),
            ("icons/circle.svg", "⭕", "circle", "Draw circle/ellipse"),
            ("icons/line.svg", "📏", "line", "Draw line"),
            ("icons/ink.svg", "✍️", "ink", "Freehand drawing"),
        ]
        
        def create_tool_button(svg_path, fallback_text, tooltip):
            btn = QPushButton()
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)

            if svg_path and os.path.exists(svg_path):
                btn.setIcon(QIcon(svg_path))
                btn.setIconSize(QSize(24, 24))
            else:
                btn.setText(fallback_text)

            return btn
        
        # Create tool buttons
        for svg, emoji, tool, tip in annotation_tools:
            btn = create_tool_button(svg, emoji, tip)
            btn.clicked.connect(lambda checked, t=tool: self._set_annotation_tool(t))

            annotation_toolbar_layout.addWidget(btn)
            self.annotation_tool_actions[tool] = btn

        
        # Separator
        sep_label = QLabel("|")
        sep_label.setStyleSheet("color: #aaa;")
        annotation_toolbar_layout.addWidget(sep_label)
        
        # Color button with color indicator
        self.annot_color_btn = QPushButton()
        self.annot_color_btn.setToolTip("Choose annotation color")
        self.annot_color_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.annot_color_btn.setStyleSheet(f"background-color: {self.annotation_color.name()}; border: 1px solid #888;")
        self.annot_color_btn.clicked.connect(self._choose_annotation_color)
        annotation_toolbar_layout.addWidget(self.annot_color_btn)
        
        # Quick color buttons
        quick_colors = [
            (Qt.red, "Red"),
            (Qt.magenta, "Magenta"),
            (Qt.blue, "Blue"),
            (Qt.green, "Green"),
            (Qt.yellow, "Yellow"),
            (Qt.black, "Black"),
        ]
        for qcolor, name in quick_colors:
            btn = QPushButton()
            btn.setFixedSize(BUTTON_HEIGHT - 4, BUTTON_HEIGHT - 4)
            btn.setStyleSheet(f"background-color: {QColor(qcolor).name()}; border: 1px solid #888;")
            btn.setToolTip(name)
            btn.clicked.connect(lambda checked, c=qcolor: self._set_annotation_color(QColor(c)))
            annotation_toolbar_layout.addWidget(btn)

        
        # Separator
        sep_label2 = QLabel("|")
        sep_label2.setStyleSheet("color: #aaa;")
        annotation_toolbar_layout.addWidget(sep_label2)
        
        # Pen width label and selector
        width_label = QLabel("Width:")
        annotation_toolbar_layout.addWidget(width_label)
        
        self.annot_width_combo = QComboBox()
        self.annot_width_combo.addItems(["1", "2", "3", "5", "8", "12"])
        self.annot_width_combo.setCurrentText("2")
        self.annot_width_combo.setFixedWidth(50)
        self.annot_width_combo.setFixedHeight(BUTTON_HEIGHT)
        self.annot_width_combo.setToolTip("Pen/border width")
        self.annot_width_combo.currentTextChanged.connect(self._set_annotation_pen_width)
        annotation_toolbar_layout.addWidget(self.annot_width_combo)
        
        #annotation_toolbar_layout.addSpacing(10)
        
        # Separator
        sep_label3 = QLabel("|")
        sep_label3.setStyleSheet("color: #aaa;")
        annotation_toolbar_layout.addWidget(sep_label3)
        
        # Delete selected annotation button
        self.delete_annot_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(self.delete_annot_btn, "eraser")
        self.delete_annot_btn.setToolTip("Delete selected annotation (Del)")
        self.delete_annot_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        self.delete_annot_btn.clicked.connect(self._delete_selected_annotation)
        self.delete_annot_btn.setEnabled(False)
        annotation_toolbar_layout.addWidget(self.delete_annot_btn)
        
        # Clear page annotations button
        clear_annot_btn = QPushButton()
        self.clear_annot_btn = clear_annot_btn
        self.main_window.icons_manager.apply_icon_to_button(self.clear_annot_btn, "clear_page")
        clear_annot_btn.setToolTip("Clear all annotations on current page")
        clear_annot_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        clear_annot_btn.clicked.connect(self._clear_page_annotations)
        annotation_toolbar_layout.addWidget(clear_annot_btn)
        
        #annotation_toolbar_layout.addSpacing(10)
        
        # Save in-place button
        save_inplace_btn = QPushButton()
        self.main_window.icons_manager.apply_icon_to_button(save_inplace_btn, "save")
        save_inplace_btn.setToolTip("Save annotations to current file")
        save_inplace_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        save_inplace_btn.clicked.connect(self._save_annotations)
        annotation_toolbar_layout.addWidget(save_inplace_btn)

        # Save-as button
        save_as_btn = QPushButton() # "📥"
        self.main_window.icons_manager.apply_icon_to_button(save_as_btn, "save_as")
        save_as_btn.setToolTip("Save annotated PDF to a new file")
        save_as_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        save_as_btn.clicked.connect(self._save_annotations_as)
        annotation_toolbar_layout.addWidget(save_as_btn)        
        annotation_toolbar_layout.addStretch()
               
        # Close annotation toolbar button
        close_annot_btn = QPushButton("✕")
        close_annot_btn.setToolTip("Close annotation toolbar (Esc)")
        close_annot_btn.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        close_annot_btn.setStyleSheet("font-weight: bold; color: #555;")
        close_annot_btn.clicked.connect(self._hide_annotation_toolbar)
        annotation_toolbar_layout.addWidget(close_annot_btn)
        
        # Style the annotation toolbar
        # self._apply_annotation_toolbar_theme()
        self.annotation_toolbar_widget.setFixedHeight(BUTTON_HEIGHT + 8)
        self.annotation_toolbar_widget.setVisible(False)
        
        # Add annotation toolbar to main layout (right after the main toolbar)
        layout.addWidget(self.annotation_toolbar_widget)        
    
        # SCROLL AREA - This is the key component that needs to expand
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Make scroll area expand to fill available space
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setMinimumSize(300, 400)  # Reasonable minimum size
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll_changed)
        
        # ✅ NEW: Prevent scrollbars from stealing focus
        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.verticalScrollBar().setFocusPolicy(Qt.NoFocus)
        self.scroll_area.horizontalScrollBar().setFocusPolicy(Qt.NoFocus)

        # Content widget setup
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setSpacing(self.page_spacing)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_widget.setFocusPolicy(Qt.StrongFocus)
        
        # No PDF loaded label
        self.no_pdf_label = QLabel("No PDF loaded")
        self.no_pdf_label = QLabel("")
        self.no_pdf_label.setAlignment(Qt.AlignCenter)
        #self.no_pdf_label.setStyleSheet("color: #666; font-size: 14px; padding: 0px;")
        self.no_pdf_label.setObjectName("Toolbar")
        self.content_layout.addWidget(self.no_pdf_label)

        self.scroll_area.setWidget(self.content_widget)
        # Add scroll area with stretch factor to make it expand
        layout.addWidget(self.scroll_area, 1)  # Stretch factor of 1

        # Custom wheel event for zooming
        self.scroll_area.wheelEvent = self.wheel_event

        # Set cursor for reverse search mode
        self.reverse_search_mode = False

        # Final size policy enforcement
        self.updateGeometry()
        
        # Make the widget focusable for keyboard shortcuts
        self.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        
        # ✅ NEW: Install event filter on scroll area to maintain focus
        self.scroll_area.installEventFilter(self)
        
        # ✅ NEW: Setup application-level shortcuts
        #self.setup_application_shortcuts()
       
        
        # Set initial zoom spinbox value and connect signal AFTER zoom_factor is set
        self.zoom_spinbox.setValue(int(self.zoom_factor * 100))
        self.zoom_spinbox.valueChanged.connect(self.set_zoom_from_spinbox)


        self.toolbar_widget.setObjectName("Toolbar")
        self.annotation_toolbar_widget.setObjectName("Toolbar")
        self.main_toolbar_widget.setObjectName("Toolbar")
        self.search_container.setObjectName("Toolbar")

    def _apply_annotation_toolbar_theme(self):
        """Apply current theme to annotation toolbar — call at init and on theme change."""
        from style_manager import get_annotation_style
        a = get_annotation_style()
        self.annotation_toolbar_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {a['toolbar_bg']};
                border-bottom: 1px solid {a['toolbar_border']};
            }}
            QPushButton {{
                border: 1px solid {a['btn_border']};
                border-radius: 3px;
                padding: 2px;
                color: {a['label_color']};
            }}
            QPushButton:checked {{
                background-color: {a['btn_checked']};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {a['btn_hover']};
            }}
            QPushButton:checked:hover {{
                background-color: {a['btn_checked_hover']};
            }}
            QLabel {{
                color: {a['sep_color']};
                background-color: transparent;
            }}
            QComboBox {{
                border: 1px solid {a['btn_border']};
                background-color: {a['toolbar_bg']};
                color: {a['label_color']};
            }}
        """)



    def apply_global_toolbar_theme(self):
        from style_manager import get_annotation_style
        a = get_annotation_style()

        style = f"""
        /* All toolbars */
        QWidget#Toolbar {{
            background-color: {a['toolbar_bg']};
            border-bottom: 1px solid {a['toolbar_border']};
        }}

        /* Buttons */
        QWidget#Toolbar QPushButton {{
            border: 1px solid {a['btn_border']};
            border-radius: 3px;
            padding: 2px;
            color: {a['label_color']};
            background: transparent;
        }}

        QWidget#Toolbar QPushButton:hover {{
            background-color: {a['btn_hover']};
        }}

        QWidget#Toolbar QPushButton:checked {{
            background-color: {a['btn_checked']};
            color: white;
        }}

        QWidget#Toolbar QPushButton:checked:hover {{
            background-color: {a['btn_checked_hover']};
        }}

        /* Labels */
        QWidget#Toolbar QLabel {{
            color: {a['label_color']};
            background: transparent;
        }}

        /* SpinBox & Combo */
        QWidget#Toolbar QSpinBox,
        QWidget#Toolbar QComboBox {{
            border: 1px solid {a['btn_border']};
            background-color: {a['toolbar_bg']};
            color: {a['label_color']};
        }}
        """

        self.setStyleSheet(style)


    def _scroll_to_page_label(self, page_index):
        """Scroll so that the given page label is visible at the top"""
        if page_index < 0 or page_index >= len(self.page_labels):
            return
        page_label = self.page_labels[page_index]
        try:
            page_pos = page_label.mapTo(self.content_widget, QPoint(0, 0))
            self.scroll_area.verticalScrollBar().setValue(page_pos.y())
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION TOOLBAR METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _toggle_annotation_toolbar(self):
        """Toggle the annotation toolbar visibility"""
        is_visible = self.annotation_toolbar_widget.isVisible()
        self.annotation_toolbar_widget.setVisible(not is_visible)
        self.annotations_btn.setChecked(not is_visible)
        
        if not is_visible:
            # Show toolbar
            self.annotations_btn.setStyleSheet("background-color: #4CAF50;")
            self.main_window.update_status_bar("Select a tool to start annotating")
            #self._update_annot_status("Select a tool to start annotating")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Annotation mode active", 2000)
        else:
            # Hide toolbar
            self.annotations_btn.setStyleSheet("")
            self._clear_annotation_tool()
            self._clear_annotation_selection()
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Annotation mode closed", 2000)

    def _exec_dialog_safe(self, dialog):
        """Execute a modal dialog safely, preventing focus/grab interference.
        
        Fixes the issue where dialog buttons (Ok/Cancel) require multiple clicks
        when called from annotation mode.
        """
        # Release any explicit mouse grab that might be active
        app = QApplication.instance()

        grabber = None
        if hasattr(app, "mouseGrabber"):
            grabber = app.mouseGrabber()

        #grabber = QApplication.instance().mouseGrabWidget()
        if grabber:
            grabber.releaseMouse()

        # Temporarily disable mouse tracking on all page labels
        # to prevent mouseMoveEvent from firing and interfering
        tracked = []
        for label in self.page_labels:
            if label.hasMouseTracking():
                label.setMouseTracking(False)
                tracked.append(label)

        # Temporarily remove the event filter on the scroll area
        filter_removed = False
        try:
            self.scroll_area.removeEventFilter(self)
            filter_removed = True
        except Exception:
            pass

        # Flush all pending events so nothing queued interferes with the dialog
        QApplication.processEvents()

        # Ensure the dialog is application-modal
        dialog.setWindowModality(Qt.ApplicationModal)

        try:
            result = dialog.exec_()
        finally:
            # Restore mouse tracking
            for label in tracked:
                try:
                    label.setMouseTracking(True)
                except RuntimeError:
                    pass  # label may have been destroyed by render_all_pages

            # Reinstall the event filter
            if filter_removed:
                try:
                    self.scroll_area.installEventFilter(self)
                except Exception:
                    pass

            QApplication.processEvents()

        return result

    def _add_text_annotation(self, page_label, pos):
        """Add a text note (sticky note) annotation with multi-line support"""
        pdf_point = self._screen_to_pdf_point(page_label, pos)
        if not pdf_point:
            return

        page_num = page_label.page_number  # capture before dialog

        dialog = MultiLineTextDialog(
            self.window(),        # <-- parent to top-level window
            title="Add Sticky Note",
            initial_text="",
            placeholder="Enter your note here...\n(You can use multiple lines)"
        )
        if self._exec_dialog_safe(dialog) == QDialog.Accepted:
            text = dialog.get_text().strip()
            if text:
                try:
                    page = self.pdf_document[page_num]
                    annot = page.add_text_annot(pdf_point, text)
                    annot.set_colors(stroke=self.annotation_color.getRgbF()[:3])
                    annot.update()
                    self._save_and_refresh_annotations()
                    self.main_window.update_status_bar("Sticky note added")
                    #self._update_annot_status("Sticky note added")
                except Exception as e:
                    QMessageBox.critical(self.window(), "Error",
                                         f"Failed to add sticky note: {str(e)}")
                
    
    # def _show_annotation_toolbar(self):
        # """Show the annotation toolbar"""
        # self.annotation_toolbar_widget.setVisible(True)
        # self.annotations_btn.setChecked(True)
        # self.annotations_btn.setStyleSheet("background-color: #4CAF50;")
        # self.main_window.update_status_bar("Select a tool to start annotating")
        # #self._update_annot_status("Select a tool to start annotating")
    
        
    # def _hide_annotation_toolbar(self):
        # """Hide the annotation toolbar"""
        # if self.annotations_modified:
            # msgbox = QMessageBox(self.window())
            # msgbox.setWindowTitle("Unsaved Annotations")
            # msgbox.setText("You have unsaved annotations. Do you want to save before closing?")
            # msgbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            # msgbox.setDefaultButton(QMessageBox.Save)

            # result = self._exec_dialog_safe(msgbox)
            # if result == QMessageBox.Save:
                # self._save_annotations_as()
            # elif result == QMessageBox.Cancel:
                # return

        # self.annotation_toolbar_widget.setVisible(False)
        # self.annotations_btn.setChecked(False)
        # self.annotations_btn.setStyleSheet("")
        # self._clear_annotation_tool()
        # self._clear_annotation_selection() 

    def _hide_annotation_toolbar(self):
        """Hide the annotation toolbar"""
        if self.annotations_modified:
            msgbox = QMessageBox(self.window())
            msgbox.setWindowTitle("Unsaved Annotations")
            msgbox.setText("You have unsaved annotations. Do you want to save before closing?")
            # Create custom buttons for Save, Save As, Discard, and Cancel
            save_btn = msgbox.addButton("Save", QMessageBox.AcceptRole)
            save_as_btn = msgbox.addButton("Save As", QMessageBox.AcceptRole)
            discard_btn = msgbox.addButton("Discard", QMessageBox.DestructiveRole)
            cancel_btn = msgbox.addButton("Cancel", QMessageBox.RejectRole)
            msgbox.setDefaultButton(save_btn)
            result = self._exec_dialog_safe(msgbox)
            if msgbox.clickedButton() == save_btn:
                self._save_annotations()
            elif msgbox.clickedButton() == save_as_btn:
                self._save_annotations_as()
            elif msgbox.clickedButton() == discard_btn:
                self.main_window.pdf_manager.refresh_pdf()                
            elif msgbox.clickedButton() == cancel_btn:
                return
        self.annotation_toolbar_widget.setVisible(False)
        self.annotations_btn.setChecked(False)
        self.annotations_btn.setStyleSheet("")
        self._clear_annotation_tool()
        self._clear_annotation_selection() 
                
    
    def _clear_annotation_tool(self):
        """Clear current annotation tool selection"""
        self.annotation_tool = None
        for btn in self.annotation_tool_actions.values():
            btn.setChecked(False)
        
        # Restore normal cursor on all page labels
        for label in self.page_labels:
            if self.select_mode:
                label.setCursor(Qt.IBeamCursor)
            elif self.pan_mode:
                label.setCursor(Qt.OpenHandCursor)
            else:
                label.setCursor(Qt.ArrowCursor)
        
        #self._update_annot_status("")
        self.main_window.update_status_bar("")
    
    def _clear_annotation_selection(self):
        """Clear the currently selected annotation"""
        self.selected_annot_rect = None
        self.selected_annot_type = None
        self.selected_annot_page = -1
        self.dragging_annot = False
        self.drag_start = None
        self.last_drag_pos = None
        self.delete_annot_btn.setEnabled(False)
    
    def _set_annotation_tool(self, tool):
        """Set the current annotation tool"""
        # Clear previous selection when changing tools
        if tool != "select":
            self._clear_annotation_selection()
        
        self.annotation_tool = tool
        
        # Update button states
        for t, btn in self.annotation_tool_actions.items():
            btn.setChecked(t == tool)
        
        # Set appropriate cursor
        cursor_map = {
            "select": Qt.ArrowCursor,
            "text": Qt.CrossCursor,
            "freetext": Qt.CrossCursor,
            "highlight": Qt.CrossCursor,
            "rect": Qt.CrossCursor,
            "circle": Qt.CrossCursor,
            "line": Qt.CrossCursor,
            "ink": Qt.CrossCursor,
        }
        cursor = cursor_map.get(tool, Qt.ArrowCursor)
        
        for label in self.page_labels:
            label.setCursor(cursor)
        
        # Update status
        status_map = {
            "select": "Click to select, drag to move, right-click for options",
            "text": "Click to add a sticky note",
            "freetext": "Click to add a text box",
            "highlight": "Drag to highlight an area",
            "rect": "Drag to draw a rectangle",
            "circle": "Drag to draw a circle/ellipse",
            "line": "Drag to draw a line",
            "ink": "Drag to draw freehand",
        }
        self.main_window.update_status_bar(status_map.get(tool, ""))
        #self._update_annot_status(status_map.get(tool, ""))
        
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(f"Annotation tool: {tool}", 2000)
    
    #def _update_annot_status(self, message):
    #    """Update the annotation status label"""
    #    self.main_window.update_status_bar(message)
        #if hasattr(self, 'annot_status_label'):
        #    self.annot_status_label.setText(message)
    
    def _choose_annotation_color(self):
        """Open color dialog for annotation color"""
        dlg = QColorDialog(self.annotation_color, self.window())
        dlg.setOption(QColorDialog.DontUseNativeDialog, True)
        if self._exec_dialog_safe(dlg) == QDialog.Accepted:
            self._set_annotation_color(dlg.currentColor())
            
    
    def _set_annotation_color(self, color):
        """Set the annotation color"""
        self.annotation_color = color
        # Update button to show current color
        self.annot_color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(f"Annotation color: {color.name()}", 2000)
    
    def _set_annotation_pen_width(self, width_str):
        """Set annotation pen width"""
        try:
            self.annotation_pen_width = int(width_str)
        except ValueError:
            self.annotation_pen_width = 2
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION COORDINATE CONVERSION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _screen_to_pdf_point(self, page_label, screen_point):
        """Convert screen coordinates to PDF coordinates"""
        if not self.pdf_document:
            return None
        
        page_num = page_label.page_number
        if page_num >= self.total_pages:
            return None
        
        page = self.pdf_document[page_num]
        pixmap = page_label.pixmap()
        
        if not pixmap:
            return None
        
        x = screen_point.x()
        y = screen_point.y()
        
        # Check bounds
        if x < 0 or y < 0 or x >= pixmap.width() or y >= pixmap.height():
            return None
        
        # Convert to PDF coordinates
        scale_x = page.rect.width / pixmap.width()
        scale_y = page.rect.height / pixmap.height()
        
        return fitz.Point(x * scale_x, y * scale_y)
    
    def _pdf_to_screen_rect(self, page_label, pdf_rect):
        """Convert PDF rectangle to screen coordinates"""
        if not self.pdf_document:
            return None
        
        page_num = page_label.page_number
        if page_num >= self.total_pages:
            return None
        
        page = self.pdf_document[page_num]
        pixmap = page_label.pixmap()
        
        if not pixmap:
            return None
        
        scale_x = pixmap.width() / page.rect.width
        scale_y = pixmap.height() / page.rect.height
        
        return QRect(
            int(pdf_rect[0] * scale_x),
            int(pdf_rect[1] * scale_y),
            int((pdf_rect[2] - pdf_rect[0]) * scale_x),
            int((pdf_rect[3] - pdf_rect[1]) * scale_y)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION FINDING METHODS
    # ═══════════════════════════════════════════════════════════════════════════════

    def _find_annot_at_point(self, page_num, pdf_point):
        """Find annotation at given PDF point"""
        if not self.pdf_document or page_num >= self.total_pages:
            return None
        page = self.pdf_document[page_num]
        found_annots = []
        annots = page.annots()
        if annots:
            for annot in annots:
                try:
                    rect       = annot.rect
                    rect_tuple = (rect.x0, rect.y0, rect.x1, rect.y1)
                    annot_type = annot.type[1]
                    # Ink bounding boxes can be very tight — use larger hit tolerance
                    HIT = 8 if annot_type == "Ink" else 2
                    hit_rect = fitz.Rect(rect.x0 - HIT, rect.y0 - HIT,
                                         rect.x1 + HIT, rect.y1 + HIT)
                    if hit_rect.contains(pdf_point):
                        found_annots.append({'rect': rect_tuple, 'type': annot_type})
                except:
                    continue
        return found_annots[-1] if found_annots else None
    
    def _get_page_and_annot(self, page_num, rect_tuple):
        """Find annotation and return (page, annot) tuple.
        
        CRITICAL: The caller MUST keep the returned 'page' reference alive 
        in a local variable as long as it operates on 'annot'. If 'page' is 
        garbage-collected, 'annot' becomes unbound and all operations fail 
        with 'annotation not bound to any page'.
        """
        if not self.pdf_document or page_num >= self.total_pages or not rect_tuple:
            return None, None

        page = self.pdf_document[page_num]
        x0, y0, x1, y1 = rect_tuple

        for annot in page.annots():
            try:
                r = annot.rect
                if (abs(r.x0 - x0) < 2 and abs(r.y0 - y0) < 2 and
                    abs(r.x1 - x1) < 2 and abs(r.y1 - y1) < 2):
                    return page, annot
            except:
                continue

        return page, None    
    
    def _find_annot_by_rect(self, page_num, rect_tuple):
        """Find annotation by its rectangle (used after page refresh)"""
        if not self.pdf_document or page_num >= self.total_pages or not rect_tuple:
            return None
        
        page = self.pdf_document[page_num]
        x0, y0, x1, y1 = rect_tuple
        
        # Find annotation with matching rectangle (with small tolerance)
        annots = page.annots()
        if annots:
            for annot in annots:
                try:
                    r = annot.rect
                    if (abs(r.x0 - x0) < 2 and abs(r.y0 - y0) < 2 and 
                        abs(r.x1 - x1) < 2 and abs(r.y1 - y1) < 2):
                        return annot
                except:
                    continue
        return None
    
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION CREATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
        
    def _edit_text_annotation(self, page_num, annot_rect):
        """Edit an existing text annotation (sticky note)"""
        try:
            if isinstance(annot_rect, dict):
                annot_rect = annot_rect.get('rect')
            if not annot_rect:
                return

            page, annot = self._get_page_and_annot(page_num, annot_rect)
            if not annot:
                self.main_window.update_status_bar("Could not find annotation to edit")
                #self._update_annot_status("Could not find annotation to edit")
                return
            if annot.type[1] != "Text":
                self.main_window.update_status_bar("Only text annotations can be edited this way")
                #self._update_annot_status("Only text annotations can be edited this way")
                return

            try:
                current_text = annot.info.get("content", "")
            except Exception:
                current_text = ""
            old_rect = fitz.Rect(annot.rect)
            colors = dict(annot.colors) if annot.colors else {}
            stroke_color = colors.get("stroke", (0, 0, 1))

            dialog = MultiLineTextDialog(
                self.window(),
                title="Edit Sticky Note",
                initial_text=current_text,
                placeholder="Enter your note here..."
            )
            if self._exec_dialog_safe(dialog) == QDialog.Accepted:
                new_text = dialog.get_text().strip()
                if new_text:
                    try:
                        page2, annot2 = self._get_page_and_annot(page_num, annot_rect)
                        if not annot2:
                            self.main_window.update_status_bar("Annotation disappeared")
                            #self._update_annot_status("Annotation disappeared")
                            return
                        page2.delete_annot(annot2)
                        new_point = fitz.Point(old_rect.x0, old_rect.y0)
                        new_annot = page2.add_text_annot(new_point, new_text)
                        new_annot.set_colors(stroke=stroke_color)
                        new_annot.update()
                        r = new_annot.rect
                        self.selected_annot_rect = (r.x0, r.y0, r.x1, r.y1)
                        self.selected_annot_page = page_num
                        self._save_and_refresh_annotations()
                        self.main_window.update_status_bar("Sticky note updated")
                        #self._update_annot_status("Sticky note updated")
                    except Exception as e:
                        QMessageBox.critical(self.window(), "Error",
                                             f"Failed to update sticky note: {str(e)}")
        except Exception as e:
            print(f"Error editing text annotation: {e}")
            import traceback
            traceback.print_exc()
            
        
 
    def _edit_freetext_annotation(self, page_num, annot_rect):
        """Edit an existing FreeText annotation (text box)"""
        try:
            if isinstance(annot_rect, dict):
                annot_rect = annot_rect.get('rect')
            if not annot_rect:
                return

            page, annot = self._get_page_and_annot(page_num, annot_rect)
            if not annot:
                self.main_window.update_status_bar("Could not find text box to edit")
                #self._update_annot_status("Could not find text box to edit")
                return
            if annot.type[1] != "FreeText":
                self.main_window.update_status_bar("Only text box annotations can be edited this way")
                #self._update_annot_status("Only text box annotations can be edited this way")
                return

            try:
                current_text = annot.info.get("content", "") or ""
            except Exception:
                current_text = ""
            old_rect = fitz.Rect(annot.rect)
            colors = dict(annot.colors) if annot.colors else {}
            text_color = colors.get("stroke", self.annotation_color.getRgbF()[:3])

            dialog = MultiLineTextDialog(
                self.window(),
                title="Edit Text Box",
                initial_text=current_text,
                placeholder="Enter text here..."
            )
            if self._exec_dialog_safe(dialog) == QDialog.Accepted:
                new_text = dialog.get_text().strip()
                if new_text:
                    try:
                        page2, annot2 = self._get_page_and_annot(page_num, annot_rect)
                        if not annot2:
                            self.main_window.update_status_bar("Annotation disappeared")
                            #self._update_annot_status("Annotation disappeared")
                            return
                        page2.delete_annot(annot2)
                        new_annot = page2.add_freetext_annot(
                            old_rect, new_text,
                            fontsize=12,
                            text_color=text_color
                        )
                        new_annot.update()
                        r = new_annot.rect
                        self.selected_annot_rect = (r.x0, r.y0, r.x1, r.y1)
                        self.selected_annot_page = page_num
                        self._save_and_refresh_annotations()
                        self.main_window.update_status_bar("Text box updated")
                        #self._update_annot_status("Text box updated")
                    except Exception as e:
                        QMessageBox.critical(self.window(), "Error",
                                             f"Failed to update text box: {str(e)}")
        except Exception as e:
            print(f"Error editing freetext annotation: {e}")
            import traceback
            traceback.print_exc()
        
        
    
    def _add_freetext_annotation(self, page_label, pos):
        """Add a freetext annotation (text box)"""
        pdf_point = self._screen_to_pdf_point(page_label, pos)
        if not pdf_point:
            return

        page_num = page_label.page_number

        dialog = MultiLineTextDialog(
            self.window(),
            title="Add Text Box",
            initial_text="",
            placeholder="Enter text here..."
        )
        if self._exec_dialog_safe(dialog) == QDialog.Accepted:
            text = dialog.get_text().strip()
            if text:
                try:
                    page = self.pdf_document[page_num]
                    rect = fitz.Rect(
                        pdf_point.x, pdf_point.y,
                        pdf_point.x + 200,
                        pdf_point.y + 50
                    )
                    annot = page.add_freetext_annot(
                        rect, text,
                        fontsize=12,
                        text_color=self.annotation_color.getRgbF()[:3]
                    )
                    annot.update()
                    self._save_and_refresh_annotations()
                    self.main_window.update_status_bar("Text box added")
                    #self._update_annot_status("Text box added")
                except Exception as e:
                    QMessageBox.critical(self.window(), "Error",
                                         f"Failed to add free text: {str(e)}")

    def _commit_ink_annotation(self, page_label):
        """Commit ink annotation from drawn points"""
        if not self.annotation_ink_points or len(self.annotation_ink_points) < 2:
            self.annotation_ink_points = []
            return
        try:
            page = self.pdf_document[page_label.page_number]
            pdf_points = []
            for pt in self.annotation_ink_points:
                pdf_pt = self._screen_to_pdf_point(page_label, pt)
                if pdf_pt:
                    pdf_points.append((pdf_pt.x, pdf_pt.y))

            if len(pdf_points) < 2:
                return

            # Deduplicate consecutive identical points
            deduped = [pdf_points[0]]
            for p in pdf_points[1:]:
                if abs(p[0] - deduped[-1][0]) > 0.1 or abs(p[1] - deduped[-1][1]) > 0.1:
                    deduped.append(p)

            if len(deduped) < 2:
                return

            # PyMuPDF expects a list-of-strokes: [[pt1, pt2, ...]]
            annot = page.add_ink_annot([deduped])
            annot.set_colors(stroke=self.annotation_color.getRgbF()[:3])
            annot.set_border(width=max(1.0, self.annotation_pen_width / 2.0))
            annot.update()

            # Force-flush to the document stream so re-render doesn't lose it
            #self.pdf_document.saveIncr()

            #self.annotations_modified = True            
            #self.render_all_pages()
            
            self._save_and_refresh_annotations()
            self.main_window.update_status_bar("Ink annotation added")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add ink annotation: {str(e)}")
        finally:
            self.annotation_ink_points = []
    
    def _commit_shape_annotation(self, page_label, end_pos):
        """Commit shape annotation (rect, circle, line, highlight)"""
        if not self.annotation_start_pos:
            return
        
        start_pdf = self._screen_to_pdf_point(page_label, self.annotation_start_pos)
        end_pdf = self._screen_to_pdf_point(page_label, end_pos)
        
        if not start_pdf or not end_pdf:
            return
        
        try:
            page = self.pdf_document[page_label.page_number]
            rect = fitz.Rect(
                min(start_pdf.x, end_pdf.x),
                min(start_pdf.y, end_pdf.y),
                max(start_pdf.x, end_pdf.x),
                max(start_pdf.y, end_pdf.y)
            )
            
            # Ensure minimum size
            if rect.width < 5 or rect.height < 5:
                self.main_window.update_status_bar("Shape too small - drag more")
                #self._update_annot_status("Shape too small - drag more")
                return
            
            color = self.annotation_color.getRgbF()[:3]
            annot = None
            
            if self.annotation_tool == "highlight":
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=color)
                annot.set_opacity(0.5)
            elif self.annotation_tool == "rect":
                annot = page.add_rect_annot(rect)
                annot.set_border(width=self.annotation_pen_width / 2.0)
                annot.set_colors(stroke=color)
            elif self.annotation_tool == "circle":
                annot = page.add_circle_annot(rect)
                annot.set_border(width=self.annotation_pen_width / 2.0)
                annot.set_colors(stroke=color)
            elif self.annotation_tool == "line":
                annot = page.add_line_annot(start_pdf, end_pdf)
                annot.set_border(width=self.annotation_pen_width / 2.0)
                annot.set_colors(stroke=color)
            
            if annot:
                annot.update()
                self._save_and_refresh_annotations()
                self.main_window.update_status_bar(f"{self.annotation_tool.capitalize()} added")
                #self._update_annot_status(f"{self.annotation_tool.capitalize()} added")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add shape: {str(e)}")
        finally:
            self.annotation_start_pos = None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION SELECTION AND MOVEMENT
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _select_annotation(self, page_num, annot_info):
        """Select an annotation - annot_info is dict with 'rect' and 'type', or a tuple"""
        if isinstance(annot_info, dict):
            self.selected_annot_rect = annot_info['rect']
            self.selected_annot_type = annot_info.get('type', None)
        else:
            self.selected_annot_rect = annot_info
            self.selected_annot_type = None
        self.selected_annot_page = page_num
        self.delete_annot_btn.setEnabled(True)
        type_label = self.selected_annot_type or 'Annotation'
        # self._update_annot_status(
            # f"Selected {type_label} — drag to move, right-click for options, double-click to edit"
        # )
        self.main_window.update_status_bar(
            f"Selected {type_label} — drag to move, right-click for options, double-click to edit"
        )
    

    def _move_annotation(self, page_num, dx, dy):
        """Move annotation by dx, dy in PDF coordinates"""
        if not self.selected_annot_rect or not self.pdf_document:
            return False
        try:
            page = self.pdf_document[page_num]
            x0, y0, x1, y1 = self.selected_annot_rect

            annot = None
            for a in list(page.annots()):
                try:
                    r = a.rect
                    if (abs(r.x0 - x0) < 2 and abs(r.y0 - y0) < 2 and
                            abs(r.x1 - x1) < 2 and abs(r.y1 - y1) < 2):
                        annot = a
                        break
                except:
                    continue

            if not annot:
                self.main_window.update_status_bar("Could not find annotation to move")
                return False

            # ── Extract ALL properties BEFORE delete ──────────────────────
            annot_type   = annot.type[1]
            old_rect     = fitz.Rect(annot.rect)
            colors       = dict(annot.colors) if annot.colors else {}
            border       = dict(annot.border) if annot.border else {}
            stroke_color = colors.get("stroke") or (0, 0, 1)
            width        = border.get("width", 1) if border else 1
            opacity      = 0.5
            text_content     = ""
            freetext_content = ""
            freetext_color   = (0, 0, 0)
            vertices         = None

            if annot_type == "Text":
                try:
                    text_content = annot.info.get("content", "")
                except:
                    text_content = ""

            # elif annot_type == "FreeText":
                # try:
                    # freetext_content = annot.info.get("content", "")
                # except:
                    # freetext_content = ""
                # # PyMuPDF stores FreeText text color in colors["fill"]
                # # Fall back to stroke, then annotation_color, never pure black by accident
                # raw_fill = colors.get("fill")
                # if raw_fill and any(c > 0 for c in raw_fill):
                    # freetext_color = raw_fill
                # elif any(c > 0 for c in stroke_color):
                    # freetext_color = stroke_color
                # else:
                    # # Last resort: use the current annotation color from the toolbar
                    # freetext_color = self.annotation_color.getRgbF()[:3]



            elif annot_type == "FreeText":
                try:
                    freetext_content = annot.info.get("content", "") or ""
                except:
                    freetext_content = ""
                
                # For FreeText, we need to preserve the text color
                # Check colors dictionary for text color (stored as "fill" in PyMuPDF)
                raw_fill = colors.get("fill")
                if raw_fill and any(c > 0 for c in raw_fill):
                    freetext_color = raw_fill
                else:
                    # Fallback to stroke color or current annotation color
                    raw_stroke = colors.get("stroke")
                    if raw_stroke and any(c > 0 for c in raw_stroke):
                        freetext_color = raw_stroke
                    else:
                        # Last resort: use the current annotation color from the toolbar
                        freetext_color = self.annotation_color.getRgbF()[:3]




                    
            elif annot_type == "Highlight":
                try:
                    opacity = annot.opacity if hasattr(annot, "opacity") else 0.5
                except:
                    opacity = 0.5
                try:
                    raw = annot.vertices
                    vertices = list(raw) if raw else None
                except:
                    vertices = None

            elif annot_type == "Line":
                try:
                    raw = annot.vertices
                    vertices = list(raw) if raw else None
                except:
                    vertices = None

            elif annot_type == "Ink":
                # annot.vertices for Ink = list-of-strokes: [[pt, pt, ...], [pt, ...]]
                # Each element is itself a list/sequence of points.
                try:
                    raw = annot.vertices
                    if raw:
                        # Normalise every point to a plain (x, y) tuple
                        strokes = []
                        for stroke in raw:
                            pts = []
                            for p in stroke:
                                if isinstance(p, (tuple, list)) and len(p) >= 2:
                                    pts.append((float(p[0]), float(p[1])))
                                elif hasattr(p, "x"):
                                    pts.append((float(p.x), float(p.y)))
                            if pts:
                                strokes.append(pts)
                        vertices = strokes if strokes else None
                    else:
                        vertices = None
                except Exception as e:
                    print(f"Ink vertices read error: {e}")
                    vertices = None

            # ── Delete original ────────────────────────────────────────────
            page.delete_annot(annot)
            moved = False
            new_rect_tuple = None

            # ── Recreate at new position ───────────────────────────────────
            if annot_type == "Text":
                new_pt = fitz.Point(old_rect.x0 + dx, old_rect.y0 + dy)
                na = page.add_text_annot(new_pt, text_content)
                na.set_colors(stroke=stroke_color)
                na.update()
                r = na.rect
                new_rect_tuple = (r.x0, r.y0, r.x1, r.y1)
                moved = True

            elif annot_type == "FreeText":
                new_rect = fitz.Rect(old_rect.x0+dx, old_rect.y0+dy,
                                     old_rect.x1+dx, old_rect.y1+dy)
                na = page.add_freetext_annot(
                    new_rect, freetext_content,
                    fontsize=12,
                    text_color=freetext_color   # ← preserved color
                )
                na.update()
                new_rect_tuple = (new_rect.x0, new_rect.y0, new_rect.x1, new_rect.y1)
                moved = True

            elif annot_type == "Highlight":
                if vertices:
                    new_verts = [(p[0]+dx, p[1]+dy) if isinstance(p, (tuple,list))
                                 else (p.x+dx, p.y+dy) for p in vertices]
                    xs = [v[0] for v in new_verts]
                    ys = [v[1] for v in new_verts]
                    new_rect = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                else:
                    new_rect = fitz.Rect(old_rect.x0+dx, old_rect.y0+dy,
                                         old_rect.x1+dx, old_rect.y1+dy)
                na = page.add_highlight_annot(new_rect)
                na.set_colors(stroke=stroke_color)
                na.set_opacity(opacity)
                na.update()
                new_rect_tuple = (new_rect.x0, new_rect.y0, new_rect.x1, new_rect.y1)
                moved = True

            elif annot_type == "Line":
                if vertices and len(vertices) >= 2:
                    s, e = vertices[0], vertices[1]
                    if isinstance(s, (tuple, list)):
                        new_s = fitz.Point(s[0]+dx, s[1]+dy)
                        new_e = fitz.Point(e[0]+dx, e[1]+dy)
                    else:
                        new_s = fitz.Point(s.x+dx, s.y+dy)
                        new_e = fitz.Point(e.x+dx, e.y+dy)
                    na = page.add_line_annot(new_s, new_e)
                    na.set_colors(stroke=stroke_color)
                    na.set_border(width=width)
                    na.update()
                    r = na.rect
                    new_rect_tuple = (r.x0, r.y0, r.x1, r.y1)
                    moved = True

            elif annot_type == "Ink":
                if vertices:
                    # Translate every stroke by (dx, dy)
                    new_strokes = [
                        [(p[0]+dx, p[1]+dy) for p in stroke]
                        for stroke in vertices
                    ]
                    na = page.add_ink_annot(new_strokes)
                    na.set_colors(stroke=stroke_color)
                    na.set_border(width=width)
                    na.update()
                    r = na.rect
                    new_rect_tuple = (r.x0, r.y0, r.x1, r.y1)
                    moved = True
                else:
                    self.main_window.update_status_bar("Ink: no vertex data found")

            elif annot_type in ("Square", "Rect"):
                new_rect = fitz.Rect(old_rect.x0+dx, old_rect.y0+dy,
                                     old_rect.x1+dx, old_rect.y1+dy)
                na = page.add_rect_annot(new_rect)
                na.set_colors(stroke=stroke_color)
                na.set_border(width=width)
                na.update()
                new_rect_tuple = (new_rect.x0, new_rect.y0, new_rect.x1, new_rect.y1)
                moved = True

            elif annot_type == "Circle":
                new_rect = fitz.Rect(old_rect.x0+dx, old_rect.y0+dy,
                                     old_rect.x1+dx, old_rect.y1+dy)
                na = page.add_circle_annot(new_rect)
                na.set_colors(stroke=stroke_color)
                na.set_border(width=width)
                na.update()
                new_rect_tuple = (new_rect.x0, new_rect.y0, new_rect.x1, new_rect.y1)
                moved = True

            if moved and new_rect_tuple:
                self.selected_annot_rect = new_rect_tuple
                self._save_and_refresh_annotations()
                self.main_window.update_status_bar(
                    f"{annot_type} moved (dx={dx:.1f}, dy={dy:.1f})")
                return True
            else:
                self.main_window.update_status_bar(f"Could not move {annot_type}")
                return False

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.main_window.update_status_bar(f"Move error: {str(e)}")
            return False
            
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION DELETE AND CLEAR
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _delete_selected_annotation(self):
        """Delete the currently selected annotation"""
        if not self.selected_annot_rect or self.selected_annot_page < 0:
            self.main_window.update_status_bar("No annotation selected")
            #self._update_annot_status("No annotation selected")
            return
        if not self.pdf_document:
            return

        try:
            # CRITICAL: keep 'page' alive
            page, annot = self._get_page_and_annot(
                self.selected_annot_page, self.selected_annot_rect)
            if annot:
                annot_type = annot.type[1]
                page.delete_annot(annot)
                self._clear_annotation_selection()
                self._save_and_refresh_annotations()
                self.main_window.update_status_bar(f"{annot_type} deleted")
                #self._update_annot_status(f"{annot_type} deleted")
            else:
                self.main_window.update_status_bar("Could not find annotation to delete")
                #self._update_annot_status("Could not find annotation to delete")
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to delete annotation: {str(e)}"
            )
    
    def _clear_page_annotations(self):
        """Clear all annotations from current page"""
        if not self.pdf_document or self.current_page >= self.total_pages:
            return

        page = self.pdf_document[self.current_page]
        annot_list = list(page.annots()) if page.annots() else []
        if not annot_list:
            self.main_window.update_status_bar("No annotations on this page")
            #self._update_annot_status("No annotations on this page")
            return

        msgbox = QMessageBox(self.window())
        msgbox.setWindowTitle("Clear Annotations")
        msgbox.setText(f"Remove all {len(annot_list)} annotations from current page?")
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.No)

        if self._exec_dialog_safe(msgbox) == QMessageBox.Yes:
            try:
                # Re-fetch because render might have happened during dialog
                page = self.pdf_document[self.current_page]
                annot_list = list(page.annots()) if page.annots() else []
                count = len(annot_list)
                for annot in annot_list:
                    page.delete_annot(annot)
                self._clear_annotation_selection()
                self._save_and_refresh_annotations()
                self.main_window.update_status_bar(f"Cleared {count} annotations")
                #self._update_annot_status(f"Cleared {count} annotations")
            except Exception as e:
                QMessageBox.critical(self.window(), "Error",
                                     f"Failed to clear annotations: {str(e)}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION SAVE METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    # def _save_and_refresh_annotations(self):
        # """Save changes incrementally and refresh display"""
        # if not self.pdf_document:
            # return
        
        # self.annotations_modified = True
        
        # # Try incremental save
        # try:
            # self.pdf_document.saveIncr()
        # except:
            # pass  # Some PDFs don't support incremental save
        
        # # Re-render all pages to show annotation changes
        # self.render_all_pages()

    def _save_and_refresh_annotations(self):
        """Save changes and refresh display — uses in-memory round-trip to guarantee persistence"""
        if not self.pdf_document:
            return
        self.annotations_modified = True

        try:
            # Write current state to bytes and reopen — this flushes all pending
            # annotation changes into the document's object stream, preventing
            # any annotation from silently disappearing on the next render.
            pdf_bytes = self.pdf_document.tobytes(garbage=0, deflate=False)
            self.pdf_document.close()
            self.pdf_document = fitz.open("pdf", pdf_bytes)
        except Exception as e:
            print(f"Warning: in-memory round-trip failed: {e}")
            # Fallback: try incremental save
            try:
                self.pdf_document.saveIncr()
            except Exception:
                pass

        self.render_all_pages()

    def _save_annotations(self):
        """Save annotations into the currently open PDF file (atomic temp-file swap)."""
        if not self.pdf_document or not self.current_pdf_path:
            QMessageBox.warning(self, "Warning", "No PDF document loaded.")
            return

        import shutil, tempfile, os

        src = self.current_pdf_path
        src_dir = os.path.dirname(src)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        tmp_path = None
        try:
            # 1. Write to a temp file in the same directory (same filesystem → atomic rename)
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=src_dir)
            os.close(fd)

            pdf_bytes = self.pdf_document.tobytes(garbage=4, deflate=True)
            with open(tmp_path, "wb") as f:
                f.write(pdf_bytes)

            # Verify the temp file is a valid PDF
            verify = fitz.open(tmp_path)
            n_pages = len(verify)
            verify.close()

            # 2. Close the current document so the file handle is released (important on Windows)
            self.pdf_document.close()
            self.pdf_document = None

            # 3. Atomic replace: rename temp → original path
            #    On Windows os.replace() handles locked files better than shutil.move
            os.replace(tmp_path, src)
            tmp_path = None   # prevent cleanup of the now-renamed file

            # 4. Re-open the saved file so the viewer stays functional
            self.pdf_document = fitz.open(src)
            self.annotations_modified = False

            QApplication.restoreOverrideCursor()
            self.main_window.update_status_bar(
                f"Saved ({n_pages} pages) → {os.path.basename(src)}")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"Annotations saved to {src}", 3000)

            # Re-render so the UI reflects the freshly saved document
            self.render_all_pages()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            import traceback
            traceback.print_exc()
            # Re-open original if we managed to close it but rename failed
            if self.pdf_document is None and os.path.exists(src):
                try:
                    self.pdf_document = fitz.open(src)
                    self.render_all_pages()
                except Exception:
                    pass
            QMessageBox.critical(
                self, "Save Error",
                f"Failed to save annotations in-place:\n\n{e}\n\n"
                f"Use 'Save As' to save to a new file."
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            QApplication.restoreOverrideCursor()
        
    def _save_annotations_as(self):
        """Save annotated PDF to a new file - WORKAROUND for PyMuPDF crash on Windows"""
        if not self.pdf_document or not self.current_pdf_path:
            QMessageBox.warning(self, "Warning", "No PDF document loaded")
            return
        
        # Suggest default filename
        directory = os.path.dirname(self.current_pdf_path)
        filename = os.path.basename(self.current_pdf_path)
        name, ext = os.path.splitext(filename)
        default_path = os.path.join(directory, f"{name}_annotated{ext}")
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotated PDF", default_path, "PDF Files (*.pdf)"
        )
        
        if not path:
            return
        
        if not path.endswith('.pdf'):
            path += '.pdf'
        
        # Check if trying to overwrite the currently open file
        if os.path.normpath(path) == os.path.normpath(self.current_pdf_path):
            QMessageBox.warning(
                self, "Cannot Overwrite", 
                "Cannot save over the currently open PDF.\nPlease choose a different filename."
            )
            return
        
        # ✅ WORKAROUND: Save by creating a new document from scratch
        # This avoids the crash in PyMuPDF's save() on Windows
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        
        try:
            import shutil
            import tempfile
            
            #print(f"\n💾 Using safe copy method for Windows...")
            
            # Method 1: Try to use tobytes() and write manually
            try:
                #print(f"   Method 1: Direct byte copy...")
                
                # Get the PDF as bytes
                pdf_bytes = self.pdf_document.tobytes(
                    garbage=4,      # Clean up
                    deflate=True    # Compress
                )
                
                # Write to target file
                with open(path, 'wb') as f:
                    f.write(pdf_bytes)
                
                #print(f"   ✅ Method 1 successful: {len(pdf_bytes):,} bytes written")
                
                # Verify
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    # Try to open it
                    verify_doc = fitz.open(path)
                    verify_pages = len(verify_doc)
                    verify_doc.close()
                    
                    #print(f"   ✅ Verified: {verify_pages} pages")
                    
                    # Success!
                    self.annotations_modified = False
                    self.main_window.update_status_bar(f"Saved to {os.path.basename(path)}")
                    #self._update_annot_status(f"Saved to {os.path.basename(path)}")
                    
                    if hasattr(self.main_window, 'statusBar'):
                        self.main_window.statusBar().showMessage(
                            f"Annotations saved: {path}", 3000
                        )
                    
                    QApplication.restoreOverrideCursor()
                    
                    QMessageBox.information(
                        self, "Success", 
                        f"Annotated PDF saved successfully!\n\n{path}"
                    )
                    return
                
            except Exception as method1_error:
                print(f"   ❌ Method 1 failed: {method1_error}")
            
            # Method 2: First save incrementally to source, then copy
            try:
                #print(f"   Method 2: Incremental save + file copy...")
                
                # Save changes to the current file
                self.pdf_document.saveIncr()
                #print(f"   ✅ Incremental save completed")
                
                # Now just copy the file
                shutil.copy2(self.current_pdf_path, path)
                #print(f"   ✅ File copied successfully")
                
                # Verify
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    #print(f"   ✅ Verified: {size:,} bytes")
                    
                    self.annotations_modified = False
                    self.main_window.update_status_bar(f"Saved to {os.path.basename(path)}")
                    #self._update_annot_status(f"Saved to {os.path.basename(path)}")
                    
                    if hasattr(self.main_window, 'statusBar'):
                        self.main_window.statusBar().showMessage(
                            f"Annotations saved: {path}", 3000
                        )
                    
                    QApplication.restoreOverrideCursor()
                    
                    QMessageBox.information(
                        self, "Success", 
                        f"Annotated PDF saved successfully!\n\n{path}"
                    )
                    return
                
            except Exception as method2_error:
                print(f"   ❌ Method 2 failed: {method2_error}")
            
            # Method 3: Save to temp file first, then copy
            try:
                print(f"   Method 3: Temp file + copy...")
                
                # Create temp file in the same directory as source
                temp_dir = os.path.dirname(self.current_pdf_path)
                with tempfile.NamedTemporaryFile(
                    suffix='.pdf', 
                    dir=temp_dir, 
                    delete=False
                ) as tmp:
                    temp_path = tmp.name
                
                #print(f"   Using temp file: {temp_path}")
                
                # Try writing to temp
                pdf_bytes = self.pdf_document.tobytes()
                with open(temp_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                # Copy from temp to destination
                shutil.move(temp_path, path)
                
                #print(f"   ✅ Method 3 successful")
                
                if os.path.exists(path):
                    self.annotations_modified = False
                    self.main_window.update_status_bar(f"Saved to {os.path.basename(path)}")
                    #self._update_annot_status(f"Saved to {os.path.basename(path)}")
                    
                    if hasattr(self.main_window, 'statusBar'):
                        self.main_window.statusBar().showMessage(
                            f"Annotations saved: {path}", 3000
                        )
                    
                    QApplication.restoreOverrideCursor()
                    
                    QMessageBox.information(
                        self, "Success", 
                        f"Annotated PDF saved successfully!\n\n{path}"
                    )
                    return
                
            except Exception as method3_error:
                print(f"   ❌ Method 3 failed: {method3_error}")
                # Clean up temp file if it exists
                try:
                    if 'temp_path' in locals() and os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
            
            # If we get here, all methods failed
            raise Exception("All save methods failed. See console for details.")
            
        except Exception as e:
            print(f"\n❌ All save methods failed: {e}")
            import traceback
            traceback.print_exc()
            
            QApplication.restoreOverrideCursor()
            
            QMessageBox.critical(
                self, "Save Error",
                f"Failed to save annotated PDF:\n\n{str(e)}\n\n"
                f"This appears to be a PyMuPDF issue on Windows.\n\n"
                f"Workaround:\n"
                f"1. The annotations are still in the current PDF\n"
                f"2. Close this PDF and reopen it\n"
                f"3. Try 'Save As' again\n\n"
                f"Or manually copy the file:\n{self.current_pdf_path}"
            )
        
        finally:
            QApplication.restoreOverrideCursor()
        
        
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANNOTATION CONTEXT MENU
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _show_annotation_context_menu(self, global_pos, page_num):
        """Show context menu for annotation"""
        if not self.selected_annot_rect:
            return

        menu = QMenu(self)

        # Use stored type (avoids page lifecycle issues)
        annot_type = self.selected_annot_type

        # Fallback: fresh lookup if stored type is missing
        if not annot_type:
            try:
                page, annot = self._get_page_and_annot(
                    page_num, self.selected_annot_rect)
                if annot:
                    annot_type = annot.type[1]
            except Exception:
                annot_type = None

        # Capture values for lambdas (avoid late-binding)
        _pn = page_num
        _rect = self.selected_annot_rect

        # Edit action for Text (sticky note)
        if annot_type == "Text":
            edit_action = QAction("✏️ Edit Note", self)
            edit_action.triggered.connect(
                lambda checked, pn=_pn, r=_rect:
                    self._edit_text_annotation(pn, r)
            )
            font = edit_action.font()
            font.setBold(True)
            edit_action.setFont(font)
            menu.addAction(edit_action)
            menu.addSeparator()

        # Edit action for FreeText (text box)
        elif annot_type == "FreeText":
            edit_action = QAction("✏️ Edit Text Box", self)
            edit_action.triggered.connect(
                lambda checked, pn=_pn, r=_rect:
                    self._edit_freetext_annotation(pn, r)
            )
            font = edit_action.font()
            font.setBold(True)
            edit_action.setFont(font)
            menu.addAction(edit_action)
            menu.addSeparator()

        # Delete action
        delete_action = QAction("🗑️ Delete Annotation", self)
        delete_action.triggered.connect(self._delete_selected_annotation)
        if annot_type not in ("Text", "FreeText"):
            font = delete_action.font()
            font.setBold(True)
            delete_action.setFont(font)
        menu.addAction(delete_action)

        menu.addSeparator()

        # Change color
        change_color_action = QAction("🎨 Change Color", self)
        change_color_action.triggered.connect(
            lambda checked, pn=_pn: self._change_annotation_color(pn)
        )
        menu.addAction(change_color_action)

        # Type info
        if annot_type:
            menu.addSeparator()
            info_action = QAction(f"Type: {annot_type}", self)
            info_action.setEnabled(False)
            menu.addAction(info_action)

        menu.exec_(global_pos)
    
    
    def _change_annotation_color(self, page_num):
        """Change color of selected annotation - handles all types including FreeText"""
        if not self.selected_annot_rect:
            return

        dlg = QColorDialog(self.annotation_color, self.window())
        dlg.setOption(QColorDialog.DontUseNativeDialog, True)
        if self._exec_dialog_safe(dlg) != QDialog.Accepted:
            return

        color = dlg.currentColor()
        if not color.isValid():
            return

        try:
            page, annot = self._get_page_and_annot(
                page_num, self.selected_annot_rect)
            if not annot:
                self.main_window.update_status_bar("Could not find annotation")
                #self._update_annot_status("Could not find annotation")
                return

            rgb = color.getRgbF()[:3]
            annot_type = annot.type[1]

            if annot_type == "FreeText":
                old_rect = fitz.Rect(annot.rect)
                try:
                    content = annot.info.get("content", "") or ""
                except Exception:
                    content = ""
                page.delete_annot(annot)
                new_annot = page.add_freetext_annot(
                    old_rect, content,
                    fontsize=12,
                    text_color=rgb,
                )
                new_annot.update()
                r = new_annot.rect
                self.selected_annot_rect = (r.x0, r.y0, r.x1, r.y1)
                self.selected_annot_page = page_num
            else:
                annot.set_colors(stroke=rgb)
                annot.update()

            self._save_and_refresh_annotations()
            self.main_window.update_status_bar("Color changed")
            #self._update_annot_status("Color changed")
        except Exception as e:
            QMessageBox.critical(
                self.window(), "Error",
                f"Failed to change color: {str(e)}"
            )        

    def _ensure_focus_after_action(self):
        """Ensure focus returns to PDF viewer after any action"""
        # Force focus back to scroll area and content widget
        self.scroll_area.setFocus(Qt.OtherFocusReason)
        self.content_widget.setFocus(Qt.OtherFocusReason)
    

    # def _handle_escape(self):
        # """Handle Escape key"""
        # if self.search_toolbar_visible:
            # self.hide_search_toolbar()

    # def _handle_print(self):
        # """Handle Ctrl+P for printing"""
        # if hasattr(self, 'print_btn') and self.print_btn.isEnabled():
            # self.print_pdf()
        

    def fit_to_text_width(self):
        """Fit PDF to text width by excluding margins - opens dialog for margin input"""
        if not self.pdf_document or len(self.pdf_document) == 0:
            return
        
        # Show margin input dialog
        dialog = MarginInputDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return  # User cancelled
        
        # Get margin in PDF points
        margin_points = dialog.get_margin_in_points()
        
        try:
            # Get first page dimensions
            page = self.pdf_document[0]
            page_rect = page.rect
            page_width_points = page_rect.width
            
            # Calculate text width (page width minus both margins)
            text_width_points = page_width_points - (2 * margin_points)
            
            # Make sure text width is positive
            if text_width_points <= 0:
                if hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(
                        "Error: Margins are too large for this page", 3000
                    )
                return
            
            # Calculate zoom factor to fit text width
            viewer_width = self.scroll_area.viewport().width() - 20  # Subtract padding
            self.zoom_factor = viewer_width / text_width_points
            
            # Store the margin offset for horizontal scrolling
            self.text_fit_margin_offset = margin_points * self.zoom_factor
            
            # Update display and render
            self.update_zoom_display()
            self.render_all_pages()
            
            # After rendering, scroll horizontally to hide the left margin
            QTimer.singleShot(100, self._apply_text_fit_scroll)
            
            # Status message
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(
                    f"Fit to text width: {margin_points:.1f}pt margins excluded", 3000
                )
            
        except Exception as e:
            print(f"Error in fit_to_text_width: {e}")
            import traceback
            traceback.print_exc()

    def _apply_text_fit_scroll(self):
        """Apply horizontal scroll to center the text area (hide margins)"""
        if hasattr(self, 'text_fit_margin_offset'):
            # Scroll to hide the left margin
            h_scrollbar = self.scroll_area.horizontalScrollBar()
            h_scrollbar.setValue(int(self.text_fit_margin_offset))

    def fit_page_to_window(self):
        """Fit entire page (including all margins) to the viewer window"""
        if not self.pdf_document or len(self.pdf_document) == 0:
            return
        
        try:
            # Get first page dimensions
            page = self.pdf_document[0]
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Get viewport dimensions
            viewport_width = self.scroll_area.viewport().width() - 20
            viewport_height = self.scroll_area.viewport().height() - 20
            
            # Calculate zoom factors for both dimensions
            zoom_width = viewport_width / page_width
            zoom_height = viewport_height / page_height
            
            # Use the smaller zoom factor to ensure entire page fits
            self.zoom_factor = min(zoom_width, zoom_height)
            
            # Clear any text fit margin offset
            if hasattr(self, 'text_fit_margin_offset'):
                delattr(self, 'text_fit_margin_offset')
            
            # Update display and render
            self.update_zoom_display()
            self.render_all_pages()
            
            # Center the page horizontally after rendering
            QTimer.singleShot(100, self._center_page_horizontally)
            
            # Status message
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(
                    f"Fit page to window: {self.zoom_factor * 100:.0f}% zoom", 3000
                )
            
        except Exception as e:
            print(f"Error in fit_page_to_window: {e}")
            import traceback
            traceback.print_exc()

    def _center_page_horizontally(self):
        """Center the page horizontally in the viewport"""
        if not self.page_labels:
            return
        
        # Get the first page width
        first_page = self.page_labels[0]
        page_width = first_page.width()
        viewport_width = self.scroll_area.viewport().width()
        
        # If page is smaller than viewport, center it
        if page_width < viewport_width:
            offset = (viewport_width - page_width) // 2
            h_scrollbar = self.scroll_area.horizontalScrollBar()
            h_scrollbar.setValue(max(0, -offset))
        else:
            # Page is larger - scroll to show left edge
            h_scrollbar = self.scroll_area.horizontalScrollBar()
            h_scrollbar.setValue(0)
        

    # def _scroll_by(self, amount):
        # """Scroll vertically by amount"""
        # scrollbar = self.scroll_area.verticalScrollBar()
        # scrollbar.setValue(scrollbar.value() + amount)
        # self._ensure_focus_after_action()

    # def _scroll_horizontal(self, amount):
        # """Scroll horizontally by amount"""
        # scrollbar = self.scroll_area.horizontalScrollBar()
        # scrollbar.setValue(scrollbar.value() + amount)
        # self._ensure_focus_after_action()

    # def _scroll_page_down(self):
        # """Scroll down by one viewport height"""
        # scrollbar = self.scroll_area.verticalScrollBar()
        # scrollbar.setValue(scrollbar.value() + self.scroll_area.viewport().height())
        # self._ensure_focus_after_action()

    # def _scroll_page_up(self):
        # """Scroll up by one viewport height"""
        # scrollbar = self.scroll_area.verticalScrollBar()
        # scrollbar.setValue(scrollbar.value() - self.scroll_area.viewport().height())
        # self._ensure_focus_after_action()

    # def _reset_zoom(self):
        # """Reset zoom to 100%"""
        # self.zoom_factor = 1.0
        # self.update_zoom_display()
        # self.render_all_pages()
        # self._ensure_focus_after_action()
    
        
    def set_toolbar_visible(self, visible):
        """Show or hide the toolbar
        Args:
            visible: True to show, False to hide
        """
        if hasattr(self, 'toolbar_widget'):
            self.toolbar_widget.setVisible(visible)

    def is_toolbar_visible(self):
        """Check if toolbar is currently visible
        Returns:
            bool: True if visible, False otherwise
        """
        if hasattr(self, 'toolbar_widget'):
            return self.toolbar_widget.isVisible()
        return True  # Default state

    def on_scroll_changed(self, value):
        """Handle scroll position changes to update current page"""
        if not self.pdf_document or not self.page_labels:
            return

        viewport_top = self.scroll_area.verticalScrollBar().value()
        viewport_height = self.scroll_area.viewport().height()

        best_page = 0
        max_visible_area = 0

        for i, page_label in enumerate(self.page_labels):
            # mapTo gives the correct position even when the label
            # is nested inside a row QWidget (grid mode).
            try:
                page_pos = page_label.mapTo(self.content_widget, QPoint(0, 0))
                page_top = page_pos.y()
            except Exception:
                page_top = page_label.y()

            page_bottom = page_top + page_label.height()

            visible_top = max(page_top, viewport_top)
            visible_bottom = min(page_bottom, viewport_top + viewport_height)
            visible_height = max(0, visible_bottom - visible_top)

            if visible_height > max_visible_area:
                max_visible_area = visible_height
                best_page = i

        if self.current_page != best_page:
            self.current_page = best_page
            self.update_page_controls()
            

    def load_toc(self):
        """Load table of contents (signets/bookmarks) from PDF"""
        self.toc_entries.clear()
        
        if not self.pdf_document:
            return
        
        try:
            toc = self.pdf_document.get_toc()  # Returns list of [level, title, page]
            self.toc_entries = toc
            #print(f"📚 Loaded {len(toc)} TOC entries")
        except Exception as e:
            print(f"Error loading TOC: {e}")
            self.toc_entries = []

    def on_toc_selected(self, index):
        """Handle TOC/signets selection from combo box"""
        if index < 0 or index >= len(self.toc_entries):
            return
        
        # Get the selected TOC entry
        level, title, page = self.toc_entries[index]
        
        # Convert to 0-indexed page number (TOC pages are 1-indexed)
        page_index = page - 1
        
        if 0 <= page_index < self.total_pages:
            print(f"📑 Navigating to TOC entry: {title} (page {page})")
            
            # Add to navigation history before jumping
            if not self.is_navigating_history:
                self._add_to_history()
                self._update_history_buttons()
            
            # Scroll to the page
            self.scroll_to_page(page_index)
            
            # Update status bar
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(
                    f"Jumped to: {title} (page {page})", 3000
                )
            
            # Reset combo to placeholder (optional - for better UX)
            self.toc_combo.blockSignals(True)
            self.toc_combo.setCurrentIndex(-1)
            self.toc_combo.blockSignals(False)

    def populate_toc_combo(self):
        """Populate the TOC combo box with signets/bookmarks"""
        self.toc_combo.blockSignals(True)
        self.toc_combo.clear()
        
        if not self.toc_entries:
            self.toc_combo.addItem("(No table of contents)")
            self.toc_combo.setEnabled(False)
        else:
            self.toc_combo.setEnabled(True)
            # Add entries with indentation based on level
            for level, title, page in self.toc_entries:
                # Indent based on level (level 1 = no indent, level 2 = 2 spaces, etc.)
                indent = "  " * (level - 1)
                display_title = f"{indent}{title} ({page})"
                self.toc_combo.addItem(display_title)
        
        # Set to no selection initially
        self.toc_combo.setCurrentIndex(-1)
        self.toc_combo.blockSignals(False)
    
    
    def get_zoom_factor(self):
        """Get current zoom factor"""
        return getattr(self, 'zoom_factor', 1.0)

    def set_zoom_factor(self, zoom):
        """Set zoom factor and update display"""
        try:
            # Validate zoom value
            zoom = max(0.1, min(5.0, float(zoom)))  # Clamp between 10% and 500%
            
            # Only update if zoom actually changed
            if abs(self.zoom_factor - zoom) < 0.001:
                # print(f"📊 Zoom unchanged: {zoom}")
                return
            
            # print(f"📊 Setting zoom factor from {self.zoom_factor} to {zoom}")
            self.zoom_factor = zoom
            
            # Update the zoom spinbox display (without triggering re-render)
            if hasattr(self, 'zoom_spinbox') and self.zoom_spinbox:
                self.zoom_spinbox.blockSignals(True)
                self.zoom_spinbox.setValue(int(zoom * 100))
                self.zoom_spinbox.blockSignals(False)
            
            # Re-render all pages with new zoom
            if self.pdf_document and self.total_pages > 0:
                self.render_all_pages()
                # print(f"✅ Zoom applied: {zoom * 100:.0f}%")
            
        except Exception as e:
            print(f"❌ Error setting zoom factor: {e}")
            import traceback
            traceback.print_exc()
        

    # ✅ NEW: Add current location to navigation history
    def _add_to_history(self, page_num=None, scroll_y=None):
        """Add current location to navigation history
        
        Args:
            page_num: Page number to save (defaults to current page)
            scroll_y: Scroll position to save (defaults to current scroll)
        """
        # Don't add to history if we're navigating through history
        if self.is_navigating_history:
            return
        
        if page_num is None:
            page_num = self.current_page
        
        if scroll_y is None:
            scroll_y = self.scroll_area.verticalScrollBar().value()
        
        # If we're in the middle of history (after going back), 
        # remove all forward history
        if self.history_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.history_index + 1]
        
        # Add new location
        new_location = (page_num, scroll_y)
        
        # Don't add duplicate consecutive entries
        if (len(self.navigation_history) == 0 or 
            self.navigation_history[-1] != new_location):
            self.navigation_history.append(new_location)
            
            # Limit history size
            if len(self.navigation_history) > self.max_history_size:
                self.navigation_history.pop(0)
            else:
                self.history_index += 1
            
            # Update history index
            self.history_index = len(self.navigation_history) - 1
            
            # print(f"📚 Added to history: page {page_num + 1}, scroll {scroll_y} (index {self.history_index}/{len(self.navigation_history)-1})")

    # def _update_history_buttons(self):
        # """Update the enabled state of back/forward buttons based on history"""
        # if hasattr(self, 'back_btn'):
            # self.back_btn.setEnabled(self.history_index > 0)
        
        # if hasattr(self, 'forward_btn'):
            # self.forward_btn.setEnabled(self.history_index < len(self.navigation_history) - 1)

    # ✅ FIXED: navigate_back with better debugging
    def navigate_back(self):
        """Navigate to previous location in history (Alt+Left Arrow)"""
        # print(f"⬅️ navigate_back called: history_index={self.history_index}, history_len={len(self.navigation_history)}")
        
        if len(self.navigation_history) == 0:
            # print("⚠️ Navigation history is empty")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("No navigation history", 2000)
            return
        
        if self.history_index <= 0:
            # print("⚠️ Already at the beginning of history")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("No previous location", 2000)
            return
        
        # Save current location if we're at the end of history
        current_scroll = self.scroll_area.verticalScrollBar().value()
        current_location = (self.current_page, current_scroll)
        
        # If at end of history and current location is different, update last entry
        if self.history_index == len(self.navigation_history) - 1:
            if self.navigation_history[-1] != current_location:
                # Add current location as a new entry so we can come back to it
                self.navigation_history.append(current_location)
                self.history_index = len(self.navigation_history) - 1
                # print(f"📚 Added current location before going back: {current_location}")
        
        # Move back in history
        self.history_index -= 1
        page_num, scroll_y = self.navigation_history[self.history_index]
        
        # print(f"⬅️ Navigating back to: page {page_num + 1}, scroll {scroll_y} (index {self.history_index}/{len(self.navigation_history)-1})")
        
        # Set flag to prevent adding to history
        self.is_navigating_history = True
        
        # Navigate to the location
        self._navigate_to_history_location(page_num, scroll_y)
        
        # Reset flag
        self.is_navigating_history = False
        
        # Update button states
        self._update_history_buttons()
        
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(
                f"Back to page {page_num + 1} ({self.history_index + 1}/{len(self.navigation_history)})", 
                2000
            )
        self._ensure_focus_after_action()

    def navigate_forward(self):
        """Navigate to next location in history (Alt+Right Arrow)"""
        #print(f"➡️ navigate_forward called: history_index={self.history_index}, history_len={len(self.navigation_history)}")
        
        if self.history_index >= len(self.navigation_history) - 1:
            # print("⚠️ Already at the end of history")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("No forward location", 2000)
            return
        
        # Move forward in history
        self.history_index += 1
        page_num, scroll_y = self.navigation_history[self.history_index]
        
        # print(f"➡️ Navigating forward to: page {page_num + 1}, scroll {scroll_y} (index {self.history_index}/{len(self.navigation_history)-1})")
        
        # Set flag to prevent adding to history
        self.is_navigating_history = True
        
        # Navigate to the location
        self._navigate_to_history_location(page_num, scroll_y)
        
        # Reset flag
        self.is_navigating_history = False
        
        # Update button states
        self._update_history_buttons()
        
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(
                f"Forward to page {page_num + 1} ({self.history_index + 1}/{len(self.navigation_history)})", 
                2000
            )
        self._ensure_focus_after_action()

    # ✅ FIXED: _update_history_buttons with debugging
    def _update_history_buttons(self):
        """Update the enabled state of back/forward buttons based on history"""
        can_go_back = self.history_index > 0 and len(self.navigation_history) > 1
        can_go_forward = self.history_index < len(self.navigation_history) - 1
        
        # print(f"🔄 Updating history buttons: can_back={can_go_back}, can_forward={can_go_forward}, index={self.history_index}, len={len(self.navigation_history)}")
        
        if hasattr(self, 'back_btn'):
            self.back_btn.setEnabled(can_go_back)
            # print(f"   back_btn enabled: {can_go_back}")
        
        if hasattr(self, 'forward_btn'):
            self.forward_btn.setEnabled(can_go_forward)
            # print(f"   forward_btn enabled: {can_go_forward}")


    # ✅ FIXED: _navigate_to_history_location
    def _navigate_to_history_location(self, page_num, scroll_y):
        """Navigate to a specific page and scroll position from history
        
        Args:
            page_num: Target page number
            scroll_y: Target scroll position
        """
        #print(f"📍 Navigating to history location: page {page_num + 1}, scroll {scroll_y}")
        
        if 0 <= page_num < len(self.page_labels):
            # Update current page
            self.current_page = page_num
            
            # Scroll to the position
            self.scroll_area.verticalScrollBar().setValue(scroll_y)
            
            # Update page controls
            self.update_page_controls()
            
            #print(f"📍 Navigation complete")
        #else:
        #    print(f"⚠️ Invalid page number: {page_num}")
        

    def handle_link_click(self, link_info):
        """Handle clicking on a hyperlink - FIXED VERSION with history
        
        Args:
            link_info: Dict with 'type', 'dest', 'dest_page', 'dest_point', and 'rect' keys
        """
        link_type = link_info.get('type')
        dest = link_info.get('dest')
        dest_page = link_info.get('dest_page')
        dest_point = link_info.get('dest_point')  # This is in PDF coordinates (bottom-left origin)
        
        # print(f"🔗 Handling link click: type={link_type}, dest={dest}, dest_page={dest_page}, dest_point={dest_point}")
        
        if link_type == 'goto':
            # ✅ ADD TO HISTORY BEFORE JUMPING
            self._add_to_history()
            self._update_history_buttons()  # ✅ Update buttons immediately
            
            # Jump to internal page/location
            page_num = dest_page if dest_page is not None else dest
            if isinstance(page_num, int) and 0 <= page_num < self.total_pages:
                # print(f"🔗 Jumping to page {page_num + 1}")
                self.scroll_to_page_with_offset(page_num, dest_point)
            # else:
                # print(f"⚠️ Invalid page number: {page_num}")
        
        elif link_type == 'uri':
            # External URLs don't affect history
            # print(f"🔗 Opening URL: {dest}")
            import webbrowser
            try:
                webbrowser.open(str(dest))
            except Exception as e:
                print(f"❌ Error opening URL: {e}")
        
        elif link_type == 'named':
            # ✅ ADD TO HISTORY BEFORE JUMPING
            self._add_to_history()
            self._update_history_buttons()  # ✅ Update buttons immediately
            
            # Handle named destinations (resolve to page number)
            try:
                page_num = self._resolve_named_dest(dest)
                if page_num is not None:
                    #print(f"🔗 Jumping to named destination '{dest}' (page {page_num + 1})")
                    self.scroll_to_page(page_num)
                else:
                    #print(f"⚠️ Could not resolve named destination: {dest}")
                    pass
            except Exception as e:
                print(f"❌ Error resolving named destination: {e}")
        
        elif link_type == 'gotor':
            # Link to external PDF
            #print(f"🔗 External PDF link: {dest}")
            if dest and os.path.exists(dest):
                if hasattr(self.main_window, 'pdf_manager'):
                    self.main_window.pdf_manager.load_pdf_in_viewer(dest)
            else:
                #print(f"⚠️ External PDF not found: {dest}")
                pass
            
    def _add_to_history(self, page_num=None, scroll_y=None):
        """Add current location to navigation history
        
        Args:
            page_num: Page number to save (defaults to current page)
            scroll_y: Scroll position to save (defaults to current scroll)
        """
        # Don't add to history if we're navigating through history
        if self.is_navigating_history:
            return
        
        if page_num is None:
            page_num = self.current_page
        
        if scroll_y is None:
            scroll_y = self.scroll_area.verticalScrollBar().value()
        
        # If we're in the middle of history (after going back), 
        # remove all forward history
        if self.history_index >= 0 and self.history_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.history_index + 1]
        
        # Add new location
        new_location = (page_num, scroll_y)
        
        # Don't add duplicate consecutive entries
        if (len(self.navigation_history) == 0 or 
            self.navigation_history[-1] != new_location):
            self.navigation_history.append(new_location)
            
            # Limit history size
            if len(self.navigation_history) > self.max_history_size:
                self.navigation_history.pop(0)
            
            # Update history index to point to the last entry
            self.history_index = len(self.navigation_history) - 1
            
            #print(f"📚 Added to history: page {page_num + 1}, scroll {scroll_y} (index {self.history_index}/{len(self.navigation_history)-1})")
            #print(f"📚 History now has {len(self.navigation_history)} entries")


    def toggle_tooltips(self):
        """Toggle tooltip display on/off"""
        self.tooltips_enabled = self.tooltip_toggle_btn.isChecked()
        self._update_tooltip_button_style()
        
        status_msg = "Link tooltips enabled" if self.tooltips_enabled else "Link tooltips disabled"
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(status_msg, 2000)

    def _update_tooltip_button_style(self):
        """Update the tooltip button appearance based on state"""
        if self.tooltips_enabled:
            self.tooltip_toggle_btn.setStyleSheet("background-color: #4CAF50;")  # Green when enabled
            self.tooltip_toggle_btn.setToolTip("Link tooltips: ON (click to disable)")
        else:
            self.tooltip_toggle_btn.setStyleSheet("")  # Default style when disabled
            self.tooltip_toggle_btn.setToolTip("Link tooltips: OFF (click to enable)")

    def _show_link_tooltip(self):
        """Show tooltip for the pending link"""
        if not self.tooltips_enabled or not self.pending_tooltip_link:
            return
        
        link_info = self.pending_tooltip_link
        tooltip_text = self._generate_tooltip_text(link_info)
        
        if tooltip_text and self.pending_tooltip_pos:
            from PyQt5.QtWidgets import QToolTip
            QToolTip.showText(self.pending_tooltip_pos, tooltip_text)

    # =========================================================================
    # COORDINATE CONVERSION - THE KEY FIX
    # =========================================================================
    
    def pdf_point_to_widget_y(self, page, pdf_y):
        """
        Convert PDF Y coordinate (bottom-left origin, points)
        to widget Y coordinate (top-left origin, pixels with zoom)
        
        This is THE KEY FUNCTION that fixes both problems:
        1. Link clicking lands at wrong position
        2. Tooltip previews show wrong text
        
        Args:
            page: fitz.Page object
            pdf_y: Y coordinate in PDF space (origin at bottom-left)
            
        Returns:
            Y coordinate in widget space (origin at top-left, scaled by zoom)
        """
        page_height_pdf = page.rect.height
        # Invert Y axis: PDF has origin at bottom, screen has origin at top
        inverted_y = page_height_pdf - pdf_y
        # Apply zoom scaling
        return inverted_y * self.zoom_factor
    
    # def pdf_point_to_widget(self, page, pdf_x, pdf_y):
        # """
        # Convert PDF point (x, y) to widget coordinates
        
        # Args:
            # page: fitz.Page object
            # pdf_x: X coordinate in PDF space
            # pdf_y: Y coordinate in PDF space (origin at bottom-left)
            
        # Returns:
            # Tuple (widget_x, widget_y) in widget space
        # """
        # page_height_pdf = page.rect.height
        # # X stays the same direction, just scale
        # widget_x = pdf_x * self.zoom_factor
        # # Y needs inversion AND scaling
        # widget_y = (page_height_pdf - pdf_y) * self.zoom_factor
        # return (widget_x, widget_y)
    
    # def widget_point_to_pdf(self, page, widget_x, widget_y):
        # """
        # Convert widget coordinates back to PDF coordinates
        # (useful for text extraction at click position)
        
        # Args:
            # page: fitz.Page object
            # widget_x: X coordinate in widget space
            # widget_y: Y coordinate in widget space
            
        # Returns:
            # Tuple (pdf_x, pdf_y) in PDF space
        # """
        # page_height_pdf = page.rect.height
        # # Reverse the zoom scaling
        # pdf_x = widget_x / self.zoom_factor
        # # Reverse zoom AND invert Y
        # pdf_y = page_height_pdf - (widget_y / self.zoom_factor)
        # return (pdf_x, pdf_y)

    def _show_annotation_tooltip(self, page_num, annot_info, pos):
        """Show tooltip for annotation when hovering
        Args:
            annot_info: Dict with 'rect' and 'type' keys, or tuple (x0,y0,x1,y1) for backwards compat
        """
        try:
            # Handle both dict and tuple formats
            if isinstance(annot_info, dict):
                annot_rect = annot_info['rect']
                annot_type = annot_info.get('type', 'Unknown')
            else:
                # Fallback for tuple format
                annot_rect = annot_info
                # Need to look up type
                annot = self._find_annot_by_rect(page_num, annot_rect)
                if not annot:
                    return
                try:
                    annot_type = annot.type[1]
                except:
                    annot_type = "Unknown"
            
            # For text annotations (sticky notes), show the content
            if annot_type == "Text":
                try:
                    # Re-find annotation to get fresh content
                    annot = self._find_annot_by_rect(page_num, annot_rect)
                    if annot:
                        content = annot.info.get("content", "")
                        if content:
                            from PyQt5.QtWidgets import QToolTip
                            
                            # Format multi-line content
                            lines = content.split('\n')
                            if len(lines) > 15:
                                display_lines = lines[:15]
                                display_content = '\n'.join(display_lines) + '\n... (double-click to edit)'
                            else:
                                display_content = content + '\n\n(double-click to edit)'
                            
                            # Wrap long lines
                            formatted_lines = []
                            for line in display_content.split('\n'):
                                if len(line) > 80:
                                    while len(line) > 80:
                                        formatted_lines.append(line[:80])
                                        line = line[80:]
                                    if line:
                                        formatted_lines.append(line)
                                else:
                                    formatted_lines.append(line)
                            
                            display_content = '\n'.join(formatted_lines)
                            QToolTip.showText(pos, f"📝 Note:\n{display_content}")
                except Exception as e:
                    print(f"Error showing text annotation tooltip: {e}")
            elif annot_type == "FreeText":
                from PyQt5.QtWidgets import QToolTip
                QToolTip.showText(pos, "✏️ Text Box (visible on page)")
        except Exception as e:
            print(f"Error showing annotation tooltip: {e}")
            import traceback
            traceback.print_exc()
        
    def _generate_tooltip_text(self, link_info):
        """Generate tooltip text with precise destination preview"""
        link_type = link_info.get('type')
        dest = link_info.get('dest')
        dest_page = link_info.get('dest_page')
        dest_point = link_info.get('dest_point')
        
        if link_type == 'goto':
            # Internal link - show page number and try to get content preview
            page_num = dest_page if dest_page is not None else dest
            if isinstance(page_num, int) and self.pdf_document and 0 <= page_num < len(self.pdf_document):
                tooltip = f"📄 Go to page {page_num + 1}"
                
                # Try specialized bibliography extraction first
                if dest_point:
                    page = self.pdf_document[page_num]
                    
                    # Check if this looks like a bibliography reference
                    # (destination is in bottom half of page, common for references)
                    page_height = page.rect.height
                    if dest_point[1] > page_height * 0.5:
                        preview = self._extract_bibliography_entry(page, dest_point)
                        if preview:
                            tooltip += f"\n\n{preview}"
                            return tooltip
                
                # Standard text extraction
                preview = self._get_destination_preview(page_num, dest_point)
                if preview:
                    tooltip += f"\n\n{preview}"
                
                return tooltip
            return f"📄 Internal link: {dest}"
        
        elif link_type == 'uri':
            # External URL
            url = str(dest)
            if len(url) > 60:
                url = url[:57] + "..."
            return f"🔗 External link:\n{url}"
        
        elif link_type == 'named':
            # Named destination
            tooltip = f"🏷️ Reference: {dest}"
            
            # Try to resolve named destination and get preview
            resolved_page = self._resolve_named_dest(dest)
            if resolved_page is not None:
                tooltip += f"\n(Page {resolved_page + 1})"
                preview = self._get_destination_preview(resolved_page)
                if preview:
                    tooltip += f"\n\n{preview}"
            
            return tooltip
        
        elif link_type == 'gotor':
            # Link to external PDF
            return f"📁 External PDF: {dest}"
        
        return f"🔗 Link: {dest}"

    def _get_destination_preview(self, page_num, dest_point=None, max_chars=200):
        """Get a precise text preview from the destination location in PDF
        
        FIXED: Now properly converts PDF coordinates before extracting text
        
        Args:
            page_num: 0-indexed page number
            dest_point: Optional (x, y) destination point in PDF coordinates (bottom-left origin)
            max_chars: Maximum characters to show in preview
            
        Returns:
            Formatted preview string or None
        """
        try:
            if not self.pdf_document or page_num < 0 or page_num >= len(self.pdf_document):
                return None
            
            page = self.pdf_document[page_num]
            
            if dest_point:
                pdf_x, pdf_y = dest_point
                
                # ✅ FIX: Convert PDF coordinates (bottom-left origin) to 
                # coordinates suitable for text extraction (top-left origin)
                # PyMuPDF's get_text() uses top-left origin internally
                corrected_point = (
                    pdf_x,
                    page.rect.height - pdf_y  # Invert Y axis
                )
                
                # ENHANCED: Use multiple methods for precise extraction at destination point
                preview = self._extract_text_at_point(page, corrected_point, max_chars)
                if preview:
                    return preview
            
            # Fallback: Get text from the top of the page
            return self._extract_text_from_top(page, max_chars)
        
        except Exception as e:
            print(f"Error getting destination preview: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_text_at_point(self, page, dest_point, max_chars=250):
        """Extract text precisely at the destination point using ENHANCED strategies
        
        IMPORTANT: dest_point should already be in top-left origin coordinates
        (i.e., already converted from PDF's bottom-left origin)
        
        Args:
            page: fitz.Page object
            dest_point: (x, y) tuple in TOP-LEFT origin coordinates (already converted)
            max_chars: Maximum characters to show
            
        Returns:
            Formatted text preview or None
        """
        x, y = dest_point
        
        # STRATEGY 1: Use get_text("blocks") with reading order - MOST ACCURATE
        try:
            blocks = page.get_text("blocks", sort=True)  # sort=True preserves reading order
            
            # Find blocks that contain or are very close to the destination point
            candidate_blocks = []
            
            for block in blocks:
                # block format: (x0, y0, x1, y1, "text", block_no, block_type)
                if len(block) < 7:
                    continue
                
                x0, y0, x1, y1 = block[0], block[1], block[2], block[3]
                block_text = block[4]
                
                # Calculate vertical distance (more important for reading order)
                # and horizontal distance
                v_dist = min(abs(y - y0), abs(y - y1))
                h_dist = min(abs(x - x0), abs(x - x1))
                
                # Check if point is inside block (with generous expansion)
                expanded_y0 = y0 - 30
                expanded_y1 = y1 + 30
                expanded_x0 = x0 - 50
                expanded_x1 = x1 + 400  # Generous right expansion to catch continuation
                
                is_inside_expanded = (expanded_x0 <= x <= expanded_x1 and 
                                     expanded_y0 <= y <= expanded_y1)
                
                if is_inside_expanded:
                    # Calculate priority score (lower is better)
                    # Prioritize vertical proximity over horizontal
                    score = v_dist * 2 + h_dist
                    candidate_blocks.append((score, block, block_text))
                elif v_dist < 50 and h_dist < 200:
                    # Also consider nearby blocks
                    score = v_dist * 3 + h_dist * 1.5
                    candidate_blocks.append((score, block, block_text))
            
            if candidate_blocks:
                # Sort by score (closest blocks first)
                candidate_blocks.sort(key=lambda x: x[0])
                
                # Take the best 3-5 blocks to form context
                best_blocks = candidate_blocks[:5]
                
                # Extract text from these blocks in reading order
                text_parts = []
                for score, block, block_text in best_blocks:
                    cleaned_text = block_text.strip()
                    if cleaned_text:
                        text_parts.append(cleaned_text)
                
                if text_parts:
                    # Join with space and format
                    combined_text = ' '.join(text_parts)
                    formatted = self._format_preview_text(combined_text, max_chars)
                    if formatted:
                        return formatted
        
        except Exception as e:
            print(f"Strategy 1 (blocks with reading order) failed: {e}")
        
        # STRATEGY 2: Use get_text("words") with intelligent line reconstruction
        try:
            words = page.get_text("words", sort=True)  # sort=True for reading order
            
            # Find words near the destination point with priority scoring
            nearby_words = []
            
            for word_info in words:
                # word_info = (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                if len(word_info) < 5:
                    continue
                
                x0, y0, x1, y1 = word_info[0], word_info[1], word_info[2], word_info[3]
                word_text = word_info[4]
                
                # Calculate word center
                word_x = (x0 + x1) / 2
                word_y = (y0 + y1) / 2
                
                # Calculate distances
                v_dist = abs(y - word_y)
                h_dist = abs(x - word_x)
                
                # Check if point is near this word
                # For bibliography entries like [6], we want words on the same line and after
                expanded_y0 = y0 - 15
                expanded_y1 = y1 + 15
                expanded_x0 = x0 - 30
                expanded_x1 = x1 + 500  # Very generous right expansion
                
                if (expanded_x0 <= x <= expanded_x1 and 
                    expanded_y0 <= y <= expanded_y1):
                    # Point is in or near this word
                    # Priority: words to the right and on same line get lower score
                    if x <= word_x:
                        # Word is to the right of or at destination point
                        score = v_dist * 2 + h_dist * 0.5
                    else:
                        # Word is to the left
                        score = v_dist * 2 + h_dist * 2
                    
                    nearby_words.append((score, word_info))
                elif v_dist < 30 and h_dist < 300:
                    # Nearby word
                    score = v_dist * 3 + h_dist
                    nearby_words.append((score, word_info))
            
            if nearby_words:
                # Sort by score (best matches first)
                nearby_words.sort(key=lambda x: x[0])
                
                # Take best 30-40 words for context
                best_words = [w[1] for w in nearby_words[:40]]
                
                # Group by line number if available
                if len(best_words[0]) >= 7:
                    lines_dict = {}
                    for word_info in best_words:
                        line_no = word_info[6]
                        if line_no not in lines_dict:
                            lines_dict[line_no] = []
                        lines_dict[line_no].append(word_info)
                    
                    # Reconstruct text line by line
                    text_lines = []
                    for line_no in sorted(lines_dict.keys()):
                        line_words = sorted(lines_dict[line_no], key=lambda w: w[0])  # Sort by x
                        line_text = ' '.join(w[4] for w in line_words)
                        text_lines.append(line_text)
                    
                    if text_lines:
                        combined = ' '.join(text_lines)
                        formatted = self._format_preview_text(combined, max_chars)
                        if formatted:
                            return formatted
                else:
                    # No line info - just concatenate by position
                    text = ' '.join(w[4] for w in best_words)
                    formatted = self._format_preview_text(text, max_chars)
                    if formatted:
                        return formatted
        
        except Exception as e:
            print(f"Strategy 2 (words with reading order) failed: {e}")
        
        # STRATEGY 3: Use get_text("dict") for detailed structure analysis
        try:
            text_dict = page.get_text("dict", sort=True)
            blocks = text_dict.get("blocks", [])
            
            best_lines = []
            
            for block in blocks:
                if block.get("type") != 0:  # Skip non-text blocks
                    continue
                
                block_bbox = block.get("bbox")
                if not block_bbox:
                    continue
                
                # Check if block is near destination
                bx0, by0, bx1, by1 = block_bbox
                
                # Expanded check
                if not (bx0 - 50 <= x <= bx1 + 400 and by0 - 30 <= y <= by1 + 30):
                    continue
                
                # Analyze lines in this block
                lines = block.get("lines", [])
                for line in lines:
                    line_bbox = line.get("bbox")
                    if not line_bbox:
                        continue
                    
                    lx0, ly0, lx1, ly1 = line_bbox
                    
                    # Calculate vertical distance to line
                    line_y_center = (ly0 + ly1) / 2
                    v_dist = abs(y - line_y_center)
                    
                    # Check horizontal position relative to line
                    if lx0 - 40 <= x <= lx1 + 500 and v_dist < 25:
                        # Extract text from spans
                        spans = line.get("spans", [])
                        line_text_parts = []
                        
                        for span in spans:
                            span_text = span.get("text", "")
                            span_bbox = span.get("bbox")
                            
                            if span_bbox:
                                sx0, sy0, sx1, sy1 = span_bbox
                                # Include spans at or after the destination point
                                if sx1 >= x - 40:
                                    line_text_parts.append(span_text)
                            elif span_text:
                                line_text_parts.append(span_text)
                        
                        if line_text_parts:
                            line_text = ''.join(line_text_parts)
                            best_lines.append((v_dist, line_text))
            
            if best_lines:
                # Sort by vertical distance
                best_lines.sort(key=lambda x: x[0])
                # Take best 3-5 lines
                texts = [line[1] for line in best_lines[:5]]
                combined = ' '.join(texts)
                formatted = self._format_preview_text(combined, max_chars)
                if formatted:
                    return formatted
        
        except Exception as e:
            print(f"Strategy 3 (dict with spans) failed: {e}")
        
        # STRATEGY 4: Precise vertical slice with horizontal extension
        try:
            # Create a thin horizontal slice at the destination y-coordinate
            # but extend far to the right to catch full lines
            slice_height = 25  # Thin vertical slice
            wide_rect = fitz.Rect(
                x - 40,           # Start slightly before point
                y - slice_height/2,   # Center vertically on point
                x + 500,          # Extend far right
                y + slice_height/2
            )
            
            text = page.get_text("text", clip=wide_rect).strip()
            
            if text:
                # Also get a bit below for context
                below_rect = fitz.Rect(x - 40, y + slice_height/2, x + 500, y + slice_height/2 + 40)
                text_below = page.get_text("text", clip=below_rect).strip()
                
                combined = text
                if text_below:
                    combined = text + " " + text_below
                
                formatted = self._format_preview_text(combined, max_chars)
                if formatted:
                    return formatted
        
        except Exception as e:
            print(f"Strategy 4 (horizontal slice) failed: {e}")
        
        # STRATEGY 5: Wider fallback with reading order preservation
        try:
            wide_rect = fitz.Rect(x - 50, y - 25, x + 450, y + 100)
            
            # Use get_text with flags to preserve layout
            text = page.get_text("text", clip=wide_rect, sort=True).strip()
            
            if text:
                return self._format_preview_text(text, max_chars)
        
        except Exception as e:
            print(f"Strategy 5 (wide fallback) failed: {e}")
        
        return None

    def _extract_text_from_top(self, page, max_chars=200):
        """Extract text from the top of a page as fallback"""
        try:
            # Get text from top portion of page
            page_rect = page.rect
            top_rect = fitz.Rect(
                page_rect.x0,
                page_rect.y0,
                page_rect.x1,
                min(page_rect.y0 + 150, page_rect.y1)  # Top 150 points
            )
            
            text = page.get_text("text", clip=top_rect, sort=True).strip()
            
            if text:
                return self._format_preview_text(text, max_chars)
            
            return None
        except Exception as e:
            print(f"Error extracting text from top: {e}")
            return None

    def _format_preview_text(self, text, max_chars=250):
        """Format extracted text for tooltip display with smart truncation
        
        Args:
            text: Raw extracted text
            max_chars: Maximum characters to show
            
        Returns:
            Formatted preview string
        """
        if not text:
            return None
        
        # Clean up the text but preserve important formatting
        # Replace multiple spaces with single space
        import re
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with single newline
        text = re.sub(r'\n+', '\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # For bibliography entries, keep them more intact
        # Bibliography entries often start with [number] or author names
        is_biblio = any(re.match(r'^\[\d+\]', line) for line in lines)
        
        if is_biblio:
            # For bibliography: keep first 2-3 complete lines
            preview_lines = lines[:3]
            preview = '\n'.join(preview_lines)
            
            # Truncate if too long
            if len(preview) > max_chars:
                # Try to truncate at a sensible point (end of sentence/phrase)
                truncate_points = ['. ', ', ', '; ', ' and ', ' in ']
                for point in truncate_points:
                    last_pos = preview[:max_chars].rfind(point)
                    if last_pos > max_chars * 0.6:  # At least 60% of desired length
                        preview = preview[:last_pos + len(point)] + "..."
                        break
                else:
                    # No good truncation point found
                    preview = preview[:max_chars-3] + "..."
        else:
            # For other content: reflow into readable lines
            preview_lines = []
            current_line = ""
            words = ' '.join(lines).split()
            
            for word in words:
                if len(current_line) + len(word) + 1 <= 65:  # ~65 chars per line
                    current_line += word + " "
                else:
                    if current_line:
                        preview_lines.append(current_line.strip())
                    current_line = word + " "
                    
                    # Limit to 4 lines
                    if len(preview_lines) >= 3:
                        break
            
            # Add remaining text
            if current_line and len(preview_lines) < 4:
                preview_lines.append(current_line.strip())
            
            preview = '\n'.join(preview_lines)
            
            # Truncate if needed
            if len(preview) > max_chars:
                preview = preview[:max_chars-3] + "..."
        
        # Add quotes for clarity
        return f'"{preview}"'

    # def _extract_text_from_block(self, block):
        # """Extract text from a text block dictionary with reading order preservation
        
        # Args:
            # block: Block dictionary from get_text("dict")
            
        # Returns:
            # Extracted text string with proper spacing
        # """
        # try:
            # lines = block.get("lines", [])
            # text_parts = []
            
            # for line in lines:
                # spans = line.get("spans", [])
                # line_parts = []
                
                # for span in spans:
                    # span_text = span.get("text", "")
                    # if span_text:
                        # # Preserve spaces between spans
                        # line_parts.append(span_text)
                
                # if line_parts:
                    # # Join spans with space if needed
                    # line_text = ''.join(line_parts)
                    # # Clean up multiple spaces
                    # line_text = ' '.join(line_text.split())
                    # if line_text:
                        # text_parts.append(line_text)
            
            # # Join lines with space (not newline, for tooltip compactness)
            # return ' '.join(text_parts)
        
        # except Exception as e:
            # print(f"Error extracting text from block: {e}")
            # return None

    def _extract_bibliography_entry(self, page, dest_point):
        """Specialized method for extracting bibliography entries
        
        FIXED: Now properly handles PDF coordinate conversion
        
        Bibliography entries typically have a specific format like:
        [6] Author Name. Title of Paper. Journal, Year.
        
        Args:
            page: fitz.Page object
            dest_point: (x, y) tuple in PDF coordinates (bottom-left origin)
            
        Returns:
            Full bibliography entry or None
        """
        try:
            pdf_x, pdf_y = dest_point
            
            # ✅ FIX: Convert PDF Y coordinate to top-left origin for text extraction
            x = pdf_x
            y = page.rect.height - pdf_y
            
            # Get all text with positions
            text_dict = page.get_text("dict", sort=True)
            blocks = text_dict.get("blocks", [])
            
            for block in blocks:
                if block.get("type") != 0:
                    continue
                
                block_bbox = block.get("bbox")
                if not block_bbox:
                    continue
                
                bx0, by0, bx1, by1 = block_bbox
                
                # Check if this block is near the destination
                if not (bx0 - 30 <= x <= bx1 + 50 and by0 - 20 <= y <= by1 + 20):
                    continue
                
                # Extract all text from block
                lines = block.get("lines", [])
                block_text_lines = []
                
                for line in lines:
                    line_bbox = line.get("bbox")
                    if not line_bbox:
                        continue
                    
                    lx0, ly0, lx1, ly1 = line_bbox
                    
                    # Check if this line contains the destination point
                    line_contains_point = (lx0 - 30 <= x <= lx1 + 50 and 
                                          ly0 - 10 <= y <= ly1 + 10)
                    
                    # Extract line text
                    spans = line.get("spans", [])
                    line_text = ''.join(span.get("text", "") for span in spans)
                    line_text = line_text.strip()
                    
                    if line_contains_point:
                        # This line contains our point - start from here
                        block_text_lines = [line_text]
                        
                        # Get the next few lines for complete entry
                        line_idx = lines.index(line)
                        for next_line in lines[line_idx + 1:line_idx + 4]:
                            next_spans = next_line.get("spans", [])
                            next_text = ''.join(s.get("text", "") for s in next_spans).strip()
                            if next_text:
                                # Check if next line is continuation (indented or close)
                                next_bbox = next_line.get("bbox")
                                if next_bbox:
                                    next_x0 = next_bbox[0]
                                    # If next line starts near or after current line's x, it's continuation
                                    if next_x0 >= lx0 - 20:
                                        block_text_lines.append(next_text)
                                    else:
                                        # New entry started
                                        break
                        break
                    elif block_text_lines:
                        # We already started extracting - add this line
                        if line_text:
                            block_text_lines.append(line_text)
                
                if block_text_lines:
                    # Found the entry
                    entry_text = ' '.join(block_text_lines)
                    
                    # Clean up common bibliography patterns
                    entry_text = entry_text.strip()
                    
                    return self._format_preview_text(entry_text, max_chars=300)
        
        except Exception as e:
            print(f"Bibliography extraction failed: {e}")
        
        return None
    
    
        
    # Additional helper method for PDFViewer class
    # def preserve_expand_state_during_layout_change(self):
        # """Helper method to preserve expand state during layout changes"""
        # if hasattr(self, 'is_expanded') and self.is_expanded:
            # # Store state in layout manager for persistence
            # if hasattr(self.main_window, 'layout_manager'):
                # self.main_window.layout_manager._pdf_expanded = True
                
                # # Find current editor index
                # if hasattr(self.main_window, 'main_splitter'):
                    # splitter = self.main_window.main_splitter
                    # for i in range(splitter.count()):
                        # widget = splitter.widget(i)
                        # if widget and not self._widget_contains_pdf_viewer(widget):
                            # # This is likely the editor container
                            # if hasattr(widget, '__class__') and 'SidePanel' not in widget.__class__.__name__:
                                # self.main_window.layout_manager._pdf_expanded_editor_index = i
                                # break    


    def toggle_select_mode(self):
        """Toggle between Pan mode and Select mode"""
        self.select_mode = self.select_mode_btn.isChecked()
        self.pan_mode = not self.select_mode
        
        # ✅ NEW: Disable reverse search mode when entering select mode
        if self.select_mode and self.reverse_search_mode:
            self.reverse_search_mode = False
            # Update reverse search button if it exists
            if hasattr(self, 'synctex_btn'):
                self.synctex_btn.setChecked(False)
                self.synctex_btn.setStyleSheet("")
        
        if self.select_mode:
            # Select mode active
            self.select_mode_btn.setStyleSheet("background-color: #2196F3;")  # Blue highlight
            self.content_widget.setCursor(Qt.IBeamCursor)  # Text cursor
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Select Mode: Click and drag to select text", 2000)
        else:
            # Pan mode active (default)
            self.select_mode_btn.setStyleSheet("")
            self.content_widget.setCursor(Qt.OpenHandCursor)  # Open hand cursor
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Pan Mode: Click and drag to move the page", 2000)
        
        # Update cursor on all page labels
        for label in self.page_labels:
            if self.select_mode:
                label.setCursor(Qt.IBeamCursor)
            else:
                label.setCursor(Qt.OpenHandCursor)
            
                                
    def toggle_expand_width(self):
        """Toggle PDF viewer between normal and expanded width - FIXED VERSION"""
        #print(f"FIXED: Starting toggle_expand_width, is_expanded: {getattr(self, 'is_expanded', False)}")
        
        if not hasattr(self.main_window, 'main_splitter'):
            print("ERROR: main_window.main_splitter not found")
            return

        try:
            splitter = self.main_window.main_splitter
            #print(f"FIXED: Splitter found, widget count: {splitter.count()}")
            #print(f"FIXED: Current splitter sizes: {splitter.sizes()}")

            # Initialize expanded state if not exists
            if not hasattr(self, 'is_expanded'):
                self.is_expanded = False

            # Detect which widget contains the PDF viewer and which contains the editor
            pdf_widget_index = -1
            editor_widget_index = -1
            side_panel_index = -1
            
            for i in range(splitter.count()):
                widget = splitter.widget(i)
                if widget:
                    # Check for side panel
                    if hasattr(widget, '__class__') and 'SidePanel' in widget.__class__.__name__:
                        side_panel_index = i
                        print(f"FIXED: Side panel found at index {i}")
                    # Check for PDF viewer
                    elif self._widget_contains_pdf_viewer(widget):
                        pdf_widget_index = i
                        print(f"FIXED: PDF viewer found at index {i}")
                    # Everything else is editor
                    else:
                        editor_widget_index = i
                        print(f"FIXED: Editor found at index {i}")

            if pdf_widget_index == -1:
                print("ERROR: Could not detect PDF viewer position")
                return

            if not self.is_expanded:
                # EXPAND: Hide editor, expand PDF viewer
                print("FIXED: Expanding PDF viewer...")
                self.is_expanded = True

                # Store current sizes for restoration
                if not hasattr(self, 'original_sizes'):
                    self.original_sizes = splitter.sizes().copy()
                    print(f"FIXED: Stored original sizes: {self.original_sizes}")

                # Store expanded state in main window for persistence
                if hasattr(self.main_window, 'layout_manager'):
                    self.main_window.layout_manager._pdf_expanded = True
                    self.main_window.layout_manager._pdf_expanded_editor_index = editor_widget_index

                # Get total available width
                total_width = sum(splitter.sizes())
                
                # Calculate new sizes
                new_sizes = [0] * splitter.count()
                
                # Keep side panel visible if it exists
                if side_panel_index != -1:
                    side_panel_widget = splitter.widget(side_panel_index)
                    if side_panel_widget and side_panel_widget.isVisible():
                        new_sizes[side_panel_index] = self.original_sizes[side_panel_index]
                        total_width -= new_sizes[side_panel_index]

                # Hide editor completely
                if editor_widget_index != -1:
                    new_sizes[editor_widget_index] = 0
                    editor_widget = splitter.widget(editor_widget_index)
                    if editor_widget:
                        # AGGRESSIVE hiding methods
                        editor_widget.setMaximumWidth(0)
                        editor_widget.hide()
                        self._deep_constraint_removal(editor_widget)

                # Give all remaining space to PDF
                new_sizes[pdf_widget_index] = total_width

                print(f"FIXED: Setting expand sizes to: {new_sizes}")
                splitter.setSizes(new_sizes)

                # Update button icon
                self.main_window.icons_manager.apply_icon_to_button(self.expand_btn, "collapse_width")
                self.expand_btn.setToolTip("Restore normal width")

            else:
                # COLLAPSE: Restore original layout
                print("FIXED: Collapsing to original state...")
                self.is_expanded = False

                # Clear expanded state from layout manager
                if hasattr(self.main_window, 'layout_manager'):
                    if hasattr(self.main_window.layout_manager, '_pdf_expanded'):
                        delattr(self.main_window.layout_manager, '_pdf_expanded')
                    if hasattr(self.main_window.layout_manager, '_pdf_expanded_editor_index'):
                        delattr(self.main_window.layout_manager, '_pdf_expanded_editor_index')

                # Restore editor widget visibility
                if editor_widget_index != -1:
                    editor_widget = splitter.widget(editor_widget_index)
                    if editor_widget:
                        editor_widget.show()
                        editor_widget.setMaximumWidth(16777215)  # Reset to default max
                        # Restore minimum size constraints
                        editor_widget.setMinimumSize(300, 200)

                # Restore original sizes
                if hasattr(self, 'original_sizes'):
                    print(f"FIXED: Restoring to: {self.original_sizes}")
                    splitter.setSizes(self.original_sizes)

                # Update button icon
                self.main_window.icons_manager.apply_icon_to_button(self.expand_btn, "expand_width")
                self.expand_btn.setToolTip("Expand to full width")

            # Force layout update
            splitter.update()
            QApplication.processEvents()
            
            print(f"FIXED: Final result: {splitter.sizes()}")

        except Exception as e:
            print(f"FIXED: Error in toggle_expand_width: {e}")
            import traceback
            traceback.print_exc()

    def _widget_contains_pdf_viewer(self, widget):
        """Check if a widget contains a PDF viewer (this instance or another)"""
        # Check if this widget IS a PDF viewer
        if isinstance(widget, PDFViewer):
            return True
        
        # Check if this widget contains PDF viewer in its hierarchy
        pdf_viewers = widget.findChildren(PDFViewer)
        if pdf_viewers:
            return True
        
        # Check for QTabWidget containing PDF viewers
        if hasattr(widget, 'count') and hasattr(widget, 'widget'):
            for i in range(widget.count()):
                child = widget.widget(i)
                if child and isinstance(child, PDFViewer):
                    return True
                # Recursive check for nested containers
                if child and self._widget_contains_pdf_viewer(child):
                    return True
        
        # Check layouts
        if hasattr(widget, 'layout') and widget.layout():
            layout = widget.layout()
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    if isinstance(item.widget(), PDFViewer):
                        return True
                    if self._widget_contains_pdf_viewer(item.widget()):
                        return True
        
        return False

    def _deep_constraint_removal(self, widget):
        """Aggressively remove ALL minimum size constraints"""
        from PyQt5.QtWidgets import QWidget
        
        try:
            # Remove from this widget
            widget.setMinimumSize(0, 0)
            print(f"  - Removed constraints from {type(widget).__name__}")
            
            # Get ALL child widgets recursively
            all_children = widget.findChildren(QWidget)
            print(f"  - Found {len(all_children)} child widgets")
            
            # Remove constraints from every single child
            for child in all_children:
                child.setMinimumSize(0, 0)
                
        except Exception as e:
            print(f"  - Error in constraint removal: {e}")

    # def _store_original_min_sizes(self, splitter):
        # """Store original minimum sizes of splitter widgets"""
        # if not hasattr(self, 'original_min_sizes'):
            # self.original_min_sizes = {}
            
        # for i in range(splitter.count()):
            # widget = splitter.widget(i)
            # if widget:
                # self.original_min_sizes[i] = widget.minimumSize()
                # # Also check for nested tab widgets or containers
                # self._store_nested_min_sizes(widget, f"widget_{i}")

    def _store_nested_min_sizes(self, widget, prefix):
        """Recursively store minimum sizes of nested widgets"""
        if not hasattr(self, 'nested_min_sizes'):
            self.nested_min_sizes = {}
            
        # Store this widget's min size
        self.nested_min_sizes[prefix] = widget.minimumSize()
        
        # Check for common container types
        if hasattr(widget, 'widget') and widget.widget():  # QScrollArea, etc.
            self.nested_min_sizes[f"{prefix}_content"] = widget.widget().minimumSize()
            
        # Check for tab widgets
        if hasattr(widget, 'count'):  # QTabWidget
            for i in range(widget.count()):
                tab = widget.widget(i)
                if tab:
                    self.nested_min_sizes[f"{prefix}_tab_{i}"] = tab.minimumSize()

    # def _remove_min_size_constraints(self, splitter):
        # """Temporarily remove minimum size constraints for expansion"""
        # for i in range(splitter.count()):
            # widget = splitter.widget(i)
            # if widget:
                # # Set minimum size to 0 for the editor side (left side, index 0)
                # if i == 0:  # Editor side
                    # widget.setMinimumSize(0, 0)
                    # self._remove_nested_min_sizes(widget)

    def _remove_nested_min_sizes(self, widget):
        """Recursively remove minimum sizes of nested widgets"""
        # Remove min size for this widget
        widget.setMinimumSize(0, 0)
        
        # Check for common container types
        if hasattr(widget, 'widget') and widget.widget():  # QScrollArea, etc.
            widget.widget().setMinimumSize(0, 0)
            
        # Check for tab widgets
        if hasattr(widget, 'count'):  # QTabWidget
            for i in range(widget.count()):
                tab = widget.widget(i)
                if tab:
                    tab.setMinimumSize(0, 0)

    # def _restore_original_min_sizes(self, splitter):
        # """Restore original minimum sizes"""
        # if hasattr(self, 'original_min_sizes'):
            # for i, min_size in self.original_min_sizes.items():
                # widget = splitter.widget(i)
                # if widget:
                    # widget.setMinimumSize(min_size)
        
        # # Restore nested minimum sizes
        # if hasattr(self, 'nested_min_sizes'):
            # self._restore_nested_min_sizes(splitter)

    def _restore_nested_min_sizes(self, splitter):
        """Restore nested minimum sizes"""
        for i in range(splitter.count()):
            widget = splitter.widget(i)
            if widget:
                prefix = f"widget_{i}"
                
                # Restore main widget
                if prefix in self.nested_min_sizes:
                    widget.setMinimumSize(self.nested_min_sizes[prefix])
                
                # Restore content widget
                content_key = f"{prefix}_content"
                if content_key in self.nested_min_sizes and hasattr(widget, 'widget') and widget.widget():
                    widget.widget().setMinimumSize(self.nested_min_sizes[content_key])
                
                # Restore tab widgets
                if hasattr(widget, 'count'):  # QTabWidget
                    for j in range(widget.count()):
                        tab = widget.widget(j)
                        tab_key = f"{prefix}_tab_{j}"
                        if tab and tab_key in self.nested_min_sizes:
                            tab.setMinimumSize(self.nested_min_sizes[tab_key])

    def set_zoom_from_spinbox(self, percentage):
        """Set zoom factor from spinbox percentage value"""
        if self.pdf_document:  # Only update if PDF is loaded
            self.zoom_factor = percentage / 100.0
            self.render_all_pages()
        
    # def create_pdf_wrapper(self, viewer, pdf_path):
        # """Create wrapper widget for PDF viewer in splitter mode
        # use_header=False when viewer is inside a QTabWidget"""
        # from PyQt5.QtWidgets import QLabel, QSizePolicy, QPushButton
        # from PyQt5.QtGui import QFont
        # from PyQt5.QtCore import Qt

        # wrapper = QWidget()
        # wrapper_layout = QVBoxLayout(wrapper)
        # wrapper_layout.setContentsMargins(0, 0, 0, 0)
        # wrapper_layout.setSpacing(2)


        # # Add viewer
        # viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # viewer.setMinimumSize(200, 200)
        # wrapper_layout.addWidget(viewer, 1)

        # wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # wrapper.setMinimumSize(250, 250)

        # return wrapper

    # def close_pdf_handler(self, pdf_path):
        # """Handle closing of PDF"""
        # # Implement this based on how your main window handles PDF closing
        # if hasattr(self.main_window, 'pdf_manager'):
            # # Try different possible methods
            # if hasattr(self.main_window.pdf_manager, 'close_pdf'):
                # self.main_window.pdf_manager.close_pdf(pdf_path)
            # elif hasattr(self.main_window.pdf_manager, 'remove_pdf'):
                # self.main_window.pdf_manager.remove_pdf(pdf_path)
            # elif hasattr(self.main_window.pdf_manager, 'close_pdf_viewer'):
                # self.main_window.pdf_manager.close_pdf_viewer(pdf_path)
        # else:
            # print(f"Would close PDF: {pdf_path}")    
    
    def close_pdf(self, pdf_path):
        """Close the PDF (implement this method according to your needs)"""
        # You'll need to implement this based on how your main window handles PDF closing
        if hasattr(self.main_window, 'pdf_manager'):
            self.main_window.pdf_manager.close_pdf(pdf_path)
        
       

    def toggle_reverse_search_mode(self):
        """Toggle reverse search mode"""
        self.reverse_search_mode = not self.reverse_search_mode
        
        # ✅ NEW: Disable select mode when entering reverse search mode
        if self.reverse_search_mode and self.select_mode:
            self.select_mode = False
            self.pan_mode = True
            self.select_mode_btn.setChecked(False)
            self.select_mode_btn.setStyleSheet("")
        
        # Update cursor for content widget and all page labels
        if self.reverse_search_mode:
            cursor = Qt.CrossCursor  # "+" cursor
            # ✅ NEW: Visual feedback for active reverse search mode
            if hasattr(self, 'synctex_btn'):
                self.synctex_btn.setStyleSheet("background-color: #FF9800;")  # Orange highlight
            # Update status
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(
                    "Reverse Search Mode: Click on PDF to jump to source", 3000
                )
        elif self.select_mode:
            cursor = Qt.IBeamCursor  # Text selection cursor
            if hasattr(self, 'synctex_btn'):
                self.synctex_btn.setStyleSheet("")
        elif self.pan_mode:
            cursor = Qt.OpenHandCursor  # Hand cursor
            if hasattr(self, 'synctex_btn'):
                self.synctex_btn.setStyleSheet("")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Pan Mode: Click and drag to move the page", 2000)
        else:
            cursor = Qt.ArrowCursor  # Default arrow
            if hasattr(self, 'synctex_btn'):
                self.synctex_btn.setStyleSheet("")
        
        # Apply cursor to content widget
        self.content_widget.setCursor(cursor)
        
        # Apply cursor to all page labels
        for label in self.page_labels:
            label.setCursor(cursor)
        
            
    
    def wheel_event(self, event):
        """Handle mouse wheel for zooming"""
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            QScrollArea.wheelEvent(self.scroll_area, event)
    
    def clear_pages(self):
        """Clear all page widgets"""
        if not self.is_valid:
            return
            
        try:
            # Remove page labels from parent and clear list
            for page_label in self.page_labels:
                if page_label and page_label.parent():
                    page_label.setParent(None)
            self.page_labels.clear()
            
            # Safely remove all widgets from layout
            while self.content_layout.count() > 0:
                item = self.content_layout.takeAt(0)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e):
                pass  # Object already deleted, that's okay
            else:
                raise e
        except Exception as e:
            pass  # Silently ignore errors during cleanup

    def show_error(self, message):
        """Show error message"""
        if not self.is_valid:
            return
            
        try:
            self.clear_pages()
            error_label = QLabel(message)
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 50px;")
            self.content_layout.addWidget(error_label)
            self.total_pages = 0
            self.current_page = 0
            self.update_page_controls()
            
            # ✅ ADD THIS - Disable external viewer button when no PDF
            if hasattr(self, 'open_external_btn'):
                self.open_external_btn.setEnabled(False)            
        except Exception as e:
            pass  # Silently ignore errors
            

    def render_all_pages(self):
        """Render all PDF pages, optionally in a grid layout"""
        if not self.is_valid:
            return
        try:
            # Clear existing page labels
            for label in self.page_labels:
                label.deleteLater()
            self.page_labels.clear()

            # Clear ALL widgets from content layout (including row containers)
            while self.content_layout.count() > 0:
                item = self.content_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()

            if not self.pdf_document:
                return

            ppl = getattr(self, 'pages_per_line', 1)

            for row_start in range(0, self.total_pages, ppl):
                # Create a row container when displaying multiple pages per line
                if ppl > 1:
                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setAlignment(Qt.AlignCenter)
                    row_layout.setSpacing(self.page_spacing)
                    row_layout.setContentsMargins(0, 0, 0, 0)

                for col in range(ppl):
                    page_num = row_start + col
                    if page_num >= self.total_pages:
                        break

                    page = self.pdf_document[page_num]

                    # Render page to pixmap
                    mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("ppm")
                    qpixmap = QPixmap()
                    qpixmap.loadFromData(img_data)

                    # Extract hyperlinks
                    links = self._extract_page_links(page, self.zoom_factor)

                    # Create label
                    page_label = SelectablePageLabel(page_num, self, links=links)
                    page_label.setPixmap(qpixmap)
                    page_label.setAlignment(Qt.AlignCenter)
                    self.page_labels.append(page_label)

                    if ppl > 1:
                        row_layout.addWidget(page_label)
                    else:
                        self.content_layout.addWidget(page_label)

                if ppl > 1:
                    self.content_layout.addWidget(row_widget)

            #print(f"✅ Rendered {len(self.page_labels)} pages "
            #      f"({ppl} per line)\n")
            self.update_page_controls()
        except Exception as e:
            print(f"❌ Error rendering pages: {e}")
            import traceback
            traceback.print_exc()

    def _extract_page_links(self, page, zoom_factor):
        """Extract all hyperlinks from a PDF page - ENHANCED VERSION
        
        Args:
            page: fitz.Page object
            zoom_factor: Current zoom level
            
        Returns:
            List of dicts: [{'rect': QRect, 'dest': destination, 'type': 'goto'/'uri'/'named', 'dest_page': int, 'dest_point': tuple}]
        """
        links = []
        
        try:
            # Get all links from the page using get_links()
            link_list = page.get_links()
            
            #print(f"    Raw links from get_links(): {len(link_list)}")
            
            for link in link_list:
                # Get link rectangle (coordinates in PDF space)
                rect = link.get('from')  # Note: it's 'from', not 'rect' in newer PyMuPDF
                if not rect:
                    rect = link.get('rect')  # Fallback for older versions
                
                if not rect:
                    continue
                
                # Handle both Rect object and tuple
                if hasattr(rect, 'x0'):
                    x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                else:
                    x0, y0, x1, y1 = rect[0], rect[1], rect[2], rect[3]
                
                # Scale rectangle to match current zoom
                # NOTE: Link rectangles from get_links() are already in top-left origin
                # so we just need to scale them
                scaled_rect = QRect(
                    int(x0 * zoom_factor),
                    int(y0 * zoom_factor),
                    int((x1 - x0) * zoom_factor),
                    int((y1 - y0) * zoom_factor)
                )
                
                link_info = {
                    'rect': scaled_rect,
                    'type': None,
                    'dest': None,
                    'dest_page': None,
                    'dest_point': None,  # This will be in PDF coordinates (bottom-left origin)
                    'raw_link': link  # Store raw link for tooltip generation
                }
                
                # Determine link type and destination
                kind = link.get('kind')
                
                if kind == fitz.LINK_GOTO or 'page' in link:
                    # Internal link to another page/location
                    link_info['type'] = 'goto'
                    link_info['dest_page'] = link.get('page', 0)
                    
                    # Get destination point if available
                    # This is in PDF coordinates (bottom-left origin)
                    if 'to' in link:
                        to_point = link['to']
                        if hasattr(to_point, 'x'):
                            link_info['dest_point'] = (to_point.x, to_point.y)
                        elif isinstance(to_point, (tuple, list)) and len(to_point) >= 2:
                            link_info['dest_point'] = (to_point[0], to_point[1])
                    
                    link_info['dest'] = link_info['dest_page']
                    
                elif kind == fitz.LINK_URI or 'uri' in link:
                    # External URL
                    link_info['type'] = 'uri'
                    link_info['dest'] = link.get('uri', '')
                    
                elif kind == fitz.LINK_NAMED or 'nameddest' in link:
                    # Named destination (often used for internal references)
                    link_info['type'] = 'named'
                    link_info['dest'] = link.get('nameddest') or link.get('name', '')
                    
                elif kind == fitz.LINK_GOTOR:
                    # Link to another PDF file
                    link_info['type'] = 'gotor'
                    link_info['dest'] = link.get('file', '') or link.get('fileSpec', '')
                    link_info['dest_page'] = link.get('page', 0)
                
                if link_info['type'] is not None:
                    links.append(link_info)
                    #print(f"      Extracted link: type={link_info['type']}, dest={link_info['dest']}, rect={scaled_rect}")
            
            # Also try to extract annotations that might be links
            annots = page.annots()
            if annots:
                for annot in annots:
                    if annot.type[0] == fitz.PDF_ANNOT_LINK:
                        rect = annot.rect
                        scaled_rect = QRect(
                            int(rect.x0 * zoom_factor),
                            int(rect.y0 * zoom_factor),
                            int((rect.x1 - rect.x0) * zoom_factor),
                            int((rect.y1 - rect.y0) * zoom_factor)
                        )
                        
                        # Check if this link is already in our list
                        is_duplicate = any(
                            abs(l['rect'].x() - scaled_rect.x()) < 5 and 
                            abs(l['rect'].y() - scaled_rect.y()) < 5 
                            for l in links
                        )
                        
                        if not is_duplicate:
                            link_info = {
                                'rect': scaled_rect,
                                'type': 'annot',
                                'dest': annot.info.get('title', 'Link'),
                                'dest_page': None,
                                'dest_point': None,
                                'raw_link': None
                            }
                            links.append(link_info)
        
        except Exception as e:
            print(f"Error extracting links from page: {e}")
            import traceback
            traceback.print_exc()
        
        return links
    


    def scroll_to_page_with_offset(self, page_index, dest_point=None):
        """Scroll to specific page with optional vertical offset - FIXED VERSION
        
        This method now properly converts PDF coordinates (bottom-left origin)
        to widget coordinates (top-left origin) before scrolling.
        
        Args:
            page_index: 0-indexed page number
            dest_point: Optional (x, y) in PDF coordinates (bottom-left origin, points)
        """
        if 0 <= page_index < len(self.page_labels):
            page_widget = self.page_labels[page_index]
            
            if dest_point and self.pdf_document:
                # ✅ FIX: Properly convert PDF coordinates to widget coordinates
                pdf_x, pdf_y = dest_point
                page = self.pdf_document[page_index]
                
                # Convert PDF Y (bottom-left origin) to widget Y (top-left origin)
                widget_y = self.pdf_point_to_widget_y(page, pdf_y)
                
                # Calculate the absolute position in the scroll area
                page_pos = page_widget.y()
                target_y = page_pos + int(widget_y)
                
                # Scroll with some margin from top (50 pixels offset for visibility)
                margin = 50
                final_scroll_y = max(0, target_y - margin)
                
                self.scroll_area.verticalScrollBar().setValue(final_scroll_y)
            else:
                # No dest_point - scroll to top of page
                page_pos = page_widget.y()
                self.scroll_area.verticalScrollBar().setValue(page_pos)
            
            self.current_page = page_index
            self.update_page_controls()
        

    def _resolve_named_dest(self, named_dest):
        """Resolve a named destination to a page number
        
        Args:
            named_dest: String name of the destination
            
        Returns:
            Page number (int) or None if not found
        """
        if not self.pdf_document:
            return None
        
        try:
            # Method 1: Try to resolve using PyMuPDF's built-in method
            if hasattr(self.pdf_document, 'resolve_link'):
                try:
                    # Some versions of PyMuPDF have this method
                    link_dest = self.pdf_document.resolve_link(f"#{named_dest}")
                    if link_dest and hasattr(link_dest, 'page'):
                        return link_dest.page
                except:
                    pass
            
            # Method 2: Check the PDF's name dictionary
            try:
                # Get the PDF catalog
                catalog = self.pdf_document.pdf_catalog()
                if catalog:
                    # Try to find named destinations
                    names = self.pdf_document.xref_get_key(catalog, "Names")
                    if names:
                        # This is complex - named destinations can be nested
                        pass
            except:
                pass
            
            # Method 3: Search through table of contents
            toc = self.pdf_document.get_toc()
            for entry in toc:
                # TOC entry format: [level, title, page_num, dest]
                if len(entry) >= 3:
                    title = str(entry[1]).lower()
                    page_num = entry[2] - 1  # Convert to 0-indexed
                    
                    # Check for match
                    named_lower = named_dest.lower()
                    if named_lower in title or title in named_lower:
                        return page_num
                    
                    # Also check if the named_dest matches common patterns
                    # like "cite.author2020" or "eq:equation1"
                    if len(entry) > 3 and entry[3]:
                        dest_name = str(entry[3]).lower()
                        if named_lower in dest_name:
                            return page_num
            
            # Method 4: Try direct page number extraction from name
            # Some named dests are like "page.5" or "cite.p10"
            import re
            page_match = re.search(r'(?:page|p)\.?(\d+)', named_dest.lower())
            if page_match:
                page_num = int(page_match.group(1)) - 1
                if 0 <= page_num < self.total_pages:
                    return page_num
            
            return None
            
        except Exception as e:
            print(f"Error resolving named destination '{named_dest}': {e}")
            return None
        


    def go_to_page_number(self, page_num):
        """Jump to a specific page number (1-indexed from spinbox)"""
        if not self.is_valid or not self.pdf_document:
            return
        # Convert from 1-indexed (display) to 0-indexed (internal)
        page_index = page_num - 1
        if 0 <= page_index < self.total_pages:
            self.current_page = page_index
            # Scroll to the page
            if page_index < len(self.page_labels):
                label = self.page_labels[page_index]
                # Scroll the page into view
                self.scroll_area.ensureWidgetVisible(
                    label, 
                    0,  # Horizontal margin
                    50  # Vertical margin (offset from top)
                )
            self.update_page_controls()
        
        
    
    def load_pdf(self, pdf_path):
        """Load PDF file - DEBUGGED VERSION"""
        if not self.is_valid:
            #print("❌ PDF Viewer is not valid")
            return False
        
        try:
           
            if self.pdf_document:
                self.pdf_document.close()
                
            # ✅ NEW: Clear navigation history when loading new PDF
            self.navigation_history.clear()
            self.history_index = -1
            self._update_history_buttons()
    
            
            self.pdf_document = fitz.open(pdf_path)
            self.current_pdf_path = pdf_path
            self.total_pages = len(self.pdf_document)
            self.current_page = 0
            
            #print(f"✅ PDF loaded: {self.total_pages} pages")
            
            # Check if content_layout exists
            if not hasattr(self, 'content_layout') or self.content_layout is None:
                #print("❌ ERROR: content_layout is None!")
                return False
            
            #print(f"✅ content_layout exists: {type(self.content_layout).__name__}")
            
            self.render_all_pages()
            self.update_page_controls()
            # ✅ NEW: Load table of contents
            self.load_toc()
            
            # ✅ IMPROVED: Aggressive focus setting
            self.setFocus(Qt.OtherFocusReason)
            self.scroll_area.setFocus(Qt.OtherFocusReason)
            self.content_widget.setFocus(Qt.OtherFocusReason)
            
            # Raise and activate
            self.raise_()
            self.activateWindow()
            
            # Track that we just loaded (for shortcut fallback)
            from time import time
            self._last_click_time = time()
            
          
            # ✅ Run structure analysis AFTER loading PDF
            #QTimer.singleShot(1000, self.analyze_structure)
            
            # ✅ Enable external viewer button when PDF is loaded
            if hasattr(self, 'open_external_btn'):
                self.open_external_btn.setEnabled(True)
            
            # ✅ Add initial position to history after rendering
            QTimer.singleShot(100, self._initialize_history)
            
            
            #print(f"✅ PDF load complete\n")
            
            #QTimer.singleShot(500, self.debug_pdf_links)
            return True
            
        except Exception as e:
            print(f"❌ Error loading PDF: {e}")
            import traceback
            traceback.print_exc()
            self.show_error(f"Error loading PDF: {str(e)}")
            return False
            
    # def _initialize_history(self):
        # """Initialize navigation history with the starting position"""
        # if self.pdf_document and not self.navigation_history:
            # # Add initial position (page 0, scroll position 0)
            # initial_scroll = self.scroll_area.verticalScrollBar().value()
            # self.navigation_history.append((0, initial_scroll))
            # self.history_index = 0
            # self._update_history_buttons()
            # #print(f"📚 Initialized history with starting position: page 1, scroll {initial_scroll}")

    def _initialize_history(self):
        """Initialize navigation history with the starting position"""
        # Safely check if the document is open and valid
        try:
            if self.pdf_document is not None and len(self.pdf_document) > 0 and not self.navigation_history:
                # Add initial position (page 0, scroll position 0)
                initial_scroll = self.scroll_area.verticalScrollBar().value()
                self.navigation_history.append((0, initial_scroll))
                self.history_index = 0
                self._update_history_buttons()
        except ValueError as e:
            if str(e) == 'document closed':
                # Document is closed – reset reference and ignore
                self.pdf_document = None
            else:
                # Re-raise unexpected errors
                raise            
        
    def perform_reverse_search(self, page_num, x, y):
        """Perform reverse search using SyncTeX"""
        if not self.synctex_available:
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar("SyncTeX not installed or not available")
            return

        if not self.current_pdf_path:
            return

        try:
            pdf_dir = os.path.dirname(self.current_pdf_path)
            pdf_name = os.path.splitext(os.path.basename(self.current_pdf_path))[0]

            synctex_file = os.path.join(pdf_dir, pdf_name + ".synctex.gz")
            if not os.path.exists(synctex_file):
                if hasattr(self.main_window, 'update_status_bar'):
                    self.main_window.update_status_bar(
                        f"SyncTeX file not found. Compile with -synctex=1 option."
                    )
                return

            pdf_x = x / self.zoom_factor
            pdf_y = y / self.zoom_factor

            command = [
                'synctex', 'edit',
                '-o', f"{page_num + 1}:{pdf_x}:{pdf_y}:{self.current_pdf_path}"
            ]

            # ── Suppress console window on Windows ──
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 10,
                'cwd': pdf_dir
            }
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = si
            # ─────────────────────────────────────────

            result = subprocess.run(command, **kwargs)

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    self.parse_synctex_output(output)
                else:
                    if hasattr(self.main_window, 'update_status_bar'):
                        self.main_window.update_status_bar(
                            "No source location found at this position")
            else:
                error_msg = result.stderr.strip()
                if hasattr(self.main_window, 'update_status_bar'):
                    self.main_window.update_status_bar(f"SyncTeX error: {error_msg}")

        except subprocess.TimeoutExpired:
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar("SyncTeX timed out")
        except FileNotFoundError:
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar("SyncTeX not installed")
        except Exception as e:
            import traceback
            traceback.print_exc()
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar(f"Reverse search error: {str(e)}")

    def parse_synctex_output(self, output):
        """Parse SyncTeX output and jump to source location - FIXED for H/V mode"""
        try:
            lines = output.strip().split('\n')
            tex_file = None
            line_num = None
            column_num = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('Input:'):
                    tex_file = line.split(':', 1)[1].strip()
                elif line.startswith('Line:'):
                    try:
                        line_num = int(line.split(':', 1)[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('Column:'):
                    try:
                        column_num = int(line.split(':', 1)[1].strip())
                    except (ValueError, IndexError):
                        pass
            
            if not tex_file or not line_num:
                if hasattr(self.main_window, 'update_status_bar'):
                    self.main_window.update_status_bar("Could not parse SyncTeX output")
                return
            
            # Normalize the file path
            tex_file = os.path.abspath(tex_file)
            
            # ✅ Check if file is already open (works for both tabbed and H/V modes)
            if hasattr(self.main_window, 'editor_manager'):
                editor_manager = self.main_window.editor_manager
                
                # Use the existing method to find if file is open
                existing_path = editor_manager._find_open_file(tex_file)
                
                if existing_path:
                    # ✅ File is already open - switch to it and jump to line
                    print(f"✅ File already open: {os.path.basename(existing_path)}")
                    
                    # Get the editor for this file
                    editor_data = editor_manager.editor_files.get(existing_path)
                    if editor_data:
                        editor = editor_data.get('editor')
                        
                        if editor:
                            # ✅ Switch to this file based on layout mode
                            if editor_manager.editor_layout_mode == "tabbed":
                                # Tabbed mode - switch tab
                                if isinstance(editor_manager.editor_tabs, QTabWidget):
                                    tab_index = editor_manager.editor_tabs.indexOf(editor)
                                    if tab_index != -1:
                                        editor_manager.editor_tabs.setCurrentIndex(tab_index)
                            else:
                                # H/V mode - update active tab widget index and switch
                                tab_widget_index = editor_data.get('tab_widget_index', 0)
                                editor_manager._active_tab_widget_index = tab_widget_index
                                
                                # Switch to the correct tab widget
                                if isinstance(editor_manager.editor_tabs, list):
                                    if 0 <= tab_widget_index < len(editor_manager.editor_tabs):
                                        tab_widget = editor_manager.editor_tabs[tab_widget_index]
                                        if tab_widget:
                                            tab_index = tab_widget.indexOf(editor)
                                            if tab_index != -1:
                                                tab_widget.setCurrentIndex(tab_index)
                            
                            # Update current file
                            editor_manager.current_file = existing_path
                            
                            # Focus the editor
                            editor.setFocus()
                            
                            # Jump to the line
                            self._jump_to_line_in_editor(editor, line_num, column_num)
                            
                            if hasattr(self.main_window, 'update_status_bar'):
                                self.main_window.update_status_bar(
                                    f"Jumped to {os.path.basename(tex_file)}:{line_num}"
                                )
                            
                            return
                
                # ✅ File is not open - open it normally
                print(f"📂 Opening new file: {os.path.basename(tex_file)}")
                editor_manager.open_specific_file(tex_file)
                
                # After opening, jump to the line
                if tex_file in editor_manager.editor_files:
                    editor_data = editor_manager.editor_files[tex_file]
                    editor = editor_data.get('editor')
                    if editor:
                        self._jump_to_line_in_editor(editor, line_num, column_num)
                        
                if hasattr(self.main_window, 'update_status_bar'):
                    self.main_window.update_status_bar(
                        f"Jumped to {os.path.basename(tex_file)}:{line_num}"
                    )
            
        except Exception as e:
            print(f"Error parsing SyncTeX output: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar(f"Error: {str(e)}")

    def _jump_to_line_in_editor(self, editor, line_num, column_num=None):
        """Helper to jump to a specific line in an editor"""
        try:
            from PyQt5.QtGui import QTextCursor
            
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            
            # Move to the target line
            for _ in range(line_num - 1):
                cursor.movePosition(QTextCursor.NextBlock)
            
            # Move to column if specified
            if column_num:
                cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, column_num - 1)
            
            # Set cursor and ensure visible
            editor.setTextCursor(cursor)
            editor.ensureCursorVisible()
            
            # Optional: Highlight the line briefly
            editor.centerCursor()
            
        except Exception as e:
            print(f"Error jumping to line: {e}")                            
##############
    def jump_to_synctex_location(self, page_index, x, y):
        """Jump to a specific location from SyncTeX forward search and highlight it
        
        Args:
            page_index: 0-indexed page number
            x: X coordinate in PDF points (from SyncTeX)
            y: Y coordinate in PDF points (from SyncTeX, measured from top)
        """
        if not self.pdf_document or page_index < 0 or page_index >= self.total_pages:
            return
        
        print(f"📍 Jumping to page {page_index + 1}, x={x}, y={y}")
        
        # Add to navigation history before jumping
        if not self.is_navigating_history:
            self._add_to_history()
        
        # Scroll to the page with the specific y offset
        self.scroll_to_page_with_synctex_highlight(page_index, x, y)
        
        # Update current page
        self.current_page = page_index
        self.update_page_controls()


    def scroll_to_page_with_synctex_highlight(self, page_index, x, y):
        """Scroll to page and highlight the SyncTeX target location
        
        Args:
            page_index: 0-indexed page number
            x: X coordinate in PDF points
            y: Y coordinate in PDF points (from top of page)
        """
        if page_index < 0 or page_index >= len(self.page_labels):
            return
        
        page_widget = self.page_labels[page_index]
        
        # Convert PDF coordinates to widget coordinates
        widget_x = int(x * self.zoom_factor)
        widget_y = int(y * self.zoom_factor)
        
        # Calculate scroll position
        page_pos = page_widget.y()
        target_scroll_y = page_pos + widget_y - 100  # 100px margin from top
        target_scroll_y = max(0, target_scroll_y)
        
        # Scroll to position
        self.scroll_area.verticalScrollBar().setValue(target_scroll_y)
        
        # Highlight the location
        self._highlight_synctex_target(page_index, widget_x, widget_y)


    def _highlight_synctex_target(self, page_index, widget_x, widget_y):
        """Draw a temporary highlight at the SyncTeX target location
        
        Args:
            page_index: 0-indexed page number  
            widget_x: X coordinate in widget pixels
            widget_y: Y coordinate in widget pixels
        """
        if page_index < 0 or page_index >= len(self.page_labels):
            return
        
        page_label = self.page_labels[page_index]
        
        # Create highlight overlay
        highlight_width = 700  # Width of highlight bar
        highlight_height = 80  # Height of highlight bar
        
        # Store original pixmap if not already stored
        if not hasattr(page_label, '_original_pixmap') or page_label._original_pixmap is None:
            page_label._original_pixmap = page_label.pixmap().copy()
        
        # Create a copy of the pixmap to draw on
        highlighted_pixmap = page_label._original_pixmap.copy()
        
        from PyQt5.QtGui import QPainter, QColor, QPen
        
        painter = QPainter(highlighted_pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw highlight rectangle (yellow with transparency)
            highlight_color = QColor(255, 255, 0, 100)  # Yellow, semi-transparent
            painter.fillRect(
                max(0, widget_x - 10),
                max(0, widget_y - highlight_height // 2),
                highlight_width,
                highlight_height,
                highlight_color
            )
            
            # Draw border
            border_color = QColor(255, 200, 0, 200)  # Orange border
            pen = QPen(border_color, 2)
            painter.setPen(pen)
            painter.drawRect(
                max(0, widget_x - 10),
                max(0, widget_y - highlight_height // 2),
                highlight_width,
                highlight_height
            )
            
            # Draw a small marker at the exact position
            marker_color = QColor(255, 0, 0, 200)  # Red marker
            painter.setBrush(marker_color)
            painter.setPen(QPen(Qt.black, 1))
            painter.drawEllipse(widget_x - 5, widget_y - 5, 10, 10)


        finally:
            painter.end()
        
        # Apply highlighted pixmap
        page_label.setPixmap(highlighted_pixmap)
        
        # Remove highlight after 2 seconds
        QTimer.singleShot(2000, lambda: self._remove_synctex_highlight(page_index))


    def _remove_synctex_highlight(self, page_index):
        """Remove the SyncTeX highlight and restore original pixmap
        
        Args:
            page_index: 0-indexed page number
        """
        if page_index < 0 or page_index >= len(self.page_labels):
            return
        
        page_label = self.page_labels[page_index]
        
        # Restore original pixmap if it exists
        if hasattr(page_label, '_original_pixmap') and page_label._original_pixmap is not None:
            page_label.setPixmap(page_label._original_pixmap)
            page_label._original_pixmap = None


    def _add_to_history(self):
        """Add current position to navigation history"""
        if self.is_navigating_history:
            return
        
        current_scroll = self.scroll_area.verticalScrollBar().value()
        current_position = (self.current_page, current_scroll)
        
        # Remove any forward history when adding new entry
        if self.history_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.history_index + 1]
        
        # Add new position
        self.navigation_history.append(current_position)
        
        # Limit history size
        if len(self.navigation_history) > self.max_history_size:
            self.navigation_history.pop(0)
        
        self.history_index = len(self.navigation_history) - 1
        self._update_history_buttons()


    # def jump_to_source_location(self, file_path, line_number):
        # """Jump to specific location in source file - improved version"""
        # if not self.main_window:
            # #print(f"Would jump to {file_path}:{line_number}")
            # return
        
        # try:
            # # Normalize the file path
            # file_path = os.path.normpath(os.path.abspath(file_path))
            
            # # Check if file exists
            # if not os.path.exists(file_path):
                # #print(f"Source file not found: {file_path}")
                # if hasattr(self.main_window, 'update_status_bar'):
                    # self.main_window.update_status_bar(f"Source file not found: {os.path.basename(file_path)}")
                # return
            
            # if not hasattr(self.main_window, 'editor_manager'):
                # #print("Editor manager not available")
                # return
            
            # editor_manager = self.main_window.editor_manager
            
            # # Open the file if not already open
            # current_file = editor_manager.get_current_file_path()
            # if current_file != file_path:
                # # Open the file
                # success = editor_manager.open_specific_file(file_path)
                # if not success:
                    # #print(f"Failed to open file: {file_path}")
                    # if hasattr(self.main_window, 'update_status_bar'):
                        # self.main_window.update_status_bar(f"Failed to open: {os.path.basename(file_path)}")
                    # return
            
            # # Get current editor
            # current_editor = editor_manager.get_current_editor()
            # if not current_editor:
                # #print("No editor available")
                # return
            
            # # Validate line number
            # line_count = current_editor.document().blockCount()
            # if line_number < 1:
                # line_number = 1
            # elif line_number > line_count:
                # line_number = line_count
            
            # # Jump to line using the same method as go_to_line
            # cursor = current_editor.textCursor()
            # cursor.movePosition(QTextCursor.Start)
            
            # # Move to target line efficiently
            # for _ in range(line_number - 1):
                # cursor.movePosition(QTextCursor.NextBlock)
            
            # # Set cursor and ensure it's visible
            # current_editor.setTextCursor(cursor)
            # current_editor.ensureCursorVisible()
            
            # # Highlight the current line temporarily
            # self._highlight_synctex_line(current_editor, line_number)
            
            # # Focus the editor
            # current_editor.setFocus()
            
            # # Update status bar
            # if hasattr(self.main_window, 'update_status_bar'):
                # self.main_window.update_status_bar(
                    # f"SyncTeX: Jumped to line {line_number} in {os.path.basename(file_path)}"
                # )
            
            # #print(f"Successfully jumped to {file_path}:{line_number}")
            
        # except Exception as e:
            # print(f"Error jumping to source: {str(e)}")
            # import traceback
            # traceback.print_exc()
            
            # if hasattr(self.main_window, 'update_status_bar'):
                # self.main_window.update_status_bar(f"SyncTeX error: {str(e)}")
                
    def _highlight_synctex_line(self, editor, line_number):
        """Temporarily highlight the line that was jumped to"""
        try:
            from PyQt5.QtGui import QColor
            from PyQt5.QtWidgets import QTextEdit
            from PyQt5.QtCore import QTimer
            
            # Create a selection for the entire line
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            for _ in range(line_number - 1):
                cursor.movePosition(QTextCursor.NextBlock)
            
            # Select the entire line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            
            # Create extra selection for highlighting
            extra_selections = []
            selection = QTextEdit.ExtraSelection()
            
            # Yellow highlight color
            selection.format.setBackground(QColor(255, 255, 0, 80))  # Yellow with transparency
            selection.cursor = cursor
            extra_selections.append(selection)
            
            editor.setExtraSelections(extra_selections)
            
            # Clear highlight after 2 seconds
            QTimer.singleShot(2000, lambda: editor.setExtraSelections([]))
            
        except Exception as e:
            print(f"Error highlighting line: {e}")
    
    def update_page_controls(self):
        """Update page controls"""
        has_pdf = self.total_pages > 0
        if has_pdf:
            self.page_spinbox.setEnabled(True)
            self.page_spinbox.setMaximum(self.total_pages)
            self.page_spinbox.valueChanged.disconnect()
            self.page_spinbox.setValue(self.current_page + 1)
            self.page_spinbox.valueChanged.connect(self.go_to_page_number)
            self.total_pages_label.setText(str(self.total_pages))            
            at_first = self.current_page <= 0
            at_last = self.current_page >= self.total_pages - 1
            self.first_page_btn.setEnabled(not at_first)
            #self.prev_page_btn.setEnabled(not at_first)
            #self.next_page_btn.setEnabled(not at_last)
            self.last_page_btn.setEnabled(not at_last)                      
        else:
            self.page_spinbox.setEnabled(False)
            self.page_spinbox.setMinimum(1)
            self.page_spinbox.setMaximum(1)
            self.page_spinbox.setValue(1)
            self.total_pages_label.setText("0")
            self.first_page_btn.setEnabled(False)
            #self.prev_page_btn.setEnabled(False)
            #self.next_page_btn.setEnabled(False)
            self.last_page_btn.setEnabled(False)
    
    def scroll_to_page(self, page_index):
        """Scroll to specific page"""
        if 0 <= page_index < len(self.page_labels):
            page_widget = self.page_labels[page_index]
            page_pos = page_widget.y()
            self.scroll_area.verticalScrollBar().setValue(page_pos)
            self.current_page = page_index
            self.update_page_controls()
    
    def go_to_first_page(self):
        """Navigate to first page"""
        self.scroll_to_page(0)
        self._ensure_focus_after_action()
    
    # def go_to_previous_page(self):
        # """Navigate to previous page (5 pages back)"""
        # if self.current_page > 4:
            # self.scroll_to_page(self.current_page - 5)
        # else:
            # self.scroll_to_page(0)  # Go to first page if less than 5 pages back
        # self._ensure_focus_after_action()    

    # def go_to_next_page(self):
        # """Navigate to next page (5 pages forward)"""
        # if self.current_page < self.total_pages - 5:
            # self.scroll_to_page(self.current_page + 5)
        # else:
            # self.scroll_to_page(self.total_pages - 1)  # Go to last page if less than 5 pages forward
        # self._ensure_focus_after_action()
        
    def go_to_last_page(self):
        """Navigate to last page"""
        if self.total_pages > 0:
            self.scroll_to_page(self.total_pages - 1)
        self._ensure_focus_after_action()
    
    def zoom_in(self):
        """Increase zoom"""
        self.zoom_factor = min(self.zoom_factor * 1.2, 5.0)
        self.update_zoom_display()
        self.render_all_pages()
        self._ensure_focus_after_action()
    
    def zoom_out(self):
        """Decrease zoom"""
        self.zoom_factor = max(self.zoom_factor / 1.2, 0.1)
        self.update_zoom_display()
        self.render_all_pages()
        self._ensure_focus_after_action()
        
    def update_zoom_display(self):
        """Update zoom percentage in spinbox"""
        if hasattr(self, 'zoom_spinbox') and self.zoom_spinbox:
            percentage = int(self.zoom_factor * 100)
            # Temporarily disconnect signal to avoid recursion
            try:
                self.zoom_spinbox.valueChanged.disconnect()
            except:
                pass
            self.zoom_spinbox.setValue(percentage)
            try:
                self.zoom_spinbox.valueChanged.connect(self.set_zoom_from_spinbox)
            except:
                pass
        self._ensure_focus_after_action()
    
        
    def fit_page_width(self):
        """Fit PDF page width to viewer (supports grid view)"""
        if not self.pdf_document or len(self.pdf_document) == 0:
            return

        page = self.pdf_document[0]
        page_rect = page.rect

        # Total available width inside scroll area
        viewer_width = self.scroll_area.viewport().width()

        # Optional: subtract spacing/margins if you use layout spacing
        spacing = 10  # adjust if needed
        total_spacing = spacing * (self.pages_per_line - 1)

        available_width = viewer_width - total_spacing

        # Divide width per page in grid
        width_per_page = available_width / self.pages_per_line

        # Calculate zoom
        self.zoom_factor = width_per_page / page_rect.width

        # Remove text fit offset if exists
        if hasattr(self, 'text_fit_margin_offset'):
            delattr(self, 'text_fit_margin_offset')

        self.update_zoom_display()
        self.render_all_pages()

        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(
                f"Fit page width ({self.pages_per_line} per line): {self.zoom_factor * 100:.0f}%",
                2000
            )
 
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts including navigation"""
        #print(f"⌨️ PDFViewer.keyPressEvent: key={event.key()}, modifiers={event.modifiers()}")
    
        # Navigation history shortcuts (Alt+Left/Right)
        if event.modifiers() == Qt.AltModifier:
            if event.key() == Qt.Key_Left:
                print(f"⬅️ Alt+Left detected in PDF viewer keyPressEvent")
                self.navigate_back()
                event.accept()
                return
            elif event.key() == Qt.Key_Right:
                print(f"➡️ Alt+Right detected in PDF viewer keyPressEvent")
                self.navigate_forward()
                event.accept()
                return

        # ✅ E KEY - Edit selected text/freetext annotation
        if event.key() == Qt.Key_E:
            if (hasattr(self, 'annotation_toolbar_widget') and 
                self.annotation_toolbar_widget.isVisible() and
                self.annotation_tool == "select" and
                self.selected_annot_rect):
                if self.selected_annot_type == "Text":
                    self._edit_text_annotation(self.selected_annot_page, self.selected_annot_rect)
                    event.accept()
                    return
                elif self.selected_annot_type == "FreeText":
                    self._edit_freetext_annotation(self.selected_annot_page, self.selected_annot_rect)
                    event.accept()
                    return
                
        # ✅ DELETE KEY - Delete selected annotation
        if event.key() == Qt.Key_Delete:
            if (hasattr(self, 'annotation_toolbar_widget') and 
                self.annotation_toolbar_widget.isVisible() and
                self.selected_annot_rect):
                self._delete_selected_annotation()
                event.accept()
                return
        
        # ✅ ESCAPE - Close annotation toolbar or search
        if event.key() == Qt.Key_Escape:
            if hasattr(self, 'annotation_toolbar_widget') and self.annotation_toolbar_widget.isVisible():
                self._clear_annotation_tool()
                self._clear_annotation_selection()
                self.main_window.update_status_bar("Tool deselected")
                #self._update_annot_status("Tool deselected")
                event.accept()
                return
            if self.search_toolbar_visible:
                self.hide_search_toolbar()
                event.accept()
                return
                
        # Shift+F3 or Ctrl+Shift+G: Find previous
        if (event.key() == Qt.Key_F3 and event.modifiers() == Qt.ShiftModifier) or \
           (event.key() == Qt.Key_G and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier)):
            self.search_previous()
            event.accept()
            return

        # Escape: Hide search toolbar
        if event.key() == Qt.Key_Escape:
            if self.search_toolbar_visible:
                self.hide_search_toolbar()
                event.accept()
                return

        # Navigation history shortcuts (Alt+Left/Right)
        if event.modifiers() == Qt.AltModifier:
            if event.key() == Qt.Key_Left:
                self.navigate_back()
                event.accept()
                return
            elif event.key() == Qt.Key_Right:
                self.navigate_forward()
                event.accept()
                return

        # Zoom shortcuts
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
                self.zoom_in()
                event.accept()
                return
            elif event.key() == Qt.Key_Minus:
                self.zoom_out()
                event.accept()
                return
            elif event.key() == Qt.Key_0:
                self.zoom_factor = 1.0
                self.update_zoom_display()
                self.render_all_pages()
                event.accept()
                return
            elif event.key() == Qt.Key_Home:
                self.go_to_first_page()
                event.accept()
                return
            elif event.key() == Qt.Key_End:
                self.go_to_last_page()
                event.accept()
                return
            elif event.key() == Qt.Key_P:
                if hasattr(self, 'print_btn') and self.print_btn.isEnabled():
                    self.print_pdf()
                event.accept()
                return

        # ✅ Page navigation (no modifier)
        if event.key() == Qt.Key_PageUp:
            self.go_to_previous_page()
            event.accept()
            return
        elif event.key() == Qt.Key_PageDown:
            self.go_to_next_page()
            event.accept()
            return
        elif event.key() == Qt.Key_Home:
            self.go_to_first_page()
            event.accept()
            return
        elif event.key() == Qt.Key_End:
            self.go_to_last_page()
            event.accept()
            return

        # ✅ Arrow key scrolling
        if event.key() == Qt.Key_Up:
            # Scroll up by a small amount
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.value() - 50)
            event.accept()
            return
        elif event.key() == Qt.Key_Down:
            # Scroll down by a small amount
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.value() + 50)
            event.accept()
            return
        elif event.key() == Qt.Key_Left:
            # Scroll left
            scrollbar = self.scroll_area.horizontalScrollBar()
            scrollbar.setValue(scrollbar.value() - 50)
            event.accept()
            return
        elif event.key() == Qt.Key_Right:
            # Scroll right
            scrollbar = self.scroll_area.horizontalScrollBar()
            scrollbar.setValue(scrollbar.value() + 50)
            event.accept()
            return

        # ✅ Space bar: scroll down one viewport height (like Page Down)
        if event.key() == Qt.Key_Space:
            if event.modifiers() == Qt.ShiftModifier:
                # Shift+Space: scroll up
                scrollbar = self.scroll_area.verticalScrollBar()
                scrollbar.setValue(scrollbar.value() - self.scroll_area.viewport().height())
            else:
                # Space: scroll down
                scrollbar = self.scroll_area.verticalScrollBar()
                scrollbar.setValue(scrollbar.value() + self.scroll_area.viewport().height())
            event.accept()
            return

        # Let parent handle other keys
        super().keyPressEvent(event)
    

    def eventFilter(self, obj, event):
        """Filter events to maintain focus and handle edge cases"""
        if event.type() == QEvent.KeyPress:
            if event.modifiers() == Qt.AltModifier:
                if event.key() in [Qt.Key_Left, Qt.Key_Right]:
                    print(f"🔄 Tab widget calling viewer method directly")
                    # Call the method directly instead of forwarding event
                    if event.key() == Qt.Key_Left:
                        self.viewer.navigate_back()
                    else:
                        self.viewer.navigate_forward()
                    event.accept()
                    return True  # Consume event
        # Prevent focus loss when interacting with scrollbars
        if obj == self.scroll_area:
            if event.type() == event.FocusOut:
                # If focus is moving to a scrollbar, prevent it
                new_focus = QApplication.focusWidget()
                if new_focus and (new_focus == self.scroll_area.verticalScrollBar() or 
                                new_focus == self.scroll_area.horizontalScrollBar()):
                    # Keep focus on scroll area
                    QTimer.singleShot(0, lambda: self.scroll_area.setFocus(Qt.OtherFocusReason))
        
        return super().eventFilter(obj, event)
    
    def extract_selected_text(self):
        """Extract text from selected area"""
        if not self.pdf_document or not self.selection_rect:
            return
            
        try:
            # Find which page the selection is on
            page_num = self.get_page_from_position(self.selection_start)
            if page_num >= 0 and page_num < len(self.pdf_document):
                page = self.pdf_document[page_num]
                
                # Convert selection coordinates to PDF coordinates
                page_label = self.page_labels[page_num]
                page_rect = page_label.geometry()
                
                # Calculate relative position within the page
                rel_x1 = (self.selection_rect.x() - page_rect.x()) / self.zoom_factor
                rel_y1 = (self.selection_rect.y() - page_rect.y()) / self.zoom_factor
                rel_x2 = (self.selection_rect.right() - page_rect.x()) / self.zoom_factor
                rel_y2 = (self.selection_rect.bottom() - page_rect.y()) / self.zoom_factor
                
                # Create rectangle for text extraction
                fitz_rect = fitz.Rect(rel_x1, rel_y1, rel_x2, rel_y2)
                
                # Extract text from the selected area
                selected_text = page.get_text("text", clip=fitz_rect)
                
                if selected_text.strip():
                    # Copy to clipboard
                    clipboard = QApplication.clipboard()
                    clipboard.setText(selected_text)
                    
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
    
    def get_page_from_position(self, pos):
        """Get page number from position (pos in content_widget coordinates)"""
        for i, page_label in enumerate(self.page_labels):
            try:
                page_pos = page_label.mapTo(self.content_widget, QPoint(0, 0))
                page_rect = QRect(page_pos, page_label.size())
            except Exception:
                page_rect = page_label.geometry()
            if page_rect.contains(pos):
                return i
        return -1
    
    def closeEvent(self, event):
        """Handle widget closing"""
        try:
            if hasattr(self, 'pdf_document') and self.pdf_document:
                self.pdf_document.close()
        except:
            pass
        event.accept()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if hasattr(self, 'pdf_document') and self.pdf_document:
                self.pdf_document.close()
        except:
            pass
        
            
    def print_pdf(self):
        """Print the current PDF document"""
        if not self.pdf_document or not self.current_pdf_path:
            return
        
        if not PRINT_SUPPORT_AVAILABLE:
            # Fallback to system print when PyQt5 print support isn't available
            self._print_with_system_viewer()
            return
        
        try:
            # Create printer and print dialog
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Portrait)
            
            # Show print dialog
            print_dialog = QPrintDialog(printer, self)
            print_dialog.setWindowTitle("Print PDF")
            
            if print_dialog.exec_() == QPrintDialog.Accepted:
                self._print_to_printer(printer)
                
        except Exception as e:
            print(f"Print error: {e}")
            # Fallback: try to open with system default PDF viewer for printing
            self._print_with_system_viewer()
    
    def _print_to_printer(self, printer):
        """Print PDF pages to the specified printer"""
        if not PRINT_SUPPORT_AVAILABLE:
            return
        
        painter = QPainter(printer)    
        try:            
            if not painter.isActive():
                return
            
            # Get page range from printer settings
            from_page = printer.fromPage() if printer.fromPage() > 0 else 1
            to_page = printer.toPage() if printer.toPage() > 0 else self.total_pages
            
            # Ensure valid page range
            from_page = max(1, min(from_page, self.total_pages))
            to_page = max(from_page, min(to_page, self.total_pages))
            
            # Print each page
            for page_num in range(from_page - 1, to_page):  # Convert to 0-based index
                if page_num > from_page - 1:  # Not the first page
                    printer.newPage()
                
                # Get page as pixmap
                page = self.pdf_document[page_num]
                mat = fitz.Matrix(2.0, 2.0)  # Higher resolution for printing
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to QPixmap
                img_data = pix.tobytes("ppm")
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                
                # Scale to fit printer page
                printer_rect = printer.pageRect()
                scaled_pixmap = pixmap.scaled(
                    printer_rect.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                
                # Center on page
                x = (printer_rect.width() - scaled_pixmap.width()) // 2
                y = (printer_rect.height() - scaled_pixmap.height()) // 2
                
                painter.drawPixmap(x, y, scaled_pixmap)
            
            
            
        except Exception as e:
            print(f"Error during printing: {e}")
            painter.end()
            self._print_with_system_viewer()
        
        finally:
            painter.end()
    
    def _print_with_system_viewer(self):
        """Fallback: Open PDF with system default viewer for printing"""
        try:
            if os.name == 'nt':  # Windows
                # Try to open with print verb first
                try:
                    os.startfile(self.current_pdf_path, 'print')
                except:
                    # Fallback to regular open
                    os.startfile(self.current_pdf_path)
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Print", 
                        "PDF opened in default viewer. Use Ctrl+P to print from there.")
            elif os.name == 'posix':  # macOS and Linux
                if os.uname().sysname == 'Darwin':  # macOS
                    subprocess.run(['open', self.current_pdf_path])
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Print", 
                        "PDF opened in default viewer. Use Cmd+P to print from there.")
                else:  # Linux
                    subprocess.run(['xdg-open', self.current_pdf_path])
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Print", 
                        "PDF opened in default viewer. Use Ctrl+P to print from there.")
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Print Error",  f"Could not open PDF for printing: {e}")
    def open_in_external_viewer(self):
        """Open the current PDF file in the system's default PDF viewer"""
        if not self.current_pdf_path or not os.path.exists(self.current_pdf_path):
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("No PDF file to open", 2000)
            return
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.current_pdf_path)
                status_msg = f"Opened {os.path.basename(self.current_pdf_path)} in default viewer"
            elif os.name == 'posix':  # macOS and Linux
                if os.uname().sysname == 'Darwin':  # macOS
                    subprocess.run(['open', self.current_pdf_path])
                    status_msg = f"Opened {os.path.basename(self.current_pdf_path)} in default viewer"
                else:  # Linux
                    subprocess.run(['xdg-open', self.current_pdf_path])
                    status_msg = f"Opened {os.path.basename(self.current_pdf_path)} in default viewer"
            
            # Update status bar
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(status_msg, 3000)
                
        except Exception as e:
            # Show error message
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Cannot Open PDF", 
                f"Could not open PDF in external viewer:\n{str(e)}"
            )
        
    def set_magnifier_size(self, size):
        """Set the size of the magnifying glass (default: 200)"""
        self.magnifier_size = max(100, min(400, size))

    def set_magnifier_zoom(self, zoom):
        """Set the magnification factor (default: 2.0)"""
        self.magnifier_zoom = max(1.5, min(5.0, zoom))

    def set_magnifier_quality(self, quality_multiplier):
        """Set the quality multiplier for magnifier rendering (default: 2.0)
        Higher values = sharper but slower. Range: 1.0 to 4.0"""
        self.magnifier_quality_multiplier = max(1.0, min(4.0, quality_multiplier))


    # ═══════════════════════════════════════════════════════════════════════════════
    # NEW/MODIFIED SEARCH METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    def toggle_search_toolbar(self):
        """Toggle the search toolbar visibility"""
        if self.search_toolbar_visible:
            self.hide_search_toolbar()
        else:
            self.show_search_toolbar()
    def show_search_toolbar(self):
        """Show search toolbar and hide main toolbar - WITH TOC"""
        self.search_toolbar_visible = True
        
        # Hide main toolbar buttons
        self.main_toolbar_widget.setVisible(False)
        
        # Show search container
        self.search_container.setVisible(True)
        self.search_toggle_btn.setChecked(True)
        
        # Update toggle button styling to show active state
        self.search_toggle_btn.setStyleSheet("background-color: #4CAF50;")
        
        # ✅ NEW: Populate TOC combo when showing search toolbar
        self.populate_toc_combo()
        
        # Focus and select all text in search field
        self.search_field.setFocus()
        self.search_field.selectAll()
        
        # Status message
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(
                "Search mode active - Use dropdown to navigate sections (press Esc to exit)", 3000
            )
    def hide_search_toolbar(self):
        """Hide search toolbar and show main toolbar - EXIT SEARCH MODE"""
        self.search_toolbar_visible = False
        
        # ✅ SHOW main toolbar buttons
        self.main_toolbar_widget.setVisible(True)
        
        # ✅ HIDE search container
        self.search_container.setVisible(False)
        self.search_toggle_btn.setChecked(False)
        
        # ✅ Reset toggle button styling
        self.search_toggle_btn.setStyleSheet("")
        
        # Clear search
        self.clear_search()
        
        # Status message
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage("Search mode closed", 2000)
        
    def on_search_text_changed(self, text):
        """Handle search text changes - clear highlights when text changes"""
        if text != self.search_text:
            # Text changed, need to re-search
            self.all_results_highlighted = False
            # Clear old results
            if self.search_results:
                self.clear_search_highlights()
                self.search_results = []
                self.current_search_index = -1
                self.update_search_ui()
            
    def perform_search(self):
        """Search for text in the PDF and highlight ALL results"""
        search_text = self.search_field.text().strip()
        
        if not search_text:
            self.clear_search()
            return
        
        if not self.pdf_document:
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("No PDF loaded", 2000)
            return
        
        # Check if this is a new search
        is_new_search = (search_text != self.search_text)
        
        if is_new_search:
            # Clear previous search
            self.clear_search_highlights()
            self.search_results = []
            self.current_search_index = -1
            self.search_text = search_text
            self.all_results_highlighted = False
            
            # Search through all pages
            #print(f"🔍 Searching for: '{search_text}'")
            
            for page_num in range(self.total_pages):
                page = self.pdf_document[page_num]
                text_instances = page.search_for(search_text)
                
                for rect in text_instances:
                    scaled_rect = QRect(
                        int(rect.x0 * self.zoom_factor),
                        int(rect.y0 * self.zoom_factor),
                        int((rect.x1 - rect.x0) * self.zoom_factor),
                        int((rect.y1 - rect.y0) * self.zoom_factor)
                    )
                    self.search_results.append((page_num, scaled_rect, rect))
            
            # Update UI and highlight ALL results
            if self.search_results:
                self.current_search_index = 0
                self.update_search_ui()
                self.highlight_all_search_results()
                self.scroll_to_current_result()
                
                if hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(
                        f"Found {len(self.search_results)} results", 2000
                    )
            else:
                self.search_results_label.setText("0/0")
                self.prev_search_btn.setEnabled(False)
                self.next_search_btn.setEnabled(False)
                if hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage("No results found", 2000)
        else:
            # Same search text - just go to next result
            if self.search_results:
                # Only navigate if we have results
                self.search_next()
            else:
                # No results to navigate - inform user
                if hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage("No results found", 2000)

        
    def highlight_all_search_results(self):
        """Highlight ALL search results on all pages with yellow highlighting"""
        if not self.search_results or self.all_results_highlighted:
            return
        #print(f"🎨 Highlighting all {len(self.search_results)} search results")
        # Group results by page
        results_by_page = {}
        for page_num, widget_rect, pdf_rect in self.search_results:
            if page_num not in results_by_page:
                results_by_page[page_num] = []
            results_by_page[page_num].append(widget_rect)
        # Highlight results on each page
        for page_num, rects in results_by_page.items():
            if page_num < len(self.page_labels):
                self._draw_all_highlights_on_page(page_num, rects)
        self.all_results_highlighted = True
    def _draw_all_highlights_on_page(self, page_num, widget_rects):
        """Draw yellow highlights for all search results on a single page
        Args:
            page_num: Page number (0-indexed)
            widget_rects: List of QRect objects for all results on this page
        """
        if page_num < 0 or page_num >= len(self.page_labels):
            return
        page_label = self.page_labels[page_num]
        # Store original pixmap if not already stored
        if not hasattr(page_label, '_original_pixmap') or page_label._original_pixmap is None:
            page_label._original_pixmap = page_label.pixmap().copy()
        # Create highlighted pixmap from original
        highlighted_pixmap = page_label._original_pixmap.copy()
        painter = QPainter(highlighted_pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            # Draw yellow highlight for each result
            highlight_color = QColor(255, 255, 0, 100)  # Yellow, semi-transparent
            border_color = QColor(255, 200, 0, 150)  # Orange border
            for rect in widget_rects:
                # Fill with yellow
                painter.fillRect(rect, highlight_color)
                # Draw border
                pen = QPen(border_color, 1)
                painter.setPen(pen)
                painter.drawRect(rect)

        finally:
            painter.end()

        # Apply highlighted pixmap
        page_label.setPixmap(highlighted_pixmap)
        page_label._search_highlighted = True


    def scroll_to_current_result(self):
        """Scroll to the current search result and add emphasis highlight"""
        if not self.search_results or self.current_search_index < 0:
            return
        page_num, widget_rect, pdf_rect = self.search_results[self.current_search_index]
        # Scroll to the page and position
        if page_num < len(self.page_labels):
            page_label = self.page_labels[page_num]
            # Calculate scroll position
            page_pos = page_label.y()
            target_y = page_pos + widget_rect.y() - 100  # 100px margin from top
            target_y = max(0, target_y)
            # Scroll to position
            self.scroll_area.verticalScrollBar().setValue(target_y)
            # Add emphasis to current result (orange border)
            self._emphasize_current_result(page_num, widget_rect)
            # Update current page
            self.current_page = page_num
            self.update_page_controls()
    def _emphasize_current_result(self, page_num, current_rect):
        """Add emphasis (thicker border) to the current search result
        This re-draws all highlights but makes the current one stand out.
        """
        if page_num < 0 or page_num >= len(self.page_labels):
            return
        page_label = self.page_labels[page_num]
        # Get original pixmap
        if not hasattr(page_label, '_original_pixmap') or page_label._original_pixmap is None:
            return
        # Get all results for this page
        page_results = [(rect, pdf_rect) for p, rect, pdf_rect in self.search_results if p == page_num]
        # Create highlighted pixmap
        highlighted_pixmap = page_label._original_pixmap.copy()
        painter = QPainter(highlighted_pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            # Draw all results
            for rect, _ in page_results:
                is_current = (rect == current_rect)
                if is_current:
                    # Current result: brighter yellow, thicker orange border
                    highlight_color = QColor(255, 255, 0, 150)  # Brighter yellow
                    border_color = QColor(255, 100, 0, 255)  # Bright orange
                    border_width = 3
                else:
                    # Other results: normal yellow highlight
                    highlight_color = QColor(255, 255, 0, 80)  # Lighter yellow
                    border_color = QColor(255, 200, 0, 150)  # Light orange
                    border_width = 1
                # Fill
                painter.fillRect(rect, highlight_color)
                # Border
                pen = QPen(border_color, border_width)
                painter.setPen(pen)
                painter.drawRect(rect)

        finally:
            painter.end()

        page_label.setPixmap(highlighted_pixmap)

    def search_next(self):
        """Go to next search result"""
        if not self.search_results:
            # Only perform search if this is the first search attempt
            if not self.search_text:  # Not searched yet
                self.perform_search()
            return  # Exit early if no results
        # if not self.search_results:
            # self.perform_search()
            # return
        # Clear emphasis from current result
        if self.current_search_index >= 0:
            old_page = self.search_results[self.current_search_index][0]
            self._refresh_page_highlights(old_page)
        # Move to next
        if self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
        else:
            self.current_search_index = 0  # Wrap around
        self.update_search_ui()
        self.scroll_to_current_result()
    def search_previous(self):
        """Go to previous search result"""
        if not self.search_results:
            # Only perform search if this is the first search attempt
            if not self.search_text:  # Not searched yet
                self.perform_search()
            return  # Exit early if no results
        # if not self.search_results:
            # return
        # Clear emphasis from current result
        if self.current_search_index >= 0:
            old_page = self.search_results[self.current_search_index][0]
            self._refresh_page_highlights(old_page)
        # Move to previous
        if self.current_search_index > 0:
            self.current_search_index -= 1
        else:
            self.current_search_index = len(self.search_results) - 1  # Wrap around
        self.update_search_ui()
        self.scroll_to_current_result()
    def _refresh_page_highlights(self, page_num):
        """Refresh highlights on a page (remove emphasis from previous current result)"""
        if page_num < 0 or page_num >= len(self.page_labels):
            return
        # Get all results for this page
        page_rects = [rect for p, rect, _ in self.search_results if p == page_num]
        if page_rects:
            self._draw_all_highlights_on_page(page_num, page_rects)
    def update_search_ui(self):
        """Update search UI elements"""
        if self.search_results:
            self.search_results_label.setText(
                f"{self.current_search_index + 1}/{len(self.search_results)}"
            )
            self.prev_search_btn.setEnabled(True)
            self.next_search_btn.setEnabled(True)
        else:
            self.search_results_label.setText("0/0")
            self.prev_search_btn.setEnabled(False)
            self.next_search_btn.setEnabled(False)
    def clear_search_highlights(self):
        """Remove all search highlights from pages"""
        for page_label in self.page_labels:
            if hasattr(page_label, '_search_highlighted') and page_label._search_highlighted:
                if hasattr(page_label, '_original_pixmap') and page_label._original_pixmap:
                    page_label.setPixmap(page_label._original_pixmap)
                page_label._search_highlighted = False
        self.all_results_highlighted = False
    def clear_search(self):
        """Clear search results and highlights"""
        self.search_results = []
        self.current_search_index = -1
        self.search_text = ""
        self.search_field.clear()
        self.search_results_label.setText("")
        self.prev_search_btn.setEnabled(False)
        self.next_search_btn.setEnabled(False)
        self.all_results_highlighted = False
        self.clear_search_highlights()

# ============================================================================
# PART 4: COMPLETE REPLACEMENT for SelectablePageLabel class WITH HYPERLINKS
# ============================================================================
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QPainterPath
from PyQt5.QtWidgets import QLabel
import fitz

class SelectablePageLabel(QLabel):
    """Custom QLabel that handles text selection, pan mode, reverse search, magnifying glass, hyperlinks, AND annotations"""
    
    def __init__(self, page_number, pdf_viewer, links=None):
        super().__init__()
        self.page_number = page_number
        self.pdf_viewer = pdf_viewer
        self.links = links or []
        self.hover_link = None
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        
        # Annotation drawing state
        self.annot_drawing = False
        self.annot_temp_pixmap = None
        
        self.setMouseTracking(True)
    
    def _is_annotation_mode_active(self):
        """Check if annotation toolbar is visible and a tool is selected"""
        return (hasattr(self.pdf_viewer, 'annotation_toolbar_widget') and
                self.pdf_viewer.annotation_toolbar_widget.isVisible() and
                self.pdf_viewer.annotation_tool is not None)
                
    def mouseDoubleClickEvent(self, event):
        """Handle double-click for editing annotations"""
        if (self._is_annotation_mode_active() and
            self.pdf_viewer.annotation_tool == "select" and
            event.button() == Qt.LeftButton):

            pdf_point = self.pdf_viewer._screen_to_pdf_point(self, event.pos())
            if pdf_point:
                annot_info = self.pdf_viewer._find_annot_at_point(
                    self.page_number, pdf_point)

                if annot_info and isinstance(annot_info, dict):
                    rect_tuple = annot_info['rect']
                    annot_type = annot_info.get('type', '')

                    # Select first so everything is consistent
                    self.pdf_viewer._select_annotation(
                        self.page_number, annot_info)

                    # Edit based on type
                    if annot_type == "Text":
                        self.pdf_viewer._edit_text_annotation(
                            self.page_number, rect_tuple)
                        event.accept()
                        return
                    elif annot_type == "FreeText":
                        self.pdf_viewer._edit_freetext_annotation(
                            self.page_number, rect_tuple)
                        event.accept()
                        return

            event.accept()
            return

        if not self._is_annotation_mode_active():
            super().mouseDoubleClickEvent(event)
        
        
    def mousePressEvent(self, event):
        """Handle mouse press for all modes including annotations"""
        # Focus handling
        self.pdf_viewer.scroll_area.setFocus(Qt.MouseFocusReason)

        from time import time
        self.pdf_viewer._last_click_time = time()

        # ═══════════════════════════════════════════════════════════════════
        # PRIORITY 0: ANNOTATION TOOLS
        # ═══════════════════════════════════════════════════════════════════
        if self._is_annotation_mode_active():
            tool = self.pdf_viewer.annotation_tool
            

            if tool == "select":
                pdf_point = self.pdf_viewer._screen_to_pdf_point(self, event.pos())
                if pdf_point:
                    annot_info = self.pdf_viewer._find_annot_at_point(
                        self.page_number, pdf_point)
                    if annot_info:
                        if isinstance(annot_info, dict):
                            rect_tuple = annot_info['rect']
                        else:
                            rect_tuple = annot_info
                        if event.button() == Qt.LeftButton:
                            # Always just select + start drag on single click.
                            # Double-click (mouseDoubleClickEvent) handles editing.
                            self.pdf_viewer._select_annotation(
                                self.page_number, annot_info)
                            self.pdf_viewer.dragging_annot = True
                            self.pdf_viewer.drag_start = pdf_point
                            self.pdf_viewer.last_drag_pos = (0, 0)
                            self.setCursor(Qt.ClosedHandCursor)
                        elif event.button() == Qt.RightButton:
                            self.pdf_viewer._select_annotation(
                                self.page_number, annot_info)
                    else:
                        self.pdf_viewer._clear_annotation_selection()
                event.accept()
                return

            # if tool == "select":
                # pdf_point = self.pdf_viewer._screen_to_pdf_point(self, event.pos())
                # if pdf_point:
                    # annot_info = self.pdf_viewer._find_annot_at_point(self.page_number, pdf_point)

                    # if annot_info:
                        # # Extract rect tuple and type from the dict
                        # if isinstance(annot_info, dict):
                            # rect_tuple = annot_info['rect']
                            # annot_type = annot_info.get('type', '')
                        # else:
                            # rect_tuple = annot_info
                            # annot_type = ''

                        # if event.button() == Qt.LeftButton:
                            # # Check if clicking on ALREADY selected annotation
                            # if (self.pdf_viewer.selected_annot_rect == rect_tuple and
                                # self.pdf_viewer.selected_annot_page == self.page_number):
                                # # Single click on already-selected → open editor
                                # if annot_type == "Text":
                                    # self.pdf_viewer._edit_text_annotation(
                                        # self.page_number, rect_tuple)
                                    # event.accept()
                                    # return
                                # elif annot_type == "FreeText":
                                    # self.pdf_viewer._edit_freetext_annotation(
                                        # self.page_number, rect_tuple)
                                    # event.accept()
                                    # return

                            # # Select the annotation (stores rect + type)
                            # self.pdf_viewer._select_annotation(
                                # self.page_number, annot_info)

                            # # Start drag
                            # self.pdf_viewer.dragging_annot = True
                            # self.pdf_viewer.drag_start = pdf_point
                            # self.pdf_viewer.last_drag_pos = (0, 0)
                            # self.setCursor(Qt.ClosedHandCursor)

                        # elif event.button() == Qt.RightButton:
                            # # Just select — contextMenuEvent will show the menu
                            # self.pdf_viewer._select_annotation(
                                # self.page_number, annot_info)
                    # else:
                        # # Clicked on empty area — deselect
                        # self.pdf_viewer._clear_annotation_selection()
                        # #self.pdf_viewer.main_window.update_status_bar("Click on an annotation to select it")
                        # #self._update_annot_status("Click on an annotation to select it")

                # event.accept()
                # return

            elif tool == "text" and event.button() == Qt.LeftButton:
                self.pdf_viewer._add_text_annotation(self, event.pos())
                event.accept()
                return
            elif tool == "freetext" and event.button() == Qt.LeftButton:
                self.pdf_viewer._add_freetext_annotation(self, event.pos())
                event.accept()
                return
            elif tool == "ink" and event.button() == Qt.LeftButton:
                self.annot_drawing = True
                self.pdf_viewer.annotation_ink_points = [event.pos()]
                self.annot_temp_pixmap = self.pixmap().copy() if self.pixmap() else None
                event.accept()
                return
            elif tool in ["highlight", "rect", "circle", "line"] and event.button() == Qt.LeftButton:
                self.annot_drawing = True
                self.pdf_viewer.annotation_start_pos = event.pos()
                self.annot_temp_pixmap = self.pixmap().copy() if self.pixmap() else None
                event.accept()
                return

            # If in annotation mode, consume right-click
            if event.button() == Qt.RightButton:
                event.accept()
                return

        # ═══════════════════════════════════════════════════════════════════
        # PRIORITY 1: CHECK FOR HYPERLINK CLICK
        # ═══════════════════════════════════════════════════════════════════
        if event.button() == Qt.LeftButton and self.hover_link:
            self.pdf_viewer.handle_link_click(self.hover_link)
            event.accept()
            return

        # ═══════════════════════════════════════════════════════════════════
        # PRIORITY 2: REVERSE SEARCH MODE
        # ═══════════════════════════════════════════════════════════════════
        if (event.button() == Qt.LeftButton and
            self.pdf_viewer.reverse_search_mode and
            self.pdf_viewer.synctex_available):
            click_pos = event.pos()
            self.pdf_viewer.perform_reverse_search(
                self.page_number, click_pos.x(), click_pos.y())
            event.accept()
            return

        # ═══════════════════════════════════════════════════════════════════
        # PRIORITY 3: MAGNIFYING GLASS (Right button)
        # ═══════════════════════════════════════════════════════════════════
        if event.button() == Qt.RightButton:
            self.pdf_viewer.magnifier_active = True
            self.pdf_viewer.magnifier_pos = event.pos()
            self.setCursor(Qt.BlankCursor)
            if hasattr(self.pdf_viewer.main_window, 'statusBar'):
                self.pdf_viewer.main_window.statusBar().showMessage(
                    "Magnifying glass active - Move mouse to inspect, release to exit", 0)
            self.update()
            event.accept()
            return

        # ═══════════════════════════════════════════════════════════════════
        # PRIORITY 4: PAN MODE OR SELECT MODE
        # ═══════════════════════════════════════════════════════════════════
        if event.button() == Qt.LeftButton:
            if event.modifiers() == Qt.ControlModifier and self.pdf_viewer.synctex_available:
                click_pos = event.pos()
                self.pdf_viewer.perform_reverse_search(
                    self.page_number, click_pos.x(), click_pos.y())
                return

            if self.pdf_viewer.select_mode:
                self.selection_start = event.pos()
                self.selecting = True
                self.pdf_viewer.selecting = True
                self.pdf_viewer.selection_start = self.mapToParent(event.pos())
                return

            if self.pdf_viewer.pan_mode:
                self.pdf_viewer.panning = True
                self.pdf_viewer.pan_start_pos = event.globalPos()
                self.pdf_viewer.pan_start_scroll_x = self.pdf_viewer.scroll_area.horizontalScrollBar().value()
                self.pdf_viewer.pan_start_scroll_y = self.pdf_viewer.scroll_area.verticalScrollBar().value()
                self.setCursor(Qt.ClosedHandCursor)
                return

        super().mousePressEvent(event)
    
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for all modes including annotations"""
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ ANNOTATION HANDLING
        # ═══════════════════════════════════════════════════════════════════
        if self._is_annotation_mode_active():
            tool = self.pdf_viewer.annotation_tool
            
            
            if tool == "select":
                if self.pdf_viewer.dragging_annot and self.pdf_viewer.selected_annot_rect:
                    # Dragging annotation - calculate displacement
                    pdf_point = self.pdf_viewer._screen_to_pdf_point(self, event.pos())
                    if pdf_point and self.pdf_viewer.drag_start:
                        dx = pdf_point.x - self.pdf_viewer.drag_start.x
                        dy = pdf_point.y - self.pdf_viewer.drag_start.y
                        self.pdf_viewer.last_drag_pos = (dx, dy)
                        #self.pdf_viewer.main_window.update_status_bar(f"Dragging: dx={dx:.1f}, dy={dy:.1f} (release to apply)")
                        #self._update_annot_status(f"Dragging: dx={dx:.1f}, dy={dy:.1f} (release to apply)")
                else:
                    # Hover feedback - show hand cursor over annotations
                    pdf_point = self.pdf_viewer._screen_to_pdf_point(self, event.pos())
                    if pdf_point:
                        annot_info = self.pdf_viewer._find_annot_at_point(self.page_number, pdf_point)
                        if annot_info:
                            self.setCursor(Qt.OpenHandCursor)
                            # ✅ FIXED: Pass annot_info (dict) instead of annot_rect
                            self.pdf_viewer._show_annotation_tooltip(
                                self.page_number, 
                                annot_info,  # Pass the dict
                                self.mapToGlobal(event.pos())
                            )
                        else:
                            self.setCursor(Qt.ArrowCursor)
                return
            elif tool == "ink" and self.annot_drawing:
                self.pdf_viewer.annotation_ink_points.append(event.pos())
                self._draw_temp_ink()
                return
            
            elif tool in ["highlight", "rect", "circle", "line"] and self.annot_drawing:
                self._draw_temp_shape(event.pos())
                return
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ LINK HOVER (when not in annotation mode)
        # ═══════════════════════════════════════════════════════════════════
        if self.links and not self.pdf_viewer.magnifier_active and not self._is_annotation_mode_active():
            pos = event.pos()
            found_link = None
            
            for link in self.links:
                if link['rect'].contains(pos):
                    found_link = link
                    break
            
            if found_link != self.hover_link:
                self.hover_link = found_link
                
                if hasattr(self.pdf_viewer, 'tooltip_timer'):
                    self.pdf_viewer.tooltip_timer.stop()
                
                if self.hover_link:
                    self.setCursor(Qt.PointingHandCursor)
                    if (hasattr(self.pdf_viewer, 'tooltips_enabled') and 
                        self.pdf_viewer.tooltips_enabled):
                        self.pdf_viewer.pending_tooltip_link = self.hover_link
                        self.pdf_viewer.pending_tooltip_pos = self.mapToGlobal(pos)
                        self.pdf_viewer.tooltip_timer.start(500)
                else:
                    from PyQt5.QtWidgets import QToolTip
                    QToolTip.hideText()
                    
                    if self.pdf_viewer.reverse_search_mode:
                        self.setCursor(Qt.CrossCursor)
                    elif self.pdf_viewer.select_mode:
                        self.setCursor(Qt.IBeamCursor)
                    elif self.pdf_viewer.panning:
                        self.setCursor(Qt.ClosedHandCursor)
                    elif self.pdf_viewer.pan_mode:
                        self.setCursor(Qt.OpenHandCursor)
                    else:
                        self.setCursor(Qt.ArrowCursor)
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ MAGNIFYING GLASS
        # ═══════════════════════════════════════════════════════════════════
        if self.pdf_viewer.magnifier_active:
            self.pdf_viewer.magnifier_pos = event.pos()
            self.update()
            event.accept()
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ PAN MODE DRAGGING
        # ═══════════════════════════════════════════════════════════════════
        if self.pdf_viewer.panning and self.pdf_viewer.pan_mode:
            current_pos = event.globalPos()
            delta = current_pos - self.pdf_viewer.pan_start_pos
            new_scroll_x = self.pdf_viewer.pan_start_scroll_x - delta.x()
            new_scroll_y = self.pdf_viewer.pan_start_scroll_y - delta.y()
            self.pdf_viewer.scroll_area.horizontalScrollBar().setValue(int(new_scroll_x))
            self.pdf_viewer.scroll_area.verticalScrollBar().setValue(int(new_scroll_y))
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ SELECT MODE - TEXT SELECTION
        # ═══════════════════════════════════════════════════════════════════
        if self.selecting and self.pdf_viewer.select_mode:
            self.selection_end = event.pos()
            self.pdf_viewer.selection_end = self.mapToParent(event.pos())
            start_global = self.mapToParent(self.selection_start)
            end_global = self.mapToParent(self.selection_end)
            self.pdf_viewer.selection_rect = QRect(
                min(start_global.x(), end_global.x()),
                min(start_global.y(), end_global.y()),
                abs(end_global.x() - start_global.x()),
                abs(end_global.y() - start_global.y())
            )
            self.update()
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for all modes including annotations"""
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ ANNOTATION HANDLING
        # ═══════════════════════════════════════════════════════════════════
        if self._is_annotation_mode_active():
            tool = self.pdf_viewer.annotation_tool
            if tool == "select":
                if self.pdf_viewer.dragging_annot and self.pdf_viewer.selected_annot_rect:
                    dx, dy = self.pdf_viewer.last_drag_pos if self.pdf_viewer.last_drag_pos else (0, 0)
                    # Only move if there's significant displacement
                    if abs(dx) > 1 or abs(dy) > 1:
                        self.pdf_viewer._move_annotation(self.page_number, dx, dy)
                    
                    self.pdf_viewer.dragging_annot = False
                    self.pdf_viewer.drag_start = None
                    self.pdf_viewer.last_drag_pos = None
                    self.setCursor(Qt.ArrowCursor)
                event.accept()
                return

            
            elif tool == "ink" and self.annot_drawing:
                self.annot_drawing = False
                self.pdf_viewer._commit_ink_annotation(self)
                self.annot_temp_pixmap = None
                event.accept()
                return
            
            elif tool in ["highlight", "rect", "circle", "line"] and self.annot_drawing:
                self.annot_drawing = False
                self.pdf_viewer._commit_shape_annotation(self, event.pos())
                self.annot_temp_pixmap = None
                event.accept()
                return
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ MAGNIFYING GLASS RELEASE
        # ═══════════════════════════════════════════════════════════════════
        if self.pdf_viewer.magnifier_active and event.button() == Qt.RightButton:
            self.pdf_viewer.magnifier_active = False
            self.pdf_viewer.magnifier_pos = None
            
            if self._is_annotation_mode_active():
                tool = self.pdf_viewer.annotation_tool
                if tool == "select":
                    self.setCursor(Qt.ArrowCursor)
                else:
                    self.setCursor(Qt.CrossCursor)
            elif self.pdf_viewer.select_mode:
                self.setCursor(Qt.IBeamCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
            
            if hasattr(self.pdf_viewer.main_window, 'statusBar'):
                self.pdf_viewer.main_window.statusBar().clearMessage()
            self.update()
            event.accept()
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ PAN MODE RELEASE
        # ═══════════════════════════════════════════════════════════════════
        if self.pdf_viewer.panning and event.button() == Qt.LeftButton:
            self.pdf_viewer.panning = False
            if self.hover_link:
                self.setCursor(Qt.PointingHandCursor)
            elif self.pdf_viewer.pan_mode:
                self.setCursor(Qt.OpenHandCursor)
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # ✅ TEXT SELECTION RELEASE
        # ═══════════════════════════════════════════════════════════════════
        if self.selecting and event.button() == Qt.LeftButton and self.pdf_viewer.select_mode:
            self.selecting = False
            self.pdf_viewer.selecting = False
            if self.selection_start and self.selection_end:
                self.pdf_viewer.extract_selected_text()
            self.selection_start = None
            self.selection_end = None
            self.pdf_viewer.selection_rect = None
            return
        
        super().mouseReleaseEvent(event)
    
    def _draw_temp_ink(self):
        """Draw temporary ink while drawing"""
        if not self.annot_temp_pixmap or len(self.pdf_viewer.annotation_ink_points) < 2:
            return
        
        pixmap = self.annot_temp_pixmap.copy()
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(
                self.pdf_viewer.annotation_color,
                self.pdf_viewer.annotation_pen_width,
                Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin
            )
            painter.setPen(pen)
            
            points = self.pdf_viewer.annotation_ink_points
            for i in range(1, len(points)):
                painter.drawLine(points[i-1], points[i])

        finally:
            painter.end()

        self.setPixmap(pixmap)
    
    def _draw_temp_shape(self, end_pos):
        """Draw temporary shape while drawing"""
        if not self.annot_temp_pixmap or not self.pdf_viewer.annotation_start_pos:
            return
        
        pixmap = self.annot_temp_pixmap.copy()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        start_pos = self.pdf_viewer.annotation_start_pos
        tool = self.pdf_viewer.annotation_tool
        color = self.pdf_viewer.annotation_color
        
        if tool == "highlight":
            pen = QPen(Qt.NoPen)
            brush = QBrush(QColor(color.red(), color.green(), color.blue(), 80))
            painter.setPen(pen)
            painter.setBrush(brush)
            rect = QRect(start_pos, end_pos).normalized()
            painter.drawRect(rect)
        else:
            pen = QPen(color, self.pdf_viewer.annotation_pen_width, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            if tool == "rect":
                rect = QRect(start_pos, end_pos).normalized()
                painter.drawRect(rect)
            elif tool == "circle":
                rect = QRect(start_pos, end_pos).normalized()
                painter.drawEllipse(rect)
            elif tool == "line":
                painter.drawLine(start_pos, end_pos)
        
        painter.end()
        self.setPixmap(pixmap)
    
    def contextMenuEvent(self, event):
        """Handle context menu — single entry point for annotation right-click menus"""
        if self._is_annotation_mode_active() and self.pdf_viewer.annotation_tool == "select":
            if self.pdf_viewer.selected_annot_rect:
                self.pdf_viewer._show_annotation_context_menu(
                    event.globalPos(), self.page_number)
            event.accept()
            return

        if self.pdf_viewer.magnifier_active:
            event.accept()
            return

        super().contextMenuEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leaving the widget"""
        self.hover_link = None
        
        if self.pdf_viewer.magnifier_active:
            self.pdf_viewer.magnifier_active = False
            self.pdf_viewer.magnifier_pos = None
            
            if self.pdf_viewer.select_mode:
                self.setCursor(Qt.IBeamCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
            self.update()
        
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event"""
        super().paintEvent(event)
        painter = QPainter(self)
        try:
            # Draw TEXT SELECTION rectangle
            if self.selecting and self.selection_start and self.selection_end and self.pdf_viewer.select_mode:
                pen = QPen(Qt.blue, 2, Qt.DashLine)
                painter.setPen(pen)
                start_x = min(self.selection_start.x(), self.selection_end.x())
                start_y = min(self.selection_start.y(), self.selection_end.y())
                width = abs(self.selection_end.x() - self.selection_start.x())
                height = abs(self.selection_end.y() - self.selection_start.y())
                painter.drawRect(start_x, start_y, width, height)
            
            # Draw selection highlight for selected annotation
            if (self._is_annotation_mode_active() and 
                self.pdf_viewer.annotation_tool == "select" and
                self.pdf_viewer.selected_annot_rect and
                self.pdf_viewer.selected_annot_page == self.page_number):
                
                screen_rect = self.pdf_viewer._pdf_to_screen_rect(self, self.pdf_viewer.selected_annot_rect)
                if screen_rect:
                    # Draw selection highlight
                    pen = QPen(QColor(0, 120, 215), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.setBrush(QBrush(QColor(0, 120, 215, 30)))
                    painter.drawRect(screen_rect)
                    
                    # Draw corner handles
                    handle_size = 6
                    painter.setBrush(QBrush(QColor(0, 120, 215)))
                    corners = [
                        screen_rect.topLeft(),
                        screen_rect.topRight(),
                        screen_rect.bottomLeft(),
                        screen_rect.bottomRight(),
                    ]
                    for corner in corners:
                        painter.drawRect(
                            corner.x() - handle_size // 2,
                            corner.y() - handle_size // 2,
                            handle_size, handle_size
                        )
            
            # Draw MAGNIFYING GLASS
            if self.pdf_viewer.magnifier_active and self.pdf_viewer.magnifier_pos:
                self.draw_magnifying_glass(painter)
        finally:
            painter.end()

    def draw_magnifying_glass(self, painter):
        """Draw the magnifying glass overlay with high-precision rendering"""
        mag_size = self.pdf_viewer.magnifier_size
        mag_zoom = self.pdf_viewer.magnifier_zoom
        mag_pos = self.pdf_viewer.magnifier_pos
        quality_mult = self.pdf_viewer.magnifier_quality_multiplier
        
        # Calculate the center of the magnifier
        center_x = mag_pos.x()
        center_y = mag_pos.y()
        
        # Calculate the source rectangle (area to magnify) in current resolution
        source_size = mag_size / mag_zoom
        source_rect = QRect(
            int(center_x - source_size / 2),
            int(center_y - source_size / 2),
            int(source_size),
            int(source_size)
        )
        
        # Get the pixmap bounds
        pixmap = self.pixmap()
        if not pixmap:
            return
        
        # Ensure source rect is within pixmap bounds
        source_rect = source_rect.intersected(pixmap.rect())
        
        if source_rect.isEmpty():
            return
        
        # METHOD 1: Re-render from PDF at higher resolution (BEST QUALITY)
        try:
            pdf_doc = self.pdf_viewer.pdf_document
            if pdf_doc and self.page_number < len(pdf_doc):
                page = pdf_doc[self.page_number]
                
                # Calculate which part of the PDF page we need
                page_width = pixmap.width()
                page_height = pixmap.height()
                pdf_page_rect = page.rect
                
                # Scale factors between screen pixels and PDF points
                scale_x = pdf_page_rect.width / page_width
                scale_y = pdf_page_rect.height / page_height
                
                # Convert source_rect to PDF coordinates
                pdf_x0 = source_rect.x() * scale_x
                pdf_y0 = source_rect.y() * scale_y
                pdf_x1 = (source_rect.x() + source_rect.width()) * scale_x
                pdf_y1 = (source_rect.y() + source_rect.height()) * scale_y
                
                pdf_clip_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                
                # Calculate high-resolution zoom matrix
                zoom_matrix = fitz.Matrix(
                    self.pdf_viewer.zoom_factor * mag_zoom * quality_mult,
                    self.pdf_viewer.zoom_factor * mag_zoom * quality_mult
                )
                
                # Render the high-resolution region
                pix = page.get_pixmap(matrix=zoom_matrix, clip=pdf_clip_rect)
                
                # Convert to QPixmap
                img_data = pix.tobytes("ppm")
                high_res_pixmap = QPixmap()
                high_res_pixmap.loadFromData(img_data)
                
                # Scale to final magnifier size with high quality
                magnified_pixmap = high_res_pixmap.scaled(
                    mag_size, mag_size,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                
        except Exception as e:
            # Fallback to METHOD 2 if PDF re-rendering fails
            high_res_source = pixmap.copy(source_rect).scaled(
                int(source_rect.width() * quality_mult),
                int(source_rect.height() * quality_mult),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
            
            magnified_pixmap = high_res_source.scaled(
                mag_size, mag_size,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
        
        # Calculate destination position
        dest_x = int(center_x - mag_size / 2)
        dest_y = int(center_y - mag_size / 2)
        
        # Save painter state
        painter.save()
        
        # Enable high-quality rendering
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        
        # Create circular clipping path
        path = QPainterPath()
        path.addEllipse(dest_x, dest_y, mag_size, mag_size)
        painter.setClipPath(path)
        
        # Draw magnified content
        painter.drawPixmap(dest_x, dest_y, magnified_pixmap)
        
        # Restore painter state
        painter.restore()
        
        # Draw thin border
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(50, 50, 50), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(dest_x, dest_y, mag_size, mag_size)
        
        # Draw crosshair
        painter.setPen(QPen(QColor(255, 0, 0), 1, Qt.SolidLine))
        crosshair_size = 10
        painter.drawLine(
            center_x - crosshair_size, center_y,
            center_x + crosshair_size, center_y
        )
        painter.drawLine(
            center_x, center_y - crosshair_size,
            center_x, center_y + crosshair_size
        )
        