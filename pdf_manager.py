# pdf_manager.py
"""
PDF Manager - Handles PDF viewer creation, management, and operations
"""
import sys
import os
from PyQt5.QtWidgets import (
    QTabWidget, QVBoxLayout, QWidget, QLabel, QSplitter, QTextEdit, 
    QMenu, QAction, QFileDialog, QApplication, QSizePolicy, QMessageBox,
    QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, QObject, QEvent
from PyQt5.QtGui import QFont
from pdf_viewer import PDFViewer


class HVModeAltArrowFilter(QObject):
    """Application-level filter to catch Alt+Arrow in H/V mode before anyone else"""
    
    def __init__(self, pdf_manager):
        super().__init__()
        self.pdf_manager = pdf_manager
    
    def eventFilter(self, obj, event):
        """Intercept Alt+Arrow at the application level"""
        if event.type() == QEvent.KeyPress:
            # Only handle if in H/V mode
            if self.pdf_manager.pdf_layout_mode not in ["horizontal", "vertical"]:
                return False
            
            # Check for Alt+Arrow
            if int(event.modifiers() & Qt.AltModifier) == int(Qt.AltModifier):
                if event.key() in [Qt.Key_Left, Qt.Key_Right]:
                    direction = "Left" if event.key() == Qt.Key_Left else "Right"
                    #print(f"🌍 APP FILTER: Caught Alt+{direction} in H/V mode")
                    
                    # Find the active PDF viewer
                    viewer = self._find_active_viewer()
                    if viewer:
                        #print(f"   Found active viewer, calling navigate_{'back' if event.key() == Qt.Key_Left else 'forward'}()")
                        if event.key() == Qt.Key_Left:
                            viewer.navigate_back()
                        else:
                            viewer.navigate_forward()
                        event.accept()
                        return True  # Consume the event
                    #else:
                    #    print(f"   ⚠️ No active viewer found")
        
        return False
    
    def _find_active_viewer(self):
        """Find the currently active PDF viewer"""
        # Method 1: Check focused widget
        focused = QApplication.focusWidget()
        if focused:
            # Walk up the parent tree looking for PDFViewer
            widget = focused
            while widget:
                if hasattr(widget, '__class__') and 'PDFViewer' in widget.__class__.__name__:
                    if widget.isVisible() and hasattr(widget, 'pdf_document') and widget.pdf_document:
                        return widget
                widget = widget.parent()
        
        # Method 2: Check current viewer from pdf_manager
        if hasattr(self.pdf_manager, 'get_current_viewer'):
            viewer = self.pdf_manager.get_current_viewer()
            if viewer and viewer.isVisible():
                return viewer
        
        # Method 3: Find most recently clicked viewer
        if hasattr(self.pdf_manager, 'pdf_files'):
            candidates = []
            for pdf_path, data in self.pdf_manager.pdf_files.items():
                if isinstance(data, dict):
                    viewer = data.get('viewer')
                    if viewer and viewer.isVisible():
                        if hasattr(viewer, '_last_click_time'):
                            candidates.append((viewer._last_click_time, viewer))
            
            if candidates:
                candidates.sort(reverse=True, key=lambda x: x[0])
                from time import time
                most_recent_time, most_recent_viewer = candidates[0]
                # Only use if clicked within last 10 seconds
                if time() - most_recent_time < 10.0:
                    return most_recent_viewer
        
        return None
        
class GlobalPDFClickMonitor(QObject):
    """Monitor all mouse clicks to track which PDF viewer was clicked"""
    
    def __init__(self, pdf_manager):
        super().__init__()
        self.pdf_manager = pdf_manager
    
    def eventFilter(self, obj, event):
        """Track clicks on any PDF viewer"""
        if event.type() == QEvent.MouseButtonPress:
            # Find which viewer was clicked
            viewer = self._find_viewer_for_widget(obj)
            if viewer:
                from time import time
                import os
                
                # Update click time
                viewer._last_click_time = time()
                
                # Ensure pdf_path is set
                if not hasattr(viewer, 'pdf_path') or not viewer.pdf_path:
                    # Try to find it from pdf_files
                    for pdf_path, data in self.pdf_manager.pdf_files.items():
                        if isinstance(data, dict) and data.get('viewer') == viewer:
                            viewer.pdf_path = pdf_path
                            #print(f"   📌 Set pdf_path on viewer: {os.path.basename(pdf_path)}")
                            break
                
                pdf_path = getattr(viewer, 'pdf_path', 'unknown')
                #print(f"🖱️ GLOBAL: Click on viewer: {os.path.basename(pdf_path) if pdf_path != 'unknown' else 'unknown'}")
                #print(f"   _last_click_time = {viewer._last_click_time}")
                
                # Set focus
                viewer.scroll_area.setFocus(Qt.MouseFocusReason)
                viewer.setFocus(Qt.MouseFocusReason)
                # ✅ FIX: Update border highlighting on click
                self.pdf_manager._highlight_active_pdf_viewer(viewer)                
        
        return False
    
    def _find_viewer_for_widget(self, widget):
        """Find the PDFViewer that contains this widget"""
        if not widget:
            return None
        
        # Walk up parent tree
        current = widget
        depth = 0
        while current and depth < 15:
            # Check if this is a PDFViewer
            if hasattr(current, '__class__') and 'PDFViewer' in current.__class__.__name__:
                if hasattr(current, 'pdf_document') and current.pdf_document:
                    return current
            
            # Check if current widget is inside a known wrapper
            if hasattr(self.pdf_manager, 'pdf_files'):
                for pdf_path, data in self.pdf_manager.pdf_files.items():
                    if isinstance(data, dict):
                        viewer = data.get('viewer')
                        wrapper = data.get('wrapper')
                        
                        if wrapper and self._is_inside(widget, wrapper):
                            return viewer
                        
                        if viewer and self._is_inside(widget, viewer):
                            return viewer
            
            current = current.parent()
            depth += 1
        
        return None
    
    def _is_inside(self, child, parent):
        """Check if child is inside parent widget"""
        if not child or not parent:
            return False
        widget = child
        while widget:
            if widget == parent:
                return True
            widget = widget.parent()
        return False
class PDFManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.pdf_files = {}  # {pdf_path: (widget, tab_index, label)}
        self.pdf_layout_mode = "tabbed"  # tabbed, horizontal, vertical
        self.current_sizes = {"pdf": []}
        
        # UI components (will be set by layout manager)
        self.pdf_tabs = None
        self.pdf_splitter = None

            
        # ✅ NEW: Install application-level Alt+Arrow filter for H/V mode
        app = QApplication.instance()
        if app:
            if not hasattr(app, '_hv_alt_arrow_filter'):
                #print("📌 Installing application-level Alt+Arrow filter for H/V mode...")
                self._hv_filter = HVModeAltArrowFilter(self)
                app.installEventFilter(self._hv_filter)
                app._hv_alt_arrow_filter = self._hv_filter
                #print("✅ Application-level Alt+Arrow filter installed")
            
            # ✅ NEW: Install global click monitor
            if not hasattr(app, '_global_pdf_click_monitor'):
                #print("📌 Installing global PDF click monitor...")
                self._click_monitor = GlobalPDFClickMonitor(self)
                app.installEventFilter(self._click_monitor)
                app._global_pdf_click_monitor = self._click_monitor
                #print("✅ Global PDF click monitor installed")
        
        # CRITICAL FIX: Ensure we have a proper parent container ready
        self._ensure_parent_container()

    def eventFilter(self, obj, event):
        """Track clicks on any PDF viewer"""
        if event.type() == QEvent.MouseButtonPress:
            viewer = self._find_viewer_for_widget(obj)
            if viewer:
                from time import time
                import os

                viewer._last_click_time = time()

                if not hasattr(viewer, 'pdf_path') or not viewer.pdf_path:
                    for pdf_path, data in self.pdf_manager.pdf_files.items():
                        if isinstance(data, dict) and data.get('viewer') == viewer:
                            viewer.pdf_path = pdf_path
                            break

                # Set focus
                viewer.scroll_area.setFocus(Qt.MouseFocusReason)
                viewer.setFocus(Qt.MouseFocusReason)

                # ✅ Highlight the clicked PDF viewer
                self.pdf_manager._highlight_active_pdf_viewer(viewer)

        return False    
        
    def setup_ui(self):
        """Create PDF UI components with proper parent hierarchy - FIXED"""
        #self._ensure_parent_container()
        parent_widget = getattr(self.main_window.layout_manager, 'pdf_container', self.main_window)
        
        # Only create UI components if they don't exist and we have a proper parent
        if self.pdf_layout_mode == "tabbed" and self.pdf_tabs is None:
            #parent_widget = getattr(self.main_window.layout_manager, 'pdf_container', self.main_window)
            self.pdf_tabs = QTabWidget(parent_widget)            
            self.pdf_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.pdf_tabs.setTabsClosable(True)
            self.pdf_tabs.tabCloseRequested.connect(self.close_pdf_tab)
            #self.pdf_tabs.setMinimumSize(300, 200)
            # CRITICAL: Add to parent layout immediately
            if hasattr(parent_widget, 'layout') and parent_widget.layout():
                parent_widget.layout().addWidget(self.pdf_tabs)
#                 
        elif self.pdf_layout_mode != "tabbed" and self.pdf_splitter is None:            
            orientation = Qt.Horizontal if self.pdf_layout_mode == "horizontal" else Qt.Vertical
            self.pdf_splitter = QSplitter(orientation, parent_widget)
            self.pdf_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            #self.pdf_splitter.setMinimumSize(300, 200)
            # CRITICAL: Add to parent layout immediately
            if hasattr(parent_widget, 'layout') and parent_widget.layout():
                parent_widget.layout().addWidget(self.pdf_splitter)

    def _highlight_active_pdf_viewer(self, active_viewer=None):
        """Highlight the active PDF viewer with a colored internal border, dim others."""
        ACTIVE_STYLE = "#pdf_v { border: 2px solid #f5817d; }"
        INACTIVE_STYLE = "#pdf_v { border: 2px solid transparent; }"

        for path, data in self.pdf_files.items():
            if not isinstance(data, dict):
                continue
            viewer = data.get('viewer')
            if not viewer:
                continue
            try:
                viewer.setObjectName("pdf_v")
                viewer.setStyleSheet(
                    ACTIVE_STYLE if viewer is active_viewer else INACTIVE_STYLE
                )
            except RuntimeError:
                pass  # Widget was deleted

    def on_pdf_tab_changed(self, index):
        """Handle PDF tab change - update border highlighting"""
        if index < 0 or not self.pdf_tabs:
            return

        widget = self.pdf_tabs.widget(index) if isinstance(self.pdf_tabs, QTabWidget) else None
        if not widget:
            return

        # Only take focus if the user is not currently typing in a spinbox.
        # Stealing focus mid-interaction prevents the spinbox from receiving
        # key events and makes the widget appear unresponsive.
        current_focus = QApplication.focusWidget()
        spinbox_has_focus = (
            current_focus is not None
            and isinstance(current_focus, QSpinBox)
            and current_focus.window() is self.main_window
        )
        if not spinbox_has_focus:
            widget.setFocus(Qt.TabFocusReason)

        # Find the viewer for this widget
        for pdf_path, data in self.pdf_files.items():
            if isinstance(data, dict) and data.get('viewer') is widget:
                self.current_pdf_path = pdf_path
                self._highlight_active_pdf_viewer(widget)
                return
                
    def _ensure_parent_container(self):
        """Ensure we have a proper parent container to prevent popup windows"""
        if not hasattr(self.main_window, 'layout_manager') or not self.main_window.layout_manager:
            return
            
        # Make sure the layout manager has created the pdf_container
        if not hasattr(self.main_window.layout_manager, 'pdf_container') or not self.main_window.layout_manager.pdf_container:
            # Create a temporary container widget with proper parent
            self.main_window.layout_manager.pdf_container = QWidget(self.main_window)
            pdf_layout = QVBoxLayout(self.main_window.layout_manager.pdf_container)
            pdf_layout.setContentsMargins(0, 0, 0, 0)
            self.main_window.layout_manager.pdf_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    def toggle_all_pdf_toolbars(self, visible=None):
        """Toggle visibility of toolbars in all PDF viewers
        Args:
            visible: True to show, False to hide, None to toggle
        """
        if not hasattr(self, 'pdf_files') or not self.pdf_files:
            return
        
        # Determine target state
        if visible is None:
            # Toggle: check first viewer's state
            first_viewer = next((data.get('viewer') for data in self.pdf_files.values() 
                                if isinstance(data, dict) and data.get('viewer')), None)
            if first_viewer:
                visible = not first_viewer.is_toolbar_visible()
            else:
                return
        
        # Apply to all viewers
        for pdf_path, data in self.pdf_files.items():
            if isinstance(data, dict):
                viewer = data.get('viewer')
                if viewer and hasattr(viewer, 'set_toolbar_visible'):
                    viewer.set_toolbar_visible(visible)
        
        # Update status
        status = "shown" if visible else "hidden"
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(f"PDF toolbars {status}")
        
    def open_pdf_file(self):
        """Open an external PDF file - Using refresh logic for foreground"""
        
        # ✅ FIX: Get the directory of the current .tex file using proper method
        default_dir = ""
        if hasattr(self.main_window.editor_manager, 'get_current_file_path'):
            current_tex = self.main_window.editor_manager.get_current_file_path()
            if current_tex and os.path.exists(current_tex):
                default_dir = os.path.dirname(current_tex)
                #print(f"📁 Opening PDF dialog in current tex file's directory: {default_dir}")
        
        # Fallback to last opened directory or home
        if not default_dir:
            if hasattr(self.main_window.editor_manager, 'last_opened_directory'):
                default_dir = self.main_window.editor_manager.last_opened_directory
                #print(f"📁 Opening PDF dialog in last opened directory: {default_dir}")
            else:
                default_dir = os.path.expanduser("~")
                #print(f"📁 Opening PDF dialog in home directory: {default_dir}")
        
        path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            self.main_window.translations[self.main_window.menu_language]["open_pdf"],
            default_dir,  # ✅ Changed from "" to default_dir
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if path:
            path = os.path.abspath(path)
            
            # ✅ REFRESH THE MENU
            if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'update_recent_pdf_files_menu'):
                self.main_window.menu_manager.update_recent_pdf_files_menu()
            
            # Load the PDF (create viewer if needed)
            viewer = self.load_pdf_in_viewer(path)
            if viewer:
                # ✅ ADD TO RECENT FILES
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.add_recent_pdf_file(path)
                    #print(f"✅ Added to recent PDFs: {os.path.basename(path)}")
                
                # Update the recent files menu
                if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'update_recent_pdf_files_menu'):
                    self.main_window.menu_manager.update_recent_pdf_files_menu()
                
                # ✅ Use the same foreground logic as refresh_pdf()
                if path in self.pdf_files:
                    data = self.pdf_files[path]
                    if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
                        index = data.get('index', -1)
                        if 0 <= index < self.pdf_tabs.count():
                            self.pdf_tabs.setCurrentIndex(index)
                            viewer.setFocus()
                
                self.main_window.update_status_bar(f"PDF opened: {os.path.basename(path)}")
