# ============================================================================
# FILE: plugins/graph_drawing_plugin.py
# VERSION: 3.0.0 — Dynamic canvas, unlimited drag, expanded options
# ============================================================================
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QLineEdit, QGroupBox,
    QSpinBox, QMessageBox, QComboBox, QSizePolicy,
    QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch
from matplotlib.lines import Line2D
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin

matplotlib.rcParams['figure.max_open_warning'] = 50


# ─────────────────────────────────────────────────────────────────────────────
# Draggable handler
# ─────────────────────────────────────────────────────────────────────────────
class DraggableGraph:
    """
    Handles interactive node dragging.

    Key improvements over v2:
    • Auto-expands axis limits when a node is dragged near/beyond the border,
      so nodes can be freely repositioned anywhere — including horizontal
      alignment — without hitting an invisible wall.
    • Falls back to figure-coordinate conversion when the cursor leaves the
      axes (event.xdata / ydata become None), so dragging never "sticks".
    """

    def __init__(self, ax, canvas, plugin):
        self.ax = ax
        self.canvas = canvas
        self.plugin = plugin
        self.dragging_node = None
        self.positions: Dict[int, List[float]] = {}
        self.node_circles: Dict[int, Any] = {}
        self.node_labels: Dict[int, Any] = {}
        self.edge_lines: Dict[Tuple[int, int], Any] = {}

        self.cid_press   = canvas.mpl_connect('button_press_event',   self.on_press)
        self.cid_release = canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion  = canvas.mpl_connect('motion_notify_event',  self.on_motion)

    def disconnect(self):
        for cid in (self.cid_press, self.cid_release, self.cid_motion):
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass

    def set_data(self, positions, node_circles, node_labels, edge_lines):
        self.positions    = {k: list(v) for k, v in positions.items()}
        self.node_circles = node_circles
        self.node_labels  = node_labels
        self.edge_lines   = edge_lines

    def get_positions(self):
        return {k: list(v) for k, v in self.positions.items()}

    def _hit_radius(self):
        return max(self.plugin.current_node_radius * 2.5, 0.06)

    def find_node_at(self, x, y):
        if x is None or y is None:
            return None
        hr = self._hit_radius()
        for idx, (nx, ny) in self.positions.items():
            if (x - nx) ** 2 + (y - ny) ** 2 < hr ** 2:
                return idx
        return None

    def on_press(self, event):
        if event.inaxes != self.ax or event.button != 1:
            return
        node_idx = self.find_node_at(event.xdata, event.ydata)
        if node_idx is not None:
            self.dragging_node = node_idx

    def on_release(self, event):
        if self.dragging_node is not None:
            self.plugin.node_positions = self.get_positions()
        self.dragging_node = None

    def on_motion(self, event):
        if self.dragging_node is None:
            return

        # When cursor leaves the axes, xdata/ydata become None.
        # Convert from pixel coordinates so the node keeps following the cursor.
        if event.xdata is None or event.ydata is None:
            try:
                new_x, new_y = self.ax.transData.inverted().transform(
                    (event.x, event.y))
            except Exception:
                return
        else:
            new_x, new_y = event.xdata, event.ydata

        idx = self.dragging_node
        self.positions[idx] = [new_x, new_y]

        if idx in self.node_circles:
            c = self.node_circles[idx]
            if isinstance(c, Circle):
                c.center = (new_x, new_y)
            else:
                # FancyBboxPatch — re-centre the bounding box
                r = self.plugin.current_node_radius
                c.set_xy((new_x - r, new_y - r))

        if idx in self.node_labels:
            self.node_labels[idx].set_position((new_x, new_y))

        self._update_edges_for_node(idx)
        self._auto_expand_limits()
        self.canvas.draw_idle()

    def _update_edges_for_node(self, node_idx):
        for (fn, tn), artist in self.edge_lines.items():
            if fn == node_idx or tn == node_idx:
                x1, y1 = self.positions[fn]
                x2, y2 = self.positions[tn]
                if isinstance(artist, Line2D):
                    artist.set_data([x1, x2], [y1, y2])
                elif isinstance(artist, FancyArrowPatch):
                    artist.set_positions((x1, y1), (x2, y2))

    def _auto_expand_limits(self):
        """Expand (never shrink) axis limits so dragged nodes stay visible."""
        if not self.positions:
            return
        xs = [p[0] for p in self.positions.values()]
        ys = [p[1] for p in self.positions.values()]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        mx = max((xmax - xmin) * 0.35, 0.45)
        my = max((ymax - ymin) * 0.35, 0.45)
        cxl = self.ax.get_xlim()
        cyl = self.ax.get_ylim()
        self.ax.set_xlim(min(cxl[0], xmin - mx), max(cxl[1], xmax + mx))
        self.ax.set_ylim(min(cyl[0], ymin - my), max(cyl[1], ymax + my))


