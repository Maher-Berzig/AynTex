# latex_comparator.py
"""
LaTeX File Comparison Tool

Provides a side-by-side comparison view for two LaTeX files with 
syntax highlighting and difference visualization.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QPlainTextEdit, QFileDialog, QProgressBar,
                             QSplitter, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
import difflib
import os


class LaTeXComparatorWidget(QWidget):
    """Widget for comparing two LaTeX files side by side."""
    
    comparison_started = pyqtSignal()
    comparison_finished = pyqtSignal()
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.file1_path = None
        self.file2_path = None
        self.file1_content = ""
        self.file2_content = ""
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the comparison interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ═══════════════════════════════════════════════════════════
        # TOP CONTROL PANEL
        # ═══════════════════════════════════════════════════════════
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # ═══════════════════════════════════════════════════════════
        # PROGRESS BAR (initially hidden)
        # ═══════════════════════════════════════════════════════════
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # ═══════════════════════════════════════════════════════════
        # COMPARISON VIEW (two editors side by side)
        # ═══════════════════════════════════════════════════════════
        splitter = QSplitter(Qt.Horizontal)
        
        # Left editor (File 1)
        self.editor1 = self._create_editor()
        left_frame = self._create_editor_frame(self.editor1, "File 1")
        splitter.addWidget(left_frame)
        
        # Right editor (File 2)
        self.editor2 = self._create_editor()
        right_frame = self._create_editor_frame(self.editor2, "File 2")
        splitter.addWidget(right_frame)
        
        # Equal split
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter, stretch=1)
        
        # ═══════════════════════════════════════════════════════════
        # STATISTICS PANEL
        # ═══════════════════════════════════════════════════════════
        stats_panel = self._create_statistics_panel()
        layout.addWidget(stats_panel)
    
    def _create_control_panel(self):
        """Create the top control panel with file selection and compare button."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        layout = QHBoxLayout(panel)
        
        # ─────────────────────────────────────────────────────────
        # LEFT SIDE: File 1
        # ─────────────────────────────────────────────────────────
        self.file1_label = QLabel("No file selected")
        self.file1_label.setStyleSheet("QLabel { padding: 5px; background: #f0f0f0; border-radius: 3px; }")
        self.file1_label.setMinimumWidth(200)
        layout.addWidget(self.file1_label)
        
        self.btn_open_file1 = QPushButton("Open File 1")
        self.btn_open_file1.clicked.connect(self.open_file1)
        layout.addWidget(self.btn_open_file1)
        
        # Apply icon if available
        if hasattr(self.main_window, 'icons_manager'):
            self.main_window.icons_manager.apply_icon_to_button(self.btn_open_file1, "open")
        
        # ─────────────────────────────────────────────────────────
        # CENTER: Compare Button
        # ─────────────────────────────────────────────────────────
        layout.addStretch()
        
        self.btn_compare = QPushButton("⚡ Compare Files")
        self.btn_compare.clicked.connect(self.compare_files)
        self.btn_compare.setEnabled(False)
        self.btn_compare.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.btn_compare)
        
        # Apply icon if available
        if hasattr(self.main_window, 'icons_manager'):
            self.main_window.icons_manager.apply_icon_to_button(self.btn_compare, "compare")
        
        layout.addStretch()
        
        # ─────────────────────────────────────────────────────────
        # RIGHT SIDE: File 2
        # ─────────────────────────────────────────────────────────
        self.btn_open_file2 = QPushButton("Open File 2")
        self.btn_open_file2.clicked.connect(self.open_file2)
        layout.addWidget(self.btn_open_file2)
        
        # Apply icon if available
        if hasattr(self.main_window, 'icons_manager'):
            self.main_window.icons_manager.apply_icon_to_button(self.btn_open_file2, "open")
        
        self.file2_label = QLabel("No file selected")
        self.file2_label.setStyleSheet("QLabel { padding: 5px; background: #f0f0f0; border-radius: 3px; }")
        self.file2_label.setMinimumWidth(200)
        layout.addWidget(self.file2_label)
        
        return panel
    
    def _create_editor(self):
        """Create a read-only text editor for displaying file content."""
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        
        # Set font
        font = QFont("Consolas", 10)
        editor.setFont(font)
        
        # Set RTL/LTR based on main window setting
        if hasattr(self.main_window, 'is_rtl') and self.main_window.is_rtl:
            editor.setLayoutDirection(Qt.RightToLeft)
        else:
            editor.setLayoutDirection(Qt.LeftToRight)
        
        return editor
    
    def _create_editor_frame(self, editor, title):
        """Create a frame with title for an editor."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                padding: 5px;
                background: #e0e0e0;
                border-radius: 3px;
            }
        """)
        layout.addWidget(title_label)
        
        # Editor
        layout.addWidget(editor)
        
        return frame
    
    def _create_statistics_panel(self):
        """Create statistics panel showing difference counts."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        layout = QHBoxLayout(panel)
        
        self.stats_label = QLabel("No comparison performed yet")
        self.stats_label.setStyleSheet("QLabel { padding: 5px; }")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
        
        # Legend
        legend_layout = QHBoxLayout()
        
        # Added lines
        added_box = QLabel("  ")
        added_box.setStyleSheet("QLabel { background-color: #90EE90; border: 1px solid #000; }")
        legend_layout.addWidget(added_box)
        legend_layout.addWidget(QLabel("Added"))
        
        legend_layout.addSpacing(10)
        
        # Removed lines
        removed_box = QLabel("  ")
        removed_box.setStyleSheet("QLabel { background-color: #FFB6C6; border: 1px solid #000; }")
        legend_layout.addWidget(removed_box)
        legend_layout.addWidget(QLabel("Removed"))
        
        legend_layout.addSpacing(10)
        
        # Modified lines
        modified_box = QLabel("  ")
        modified_box.setStyleSheet("QLabel { background-color: #FFD700; border: 1px solid #000; }")
        legend_layout.addWidget(modified_box)
        legend_layout.addWidget(QLabel("Modified"))
        
        layout.addLayout(legend_layout)
        
        return panel
    
    # ═══════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def open_file1(self):
        """Open first file for comparison."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select First LaTeX File",
            "",
            "LaTeX Files (*.tex);;All Files (*.*)"
        )
        
        if filename:
            self.load_file1(filename)
    
    def open_file2(self):
        """Open second file for comparison."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Second LaTeX File",
            "",
            "LaTeX Files (*.tex);;All Files (*.*)"
        )
        
        if filename:
            self.load_file2(filename)
    
    def load_file1(self, filepath):
        """Load first file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.file1_content = f.read()
            
            self.file1_path = filepath
            self.file1_label.setText(os.path.basename(filepath))
            self.editor1.setPlainText(self.file1_content)
            
            # Enable compare button if both files loaded
            self._check_enable_compare()
            
        except Exception as e:
            print(f"Error loading file 1: {e}")
            self.file1_label.setText("Error loading file")
    
    def load_file2(self, filepath):
        """Load second file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.file2_content = f.read()
            
            self.file2_path = filepath
            self.file2_label.setText(os.path.basename(filepath))
            self.editor2.setPlainText(self.file2_content)
            
            # Enable compare button if both files loaded
            self._check_enable_compare()
            
        except Exception as e:
            print(f"Error loading file 2: {e}")
            self.file2_label.setText("Error loading file")
    
    def _check_enable_compare(self):
        """Enable compare button if both files are loaded."""
        if self.file1_path and self.file2_path:
            self.btn_compare.setEnabled(True)
        else:
            self.btn_compare.setEnabled(False)
    
    # ═══════════════════════════════════════════════════════════
    # COMPARISON LOGIC
    # ═══════════════════════════════════════════════════════════
    
    def compare_files(self):
        """Perform file comparison and highlight differences."""
        if not self.file1_path or not self.file2_path:
            return
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.comparison_started.emit()
        
        # Disable buttons during comparison
        self.btn_compare.setEnabled(False)
        self.btn_open_file1.setEnabled(False)
        self.btn_open_file2.setEnabled(False)
        
        # Use QTimer to allow UI to update
        QTimer.singleShot(100, self._perform_comparison)
            
    def _perform_comparison(self):
        """Actual comparison logic (uses SequenceMatcher opcodes)."""
        try:
            # Split into lines
            lines1 = self.file1_content.splitlines()
            lines2 = self.file2_content.splitlines()

            # Update progress
            self.progress_bar.setValue(20)

            # Use SequenceMatcher to get line-level opcodes (no '? ' intraline markers)
            sm = difflib.SequenceMatcher(None, lines1, lines2)
            opcodes = sm.get_opcodes()

            self.progress_bar.setValue(50)

            # Highlight differences from opcodes
            self._highlight_differences_from_opcodes(opcodes)

            self.progress_bar.setValue(80)

            # Update statistics from opcodes
            self._update_statistics_from_opcodes(opcodes, lines1, lines2)

            self.progress_bar.setValue(100)

        except Exception as e:
            print(f"Error during comparison: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Hide progress bar and re-enable buttons
            QTimer.singleShot(500, self._finish_comparison)


    def _highlight_differences_from_opcodes(self, opcodes):
        """Highlight differences in both editors using SequenceMatcher opcodes."""
        # Reset editors (this also clears old formatting)
        self.editor1.setPlainText(self.file1_content)
        self.editor2.setPlainText(self.file2_content)

        # Prepare formats
        added_format = QTextCharFormat()
        added_format.setBackground(QColor("#90EE90"))  # Light green

        removed_format = QTextCharFormat()
        removed_format.setBackground(QColor("#FFB6C6"))  # Light red

        modified_format = QTextCharFormat()
        modified_format.setBackground(QColor("#FFD700"))  # Gold

        doc1 = self.editor1.document()
        doc2 = self.editor2.document()

        # Batch updates
        # We create new cursors for each block selection as needed (safer)
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                continue

            # Replaced lines -> mark both sides as modified
            if tag == 'replace':
                # file1 lines i1..i2-1
                for ln in range(i1, i2):
                    block = doc1.findBlockByNumber(ln)
                    if not block.isValid():
                        continue
                    c = QTextCursor(doc1)
                    c.setPosition(block.position())
                    c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    c.setCharFormat(modified_format)

                # file2 lines j1..j2-1
                for ln in range(j1, j2):
                    block = doc2.findBlockByNumber(ln)
                    if not block.isValid():
                        continue
                    c = QTextCursor(doc2)
                    c.setPosition(block.position())
                    c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    c.setCharFormat(modified_format)

            # Deleted from file2 => highlight in file1 as removed
            elif tag == 'delete':
                for ln in range(i1, i2):
                    block = doc1.findBlockByNumber(ln)
                    if not block.isValid():
                        continue
                    c = QTextCursor(doc1)
                    c.setPosition(block.position())
                    c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    c.setCharFormat(removed_format)

            # Inserted into file2 => highlight in file2 as added
            elif tag == 'insert':
                for ln in range(j1, j2):
                    block = doc2.findBlockByNumber(ln)
                    if not block.isValid():
                        continue
                    c = QTextCursor(doc2)
                    c.setPosition(block.position())
                    c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    c.setCharFormat(added_format)


    def _update_statistics_from_opcodes(self, opcodes, lines1, lines2):
        """Update statistics panel using opcodes."""
        added = sum((j2 - j1) for tag, i1, i2, j1, j2 in opcodes if tag == 'insert')
        removed = sum((i2 - i1) for tag, i1, i2, j1, j2 in opcodes if tag == 'delete')
        # For replaced lines count them as modified; use the maximum of the two sides to reflect visible lines
        modified = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in opcodes if tag == 'replace')
        unchanged = sum((i2 - i1) for tag, i1, i2, j1, j2 in opcodes if tag == 'equal')

        total_lines1 = len(lines1)
        total_lines2 = len(lines2)

        stats_text = (f"File 1: {total_lines1} lines | "
                      f"File 2: {total_lines2} lines | "
                      f"Added: {added} | "
                      f"Removed: {removed} | "
                      f"Modified: {modified} | "
                      f"Unchanged: {unchanged}")

        self.stats_label.setText(stats_text)
        
    
    def _finish_comparison(self):
        """Re-enable UI after comparison."""
        self.progress_bar.setVisible(False)
        self.btn_compare.setEnabled(True)
        self.btn_open_file1.setEnabled(True)
        self.btn_open_file2.setEnabled(True)
        self.comparison_finished.emit()
