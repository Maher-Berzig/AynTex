# ============================================================================
# FILE: tikz_plotter_tab.py - OPTIMIZED WITH LAZY LOADING
# ============================================================================
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QLabel, QPushButton, QTextEdit,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QSplitter, QGroupBox, QScrollArea, QMessageBox,
    QApplication, QFrame, QSizePolicy, QFileDialog,
    QSlider, QButtonGroup, QRadioButton, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextOption, QFontMetrics, QColor, QBrush, QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
import os
import importlib.util
import inspect
import time

# ============================================================================
# Plugin Interface (unchanged)
# ============================================================================
class PlotPlugin(ABC):
    """Abstract base class for all plot plugins"""
    name: str = "Unnamed Plugin"
    version: str = "1.0.0"
    category: str = "general"
    description: str = ""
    requires_custom_ui: bool = False

    @abstractmethod
    def get_plugin_name(self) -> str:
        pass

    @abstractmethod
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def plot(self, data: Any, options: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        pass

    def get_tikz_libraries(self) -> List[str]:
        return ["pgfplots"]

    def create_custom_ui(self, parent) -> Any:
        return None

    def get_custom_ui_data(self) -> Any:
        return None


# ============================================================================
# Lazy Plugin Manager - Only loads plugins when needed
# ============================================================================
@dataclass
class PluginInfo:
    """Lightweight plugin metadata - loaded without instantiating the plugin"""
    name: str
    category: str
    description: str
    filepath: str
    class_name: str
    module_name: str
    requires_custom_ui: bool = False
    _instance: Optional[PlotPlugin] = field(default=None, repr=False)


class LazyPluginManager:
    """
    Plugin manager with lazy loading.
    Only loads plugin metadata at startup, instantiates plugins on demand.
    """
    
    def __init__(self, plugin_directories: List[str] = None):
        self.plugin_directories = plugin_directories or []
        self.plugin_registry: Dict[str, PluginInfo] = {}  # name -> PluginInfo
        self._load_order: List[str] = []  # Preserve discovery order
        self._module_cache: Dict[str, Any] = {}  # Cache loaded modules
    
    def discover_plugins(self):
        """
        Quickly scan plugin files and extract metadata WITHOUT instantiating.
        This is much faster than loading all plugins.
        """
        start_time = time.time()
        
        for directory in self.plugin_directories:
            if not os.path.exists(directory):
                continue
            
            for filename in os.listdir(directory):
                if filename.endswith('_plugin.py') and not filename.startswith('__'):
                    filepath = os.path.join(directory, filename)
                    self._extract_plugin_metadata(filepath)
        
        elapsed = time.time() - start_time
        #print(f"✅ Discovered {len(self.plugin_registry)} plugins in {elapsed:.3f}s")
    
    def _extract_plugin_metadata(self, filepath: str):
        """Extract plugin metadata by quick parsing, without full import"""
        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            
            # Quick parse to find plugin class info
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Look for class definitions that inherit from PlotPlugin
            import re
            class_pattern = r'class\s+(\w+)\s*\(\s*PlotPlugin\s*\)'
            matches = re.findall(class_pattern, content)
            
            for class_name in matches:
                # Try to extract metadata from class attributes
                name = self._extract_attribute(content, class_name, 'name', module_name)
                category = self._extract_attribute(content, class_name, 'category', 'general')
                description = self._extract_attribute(content, class_name, 'description', '')
                requires_custom_ui = 'requires_custom_ui = True' in content
                
                # Clean up the name
                if name == module_name:
                    # Generate a readable name from class name
                    name = class_name.replace('Plugin', '').replace('Plot', ' Plot')
                    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).strip()
                
                if name not in self.plugin_registry:
                    info = PluginInfo(
                        name=name,
                        category=category,
                        description=description,
                        filepath=filepath,
                        class_name=class_name,
                        module_name=module_name,
                        requires_custom_ui=requires_custom_ui
                    )
                    self.plugin_registry[name] = info
                    self._load_order.append(name)
                    
        except Exception as e:
            print(f"Warning: Could not parse {filepath}: {e}")
    
    def _extract_attribute(self, content: str, class_name: str, attr: str, default: str) -> str:
        """Extract a class attribute value from source code"""
        import re
        # Look for patterns like: name = "Something" or name: str = "Something"
        patterns = [
            rf'{attr}\s*[=:]\s*["\']([^"\']+)["\']',
            rf'{attr}\s*=\s*["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        return default
    
    def get_plugin(self, name: str) -> Optional[PlotPlugin]:
        """Get a plugin instance, loading it if necessary (lazy load)"""
        if name not in self.plugin_registry:
            return None
        
        info = self.plugin_registry[name]
        
        # Return cached instance if already loaded
        if info._instance is not None:
            return info._instance
        
        # Load the plugin now
        start_time = time.time()
        instance = self._load_plugin_instance(info)
        elapsed = time.time() - start_time
        
        if instance:
            info._instance = instance
            #print(f"  Loaded plugin '{name}' in {elapsed:.3f}s")
        
        return instance
    
    def _load_plugin_instance(self, info: PluginInfo) -> Optional[PlotPlugin]:
        """Actually load and instantiate a plugin"""
        try:
            # Check module cache first
            if info.module_name in self._module_cache:
                module = self._module_cache[info.module_name]
            else:
                # Load the module
                spec = importlib.util.spec_from_file_location(info.module_name, info.filepath)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self._module_cache[info.module_name] = module
                else:
                    return None
            
            # Get the plugin class and instantiate
            if hasattr(module, info.class_name):
                plugin_class = getattr(module, info.class_name)
                instance = plugin_class()
                return instance
                
        except Exception as e:
            print(f"Error loading plugin {info.name}: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def get_plugin_names(self) -> List[str]:
        """Get list of all discovered plugin names"""
        return sorted(self._load_order)
    
    def get_plugins_by_category(self) -> Dict[str, List[str]]:
        """Get plugins organized by category"""
        categories = {}
        for name, info in self.plugin_registry.items():
            cat = info.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(name)
        return categories
    
    def preload_plugin(self, name: str):
        """Preload a specific plugin (can be called from background)"""
        self.get_plugin(name)
    
    def is_plugin_loaded(self, name: str) -> bool:
        """Check if a plugin is already loaded"""
        if name in self.plugin_registry:
            return self.plugin_registry[name]._instance is not None
        return False


# ============================================================================
# Background Plugin Loader Thread
# ============================================================================
class PluginPreloader(QThread):
    """Background thread to preload plugins after UI is shown"""
    plugin_loaded = pyqtSignal(str)  # Emits plugin name when loaded
    finished_loading = pyqtSignal()
    
    def __init__(self, plugin_manager: LazyPluginManager, priority_plugins: List[str] = None):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.priority_plugins = priority_plugins or []
        self._stop_requested = False
    
    def run(self):
        """Load plugins in background, priority plugins first"""
        # Load priority plugins first
        for name in self.priority_plugins:
            if self._stop_requested:
                return
            if not self.plugin_manager.is_plugin_loaded(name):
                self.plugin_manager.preload_plugin(name)
                self.plugin_loaded.emit(name)
        
        # Then load remaining plugins
        for name in self.plugin_manager.get_plugin_names():
            if self._stop_requested:
                return
            if not self.plugin_manager.is_plugin_loaded(name):
                self.plugin_manager.preload_plugin(name)
                self.plugin_loaded.emit(name)
        
        self.finished_loading.emit()
    
    def stop(self):
        self._stop_requested = True


# ============================================================================
# Plot Control Widget (unchanged from before)
# ============================================================================
class PlotControlWidget(QWidget):
    """Widget with zoom and rotation controls for the plot preview"""
    
    def __init__(self, canvas, figure, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.figure = figure
        self.current_azimuth = 45
        self.current_elevation = 30
        self.rotation_axis = 'z'
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self._auto_rotate_step)
        self.rotation_speed = 2
        self.is_3d = False
        self.parent_scroll_area = None
        self.original_canvas_size = None
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Zoom controls
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QHBoxLayout(zoom_group)
        zoom_layout.setContentsMargins(5, 5, 5, 5)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)
        
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)
        
        self.btn_zoom_reset = QPushButton("Reset")
        self.btn_zoom_reset.clicked.connect(self.zoom_reset)
        zoom_layout.addWidget(self.btn_zoom_reset)
        
        self.btn_fit = QPushButton("Fit")
        self.btn_fit.clicked.connect(self.fit_to_window)
        zoom_layout.addWidget(self.btn_fit)
        
        layout.addWidget(zoom_group)
        
        # 3D rotation controls
        self.rotation_group = QGroupBox("3D Rotation")
        rotation_layout = QVBoxLayout(self.rotation_group)
        rotation_layout.setContentsMargins(5, 5, 5, 5)
        
        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel("Axis:"))
        
        self.axis_group = QButtonGroup(self)
        self.rb_axis_x = QRadioButton("X")
        self.rb_axis_y = QRadioButton("Y")
        self.rb_axis_z = QRadioButton("Z")
        self.rb_axis_z.setChecked(True)
        
        for rb in [self.rb_axis_x, self.rb_axis_y, self.rb_axis_z]:
            self.axis_group.addButton(rb)
            axis_layout.addWidget(rb)
        
        self.rb_axis_x.toggled.connect(lambda: self.set_rotation_axis('x'))
        self.rb_axis_y.toggled.connect(lambda: self.set_rotation_axis('y'))
        self.rb_axis_z.toggled.connect(lambda: self.set_rotation_axis('z'))
        
        rotation_layout.addLayout(axis_layout)
        
        rotate_btn_layout = QHBoxLayout()
        self.btn_rotate_left = QPushButton("◀")
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_view(-15))
        rotate_btn_layout.addWidget(self.btn_rotate_left)
        
        self.btn_rotate_right = QPushButton("▶")
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_view(15))
        rotate_btn_layout.addWidget(self.btn_rotate_right)
        
        self.btn_auto_rotate = QPushButton("Auto")
        self.btn_auto_rotate.setCheckable(True)
        self.btn_auto_rotate.clicked.connect(self.toggle_auto_rotate)
        rotate_btn_layout.addWidget(self.btn_auto_rotate)
        
        rotation_layout.addLayout(rotate_btn_layout)
        layout.addWidget(self.rotation_group)
        
        layout.addStretch()
        self.rotation_group.setVisible(False)
    
    def set_scroll_area(self, scroll_area):
        self.parent_scroll_area = scroll_area
    
    def update_figure(self, figure):
        self.figure = figure
        self.check_3d_axes()
        if self.original_canvas_size is None:
            self.original_canvas_size = self.canvas.size()
    
    def check_3d_axes(self):
        self.is_3d = False
        if self.figure:
            for ax in self.figure.axes:
                if hasattr(ax, 'get_zlim'):
                    self.is_3d = True
                    break
        self.rotation_group.setVisible(self.is_3d)
    
    def set_rotation_axis(self, axis):
        self.rotation_axis = axis
    
    def zoom_in(self):
        if self.figure:
            for ax in self.figure.axes:
                if hasattr(ax, 'get_xlim'):
                    xlim, ylim = ax.get_xlim(), ax.get_ylim()
                    xc, yc = (xlim[0]+xlim[1])/2, (ylim[0]+ylim[1])/2
                    xr, yr = (xlim[1]-xlim[0])*0.4, (ylim[1]-ylim[0])*0.4
                    ax.set_xlim(xc-xr, xc+xr)
                    ax.set_ylim(yc-yr, yc+yr)
            self.canvas.draw()
    
    def zoom_out(self):
        if self.figure:
            for ax in self.figure.axes:
                if hasattr(ax, 'get_xlim'):
                    xlim, ylim = ax.get_xlim(), ax.get_ylim()
                    xc, yc = (xlim[0]+xlim[1])/2, (ylim[0]+ylim[1])/2
                    xr, yr = (xlim[1]-xlim[0])*0.6, (ylim[1]-ylim[0])*0.6
                    ax.set_xlim(xc-xr, xc+xr)
                    ax.set_ylim(yc-yr, yc+yr)
            self.canvas.draw()
    
    def zoom_reset(self):
        if self.figure:
            for ax in self.figure.axes:
                ax.autoscale()
            self.canvas.draw()
        if self.original_canvas_size:
            self.canvas.setMinimumSize(self.original_canvas_size)
            self.canvas.resize(self.original_canvas_size)
    
    def fit_to_window(self):
        if self.parent_scroll_area:
            viewport_size = self.parent_scroll_area.viewport().size()
            available_width = max(300, viewport_size.width() - 20)
            available_height = max(200, viewport_size.height() - 20)
            
            from PyQt5.QtCore import QSize
            new_size = QSize(available_width, available_height)
            self.canvas.setMinimumSize(new_size)
            self.canvas.resize(new_size)
            
            if self.figure:
                dpi = self.figure.get_dpi()
                self.figure.set_size_inches(available_width / dpi, available_height / dpi)
                self.canvas.draw()
    
    def rotate_view(self, delta):
        if not self.is_3d or not self.figure:
            return
        for ax in self.figure.axes:
            if hasattr(ax, 'view_init'):
                if self.rotation_axis == 'z':
                    self.current_azimuth = (self.current_azimuth + delta) % 360
                elif self.rotation_axis == 'x':
                    self.current_elevation = max(0, min(90, self.current_elevation + delta))
                else:
                    self.current_azimuth = (self.current_azimuth + delta) % 360
                ax.view_init(elev=self.current_elevation, azim=self.current_azimuth)
        self.canvas.draw()
    
    def toggle_auto_rotate(self, checked):
        if checked:
            self.rotation_timer.start(50)
        else:
            self.rotation_timer.stop()
    
    def _auto_rotate_step(self):
        self.rotate_view(self.rotation_speed)
    
    def stop_auto_rotate(self):
        self.rotation_timer.stop()
        if hasattr(self, 'btn_auto_rotate'):
            self.btn_auto_rotate.setChecked(False)


