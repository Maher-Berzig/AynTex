# ============================================================================
# FILE: plugins/bilinear_patch_plugin.py - NEW PLUGIN  
# ============================================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QTextEdit,
    QPushButton, QHBoxLayout
)
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class BilinearPatchPlugin(PlotPlugin):
    """Bilinear patch surface from corner points"""
    
    name = "Bilinear Patch"
    version = "1.0.0"
    category = "3d"
    description = "Create bilinear interpolated surface patches from corner points"
    requires_custom_ui = True
    
    def __init__(self):
        super().__init__()
        self._reset_state()
    
    def _reset_state(self):
        """Reset state"""
        self.custom_ui_widget = None
        self.data_text = None
        self.parsed_data = None
    
    def get_plugin_name(self) -> str:
        return "Bilinear Patch"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "colormap": {
                "type": "str",
                "default": "viridis",
                "label": "Colormap"
            },
            "show_colorbar": {
                "type": "bool",
                "default": True,
                "label": "Show Colorbar"
            },
            "interpolation": {
                "type": "int",
                "default": 10,
                "label": "Interpolation Steps",
                "min": 2,
                "max": 50
            },
            "elevation": {
                "type": "int",
                "default": 30,
                "label": "View Elevation",
                "min": 0,
                "max": 90
            },
            "azimuth": {
                "type": "int",
                "default": 45,
                "label": "View Azimuth",
                "min": 0,
                "max": 360
            },
            "top_view": {
                "type": "bool",
                "default": False,
                "label": "Top View (2D)"
            }
        }
    
    def create_custom_ui(self, parent):
        """Create custom UI"""
        self._reset_state()
        
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        
        # Data input
        data_group = QGroupBox("Patch Corner Data")
        data_layout = QVBoxLayout()
        
        instructions = QLabel(
            "Enter corner points as (x,y,z) coordinates.\n"
            "For a 2x2 patch, enter 4 points (corners).\n"
            "For larger patches, enter NxM grid of points."
        )
        instructions.setWordWrap(True)
        data_layout.addWidget(instructions)
        
        self.data_text = QTextEdit()
        self.data_text.setMinimumHeight(120)
        self.data_text.setPlaceholderText(
            "Format: x y z (one point per line)\n"
            "Example 2x2 patch:\n"
            "0 0 0\n"
            "1 0 0\n"
            "0 1 0\n"
            "1 1 1"
        )
        data_layout.addWidget(self.data_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_parse = QPushButton("Parse")
        btn_parse.clicked.connect(self.parse_data)
        btn_layout.addWidget(btn_parse)
        
        btn_sample = QPushButton("Sample 2x2")
        btn_sample.clicked.connect(self.load_sample)
        btn_layout.addWidget(btn_sample)
        
        data_layout.addLayout(btn_layout)
        
        self.status_label = QLabel("")
        data_layout.addWidget(self.status_label)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        layout.addStretch()
        return self.custom_ui_widget
    
    def parse_data(self):
        """Parse corner point data"""
        if self.data_text is None:
            return
            
        text = self.data_text.toPlainText().strip()
        if not text:
            self.status_label.setText("No data")
            return
        
        try:
            points = []
            for line in text.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        points.append([float(parts[0]), float(parts[1]), float(parts[2])])
            
            self.parsed_data = points
            n = len(points)
            # Try to determine grid size
            grid_size = int(np.sqrt(n))
            if grid_size * grid_size == n:
                self.status_label.setText(f"✓ Parsed {grid_size}x{grid_size} grid ({n} points)")
            else:
                self.status_label.setText(f"✓ Parsed {n} points")
            self.status_label.setStyleSheet("color: green;")
            
        except Exception as e:
            self.status_label.setText(f"✗ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
    
    def load_sample(self):
        """Load sample data"""
        if self.data_text:
            self.data_text.setPlainText(
                "0 0 0\n"
                "1 0 0\n"
                "0 1 0\n"
                "1 1 1"
            )
            self.parse_data()
    
    def get_custom_ui_data(self):
        """Get parsed data"""
        if self.parsed_data is None:
            self.parse_data()
        return self.parsed_data
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if data is None or len(data) < 4:
            return False, "Need at least 4 corner points"
        return True, ""
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig = plt.figure(figsize=(10, 8))
        
        if options.get('top_view', False):
            ax = fig.add_subplot(111)
        else:
            ax = fig.add_subplot(111, projection='3d')
        
        points = np.array(data)
        n = len(points)
        grid_size = int(np.sqrt(n))
        
        if grid_size * grid_size != n:
            grid_size = 2  # Default to 2x2
        
        # Reshape to grid
        try:
            X = points[:, 0].reshape(grid_size, grid_size)
            Y = points[:, 1].reshape(grid_size, grid_size)
            Z = points[:, 2].reshape(grid_size, grid_size)
        except Exception:
            # Fallback for 2x2
            X = np.array([[points[0][0], points[1][0]], 
                         [points[2][0], points[3][0]]])
            Y = np.array([[points[0][1], points[1][1]], 
                         [points[2][1], points[3][1]]])
            Z = np.array([[points[0][2], points[1][2]], 
                         [points[2][2], points[3][2]]])
        
        # Interpolate
        steps = options.get('interpolation', 10)
        u = np.linspace(0, 1, steps)
        v = np.linspace(0, 1, steps)
        U, V = np.meshgrid(u, v)
        
        # Bilinear interpolation for 2x2 base
        X_interp = (1-U)*(1-V)*X[0,0] + U*(1-V)*X[0,-1] + (1-U)*V*X[-1,0] + U*V*X[-1,-1]
        Y_interp = (1-U)*(1-V)*Y[0,0] + U*(1-V)*Y[0,-1] + (1-U)*V*Y[-1,0] + U*V*Y[-1,-1]
        Z_interp = (1-U)*(1-V)*Z[0,0] + U*(1-V)*Z[0,-1] + (1-U)*V*Z[-1,0] + U*V*Z[-1,-1]
        
        if options.get('top_view', False):
            # 2D view
            cf = ax.contourf(X_interp, Y_interp, Z_interp, 
                           cmap=options.get('colormap', 'viridis'), levels=20)
            if options.get('show_colorbar', True):
                fig.colorbar(cf, ax=ax)
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_aspect('equal')
        else:
            # 3D surface
            surf = ax.plot_surface(X_interp, Y_interp, Z_interp,
                                  cmap=options.get('colormap', 'viridis'),
                                  edgecolor='none', alpha=0.9)
            
            # Plot original points
            ax.scatter(points[:, 0], points[:, 1], points[:, 2],
                      c='red', s=50, marker='o')
            
            if options.get('show_colorbar', True):
                fig.colorbar(surf, ax=ax, shrink=0.5)
            
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_zlabel('Z')
            
            ax.view_init(elev=options.get('elevation', 30),
                        azim=options.get('azimuth', 45))
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        points = np.array(data)
        
        coord_str = "\n        ".join([f"({p[0]},{p[1]},{p[2]})" for p in points])
        
        view = "{0}{90}" if options.get('top_view', False) else f"{{{options.get('azimuth', 45)}}}{{{options.get('elevation', 30)}}}"
        
        tikz_code = f"""% Preamble: \\pgfplotsset{{width=10cm,compat=1.18}}
% \\usepgfplotslibrary{{patchplots}}
\\begin{{tikzpicture}}
\\begin{{axis}}[
    view={view},
    colormap/{options.get('colormap', 'viridis')},
    colorbar,
]
\\addplot3[
    surf,
    shader=interp,
    patch type=bilinear,
] coordinates {{
        {coord_str}
}};
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code
    
    def get_tikz_libraries(self) -> List[str]:
        return ["pgfplots", "patchplots"]