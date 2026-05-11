# pdf_comparison.py  
import difflib
import fitz  # PyMuPDF
import os
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QMessageBox, QSplitter, QScrollArea, QFrame, QProgressBar,
    QApplication, QFileDialog, QDialog, QListWidget, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

def pixmap_to_qpixmap(pix):
    """Convert PyMuPDF pixmap to QPixmap safely."""
    img_bytes = pix.tobytes("ppm")
    qimg = QImage.fromData(img_bytes)
    if qimg.isNull():
        #print("Warning: QImage.fromData returned null")
        return QPixmap()
    return QPixmap.fromImage(qimg)

class PDFComparisonWorker(QThread):
    """Worker thread for PDF comparison to avoid UI blocking"""
    progress_updated = pyqtSignal(int)
    comparison_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, doc1, doc2):
        super().__init__()
        self.doc1 = doc1
        self.doc2 = doc2
        self.is_running = True
    
    def run(self):
        try:
            max_pages = min(len(self.doc1), len(self.doc2))
            results = {}
            
            for page_num in range(max_pages):
                if not self.is_running:
                    break
                
                progress = int((page_num / max_pages) * 100)
                self.progress_updated.emit(progress)
                
                # Get text sequences for comparison
                words1, text1_seq = self.page_text_words(self.doc1, page_num)
                words2, text2_seq = self.page_text_words(self.doc2, page_num)
                
                # Compute differences using difflib
                diff = list(difflib.ndiff(text1_seq, text2_seq))
                
                # Determine if page has changes
                has_changes = any(line.startswith(('+ ', '- ')) for line in diff)
                
                results[page_num] = {
                    'words1': words1,
                    'words2': words2,
                    'text1_seq': text1_seq,
                    'text2_seq': text2_seq,
                    'diff': diff,
                    'has_changes': has_changes
                }
                
                self.msleep(10)
            
            if self.is_running:
                self.progress_updated.emit(100)
                self.comparison_finished.emit(results)
        except Exception as e:
            if self.is_running:
                self.error_occurred.emit(str(e))
    
    def stop(self):
        """Stop the worker thread gracefully"""
        self.is_running = False
    
    def page_text_words(self, doc, page_num):
        """Return list of words (with positions) and sequence for diff."""
        try:
            page = doc[page_num]
            words = page.get_text("words")
            words_sorted = sorted(words, key=lambda w: (w[1], w[0]))
            text_seq = [w[4] for w in words_sorted]
            return words_sorted, text_seq
        except Exception as e:
            print(f"Error extracting words from page {page_num}: {e}")
            return [], []