# ─────────────────────────────────────────────────────────────────────────────
# Plugin
# ─────────────────────────────────────────────────────────────────────────────
class GraphDrawingPlugin(PlotPlugin):
    """Interactive graph drawing plugin — v3.0.0"""

    name = "Graph Drawing"
    version = "3.0.0"
    category = "interactive"
    description = "Draw graphs with draggable nodes — edges follow node movement"
    requires_custom_ui = True

    CLASSIC_GRAPHS = {
        "Path P₅": {
            "nodes": ["1","2","3","4","5"],
            "edges": [(0,1),(1,2),(2,3),(3,4)],
            "description": "Path graph with 5 vertices"
        },
        "Cycle C₆": {
            "nodes": ["1","2","3","4","5","6"],
            "edges": [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0)],
            "description": "Cycle graph with 6 vertices"
        },
        "Star S₆": {
            "nodes": ["center","1","2","3","4","5"],
            "edges": [(0,1),(0,2),(0,3),(0,4),(0,5)],
            "description": "Star graph with 6 vertices"
        },
        "Wheel W₆": {
            "nodes": ["hub","1","2","3","4","5"],
            "edges": [(0,1),(0,2),(0,3),(0,4),(0,5),
                      (1,2),(2,3),(3,4),(4,5),(5,1)],
            "description": "Wheel graph with 6 vertices"
        },
        "Complete K₄": {
            "nodes": ["A","B","C","D"],
            "edges": [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)],
            "description": "Complete graph on 4 vertices"
        },
        "Complete K₅": {
            "nodes": ["A","B","C","D","E"],
            "edges": [(0,1),(0,2),(0,3),(0,4),
                      (1,2),(1,3),(1,4),(2,3),(2,4),(3,4)],
            "description": "Complete graph on 5 vertices"
        },
        "Bipartite K₃,₃": {
            "nodes": ["A₁","A₂","A₃","B₁","B₂","B₃"],
            "edges": [(0,3),(0,4),(0,5),(1,3),(1,4),(1,5),(2,3),(2,4),(2,5)],
            "description": "Complete bipartite graph (non-planar)"
        },
        "Cubical (3-Cube)": {
            "nodes": ["000","001","010","011","100","101","110","111"],
            "edges": [(0,1),(0,2),(0,4),(1,3),(1,5),(2,3),
                      (2,6),(3,7),(4,5),(4,6),(5,7),(6,7)],
            "description": "Cube graph"
        },
        "Petersen": {
            "nodes": ["0","1","2","3","4","5","6","7","8","9"],
            "edges": [(0,1),(1,2),(2,3),(3,4),(4,0),
                      (0,5),(1,6),(2,7),(3,8),(4,9),
                      (5,7),(7,9),(9,6),(6,8),(8,5)],
            "description": "Petersen graph"
        },
        "Binary Tree (depth 3)": {
            "nodes": ["root","L","R","LL","LR","RL","RR"],
            "edges": [(0,1),(0,2),(1,3),(1,4),(2,5),(2,6)],
            "description": "Complete binary tree"
        },
        "Grid 3×3": {
            "nodes": [f"({i},{j})" for i in range(3) for j in range(3)],
            "edges": [(0,1),(1,2),(3,4),(4,5),(6,7),(7,8),
                      (0,3),(3,6),(1,4),(4,7),(2,5),(5,8)],
            "description": "3×3 Grid graph"
        },
        "Diamond": {
            "nodes": ["top","left","right","bottom"],
            "edges": [(0,1),(0,2),(1,2),(1,3),(2,3)],
            "description": "Diamond graph (K₄ minus one edge)"
        },
        "House": {
            "nodes": ["roof","left-top","right-top","left-bot","right-bot"],
            "edges": [(0,1),(0,2),(1,2),(1,3),(2,4),(3,4)],
            "description": "House graph"
        },
        "Bull": {
            "nodes": ["1","2","3","4","5"],
            "edges": [(0,1),(0,2),(1,2),(1,3),(2,4)],
            "description": "Bull graph"
        },
        "Butterfly": {
            "nodes": ["center","a","b","c","d"],
            "edges": [(0,1),(0,2),(1,2),(0,3),(0,4),(3,4)],
            "description": "Butterfly / bowtie graph"
        },
        "Ladder L₄": {
            "nodes": ["a0","a1","a2","a3","b0","b1","b2","b3"],
            "edges": [(0,1),(1,2),(2,3),(4,5),(5,6),(6,7),
                      (0,4),(1,5),(2,6),(3,7)],
            "description": "Ladder graph with 4 rungs"
        },
    }

    # ── init ──────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__()
        self.nodes: List[str] = []
        self.edges: List[Tuple[int, int]] = []
        self.edge_labels: Dict[Tuple[int, int], str] = {}
        self.is_directed = False
        self.node_positions: Dict[int, List[float]] = {}

        self.current_node_radius       = 0.12
        self.current_node_color        = 'lightblue'
        self.current_node_stroke_color = 'black'

        self.draggable_graph = None
        self._plot_data: Dict = {}

        # UI refs
        self.custom_ui_widget  = None
        self.node_list         = None
        self.edge_list         = None
        self.node_input        = None
        self.edge_from         = None
        self.edge_to           = None
        self.edge_label_input  = None
        self.graph_combo       = None
        self.description_label = None
        self.nodes_group       = None
        self.edges_group       = None
        self.petersen_n        = None
        self.petersen_k        = None
        self.kn_spin           = None
        self.cn_spin           = None
        self.bip_m             = None
        self.bip_n             = None
        self.grid_m            = None
        self.grid_n            = None
        self.info_label        = None

    def get_plugin_name(self) -> str:
        return "Graph Drawing"

    # ── options ───────────────────────────────────────────────────────
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "node_color": {
                "type": "str", "default": "lightblue",
                "label": "Node Fill Color"
            },
            "node_stroke_color": {
                "type": "str", "default": "black",
                "label": "Node Stroke Color"
            },
            "node_stroke_width": {
                "type": "float", "default": 2.0,
                "label": "Node Stroke Width",
                "min": 0.5, "max": 8.0
            },
            "node_shape": {
                "type": "choice",
                "choices": ["circle", "square", "rounded_square"],
                "default": "circle",
                "label": "Node Shape"
            },
            "label_color": {
                "type": "str", "default": "black",
                "label": "Label Color"
            },
            "edge_color": {
                "type": "str", "default": "black",
                "label": "Edge Color"
            },
            "edge_width": {
                "type": "float", "default": 2.0,
                "label": "Edge Width",
                "min": 0.5, "max": 8.0
            },
            "edge_style": {
                "type": "choice",
                "choices": ["solid", "dashed", "dotted"],
                "default": "solid",
                "label": "Edge Style"
            },
            "node_size": {
                "type": "float", "default": 0.5,
                "label": "Node Size",
                "min": 0.1, "max": 2.0
            },
            "font_size": {
                "type": "int", "default": 10,
                "label": "Label Font Size",
                "min": 6, "max": 24
            },
            "rotation_angle": {
                "type": "float", "default": 0.0,
                "label": "Rotation Angle (°)",
                "min": -360.0, "max": 360.0
            },
            "graph_scale": {
                "type": "float", "default": 1.0,
                "label": "Graph Scale",
                "min": 0.1, "max": 5.0
            },
            "show_labels": {
                "type": "bool", "default": True,
                "label": "Show Node Labels"
            },
            "show_edge_labels": {
                "type": "bool", "default": True,
                "label": "Show Edge Labels"
            },
            "show_grid": {
                "type": "bool", "default": False,
                "label": "Show Grid"
            },
            "show_axes": {
                "type": "bool", "default": False,
                "label": "Show Axes / Coordinates"
            },
            "directed": {
                "type": "bool", "default": False,
                "label": "Directed Graph"
            },
            "curved_edges": {
                "type": "bool", "default": False,
                "label": "Curved Edges"
            },
            "tikz_zoom": {
                "type": "float", "default": 2.5,
                "label": "TikZ Zoom (cm)",
                "min": 0.5, "max": 10.0
            },
        }

    # ── custom UI ─────────────────────────────────────────────────────
    def create_custom_ui(self, parent):
        self.custom_ui_widget = QWidget(parent)
        outer = QVBoxLayout(self.custom_ui_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(8)
        layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── Stats bar ────────────────────────────────────────────
        self.info_label = QLabel("No graph loaded")
        self.info_label.setStyleSheet(
            "QLabel{background:#F3F4F6;border:1px solid #D1D5DB;"
            "border-radius:4px;padding:4px 8px;color:#374151;font-size:11px;}"
        )
        layout.addWidget(self.info_label)

        # ── Classic / generators ─────────────────────────────────
        cg = QGroupBox("Load Classic / Generated Graph")
        cl = QVBoxLayout(cg)

        # Petersen P(n,k)
        r = QHBoxLayout()
        r.addWidget(QLabel("Petersen P(n,k):"))
        self.petersen_n = QSpinBox(); self.petersen_n.setRange(3, 20); self.petersen_n.setValue(5)
        self.petersen_k = QSpinBox(); self.petersen_k.setRange(1, 10); self.petersen_k.setValue(2)
        r.addWidget(QLabel("n=")); r.addWidget(self.petersen_n)
        r.addWidget(QLabel("k=")); r.addWidget(self.petersen_k)
        b = QPushButton("Gen"); b.clicked.connect(self.on_generate_petersen); r.addWidget(b)
        r.addStretch(); cl.addLayout(r)

        # Complete K_n
        r = QHBoxLayout()
        r.addWidget(QLabel("Complete K_n:"))
        self.kn_spin = QSpinBox(); self.kn_spin.setRange(2, 12); self.kn_spin.setValue(4)
        r.addWidget(QLabel("n=")); r.addWidget(self.kn_spin)
        b = QPushButton("Gen"); b.clicked.connect(self.on_generate_complete); r.addWidget(b)
        r.addStretch(); cl.addLayout(r)

        # Cycle C_n
        r = QHBoxLayout()
        r.addWidget(QLabel("Cycle C_n:"))
        self.cn_spin = QSpinBox(); self.cn_spin.setRange(3, 20); self.cn_spin.setValue(6)
        r.addWidget(QLabel("n=")); r.addWidget(self.cn_spin)
        b = QPushButton("Gen"); b.clicked.connect(self.on_generate_cycle); r.addWidget(b)
        r.addStretch(); cl.addLayout(r)

        # Bipartite K_{m,n}
        r = QHBoxLayout()
        r.addWidget(QLabel("Bipartite K_{m,n}:"))
        self.bip_m = QSpinBox(); self.bip_m.setRange(1, 8); self.bip_m.setValue(3)
        self.bip_n_spin = QSpinBox(); self.bip_n_spin.setRange(1, 8); self.bip_n_spin.setValue(3)
        r.addWidget(QLabel("m=")); r.addWidget(self.bip_m)
        r.addWidget(QLabel("n=")); r.addWidget(self.bip_n_spin)
        b = QPushButton("Gen"); b.clicked.connect(self.on_generate_bipartite); r.addWidget(b)
        r.addStretch(); cl.addLayout(r)

        # Grid m×n
        r = QHBoxLayout()
        r.addWidget(QLabel("Grid m×n:"))
        self.grid_m = QSpinBox(); self.grid_m.setRange(2, 8); self.grid_m.setValue(3)
        self.grid_n = QSpinBox(); self.grid_n.setRange(2, 8); self.grid_n.setValue(3)
        r.addWidget(QLabel("m=")); r.addWidget(self.grid_m)
        r.addWidget(QLabel("n=")); r.addWidget(self.grid_n)
        b = QPushButton("Gen"); b.clicked.connect(self.on_generate_grid); r.addWidget(b)
        r.addStretch(); cl.addLayout(r)

        # Named preset dropdown
        r = QHBoxLayout()
        r.addWidget(QLabel("Named preset:"))
        self.graph_combo = QComboBox()
        self.graph_combo.addItem("-- Select --")
        for name in sorted(self.CLASSIC_GRAPHS.keys()):
            self.graph_combo.addItem(name)
        self.graph_combo.currentTextChanged.connect(self.on_classic_graph_selected)
        r.addWidget(self.graph_combo, 1); cl.addLayout(r)

        self.description_label = QLabel("")
        self.description_label.setStyleSheet("color:gray;font-style:italic;")
        cl.addWidget(self.description_label)

        b2 = QPushButton("Load Selected Preset")
        b2.clicked.connect(self.on_load_classic_graph)
        cl.addWidget(b2)
        layout.addWidget(cg)

        # ── Drag hint ────────────────────────────────────────────
        hint = QLabel("🖱️  Drag nodes freely — the canvas expands automatically.\n"
                      "   Use Centre View to re-fit after dragging.")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "QLabel{background:#EFF6FF;border:1px solid #3B82F6;"
            "border-radius:5px;padding:6px 10px;color:#1D4ED8;font-weight:bold;}"
        )
        layout.addWidget(hint)

        # ── Nodes ────────────────────────────────────────────────
        self.nodes_group = QGroupBox("Nodes (0)")
        nl = QVBoxLayout(self.nodes_group)

        r = QHBoxLayout()
        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("Label (blank → auto)")
        self.node_input.returnPressed.connect(self.on_add_node)
        r.addWidget(self.node_input)
        b = QPushButton("Add"); b.clicked.connect(self.on_add_node); r.addWidget(b)
        nl.addLayout(r)

        self.node_list = QListWidget()
        self.node_list.setMinimumHeight(80)
        self.node_list.setMaximumHeight(130)
        nl.addWidget(self.node_list)

        r = QHBoxLayout()
        b = QPushButton("Remove Selected"); b.clicked.connect(self.on_remove_node); r.addWidget(b)
        b2 = QPushButton("Rename Selected"); b2.clicked.connect(self.on_rename_node); r.addWidget(b2)
        nl.addLayout(r)
        layout.addWidget(self.nodes_group)

        # ── Edges ────────────────────────────────────────────────
        self.edges_group = QGroupBox("Edges (0)")
        el = QVBoxLayout(self.edges_group)

        r = QHBoxLayout()
        r.addWidget(QLabel("From:"))
        self.edge_from = QSpinBox(); self.edge_from.setMinimum(0); r.addWidget(self.edge_from)
        r.addWidget(QLabel("To:"))
        self.edge_to = QSpinBox(); self.edge_to.setMinimum(0); r.addWidget(self.edge_to)
        el.addLayout(r)

        r = QHBoxLayout()
        r.addWidget(QLabel("Label (opt.):"))
        self.edge_label_input = QLineEdit()
        self.edge_label_input.setPlaceholderText("e.g. weight / name")
        r.addWidget(self.edge_label_input)
        el.addLayout(r)

        b = QPushButton("Add Edge"); b.clicked.connect(self.on_add_edge); el.addWidget(b)

        self.edge_list = QListWidget()
        self.edge_list.setMinimumHeight(80)
        self.edge_list.setMaximumHeight(130)
        el.addWidget(self.edge_list)

        b = QPushButton("Remove Selected Edge"); b.clicked.connect(self.on_remove_edge); el.addWidget(b)
        layout.addWidget(self.edges_group)

        # ── Actions ──────────────────────────────────────────────
        r = QHBoxLayout()
        b = QPushButton("Reset Layout"); b.setToolTip("Return nodes to default positions")
        b.clicked.connect(self.on_reset_layout); r.addWidget(b)
        b2 = QPushButton("Centre View"); b2.setToolTip("Re-fit axis to current positions")
        b2.clicked.connect(self.on_centre_view); r.addWidget(b2)
        b3 = QPushButton("Clear All"); b3.clicked.connect(self.on_clear_all); r.addWidget(b3)
        layout.addLayout(r)

        layout.addStretch()
        self.refresh_lists()
        return self.custom_ui_widget

    # ── UI callbacks ──────────────────────────────────────────────────
    def on_reset_layout(self):
        self.node_positions.clear()
        if self.draggable_graph:
            self.draggable_graph.positions.clear()
        QMessageBox.information(
            self.custom_ui_widget, "Layout Reset",
            "Positions cleared — click Generate Preview to recompute.")

    def on_centre_view(self):
        if not self.draggable_graph or not self.draggable_graph.positions:
            return
        pos = self.draggable_graph.positions
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        mx = max((max(xs) - min(xs)) * 0.40, 0.50)
        my = max((max(ys) - min(ys)) * 0.40, 0.50)
        self.draggable_graph.ax.set_xlim(min(xs) - mx, max(xs) + mx)
        self.draggable_graph.ax.set_ylim(min(ys) - my, max(ys) + my)
        self.draggable_graph.canvas.draw_idle()

    def on_generate_petersen(self):
        n = self.petersen_n.value(); k = self.petersen_k.value()
        if k >= n // 2 + 1:
            QMessageBox.warning(self.custom_ui_widget, "Invalid",
                                f"k must be ≤ {n//2} for P({n},k)"); return
        self.nodes = [f"u{i}" for i in range(n)] + [f"v{i}" for i in range(n)]
        self.edges = ([(i,(i+1)%n) for i in range(n)] +
                      [(i, n+i) for i in range(n)] +
                      [(n+i, n+(i+k)%n) for i in range(n)])
        self.is_directed = False; self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()

    def on_generate_complete(self):
        n = self.kn_spin.value()
        self.nodes = [str(i+1) for i in range(n)]
        self.edges = [(i,j) for i in range(n) for j in range(i+1,n)]
        self.is_directed = False; self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()

    def on_generate_cycle(self):
        n = self.cn_spin.value()
        self.nodes = [str(i+1) for i in range(n)]
        self.edges = [(i,(i+1)%n) for i in range(n)]
        self.is_directed = False; self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()

    def on_generate_bipartite(self):
        m, n = self.bip_m.value(), self.bip_n_spin.value()
        self.nodes = [f"A{i+1}" for i in range(m)] + [f"B{j+1}" for j in range(n)]
        self.edges = [(i, m+j) for i in range(m) for j in range(n)]
        self.is_directed = False; self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()

    def on_generate_grid(self):
        m, n = self.grid_m.value(), self.grid_n.value()
        self.nodes = [f"({i},{j})" for i in range(m) for j in range(n)]
        self.edges = []
        for i in range(m):
            for j in range(n):
                idx = i*n+j
                if j+1 < n: self.edges.append((idx, idx+1))
                if i+1 < m: self.edges.append((idx, idx+n))
        self.is_directed = False; self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()

    def on_classic_graph_selected(self, text):
        if text in self.CLASSIC_GRAPHS:
            self.description_label.setText(
                self.CLASSIC_GRAPHS[text].get("description",""))
        else:
            self.description_label.setText("")

    def on_load_classic_graph(self):
        text = self.graph_combo.currentText()
        if text not in self.CLASSIC_GRAPHS:
            QMessageBox.warning(self.custom_ui_widget,"Error","Select a preset first."); return
        d = self.CLASSIC_GRAPHS[text]
        self.nodes = list(d["nodes"]); self.edges = list(d["edges"])
        self.is_directed = d.get("directed", False)
        self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()
        QMessageBox.information(self.custom_ui_widget,"Loaded",
            f"{text}: {len(self.nodes)} nodes, {len(self.edges)} edges")

    def on_add_node(self):
        label = self.node_input.text().strip() or f"v{len(self.nodes)}"
        self.nodes.append(label); self.refresh_lists(); self.node_input.clear()
        if self.node_list and self.node_list.count() > 0:
            self.node_list.scrollToBottom()

    def on_remove_node(self):
        row = self.node_list.currentRow()
        if row < 0: return
        self.nodes.pop(row)
        self.edges = [(f-(1 if f>row else 0), t-(1 if t>row else 0))
                      for f,t in self.edges if f!=row and t!=row]
        self.node_positions = {(i-(1 if i>row else 0)): pos
                               for i,pos in self.node_positions.items() if i!=row}
        self.edge_labels = {(f,t):v for (f,t),v in self.edge_labels.items()
                            if f!=row and t!=row}
        self.refresh_lists()

    def on_rename_node(self):
        row = self.node_list.currentRow()
        if row < 0 or row >= len(self.nodes): return
        new_label = self.node_input.text().strip()
        if not new_label:
            QMessageBox.warning(self.custom_ui_widget,"Rename",
                                "Type the new label in the node field first."); return
        self.nodes[row] = new_label; self.refresh_lists(); self.node_input.clear()

    def on_add_edge(self):
        f, t = self.edge_from.value(), self.edge_to.value()
        if f >= len(self.nodes) or t >= len(self.nodes):
            QMessageBox.warning(self.custom_ui_widget,"Error","Node index out of range."); return
        if f == t:
            QMessageBox.warning(self.custom_ui_widget,"Error","Self-loops not supported."); return
        if (f,t) not in self.edges and (t,f) not in self.edges:
            self.edges.append((f,t))
            lbl = self.edge_label_input.text().strip()
            if lbl: self.edge_labels[(f,t)] = lbl
            self.edge_label_input.clear(); self.refresh_lists()
            if self.edge_list and self.edge_list.count() > 0:
                self.edge_list.scrollToBottom()

    def on_remove_edge(self):
        row = self.edge_list.currentRow()
        if 0 <= row < len(self.edges):
            key = self.edges[row]; self.edges.pop(row)
            self.edge_labels.pop(key, None); self.edge_labels.pop((key[1],key[0]),None)
            self.refresh_lists()

    def on_clear_all(self):
        self.nodes.clear(); self.edges.clear()
        self.edge_labels.clear(); self.node_positions.clear()
        self.refresh_lists()

    def refresh_lists(self):
        if self.node_list is not None:
            self.node_list.clear()
            for i, lbl in enumerate(self.nodes):
                self.node_list.addItem(f"{i}: {lbl}")
            self.node_list.update(); self.node_list.repaint()

        if self.edge_list is not None:
            self.edge_list.clear()
            arrow = "→" if self.is_directed else "—"
            for f, t in self.edges:
                fl = self.nodes[f] if f < len(self.nodes) else str(f)
                tl = self.nodes[t] if t < len(self.nodes) else str(t)
                lbl = self.edge_labels.get((f,t), self.edge_labels.get((t,f),""))
                suffix = f"  [{lbl}]" if lbl else ""
                self.edge_list.addItem(f"{f}({fl}) {arrow} {t}({tl}){suffix}")
            self.edge_list.update(); self.edge_list.repaint()

        if self.nodes_group: self.nodes_group.setTitle(f"Nodes ({len(self.nodes)})")
        if self.edges_group: self.edges_group.setTitle(f"Edges ({len(self.edges)})")

        max_idx = max(0, len(self.nodes)-1)
        if self.edge_from: self.edge_from.setMaximum(max_idx)
        if self.edge_to:   self.edge_to.setMaximum(max_idx)

        if self.info_label is not None:
            n, m = len(self.nodes), len(self.edges)
            if n == 0:
                self.info_label.setText("No graph loaded")
            else:
                max_e = n*(n-1)//2 if not self.is_directed else n*(n-1)
                density = m/max_e if max_e > 0 else 0.0
                deg: Dict[int,int] = {}
                for f,t in self.edges:
                    deg[f] = deg.get(f,0)+1; deg[t] = deg.get(t,0)+1
                avg_d = sum(deg.values())/n if n else 0
                self.info_label.setText(
                    f"n={n}  m={m}  density={density:.2f}  "
                    f"avg deg={avg_d:.1f}  "
                    f"{'directed' if self.is_directed else 'undirected'}")

    # ── data transfer ─────────────────────────────────────────────────
    def get_custom_ui_data(self):
        if self.draggable_graph and self.draggable_graph.positions:
            self.node_positions = self.draggable_graph.get_positions()
        return {
            "nodes":       self.nodes.copy(),
            "edges":       self.edges.copy(),
            "edge_labels": {f"{k[0]},{k[1]}": v for k,v in self.edge_labels.items()},
            "positions":   {k: list(v) for k,v in self.node_positions.items()}
        }

    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if isinstance(data, dict) and "nodes" in data and "edges" in data:
            return True, ""
        return False, "Invalid graph data structure"

    # ── layout ────────────────────────────────────────────────────────
    def compute_layout(self, nodes, edges, rotation=0.0, scale=1.0):
        n = len(nodes)
        if n == 0: return {}
        positions: Dict[int, List[float]] = {}

        # Petersen-type: outer ring + spokes + inner ring
        if n % 2 == 0 and n >= 6:
            half = n // 2
            outer_ok = all((i,(i+1)%half) in edges or ((i+1)%half,i) in edges
                           for i in range(half))
            spoke_ok = all((i,half+i) in edges or (half+i,i) in edges
                           for i in range(half))
            if outer_ok and spoke_ok:
                for i in range(half):
                    a = 2*np.pi*i/half - np.pi/2
                    positions[i]       = [1.5*scale*np.cos(a), 1.5*scale*np.sin(a)]
                    positions[half+i]  = [0.6*scale*np.cos(a), 0.6*scale*np.sin(a)]
                self._apply_rotation(positions, rotation); return positions

        # Bipartite: two completely disjoint vertex sets
        if edges:
            left = set(); right = set()
            for f,t in edges: left.add(f); right.add(t)
            if not (left & right):
                ll = sorted(left); rl = sorted(right)
                for i,idx in enumerate(ll):
                    positions[idx] = [-(len(ll)-1)/2*scale + i*scale,  0.8*scale]
                for i,idx in enumerate(rl):
                    positions[idx] = [-(len(rl)-1)/2*scale + i*scale, -0.8*scale]
                for k,idx in enumerate(i for i in range(n) if i not in positions):
                    positions[idx] = [k*scale, -1.6*scale]
                self._apply_rotation(positions, rotation); return positions

        # Perfect-square grid
        gs = int(round(np.sqrt(n)))
        if gs*gs == n:
            for i in range(gs):
                for j in range(gs):
                    positions[i*gs+j] = [j*scale, -i*scale]
            self._apply_rotation(positions, rotation); return positions

        # Default circular
        for i in range(n):
            a = 2*np.pi*i/n - np.pi/2
            positions[i] = [scale*np.cos(a), scale*np.sin(a)]
        self._apply_rotation(positions, rotation)
        return positions

    @staticmethod
    def _apply_rotation(positions, rotation):
        if rotation == 0: return
        rad = np.radians(rotation); c, s = np.cos(rad), np.sin(rad)
        for idx in positions:
            x, y = positions[idx]
            positions[idx] = [x*c - y*s, x*s + y*c]

    # ── plot ──────────────────────────────────────────────────────────
    def plot(self, data: Any, options: Dict[str, Any]):
        plt.close('all')
        # Square figure avoids aspect-ratio clipping in any host widget size
        fig, ax = plt.subplots(figsize=(7, 7))
        fig.subplots_adjust(left=0.03, right=0.97, top=0.97, bottom=0.03)

        nodes         = data.get("nodes", [])
        edges         = data.get("edges", [])
        raw_pos       = data.get("positions", {})
        raw_el        = data.get("edge_labels", {})

        # Rebuild edge_labels with tuple keys
        edge_labels: Dict[Tuple[int,int], str] = {}
        for k, v in raw_el.items():
            pts = str(k).split(",")
            if len(pts) == 2:
                try: edge_labels[(int(pts[0]), int(pts[1]))] = v
                except ValueError: pass

        if not nodes:
            ax.text(0.5, 0.5, "No nodes to display.\nAdd nodes or load a graph.",
                    ha='center', va='center', fontsize=14,
                    transform=ax.transAxes, color='#6B7280')
            ax.axis('off'); return fig

        # ── read options ─────────────────────────────────────────
        node_color        = options.get('node_color',        'lightblue')
        node_stroke_color = options.get('node_stroke_color', 'black')
        node_stroke_width = options.get('node_stroke_width', 2.0)
        node_shape        = options.get('node_shape',        'circle')
        label_color       = options.get('label_color',       'black')
        edge_color        = options.get('edge_color',        'black')
        edge_width        = options.get('edge_width',        2.0)
        edge_style_opt    = options.get('edge_style',        'solid')
        node_size         = options.get('node_size',         0.5)
        font_size         = options.get('font_size',         10)
        rotation          = options.get('rotation_angle',    0.0)
        scale             = options.get('graph_scale',       1.0)
        show_labels       = options.get('show_labels',       True)
        show_edge_labels  = options.get('show_edge_labels',  True)
        show_grid         = options.get('show_grid',         False)
        show_axes         = options.get('show_axes',         False)
        is_directed       = options.get('directed',          False) or self.is_directed
        curved_edges      = options.get('curved_edges',      False)

        _ls = {'solid': '-', 'dashed': '--', 'dotted': ':'}
        linestyle = _ls.get(edge_style_opt, '-')

        self.current_node_color        = node_color
        self.current_node_stroke_color = node_stroke_color
        self.current_node_radius       = node_size * 0.12

        # ── positions ────────────────────────────────────────────
        stored = {int(k): v for k, v in raw_pos.items()}
        if stored and len(stored) == len(nodes):
            positions = {k: list(v) for k, v in stored.items()}
        else:
            positions = self.compute_layout(nodes, edges, rotation, scale)
        self.node_positions = {k: list(v) for k, v in positions.items()}

        node_circles:  Dict[int, Any] = {}
        node_labels_a: Dict[int, Any] = {}
        edge_lines:    Dict[Tuple[int,int], Any] = {}

        ax.set_aspect('equal')

        # ── edges ────────────────────────────────────────────────
        r = self.current_node_radius
        for fn, tn in edges:
            if fn >= len(nodes) or tn >= len(nodes): continue
            x1, y1 = positions[fn]; x2, y2 = positions[tn]

            if is_directed or curved_edges:
                conn = "arc3,rad=0.25" if curved_edges else "arc3,rad=0"
                arrow_style = '-|>' if is_directed else '-'
                patch = FancyArrowPatch(
                    (x1,y1),(x2,y2),
                    arrowstyle=arrow_style,
                    connectionstyle=conn,
                    mutation_scale=15,
                    color=edge_color,
                    linewidth=edge_width,
                    linestyle=linestyle,
                    zorder=1,
                    shrinkA=r*80, shrinkB=r*80
                )
                ax.add_patch(patch)
                edge_lines[(fn,tn)] = patch
            else:
                line, = ax.plot([x1,x2],[y1,y2],
                                color=edge_color,
                                linewidth=edge_width,
                                linestyle=linestyle,
                                zorder=1)
                edge_lines[(fn,tn)] = line

            # Edge label mid-point
            if show_edge_labels:
                lbl = edge_labels.get((fn,tn), edge_labels.get((tn,fn),""))
                if lbl:
                    ax.text((x1+x2)/2, (y1+y2)/2, lbl,
                            ha='center', va='bottom',
                            fontsize=max(font_size-2, 6), color=edge_color,
                            bbox=dict(boxstyle='round,pad=0.15',
                                      fc='white', ec='none', alpha=0.75),
                            zorder=4)

        # ── nodes ────────────────────────────────────────────────
        for i, label in enumerate(nodes):
            x, y = positions[i]
            if node_shape == 'square':
                patch = FancyBboxPatch(
                    (x-r, y-r), 2*r, 2*r,
                    boxstyle="square,pad=0",
                    facecolor=node_color, edgecolor=node_stroke_color,
                    linewidth=node_stroke_width, zorder=2)
            elif node_shape == 'rounded_square':
                patch = FancyBboxPatch(
                    (x-r, y-r), 2*r, 2*r,
                    boxstyle=f"round,pad=0,rounding_size={r*0.4}",
                    facecolor=node_color, edgecolor=node_stroke_color,
                    linewidth=node_stroke_width, zorder=2)
            else:
                patch = Circle(
                    (x, y), r,
                    facecolor=node_color, edgecolor=node_stroke_color,
                    linewidth=node_stroke_width, zorder=2)
            ax.add_patch(patch)
            node_circles[i] = patch

            if show_labels:
                txt = ax.text(x, y, label, ha='center', va='center',
                              fontsize=font_size, fontweight='bold',
                              color=label_color, zorder=3)
                node_labels_a[i] = txt

        # ── axis limits — 40 % margin so all nodes visible ───────
        all_x = [positions[i][0] for i in range(len(nodes))]
        all_y = [positions[i][1] for i in range(len(nodes))]
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)
        xspan = max(xmax - xmin, 1.0)
        yspan = max(ymax - ymin, 1.0)
        margin = 0.40
        ax.set_xlim(xmin - margin*xspan, xmax + margin*xspan)
        ax.set_ylim(ymin - margin*yspan, ymax + margin*yspan)

        # ── grid / axes ──────────────────────────────────────────
        if show_axes:
            ax.set_xlabel("x"); ax.set_ylabel("y")
            ax.tick_params(labelsize=8)
        else:
            ax.axis('off')

        if show_grid:
            ax.grid(True, linestyle='--', alpha=0.35)
            ax.set_axisbelow(True)
            if not show_axes:
                ax.axis('on')
                ax.set_xticklabels([]); ax.set_yticklabels([])
                ax.tick_params(left=False, bottom=False)

        self._plot_data = dict(
            ax=ax, positions=positions,
            node_circles=node_circles,
            node_labels=node_labels_a,
            edge_lines=edge_lines)
        return fig

    # ── interactive setup ─────────────────────────────────────────────
    def setup_interactive(self, canvas):
        if not self._plot_data: return
        if self.draggable_graph:
            self.draggable_graph.disconnect()
        self.draggable_graph = DraggableGraph(
            self._plot_data['ax'], canvas, self)
        self.draggable_graph.set_data(
            self._plot_data['positions'],
            self._plot_data['node_circles'],
            self._plot_data['node_labels'],
            self._plot_data['edge_lines'])

    # ── TikZ export ───────────────────────────────────────────────────
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        nodes = data.get("nodes", []); edges = data.get("edges", [])
        if not nodes: return "% No nodes defined"

        if self.draggable_graph and self.draggable_graph.positions:
            positions = self.draggable_graph.get_positions()
        elif self.node_positions:
            positions = self.node_positions
        else:
            positions = self.compute_layout(
                nodes, edges,
                options.get('rotation_angle', 0.0),
                options.get('graph_scale', 1.0))

        raw_el = data.get("edge_labels", {})
        edge_labels: Dict[Tuple[int,int],str] = {}
        for k, v in raw_el.items():
            pts = str(k).split(",")
            if len(pts)==2:
                try: edge_labels[(int(pts[0]),int(pts[1]))] = v
                except ValueError: pass

        tikz_zoom         = options.get('tikz_zoom',         2.5)
        node_color        = options.get('node_color',        'lightblue')
        node_stroke_color = options.get('node_stroke_color', 'black')
        node_stroke_width = options.get('node_stroke_width', 2.0)
        node_shape        = options.get('node_shape',        'circle')
        label_color       = options.get('label_color',       'black')
        edge_color        = options.get('edge_color',        'black')
        edge_width        = options.get('edge_width',        2.0)
        edge_style_opt    = options.get('edge_style',        'solid')
        node_size         = options.get('node_size',         0.5)
        show_labels       = options.get('show_labels',       True)
        show_edge_labels  = options.get('show_edge_labels',  True)
        is_directed       = options.get('directed',          False) or self.is_directed
        curved_edges      = options.get('curved_edges',      False)

        xs = [positions[i][0] for i in range(len(nodes))]
        ys = [positions[i][1] for i in range(len(nodes))]
        cx = (min(xs)+max(xs))/2; cy = (min(ys)+max(ys))/2
        span = max(max(xs)-min(xs), max(ys)-min(ys), 0.01)
        scaled = {i: ((positions[i][0]-cx)/span*tikz_zoom*2,
                      (positions[i][1]-cy)/span*tikz_zoom*2)
                  for i in range(len(nodes))}

        shape_map = {'circle': 'circle', 'square': 'rectangle',
                     'rounded_square': 'rounded corners'}
        tikz_shape = shape_map.get(node_shape, 'circle')
        ls_map = {'solid': '', 'dashed': 'dashed,', 'dotted': 'dotted,'}
        ls_str = ls_map.get(edge_style_opt, '')
        lw_pt  = edge_width * 0.5
        bend   = "bend left=20," if curved_edges else ""
        arrow  = f"->, {bend}" if is_directed else bend

        lines = [
            "\\begin{tikzpicture}[",
            "  every node/.style={font=\\small\\bfseries},",
        ]
        if is_directed:
            lines.append("  >={Stealth},")
        lines.append(
            f"  main node/.style={{{tikz_shape}, "
            f"draw={node_stroke_color}, line width={node_stroke_width*0.5:.1f}pt, "
            f"fill={node_color}, text={label_color}, "
            f"minimum size={node_size}cm, inner sep=1pt}}")
        lines += ["]", "", "% Nodes"]
        for i, label in enumerate(nodes):
            x, y = scaled[i]
            lbl = label if show_labels else ""
            lines.append(f"\\node[main node] (n{i}) at ({x:.3f},{y:.3f}) {{{lbl}}};")
        lines += ["", "% Edges"]
        for fn, tn in edges:
            if fn < len(nodes) and tn < len(nodes):
                lbl = edge_labels.get((fn,tn), edge_labels.get((tn,fn),""))
                elbl = (f" node[midway,above,font=\\tiny] {{{lbl}}}"
                        if lbl and show_edge_labels else "")
                lines.append(
                    f"\\draw[{arrow}{ls_str}{edge_color},"
                    f"line width={lw_pt:.1f}pt] (n{fn}) -- (n{tn}){elbl};")
        lines += ["", "\\end{tikzpicture}"]
        return "\n".join(lines)

    def get_tikz_libraries(self) -> List[str]:
        return ["tikz", "arrows.meta"]