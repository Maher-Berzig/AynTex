# ============================================================================
# FILE: plugins/polar_plugin.py
# ============================================================================

import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class PolarPlotPlugin(PlotPlugin):
    """Polar plot plugin"""
    
    name = "Polar Plot"
    version = "1.0.0"
    category = "advanced"
    description = "Create a polar/radar plot"
    
    def get_plugin_name(self) -> str:
        return "Polar Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "color": {
                "type": "str",
                "default": "blue",
                "label": "Line Color"
            },
            "fill": {
                "type": "bool",
                "default": True,
                "label": "Fill Area"
            },
            "fill_alpha": {
                "type": "float",
                "default": 0.3,
                "label": "Fill Transparency",
                "min": 0.0,
                "max": 1.0
            },
            "linewidth": {
                "type": "float",
                "default": 2.0,
                "label": "Line Width",
                "min": 0.5,
                "max": 5.0
            },
            "markers": {
                "type": "bool",
                "default": True,
                "label": "Show Markers"
            }
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        try:
            arr = np.array(data)
            if arr.ndim == 1:
                return True, ""
            if arr.ndim == 2 and arr.shape[1] == 2:
                return True, ""
            return False, "Data must be 1D (values only) or 2D (theta, r)"
        except Exception:
            return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
        
        arr = np.array(data)
        if arr.ndim == 1:
            n = len(arr)
            theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
            r = arr
            # Close the polygon
            theta = np.append(theta, theta[0])
            r = np.append(r, r[0])
        else:
            theta = arr[:, 0]
            r = arr[:, 1]
        
        marker = 'o' if options.get('markers', True) else ''
        ax.plot(theta, r, 
                color=options.get('color', 'blue'),
                linewidth=options.get('linewidth', 2.0),
                marker=marker, markersize=6)
        
        if options.get('fill', True):
            ax.fill(theta, r, color=options.get('color', 'blue'),
                   alpha=options.get('fill_alpha', 0.3))
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        arr = np.array(data)
        if arr.ndim == 1:
            n = len(arr)
            theta = np.linspace(0, 360, n, endpoint=False)
            r = arr
        else:
            theta = np.degrees(arr[:, 0])
            r = arr[:, 1]
        
        coords = "\n".join([f"        ({theta[i]:.1f},{r[i]:.3f})" for i in range(len(theta))])
        
        fill_str = f"fill={options.get('color', 'blue')}, fill opacity={options.get('fill_alpha', 0.3)}," if options.get('fill', True) else ""
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{polaraxis}}[
    width=10cm,
    height=10cm
]
\\addplot[
    color={options.get('color', 'blue')},
    line width={options.get('linewidth', 2.0)}pt,
    {fill_str}
    mark={'*' if options.get('markers', True) else 'none'}
] coordinates {{
{coords}
}} --cycle;
\\end{{polaraxis}}
\\end{{tikzpicture}}"""
        
        return tikz_code