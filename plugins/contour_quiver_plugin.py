# ============================================================================
# FILE: plugins/contour_quiver_plugin.py - NEW PLUGIN
# ============================================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QDoubleSpinBox, QPushButton, QComboBox, QCheckBox
)
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class ContourQuiverPlugin(PlotPlugin):
    """Contour plot with gradient/quiver arrows"""
    
    name = "Contour + Gradient"
    version = "1.0.0"
    category = "3d"
    description = "Create contour plots with gradient vector field"
    requires_custom_ui = True
    
    def __init__(self):
        super().__init__()
        self._reset_state()
        
        self.function_presets = {
            "Gaussian Gradient": {
                "f": "np.exp(-x**2 - y**2) * x",
                "u": "np.exp(-x**2 - y**2) * (1 - 2*x**2)",
                "v": "np.exp(-x**2 - y**2) * (-2*x*y)"
            },
            "Circular": {
                "f": "np.sqrt(x**2 + y**2)",
                "u": "x / (np.sqrt(x**2 + y**2) + 0.01)",
                "v": "y / (np.sqrt(x**2 + y**2) + 0.01)"
            },
            "Saddle": {
                "f": "x**2 - y**2",
                "u": "2*x",
                "v": "-2*y"
            },
            "Vortex": {
                "f": "np.arctan2(y, x)",
                "u": "-y / (x**2 + y**2 + 0.01)",
                "v": "x / (x**2 + y**2 + 0.01)"
            },
        }
    
    def _reset_state(self):
        """Reset state variables"""
        self.custom_ui_widget = None
        self.func_f = None
        self.func_u = None
        self.func_v = None
        self.x_min = None
        self.x_max = None
        self.show_quiver = None
    
    def get_plugin_name(self) -> str:
        return "Contour + Gradient"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "contour_levels": {
                "type": "int",
                "default": 9,
                "label": "Contour Levels",
                "min": 3,
                "max": 30
            },
            "arrow_samples": {
                "type": "int",
                "default": 15,
                "label": "Arrow Grid Size",
                "min": 5,
                "max": 30
            },
            "arrow_scale": {
                "type": "float",
                "default": 0.3,
                "label": "Arrow Scale",
                "min": 0.1,
                "max": 1.0
            },
            "colormap": {
                "type": "str",
                "default": "viridis",
                "label": "Colormap"
            },
            "arrow_color": {
                "type": "str",
                "default": "blue",
                "label": "Arrow Color"
            }
        }
    
    def create_custom_ui(self, parent):
        """Create custom UI"""
        self._reset_state()
        
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        
        # Function input
        func_group = QGroupBox("Functions")
        func_layout = QVBoxLayout()
        
        func_layout.addWidget(QLabel("Scalar field f(x,y) for contours:"))
        self.func_f = QLineEdit()
        self.func_f.setText("np.exp(-x**2 - y**2) * x")
        func_layout.addWidget(self.func_f)
        
        self.show_quiver = QCheckBox("Show gradient arrows")
        self.show_quiver.setChecked(True)
        func_layout.addWidget(self.show_quiver)
        
        func_layout.addWidget(QLabel("Gradient u(x,y) = ∂f/∂x:"))
        self.func_u = QLineEdit()
        self.func_u.setText("np.exp(-x**2 - y**2) * (1 - 2*x**2)")
        func_layout.addWidget(self.func_u)
        
        func_layout.addWidget(QLabel("Gradient v(x,y) = ∂f/∂y:"))
        self.func_v = QLineEdit()
        self.func_v.setText("np.exp(-x**2 - y**2) * (-2*x*y)")
        func_layout.addWidget(self.func_v)
        
        # Domain
        domain_layout = QHBoxLayout()
        domain_layout.addWidget(QLabel("Domain:"))
        self.x_min = QDoubleSpinBox()
        self.x_min.setRange(-20, 20)
        self.x_min.setValue(-2)
        domain_layout.addWidget(self.x_min)
        domain_layout.addWidget(QLabel("to"))
        self.x_max = QDoubleSpinBox()
        self.x_max.setRange(-20, 20)
        self.x_max.setValue(2)
        domain_layout.addWidget(self.x_max)
        func_layout.addLayout(domain_layout)
        
        func_group.setLayout(func_layout)
        layout.addWidget(func_group)
        
        # Presets
        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout()
        
        preset_combo = QComboBox()
        preset_combo.addItems(list(self.function_presets.keys()))
        preset_combo.currentTextChanged.connect(self._load_preset)
        preset_layout.addWidget(preset_combo)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        layout.addStretch()
        return self.custom_ui_widget
    
    def _load_preset(self, name: str):
        """Load preset"""
        if name in self.function_presets:
            preset = self.function_presets[name]
            if self.func_f:
                self.func_f.setText(preset["f"])
            if self.func_u:
                self.func_u.setText(preset["u"])
            if self.func_v:
                self.func_v.setText(preset["v"])
    
    def get_custom_ui_data(self):
        """Get data from UI"""
        return {
            "f": self.func_f.text() if self.func_f else "x*y",
            "u": self.func_u.text() if self.func_u else "1",
            "v": self.func_v.text() if self.func_v else "1",
            "x_min": self.x_min.value() if self.x_min else -2,
            "x_max": self.x_max.value() if self.x_max else 2,
            "show_quiver": self.show_quiver.isChecked() if self.show_quiver else True
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if isinstance(data, dict) and "f" in data:
            try:
                x, y = np.meshgrid([0, 1], [0, 1])
                eval(data["f"])
                return True, ""
            except Exception as e:
                return False, f"Invalid function: {str(e)}"
        return False, "Invalid data"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        domain_min = data.get("x_min", -2)
        domain_max = data.get("x_max", 2)
        
        # Fine grid for contours
        x_fine = np.linspace(domain_min, domain_max, 100)
        y_fine = np.linspace(domain_min, domain_max, 100)
        X_fine, Y_fine = np.meshgrid(x_fine, y_fine)
        
        x, y = X_fine, Y_fine
        try:
            Z = eval(data["f"])
        except Exception as e:
            ax.text(0.5, 0.5, f"Error in f: {e}", transform=ax.transAxes, ha='center')
            return fig
        
        # Contour plot
        levels = options.get("contour_levels", 9)
        cs = ax.contour(X_fine, Y_fine, Z, levels=levels, 
                       cmap=options.get('colormap', 'viridis'), linewidths=2)
        ax.clabel(cs, inline=True, fontsize=8)
        
        # Quiver plot
        if data.get("show_quiver", True):
            arrow_samples = options.get("arrow_samples", 15)
            x_coarse = np.linspace(domain_min, domain_max, arrow_samples)
            y_coarse = np.linspace(domain_min, domain_max, arrow_samples)
            X_coarse, Y_coarse = np.meshgrid(x_coarse, y_coarse)
            
            x, y = X_coarse, Y_coarse
            try:
                U = eval(data["u"])
                V = eval(data["v"])
                
                scale = options.get("arrow_scale", 0.3)
                ax.quiver(X_coarse, Y_coarse, U * scale, V * scale,
                         color=options.get('arrow_color', 'blue'),
                         angles='xy', scale_units='xy', scale=1)
            except Exception as e:
                pass  # Skip arrows on error
        
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title(f"Contour: {data['f']}")
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        # Convert functions
        f_tikz = data["f"]
        u_tikz = data["u"]
        v_tikz = data["v"]
        
        replacements = [
            ("np.exp", "exp"), ("np.sin", "sin"), ("np.cos", "cos"),
            ("np.sqrt", "sqrt"), ("np.arctan2", "atan2"),
            ("**", "^"),
        ]
        for old, new in replacements:
            f_tikz = f_tikz.replace(old, new)
            u_tikz = u_tikz.replace(old, new)
            v_tikz = v_tikz.replace(old, new)
        
        domain_min = data.get("x_min", -2)
        domain_max = data.get("x_max", 2)
        
        quiver_section = ""
        if data.get("show_quiver", True):
            quiver_section = f"""
    \\addplot3[
        {options.get('arrow_color', 'blue')},-stealth,
        samples={options.get('arrow_samples', 15)},
        quiver={{
            u={{{u_tikz}}},
            v={{{v_tikz}}},
            scale arrows={options.get('arrow_scale', 0.3)},
        }},
    ] {{{f_tikz}}};"""
        
        tikz_code = f"""% Preamble: \\pgfplotsset{{width=10cm,compat=1.18}}
\\begin{{tikzpicture}}
\\begin{{axis}}[
    title={{Contour and Gradient}},
    domain={domain_min}:{domain_max},
    view={{0}}{{90}},
    axis background/.style={{fill=white}},
]
    \\addplot3[
        contour lua={{number={options.get('contour_levels', 9)},labels=false}},
        thick,
    ] {{{f_tikz}}};
{quiver_section}
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code
    
    def get_tikz_libraries(self) -> List[str]:
        return ["pgfplots"]
