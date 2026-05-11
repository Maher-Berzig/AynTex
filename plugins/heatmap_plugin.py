# ============================================================================
# FILE: plugins/heatmap_plugin.py
# ============================================================================

import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class HeatmapPlugin(PlotPlugin):
    """Heatmap plugin for 2D data visualization"""
    
    name = "Heatmap"
    version = "1.0.0"
    category = "advanced"
    description = "Create a heatmap for 2D data"
    
    def get_plugin_name(self) -> str:
        return "Heatmap"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "colormap": {
                "type": "str",
                "default": "viridis",
                "label": "Color Map (viridis, hot, cool, plasma)"
            },
            "show_values": {
                "type": "bool",
                "default": True,
                "label": "Show Values"
            },
            "show_colorbar": {
                "type": "bool",
                "default": True,
                "label": "Show Color Bar"
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
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        try:
            arr = np.array(data)
            if arr.ndim == 2:
                return True, ""
            return False, "Data must be a 2D array/matrix"
        except Exception:
            return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        arr = np.array(data)
        
        cmap = options.get('colormap', 'viridis')
        im = ax.imshow(arr, cmap=cmap, aspect='auto')
        
        if options.get('show_colorbar', True):
            plt.colorbar(im, ax=ax)
        
        if options.get('show_values', True):
            for i in range(arr.shape[0]):
                for j in range(arr.shape[1]):
                    ax.text(j, i, f'{arr[i, j]:.2f}',
                           ha='center', va='center', color='white',
                           fontsize=8)
        
        ax.set_xlabel(options.get('xlabel', 'X'))
        ax.set_ylabel(options.get('ylabel', 'Y'))
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        arr = np.array(data)
        rows, cols = arr.shape
        
        # Generate matrix data
        matrix_data = []
        for i in range(rows):
            row_data = " ".join([f"{arr[i, j]:.3f}" for j in range(cols)])
            matrix_data.append(f"        {row_data}")
        
        matrix_str = "\n".join(matrix_data)
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    colormap/viridis,
    colorbar,
    xlabel={{{options.get('xlabel', 'X')}}},
    ylabel={{{options.get('ylabel', 'Y')}}},
    view={{0}}{{90}},
    width=10cm,
    height=8cm
]
\\addplot3[
    surf,
    shader=interp,
    mesh/rows={rows},
    mesh/cols={cols}
] table[row sep=\\\\] {{
{matrix_str}
}};
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code