########################
    def synctex_forward_search(self, tex_file, line_number, column_number=1):
        """Perform SyncTeX forward search - jump from TeX source to PDF location
        
        Args:
            tex_file: Path to the .tex file
            line_number: Line number in the .tex file (1-indexed)
            column_number: Column number in the .tex file (1-indexed)
        """
        import subprocess
        import os
        
        if not tex_file or not os.path.exists(tex_file):
            self.main_window.update_status_bar("No TeX file found")
            return
        
        # Determine the PDF path
        pdf_path = os.path.splitext(tex_file)[0] + ".pdf"
        
        if not os.path.exists(pdf_path):
            self.main_window.update_status_bar(f"PDF not found: {os.path.basename(pdf_path)}. Compile first.")
            return
        
        # Check for SyncTeX file
        tex_dir = os.path.dirname(tex_file)
        tex_name = os.path.splitext(os.path.basename(tex_file))[0]
        synctex_file = os.path.join(tex_dir, tex_name + ".synctex.gz")
        
        if not os.path.exists(synctex_file):
            # Try without .gz
            synctex_file = os.path.join(tex_dir, tex_name + ".synctex")
            if not os.path.exists(synctex_file):
                self.main_window.update_status_bar(
                    "SyncTeX file not found. Compile with -synctex=1 option."
                )
                return
        
        try:
            # Run synctex view command
            command = [
                'synctex', 'view',
                '-i', f"{line_number}:{column_number}:{tex_file}",
                '-o', pdf_path
            ]
            
            # ── Suppress console window on Windows ──
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 10,
                'cwd': tex_dir
            }
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = si

            result = subprocess.run(command, **kwargs)   
            
            if result.returncode == 0:
                output = result.stdout.strip()
                #print(f"   Output: {output[:200]}...")  # First 200 chars
                
                if output:
                    self._parse_synctex_forward_output(output, pdf_path)
                else:
                    self.main_window.update_status_bar("No PDF location found for this line")
            else:
                error_msg = result.stderr.strip()
                #print(f"   Error: {error_msg}")
                self.main_window.update_status_bar(f"SyncTeX error: {error_msg}")
                
        except subprocess.TimeoutExpired:
            self.main_window.update_status_bar("SyncTeX timed out")
        except FileNotFoundError:
            self.main_window.update_status_bar("SyncTeX not installed. Install TeX Live or MiKTeX.")
        except Exception as e:
            print(f"❌ SyncTeX forward search error: {e}")
            import traceback
            traceback.print_exc()
            self.main_window.update_status_bar(f"SyncTeX error: {str(e)}")

    def _run_silent(command, cwd=None, timeout=10):
        """Run a subprocess silently on Windows (no console window)."""
        kwargs = {"capture_output": True, "text": True, "timeout": timeout}
        if cwd:
            kwargs["cwd"] = cwd
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000   # CREATE_NO_WINDOW
        return subprocess.run(command, **kwargs)

    def _parse_synctex_forward_output(self, output, pdf_path):
        """Parse SyncTeX forward search output and jump to PDF location
        
        Args:
            output: Raw output from synctex view command
            pdf_path: Path to the PDF file
        """
        try:
            lines = output.strip().split('\n')
            
            page_num = None
            x_coord = None
            y_coord = None
            h_coord = None  # horizontal position
            v_coord = None  # vertical position
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('Page:'):
                    try:
                        page_num = int(line[5:].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('x:'):
                    try:
                        x_coord = float(line[2:].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('y:'):
                    try:
                        y_coord = float(line[2:].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('h:'):
                    try:
                        h_coord = float(line[2:].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('v:'):
                    try:
                        v_coord = float(line[2:].strip())
                    except (ValueError, IndexError):
                        pass
            
            #print(f"   Parsed: page={page_num}, x={x_coord}, y={y_coord}, h={h_coord}, v={v_coord}")
            
            if page_num is not None:
                # Convert to 0-indexed page number
                page_index = page_num - 1
                
                # Load/focus the PDF if not already open
                viewer = self.load_pdf_in_viewer(pdf_path, bring_to_front=True)
                
                if viewer:
                    # Use v (vertical) coordinate if available, otherwise y
                    target_y = v_coord if v_coord is not None else y_coord
                    
                    if target_y is not None:
                        # Jump to the specific location
                        viewer.jump_to_synctex_location(page_index, h_coord or 0, target_y)
                    else:
                        # Just jump to the page
                        viewer.scroll_to_page(page_index)
                    
                    self.main_window.update_status_bar(
                        f"Jumped to page {page_num} in {os.path.basename(pdf_path)}"
                    )
                else:
                    self.main_window.update_status_bar(f"Could not open PDF: {os.path.basename(pdf_path)}")
            else:
                self.main_window.update_status_bar("Could not parse SyncTeX output - no page found")
                
        except Exception as e:
            print(f"❌ Error parsing SyncTeX forward output: {e}")
            import traceback
            traceback.print_exc()
            self.main_window.update_status_bar(f"Error parsing SyncTeX: {str(e)}")
########################            
    def set_toolbar_visible_state(self, visible):
        """Store toolbar visibility state for new viewers"""
        self._toolbar_visible_state = visible
        
    def load_pdf_in_viewer(self, pdf_path, bring_to_front=True):
        """Load PDF in viewer - Each PDF gets its own dedicated viewer
        Args:
            pdf_path: Path to the PDF file
            bring_to_front: Whether to bring this PDF to foreground (default: True)
        """
        if not os.path.exists(pdf_path):
            #print(f"❌ PDF file not found: {pdf_path}")
            return None
            
        pdf_path = os.path.abspath(pdf_path)
        
        # Remove welcome tab when opening a PDF
        self._remove_welcome_tab_if_exists()
        
        # ✅ FIX: Find existing PDF entry using case-insensitive comparison
        existing_pdf_key = self._find_pdf_by_path(pdf_path)
        
        # If PDF is already open
        if existing_pdf_key:
            data = self.pdf_files[existing_pdf_key]
            viewer = data.get('viewer')
            
            if viewer:
                #print(f"📄 PDF already loaded: {os.path.basename(pdf_path)}")
                if bring_to_front:
                    #print(f"🔄 Bringing existing PDF to foreground...")
                    self._bring_pdf_to_foreground(viewer, data)
                
                # ✅ Update the key to use current case if different
                if existing_pdf_key != pdf_path:
                    #print(f"🔧 Updating PDF key case from {existing_pdf_key} to {pdf_path}")
                    self.pdf_files[pdf_path] = self.pdf_files.pop(existing_pdf_key)
                
                return viewer
            else:
                # Viewer is None, remove stale entry and reload
                #print(f"⚠️  Stale PDF entry found, reloading: {os.path.basename(pdf_path)}")
                del self.pdf_files[existing_pdf_key]
                
        # Create new viewer
        #print(f"📄 Creating new PDF viewer for: {os.path.basename(pdf_path)}")
        viewer = PDFViewer(self.main_window)
####
        # ✅ Enable drag-and-drop on each PDF viewer
        viewer.setAcceptDrops(True)
        pdf_mgr = self

        original_drag_enter = viewer.dragEnterEvent
        original_drag_move = viewer.dragMoveEvent
        original_drop = viewer.dropEvent

        def viewer_drag_enter(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile() and url.toLocalFile().lower().endswith('.pdf'):
                        event.acceptProposedAction()
                        return
            original_drag_enter(event)

        def viewer_drag_move(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile() and url.toLocalFile().lower().endswith('.pdf'):
                        event.acceptProposedAction()
                        return
            original_drag_move(event)

        def viewer_drop(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    if file_path and os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                        pdf_mgr.load_pdf_in_viewer(file_path, bring_to_front=True)
                        if hasattr(pdf_mgr.main_window, 'config_manager'):
                            pdf_mgr.main_window.config_manager.add_recent_pdf_file(file_path)
                event.acceptProposedAction()
                return
            original_drop(event)

        viewer.dragEnterEvent = viewer_drag_enter
        viewer.dragMoveEvent = viewer_drag_move
        viewer.dropEvent = viewer_drop


####
        # ✅ CRITICAL FIX: Load PDF content BEFORE adding to UI
        if not viewer.load_pdf(pdf_path):
            #print(f"❌ Failed to load PDF content for: {os.path.basename(pdf_path)}")
            return None
            
        if hasattr(self, '_toolbar_visible_state'):
            viewer.set_toolbar_visible(self._toolbar_visible_state)    

        # ✅ ADD THIS: Apply saved zoom factor to new viewer (after loading)
        if hasattr(self, 'current_zoom_factor') and self.current_zoom_factor != 1.0:
            viewer.zoom_factor = self.current_zoom_factor
            viewer.render_all_pages()  # Re-render with correct zoom
            #print(f"📊 Applied saved zoom factor to new viewer: {self.current_zoom_factor}")
        elif hasattr(self.main_window, 'config_manager'):
            saved_zoom = self.main_window.config_manager.get_pdf_zoom_factor(default=1.0)
            if saved_zoom != 1.0:
                viewer.zoom_factor = saved_zoom
                viewer.render_all_pages()  # Re-render with correct zoom
                #print(f"📊 Applied config zoom factor to new viewer: {saved_zoom}")


        # Add to UI based on layout mode
        if self.pdf_layout_mode == "tabbed":
            tab_index = self.pdf_tabs.addTab(viewer, os.path.basename(pdf_path))
            self.pdf_tabs.setTabsClosable(True)
            if bring_to_front:
                #print(f"🔄 Setting tab {tab_index} as current and focusing...")
                self.pdf_tabs.setCurrentIndex(tab_index)
                viewer.setFocus()
                self._ensure_pdf_widget_focus(viewer)
            wrapper = None
        else:
            wrapper = self._create_pdf_wrapper(viewer, pdf_path, parent_widget=self.pdf_splitter)
            self.pdf_splitter.addWidget(wrapper)
            if bring_to_front:
                viewer.setFocus()
                self._ensure_pdf_widget_focus(viewer)

        # Store PDF data
        pdf_type = 'tex_generated' if self._is_tex_generated_pdf(pdf_path) else 'external'
        self.pdf_files[pdf_path] = {
            'viewer': viewer,
            'index': self.pdf_tabs.indexOf(viewer) if self.pdf_layout_mode == "tabbed" else None,
            'wrapper': wrapper,
            'pdf_type': pdf_type
        }
        
        # ✅ Highlight this viewer as the active one
        self._highlight_active_pdf_viewer(viewer)
        
        
        # Update current PDF path
        self.current_pdf_path = pdf_path
        self.main_window.update_status_bar(f"PDF loaded: {os.path.basename(pdf_path)}")
        
        # Recreate PDF container  (may replace self.pdf_tabs with a new QTabWidget)
        #self.main_window.layout_manager._recreate_pdf_container()
        # Just ensure signals are connected on existing pdf_tabs
        if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
            try:
                self.pdf_tabs.currentChanged.disconnect(self.on_pdf_tab_changed)
            except (TypeError, RuntimeError):
                pass
            self.pdf_tabs.currentChanged.connect(self.on_pdf_tab_changed)
            try:
                self.pdf_tabs.tabBarClicked.disconnect(self._on_pdf_tab_bar_clicked)
            except (TypeError, RuntimeError):
                pass
            self.pdf_tabs.tabBarClicked.connect(self._on_pdf_tab_bar_clicked)        

        # ✅ FIX: Connect tab-change signal AFTER recreation so it's on the
        #         current self.pdf_tabs, not the one that was just replaced.
        if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
            try:
                self.pdf_tabs.currentChanged.disconnect(self.on_pdf_tab_changed)
            except (TypeError, RuntimeError):
                pass
            self.pdf_tabs.currentChanged.connect(self.on_pdf_tab_changed)

            try:
                self.pdf_tabs.tabBarClicked.disconnect(self._on_pdf_tab_bar_clicked)
            except (TypeError, RuntimeError):
                pass
            self.pdf_tabs.tabBarClicked.connect(self._on_pdf_tab_bar_clicked)

        # Add external PDFs to recent files
        if pdf_type == 'external' and hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.add_recent_pdf_file(pdf_path)
            #print(f"✅ Added external PDF to recent files: {os.path.basename(pdf_path)}")
        
        return viewer

    def _on_pdf_tab_bar_clicked(self, index):
        """Handle a direct click on a PDF tab-bar entry (fires even if already selected)."""
        if not self.pdf_tabs or not isinstance(self.pdf_tabs, QTabWidget):
            return
        widget = self.pdf_tabs.widget(index)
        if not widget:
            return
        for pdf_path, data in self.pdf_files.items():
            if isinstance(data, dict) and data.get('viewer') is widget:
                self.current_pdf_path = pdf_path
                self._highlight_active_pdf_viewer(widget)
                return

    def _find_pdf_by_path(self, pdf_path):
        """Find PDF entry in self.pdf_files using case-insensitive comparison on Windows
        
        Returns:
            The matching key from self.pdf_files, or None if not found
        """
        if not pdf_path:
            return None
        
        # Normalize the search path
        search_path = os.path.normpath(os.path.abspath(pdf_path))
        
        # Search through existing PDF files
        for existing_path in self.pdf_files.keys():
            existing_normalized = os.path.normpath(os.path.abspath(existing_path))
            
            # On Windows, compare case-insensitively
            if os.name == 'nt':
                if search_path.lower() == existing_normalized.lower():
                    return existing_path
            else:
                if search_path == existing_normalized:
                    return existing_path
        
        return None
    


    
    
    def _clean_stale_pdf_references(self):
        """Remove stale PDF references from pdf_files dict"""
        #print(f"DEBUG: _clean_stale_pdf_references called")
        if not hasattr(self, 'pdf_files') or not self.pdf_files:
            #print(f"DEBUG: No pdf_files to clean")
            return
        
        #print(f"DEBUG: Checking {len(self.pdf_files)} PDF references:")
        #for path in self.pdf_files.keys():
        #    print(f"  - {path}")
        
        stale_paths = []
        for pdf_path, data in list(self.pdf_files.items()):
            #print(f"DEBUG: Checking PDF: {pdf_path}")
            
            # Check if file still exists
            if not os.path.exists(pdf_path):
                #print(f"DEBUG: File doesn't exist: {pdf_path}")
                stale_paths.append(pdf_path)
                continue
            
            # Check if viewer widget still exists and is valid
            if isinstance(data, dict):
                viewer = data.get('viewer')
                #print(f"DEBUG: Viewer for {pdf_path}: {viewer}")
                if viewer is None:
                    #print(f"DEBUG: Viewer is None for: {pdf_path}")
                    stale_paths.append(pdf_path)
                elif not hasattr(viewer, 'isVisible'):
                    #print(f"DEBUG: Viewer has no isVisible method for: {pdf_path}")
                    stale_paths.append(pdf_path)
                else:
                    if hasattr(viewer, 'parent') and viewer.parent() is None:
                        #print(f"DEBUG: Viewer has no parent (orphaned) for: {pdf_path}")
                        stale_paths.append(pdf_path)
                #else:
                #    print(f"DEBUG: Viewer appears valid for: {pdf_path}")
            else:
                #print(f"DEBUG: Data is not dict for: {pdf_path}")
                stale_paths.append(pdf_path)
        
        # Remove stale references
        #print(f"DEBUG: Found {len(stale_paths)} stale references to remove")
        for path in stale_paths:
            if path in self.pdf_files:
                del self.pdf_files[path]
                #print(f"DEBUG: Removed stale PDF reference: {path}")
        
    def _get_active_pdf_count(self):
        """Get count of actually active PDFs (not just dictionary entries)"""
        #print(f"DEBUG: _get_active_pdf_count called")
        self._clean_stale_pdf_references()
        count = len(self.pdf_files)
        #print(f"DEBUG: Active PDF count: {count}")
        return count


    def _bring_pdf_to_foreground(self, viewer, data):
        """Bring an already open PDF to the foreground"""
        try:
            if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
                index = data.get('index', -1)
                if index == -1:
                    # Try to find the tab index by the viewer widget
                    index = self.pdf_tabs.indexOf(viewer)
                    if index != -1:
                        data['index'] = index  # Update stored index
                
                if 0 <= index < self.pdf_tabs.count():
                    self.pdf_tabs.setCurrentIndex(index)
                    #print(f"✅ Brought PDF tab to foreground: index {index}")
            
            # Set focus and ensure visibility
            viewer.setFocus()
            self._ensure_pdf_widget_focus(viewer)
            
            # Update current path
            pdf_path = None
            for path, pdf_data in self.pdf_files.items():
                if pdf_data.get('viewer') == viewer:
                    pdf_path = path
                    break
            
            if pdf_path:
                self.current_pdf_path = pdf_path
                self.main_window.update_status_bar(f"PDF focused: {os.path.basename(pdf_path)}")
                
            # ✅ Highlight the active PDF viewer border
            self._highlight_active_pdf_viewer(viewer)    
                
        except Exception as e:
            print(f"❌ Error bringing PDF to foreground: {e}")

    def _ensure_pdf_widget_focus(self, viewer):
        """Ensure the PDF widget and its main window have proper focus"""
        try:
            # Set focus to the viewer
            viewer.setFocus()
            
            # Ensure the main window is active
            if hasattr(self.main_window, 'activateWindow'):
                self.main_window.activateWindow()
            
            # Raise the main window to top
            if hasattr(self.main_window, 'raise_'):
                self.main_window.raise_()
            
            # For Qt widgets, sometimes we need to call show() to ensure visibility
            if hasattr(viewer, 'show'):
                viewer.show()
                
            #print(f"✅ Enhanced focus applied to PDF viewer")
            
        except Exception as e:
            print(f"⚠️  Error in enhanced focus management: {e}")

    # ✅ Fixed method to get all currently open PDFs (for session saving)
    def get_all_open_pdfs(self):
        """Get information about all currently open PDFs"""
        open_pdfs = []
        
        #print(f"🔍 get_all_open_pdfs called")
        #print(f"📄 self.pdf_files exists: {hasattr(self, 'pdf_files')}")
        
        if not hasattr(self, 'pdf_files'):
            #print("❌ pdf_files attribute missing, initializing...")
            self.pdf_files = {}
        
        #print(f"📄 pdf_files content: {len(self.pdf_files)} items")
        
        if self.pdf_files:
            for pdf_path, data in self.pdf_files.items():
                exists = os.path.exists(pdf_path)
                pdf_type = data.get('pdf_type', 'unknown')
                viewer = data.get('viewer')
                
                #print(f"   📄 {os.path.basename(pdf_path)} ({pdf_type}): {'✅' if exists else '❌'} exists, viewer: {viewer is not None}")
                
                pdf_info = {
                    'path': pdf_path,
                    'type': pdf_type,
                    'exists': exists,
                    'viewer': viewer,
                    'active': viewer is not None and hasattr(viewer, 'isVisible') and viewer.isVisible()
                }
                open_pdfs.append(pdf_info)
        #else:
        #    print("📄 No pdf_files found or pdf_files is empty")
        
        #print(f"📄 Returning {len(open_pdfs)} PDF files for session management")
        return open_pdfs
        
    # 4. Enhanced capture_pdf_files_before_cleanup method
    def capture_pdf_files_before_cleanup(self):
        """Capture PDF files before cleanup for session saving"""
        #print("🔄 Capturing PDF files before cleanup...")
        
        if not hasattr(self, '_captured_pdf_files'):
            self._captured_pdf_files = {}
        
        # Get PDFs from pdf_manager
        if hasattr(self, 'pdf_manager'):
            pdf_list = self.pdf_manager.get_all_open_pdfs()
            print(f"📄 Found {len(pdf_list)} PDFs from pdf_manager")
            
            for pdf_info in pdf_list:
                pdf_path = pdf_info['path']
                pdf_type = pdf_info['type']
                exists = pdf_info['exists']
                active = pdf_info.get('active', False)
                
                self._captured_pdf_files[pdf_path] = {
                    'pdf_type': pdf_type,
                    'exists': exists,
                    'active': active,
                    'captured_at': 'cleanup'
                }
                
                #print(f"   📄 Captured: {os.path.basename(pdf_path)} ({pdf_type}) - {'✅' if exists else '❌'} exists, {'🔴' if active else '⚪'} active")
        
        #print(f"📄 Total captured PDF files: {len(self._captured_pdf_files)}")
        
        # Also capture from tabs if available
        if hasattr(self, 'pdf_manager') and hasattr(self.pdf_manager, 'pdf_tabs') and self.pdf_manager.pdf_tabs:
            tabs = self.pdf_manager.pdf_tabs
            #print(f"📄 Also checking {tabs.count()} PDF tabs...")
            
            for i in range(tabs.count()):
                widget = tabs.widget(i)
                tab_text = tabs.tabText(i)
                
                # Try to find corresponding PDF path
                if hasattr(widget, 'pdf_path'):
                    pdf_path = widget.pdf_path
                    if pdf_path not in self._captured_pdf_files:
                        pdf_type = 'tex_generated' if 'tex' in tab_text.lower() else 'external'
                        self._captured_pdf_files[pdf_path] = {
                            'pdf_type': pdf_type,
                            'exists': os.path.exists(pdf_path),
                            'active': True,
                            'captured_at': 'tabs'
                        }
                        print(f"   📄 Additional from tabs: {tab_text}")
    

        

    
    # def open_recent_pdf_file(self, file_path):
        # """Open a PDF from the recent files list with guaranteed focus"""
        # if not os.path.exists(file_path):
            # print(f"❌ Recent PDF file not found: {file_path}")
            # if hasattr(self.main_window, 'config_manager'):
                # self.main_window.config_manager.remove_recent_pdf_file(file_path)
                # if hasattr(self.main_window, 'menu_manager'):
                    # self.main_window.menu_manager.update_recent_pdf_files_menu()
            # return None

        # file_path = os.path.abspath(file_path)
        # #print(f"🔄 Opening recent PDF: {os.path.basename(file_path)}")
        
        # # Debug current state
        # #print(f"📄 Current PDF files tracked: {len(self.pdf_files)}")
        # if file_path in self.pdf_files:
            # print(f"📄 PDF already exists in tracking")
        
        # # Ensure pdf_files is initialized
        # if not hasattr(self, 'pdf_files'):
            # self.pdf_files = {}
        
        # # If PDF is already open, bring it to foreground
        # if file_path in self.pdf_files:
            # #print(f"📄 PDF already open, bringing to foreground...")
            # data = self.pdf_files[file_path]
            # viewer = data.get('viewer')
            
            # if viewer and hasattr(viewer, 'isVisible'):
                # #print(f"📄 Found existing viewer, bringing to front...")
                # self._bring_pdf_to_foreground(viewer, data)
                
                # # Update recent files (move to top)
                # if hasattr(self.main_window, 'config_manager'):
                    # self.main_window.config_manager.add_recent_pdf_file(file_path)
                # if hasattr(self.main_window, 'menu_manager'):
                    # self.main_window.menu_manager.update_recent_pdf_files_menu()
                
                # self.main_window.update_status_bar(f"Recent PDF focused: {os.path.basename(file_path)}")
                # return viewer
            # else:
                # #print(f"⚠️ Stale viewer found, removing and reloading...")
                # del self.pdf_files[file_path]
        
        # # Load PDF (new or reload)
        # #print(f"📄 Loading PDF in viewer...")
        # viewer = self.load_pdf_in_viewer(file_path, bring_to_front=True)
        
        # if viewer:
            # # Ensure it's properly focused
            # #print(f"📄 Ensuring focus after load...")
            # if file_path in self.pdf_files:
                # data = self.pdf_files[file_path]
                # self._bring_pdf_to_foreground(viewer, data)
            
            # # Update recent files and menu
            # if hasattr(self.main_window, 'config_manager'):
                # self.main_window.config_manager.add_recent_pdf_file(file_path)
            # if hasattr(self.main_window, 'menu_manager'):
                # self.main_window.menu_manager.update_recent_pdf_files_menu()
            
            # self.main_window.update_status_bar(f"Recent PDF opened: {os.path.basename(file_path)}")
            
        # else:
            # print(f"❌ Failed to load PDF viewer")
        
        # return viewer

    def open_recent_pdf_file(self, file_path):
        """Open a PDF from the recent files list with guaranteed focus and wait cursor"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        # Show wait cursor immediately
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            if not os.path.exists(file_path):
                print(f"❌ Recent PDF file not found: {file_path}")
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.remove_recent_pdf_file(file_path)
                    if hasattr(self.main_window, 'menu_manager'):
                        self.main_window.menu_manager.update_recent_pdf_files_menu()
                return None

            file_path = os.path.abspath(file_path)
            
            # Debug current state
            if file_path in self.pdf_files:
                print(f"📄 PDF already exists in tracking")
            
            # Ensure pdf_files is initialized
            if not hasattr(self, 'pdf_files'):
                self.pdf_files = {}
            
            # If PDF is already open, bring it to foreground
            if file_path in self.pdf_files:
                data = self.pdf_files[file_path]
                viewer = data.get('viewer')
                
                if viewer and hasattr(viewer, 'isVisible'):
                    self._bring_pdf_to_foreground(viewer, data)
                    
                    # Update recent files (move to top)
                    if hasattr(self.main_window, 'config_manager'):
                        self.main_window.config_manager.add_recent_pdf_file(file_path)
                    if hasattr(self.main_window, 'menu_manager'):
                        self.main_window.menu_manager.update_recent_pdf_files_menu()
                    
                    self.main_window.update_status_bar(f"Recent PDF focused: {os.path.basename(file_path)}")
                    return viewer
                else:
                    print(f"⚠️ Stale viewer found, removing and reloading...")
                    del self.pdf_files[file_path]
            
            # Load PDF (new or reload)
            viewer = self.load_pdf_in_viewer(file_path, bring_to_front=True)
            
            if viewer:
                # Ensure it's properly focused
                if file_path in self.pdf_files:
                    data = self.pdf_files[file_path]
                    self._bring_pdf_to_foreground(viewer, data)
                
                # Update recent files and menu
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.add_recent_pdf_file(file_path)
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager.update_recent_pdf_files_menu()
                
                self.main_window.update_status_bar(f"Recent PDF opened: {os.path.basename(file_path)}")
            else:
                print(f"❌ Failed to load PDF viewer")
            
            return viewer
        finally:
            # Always restore the cursor, even if an error occurs
            QApplication.restoreOverrideCursor()    

       

    def _is_tex_generated_pdf(self, pdf_path):
        """Check if this PDF was generated from a .tex file"""
        tex_path = os.path.splitext(pdf_path)[0] + ".tex"
        return (tex_path in self.main_window.editor_manager.editor_files or 
                os.path.exists(tex_path))

    def show_error(self, title, message):
        """Show error message dialog"""
        QMessageBox.critical(self.main_window, title, message)


    def refresh_pdf(self):
        """Refresh the PDF for the current .tex file - Each .tex has its own PDF"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                            
        
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
    
        try:
            current_file = self.main_window.editor_manager.current_file
            if not current_file:
                self.main_window.update_status_bar(
                    self.main_window.translations[self.main_window.menu_language]["status_no_file"]
                )
                return
                
            # ✅ FIXED: Get the specific PDF for THIS .tex file
            pdf_path = os.path.splitext(current_file)[0] + ".pdf"
            
            if os.path.exists(pdf_path):
                # ✅ FIXED: Reload the specific PDF for this .tex file
                self.reload_pdf(pdf_path)
                
                # ✅ Ensure THIS PDF is in foreground (not some other PDF)
                if pdf_path in self.pdf_files:
                    data = self.pdf_files[pdf_path]
                    viewer = data.get('viewer')
                    if viewer and self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
                        index = data.get('index', -1)
                        if 0 <= index < self.pdf_tabs.count():
                            self.pdf_tabs.setCurrentIndex(index)
                            viewer.setFocus()
                    # ✅ FIX: Highlight the refreshed viewer
                    if viewer:
                        self._highlight_active_pdf_viewer(viewer)        
            else:
                self.main_window.update_status_bar(
                    self.main_window.translations[self.main_window.menu_language]["status_pdf_not_found"]
                )
        finally:
            # Always restore cursor
            QApplication.restoreOverrideCursor()


         
    def reload_pdf(self, pdf_path):
        """Reload specific PDF file - FIXED: Reload in existing viewer without closing"""
        #print(f"\n🔄 reload_pdf() called for: {os.path.basename(pdf_path)}")
        if not os.path.exists(pdf_path):
            #print(f"\n🔄 reload_pdf() called for: {os.path.basename(pdf_path)}")
            return
            
        pdf_path = os.path.abspath(pdf_path)
        #print(f"\n🔄 reload_pdf() called for: {os.path.basename(pdf_path)}")
        
        # ✅ FIXED: If this specific PDF has a viewer, just refresh its content
        if pdf_path in self.pdf_files:
            data = self.pdf_files[pdf_path]
            viewer = data.get('viewer')

            if viewer:
                try:
                    # Use position-preserving reload so the user's scroll
                    # position survives recompilation and manual refresh.
                    if hasattr(viewer, 'reload_pdf_preserving_position'):
                        reload_success = viewer.reload_pdf_preserving_position(pdf_path)
                    else:
                        reload_success = viewer.load_pdf(pdf_path)

                    if reload_success:
                        # Bring THIS specific PDF to foreground
                        if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
                            index = data.get('index', -1)
                            if index == -1:
                                index = self.pdf_tabs.indexOf(viewer)
                                if index != -1:
                                    data['index'] = index
                            if 0 <= index < self.pdf_tabs.count():
                                self.pdf_tabs.setCurrentIndex(index)
                                viewer.setFocus()

                        self.main_window.update_status_bar(f"Reloaded: {os.path.basename(pdf_path)}")
                        return
                    else:
                        print(f"❌ Reload returned False")

                except Exception as e:
                    print(f"Error reloading PDF {pdf_path}: {e}")
        #else:
            #print(f"⚠️ No existing viewer found, creating new one...")
             
        # ✅ Fallback: If no existing viewer or reload failed, create new one
        # Only attempt if the file actually exists to avoid crashing on a failed compilation.
        if os.path.exists(pdf_path):
            self.load_pdf_in_viewer(pdf_path)


    def _prompt_save_annotations(self, viewer):
        if not viewer or not hasattr(viewer, 'annotations_modified') or not viewer.annotations_modified:
            return True

        # Release mouse grab
        from PyQt5.QtWidgets import QWidget
        grabber = QWidget.mouseGrabber()
        if grabber:
            grabber.releaseMouse()
        QApplication.processEvents()

        msgbox = QMessageBox(self.main_window)
        msgbox.setWindowTitle("Unsaved Annotations")
        msgbox.setText("You have unsaved annotations. Do you want to save before closing?")
        save_btn = msgbox.addButton("Save", QMessageBox.AcceptRole)
        save_as_btn = msgbox.addButton("Save As", QMessageBox.AcceptRole)
        discard_btn = msgbox.addButton("Discard", QMessageBox.DestructiveRole)
        cancel_btn = msgbox.addButton("Cancel", QMessageBox.RejectRole)
        msgbox.setDefaultButton(save_btn)
        msgbox.setWindowModality(Qt.ApplicationModal)
        msgbox.exec_()

        clicked = msgbox.clickedButton()
        if clicked == save_btn:
            if hasattr(viewer, '_save_annotations'):
                viewer._save_annotations()
            return True
        elif clicked == save_as_btn:
            if hasattr(viewer, '_save_annotations_as'):
                success = viewer._save_annotations_as()
                return success   # Only close if actually saved
            return False
        elif clicked == discard_btn:
            if hasattr(viewer, 'load_pdf') and viewer.current_pdf_path:
                viewer.load_pdf(viewer.current_pdf_path)
            return True
        else:  # Cancel
            return False   
            
       
            
    def cleanup(self):
        """Legacy cleanup method - redirect to cleanup_for_exit"""
        # This maintains backward compatibility if cleanup() is called elsewhere
        self.cleanup_for_exit()      

    def cleanup_for_exit(self):
        """Clean up PDF resources during application exit - no UI manipulation"""
        try:
            # Close all PDF documents without UI updates
            for path, data in list(self.pdf_files.items()):
                if isinstance(data, dict):
                    viewer = data.get('viewer')
                    if viewer:
                        try:
                            # Close the PDF document
                            if hasattr(viewer, 'pdf_document') and viewer.pdf_document:
                                viewer.pdf_document.close()
                                viewer.pdf_document = None
                            
                            # Disconnect any signals to prevent callbacks during shutdown
                            if hasattr(viewer, 'disconnect'):
                                viewer.disconnect()
                            
                            # Set parent to None to help with cleanup
                            viewer.setParent(None)
                            
                        except Exception as e:
                            print(f"Error cleaning up PDF viewer for {path}: {e}")
            
            # Clear the pdf_files dictionary
            self.pdf_files.clear()
            
            # Clear references to UI elements
            self.current_pdf_path = None
            
            #print("PDF cleanup completed successfully")
            
        except Exception as e:
            print(f"Error during PDF cleanup: {e}")
            import traceback
            traceback.print_exc()

        
    def show_pdf_context_menu(self, pos, pdf_path):
        """Show context menu for PDF label"""
        if pdf_path not in self.pdf_files:
            return
            
        menu = QMenu(self.main_window)
        close_action = QAction(
            self.main_window.translations[self.main_window.menu_language]["close"], 
            self.main_window
        )
        close_action.setToolTip(
            self.main_window.translations[self.main_window.menu_language]["close_tooltip"]
        )
        
        viewer, index, label = self.pdf_files[pdf_path]
        close_action.triggered.connect(lambda: self.close_pdf_tab(index))
        menu.addAction(close_action)
        menu.exec_(label.mapToGlobal(pos))
        
               
            
    def get_container(self):
        """Return the PDF's container widget (tabbed or splitter)"""
        if self.pdf_layout_mode == "tabbed":
            return self.pdf_tabs
        else:
            return self.pdf_splitter
    

    def close_current_pdf(self):
        """Close the currently active PDF and show welcome if no PDFs left"""
        if not hasattr(self, 'pdf_files'):
            return False
        
        # Clean stale references first
        self._clean_stale_pdf_references()
        
        if not self.pdf_files:
            return False
            
        current_index = -1
        if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
            current_index = self.pdf_tabs.currentIndex()
        elif self.pdf_layout_mode in ["horizontal", "vertical"] and self.pdf_splitter:
            # In H/V mode, you might want the focused one, but for now use current widget
            # Note: QSplitter doesn't have a "current" widget, so we use index 0 or find it
            for i in range(self.pdf_splitter.count()):
                widget = self.pdf_splitter.widget(i)
                if hasattr(widget, 'hasFocus') and widget.hasFocus():
                    current_index = i
                    break
            else:
                # Fallback: first tab widget
                current_index = 0 if self.pdf_splitter.count() > 0 else -1
        if current_index >= 0:
            # Store whether this is the last PDF
            was_last_pdf = len(self.pdf_files) == 1
            #print(f"DEBUG: Closing PDF at index {current_index}, was_last_pdf: {was_last_pdf}, total PDFs: {len(self.pdf_files)}")
            # Close the tab
            success = self.close_pdf_tab(current_index, show_welcome=was_last_pdf)
            return success
        return False


    def close_all_pdfs(self):
        """Close all open PDF files - preserves tool tabs, shows welcome properly"""
        if not hasattr(self, 'pdf_files') or not self.pdf_files:
            return True
        
        pdf_count = len(self.pdf_files)
        
        # Confirm if multiple PDFs are open
        if pdf_count > 1:
            lang = self.main_window.menu_language
            t = self.main_window.translations[lang]
            reply = QMessageBox.question(
                self.main_window,
                t.get("close_all_pdfs_confirm", "Close All PDFs"),
                t.get("close_all_pdfs_message", "Close all {count} open PDF files?").format(count=pdf_count),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                return False
        
        # ✅ If in H/V mode, switch to tabbed mode FIRST (before closing)
        if self.pdf_layout_mode in ["horizontal", "vertical"]:
            #print("DEBUG: Switching from H/V mode to tabbed mode BEFORE closing PDFs")
            self.pdf_layout_mode = "tabbed"
            if hasattr(self.main_window, 'layout_manager') and hasattr(self.main_window.layout_manager, '_recreate_pdf_container'):
                self.main_window.layout_manager._recreate_pdf_container()
            if hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.set_config_value('layout', 'pdf_layout_mode', "tabbed")
        
        success = True
        
        # ✅ Now close all PDFs in tabbed mode
        if self.pdf_tabs:
            # Close only PDF tabs (not tool tabs or welcome)
            tool_tabs = ["AI Assistant", "Tools", "TikZ Plotter", "PDF Comparison"]
            indices_to_close = []
            
            for i in range(self.pdf_tabs.count()):
                tab_name = self.pdf_tabs.tabText(i)
                if tab_name not in tool_tabs and tab_name not in ["Welcome", "No PDFs", "No Pdfs"]:
                    indices_to_close.append(i)
            
            # Close from right to left (reverse order)
            reversed_indices = list(reversed(indices_to_close))
            for idx, i in enumerate(reversed_indices):
                if hasattr(self, 'close_pdf_tab'):
                    # ✅ Show welcome only on the VERY LAST close
                    show_welcome = (idx == len(reversed_indices) - 1)
                    if not self.close_pdf_tab(i, show_welcome=show_welcome):
                        success = False
                        break
                else:
                    widget = self.pdf_tabs.widget(i)
                    if widget:
                        widget.setParent(None)
                    self.pdf_tabs.removeTab(i)
        
        # Clear pdf_files dictionary
        if hasattr(self, 'pdf_files'):
            self.pdf_files.clear()
        
        # Update status bar
        if success:
            lang = self.main_window.menu_language
            t = self.main_window.translations[lang]
            self.main_window.update_status_bar(
                t.get("all_pdfs_closed", "All PDF files closed")
            )
        
        return success
    
    
        
    def close_pdf_tab_by_signal(self, index):
        """Handle tabCloseRequested signal - wrapper for close_pdf_tab"""
        #print(f"DEBUG: close_pdf_tab_by_signal called with index: {index}")
        #print(f"DEBUG: Layout mode: {self.pdf_layout_mode}")
        if self.pdf_layout_mode == "tabbed":
            #print(f"DEBUG: Tabbed mode - closing tab {index}")
            return self.close_pdf_tab(index)
        else:
            sender = self.main_window.sender()
            #print(f"DEBUG: H/V mode - signal sender: {sender} (id: {id(sender)})")
            if sender and hasattr(self, 'pdf_splitter') and self.pdf_splitter:
                splitter_index = -1
                for i in range(self.pdf_splitter.count()):
                    widget = self.pdf_splitter.widget(i)
                    #print(f"DEBUG: Comparing sender {id(sender)} with splitter widget {id(widget)} at index {i}")
                    if widget == sender:
                        splitter_index = i
                        break
                #print(f"DEBUG: Found sender at splitter index: {splitter_index}")
                if splitter_index >= 0:
                    # ✅ If closing will leave only one PDF, switch to tabbed mode FIRST, then close
                    if len(self.pdf_files) == 2:
                        #print("DEBUG: Only one PDF will remain — switching to tabbed mode")
                        # Store the PDF path to close AFTER recreation
                        pdf_path_to_close = None
                        wrapper = self.pdf_splitter.widget(splitter_index)
                        if isinstance(wrapper, QTabWidget) and wrapper.count() > 0:
                            viewer = wrapper.widget(0)
                            for path, data in self.pdf_files.items():
                                if isinstance(data, dict) and data.get('viewer') == viewer:
                                    pdf_path_to_close = path
                                    break
                        
                        # Switch to tabbed mode
                        self.pdf_layout_mode = "tabbed"
                        if hasattr(self.main_window, 'layout_manager') and hasattr(self.main_window.layout_manager, '_recreate_pdf_container'):
                            self.main_window.layout_manager._recreate_pdf_container()
                        if hasattr(self.main_window, 'config_manager'):
                            self.main_window.config_manager.set_config_value('layout', 'pdf_layout_mode', "tabbed")
                        
                        # ✅ Now close the PDF in tabbed mode
                        if pdf_path_to_close:
                            # Find the tab index for this PDF
                            tab_index = -1
                            for i in range(self.pdf_tabs.count()):
                                widget = self.pdf_tabs.widget(i)
                                if widget == self.pdf_files[pdf_path_to_close].get('viewer'):
                                    tab_index = i
                                    break
                            if tab_index >= 0:
                                print(f"DEBUG: Closing PDF {pdf_path_to_close} at tab index {tab_index} after mode switch")
                                return self.close_pdf_tab(tab_index)
                        return
                    return self.close_pdf_tab(splitter_index)
            #print(f"DEBUG: Could not find sender in splitter - falling back to index {index}")
            return self.close_pdf_tab(index)
            
        
   
    def close_pdf_tab(self, index, show_welcome=True):
        """Close PDF tab by index - FIXED: AI Assistant only closes on its own [X]"""
        if self.pdf_layout_mode == "tabbed":
            if not self.pdf_tabs:
                return False
            if index < 0 or index >= self.pdf_tabs.count():
                return False

            tab_name = self.pdf_tabs.tabText(index)
            widget = self.pdf_tabs.widget(index)

            # Tool tabs list
            tool_tabs = ["Latex Wizard", "AI Assistant", "Tools", "TikZ Plotter",
                          "PDF Comparison", "Todo list", "Spreadsheet"]

            # Check if this is a tool tab
            if tab_name in tool_tabs:
                print(f"🔧 Closing tool tab: {tab_name}")
                self.pdf_tabs.removeTab(index)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

                # ✅ FIX: Restore PDF width if it was expanded for PDF Comparison
                if tab_name == "PDF Comparison":
                    if getattr(self.main_window, '_pdf_expanded', False):
                        self.main_window.toggle_pdf_expand_width()
                    if hasattr(self.main_window, 'output_tabs_visible') and not self.main_window.output_tabs_visible:
                        self.main_window.toggle_output_tabs()

                # ✅ FIX: Show welcome ONLY if no tabs at all remain
                if self.pdf_tabs.count() == 0 and show_welcome:
                    self._show_pdf_welcome_tab()
                return True

            # Check if this is a welcome tab (shouldn't be closable)
            if tab_name in ["Welcome", "PDF Viewer", "No PDFs", "No Pdfs"]:
                print(f"⚠️ Ignoring close request for welcome tab: {tab_name}")
                return False

            # This is a PDF tab - find the pdf_path
            pdf_path_to_close = None
            for pdf_path, data in list(self.pdf_files.items()):
                if isinstance(data, dict):
                    stored_index = data.get('index', -1)
                    viewer = data.get('viewer')
                elif isinstance(data, (list, tuple)) and len(data) > 2:
                    stored_index = data[2]
                    viewer = data[0]
                else:
                    continue

                if stored_index == index or (viewer and self.pdf_tabs.indexOf(viewer) == index):
                    pdf_path_to_close = pdf_path
                    break

            if pdf_path_to_close:
                #print(f"📄 Closing PDF tab: {os.path.basename(pdf_path_to_close)}")
                # Get viewer before removing from dict
                data = self.pdf_files.get(pdf_path_to_close)
                if data:
                    viewer = data.get('viewer') if isinstance(data, dict) else data[0]
                    # --- NEW: Prompt to save unsaved annotations ---
                    if not self._prompt_save_annotations(viewer):
                        # User cancelled – do not close
                        return False                    
                    # Close the PDF document
                    if viewer and hasattr(viewer, 'pdf_document') and viewer.pdf_document:
                        try:
                            viewer.pdf_document.close()
                            viewer.pdf_document = None 
                        except:
                            pass

                # Remove from tracking dict
                del self.pdf_files[pdf_path_to_close]

            # Remove the tab
            self.pdf_tabs.removeTab(index)
            if widget:
                widget.setParent(None)

            # Update indices for remaining PDF files
            for pdf_path, data in self.pdf_files.items():
                if isinstance(data, dict):
                    old_index = data.get('index', -1)
                    if old_index > index:
                        data['index'] = old_index - 1

            # ✅ CRITICAL FIX: Show welcome only if NO tabs remain at all.
            # Tool tabs (AI Assistant, etc.) should keep the tab widget alive.
            if show_welcome:
                remaining_count = self.pdf_tabs.count()

                if remaining_count == 0:
                    # No tabs at all — show welcome
                    self._show_pdf_welcome_tab()
                else:
                    # Check if any remaining tabs are actual PDF tabs (not tools, not welcome)
                    has_pdf_tabs = False
                    has_only_tool_tabs = True
                    for i in range(remaining_count):
                        tab_text = self.pdf_tabs.tabText(i)
                        if tab_text in tool_tabs:
                            continue  # Skip tool tabs
                        if tab_text in ["Welcome", "PDF Viewer", "No PDFs", "No Pdfs"]:
                            continue  # Skip welcome tabs
                        has_pdf_tabs = True
                        has_only_tool_tabs = False
                        break

                    # ✅ If only tool tabs remain (like AI Assistant), do NOT show welcome.
                    # The tool tabs stay open on their own — no welcome tab needed.
                    # Welcome is only needed when there are zero tabs of any kind.

            #print(f"✅ Tab closed. Remaining tabs: {self.pdf_tabs.count()}")
            return True

        # ============================================
        # Handle H/V SPLITTER mode
        # ============================================
        else:
            if not self.pdf_splitter or index < 0 or index >= self.pdf_splitter.count():
                return False

            wrapper = self.pdf_splitter.widget(index)
            if not wrapper:
                return False

            # Find the PDF path for this wrapper
            pdf_path_to_close = None
            for pdf_path, data in list(self.pdf_files.items()):
                if isinstance(data, dict) and data.get('wrapper') == wrapper:
                    pdf_path_to_close = pdf_path
                    break

            if pdf_path_to_close:
                #print(f"📄 Closing PDF (H/V mode): {os.path.basename(pdf_path_to_close)}")
                data = self.pdf_files.get(pdf_path_to_close)
                if data:
                    viewer = data.get('viewer') if isinstance(data, dict) else data[0]

                    # --- NEW: Prompt to save unsaved annotations ---
                    if not self._prompt_save_annotations(viewer):
                        # User cancelled – do not close
                        return False

                    # Close document if needed
                    if viewer and hasattr(viewer, 'pdf_document') and viewer.pdf_document:
                        try:
                            viewer.pdf_document.close()
                            viewer.pdf_document = None 
                        except:
                            pass

                
                del self.pdf_files[pdf_path_to_close]

            # Remove from splitter
            wrapper.setParent(None)
            wrapper.deleteLater()

            # ✅ If only 1 PDF remains, switch to tabbed mode
            if len(self.pdf_files) == 1:
                #print("DEBUG: Only 1 PDF remains in H/V mode - switching to tabbed")
                self.pdf_layout_mode = "tabbed"
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.set_config_value('layout', 'pdf_layout_mode', 'tabbed')
                if hasattr(self.main_window, 'layout_manager'):
                    self.main_window.layout_manager._recreate_pdf_container()

            # ✅ If no PDFs remain, show welcome
            elif len(self.pdf_files) == 0 and show_welcome:
                self.pdf_layout_mode = "tabbed"
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.set_config_value('layout', 'pdf_layout_mode', 'tabbed')
                self._show_pdf_welcome_tab()

            return True
        

    def _on_hv_tab_bar_clicked(self, index, viewer):
        """Handle tab bar click in H/V mode to update active PDF border.

        In H/V mode each PDF has its own single-tab QTabWidget, so
        currentChanged never fires. tabBarClicked fires on every click.
        """
        if not viewer:
            return
        self._highlight_active_pdf_viewer(viewer)
        viewer.setFocus()
        for pdf_path, data in self.pdf_files.items():
            if isinstance(data, dict) and data.get('viewer') is viewer:
                self.current_pdf_path = pdf_path
                break
            
    def _create_pdf_wrapper(self, viewer, pdf_path, parent_widget):
        """Create wrapper widget for PDF viewer in splitter mode - ENSURE LAYOUT"""
        wrapper = QWidget(parent_widget)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(2, 2, 2, 2)
        wrapper_layout.setSpacing(2)
        
        # Create label
        label = QLabel(os.path.basename(pdf_path), wrapper)
        label.setFont(QFont(
            "Amiri" if self.main_window.menu_language == "ar" else "Consolas", 
            self.main_window.toolbar_font_size if hasattr(self.main_window, 'toolbar_font_size') else 10
        ))
        label.setAlignment(Qt.AlignRight if getattr(self.main_window, 'is_rtl', False) else Qt.AlignLeft)
        label.setContextMenuPolicy(Qt.CustomContextMenu)
        label.customContextMenuRequested.connect(
            lambda pos, p=pdf_path: self.show_pdf_context_menu(pos, p)
        )
        label.setMinimumHeight(20)
        label.setMaximumHeight(25)
        
        # Create QTabWidget for the viewer
        tab_widget = QTabWidget(wrapper)
        tab_widget.setTabsClosable(True)
        tab_widget.tabCloseRequested.connect(self.close_pdf_tab_by_signal)

        # ✅ FIX: Connect tabBarClicked for H/V mode border highlighting
        tab_widget.tabBarClicked.connect(
            lambda idx, v=viewer: self._on_hv_pdf_tab_bar_clicked(idx, v)
        )
        
        # ✅ FIX: Highlight this viewer's border when its tab bar is clicked (H/V mode)
        tab_widget.tabBarClicked.connect(
            lambda _idx, v=viewer: self._highlight_active_pdf_viewer(v)
        )
        
        
        tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tab_widget.setMinimumSize(200, 150)
        tab_widget.setFocusPolicy(Qt.NoFocus)
        
        # ✅ Focus policies - viewer should have strong focus
        viewer.setFocusPolicy(Qt.StrongFocus)
        viewer.scroll_area.setFocusPolicy(Qt.StrongFocus)
        
        # Store pdf_path on viewer for identification
        viewer.pdf_path = pdf_path
        
        # Add viewer to QTabWidget
        tab_widget.addTab(viewer, os.path.basename(pdf_path))
        
        # Add to layout
        wrapper_layout.addWidget(label)
        wrapper_layout.addWidget(tab_widget, 1)
        
        # Set wrapper properties
        wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        wrapper.setMinimumSize(250, 250)
        wrapper.setFocusPolicy(Qt.NoFocus)
        
        # Ensure visibility
        wrapper.setEnabled(True)
        wrapper.setVisible(True)
        viewer.setEnabled(True)
        viewer.setVisible(True)
        tab_widget.setEnabled(True)
        tab_widget.setVisible(True)
        
        #print(f"✅ Created H/V wrapper for: {os.path.basename(pdf_path)}")
        
        return wrapper
    
    
    

    def switch_to_pdf_for_current_tex(self):
        """Switch to the PDF viewer for the currently active .tex file"""
        current_file = self.main_window.editor_manager.current_file
        if not current_file:
            return
            
        pdf_path = os.path.splitext(current_file)[0] + ".pdf"
        
        if pdf_path in self.pdf_files:
            data = self.pdf_files[pdf_path]
            viewer = data.get('viewer')
            if viewer and self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
                index = data.get('index', -1)
                if 0 <= index < self.pdf_tabs.count():
                    self.pdf_tabs.setCurrentIndex(index)
                    viewer.setFocus()
                    # ✅ Highlight the active PDF viewer border
                    self._highlight_active_pdf_viewer(viewer) 

           
################
    def _apply_pdf_welcome_theme(self):
        """Re-style the PDF welcome widget in place without rebuilding it."""
        from style_manager import get_welcome_style
        w = get_welcome_style()
        if hasattr(self, '_pdf_welcome_widget') and self._pdf_welcome_widget:
            self._pdf_welcome_widget.setStyleSheet(
                f"background-color: {w['outer_bg']};"
            )
        
    def refresh_welcome_page(self):
        """Rebuild the PDF welcome tab with current theme."""
        if not hasattr(self, 'pdf_tabs') or not self.pdf_tabs:
            return
        for i in range(self.pdf_tabs.count()):
            widget = self.pdf_tabs.widget(i)
            if widget and widget.objectName() == "pdf_welcome_widget":
                new_welcome = self._create_pdf_welcome_widget()
                new_welcome.setObjectName("pdf_welcome_widget")
                self.pdf_tabs.removeTab(i)
                self.pdf_tabs.insertTab(i, new_welcome, "Welcome")
                self.pdf_tabs.setCurrentIndex(i)
                break
            
    def _show_pdf_welcome_tab(self):
        """Show welcome tab when no PDFs are open - with proper cleanup."""
        
        # Get pdf_container from layout_manager
        if not hasattr(self.main_window, 'layout_manager'):
            return
        
        lm = self.main_window.layout_manager
        
        if not hasattr(lm, 'pdf_container') or lm.pdf_container is None:
            return
        
        pdf_container = lm.pdf_container
        pdf_layout = pdf_container.layout()
        
        if not pdf_layout:
            return
        
        # ============================================
        # CRITICAL: Aggressively clean up ALL children
        # ============================================
        
        # Step 1: Hide and schedule deletion for ALL children
        for child in pdf_container.findChildren(QWidget):
            child.hide()
        
        # Step 2: Remove all items from layout
        while pdf_layout.count():
            item = pdf_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        
        # Step 3: Clear our references
        self.pdf_tabs = None
        
        # Step 4: Force process deletions
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Step 5: Double-check for any remaining visible orphans
        for child in pdf_container.findChildren(QWidget):
            if child.isVisible():
                #print(f"🧹 Force hiding orphan: {child.__class__.__name__}")
                child.hide()
                child.deleteLater()
        
        # ============================================
        # Now create fresh welcome content
        # ============================================
        
        from style_manager import get_welcome_style
        w = get_welcome_style()

        welcome_content = lm._create_pdf_welcome_content()
        welcome_content.setObjectName("pdf_welcome_widget")  # ← same pattern as editor

        # Create new tab widget
        welcome_tab = QTabWidget()
        welcome_tab.setObjectName("pdf_welcome_tab")
        welcome_tab.addTab(welcome_content, "PDF Viewer")
        welcome_tab.setTabsClosable(False)

        # Style with current theme instead of hardcoded white
        welcome_tab.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {w['tab_pane_bg']};
            }}
        """)

        
        # Connect close handler
        welcome_tab.tabCloseRequested.connect(self._handle_tab_close_request)
###
        # ✅ Enable drag-and-drop on the tab widget itself
        welcome_tab.setAcceptDrops(True)
        pdf_manager = self

        def tab_pdf_drag_enter(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if file_path.lower().endswith('.pdf'):
                            event.acceptProposedAction()
                            return
            QTabWidget.dragEnterEvent(welcome_tab, event)

        def tab_pdf_drag_move(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if file_path.lower().endswith('.pdf'):
                            event.acceptProposedAction()
                            return
            QTabWidget.dragMoveEvent(welcome_tab, event)

        def tab_pdf_drop(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    if file_path and os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                        pdf_manager.load_pdf_in_viewer(file_path, bring_to_front=True)
                        if hasattr(pdf_manager.main_window, 'config_manager'):
                            pdf_manager.main_window.config_manager.add_recent_pdf_file(file_path)
                event.acceptProposedAction()
                return
            QTabWidget.dropEvent(welcome_tab, event)

        welcome_tab.dragEnterEvent = tab_pdf_drag_enter
        welcome_tab.dragMoveEvent = tab_pdf_drag_move
        welcome_tab.dropEvent = tab_pdf_drop

###        
        # Add to layout
        pdf_layout.addWidget(welcome_tab)
        welcome_tab.show()
        
        # Store reference
        self.pdf_tabs = welcome_tab
        
        # ✅ FIX: Pre-connect signals on the new tab widget
        self.pdf_tabs.currentChanged.connect(self.on_pdf_tab_changed)
        self.pdf_tabs.tabBarClicked.connect(self._on_pdf_tab_bar_clicked)

        
               
    def _handle_tab_close_request(self, index):
        """Unified handler for closing tabs - works for both PDFs and tools."""
        if not self.pdf_tabs:
            return
        
        tab_text = self.pdf_tabs.tabText(index)
        widget = self.pdf_tabs.widget(index)
        
        # Tool tabs - just remove them
        tool_tabs = ["AI Assistant", "Tools", "TikZ Plotter", "PDF Comparison", "PDF Tools"]
        if tab_text in tool_tabs:
            self.pdf_tabs.removeTab(index)
            if widget:
                widget.deleteLater()
            
            # ✅ FIX: Restore PDF width if it was expanded for PDF Comparison
            if tab_text == "PDF Comparison":
                if getattr(self.main_window, '_pdf_expanded', False):
                    self.main_window.toggle_pdf_expand_width()
                # Also show output tabs if they were hidden
                if hasattr(self.main_window, 'output_tabs_visible') and not self.main_window.output_tabs_visible:
                    self.main_window.toggle_output_tabs()
            
            # If no tabs left, show welcome
            if self.pdf_tabs.count() == 0:
                self._show_pdf_welcome_tab()
            return
        
        # Welcome tabs - don't close
        if tab_text in ["Welcome", "PDF Viewer", "No PDFs"]:
            return
        
        # PDF tabs - use existing close logic
        self.close_pdf_tab(index)
    
        
    def _remove_welcome_tab_if_exists(self):
        """Remove welcome tab when a tool or PDF is opened"""
        if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
            for i in reversed(range(self.pdf_tabs.count())):
                tab_text = self.pdf_tabs.tabText(i)
                if tab_text in ["Welcome", "PDF Viewer"]:
                    self.pdf_tabs.removeTab(i)
            # Enable close button if there are tabs
            if self.pdf_tabs.count() > 0:
                self.pdf_tabs.setTabsClosable(True)
        



    def _create_pdf_welcome_action_item(self, icons_manager, icon_name, text, shortcut, callback):
        """Create a clickable action item with icon, underlined text, and shortcut for PDF welcome"""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        
        item_widget = QWidget()
        item_widget.setCursor(QCursor(Qt.PointingHandCursor))
        item_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 4px;
                padding: 5px;
            }
            QWidget:hover {
                background-color: #e8f4fc;
            }
        """)
        
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 6, 8, 6)
        item_layout.setSpacing(10)
        
        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        if icons_manager:
            icon = icons_manager.get_icon(icon_name)
            if icon and not icon.isNull():
                pixmap = icon.pixmap(20, 20)
                icon_label.setPixmap(pixmap)
        item_layout.addWidget(icon_label)
        
        # Text (underlined, clickable style)
        text_label = QLabel(f'<a style="color: #0066cc; text-decoration: underline;">{text}</a>')
        text_label.setStyleSheet("font-size: 13px;")
        item_layout.addWidget(text_label)
        
        # Shortcut (grayed)
        shortcut_label = QLabel(f"({shortcut})")
        shortcut_label.setStyleSheet("font-size: 11px; color: #888;")
        item_layout.addWidget(shortcut_label)
        
        item_layout.addStretch()
        
        # Make entire widget clickable
        def on_click(event):
            callback()
        item_widget.mousePressEvent = on_click
        
        return item_widget


    def _create_pdf_recent_files_list(self):
        """Create a scrollable list of recent PDF files"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(180)
        scroll_area.setMinimumHeight(80)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
            }
        """)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(4)
        
        # Get recent PDF files
        recent_files = []
        if hasattr(self.main_window, 'config_manager'):
            recent_files = self.main_window.config_manager.get_recent_pdf_files()[:101]  # Limit to 101
        
        if not recent_files:
            no_files_label = QLabel("No recent files")
            no_files_label.setStyleSheet("color: #999; font-style: italic; padding: 10px;")
            layout.addWidget(no_files_label)
        else:
            for file_path in recent_files:
                if not os.path.exists(file_path):
                    continue  # Skip non-existent files
                    
                file_widget = QWidget()
                file_widget.setCursor(QCursor(Qt.PointingHandCursor))
                from style_manager import get_tooltip_qss
                file_widget.setStyleSheet("""
                    QWidget {
                        background-color: transparent;
                        border-radius: 3px;
                        padding: 2px;
                    }
                    QWidget:hover {
                        background-color: #e8f4fc;
                    }
                """ + get_tooltip_qss())
                
                file_layout = QHBoxLayout(file_widget)
                file_layout.setContentsMargins(8, 4, 8, 4)
                file_layout.setSpacing(0)
                
                # File name as clickable link
                filename = os.path.basename(file_path)
                file_label = QLabel(f'<a style="color: #0066cc; text-decoration: underline;">{filename}</a>')
                
                from style_manager import get_tooltip_qss
                #file_label.setStyleSheet("font-size: 12px;" + get_tooltip_qss())
                file_label.setStyleSheet(
                    "QLabel { font-size: 12px; }"
                    + get_tooltip_qss()
                )                
                file_label.setToolTip(file_path)                
                
                
                file_layout.addWidget(file_label)
                file_layout.addStretch()
                
                # Create click handler with proper closure
                def make_click_handler(path):
                    def handler(event):
                        self.open_recent_pdf_file(path)
                    return handler
                
                file_widget.mousePressEvent = make_click_handler(file_path)
                layout.addWidget(file_widget)
        
        layout.addStretch()
        scroll_area.setWidget(container)
        
        return scroll_area

################
        
    def save_current_zoom_factor(self):
        """Save the current zoom factor to config"""
        try:
            if not hasattr(self.main_window, 'config_manager'):
                #print("⚠️ No config_manager available for saving zoom")
                return
            
            # Get current zoom from active viewer
            zoom = self.get_current_zoom_factor()
            if zoom and zoom != 1.0:  # Only save if not default
                self.main_window.config_manager.save_pdf_zoom_factor(zoom)
                #print(f"💾 Saved PDF zoom factor: {zoom}")
            #else:
            #    print(f"📊 Zoom is default (1.0), not saving")
        except Exception as e:
            print(f"❌ Error saving zoom factor: {e}")
            import traceback
            traceback.print_exc()

    def get_current_zoom_factor(self):
        """Get the current zoom factor from the active PDF viewer"""
        try:
            viewer = self.get_current_viewer()
            if viewer:
                if hasattr(viewer, 'zoom_factor'):
                    zoom = viewer.zoom_factor
                    #print(f"📊 Got zoom factor from viewer: {zoom}")
                    return zoom
                elif hasattr(viewer, 'get_zoom_factor'):
                    zoom = viewer.get_zoom_factor()
                    #print(f"📊 Got zoom factor via method: {zoom}")
                    return zoom
            #print("⚠️ No viewer found, returning default zoom 1.0")
            return 1.0
        except Exception as e:
            print(f"❌ Error getting zoom factor: {e}")
            return 1.0

    def set_zoom_factor(self, zoom):
        """Set zoom factor for all PDF viewers"""
        try:
            #print(f"📊 PDFManager.set_zoom_factor called with: {zoom}")
            
            # Store as current zoom factor
            self.current_zoom_factor = zoom
            
            # Apply to all open viewers
            applied_count = 0
            if hasattr(self, 'pdf_files') and self.pdf_files:
                for pdf_path, data in self.pdf_files.items():
                    viewer = None
                    if isinstance(data, dict):
                        viewer = data.get('viewer')
                    elif isinstance(data, (list, tuple)) and len(data) > 0:
                        viewer = data[0]
                    
                    if viewer:
                        try:
                            if hasattr(viewer, 'set_zoom_factor'):
                                viewer.set_zoom_factor(zoom)
                                applied_count += 1
                                #print(f"  ✅ Applied zoom to: {os.path.basename(pdf_path)}")
                            elif hasattr(viewer, 'zoom_factor'):
                                viewer.zoom_factor = zoom
                                # Try to trigger re-render
                                if hasattr(viewer, 'render_all_pages'):
                                    viewer.render_all_pages()
                                elif hasattr(viewer, 'update_zoom_display'):
                                    viewer.update_zoom_display()
                                applied_count += 1
                                #print(f"  ✅ Set zoom_factor directly on: {os.path.basename(pdf_path)}")
                        except Exception as viewer_error:
                            print(f"  ⚠️ Error applying zoom to {os.path.basename(pdf_path)}: {viewer_error}")
            
            #print(f"✅ Applied zoom factor {zoom} to {applied_count} viewer(s)")
        except Exception as e:
            print(f"❌ Error setting zoom factor: {e}")
            import traceback
            traceback.print_exc()

    def get_current_viewer(self):
        """Get the currently active PDF viewer"""
        try:
            # Method 1: Check tabbed mode
            if self.pdf_layout_mode == "tabbed" and self.pdf_tabs:
                current_widget = self.pdf_tabs.currentWidget()
                if current_widget:
                    # Check if it's a PDFViewer directly
                    if hasattr(current_widget, 'zoom_factor'):
                        return current_widget
                    # Check if PDFViewer is inside the widget
                    from pdf_viewer import PDFViewer
                    viewers = current_widget.findChildren(PDFViewer)
                    if viewers:
                        return viewers[0]
            
            # Method 2: Get from current_pdf_path
            if hasattr(self, 'current_pdf_path') and self.current_pdf_path:
                if self.current_pdf_path in self.pdf_files:
                    data = self.pdf_files[self.current_pdf_path]
                    if isinstance(data, dict):
                        return data.get('viewer')
            
            # Method 3: Return first available viewer
            if self.pdf_files:
                for pdf_path, data in self.pdf_files.items():
                    if isinstance(data, dict) and data.get('viewer'):
                        return data['viewer']
            
            return None
        except Exception as e:
            print(f"❌ Error getting current viewer: {e}")
            return None
