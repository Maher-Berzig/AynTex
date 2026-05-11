# ============================================================================
# FILE: plugins/errorbar_plugin.py
# NEW PLUGIN: Error bar plot from numerical data
# ============================================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit,
    QPushButton, QComboBox, QCheckBox
)
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class ErrorBarPlugin(PlotPlugin):
    """Plugin for creating error bar plots from numerical data"""
    
    name = "Error Bar Plot"
    version = "1.0.0"
    category = "data"
    description = "Create error bar plots from X, Y, Error data"
    requires_custom_ui = True
    
    def __init__(self):
        super().__init__()
        self.custom_ui_widget = None
        self.data_text = None
        self.parsed_data = None
        self.error_type_combo = None
    
    def get_plugin_name(self) -> str:
        return "Error Bar Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "color": {
                "type": "str",
                "default": "blue",
                "label": "Color"
            },
            "linewidth": {
                "type": "float",
                "default": 1.5,
                "label": "Line Width",
                "min": 0.5,
                "max": 5.0
            },
            "capsize": {
                "type": "float",
                "default": 4.0,
                "label": "Cap Size",
                "min": 0.0,
                "max": 10.0
            },
            "marker_size": {
                "type": "float",
                "default": 6.0,
                "label": "Marker Size",
                "min": 2.0,
                "max": 15.0
            },
            "xlabel": {
                "type": "str",
                "default": "X",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "Y",
                "label": "Y-axis Label"
            }
        }
    
    def create_custom_ui(self, parent):
        """Create custom UI for error bar data input"""
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        
        # Data input group
        data_group = QGroupBox("Paste Error Bar Data")
        data_layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Paste data with 3 or 4 columns:\n"
            "• 3 columns: X, Y, Y-error\n"
            "• 4 columns: X, Y, Y-error-minus, Y-error-plus"
        )
        instructions.setWordWrap(True)
        data_layout.addWidget(instructions)
        
        # Error type selection
        error_layout = QHBoxLayout()
        error_layout.addWidget(QLabel("Error Type:"))
        self.error_type_combo = QComboBox()
        self.error_type_combo.addItems(["Symmetric (3 col)", "Asymmetric (4 col)"])
        error_layout.addWidget(self.error_type_combo)
        error_layout.addStretch()
        data_layout.addLayout(error_layout)
        
        # Text area for data
        self.data_text = QTextEdit()
        self.data_text.setPlaceholderText(
            "Example (symmetric errors):\n"
            "1.0    2.5    0.3\n"
            "2.0    4.1    0.4\n"
            "3.0    5.8    0.2\n"
            "4.0    8.2    0.5"
        )
        self.data_text.setMinimumHeight(180)
        data_layout.addWidget(self.data_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_parse = QPushButton("Parse Data")
        btn_parse.clicked.connect(self.parse_data)
        btn_layout.addWidget(btn_parse)
        
        btn_sample = QPushButton("Load Sample")
        btn_sample.clicked.connect(self.load_sample)
        btn_layout.addWidget(btn_sample)
        
        data_layout.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel("")
        data_layout.addWidget(self.status_label)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        layout.addStretch()
        return self.custom_ui_widget
    
    def parse_data(self):
        """Parse the error bar data"""
        text = self.data_text.toPlainText().strip()
        if not text:
            self.status_label.setText("No data")
            return
        
        try:
            lines = text.strip().split('\n')
            data = []
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    row = [float(p) for p in parts[:4]]  # Take up to 4 columns
                    data.append(row)
            
            if len(data) > 0:
                self.parsed_data = data
                cols = len(data[0])
                self.status_label.setText(f"✓ Parsed {len(data)} points ({cols} columns)")
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText("✗ No valid data")
                self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            self.status_label.setText(f"✗ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
    
    def load_sample(self):
        """Load sample data"""
        sample = """1.0    2.3    0.2
2.0    4.1    0.3
3.0    5.8    0.25
4.0    8.2    0.4
5.0    10.1   0.35
6.0    12.5   0.3"""
        self.data_text.setPlainText(sample)
        self.parse_data()
    
    def get_custom_ui_data(self):
        if self.parsed_data is None:
            self.parse_data()
        return self.parsed_data
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if data is None or len(data) == 0:
            return False, "No data. Please paste and parse data."
        try:
            arr = np.array(data)
            if arr.ndim == 2 and arr.shape[1] >= 3:
                return True, ""
            return False, "Need at least 3 columns (X, Y, Error)"
        except Exception as e:
            return False, f"Invalid data: {str(e)}"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        arr = np.array(data)
        x = arr[:, 0]
        y = arr[:, 1]
        
        if arr.shape[1] >= 4:
            yerr = [arr[:, 2], arr[:, 3]]  # Asymmetric
        else:
            yerr = arr[:, 2]  # Symmetric
        
        ax.errorbar(x, y, yerr=yerr,
                   fmt='o',
                   color=options.get('color', 'blue'),
                   linewidth=options.get('linewidth', 1.5),
                   capsize=options.get('capsize', 4.0),
                   markersize=options.get('marker_size', 6.0),
                   capthick=options.get('linewidth', 1.5))
        
        ax.set_xlabel(options.get('xlabel', 'X'))
        ax.set_ylabel(options.get('ylabel', 'Y'))
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        arr = np.array(data)
        x = arr[:, 0]
        y = arr[:, 1]
        
        if arr.shape[1] >= 4:
            err_minus = arr[:, 2]
            err_plus = arr[:, 3]
        else:
            err_minus = arr[:, 2]
            err_plus = arr[:, 2]
        
        # Generate coordinates with error bars
        coords = []
        for i in range(len(x)):
            coords.append(f"        ({x[i]:.6f},{y[i]:.6f}) +- (0,{err_minus[i]:.6f})")
        
        coords_str = "\n".join(coords)
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    xlabel={{{options.get('xlabel', 'X')}}},
    ylabel={{{options.get('ylabel', 'Y')}}},
    grid=major,
    width=12cm,
    height=8cm
]
\\addplot[
    color={options.get('color', 'blue')},
    mark=*,
    mark size={options.get('marker_size', 6.0)/2}pt,
    error bars/.cd,
    y dir=both,
    y explicit
] coordinates {{
{coords_str}
}};
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code