# ============================================================================
# TikZ Plotter Tab - Optimized with Lazy Loading
# ============================================================================
class TikZPlotterTab(QWidget):
    """TikZ Plotter with lazy plugin loading for fast startup"""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.plugin_manager = None
        self.current_plugin = None
        self.option_widgets = {}
        self.plot_controls = None
        self.default_left_panel = None
        self.custom_left_panel = None
        self.preloader_thread = None
        self._loading_plugin = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI with lazy-loaded plugin system"""
        #start_time = time.time()
        
        # Initialize lazy plugin manager
        self.plugin_manager = LazyPluginManager(['plugins'])
        self.plugin_manager.discover_plugins()  # Fast metadata scan
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Global scroll area
        global_scroll = QScrollArea()
        global_scroll.setWidgetResizable(True)
        global_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        global_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        global_scroll.setFrameShape(QFrame.NoFrame)
        
        global_content = QWidget()
        global_content_layout = QVBoxLayout(global_content)
        global_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter for left/right panels
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Left panel
        self.left_panel_container = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel_container)
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.default_left_panel = self.create_left_panel()
        self.left_panel_layout.addWidget(self.default_left_panel)
        splitter.addWidget(self.left_panel_container)
        
        # Right panel
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 600])
        splitter.setMinimumHeight(700)
        
        global_content_layout.addWidget(splitter)
        global_scroll.setWidget(global_content)
        main_layout.addWidget(global_scroll)
        
        #elapsed = time.time() - start_time
        #print(f"✅ TikZ Plotter UI created in {elapsed:.3f}s")
        
        # Load initial plugin NOW, before the window is ever shown
        if self.plugin_combo.count() > 0:
            self.on_plugin_changed(self.plugin_combo.currentText())
        
        # Start background preloading after UI is shown
        QTimer.singleShot(100, self.start_background_preload)
    
    def start_background_preload(self):
        """Start preloading plugins in background"""
        # Get the first selected plugin name for priority loading
        first_plugin = self.plugin_combo.currentText() if self.plugin_combo.count() > 0 else None
        priority = [first_plugin] if first_plugin else []
        
        self.preloader_thread = PluginPreloader(self.plugin_manager, priority)
        self.preloader_thread.plugin_loaded.connect(self.on_plugin_preloaded)
        self.preloader_thread.finished_loading.connect(self.on_preload_finished)
        self.preloader_thread.start()
    
    def on_plugin_preloaded(self, name: str):
        """Called when a plugin is preloaded in background"""
        # Update UI if needed
        pass
    
    def on_preload_finished(self):
        """Called when all plugins are preloaded"""
        #print("✅ All plugins preloaded")
        pass
    
    def closeEvent(self, event):
        """Clean up background thread on close"""
        if self.preloader_thread and self.preloader_thread.isRunning():
            self.preloader_thread.stop()
            self.preloader_thread.wait(1000)
        super().closeEvent(event)
    
    def create_left_panel(self):
        """Create left control panel"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        
        # Plugin selector
        plugin_group = QGroupBox("Select Plugin")
        plugin_layout = QVBoxLayout()
        
        self.plugin_combo = QComboBox()
        plugin_names = self.plugin_manager.get_plugin_names()
        self.plugin_combo.addItems(plugin_names)
        self.plugin_combo.currentTextChanged.connect(self.on_plugin_changed)
        plugin_layout.addWidget(self.plugin_combo)
        
        # Loading indicator
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #2196F3; font-style: italic;")
        plugin_layout.addWidget(self.loading_label)
        
        plugin_group.setLayout(plugin_layout)
        main_layout.addWidget(plugin_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.btn_plot = QPushButton("Generate Preview")
        self.btn_plot.setMinimumHeight(35)
        self.btn_plot.clicked.connect(self.generate_plot)
        btn_layout.addWidget(self.btn_plot)
        
        self.btn_export = QPushButton("Export")
        self.btn_export.setMinimumHeight(35)
        self.btn_export.clicked.connect(self.export_preview)
        btn_layout.addWidget(self.btn_export)
        
        self.btn_tikz = QPushButton("Insert TikZ")
        self.btn_tikz.setMinimumHeight(35)
        self.btn_tikz.clicked.connect(self.insert_tikz_to_editor)
        #self.btn_tikz.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_tikz)
        
        main_layout.addLayout(btn_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Scrollable content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 5, 0)
        
        # Data input
        self.data_group = QGroupBox("Data Input")
        data_layout = QVBoxLayout()
        data_layout.addWidget(QLabel("JSON format: [1,2,3] or [[x,y],...]"))
        
        self.data_input = QTextEdit()
        self.data_input.setMinimumHeight(80)
        self.data_input.setMaximumHeight(120)
        self.data_input.setPlainText("[1, 2, 3, 4, 5, 4, 3, 2, 1]")
        data_layout.addWidget(self.data_input)
        
        quick_layout = QHBoxLayout()
        btn_s1 = QPushButton("Sample 1D")
        btn_s1.clicked.connect(lambda: self.load_sample_data("1d"))
        btn_s2 = QPushButton("Sample 2D")
        btn_s2.clicked.connect(lambda: self.load_sample_data("2d"))
        quick_layout.addWidget(btn_s1)
        quick_layout.addWidget(btn_s2)
        data_layout.addLayout(quick_layout)
        
        self.data_group.setLayout(data_layout)
        self.scroll_layout.addWidget(self.data_group)
        
        # Options
        self.options_group = QGroupBox("Plugin Options")
        self.options_layout = QVBoxLayout()
        self.options_group.setLayout(self.options_layout)
        self.scroll_layout.addWidget(self.options_group)
        
        self.scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)
        
        return panel
    
    def create_right_panel(self):
        """Create right preview panel"""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(5, 5, 5, 5)
        panel_layout.setSpacing(5)
        
        title_label = QLabel("<b>Preview</b>")
        panel_layout.addWidget(title_label)
        
        # Canvas scroll area
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(False)
        self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.canvas_scroll.setMinimumHeight(350)
        
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(600, 450)
        canvas_layout.addWidget(self.canvas)
        
        self.canvas_scroll.setWidget(canvas_container)
        panel_layout.addWidget(self.canvas_scroll, 1)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        panel_layout.addWidget(separator)
        
        # Plot controls
        self.plot_controls = PlotControlWidget(self.canvas, self.figure, self)
        self.plot_controls.setMinimumHeight(80)
        self.plot_controls.setMaximumHeight(150)
        self.plot_controls.set_scroll_area(self.canvas_scroll)
        panel_layout.addWidget(self.plot_controls)
        
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel.setMinimumHeight(500)
        
        return panel
    
    def on_plugin_changed(self, plugin_name: str):
        """Handle plugin change - loads plugin lazily"""
        if self._loading_plugin:
            return
        
        self._loading_plugin = True
        self.loading_label.setText("Loading plugin...")
        QApplication.processEvents()
        
        try:
            # Lazy load the plugin
            new_plugin = self.plugin_manager.get_plugin(plugin_name)
            
            if new_plugin is None:
                self.loading_label.setText(f"Failed to load {plugin_name}")
                self._loading_plugin = False
                return
            
            self.current_plugin = new_plugin
            self.loading_label.setText("")
            
            if self.current_plugin.requires_custom_ui:
                self.switch_to_custom_ui()
            else:
                self.switch_to_default_ui()
                self.rebuild_options_panel()
                
        except Exception as e:
            self.loading_label.setText(f"Error: {e}")
            print(f"Error loading plugin: {e}")
        finally:
            self._loading_plugin = False
    
    def switch_to_custom_ui(self):
        """Switch to custom plugin UI"""
        if self.default_left_panel:
            self.default_left_panel.hide()
        
        if self.custom_left_panel:
            self.custom_left_panel.setParent(None)
            self.custom_left_panel.deleteLater()
            self.custom_left_panel = None
        
        custom_widget = QWidget()
        custom_layout = QVBoxLayout(custom_widget)
        custom_layout.setContentsMargins(5, 5, 5, 5)
        
        # Plugin selector
        plugin_group = QGroupBox("Select Plugin")
        plugin_layout = QVBoxLayout()
        self.custom_plugin_combo = QComboBox()
        self.custom_plugin_combo.addItems(self.plugin_manager.get_plugin_names())
        self.custom_plugin_combo.setCurrentText(self.current_plugin.get_plugin_name())
        self.custom_plugin_combo.currentTextChanged.connect(self.on_plugin_changed)
        plugin_layout.addWidget(self.custom_plugin_combo)
        plugin_group.setLayout(plugin_layout)
        custom_layout.addWidget(plugin_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_plot = QPushButton("Generate Preview")
        btn_plot.setMinimumHeight(35)
        btn_plot.clicked.connect(self.generate_plot)
        btn_layout.addWidget(btn_plot)
        
        btn_export = QPushButton("Export")
        btn_export.setMinimumHeight(35)
        btn_export.clicked.connect(self.export_preview)
        btn_layout.addWidget(btn_export)
        
        btn_tikz = QPushButton("Insert TikZ")
        btn_tikz.setMinimumHeight(35)
        btn_tikz.clicked.connect(self.insert_tikz_to_editor)
        #btn_tikz.setStyleSheet("background: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(btn_tikz)
        custom_layout.addLayout(btn_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        custom_layout.addWidget(separator)
        
        # Custom UI scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        plugin_ui = self.current_plugin.create_custom_ui(scroll_content)
        if plugin_ui:
            scroll_layout.addWidget(plugin_ui)
        
        # Options
        options_group = QGroupBox("Display Options")
        options_layout = QVBoxLayout()
        self.option_widgets.clear()
        
        options = self.current_plugin.get_user_options()
        for name, info in options.items():
            label = QLabel(info.get('label', name))
            options_layout.addWidget(label)
            
            opt_type = info.get('type', 'str')
            default = info.get('default')
            
            if opt_type == 'int':
                widget = QSpinBox()
                widget.setRange(info.get('min', 0), info.get('max', 1000))
                widget.setValue(default)
            elif opt_type == 'float':
                widget = QDoubleSpinBox()
                widget.setRange(info.get('min', 0.0), info.get('max', 100.0))
                widget.setValue(default)
                widget.setSingleStep(0.1)
            elif opt_type == 'bool':
                widget = QCheckBox()
                widget.setChecked(default)
            else:
                widget = QLineEdit()
                widget.setText(str(default))
            
            options_layout.addWidget(widget)
            self.option_widgets[name] = widget
        
        options_group.setLayout(options_layout)
        scroll_layout.addWidget(options_group)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        custom_layout.addWidget(scroll_area, 1)
        
        self.custom_left_panel = custom_widget
        self.left_panel_layout.addWidget(self.custom_left_panel)
    
    def switch_to_default_ui(self):
        """Switch to default UI"""
        if self.custom_left_panel:
            self.custom_left_panel.setParent(None)
            self.custom_left_panel.deleteLater()
            self.custom_left_panel = None
        
        if self.default_left_panel:
            self.default_left_panel.show()
            self.plugin_combo.blockSignals(True)
            self.plugin_combo.setCurrentText(self.current_plugin.get_plugin_name())
            self.plugin_combo.blockSignals(False)
    
    def rebuild_options_panel(self):
        """Rebuild options panel for current plugin"""
        if hasattr(self, 'data_group'):
            self.data_group.show()
        
        while self.options_layout.count():
            child = self.options_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.option_widgets.clear()
        
        if not self.current_plugin:
            return
        
        options = self.current_plugin.get_user_options()
        for name, info in options.items():
            label = QLabel(info.get('label', name))
            self.options_layout.addWidget(label)
            
            opt_type = info.get('type', 'str')
            default = info.get('default')
            
            if opt_type == 'int':
                widget = QSpinBox()
                widget.setRange(info.get('min', 0), info.get('max', 1000))
                widget.setValue(default)
            elif opt_type == 'float':
                widget = QDoubleSpinBox()
                widget.setRange(info.get('min', 0.0), info.get('max', 100.0))
                widget.setValue(default)
                widget.setSingleStep(0.1)
            elif opt_type == 'bool':
                widget = QCheckBox()
                widget.setChecked(default)
            else:
                widget = QLineEdit()
                widget.setText(str(default))
            
            self.options_layout.addWidget(widget)
            self.option_widgets[name] = widget
        
        self.options_layout.addStretch()
    
    def get_current_options(self):
        """Get current options values"""
        options = {}
        for name, widget in self.option_widgets.items():
            if isinstance(widget, QSpinBox):
                options[name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                options[name] = widget.value()
            elif isinstance(widget, QCheckBox):
                options[name] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                options[name] = widget.text()
        return options
    
    def get_data(self):
        """Get data from UI or plugin"""
        if self.current_plugin and self.current_plugin.requires_custom_ui:
            return self.current_plugin.get_custom_ui_data()
        try:
            return json.loads(self.data_input.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Invalid JSON: {e}")
            return None
    
    def load_sample_data(self, data_type):
        """Load sample data"""
        import random
        plugin_name = self.current_plugin.get_plugin_name() if self.current_plugin else ""
        
        if plugin_name == "Pie Chart":
            data = {"Apples": 30, "Bananas": 15, "Cherries": 25, "Dates": 10}
        elif plugin_name == "Bar Plot":
            data = {"Q1": 45, "Q2": 62, "Q3": 58, "Q4": 71}
        elif data_type == "2d":
            data = [[i, random.uniform(0, 10) + i*0.5] for i in range(15)]
        else:
            data = [1, 4, 2, 8, 5, 7, 3, 9, 6]
        
        self.data_input.setPlainText(json.dumps(data, indent=2))
    
    def generate_plot(self):
        """Generate plot preview"""
        if not self.current_plugin:
            QMessageBox.warning(self, "Error",
                "Plugin not yet loaded. Please select a plugin from the list.")
            return        
        if not self.current_plugin:
            # Try to load the first plugin
            if self.plugin_combo.count() > 0:
                self.on_plugin_changed(self.plugin_combo.currentText())
            if not self.current_plugin:
                QMessageBox.warning(self, "Error", "No plugin loaded")
                return
        
        if self.plot_controls:
            self.plot_controls.stop_auto_rotate()
        
        data = self.get_data()
        if data is None:
            return
        
        valid, msg = self.current_plugin.validate_data(data)
        if not valid:
            QMessageBox.warning(self, "Validation Error", msg)
            return
        
        try:
            options = self.get_current_options()
            self.figure.clear()
            fig = self.current_plugin.plot(data, options)
            self.figure = fig
            self.canvas.figure = fig
            self.canvas.draw()
            
            if self.plot_controls:
                self.plot_controls.update_figure(fig)
            
            # Enable interactive node dragging for Graph Drawing plugin
            if hasattr(self.current_plugin, 'setup_interactive'):
                self.current_plugin.setup_interactive(self.canvas)
                
        except Exception as e:
            QMessageBox.critical(self, "Plot Error", str(e))
            import traceback
            traceback.print_exc()
    
    def export_preview(self):
        """Export preview as image"""
        if not self.figure or not self.figure.axes:
            QMessageBox.warning(self, "Export Error", "No plot to export.")
            return
        
        if self.plot_controls:
            self.plot_controls.stop_auto_rotate()
        
        file_filter = "PNG (*.png);;JPEG (*.jpg);;SVG (*.svg);;PDF (*.pdf)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Preview", "plot", file_filter)
        
        if file_path:
            try:
                if not any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.svg', '.pdf']):
                    file_path += '.png'
                self.figure.savefig(file_path, dpi=150, bbox_inches='tight', facecolor='white')
                QMessageBox.information(self, "Export Successful", f"Saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
    
    def insert_tikz_to_editor(self):
        """Insert TikZ code at cursor in active editor"""
        if not self.current_plugin:
            QMessageBox.warning(self, "Error", "No plugin selected")
            return
        
        data = self.get_data()
        if data is None:
            return
        
        valid, msg = self.current_plugin.validate_data(data)
        if not valid:
            QMessageBox.warning(self, "Validation Error", msg)
            return
        
        try:
            options = self.get_current_options()
            tikz_code = self.current_plugin.generate_tikz(data, options)
            libraries = self.current_plugin.get_tikz_libraries()
            
            # Separate packages from TikZ libraries
            packages = []
            tikz_libs = []
            needs_pgfplots = False
            
            # Known TikZ libraries
            known_tikz_libs = {
                "arrows.meta", "arrows", "calc", "positioning", "shapes",
                "shapes.geometric", "patterns", "decorations",
                "decorations.pathreplacing", "decorations.markings",
                "plotmarks", "backgrounds", "fit", "matrix", "trees",
                "chains", "scopes", "shadows", "automata", "petri",
                "topaths", "graphs", "graphdrawing", "intersections",
                "through", "3d", "perspective", "angles", "quotes",
                "babel", "folding", "shadings", "fadings", "spy",
                "calendar", "er", "circuits", "circuits.logic",
                "circuits.logic.US", "circuits.logic.IEC", "circuits.ee",
                "circuits.ee.IEC", "datavisualization", "lindenmayersystems",
                "turtle", "plothandlers", "curvilinear", "fixedpointarithmetic",
                "svg.path", "external", "fpu", "math"
            }
            
            for lib in libraries:
                if lib == "tikz":
                    continue
                elif lib == "pgfplots":
                    needs_pgfplots = True
                elif lib in known_tikz_libs:
                    tikz_libs.append(lib)
                else:
                    packages.append(lib)
            
            # Build preamble comment
            preamble_lines = ["% Required packages and libraries:"]
            preamble_lines.append("% \\usepackage{tikz}")
            
            if tikz_libs:
                libs_str = ", ".join(tikz_libs)
                preamble_lines.append(f"% \\usetikzlibrary{{{libs_str}}}")
            
            if needs_pgfplots:
                preamble_lines.append("% \\usepackage{pgfplots}")
                preamble_lines.append("% \\pgfplotsset{compat=1.18}")
            
            for pkg in packages:
                preamble_lines.append(f"% \\usepackage{{{pkg}}}")
            
            preamble_comment = "\n".join(preamble_lines) + "\n\n"
            
            # Insert into editor
            if hasattr(self.main_window, 'editor_manager'):
                active_editor = self.main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    cursor.insertText(preamble_comment + tikz_code + "\n")
                    active_editor.setFocus()
                    self.main_window.editor_manager.on_text_changed()
                    
                    # Build success message
                    msg = "TikZ code inserted!\n\nAdd to your preamble:\n"
                    msg += "\\usepackage{tikz}\n"
                    if tikz_libs:
                        msg += f"\\usetikzlibrary{{{', '.join(tikz_libs)}}}\n"
                    if needs_pgfplots:
                        msg += "\\usepackage{pgfplots}\n"
                        msg += "\\pgfplotsset{compat=1.18}\n"
                    for pkg in packages:
                        msg += f"\\usepackage{{{pkg}}}\n"
                    
                    QMessageBox.information(self, "TikZ Inserted", msg)
                    print("✅ TikZ code inserted")
                else:
                    QMessageBox.warning(self, "Warning", "No active editor!")
            else:
                QMessageBox.warning(self, "Warning", "Editor manager not available!")
                
        except Exception as e:
            QMessageBox.critical(self, "TikZ Error", str(e))
            import traceback
            traceback.print_exc()


# ============================================================================
# Helper function to add TikZ Plotter tab
# ============================================================================
def add_tikz_plotter_tab_to_pdf_viewer(main_window):
    """Add TikZ Plotter tab to PDF viewer"""
    lang = main_window.menu_language
    translations = main_window.translations
    tr = translations[lang]          
    try:
        #print("🔧 add_tikz_plotter_tab_to_pdf_viewer called")
        
        if not hasattr(main_window, 'pdf_manager'):
            QMessageBox.warning(main_window, "Warning", "PDF manager not available!")
            return
        
        if not hasattr(main_window, 'layout_manager'):
            QMessageBox.warning(main_window, "Warning", "Layout manager not available!")
            return
        
        layout_manager = main_window.layout_manager
        pdf_manager = main_window.pdf_manager
        
        if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
            layout_manager._recreate_pdf_container()
        
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info",
                "TikZ Plotter requires tabbed mode. Switch to tabbed mode first.")
            return
        
        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
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
                        item.widget().deleteLater()
                pdf_layout.addWidget(pdf_manager.pdf_tabs)
        
        tab_widget = pdf_manager.pdf_tabs
        if tab_widget is None:
            QMessageBox.critical(main_window, "Error", "Could not initialize PDF tabs")
            return
        
        # Remove placeholder tabs
        for i in reversed(range(tab_widget.count())):
            if tab_widget.tabText(i) in ["Welcome", "No Pdfs", "No PDFs"]:
                tab_widget.removeTab(i)
        
        # Check if already exists
        possible_labels = {
            tr["tikz_plotter"] for tr in translations.values()
        }                        
            
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                tab_widget.setCurrentIndex(i)
                #print(f"✅ Switched to existing TikZ Plotter tab")
                return
        
        # Create new tab
        tikz_tab = TikZPlotterTab(main_window)
        
        if not hasattr(main_window, '_tikz_plotter_tabs'):
            main_window._tikz_plotter_tabs = []
        main_window._tikz_plotter_tabs.append(tikz_tab)

        tab_name = tr.get("tikz_plotter", "TikZ Plotter")
        tab_index = tab_widget.addTab(tikz_tab, tab_name)                                    
        tab_widget.tabBar().setTabData(tab_index, "tikz_plotter")    
        
        # ✅ Set SVG icon properly
        icon = QIcon("icons/tikz.svg")
        tab_widget.setTabIcon(tab_index, icon)        
        
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)
        
        tab_widget.show()
        tab_widget.setVisible(True)
        tikz_tab.show()
        
        #print(f"✅ TikZ Plotter tab added at index {tab_index}")
        
    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add TikZ Plotter tab:\n{str(e)}")
        import traceback
        traceback.print_exc()