# layout_manager.py
"""
Layout Manager - Enhanced with Configuration Integration
"""
import os
from PyQt5.QtWidgets import (
    QSplitter, QTabWidget, QVBoxLayout, QWidget, QTextEdit, 
    QScrollArea, QSizePolicy, QApplication, QMessageBox, 
    QFrame, QPlainTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import  QFont, QTextCursor
from side_panel import SidePanel

class LayoutManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_layout = "editor_left"  # editor_left, pdf_left
        self.orientation = "side_by_side"  # side_by_side, stacked  
        # Main components
        self.main_splitter = None
        self.editor_container = None
        self.pdf_container = None
        self.output_container = None
        self.terminal_widget = None
        self._recreating = False   # new flag

        
        self.editor_vertical_splitter = None  # Store reference to prevent
        self._toggle_lock = False  # Prevent rapid clicks
        self.side_panel = None
        self._layout_switching = False  # Prevent recursive calls
        self._pending_recreation_timers = []  # Track pending timers
        self._recreation_suspended = False    # Suspend recreation during loading
        
        
        # Enhanced output container management
        self._base_tabs_created = False
        
        # Flag to track if we should restore sizes
        self._should_restore_splitter_sizes = True
        self._initial_layout_done = False
        self._save_timer = None 


    
    def setup_layout(self):
        """Setup the main window layout with proper error handling"""
        try:
            #print(f"🔧 Setting up layout with orientation: {self.orientation}")
            
            # === STEP 1: Create or update main splitter orientation ===
            if not hasattr(self, 'main_splitter') or self.main_splitter is None:
                if self.orientation == "side_by_side":
                    self.main_splitter = QSplitter(Qt.Horizontal)
                else:
                    self.main_splitter = QSplitter(Qt.Vertical)
                    
                # Set splitter properties
                self.main_splitter.setChildrenCollapsible(False)
                self.main_splitter.setHandleWidth(3)
                #print("✅ Created new main splitter")

            else:
                # Update existing splitter orientation if needed
                current_orientation = self.main_splitter.orientation()
                desired_orientation = Qt.Horizontal if self.orientation == "side_by_side" else Qt.Vertical
                
                if current_orientation != desired_orientation:
                    print(f"🔄 Changing splitter orientation from {current_orientation} to {desired_orientation}")
                    self.main_splitter.setOrientation(desired_orientation)                    

            
            # === STEP 2: Create containers (only if they don't exist) ===
            # Create output container FIRST with proper parent
#            if not hasattr(self, 'output_container') or self.output_container is None:
#                self._create_output_container()
            if (not hasattr(self, 'output_container') or
                not isinstance(self.output_container, QTabWidget)):
                self._create_output_container()

                
            # Create editor container (check if it exists first)
            if not hasattr(self, 'editor_container') or self.editor_container is None:
                self._create_editor_container()
            
            # Create PDF container (check if it exists first) 
            if not hasattr(self, 'pdf_container') or self.pdf_container is None:
                self._create_pdf_container()
                
            # === STEP 3: Handle welcome tab logic more safely ===
            # Check if editor manager exists and has no files
            if (hasattr(self.main_window, 'editor_manager') and 
                hasattr(self.main_window.editor_manager, 'editor_files') and
                not self.main_window.editor_manager.editor_files):
                
                # Only recreate if necessary and safe to do so
                if hasattr(self, '_recreate_editor_container'):
                    #print("🔄 Recreating editor container for welcome tab")
                    self._recreate_editor_container()

            # === STEP 5: Set dynamic properties based on container count ===
            container_count = self.main_splitter.count()
            if container_count > 0:
                # Set equal stretch factors for all containers
                for i in range(container_count):
                    self.main_splitter.setStretchFactor(i, 1)
                
                screen = QApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()  # Excludes taskbar/dock
                total_width = screen_geometry.width()
                panel_width = min(250, total_width // 6)  # 1/6 of screen width, max 250px                
                
                # Set dynamic sizes based on available space
                if container_count == 2:
                    self.main_splitter.setSizes([total_width // 2, total_width // 2])
                elif container_count == 3:
                    self.main_splitter.setSizes([panel_width, (total_width - panel_width) // 2, (total_width - panel_width) // 2])  # side_panel, editor, pdf
                else:
                    # Equal distribution for any number of containers
                    equal_size = total_width // 2
                    sizes = [equal_size] * container_count
                    self.main_splitter.setSizes(sizes)
            
            # === STEP 6: Adjust vertical splitter if it exists ===
            if hasattr(self, 'editor_vertical_splitter') and self.editor_vertical_splitter is not None:
                self.editor_vertical_splitter.adjustSize()
                    
            # Add terminal tab if visible
            terminal_visible = getattr(self.main_window, 'terminal_tab_visible', True)
            if terminal_visible:
                self._create_terminal_tab()
                
            # ========== ADD THIS SECTION BEFORE THE RETURN ==========
            # Connect splitter signals for auto-save
            self.connect_splitter_signals()
            
            # Restore saved splitter sizes (only on first setup)
            if self._should_restore_splitter_sizes and not self._initial_layout_done:
                # Use a timer to restore after layout is fully rendered
                QTimer.singleShot(200, self.restore_splitter_sizes)
                self._initial_layout_done = True
                #print("📋 Scheduled splitter size restoration")
            # ========== END OF NEW SECTION ==========    
            
            #print(f"✅ Layout setup complete with {container_count} containers")
            return self.main_splitter
            
            
        except Exception as e:
            print(f"❌ Error in setup_layout: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: create minimal splitter
            if not hasattr(self, 'main_splitter') or self.main_splitter is None:
                self.main_splitter = QSplitter(Qt.Horizontal)
                self.main_splitter.setChildrenCollapsible(False)
            
            return self.main_splitter

    def save_current_splitter_sizes(self):
        """Save current splitter sizes to config"""
        try:
            if not hasattr(self.main_window, 'config_manager'):
                #print("⚠️ No config_manager available for saving splitter sizes")
                return
            
            config_manager = self.main_window.config_manager
            
            # Save main splitter sizes
            if self.main_splitter and self.main_splitter.count() > 0:
                sizes = self.main_splitter.sizes()
                if sizes and sum(sizes) > 0:
                    config_manager.save_splitter_sizes('main_splitter', sizes)
                    #print(f"💾 Main splitter sizes saved: {sizes}")
            
            # Save editor vertical splitter sizes
            if self.editor_vertical_splitter and self.editor_vertical_splitter.count() > 0:
                sizes = self.editor_vertical_splitter.sizes()
                if sizes and sum(sizes) > 0:
                    config_manager.save_splitter_sizes('editor_vertical_splitter', sizes)
                    #print(f"💾 Editor vertical splitter sizes saved: {sizes}")
                    
        except Exception as e:
            print(f"❌ Error saving splitter sizes: {e}")
            import traceback
            traceback.print_exc()
        
    def restore_splitter_sizes(self):
        """Restore splitter sizes from config"""
        try:
            if not hasattr(self.main_window, 'config_manager'):
                #print("⚠️ No config_manager available for restoring splitter sizes")
                return
            
            config_manager = self.main_window.config_manager
            
            # Restore main splitter sizes
            if self.main_splitter and self.main_splitter.count() > 0:
                saved_sizes = config_manager.get_splitter_sizes('main_splitter')
                if saved_sizes:
                    # Check if the number of widgets matches
                    if len(saved_sizes) == self.main_splitter.count():
                        # Validate sizes are reasonable
                        total = sum(saved_sizes)
                        if total > 0:
                            self.main_splitter.setSizes(saved_sizes)
                            #print(f"✅ Restored main splitter sizes: {saved_sizes}")
                    #else:
                    #    print(f"⚠️ Saved sizes count ({len(saved_sizes)}) doesn't match widget count ({self.main_splitter.count()})")
            
            # Restore editor vertical splitter sizes
            if self.editor_vertical_splitter and self.editor_vertical_splitter.count() > 0:
                saved_sizes = config_manager.get_splitter_sizes('editor_vertical_splitter')
                if saved_sizes:
                    if len(saved_sizes) == self.editor_vertical_splitter.count():
                        total = sum(saved_sizes)
                        if total > 0:
                            self.editor_vertical_splitter.setSizes(saved_sizes)
                            #print(f"✅ Restored editor vertical splitter sizes: {saved_sizes}")
                    #else:
                    #    print(f"⚠️ Saved editor splitter sizes count doesn't match widget count")
                        
        except Exception as e:
            print(f"❌ Error restoring splitter sizes: {e}")
            import traceback
            traceback.print_exc()

    def connect_splitter_signals(self):
        """Connect splitter moved signals to save sizes"""
        try:
            # Connect main splitter
            if self.main_splitter:
                # Disconnect first to avoid duplicate connections
                try:
                    self.main_splitter.splitterMoved.disconnect(self._on_splitter_moved)
                except (TypeError, RuntimeError):
                    pass  # Not connected yet
                self.main_splitter.splitterMoved.connect(self._on_splitter_moved)
                #print("✅ Connected main splitter signal")
            
            # Connect editor vertical splitter
            if self.editor_vertical_splitter:
                try:
                    self.editor_vertical_splitter.splitterMoved.disconnect(self._on_splitter_moved)
                except (TypeError, RuntimeError):
                    pass
                self.editor_vertical_splitter.splitterMoved.connect(self._on_splitter_moved)
                #print("✅ Connected editor vertical splitter signal")
                
        except Exception as e:
            print(f"❌ Error connecting splitter signals: {e}")

    def _on_splitter_moved(self, pos, index):
        """Handle splitter moved event - save sizes after a delay to avoid excessive saves"""
        # Use a timer to debounce - only save 500ms after user stops dragging
        if self._save_timer is None:
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._debounced_save_splitter_sizes)
        
        # Reset/start the timer
        self._save_timer.stop()
        self._save_timer.start(500)  # 500ms delay
######      

    def refresh_welcome_pages(self):
        """Re-style welcome pages in place WITHOUT removing/reinserting tabs."""
        from style_manager import get_welcome_style
        w = get_welcome_style()

        TOOL_TABS = {
            "AI Assistant", "Tools", "Accessories", "Insert Character", "Latex Wizard",
            "TikZ Plotter", "File Comparison", "PDF Comparison", "Todo list", "Spreadsheet"
        }

        # Editor welcome — re-style the existing widget, never remove it
        editor_tabs = getattr(self.main_window.editor_manager, 'editor_tabs', None)
        if isinstance(editor_tabs, QTabWidget):
            for i in range(editor_tabs.count()):
                widget = editor_tabs.widget(i)
                if widget and widget.objectName() == "editor_welcome_outer_frame":
                    self._restyle_welcome_frame(widget, w, "editor")
                    break

        # PDF welcome — re-style the existing widget, never remove it
        pdf_manager = getattr(self.main_window, 'pdf_manager', None)
        pdf_tabs = getattr(pdf_manager, 'pdf_tabs', None)
        if isinstance(pdf_tabs, QTabWidget):
            for i in range(pdf_tabs.count()):
                tab_text = pdf_tabs.tabText(i)
                if tab_text in TOOL_TABS:
                    continue  # Never touch tool tabs
                widget = pdf_tabs.widget(i)
                if widget and widget.objectName() == "pdf_welcome_outer_frame":
                    self._restyle_welcome_frame(widget, w, "pdf")
                    break

    def _restyle_welcome_frame(self, outer_frame, w, frame_type):
        """Re-apply theme colors to an existing welcome frame in place."""
        from PyQt5.QtWidgets import QFrame, QLabel, QWidget

        outer_frame.setStyleSheet(f"""
            QFrame#{frame_type}_welcome_outer_frame {{
                background-color: {w['outer_bg']};
                border: 1px solid {w['outer_border']};
            }}
        """)

        # Find and restyle the inner frame
        for child in outer_frame.findChildren(QFrame):
            obj_name = child.objectName()
            if obj_name == f"{frame_type}_welcome_inner_frame":
                child.setStyleSheet(f"""
                    QFrame#{frame_type}_welcome_inner_frame {{
                        background-color: {w['inner_bg']};
                        border: 1px solid {w['inner_border']};
                    }}
                """)

        # ✅ Restyle action-item rows (hover colour + child labels)
        for child in outer_frame.findChildren(QWidget):
            if not child.property("welcome_action_item"):
                continue
            obj_name = child.objectName()          # e.g. "welcome_item_new"
            child.setStyleSheet(f"""
                QWidget#{obj_name} {{
                    background-color: transparent;
                    border-radius: 4px;
                }}
                QWidget#{obj_name}:hover {{
                    background-color: {w['hover_bg']};
                }}
            """)
            # Restyle child labels inside this action item
            for label in child.findChildren(QLabel):
                s = label.styleSheet()
                if not s or 'color' not in s:
                    continue
                if w['shortcut_color'] in s or 'shortcut' in s.lower():
                    label.setStyleSheet(
                        f"color: {w['shortcut_color']}; background-color: transparent;")
                else:
                    label.setStyleSheet(
                        f"color: {w['link_color']}; background-color: transparent;")

        # Restyle remaining labels (headers, "Recent Files:", etc.)
        for label in outer_frame.findChildren(QLabel):
            # Skip labels that are already handled inside action items
            parent = label.parent()
            while parent and parent is not outer_frame:
                if parent.property("welcome_action_item"):
                    break
                parent = parent.parent()
            else:
                # label is NOT inside an action item — handle it here
                current_style = label.styleSheet()
                if w['link_color'] and 'color' in current_style:
                    if 'header_text' in current_style or 'Recent' in label.text():
                        label.setStyleSheet(
                            f"color: {w['header_text']}; background-color: transparent;")
                    elif 'shortcut' in current_style.lower():
                        label.setStyleSheet(
                            f"color: {w['shortcut_color']}; background-color: transparent;")                      
                    
    def _create_editor_welcome_content(self):
        """Create simple welcome content for LaTeX editor - WITH DOUBLE BORDER."""
        from PyQt5.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel,
            QScrollArea, QFrame, QSizePolicy
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        import os
        from style_manager import get_welcome_style
        w = get_welcome_style()

        # =============================================
        # OUTER FRAME (continuation of tab border)
        # =============================================
        outer_frame = QFrame()
        outer_frame.setObjectName("editor_welcome_outer_frame")
        outer_frame.setStyleSheet(f"""
            QFrame#editor_welcome_outer_frame {{
                background-color: {w['outer_bg']};
                border: 1px solid {w['outer_border']};
            }}
        """)

        # ✅ Enable drag-and-drop on outer frame
        outer_frame.setAcceptDrops(True)
        editor_manager = self.main_window.editor_manager

        def welcome_drag_enter(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        event.acceptProposedAction()
                        return
            event.ignore()

        def welcome_drag_move(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        event.acceptProposedAction()
                        return
            event.ignore()

        def welcome_drop(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    if file_path and os.path.isfile(file_path):
                        editor_manager.open_specific_file(file_path)
                event.acceptProposedAction()
                return
            event.ignore()

        outer_frame.dragEnterEvent = welcome_drag_enter
        outer_frame.dragMoveEvent = welcome_drag_move
        outer_frame.dropEvent = welcome_drop
###
        
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(1, 1, 1, 2)  # Small gap between outer and inner
        outer_layout.setSpacing(0)

        # =============================================
        # INNER FRAME (the internal border)
        # =============================================
        inner_frame = QFrame()
        inner_frame.setObjectName("editor_welcome_inner_frame")
        inner_frame.setStyleSheet(f"""
            QFrame#editor_welcome_inner_frame {{
                background-color: {w['inner_bg']};
                border: 1px solid {w['inner_border']};
            }}
        """)

        # =============================================
        # CONTENT LAYOUT
        # =============================================
        main_layout = QVBoxLayout(inner_frame)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(15)
        
        main_layout.addStretch(1)
        
        # Actions container
        actions_container = QWidget()
        actions_container.setStyleSheet("background-color: transparent;")
        actions_container.setMaximumWidth(400)
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        icons_manager = None
        if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'icons_manager'):
            icons_manager = self.main_window.menu_manager.icons_manager
        
        # New File
        new_file_item = self._create_welcome_action_item(
            icons_manager, "new", "New File", "Ctrl+N",
            lambda: self.main_window.editor_manager.new_file()
        )
        actions_layout.addWidget(new_file_item)
        
        # Open File
        open_file_item = self._create_welcome_action_item(
            icons_manager, "open", "Open File", "Ctrl+O",
            lambda: self.main_window.editor_manager.open_file()
        )
        actions_layout.addWidget(open_file_item)
        
        # Separator
        separator_label = QLabel()
        separator_label.setFixedHeight(1)
        separator_label.setStyleSheet(f"background-color: {w['separator']};")
        actions_layout.addSpacing(10)
        actions_layout.addWidget(separator_label)
        actions_layout.addSpacing(5)
        
        # Recent header
        recent_header = QLabel("<b>Recent Files:</b>")
        recent_header.setStyleSheet(f"color: {w['header_text']}; background-color: transparent;")
        actions_layout.addWidget(recent_header)
        
        # Recent files list
        recent_scroll = self._create_editor_recent_files_list_no_frame()
        actions_layout.addWidget(recent_scroll)
        
        # Center
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(actions_container)
        h_layout.addStretch(1)
        main_layout.addLayout(h_layout)
        
        main_layout.addStretch(1)
        
        # Add inner frame to outer frame
        outer_layout.addWidget(inner_frame)
        
        outer_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return outer_frame


    def _create_pdf_welcome_content(self):
        """Create simple welcome content for PDF viewer - WITH DOUBLE BORDER."""
        from PyQt5.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel,
            QScrollArea, QFrame, QSizePolicy
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        import os
        from style_manager import get_welcome_style
        w = get_welcome_style()

        # =============================================
        # OUTER FRAME (continuation of tab border)
        # =============================================
        outer_frame = QFrame()
        outer_frame.setObjectName("pdf_welcome_outer_frame")
        outer_frame.setStyleSheet(f"""
            QFrame#pdf_welcome_outer_frame {{
                background-color: {w['outer_bg']};
                border: 1px solid {w['outer_border']};
            }}
        """)




        # ✅ Enable drag-and-drop for PDF files on outer frame
        outer_frame.setAcceptDrops(True)
        pdf_manager = self.main_window.pdf_manager

        def pdf_welcome_drag_enter(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if file_path.lower().endswith('.pdf'):
                            event.acceptProposedAction()
                            return
            event.ignore()

        def pdf_welcome_drag_move(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if file_path.lower().endswith('.pdf'):
                            event.acceptProposedAction()
                            return
            event.ignore()

        def pdf_welcome_drop(event):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    if file_path and os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                        pdf_manager.load_pdf_in_viewer(file_path, bring_to_front=True)
                        if hasattr(pdf_manager.main_window, 'config_manager'):
                            pdf_manager.main_window.config_manager.add_recent_pdf_file(file_path)
                event.acceptProposedAction()
                return
            event.ignore()

        outer_frame.dragEnterEvent = pdf_welcome_drag_enter
        outer_frame.dragMoveEvent = pdf_welcome_drag_move
        outer_frame.dropEvent = pdf_welcome_drop


        
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(1, 1, 1, 2)  # Small gap between outer and inner
        outer_layout.setSpacing(0)

        # =============================================
        # INNER FRAME (the internal border)
        # =============================================
        inner_frame = QFrame()
        inner_frame.setObjectName("pdf_welcome_inner_frame")
        inner_frame.setStyleSheet(f"""
            QFrame#pdf_welcome_inner_frame {{
                background-color: {w['inner_bg']};
                border: 1px solid {w['inner_border']};
            }}
        """)

        # =============================================
        # CONTENT LAYOUT
        # =============================================
        main_layout = QVBoxLayout(inner_frame)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(15)
        
        main_layout.addStretch(1)
        
        # Actions container
        actions_container = QWidget()
        actions_container.setStyleSheet("background-color: transparent;")
        actions_container.setMaximumWidth(400)
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        icons_manager = None
        if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'icons_manager'):
            icons_manager = self.main_window.menu_manager.icons_manager
        
        # Open PDF File
        open_pdf_callback = lambda: self.main_window.pdf_manager.open_pdf_file()
        open_pdf_item = self._create_welcome_action_item(
            icons_manager, "pdf", "Open PDF", "Ctrl+Shift+O", open_pdf_callback
        )
        actions_layout.addWidget(open_pdf_item)
        
        # Separator
        separator_label = QLabel()
        separator_label.setFixedHeight(1)
        separator_label.setStyleSheet(f"background-color: {w['separator']};")
        actions_layout.addSpacing(10)
        actions_layout.addWidget(separator_label)
        actions_layout.addSpacing(5)
        
        # Recent Files header
        recent_header = QLabel("<b>Recent Files:</b>")
        recent_header.setStyleSheet(f"color: {w['header_text']}; background-color: transparent;")
        actions_layout.addWidget(recent_header)
        
        # Recent PDF files list
        recent_scroll = self._create_pdf_recent_files_list_no_frame()
        actions_layout.addWidget(recent_scroll)
        
        # Center
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(actions_container)
        h_layout.addStretch(1)
        main_layout.addLayout(h_layout)
        
        main_layout.addStretch(1)
        
        # Add inner frame to outer frame
        outer_layout.addWidget(inner_frame)
        
        outer_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return outer_frame
    
    

    def _create_editor_recent_files_list_no_frame(self):
        """Create recent tex files list WITHOUT any QFrame elements."""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        from style_manager import get_welcome_style, get_tooltip_qss
        import os

        w = get_welcome_style()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(180)
        scroll_area.setMinimumHeight(80)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            "QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(4)

        recent_files = []
        if hasattr(self.main_window, 'config_manager'):
            recent_files = self.main_window.config_manager.get_recent_files()[:101]

        if not recent_files:
            lbl = QLabel("No recent files")
            lbl.setStyleSheet(
                f"color: {w['no_files_color']};"
                " font-style: italic;"
                " background-color: transparent;")
            layout.addWidget(lbl)
        else:
            for file_path in recent_files:
                if not os.path.exists(file_path):
                    continue

                filename = os.path.basename(file_path)
                lbl = QLabel(filename)
                lbl.setCursor(QCursor(Qt.PointingHandCursor))
                lbl.setToolTip(file_path)
                lbl.setStyleSheet(
                    f"QLabel {{ color: {w['link_color']}; background-color: transparent; padding: 2px 4px; border-radius: 3px; }}"
                    + get_tooltip_qss()
                )

                def make_click(path):
                    def handler(event):
                        self.main_window.editor_manager.open_specific_file(path)
                    return handler

                lbl.mousePressEvent = make_click(file_path)
                layout.addWidget(lbl)

        layout.addStretch()
        scroll_area.setWidget(container)
        return scroll_area


    def _create_pdf_recent_files_list_no_frame(self):
        """Create recent PDF files list WITHOUT any QFrame elements."""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        from style_manager import get_welcome_style, get_tooltip_qss
        import os

        w = get_welcome_style()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(180)
        scroll_area.setMinimumHeight(80)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            "QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(4)

        recent_files = []
        if hasattr(self.main_window, 'config_manager'):
            recent_files = self.main_window.config_manager.get_recent_pdf_files()[:101]

        if not recent_files:
            lbl = QLabel("No recent files")
            lbl.setStyleSheet(
                f"color: {w['no_files_color']};"
                " font-style: italic;"
                " background-color: transparent;")
            layout.addWidget(lbl)
        else:
            for file_path in recent_files:
                if not os.path.exists(file_path):
                    continue

                filename = os.path.basename(file_path)
                lbl = QLabel(filename)
                lbl.setCursor(QCursor(Qt.PointingHandCursor))
                lbl.setToolTip(file_path)
                lbl.setStyleSheet(
                    f"QLabel {{ color: {w['link_color']}; background-color: transparent; padding: 2px 4px; border-radius: 3px; }}"
                    + get_tooltip_qss()
                )
                def make_click(path):
                    def handler(event):
                        self.main_window.pdf_manager.open_recent_pdf_file(path)
                    return handler

                lbl.mousePressEvent = make_click(file_path)
                layout.addWidget(lbl)

        layout.addStretch()
        scroll_area.setWidget(container)
        return scroll_area

    def _create_welcome_action_item(self, icons_manager, icon_name, text, shortcut, callback):
        """Create a clickable action item - NO FRAMES."""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        from style_manager import get_welcome_style
        w = get_welcome_style()

        item_widget = QWidget()
        item_widget.setCursor(QCursor(Qt.PointingHandCursor))
        # Use object name for hover — avoids the app-level QPushButton conflict
        item_widget.setObjectName(f"welcome_item_{icon_name}")
        # ✅ Mark so _restyle_welcome_frame can find and re-theme this widget
        item_widget.setProperty("welcome_action_item", True)
        item_widget.setStyleSheet(f"""
            QWidget#welcome_item_{icon_name} {{
                background-color: transparent;
                border-radius: 4px;
            }}
            QWidget#welcome_item_{icon_name}:hover {{
                background-color: {w['hover_bg']};
            }}
        """)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 6, 8, 6)
        item_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet("background-color: transparent;")
        icon_pixmap = self._create_painted_icon(icon_name, 24)
        if icon_pixmap and not icon_pixmap.isNull():
            icon_label.setPixmap(icon_pixmap)
        item_layout.addWidget(icon_label)

        text_label = QLabel(text)
        text_label.setStyleSheet(
            f"color: {w['link_color']}; background-color: transparent;")
        item_layout.addWidget(text_label)

        shortcut_label = QLabel(f"({shortcut})")
        shortcut_label.setStyleSheet(
            f"color: {w['shortcut_color']}; background-color: transparent;")
        item_layout.addWidget(shortcut_label)

        item_layout.addStretch()
        item_widget.mousePressEvent = lambda event: callback()
        return item_widget

    def _create_painted_icon(self, icon_name, size=24):
        """Create a custom painted icon for welcome screen - FIXED sizing"""
        from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QFont
        from PyQt5.QtCore import Qt, QRectF, QPointF
        
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Define colors
            primary_color = QColor("#0066cc")
            secondary_color = QColor("#4a90d9")
            accent_color = QColor("#ffffff")
            
            # Scale factor - draw within bounds with 2px margin
            margin = 2
            scale = (size - 2 * margin) / 24.0  # Original design was for 24px
            
            painter.translate(margin, margin)
            painter.scale(scale, scale)
            
            if icon_name == "new":
                # Draw "New File" icon - document with plus sign
                pen = QPen(primary_color, 1.5)
                painter.setPen(pen)
                painter.setBrush(QBrush(accent_color))
                
                # Document shape (within 0-24 range)
                doc_path = QPainterPath()
                doc_path.moveTo(3, 1)
                doc_path.lineTo(15, 1)
                doc_path.lineTo(21, 7)
                doc_path.lineTo(21, 23)
                doc_path.lineTo(3, 23)
                doc_path.closeSubpath()
                painter.drawPath(doc_path)
                
                # Folded corner
                painter.setBrush(QBrush(QColor("#e0e0e0")))
                corner_path = QPainterPath()
                corner_path.moveTo(15, 1)
                corner_path.lineTo(15, 7)
                corner_path.lineTo(21, 7)
                corner_path.closeSubpath()
                painter.drawPath(corner_path)
                
                
            elif icon_name == "open":
                # Draw "Open" icon - PDF-style document, but keep OPEN colors and TeX text
                pen = QPen(primary_color, 1.5)
                painter.setPen(pen)
                painter.setBrush(QBrush(accent_color))

                # Document shape
                doc_path = QPainterPath()
                doc_path.moveTo(3, 1)
                doc_path.lineTo(15, 1)
                doc_path.lineTo(21, 7)
                doc_path.lineTo(21, 23)
                doc_path.lineTo(3, 23)
                doc_path.closeSubpath()
                painter.drawPath(doc_path)

                # Folded corner (light blue instead of red tint)
                painter.setBrush(QBrush(QColor("#d4e6f9")))
                corner_path = QPainterPath()
                corner_path.moveTo(15, 1)
                corner_path.lineTo(15, 7)
                corner_path.lineTo(21, 7)
                corner_path.closeSubpath()
                painter.drawPath(corner_path)

                # Blue banner for TeX text (same family as open colors)
                painter.setBrush(QBrush(primary_color))
                painter.setPen(Qt.NoPen)
                painter.drawRect(3, 12, 18, 8)

                # TeX text
                painter.setPen(QPen(Qt.white))
                font = QFont("Arial", 7, QFont.Bold)
                painter.setFont(font)
                painter.drawText(QRectF(3, 12, 18, 8), Qt.AlignCenter, "TeX")


                
            elif icon_name == "pdf":
                # Draw "PDF" icon - red document
                pen = QPen(QColor("#cc0000"), 1.5)
                painter.setPen(pen)
                painter.setBrush(QBrush(accent_color))
                
                # Document shape
                doc_path = QPainterPath()
                doc_path.moveTo(3, 1)
                doc_path.lineTo(15, 1)
                doc_path.lineTo(21, 7)
                doc_path.lineTo(21, 23)
                doc_path.lineTo(3, 23)
                doc_path.closeSubpath()
                painter.drawPath(doc_path)
                
                # Folded corner
                painter.setBrush(QBrush(QColor("#ffcccc")))
                corner_path = QPainterPath()
                corner_path.moveTo(15, 1)
                corner_path.lineTo(15, 7)
                corner_path.lineTo(21, 7)
                corner_path.closeSubpath()
                painter.drawPath(corner_path)
                
                # Red banner for PDF text
                painter.setBrush(QBrush(QColor("#cc0000")))
                painter.setPen(Qt.NoPen)
                painter.drawRect(3, 12, 18, 8)
                
                # PDF text
                painter.setPen(QPen(Qt.white))
                font = QFont("Arial", 7, QFont.Bold)
                painter.setFont(font)
                painter.drawText(QRectF(3, 12, 18, 8), Qt.AlignCenter, "PDF")
                
            else:
                # Default: simple document icon
                pen = QPen(primary_color, 1.5)
                painter.setPen(pen)
                painter.setBrush(QBrush(accent_color))
                
                # Simple document
                painter.drawRoundedRect(3, 1, 18, 22, 2, 2)
                
                # Lines representing text
                painter.setPen(QPen(QColor("#cccccc"), 1.5))
                painter.drawLine(6, 6, 18, 6)
                painter.drawLine(6, 10, 18, 10)
                painter.drawLine(6, 14, 14, 14)
        
        
        finally:
            painter.end()
            
        return pixmap

    def _debounced_save_splitter_sizes(self):
        """Actually save splitter sizes after debounce delay"""
        #print("🔄 Saving splitter sizes after user stopped dragging...")
        self.save_current_splitter_sizes()
    
        

    def _create_terminal_tab(self):
        """Create and add terminal tab to output container"""
        # Create widget if needed
        self._create_terminal_tab_widget()
        
        # Add to output container if not already there
        if self.output_container and self.terminal_widget:
            # Check if terminal tab already exists
            terminal_exists = False
            for i in range(self.output_container.count()):
                if self.output_container.widget(i) == self.terminal_widget:
                    terminal_exists = True
                    break
                    
            if not terminal_exists:
                self.output_container.addTab(self.terminal_widget, "Terminal")

    def _create_terminal_tab_widget(self):
        """Create the terminal widget instance"""
        if self.terminal_widget is None:
            # Import here to avoid circular imports
            from terminal_widget import AIWidgetLite
            self.terminal_widget = TerminalWidget(self.main_window)
            
            # Set initial directory to current file if available
            if hasattr(self.main_window, 'editor_manager'):
                current_file = self.main_window.editor_manager.get_current_file_path()
                if current_file:
                    self.terminal_widget.set_working_directory(current_file)
        
        return self.terminal_widget

    def _create_editor_container(self):
        """Create editor container layout"""
        # Preserve output container (do NOT destroy)
        preserved_output = self.output_container

        # Only destroy the vertical splitter, not the container
        if self.editor_vertical_splitter is not None:
            # Remove all children first
            for i in reversed(range(self.editor_vertical_splitter.count())):
                widget = self.editor_vertical_splitter.widget(i)
                if widget != preserved_output:  # Keep output
                    widget.setParent(None)  # Proper removal
            self.editor_vertical_splitter = None

        # Create editor_container with proper parent
        if self.editor_container is None:
            self.editor_container = QWidget(self.main_splitter)  # Set parent
            self.editor_container.setObjectName('editor_container')  # ✅ ADD THIS
            layout = QVBoxLayout(self.editor_container)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            # Clear layout
            self.editor_container.setObjectName('editor_container')  # ✅ ADD THIS
            while self.editor_container.layout().count():
                item = self.editor_container.layout().takeAt(0)

        # Create new vertical splitter with proper parent
        self.editor_vertical_splitter = QSplitter(Qt.Vertical, self.editor_container)
        self.editor_vertical_splitter.setChildrenCollapsible(False)
        self.editor_vertical_splitter.setHandleWidth(6)

        # Get editor widget
        editor_widget = self.main_window.editor_manager.get_container()
        if editor_widget is None:
            return

        # Add editor and output
        self.editor_vertical_splitter.addWidget(editor_widget)
        if preserved_output and self.editor_vertical_splitter.indexOf(preserved_output) == -1:
            self.editor_vertical_splitter.addWidget(preserved_output)

        # Set sizes
        total_height = 600
        if self.main_window.output_tabs_visible:
            self.editor_vertical_splitter.setSizes([total_height * 2 // 3, total_height // 3])
        else:
            self.editor_vertical_splitter.setSizes([total_height, 0])

        # Add splitter to container
        self.editor_container.layout().addWidget(self.editor_vertical_splitter)

        # Set properties
        self.editor_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.editor_container.setMinimumSize(300, 200)

        # Add to main splitter only if not already present
        if self.main_splitter.indexOf(self.editor_container) == -1:
            self.main_splitter.addWidget(self.editor_container)

        # Ensure editor expands
        self.editor_vertical_splitter.setStretchFactor(0, 1)  # Editor stretches
        self.editor_vertical_splitter.setStretchFactor(1, 0)  # Output does not

    def _create_pdf_container(self):
        """Create PDF container widget - FIXED"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QSizePolicy
        from PyQt5.QtCore import Qt
        
        if self.pdf_container is None:
            self.pdf_container = QWidget(self.main_splitter)
            self.pdf_container.setObjectName('pdf_container')
            pdf_layout = QVBoxLayout(self.pdf_container)
            pdf_layout.setContentsMargins(0, 0, 0, 0)
            pdf_layout.setSpacing(0)
        else:
            self.pdf_container.setObjectName('pdf_container')
            pdf_layout = self.pdf_container.layout()
            if pdf_layout:
                pdf_layout.setContentsMargins(0, 0, 0, 0)
                pdf_layout.setSpacing(0)
        
        # Clear any existing widgets
        if pdf_layout:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    item.widget().deleteLater()
        
        # Check if we have real PDF content
        pdf_widget = None
        if hasattr(self.main_window, 'pdf_manager'):
            pdf_widget = self.main_window.pdf_manager.get_container()
        
        if not self.main_window.pdf_manager.pdf_files or pdf_widget is None:
            # Create welcome content
            welcome_content = self._create_pdf_welcome_content()
            
            # Create tab widget
            welcome_tab = QTabWidget()
            welcome_tab.setObjectName("pdf_welcome_tab")
            welcome_tab.addTab(welcome_content, "PDF Viewer")
            welcome_tab.setTabsClosable(False)
            
            # Remove the 2-pixel pane border that causes the white bar
            welcome_tab.setStyleSheet("""
                QTabWidget::pane {
                    border: 0px;
                    padding: 0px;
                    margin: 0px;
                    background-color: white;
                }
                QTabWidget::tab-bar {
                    left: 0px;
                }
            """)
            
            
            # Connect close handler
            if hasattr(self.main_window.pdf_manager, '_handle_tab_close_request'):
                welcome_tab.tabCloseRequested.connect(
                    self.main_window.pdf_manager._handle_tab_close_request
                )
            
            # Add to layout
            pdf_layout.addWidget(welcome_tab, 1)
            
            # ✅ CRITICAL: Ensure visibility
            welcome_tab.setVisible(True)
            welcome_tab.show()
            
            # Store reference
            self.main_window.pdf_manager.pdf_tabs = welcome_tab

            # Install tab context menu on this (possibly first) PDF tab bar
            if hasattr(self.main_window, 'tab_context_menu'):
                self.main_window.tab_context_menu.reinstall()

            pdf_widget = welcome_tab
        else:
            if pdf_widget.parent() != self.pdf_container:
                pdf_widget.setParent(self.pdf_container)
            if pdf_layout.indexOf(pdf_widget) == -1:
                pdf_layout.addWidget(pdf_widget)

        return pdf_widget


    

    def _create_output_container(self):
        """Create enhanced output container - ONLY CREATE ONCE"""
        if self.output_container is not None:
            return  # Already exists
            
        # Use enhanced tab widget instead of regular QTabWidget
        self.output_container = EnhancedTabWidget(self.main_window)
        self.output_container.setObjectName('output_container')  
        self.main_window._apply_error_text_style()
        # Add base tabs
        self.output_container.addTab(self.main_window.output_text, "Output")
        self.output_container.addTab(self.main_window.errors_text, "Errors")
        


    def retranslate_output_tabs(self):
        if self.output_container is None:
            return

        mw = self.main_window
        lang = getattr(mw, "menu_language", "en")
        translations = getattr(mw, "translations", {})
        tr = translations.get(lang, {})

        oc = self.output_container

        # Tabs we want to remove/recreate
        keys = ["output","errors","symbols", "commands", "tree", "bookmarks", "terminal"]

        # Build all possible labels (source + all translations)
        possible_labels = {"Output","Errors", "Symbols", "Commands", "Tree", "Bookmarks", "Terminal"}
        for l in translations:
            for k in keys:
                possible_labels.add(translations[l].get(k, ""))

        # Step 1: collect matching tabs (widget + key)
        tabs_to_recreate = []

        for i in reversed(range(oc.count())):  # 🔑 reverse iteration
            text = oc.tabText(i)
            widget = oc.widget(i)

            if text in possible_labels:
                # try to detect which key it is
                found_key = None
                for k in keys:
                    if text == tr.get(k) or any(
                        text == translations[l].get(k) for l in translations
                    ) or text.lower() == k:
                        found_key = k
                        break

                if found_key:
                    tabs_to_recreate.append((widget, found_key))

                oc.removeTab(i)  # remove safely

        # Step 2: re-add them with translated labels
        for widget, key in reversed(tabs_to_recreate):  # preserve order
            oc.addTab(widget, tr.get(key, key.capitalize()))  

            # SYMBOLS
            if key == "symbols" and hasattr(widget, "symbols_tabs"):
                widget.math_menu.build_symbol_categories()

                for i, (k, data) in enumerate(widget.math_menu.symbol_categories.items()):
                    widget.symbols_tabs.setTabText(i, data["tr"])

            # COMMANDS
            if key == "commands" and hasattr(widget, "commands_tabs"):
                widget.commands_menu.build_commands_categories()

                for i, (k, data) in enumerate(widget.commands_menu.sectionning_categories.items()):
                    widget.commands_tabs.setTabText(i, data["tr"])

    
 
    def get_output_container(self):
        """Get the output container (for external access)"""
        return self.output_container

    
 
    def switch_layout(self):
        """Switch between editor_left and pdf_left layouts WITHOUT recreating editors"""
        #print("Switching layout...")
        
        # Toggle the layout
        self.current_layout = "pdf_left" if getattr(self, 'current_layout', 'editor_left') == "editor_left" else "editor_left"
        
        # Save to configuration
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value('layout', 'switch_mode', self.current_layout)
            self.main_window.config_manager.save_config()
        
        # Only rearrange containers - do NOT recreate editor container
        self._arrange_containers()  # This should only move existing containers
        
        # Update status
        status_key = "status_layout_pdf_left" if self.current_layout == "pdf_left" else "status_layout_editor_left"
        if hasattr(self.main_window, 'translations'):
            status_text = self.main_window.translations[self.main_window.menu_language][status_key]
            self.main_window.update_status_bar(status_text)
        


    def _arrange_containers(self):
        """Enhanced container arrangement with proper side panel positioning - SAFE"""
        try:
            # ✅ Ensure main_splitter exists
            if not hasattr(self, 'main_splitter') or self.main_splitter is None:
                #print("⚠️ main_splitter is None, calling setup_layout()")
                self.setup_layout()
                if not hasattr(self, 'main_splitter') or self.main_splitter is None:
                    raise RuntimeError("Failed to create main_splitter")
           
            # FIX: Ensure side panel exists and get reference safely
            if not hasattr(self.main_window, 'side_panel') or self.main_window.side_panel is None:
                #print("⚠️ Side panel not found, creating it...")
                self.main_window.side_panel = SidePanel(self.main_window)
            
            # After creating the side panel
            if not self.main_window.isVisible():
                self.main_window.side_panel.hide()  # Hide until main window shows
            
            side_panel = self.main_window.side_panel
            
            # === STEP 1: Remove ALL widgets from main_splitter ===
            widgets_to_remove = []
            for i in range(self.main_splitter.count()):
                widget = self.main_splitter.widget(i)
                if widget:
                    widgets_to_remove.append(widget)
            
            for widget in widgets_to_remove:
                widget.setParent(None)  # Properly remove from layout
            
            # === STEP 2: Determine order based on layout and side panel position ===
            side_panel_on_left = getattr(self.main_window, 'side_panel_on_left', True)
            show_side_panel = getattr(self.main_window, 'side_panel_visible', True)
            current_layout = getattr(self, 'current_layout', 'editor_left')
            
            containers = []
            
            # Build container list in correct order
            if show_side_panel and side_panel_on_left:
                containers.append(('side_panel', side_panel))
            
            # Add main containers in correct order
            if current_layout == "editor_left":
                containers.append(('editor', self.editor_container))
                containers.append(('pdf', self.pdf_container))
            else:  # "pdf_left"
                containers.append(('pdf', self.pdf_container))
                containers.append(('editor', self.editor_container))
            
            if show_side_panel and not side_panel_on_left:
                containers.append(('side_panel', side_panel))


    
            
            # === STEP 3: Insert all containers in order ===
            for name, widget in containers:
                if widget is not None:
                    self.main_splitter.addWidget(widget)
                    #print(f"  ✅ Added {name} to splitter")
                #else:
                #    print(f"  ❌ Attempted to add None widget ({name}) to splitter")
            
            # === STEP 4: Set sizes and stretch factors ===
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()  # Excludes taskbar/dock
            total_width = screen_geometry.width()
            
            panel_width = min(70, total_width // 6)  # 1/6 of screen width, max 250px
            
            main_width = (total_width - panel_width) // 2 if show_side_panel else total_width // 2
            
            sizes = []
            for name, widget in containers:
                if name == 'side_panel':
                    sizes.append(panel_width)
                else:
                    sizes.append(main_width)
            
            if sizes:
                self.main_splitter.setSizes(sizes)
                #print(f"  📏 Set splitter sizes: {sizes}")
            
            # Set stretch factors
            for i in range(self.main_splitter.count()):
                widget = self.main_splitter.widget(i)
                container_name = None
                for name, cont_widget in containers:
                    if cont_widget == widget:
                        container_name = name
                        break
                
                if container_name == 'side_panel':
                    self.main_splitter.setStretchFactor(i, 0)  # Fixed width
                else:
                    self.main_splitter.setStretchFactor(i, 1)  # Expandable
             
            # === STEP 5: Ensure visibility ===
            if show_side_panel:
                side_panel.show()
            else:
                side_panel.hide()
                 
            self.main_splitter.show()
            self.main_splitter.update()
            
            #print(f"✅ Container arrangement complete - {len(containers)} widgets added")
            for i in range(self.main_splitter.count()):
                w = self.main_splitter.widget(i)
                #print(f"  Widget {i}: {type(w).__name__}")
                
        except Exception as e:
            print(f"❌ Error in _arrange_containers: {e}")
            import traceback
            traceback.print_exc()
       
        
    
    def _create_pdf_wrapper(self, viewer, pdf_path):
        """Create wrapper widget for PDF viewer in splitter mode"""
        from PyQt5.QtWidgets import QLabel, QSizePolicy
        from PyQt5.QtGui import QFont
        
        # FIXED: Set proper parent to prevent popup
        wrapper = QWidget(self.pdf_container)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(2)  # Small spacing between label and viewer
        
        label = QLabel(os.path.basename(pdf_path), wrapper)  # Set parent
        label.setFont(QFont(
            "Amiri" if self.main_window.menu_language == "ar" else "Consolas", 
            self.main_window.toolbar_font_size
        ))
        label.setAlignment(Qt.AlignRight if self.main_window.is_rtl else Qt.AlignLeft)
        label.setContextMenuPolicy(Qt.CustomContextMenu)
        label.customContextMenuRequested.connect(
            lambda pos, p=pdf_path: self.main_window.pdf_manager.show_pdf_context_menu(pos, p)
        )
        label.setMinimumHeight(20)  # Ensure label is visible
        label.setMaximumHeight(25)  # Prevent label from taking too much space
        
        # Make sure viewer expands to fill space and has proper parent
        viewer.setParent(wrapper)
        viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        viewer.setMinimumSize(200, 200)  # Ensure minimum visible size
        
        wrapper_layout.addWidget(label)
        wrapper_layout.addWidget(viewer, 1)  # Give viewer stretch factor of 1
        
        # Ensure wrapper expands
        wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        wrapper.setMinimumSize(250, 250)  # Ensure wrapper has minimum size
        
        return wrapper
                     



    def toggle_editor_layout(self):
        """Toggle editor layout with proper initialization protection"""
        try:
            #print("🔄 toggle_editor_layout called")
            
            # Skip during initialization AND for a short period after session loading
            if (getattr(self.main_window, 'initializing', False) or 
                getattr(self.main_window, 'loading_session', False)):
                #print("Skipping layout toggle - initialization/session loading in progress")
                return
                
            if self._toggle_lock:
                #print("Toggle is locked")
                return
                
            # Add validation checks
            if not hasattr(self, 'editor_vertical_splitter') or self.editor_vertical_splitter is None:
                #print("❌ editor_vertical_splitter not found")
                return
                
            if not hasattr(self.main_window, 'editor_manager'):
                #print("❌ editor_manager not found")
                return
                
            editor_count = len(self.main_window.editor_manager.editor_files)
            #print(f"Editor count: {editor_count}")
            
            if editor_count < 2:
                QMessageBox.information(
                    self.main_window,
                    "Layout Toggle", 
                    "At least 2 files must be opened to change the editor layout.\n\n"
                    "Please open more files to use horizontal or vertical layouts."
                )
                return

            # Rest of your code...
            modes = ["tabbed", "horizontal", "vertical"]
            current_mode = self.main_window.editor_manager.editor_layout_mode
            new_mode = modes[(modes.index(current_mode) + 1) % len(modes)]
            self.main_window.editor_manager.editor_layout_mode = new_mode
            
            if hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.set_config_value('layout', 'editor_layout_mode', new_mode)
            
            # Only recreate if not already scheduled
            if not hasattr(self, '_recreation_pending') or not self._recreation_pending:
                self._recreation_pending = True
                self._safe_recreate_with_cleanup()
            
            # Update status
            status_key = f"status_editor_{new_mode}"
            self.main_window.update_status_bar(
                self.main_window.translations[self.main_window.menu_language][status_key]
            )
        
        except Exception as e:
            print(f"❌ Error in toggle_editor_layout: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self.main_window, "Error", f"Failed to toggle layout: {str(e)}")


    def _safe_recreate_with_cleanup(self):
        """Recreate container and cleanup flags"""
        try:
            self._safe_recreate_editor_container()
        finally:
            self._recreation_pending = False
        
    def _safe_recreate_editor_container(self):
        """Safe recreation without blocking UI"""
        try:
            self._recreate_editor_container()
        except Exception as e:
            print(f"Error in _safe_recreate_editor_container: {e}")


    def toggle_pdf_layout(self):
        """Cycle PDF layout: tabbed → horizontal → vertical → tabbed."""
        pdf_count = 0
        if hasattr(self.main_window.pdf_manager, 'pdf_files') and self.main_window.pdf_manager.pdf_files:
            pdf_count = self.main_window.pdf_manager._get_active_pdf_count()

        if pdf_count < 2:
            from PyQt5.QtWidgets import QMessageBox
            message = (
                "No PDF files are currently open.\n\nPlease open at least 2 PDF files to change the layout."
                if pdf_count == 0 else
                "At least 2 PDF files must be opened to change the PDF layout.\n\nPlease open more PDF files to use horizontal or vertical layouts."
            )
            QMessageBox.information(self.main_window, "Layout Toggle", message)
            return

        modes = ["tabbed", "horizontal", "vertical"]
        current_mode = self.main_window.pdf_manager.pdf_layout_mode
        new_mode = modes[(modes.index(current_mode) + 1) % len(modes)]
        self._apply_pdf_layout(new_mode)

    def _apply_pdf_layout(self, new_mode):
        """Switch the PDF pane directly to *new_mode* (tabbed/horizontal/vertical).

        Called by toggle_pdf_layout (cycle) and by context_menu._set_pdf_layout
        (direct jump).  Keeping the transition logic here — in one place — means
        the context menu never cycles through an intermediate mode, which was the
        source of the brief floating-window flash.
        """
        self.main_window.pdf_manager.pdf_layout_mode = new_mode
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value('layout', 'pdf_layout_mode', new_mode)

        # Detach tab context menu filters BEFORE destroying old widgets
        if hasattr(self.main_window, 'tab_context_menu'):
            self.main_window.tab_context_menu.detach_pdf()

        # Suppress repaints during the transition to avoid any flash
        self.pdf_container.setUpdatesEnabled(False)
        try:
            pdf_layout = self.pdf_container.layout()
            if pdf_layout is None:
                return
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                w = item.widget() if item else None
                if w:
                    self.main_window.pdf_manager._detach_and_destroy_widget(w)
            self.main_window.pdf_manager.pdf_tabs = None
            self.main_window.pdf_manager.pdf_splitter = None
            self._recreate_pdf_container()
        finally:
            self.pdf_container.setUpdatesEnabled(True)
            self.pdf_container.update()

        if hasattr(self.main_window, 'tab_context_menu'):
            self.main_window.tab_context_menu.reinstall_pdf()

        status_key = f"status_pdf_{new_mode}"
        self.main_window.update_status_bar(
            self.main_window.translations[self.main_window.menu_language][status_key]
        )

    def _add_single_welcome_tab(self, container, mode):
        """Helper to add single Krita-style welcome tab"""
        from style_manager import get_welcome_style
        w = get_welcome_style()        
        if mode == "tabbed":
            # Only style the pane, not the tabs
            container.setStyleSheet("""
                QTabWidget::pane {
                    background-color: {w['tab_pane_bg']};
                    border: none;
                }
            """)
            
            welcome_content = self._create_editor_welcome_content()
            container.addTab(welcome_content, "Latex Editor")
            container.setTabsClosable(False)
            
            # ✅ Enable drop on the tab widget itself (for drops on the tab bar area)
            container.setAcceptDrops(True)
            editor_manager = self.main_window.editor_manager

            def tab_drag_enter(event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        if url.isLocalFile():
                            event.acceptProposedAction()
                            return
                # Call original for tab drag-reorder support
                QTabWidget.dragEnterEvent(container, event)

            def tab_drag_move(event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        if url.isLocalFile():
                            event.acceptProposedAction()
                            return
                QTabWidget.dragMoveEvent(container, event)

            def tab_drop(event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        file_path = url.toLocalFile()
                        if file_path and os.path.isfile(file_path):
                            editor_manager.open_specific_file(file_path)
                    event.acceptProposedAction()
                    return
                QTabWidget.dropEvent(container, event)

            container.dragEnterEvent = tab_drag_enter
            container.dragMoveEvent = tab_drag_move
            container.dropEvent = tab_drop
            
        else:
            tab_widget = QTabWidget()
            tab_widget.setTabsClosable(False)
            tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            tab_widget.setMinimumSize(200, 150)
            tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    background-color: {w['tab_pane_bg']};
                    border: none;
                }
            """)
            
            welcome_content = self._create_editor_welcome_content()
            tab_widget.addTab(welcome_content, "Latex Editor")
            
            container.addWidget(tab_widget)
            self.main_window.editor_manager.editor_tabs = [tab_widget]

            if hasattr(self.main_window, 'tab_context_menu'):
                self.main_window.tab_context_menu.reinstall_editor()

    def _recreate_editor_container(self):
        """Recreate editor container with new layout mode - FIXED path/basename issues"""
        if self._recreating:
            return
        self._recreating = True
        
        try:
            # Preserve output container FIRST - this is critical
            preserved_output = self.output_container
            if preserved_output is None:
                self._create_output_container()
                preserved_output = self.output_container
            if preserved_output is None:
                #print("Failed to create output_container!")
                return

            # ✅ Store current editors and their states with safety checks
            # KEY FIX: Always use FULL PATHS as keys consistently
            current_editors = {}
            if hasattr(self.main_window.editor_manager, 'editor_files') and self.main_window.editor_manager.editor_files:
                for full_path, data in self.main_window.editor_manager.editor_files.items():
                    if isinstance(data, dict) and data.get('editor'):
                        editor = data['editor']
                        try:
                            # Test if widget is still alive
                            editor.isVisible()
                            current_editors[full_path] = {  # Use full_path as key
                                'editor': editor,
                                'content': editor.toPlainText(),
                                'pdf_path': data.get('pdf_path', ''),
                                'cursor_position': editor.textCursor().position(),
                                'modified': data.get('modified', False)
                            }
                        except (RuntimeError, AttributeError):
                            print(f"Widget for {full_path} was deleted")
                            current_editors[full_path] = {  # Use full_path as key
                                'editor': None,
                                'content': data.get('saved_content', ''),
                                'pdf_path': data.get('pdf_path', ''),
                                'cursor_position': 0,
                                'modified': data.get('modified', False)
                            }

            
            if hasattr(self.main_window.editor_manager, 'tab_order'):
                #print(f"tab_order contents: {self.main_window.editor_manager.tab_order}")
                for item in self.main_window.editor_manager.tab_order:
                    is_full_path = os.path.isabs(item)
                    #print(f"  {item} -> is_full_path: {is_full_path}")

            # Remove current editor widget from vertical splitter (but keep output)
            if self.editor_vertical_splitter and self.editor_vertical_splitter.count() > 0:
                old_editor_widget = self.editor_vertical_splitter.widget(0)
                if old_editor_widget != preserved_output:
                    old_editor_widget.setParent(None)
                    old_editor_widget.deleteLater()  # <-- Add this line

            # Create new editor widget based on layout mode
            new_editor_widget = None
            mode = self.main_window.editor_manager.editor_layout_mode

            if mode == "tabbed":
                new_editor_widget = QTabWidget(self.editor_vertical_splitter)
                new_editor_widget.setTabsClosable(True)
                new_editor_widget.tabCloseRequested.connect(self.main_window.editor_manager.close_editor_tab)
                new_editor_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                new_editor_widget.setMinimumSize(300, 200)
                self.main_window.editor_manager.editor_tabs = new_editor_widget
                self.main_window.editor_manager.editor_splitter = None
                # ✅ FIX: Reconnect tab-change signal on the NEW widget
                new_editor_widget.currentChanged.connect(self.main_window.editor_manager.on_tab_changed)
                self.main_window.editor_manager._tab_change_connected = True                
            else:
                orientation = Qt.Horizontal if mode == "horizontal" else Qt.Vertical
                new_editor_widget = QSplitter(orientation, self.editor_vertical_splitter)
                new_editor_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                new_editor_widget.setMinimumSize(300, 200)
                new_editor_widget.setChildrenCollapsible(False)
                new_editor_widget.setHandleWidth(3)
                new_editor_widget.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")
                self.main_window.editor_manager.editor_splitter = new_editor_widget
                self.main_window.editor_manager.editor_tabs = []

            # Insert new editor widget at index 0
            self.editor_vertical_splitter.insertWidget(0, new_editor_widget)

            # Ensure output is at the end
            if self.editor_vertical_splitter.indexOf(preserved_output) == -1:
                self.editor_vertical_splitter.addWidget(preserved_output)

            # ✅ Restore editors without recreating them
            if current_editors:
                if mode == "tabbed":
                    # FIXED: Use editor_files keys directly instead of tab_order to ensure consistency
                    ordered_files = []
                    
                    # Try to maintain order from tab_order if it exists and contains full paths
                    if (hasattr(self.main_window.editor_manager, 'tab_order') and 
                        self.main_window.editor_manager.tab_order):
                        
                        # Check if tab_order contains full paths
                        for item in self.main_window.editor_manager.tab_order:
                            if os.path.isabs(item) and item in current_editors:
                                ordered_files.append(item)
                        
                        # Add any missing files from editor_files
                        for full_path in current_editors.keys():
                            if full_path not in ordered_files:
                                ordered_files.append(full_path)
                    else:
                        # No tab_order or it's invalid, use editor_files order
                        ordered_files = list(current_editors.keys())
                        
                    # Add any missing (should not happen, but safe)
                    for path in current_editors.keys():
                        if path not in ordered_files:
                            ordered_files.append(path)                        

                    #print(f"Processing files in order: {[os.path.basename(f) for f in ordered_files]}")

                    for full_path in ordered_files:
                        if full_path not in current_editors:
                            continue
                        
                        editor_info = current_editors[full_path]
                        editor = editor_info['editor']
                        if not editor:
                            continue

                        # ✅ Detach from old parent
                        editor.setParent(None)
                        
                        # Display name uses basename, but key is always full path
                        tab_name = os.path.basename(full_path)
                        if editor_info.get('modified', False):
                            tab_name = f"*{tab_name}"

                        index = new_editor_widget.addTab(editor, tab_name)

                        # ✅ Only update content if needed
                        if editor.toPlainText() != editor_info['content']:
                            editor.blockSignals(True)
                            cursor = editor.textCursor()
                            cursor.beginEditBlock()
                            editor.setPlainText(editor_info['content'])
                            cursor.endEditBlock()
                            editor.blockSignals(False)

                        # ✅ Restore cursor
                        cursor = editor.textCursor()
                        cursor.setPosition(min(editor_info['cursor_position'], len(editor_info['content'])))
                        editor.setTextCursor(cursor)
                        editor.ensureCursorVisible()

                        # Update file data using FULL PATH as key
                        if full_path in self.main_window.editor_manager.editor_files:
                            data = self.main_window.editor_manager.editor_files[full_path]
                            if isinstance(data, dict):
                                data['index'] = index
                                data['saved_content'] = editor_info['content']
                                data['modified'] = editor_info['modified']

                else:
                    # H/V mode - FIXED: Use consistent full path keys
                    ordered_files = []
                    
                    # Try to maintain order from tab_order if it exists and contains full paths
                    if (hasattr(self.main_window.editor_manager, 'tab_order') and 
                        self.main_window.editor_manager.tab_order):
                        
                        for item in self.main_window.editor_manager.tab_order:
                            if os.path.isabs(item) and item in current_editors:
                                ordered_files.append(item)
                        
                        # Add any missing files
                        for full_path in current_editors.keys():
                            if full_path not in ordered_files:
                                ordered_files.append(full_path)
                    else:
                        ordered_files = list(current_editors.keys())

                    for full_path in ordered_files:
                        if full_path not in current_editors:
                            continue
                            
                        editor_info = current_editors[full_path]
                        editor = editor_info['editor']
                        if not editor:
                            continue

                        editor.setParent(None)
                        tab_widget = QTabWidget()
                        tab_widget.setTabsClosable(True)
                        
                        # Create closure with full path
                        def make_close_handler(file_path):
                            def handler(idx):
                                self.main_window.editor_manager.close_editor_tab_by_filename(file_path)
                            return handler
                        
                        tab_widget.tabCloseRequested.connect(make_close_handler(full_path))
                        # ✅ FIX: Connect tabBarClicked for H/V border highlighting
                        tab_widget.tabBarClicked.connect(
                            lambda idx, e=editor: self.main_window.editor_manager._on_hv_tab_bar_clicked(idx, e)
                        )                        
                        tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        tab_widget.setMinimumSize(200, 150)
                        
                        # Display name uses basename, but operations use full path
                        tab_name = os.path.basename(full_path)
                        if editor_info.get('modified', False):
                            tab_name = f"*{tab_name}"
                            
                        tab_widget.addTab(editor, tab_name)

                        # ✅ Restore content only if changed
                        if editor.toPlainText() != editor_info['content']:
                            editor.blockSignals(True)
                            cursor = editor.textCursor()
                            cursor.beginEditBlock()
                            if hasattr(editor, 'loadFileContent'):
                                editor.loadFileContent(editor_info['content'])
                            else:
                                editor.setPlainText(editor_info['content'])
                            cursor.endEditBlock()
                            editor.blockSignals(False)

                        # Restore cursor
                        cursor = editor.textCursor()
                        cursor.setPosition(min(editor_info['cursor_position'], len(editor_info['content'])))
                        editor.setTextCursor(cursor)
                        editor.ensureCursorVisible()

                        # Store using FULL PATH as key
                        if full_path in self.main_window.editor_manager.editor_files:
                            data = self.main_window.editor_manager.editor_files[full_path]
                            if isinstance(data, dict):
                                data['tab_widget'] = tab_widget
                                data['index'] = 0

                        new_editor_widget.addWidget(tab_widget)
                        self.main_window.editor_manager.editor_tabs.append(tab_widget)

                    # Set equal sizes for all widgets
                    if new_editor_widget.count() > 0:
                        equal_size = 600 // new_editor_widget.count()
                        new_editor_widget.setSizes([equal_size] * new_editor_widget.count())
            else:
                # No editors: show welcome
                self._add_single_welcome_tab(new_editor_widget, mode)

            # Set sizes for vertical splitter
            total = 600
            if hasattr(self.main_window, 'output_tabs_visible') and self.main_window.output_tabs_visible:
                self.editor_vertical_splitter.setSizes([total * 2 // 3, total // 3])
            else:
                self.editor_vertical_splitter.setSizes([total, 0])

            # Force visibility and update
            new_editor_widget.show()
            new_editor_widget.update()
            self.editor_vertical_splitter.update()

            # Update UI
            if hasattr(self.main_window, 'update_title'):
                self.main_window.update_title()

            # Reinstall tab context menus on the new editor tab bar(s) only
            if hasattr(self.main_window, 'tab_context_menu'):
                self.main_window.tab_context_menu.reinstall_editor()

        except Exception as e:
            print(f"❌ Error in _recreate_editor_container: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            self._recreating = False
 

    def _recreate_pdf_container(self):
        """Recreate PDF container with new layout mode - FIXED to preserve data and display splitters properly"""
        try:           
            #print(f"Recreating PDF container with mode: {self.main_window.pdf_manager.pdf_layout_mode}")
            # Store current PDF data WITHOUT clearing the manager's data
            current_pdfs = {}
            if hasattr(self.main_window.pdf_manager, 'pdf_files') and self.main_window.pdf_manager.pdf_files:
                for pdf_path, data in self.main_window.pdf_manager.pdf_files.items():
                    if os.path.exists(pdf_path):
                        if isinstance(data, (list, tuple)) and len(data) > 0:
                            viewer = data[0]
                        elif isinstance(data, dict):
                            viewer = data.get('viewer')
                        else:
                            continue
                        if viewer:
                            current_pdfs[pdf_path] = {
                                'viewer': viewer,
                                'data': data  # Keep original data structure
                            }
            # Get current layout and clear old widget safely
            pdf_layout = self.pdf_container.layout()
            if pdf_layout.count() > 0:
                old_pdf_widget = pdf_layout.itemAt(0).widget()
                if old_pdf_widget:
                    # Detach filters and schedule deletion — bare setParent(None)
                    # leaves dangling _TabBarFilter C++ references that crash later.
                    self.main_window.pdf_manager._detach_and_destroy_widget(old_pdf_widget)
            # Clear old manager widget references but NOT the file data
            old_tabs = getattr(self.main_window.pdf_manager, 'pdf_tabs', None)
            old_splitter = getattr(self.main_window.pdf_manager, 'pdf_splitter', None)
            # Create new widget based on layout mode
            new_pdf_widget = None
            mode = self.main_window.pdf_manager.pdf_layout_mode
            if mode == "tabbed":
                new_pdf_widget = QTabWidget(self.pdf_container)
                new_pdf_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                new_pdf_widget.setTabsClosable(True)
                # Use the wrapper method
                new_pdf_widget.tabCloseRequested.connect(self.main_window.pdf_manager.close_pdf_tab_by_signal)
                new_pdf_widget.setMinimumSize(300, 200)
                self.main_window.pdf_manager.pdf_tabs = new_pdf_widget
                self.main_window.pdf_manager.pdf_splitter = None
                # ✅ FIX: Connect tab-change signal for border highlighting
                new_pdf_widget.currentChanged.connect(self.main_window.pdf_manager.on_pdf_tab_changed)                
            else:
                orientation = Qt.Horizontal if mode == "horizontal" else Qt.Vertical
                new_pdf_widget = QSplitter(orientation, self.pdf_container)
                new_pdf_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                new_pdf_widget.setMinimumSize(300, 200)
                # Set splitter properties for proper display
                new_pdf_widget.setChildrenCollapsible(False)  # Prevent widgets from collapsing
                new_pdf_widget.setHandleWidth(3)  # Make splitter handle visible
                new_pdf_widget.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")
                self.main_window.pdf_manager.pdf_splitter = new_pdf_widget
                self.main_window.pdf_manager.pdf_tabs = []  # Store multiple tab widgets
            # Add to layout
            pdf_layout.addWidget(new_pdf_widget)
            # Restore PDF viewers - DON'T clear pdf_files
            if mode == "tabbed":
                # Standard tabbed mode - all PDFs in one tab widget
                for pdf_path, pdf_info in current_pdfs.items():
                    viewer = pdf_info['viewer']
                    viewer.setParent(new_pdf_widget)
                    tab_name = os.path.basename(pdf_path)
                    index = new_pdf_widget.addTab(viewer, tab_name)
                    # Update the file data with new index
                    if pdf_path in self.main_window.pdf_manager.pdf_files:
                        data = self.main_window.pdf_manager.pdf_files[pdf_path]
                        if isinstance(data, list) and len(data) > 2:
                            data[2] = index
                        elif isinstance(data, dict):
                            data['index'] = index
            else:
                # ✅ ONE QTabWidget PER PDF
                for pdf_path, pdf_info in current_pdfs.items():
                    viewer = pdf_info['viewer']
                    # Create a new QTabWidget for this single PDF
                    tab_widget = QTabWidget()
                    tab_widget.setTabsClosable(True)
                    # Use the wrapper method
                    tab_widget.tabCloseRequested.connect(self.main_window.pdf_manager.close_pdf_tab_by_signal)
                    # ✅ FIX: Connect tabBarClicked for H/V border highlighting
                    tab_widget.tabBarClicked.connect(
                        lambda idx, v=viewer: self.main_window.pdf_manager._on_hv_tab_bar_clicked(idx, v)
                    )                    
                    tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    tab_widget.setMinimumSize(200, 150)
                    # Add viewer
                    tab_name = os.path.basename(pdf_path)
                    tab_widget.addTab(viewer, tab_name)
                    # Install shortcuts on the tab widget for H/V mode
                    if hasattr(viewer, 'install_shortcuts_on_parent'):
                        viewer.install_shortcuts_on_parent(tab_widget)
                    # Store
                    if pdf_path in self.main_window.pdf_manager.pdf_files:
                        data = self.main_window.pdf_manager.pdf_files[pdf_path]
                        if isinstance(data, dict):
                            data['tab_widget'] = tab_widget
                            data['index'] = 0
                            data['tab_widget_index'] = new_pdf_widget.count()
                    # Add to splitter
                    new_pdf_widget.addWidget(tab_widget)
                # ✅ Equal sizes
                if new_pdf_widget.count() > 0:
                    equal_size = 600 // new_pdf_widget.count()
                    new_pdf_widget.setSizes([equal_size] * new_pdf_widget.count())
            # Add placeholder if no PDFs AND no tool tabs
            if not current_pdfs:
                # Check for tool tabs
                tool_tabs = ["AI Assistant", "Tools", "Accessories", "Insert Character", "TikZ Plotter", "File Comparison", "PDF Comparison", "Todo list", "Spreadsheet"]
                has_tool_tabs = False
                
                if mode == "tabbed":
                    for i in range(new_pdf_widget.count()):
                        if new_pdf_widget.tabText(i) in tool_tabs:
                            has_tool_tabs = True
                            break
                
                # Only show placeholder if no tool tabs exist
                if not has_tool_tabs:
                    if mode == "tabbed":
                        welcome_content = self._create_pdf_welcome_content()
                        new_pdf_widget.addTab(welcome_content, "PDF Viewer")
                        new_pdf_widget.setTabsClosable(False)
                    else:
                        # H/V mode placeholder
                        for i in range(2):
                            tab_widget = QTabWidget()
                            tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                            tab_widget.setMinimumSize(200, 150)
                            placeholder_label = QLabel(f"No PDF files loaded\n\nSection {i+1}")
                            placeholder_label.setAlignment(Qt.AlignCenter)
                            placeholder_label.setStyleSheet("color: #666; font-size: 14px; padding: 20px;")
                            tab_widget.addTab(placeholder_label, "No PDFs")
                            new_pdf_widget.addWidget(tab_widget)
                        new_pdf_widget.setSizes([400, 400])
                        self.main_window.pdf_manager.pdf_tabs = [new_pdf_widget.widget(0), new_pdf_widget.widget(1)]
            
            # Force visibility and update
            new_pdf_widget.show()
            new_pdf_widget.update()
            self.pdf_container.update()

            #print(f"PDF container recreation complete with {len(current_pdfs)} PDFs restored")
        except Exception as e:
            print(f"Error in _recreate_pdf_container: {e}")
            import traceback
            traceback.print_exc()
                    
    def get_layout_status(self):
        """Get current layout status for status bar"""
        layout_text = self.main_window.translations[self.main_window.menu_language]["status_layout_editor_left"]
        if self.current_layout == "pdf_left":
            layout_text = self.main_window.translations[self.main_window.menu_language]["status_layout_pdf_left"]
        
        orientation_text = self.main_window.translations[self.main_window.menu_language]["status_layout_side_by_side"]
        if self.orientation == "stacked":
            orientation_text = self.main_window.translations[self.main_window.menu_language]["status_layout_stacked"]
        
        return f"{layout_text} | {orientation_text}"
    


    def apply_editor_layout(self):
        """Apply current editor layout mode"""
        mode = self.main_window.editor_manager.editor_layout_mode
        editor_container = self.main_window.editor_manager.get_container()
        
        # Re-add based on mode
        if mode == "tabbed":
            # Editor tabs already managed by QTabWidget
            pass
        elif mode == "horizontal":
            self.main_window.editor_manager.editor_splitter.setOrientation(Qt.Horizontal)
        elif mode == "vertical":
            self.main_window.editor_manager.editor_splitter.setOrientation(Qt.Vertical)


    def apply_pdf_layout(self):
        """Apply current PDF layout mode"""
        mode = self.main_window.pdf_manager.pdf_layout_mode
        pdf_container = self.main_window.pdf_manager.get_container()
        
        # Re-add based on mode
        if mode == "tabbed":
            # PDF tabs already managed by QTabWidget
            pass
        elif mode == "horizontal":
            self.main_window.pdf_manager.pdf_splitter.setOrientation(Qt.Horizontal)
        elif mode == "vertical":
            self.main_window.pdf_manager.pdf_splitter.setOrientation(Qt.Vertical)
                
    def switch_to_side_by_side(self):
        """Switch main layout to side-by-side (horizontal)"""
        if hasattr(self.main_window, 'main_splitter'):
            self.main_window.main_splitter.setOrientation(Qt.Horizontal)

    def switch_to_stacked(self):
        """Switch main layout to stacked (vertical)"""
        if hasattr(self.main_window, 'main_splitter'):
            self.main_window.main_splitter.setOrientation(Qt.Vertical)
 
class EnhancedTabWidget(QTabWidget):
    """Enhanced tab widget with dynamic tab management"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setTabsClosable(False)  # Base tabs should not be closable
        self.setMovable(True)  # Allow tab reordering
        
        # ✅ Apply UI font to tab bar
        self.update_font()
        


    def update_font(self):
        """Update tab bar font to match interface font"""
        if hasattr(self.main_window, 'get_current_font_settings'):
            current_fonts = self.main_window.get_current_font_settings()
            ui_font_family = current_fonts.get('ui_font_family', 'Arial')
            ui_font_size = current_fonts.get('toolbar_font_size', 10)
        else:
            ui_font_family = getattr(self.main_window, 'ui_font_family', 'Arial')
            ui_font_size = getattr(self.main_window, 'toolbar_font_size', 10)

        ui_font = QFont(ui_font_family, ui_font_size)
        
        # Apply to tab bar
        self.tabBar().setFont(ui_font)
        
        # Apply to all tab contents
        for i in range(self.count()):
            widget = self.widget(i)
            if widget:
                self._apply_font_to_widget(widget, ui_font)

    def _apply_font_to_widget(self, widget, font):
        """Recursively apply font to widget and its children (excluding editors)"""
        from PyQt5.QtWidgets import QLabel, QPushButton, QTreeWidget, QTabWidget
        
        # Skip text editors
        if isinstance(widget, (QTextEdit, QPlainTextEdit)):
            return
            
        # Apply font to common widget types
        if isinstance(widget, (QLabel, QPushButton)):
            widget.setFont(font)
        elif isinstance(widget, QTreeWidget):
            widget.setFont(font)
            widget.header().setFont(font)
        elif isinstance(widget, QTabWidget):
            widget.tabBar().setFont(font)
            
        # Recursively apply to children
        for child in widget.findChildren(QWidget):
            if not isinstance(child, (QTextEdit, QPlainTextEdit)):
                if isinstance(child, (QLabel, QPushButton)):
                    child.setFont(font)
                elif isinstance(child, QTreeWidget):
                    child.setFont(font)


    def has_tab(self, label):
        """Check if a tab with the given label exists"""
        for i in range(self.count()):
            if self.tabText(i) == label:
                return True
        return False
