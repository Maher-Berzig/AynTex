# completion_settings_widget.py
"""
Completion Settings Widget - UI for managing CWL file selection
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QCheckBox, 
    QLabel, QLineEdit, QPushButton, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal


class CompletionSettingsWidget(QWidget):
    """Widget for managing CWL completion files - TeXstudio style"""
    
    completionChanged = pyqtSignal()  # Emitted when completion settings change
    
    def __init__(self, cwl_manager, parent=None):
        super().__init__(parent)
        self.cwl_manager = cwl_manager
        self.checkboxes = {}
        self._setup_ui()
        self._load_file_list()
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Filter:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter files...")
        self.search_box.textChanged.connect(self._filter_files)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none)
        self.select_common_btn = QPushButton("Select Common")
        self.select_common_btn.clicked.connect(self._select_common)
        actions_layout.addWidget(self.select_all_btn)
        actions_layout.addWidget(self.select_none_btn)
        actions_layout.addWidget(self.select_common_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        # Scrollable checkbox list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setAlignment(Qt.AlignTop)
        self.files_layout.setSpacing(2)
        
        scroll.setWidget(self.files_container)
        layout.addWidget(scroll)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Commands: 0 | Files: 0/0")
        self.stats_label.setStyleSheet("color: #666;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_files)
        stats_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(stats_layout)
    
    def _load_file_list(self):
        """Load and display available CWL files"""
        # Clear existing checkboxes
        for cb in self.checkboxes.values():
            cb.setParent(None)
            cb.deleteLater()
        self.checkboxes.clear()
        
        # Clear any existing widgets in layout
        while self.files_layout.count():
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get available files
        files = self.cwl_manager.available_files()
        
        if not files:
            no_files_label = QLabel(
                "No .cwl files found.\n"
                f"Place .cwl files in:\n{self.cwl_manager.cwl_dir}"
            )
            no_files_label.setStyleSheet("color: #888; padding: 20px;")
            no_files_label.setAlignment(Qt.AlignCenter)
            no_files_label.setWordWrap(True)
            self.files_layout.addWidget(no_files_label)
            self._update_stats()
            return
        
        # Create checkboxes for each file
        for filename in files:
            cb = QCheckBox(filename)
            cb.setChecked(self.cwl_manager.is_enabled(filename))
            cb.stateChanged.connect(lambda state, f=filename: self._toggle_file(f, state))
            self.files_layout.addWidget(cb)
            self.checkboxes[filename] = cb
        
        self._update_stats()
    
    def _toggle_file(self, filename: str, state: int):
        """Handle checkbox toggle"""
        if state == Qt.Checked:
            self.cwl_manager.enable_file(filename)
        else:
            self.cwl_manager.disable_file(filename)
        
        self._update_stats()
        self.completionChanged.emit()
    
    def _filter_files(self, text: str):
        """Filter displayed files by search text"""
        text_lower = text.lower()
        for filename, cb in self.checkboxes.items():
            cb.setVisible(text_lower in filename.lower())
    
    def _update_stats(self):
        """Update statistics display"""
        total_files = len(self.checkboxes)
        enabled_files = self.cwl_manager.get_enabled_file_count()
        command_count = self.cwl_manager.get_command_count()
        
        self.stats_label.setText(
            f"Commands: {command_count} | Files: {enabled_files}/{total_files}"
        )
    
    def _select_all(self):
        """Select all visible files"""
        for filename, cb in self.checkboxes.items():
            if cb.isVisible():
                cb.setChecked(True)
    
    def _select_none(self):
        """Deselect all files"""
        for cb in self.checkboxes.values():
            cb.setChecked(False)
    
    def _select_common(self):
        """Select commonly used LaTeX packages"""
        common_files = [
            'latex-document.cwl', 'latex-dev.cwl', 'latex.cwl',
            'amsmath.cwl', 'amssymb.cwl', 'amsthm.cwl',
            'graphicx.cwl', 'hyperref.cwl', 'geometry.cwl',
            'xcolor.cwl', 'tikz.cwl', 'biblatex.cwl',
            'fontspec.cwl', 'polyglossia.cwl', 'babel.cwl',
            'inputenc.cwl', 'fontenc.cwl', 'microtype.cwl'
        ]
        
        for filename, cb in self.checkboxes.items():
            cb.setChecked(filename in common_files)
    
    def _refresh_files(self):
        """Refresh the file list"""
        self._load_file_list()
        self._update_stats()
    
    def get_enabled_files(self) -> list:
        """Get list of enabled files"""
        return list(self.cwl_manager.enabled_files)
    
    def set_enabled_files(self, files: list):
        """Set enabled files from a list"""
        self.cwl_manager.set_enabled_files(files)
        
        # Update checkboxes
        for filename, cb in self.checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(filename in files)
            cb.blockSignals(False)
        
        self._update_stats()