class PDFComparisonViewerSimplified(QWidget):
    """Simplified PDF Comparison viewer with file picker buttons and comparison button"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.doc1 = None
        self.doc2 = None
        self.pdf1_path = None
        self.pdf2_path = None
        self.current_page = 0
        self.comparison_results = {}
        self.comparison_worker = None
        self.zoom_level = 1.0  # Default zoom level
        self.setup_ui()
        self.dump_widget_tree()
        self.show_hierarchy_to_main(self.left_viewer, "Left PDF Viewer")
        self.show_hierarchy_to_main(self.right_viewer, "Right PDF Viewer")
    
    def setup_ui(self):
        """Setup the simplified comparison viewer UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # Progress bar row
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Main comparison area
        comparison_splitter = QSplitter(Qt.Horizontal)
        comparison_splitter.setChildrenCollapsible(False)

        self.left_viewer = self.create_pdf_viewer("PDF 1")
        comparison_splitter.addWidget(self.left_viewer)

        self.right_viewer = self.create_pdf_viewer("PDF 2")
        comparison_splitter.addWidget(self.right_viewer)

        comparison_splitter.setSizes([400, 400])
        layout.addWidget(comparison_splitter, 1)

        # Status bar – fixed height
        self.status_label = QLabel("Select PDF files using the buttons above, then click Compare to start")
        self.status_label.setFixedHeight(28)                     # Fixed height
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.status_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )                                                       # Never expand vertically
        self.status_label.setStyleSheet("""
            QLabel { 
                padding: 5px; 
                background-color: #f0f0f0; 
                border: 1px solid #ccc; 
            }
        """)
        layout.addWidget(self.status_label)

        # Setup synchronized scrolling
        self.setup_synchronized_scrolling()
    
    def dump_widget_tree(self, widget=None, indent=0):
        if widget is None:
            widget = self
        name = widget.objectName() or "<no-name>"
        #print("  " * indent + f"{widget.__class__.__name__} ({name})")
        for child in widget.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            self.dump_widget_tree(child, indent + 1)
    
    def show_hierarchy_to_main(self, widget, label=None):
        #print(f"\n== Hierarchy for {label or widget.objectName() or widget.__class__.__name__} ==")
        w = widget
        while w is not None:
            #print(f"{w.__class__.__name__} (objectName={w.objectName()!r})")
            w = w.parentWidget()
    
    def create_control_panel(self):
        """Create control panel with file picker buttons, comparison controls and navigation"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(panel)
        layout.setSpacing(20)

        # --- Common button height ---
        BUTTON_HEIGHT = 32

        # --- PDF 1 button ---
        self.btn_pdf1 = QPushButton("Open PDF 1")
        self.btn_pdf1.setFixedHeight(BUTTON_HEIGHT)
        self.btn_pdf1.setStyleSheet("""
            QPushButton {
                padding: 0 16px;
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        self.btn_pdf1.clicked.connect(self.select_pdf1)
        layout.addWidget(self.btn_pdf1)

        layout.addStretch()

        # --- Zoom controls (keep fixed 30×30) ---
        zoom_widget = QWidget()
        zoom_layout = QHBoxLayout(zoom_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(5)

        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setFixedHeight(30)
        self.zoom_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        zoom_layout.addWidget(self.zoom_label)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.zoom_in_btn)

        layout.addWidget(zoom_widget)

        layout.addStretch()
        
        # --- Compare button ---
        self.compare_btn = QPushButton("Compare PDFs")
        self.compare_btn.setEnabled(False)
        self.compare_btn.setFixedHeight(BUTTON_HEIGHT)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                padding: 0 20px;
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.compare_btn.clicked.connect(self.manual_start_comparison)
        layout.addWidget(self.compare_btn)

        layout.addStretch()
        

        # --- Navigation section ---
        nav_section = QHBoxLayout()
        nav_section.setSpacing(5)

        self.btn_prev = QPushButton("◀ Previous")
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setEnabled(False)
        self.btn_prev.setFixedHeight(BUTTON_HEIGHT)
        self.btn_prev.setStyleSheet("QPushButton { padding: 0 10px; }")
        nav_section.addWidget(self.btn_prev)

        self.page_label = QLabel("Page: 0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(100)
        self.page_label.setFixedHeight(30)
        self.page_label.setStyleSheet("""
            QLabel { 
                padding: 5px; 
                background-color: #f5f5f5; 
                border: 1px solid #ccc; 
                border-radius: 3px;
            }
        """)
        nav_section.addWidget(self.page_label)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setEnabled(False)
        self.btn_next.setFixedHeight(BUTTON_HEIGHT)
        self.btn_next.setStyleSheet("QPushButton { padding: 0 10px; }")
        nav_section.addWidget(self.btn_next)

        layout.addLayout(nav_section)
        
        layout.addStretch()
        
        # --- PDF 2 button ---
        self.btn_pdf2 = QPushButton("Open PDF 2")
        self.btn_pdf2.setFixedHeight(BUTTON_HEIGHT)
        self.btn_pdf2.setStyleSheet("""
            QPushButton {
                padding: 0 16px;
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.btn_pdf2.clicked.connect(self.select_pdf2)
        layout.addWidget(self.btn_pdf2)

        layout.addSpacing(20)
        
        panel.setFixedHeight(56)
        
        return panel
    
    def create_pdf_viewer(self, title):
        """Create a PDF viewer panel"""
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 10)
        
        # Title with color coding - will be updated with filename
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        if title == "PDF 1":
            title_label.setStyleSheet("""
                QLabel { 
                    padding: 5px; 
                    background-color: #e3f2fd; 
                    border-bottom: 2px solid #2196f3;
                    color: #1565c0;
                }
            """)
            self.left_title_label = title_label
        elif title.strip().lower() == "pdf 2":
            title_label.setStyleSheet("""
                QLabel { 
                    padding: 5px; 
                    background-color: #fff3e0; 
                    border-bottom: 2px solid #ff9800;
                    color: #e65100;
                }
            """)
            self.right_title_label = title_label
        layout.addWidget(title_label)
        
        # Scroll area for PDF content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(False)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setMinimumSize(300, 400)
        
        # PDF display label
        pdf_label = QLabel("No PDF selected")
        pdf_label.setAlignment(Qt.AlignCenter)
        pdf_label.setStyleSheet("QLabel { color: #666; font-size: 12px; padding: 20px; }")
        pdf_label.setMinimumSize(250, 350)
        
        scroll_area.setWidget(pdf_label)
        layout.addWidget(scroll_area)
        
        # Store references
        if title == "PDF 1":
            self.left_scroll = scroll_area
            self.left_label = pdf_label
            self.left_scroll_area = scroll_area   # same ref, clearer name
        else:
            self.right_scroll = scroll_area
            self.right_label = pdf_label
            self.right_scroll_area = scroll_area
    
        return container
    
    def select_pdf1(self):
        """Select first PDF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select First PDF", 
            "", 
            "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.pdf1_path = file_path
            filename = os.path.basename(file_path)
            self.left_title_label.setText(filename)
            self.load_pdf1(file_path)
    
    def select_pdf2(self):
        """Select second PDF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Second PDF", 
            "", 
            "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.pdf2_path = file_path
            filename = os.path.basename(file_path)
            self.right_title_label.setText(filename)
            self.load_pdf2(file_path)
    
    def load_pdf1(self, file_path):
        """Load first PDF and display it immediately"""
        try:
            if self.doc1:
                self.doc1.close()
            self.doc1 = fitz.open(file_path)
            # Display first page immediately
            self.display_pdf_page(self.doc1, 0, self.left_label, self.left_scroll)
            self.check_compare_button_state()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF 1:\n{str(e)}")
            self.left_title_label.setText("PDF 1: Error loading")
    
    def load_pdf2(self, file_path):
        """Load second PDF and display it immediately"""
        try:
            if self.doc2:
                self.doc2.close()
            self.doc2 = fitz.open(file_path)
            # Display first page immediately
            self.display_pdf_page(self.doc2, 0, self.right_label, self.right_scroll)
            self.check_compare_button_state()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF 2:\n{str(e)}")
            self.right_title_label.setText("PDF 2: Error loading")
    
    def display_pdf_page(self, doc, page_num, label, scroll_area):
        try:
            if page_num >= len(doc):
                return
            page = doc[page_num]
            zoom_matrix = fitz.Matrix(2 * self.zoom_level, 2 * self.zoom_level)
            pix = page.get_pixmap(matrix=zoom_matrix)
            pixmap = pixmap_to_qpixmap(pix)
            if not pixmap.isNull():
                label.setPixmap(pixmap)
                label.resize(pixmap.size())
                label.adjustSize()
                scroll_area.updateGeometry()
        except Exception as e:
            print(f"Error displaying page {page_num}: {e}")
        
    def check_compare_button_state(self):
        """Enable/disable compare button based on loaded PDFs"""
        if self.doc1 and self.doc2:
            self.compare_btn.setEnabled(True)
            self.status_label.setText("Both PDFs loaded - Click 'Compare PDFs' to start comparison")
        elif self.doc1:
            self.status_label.setText("PDF 1 loaded - Please select PDF 2")
        elif self.doc2:
            self.status_label.setText("PDF 2 loaded - Please select PDF 1")
        else:
            self.compare_btn.setEnabled(False)
    
    def setup_synchronized_scrolling(self):
        """Setup synchronized scrolling between left and right viewers"""
        # Connect scroll bars
        left_vbar = self.left_scroll.verticalScrollBar()
        right_vbar = self.right_scroll.verticalScrollBar()
        left_hbar = self.left_scroll.horizontalScrollBar()
        right_hbar = self.right_scroll.horizontalScrollBar()
        
        # Vertical synchronization
        left_vbar.valueChanged.connect(lambda value: self.sync_scroll(right_vbar, value, 'left_v'))
        right_vbar.valueChanged.connect(lambda value: self.sync_scroll(left_vbar, value, 'right_v'))
        
        # Horizontal synchronization
        left_hbar.valueChanged.connect(lambda value: self.sync_scroll(right_hbar, value, 'left_h'))
        right_hbar.valueChanged.connect(lambda value: self.sync_scroll(left_hbar, value, 'right_h'))
        
        # Track which scrollbar initiated the change to avoid loops
        self._sync_source = None
    
    def sync_scroll(self, target_scrollbar, value, source):
        """Synchronize scroll position between viewers"""
        if self._sync_source != source:
            self._sync_source = source
            target_scrollbar.setValue(value)
            self._sync_source = None
    
    def zoom_in(self):
        """Zoom in both PDFs"""
        self.zoom_level = min(3.0, self.zoom_level + 0.10)
        self.update_zoom_label()
        self.refresh_current_page()
    
    def zoom_out(self):
        """Zoom out both PDFs"""
        self.zoom_level = max(0.5, self.zoom_level - 0.10)
        self.update_zoom_label()
        self.refresh_current_page()
    
    def update_zoom_label(self):
        """Update zoom level label"""
        zoom_percent = int(self.zoom_level * 100)
        self.zoom_label.setText(f"{zoom_percent}%")
    
    def refresh_current_page(self):
        """Refresh current page with new zoom level"""
        if self.comparison_results and self.current_page in self.comparison_results:
            self.show_page(self.current_page)
        elif self.doc1 and self.doc2:
            # If no comparison yet, just refresh the raw display
            self.display_pdf_page(self.doc1, self.current_page, self.left_label, self.left_scroll)
            self.display_pdf_page(self.doc2, self.current_page, self.right_label, self.right_scroll)
            self.left_scroll.updateGeometry()
            self.right_scroll.updateGeometry()
            self.left_scroll.horizontalScrollBar().setValue(0)   # optional
            self.left_scroll.horizontalScrollBar().update()
    
    def manual_start_comparison(self):
        """Start comparison manually when button is clicked"""
        if not (self.doc1 and self.doc2):
            QMessageBox.warning(self, "Warning", "Please load both PDF files first")
            return
        self.start_comparison()
    
    def start_comparison(self):
        """Start the PDF comparison process"""
        if not (self.doc1 and self.doc2):
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Comparing PDFs...")
        self.compare_btn.setEnabled(False)
        
        # Disable navigation during comparison
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        
        # Stop any existing worker
        if self.comparison_worker and self.comparison_worker.isRunning():
            self.comparison_worker.stop()
            self.comparison_worker.wait()
        
        # Start worker thread
        self.comparison_worker = PDFComparisonWorker(self.doc1, self.doc2)
        self.comparison_worker.progress_updated.connect(self.progress_bar.setValue)
        self.comparison_worker.comparison_finished.connect(self.on_comparison_finished)
        self.comparison_worker.error_occurred.connect(self.on_comparison_error)
        self.comparison_worker.start()
    
    def on_comparison_finished(self, results):
        """Handle comparison completion"""
        self.comparison_results = results
        self.progress_bar.setVisible(False)
        self.compare_btn.setEnabled(True)
        
        # Update status
        total_pages = min(len(self.doc1), len(self.doc2))
        changed_pages = sum(1 for r in results.values() if r['has_changes'])
        self.status_label.setText(f"Comparison complete: {changed_pages} of {total_pages} pages have differences")
        
        # Enable navigation
        self.btn_prev.setEnabled(True)
        self.btn_next.setEnabled(True)
        
        # Show first page
        self.current_page = 0
        self.show_page(0)
        self.update_page_counter()
    
    def on_comparison_error(self, error_msg):
        """Handle comparison error"""
        self.progress_bar.setVisible(False)
        self.compare_btn.setEnabled(True)
        self.status_label.setText(f"Comparison failed: {error_msg}")
        QMessageBox.critical(self, "Comparison Error", f"Failed to compare PDFs:\n{error_msg}")
    
    def render_page_with_highlights(self, doc, page_num, reference_text, words):
        """Render PDF page with difference highlights and zoom"""
        try:
            page = doc[page_num]
            # Apply zoom level to matrix
            zoom_matrix = fitz.Matrix(2 * self.zoom_level, 2 * self.zoom_level)
            pix = page.get_pixmap(matrix=zoom_matrix)
            
            # Convert to QPixmap
            img_bytes = pix.tobytes("ppm")
            qimg = QImage.fromData(img_bytes)
            if qimg.isNull():
                return QPixmap()
            pixmap = QPixmap.fromImage(qimg)
            
            # Get current page text and calculate differences
            current_text = [w[4] for w in words]
            diff = list(difflib.ndiff(current_text, reference_text))
            
            changed_indices = set()
            idx = 0
            for token in diff:
                if token.startswith("- "):
                    changed_indices.add(idx)
                    idx += 1
                elif token.startswith("  "):
                    idx += 1
            
            # Draw highlights (adjusted for zoom)
            painter = QPainter()
            try:
                if painter.begin(pixmap):
                    painter.setBrush(QColor(255, 100, 100, 80))
                    painter.setPen(QColor(200, 0, 0))
                    for i, word in enumerate(words):
                        if i in changed_indices:
                            # Scale rectangle coordinates by zoom
                            scale = 2 * self.zoom_level
                            rect = (word[0]*scale, word[1]*scale, 
                                   (word[2]-word[0])*scale, (word[3]-word[1])*scale)
                            painter.drawRect(*map(int, rect))
            finally:
                painter.end()
            return pixmap
        except Exception as e:
            print(f"Error rendering page {page_num}: {e}")
            return QPixmap()
    
    def show_page(self, page_num):
        """Display a specific page with highlights"""
        if not self.comparison_results or page_num not in self.comparison_results:
            return
        
        self.current_page = page_num
        results = self.comparison_results[page_num]
        
        # Render PDFs with highlights and current zoom
        pixmap1 = self.render_page_with_highlights(
            self.doc1, page_num, results['text2_seq'], results['words1']
        )
        if not pixmap1.isNull():
            self.left_label.setPixmap(pixmap1)
            self.left_label.resize(pixmap1.size())
            
        pixmap2 = self.render_page_with_highlights(
            self.doc2, page_num, results['text1_seq'], results['words2']
        )
        if not pixmap2.isNull():
            self.right_label.setPixmap(pixmap2)
            self.right_label.resize(pixmap2.size())
        
        self.current_page = page_num
        self.update_page_counter()
    
    def update_page_counter(self):
        """Update the page counter display"""
        if self.comparison_results:
            total_pages = len(self.comparison_results)
            self.page_label.setText(f"Page: {self.current_page + 1} / {total_pages}")
        else:
            self.page_label.setText("Page: 0 / 0")
    
    def next_page(self):
        """Go to next page"""
        if self.comparison_results and self.current_page < len(self.comparison_results) - 1:
            self.show_page(self.current_page + 1)
    
    def prev_page(self):
        """Go to previous page"""
        if self.comparison_results and self.current_page > 0:
            self.show_page(self.current_page - 1)
        
    def closeEvent(self, event):
        """Handle widget close properly"""
        try:
            if hasattr(self, 'doc1') and self.doc1:
                self.doc1.close()
            if hasattr(self, 'doc2') and self.doc2:
                self.doc2.close()
            if hasattr(self, 'comparison_worker') and self.comparison_worker:
                if self.comparison_worker.isRunning():
                    self.comparison_worker.stop()
                    self.comparison_worker.wait()
        except:
            pass
        super().closeEvent(event)
