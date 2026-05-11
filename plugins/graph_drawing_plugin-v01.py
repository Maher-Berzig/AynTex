# ============================================================================
# FILE: plugins/graph_drawing_plugin.py - INTERACTIVE VERSION WITH DYNAMIC EDGES
# ============================================================================
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QLineEdit, QGroupBox,
    QSpinBox, QMessageBox, QComboBox
)
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
from matplotlib.lines import Line2D
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin
matplotlib.rcParams['figure.max_open_warning'] = 50
class DraggableGraph:
    """
    Handles interactive node dragging with edges that follow the nodes.
    Edges remain connected to nodes as they are moved.
    """
    def __init__(self, ax, canvas, plugin):
        self.ax = ax
        self.canvas = canvas
        self.plugin = plugin
        self.dragging_node = None
        self.positions = {}  # {node_index: [x, y]}
        # Artist storage
        self.node_circles = {}   # {node_index: Circle patch}
        self.node_labels = {}    # {node_index: Text artist}
        self.edge_lines = {}     # {(from, to): Line2D or FancyArrowPatch}
        # Connect events
        self.cid_press = canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_release = canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = canvas.mpl_connect('motion_notify_event', self.on_motion)
    def disconnect(self):
        """Disconnect event handlers"""
        if self.canvas:
            try:
                self.canvas.mpl_disconnect(self.cid_press)
                self.canvas.mpl_disconnect(self.cid_release)
                self.canvas.mpl_disconnect(self.cid_motion)
            except:
                pass
    def set_data(self, positions, node_circles, node_labels, edge_lines):
        """Set the graph data and artist references"""
        self.positions = {k: list(v) for k, v in positions.items()}
        self.node_circles = node_circles
        self.node_labels = node_labels
        self.edge_lines = edge_lines
    def get_positions(self):
        """Return current node positions"""
        return {k: list(v) for k, v in self.positions.items()}
    def find_node_at(self, x, y):
        """Find which node (if any) is at the given coordinates"""
        if x is None or y is None:
            return None
        node_radius = self.plugin.current_node_radius
        for idx, (nx, ny) in self.positions.items():
            dist = np.sqrt((x - nx)**2 + (y - ny)**2)
            if dist < node_radius * 2:  # Generous click area
                return idx
        return None
    def on_press(self, event):
        """Handle mouse button press"""
        if event.inaxes != self.ax:
            return
        node_idx = self.find_node_at(event.xdata, event.ydata)
        if node_idx is not None:
            self.dragging_node = node_idx
            # Change cursor style to indicate dragging
            self.canvas.get_tk_widget().config(cursor="fleur") if hasattr(self.canvas, 'get_tk_widget') else None
    def on_release(self, event):
        """Handle mouse button release"""
        if self.dragging_node is not None:
            # Update plugin's stored positions
            self.plugin.node_positions = self.get_positions()
        self.dragging_node = None
    def on_motion(self, event):
        """Handle mouse motion - drag node and update connected edges"""
        if self.dragging_node is None:
            return
        if event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        idx = self.dragging_node
        new_x, new_y = event.xdata, event.ydata
        # Update position
        self.positions[idx] = [new_x, new_y]
        # Update node circle
        if idx in self.node_circles:
            self.node_circles[idx].center = (new_x, new_y)
        # Update node label
        if idx in self.node_labels:
            self.node_labels[idx].set_position((new_x, new_y))
        # Update all edges connected to this node
        self.update_edges_for_node(idx)
        # Redraw canvas
        self.canvas.draw_idle()
    def update_edges_for_node(self, node_idx):
        """Update all edges connected to the given node"""
        for (from_node, to_node), artist in self.edge_lines.items():
            if from_node == node_idx or to_node == node_idx:
                x1, y1 = self.positions[from_node]
                x2, y2 = self.positions[to_node]
                if isinstance(artist, Line2D):
                    # Update line endpoints
                    artist.set_data([x1, x2], [y1, y2])
                elif isinstance(artist, FancyArrowPatch):
                    # For arrows, we need to update the path
                    artist.set_positions((x1, y1), (x2, y2))
class GraphDrawingPlugin(PlotPlugin):
    """Interactive graph drawing plugin with draggable nodes"""
    name = "Graph Drawing"
    version = "2.3.0"
    category = "interactive"
    description = "Draw graphs with draggable nodes - edges follow node movement"
    requires_custom_ui = True
    CLASSIC_GRAPHS = {
        "Path P₅": {
            "nodes": ["1", "2", "3", "4", "5"],
            "edges": [(0,1), (1,2), (2,3), (3,4)],
            "description": "Path graph with 5 vertices"
        },
        "Cycle C₆": {
            "nodes": ["1", "2", "3", "4", "5", "6"],
            "edges": [(0,1), (1,2), (2,3), (3,4), (4,5), (5,0)],
            "description": "Cycle graph with 6 vertices"
        },
        "Star S₆": {
            "nodes": ["center", "1", "2", "3", "4", "5"],
            "edges": [(0,1), (0,2), (0,3), (0,4), (0,5)],
            "description": "Star graph with 6 vertices"
        },
        "Wheel W₆": {
            "nodes": ["hub", "1", "2", "3", "4", "5"],
            "edges": [(0,1), (0,2), (0,3), (0,4), (0,5), (1,2), (2,3), (3,4), (4,5), (5,1)],
            "description": "Wheel graph with 6 vertices"
        },
        "Complete K₄": {
            "nodes": ["A", "B", "C", "D"],
            "edges": [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)],
            "description": "Complete graph on 4 vertices"
        },
        "Complete K₅": {
            "nodes": ["A", "B", "C", "D", "E"],
            "edges": [(0,1), (0,2), (0,3), (0,4), (1,2), (1,3), (1,4), (2,3), (2,4), (3,4)],
            "description": "Complete graph on 5 vertices"
        },
        "Bipartite K₃,₃": {
            "nodes": ["A₁", "A₂", "A₃", "B₁", "B₂", "B₃"],
            "edges": [(0,3), (0,4), (0,5), (1,3), (1,4), (1,5), (2,3), (2,4), (2,5)],
            "description": "Complete bipartite graph (non-planar)"
        },
        "Cubical (3-Cube)": {
            "nodes": ["000", "001", "010", "011", "100", "101", "110", "111"],
            "edges": [(0,1), (0,2), (0,4), (1,3), (1,5), (2,3), (2,6), (3,7), (4,5), (4,6), (5,7), (6,7)],
            "description": "Cube graph"
        },
        "Petersen": {
            "nodes": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            "edges": [
                (0,1), (1,2), (2,3), (3,4), (4,0),
                (0,5), (1,6), (2,7), (3,8), (4,9),
                (5,7), (7,9), (9,6), (6,8), (8,5),
            ],
            "description": "Petersen graph"
        },
        "Binary Tree (depth 3)": {
            "nodes": ["root", "L", "R", "LL", "LR", "RL", "RR"],
            "edges": [(0,1), (0,2), (1,3), (1,4), (2,5), (2,6)],
            "description": "Complete binary tree"
        },
        "Grid 3×3": {
            "nodes": [f"({i},{j})" for i in range(3) for j in range(3)],
            "edges": [(0,1), (1,2), (3,4), (4,5), (6,7), (7,8), (0,3), (3,6), (1,4), (4,7), (2,5), (5,8)],
            "description": "3×3 Grid graph"
        },
        "Diamond": {
            "nodes": ["top", "left", "right", "bottom"],
            "edges": [(0,1), (0,2), (1,2), (1,3), (2,3)],
            "description": "Diamond graph (K₄ minus one edge)"
        },
        "House": {
            "nodes": ["roof", "left-top", "right-top", "left-bot", "right-bot"],
            "edges": [(0,1), (0,2), (1,2), (1,3), (2,4), (3,4)],
            "description": "House graph"
        },
    }
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.edges = []
        self.is_directed = False
        self.node_positions = {}
        # Current rendering settings
        self.current_node_radius = 0.1
        self.current_node_color = 'lightblue'
        self.current_node_stroke_color = 'black'
        self.current_edge_color = 'black'
        # Interactive handler
        self.draggable_graph = None
        # UI references
        self.custom_ui_widget = None
        self.node_list = None
        self.edge_list = None
        self.node_input = None
        self.edge_from = None
        self.edge_to = None
        self.graph_combo = None
        self.description_label = None
        self.nodes_group = None
        self.edges_group = None
        self.petersen_n = None
        self.petersen_k = None
    def get_plugin_name(self) -> str:
        return "Graph Drawing"
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "node_color": {
                "type": "str",
                "default": "lightblue",
                "label": "Node Fill Color"
            },
            # ----------------------------------------------------------------
            # NEW: stroke (border) color for nodes
            # ----------------------------------------------------------------
            "node_stroke_color": {
                "type": "str",
                "default": "black",
                "label": "Node Stroke Color"
            },
            "edge_color": {
                "type": "str",
                "default": "black",
                "label": "Edge Color"
            },
            "node_size": {
                "type": "float",
                "default": 0.5,
                "label": "Node Size",
                "min": 0.1,
                "max": 2.0
            },
            "font_size": {
                "type": "int",
                "default": 10,
                "label": "Label Font Size",
                "min": 6,
                "max": 20
            },
            "rotation_angle": {
                "type": "float",
                "default": 0.0,
                "label": "Rotation Angle (°)",
                "min": -360.0,
                "max": 360.0
            },
            "graph_scale": {
                "type": "float",
                "default": 1.0,
                "label": "Graph Scale",
                "min": 0.1,
                "max": 5.0
            },
            "tikz_zoom": {
                "type": "float",
                "default": 2.5,
                "label": "TikZ Zoom (cm)",
                "min": 0.5,
                "max": 10.0
            },
            "show_labels": {
                "type": "bool",
                "default": True,
                "label": "Show Node Labels"
            },
            "directed": {
                "type": "bool",
                "default": False,
                "label": "Directed Graph"
            }
        }
    def create_custom_ui(self, parent):
        """Create custom UI for graph drawing"""
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        layout.setSpacing(8)
        # === CLASSIC GRAPHS ===
        classic_group = QGroupBox("Load Classic Graph")
        classic_layout = QVBoxLayout(classic_group)
        # Petersen generator
        petersen_layout = QHBoxLayout()
        petersen_layout.addWidget(QLabel("Petersen P(n,k):"))
        self.petersen_n = QSpinBox()
        self.petersen_n.setRange(3, 20)
        self.petersen_n.setValue(5)
        petersen_layout.addWidget(QLabel("n="))
        petersen_layout.addWidget(self.petersen_n)
        self.petersen_k = QSpinBox()
        self.petersen_k.setRange(1, 10)
        self.petersen_k.setValue(2)
        petersen_layout.addWidget(QLabel("k="))
        petersen_layout.addWidget(self.petersen_k)
        btn_petersen = QPushButton("Generate")
        btn_petersen.clicked.connect(self.on_generate_petersen)
        petersen_layout.addWidget(btn_petersen)
        petersen_layout.addStretch()
        classic_layout.addLayout(petersen_layout)
        # Graph dropdown
        graph_layout = QHBoxLayout()
        graph_layout.addWidget(QLabel("Preset:"))
        self.graph_combo = QComboBox()
        self.graph_combo.addItem("-- Select --")
        for name in sorted(self.CLASSIC_GRAPHS.keys()):
            self.graph_combo.addItem(name)
        self.graph_combo.currentTextChanged.connect(self.on_classic_graph_selected)
        graph_layout.addWidget(self.graph_combo, 1)
        classic_layout.addLayout(graph_layout)
        self.description_label = QLabel("")
        self.description_label.setStyleSheet("color: gray; font-style: italic;")
        classic_layout.addWidget(self.description_label)
        btn_load = QPushButton("Load Selected Graph")
        btn_load.clicked.connect(self.on_load_classic_graph)
        classic_layout.addWidget(btn_load)
        layout.addWidget(classic_group)
        # === DRAG INFO ===
        info_box = QLabel("🖱️ Drag nodes in the preview to reposition them.\n"
                          "   Edges will follow automatically!")
        info_box.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                border: 1px solid #2196F3;
                border-radius: 5px;
                padding: 8px;
                color: #1565C0;
                font-weight: bold;
            }
        """)
        layout.addWidget(info_box)
        # === NODES ===
        self.nodes_group = QGroupBox(f"Nodes ({len(self.nodes)})")
        nodes_layout = QVBoxLayout(self.nodes_group)
        add_node_layout = QHBoxLayout()
        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("Node label")
        self.node_input.returnPressed.connect(self.on_add_node)
        add_node_layout.addWidget(self.node_input)
        btn_add_node = QPushButton("Add Node")
        btn_add_node.clicked.connect(self.on_add_node)
        add_node_layout.addWidget(btn_add_node)
        nodes_layout.addLayout(add_node_layout)
        # FIX: give the list a proper minimum height and make it visible
        self.node_list = QListWidget()
        self.node_list.setMinimumHeight(80)
        self.node_list.setMaximumHeight(120)
        nodes_layout.addWidget(self.node_list)
        btn_remove_node = QPushButton("Remove Selected Node")
        btn_remove_node.clicked.connect(self.on_remove_node)
        nodes_layout.addWidget(btn_remove_node)
        layout.addWidget(self.nodes_group)
        # === EDGES ===
        self.edges_group = QGroupBox(f"Edges ({len(self.edges)})")
        edges_layout = QVBoxLayout(self.edges_group)
        add_edge_layout = QHBoxLayout()
        add_edge_layout.addWidget(QLabel("From:"))
        self.edge_from = QSpinBox()
        self.edge_from.setMinimum(0)
        add_edge_layout.addWidget(self.edge_from)
        add_edge_layout.addWidget(QLabel("To:"))
        self.edge_to = QSpinBox()
        self.edge_to.setMinimum(0)
        add_edge_layout.addWidget(self.edge_to)
        btn_add_edge = QPushButton("Add Edge")
        btn_add_edge.clicked.connect(self.on_add_edge)
        add_edge_layout.addWidget(btn_add_edge)
        edges_layout.addLayout(add_edge_layout)
        # FIX: give the list a proper minimum height and make it visible
        self.edge_list = QListWidget()
        self.edge_list.setMinimumHeight(80)
        self.edge_list.setMaximumHeight(120)
        edges_layout.addWidget(self.edge_list)
        btn_remove_edge = QPushButton("Remove Selected Edge")
        btn_remove_edge.clicked.connect(self.on_remove_edge)
        edges_layout.addWidget(btn_remove_edge)
        layout.addWidget(self.edges_group)
        # === ACTIONS ===
        actions_layout = QHBoxLayout()
        btn_reset = QPushButton("Reset Layout")
        btn_reset.setToolTip("Reset nodes to default positions")
        btn_reset.clicked.connect(self.on_reset_layout)
        actions_layout.addWidget(btn_reset)
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self.on_clear_all)
        actions_layout.addWidget(btn_clear)
        layout.addLayout(actions_layout)
        layout.addStretch()
        # Populate lists with any existing data (e.g. after plugin reload)
        self.refresh_lists()
        return self.custom_ui_widget
    def on_reset_layout(self):
        """Reset to default layout positions"""
        self.node_positions.clear()
        if self.draggable_graph:
            self.draggable_graph.positions.clear()
        QMessageBox.information(self.custom_ui_widget, "Layout Reset",
                               "Node positions reset. Click 'Generate Preview' to apply.")
    def on_generate_petersen(self):
        """Generate generalized Petersen graph P(n,k)"""
        n = self.petersen_n.value()
        k = self.petersen_k.value()
        if k >= n // 2 + 1:
            QMessageBox.warning(self.custom_ui_widget, "Invalid",
                               f"For P(n,k), k should be ≤ n/2. Try k ≤ {n//2}")
            return
        self.nodes = [f"u{i}" for i in range(n)] + [f"v{i}" for i in range(n)]
        self.edges = []
        # Outer cycle
        for i in range(n):
            self.edges.append((i, (i + 1) % n))
        # Spokes
        for i in range(n):
            self.edges.append((i, n + i))
        # Inner star
        for i in range(n):
            self.edges.append((n + i, n + ((i + k) % n)))
        self.is_directed = False
        self.node_positions.clear()
        self.refresh_lists()
        QMessageBox.information(self.custom_ui_widget, "Generated",
                               f"Petersen P({n},{k}): {len(self.nodes)} nodes, {len(self.edges)} edges")
    def on_classic_graph_selected(self, text: str):
        """Update description when graph selected"""
        if text in self.CLASSIC_GRAPHS:
            self.description_label.setText(self.CLASSIC_GRAPHS[text].get("description", ""))
        else:
            self.description_label.setText("")
    def on_load_classic_graph(self):
        """Load the selected classic graph"""
        text = self.graph_combo.currentText()
        if text not in self.CLASSIC_GRAPHS:
            QMessageBox.warning(self.custom_ui_widget, "Error", "Please select a graph first.")
            return
        data = self.CLASSIC_GRAPHS[text]
        self.nodes = list(data["nodes"])
        self.edges = list(data["edges"])
        self.is_directed = data.get("directed", False)
        self.node_positions.clear()
        self.refresh_lists()
        QMessageBox.information(self.custom_ui_widget, "Loaded",
                               f"{text}: {len(self.nodes)} nodes, {len(self.edges)} edges")
    def on_add_node(self):
        """Add a new node"""
        label = self.node_input.text().strip()
        if not label:
            label = f"v{len(self.nodes)}"
        self.nodes.append(label)
        self.refresh_lists()
        self.node_input.clear()
        # FIX: scroll to the newly added item so the user sees it
        if self.node_list and self.node_list.count() > 0:
            self.node_list.scrollToBottom()
    def on_remove_node(self):
        """Remove selected node and its edges"""
        row = self.node_list.currentRow()
        if row < 0:
            return
        self.nodes.pop(row)
        # Remove edges connected to this node
        self.edges = [(f, t) for f, t in self.edges if f != row and t != row]
        # Adjust edge indices
        self.edges = [(f - 1 if f > row else f, t - 1 if t > row else t) for f, t in self.edges]
        # Adjust positions
        new_positions = {}
        for idx, pos in self.node_positions.items():
            if idx < row:
                new_positions[idx] = pos
            elif idx > row:
                new_positions[idx - 1] = pos
        self.node_positions = new_positions
        self.refresh_lists()
    def on_add_edge(self):
        """Add a new edge"""
        f = self.edge_from.value()
        t = self.edge_to.value()
        if f >= len(self.nodes) or t >= len(self.nodes):
            QMessageBox.warning(self.custom_ui_widget, "Error", "Invalid node indices.")
            return
        if (f, t) not in self.edges and (t, f) not in self.edges:
            self.edges.append((f, t))
            self.refresh_lists()
            # FIX: scroll to the newly added item so the user sees it
            if self.edge_list and self.edge_list.count() > 0:
                self.edge_list.scrollToBottom()
    def on_remove_edge(self):
        """Remove selected edge"""
        row = self.edge_list.currentRow()
        if row >= 0 and row < len(self.edges):
            self.edges.pop(row)
            self.refresh_lists()
    def on_clear_all(self):
        """Clear all nodes and edges"""
        self.nodes.clear()
        self.edges.clear()
        self.node_positions.clear()
        self.refresh_lists()
    def refresh_lists(self):
        """Refresh the UI lists"""
        if self.node_list is not None:
            self.node_list.clear()
            for i, label in enumerate(self.nodes):
                self.node_list.addItem(f"{i}: {label}")
            # FIX: force the widget to repaint so items appear immediately
            self.node_list.update()
            self.node_list.repaint()
        if self.edge_list is not None:
            self.edge_list.clear()
            arrow = "→" if self.is_directed else "—"
            for f, t in self.edges:
                fl = self.nodes[f] if f < len(self.nodes) else str(f)
                tl = self.nodes[t] if t < len(self.nodes) else str(t)
                self.edge_list.addItem(f"{f}({fl}) {arrow} {t}({tl})")
            # FIX: force the widget to repaint so items appear immediately
            self.edge_list.update()
            self.edge_list.repaint()
        if self.nodes_group is not None:
            self.nodes_group.setTitle(f"Nodes ({len(self.nodes)})")
        if self.edges_group is not None:
            self.edges_group.setTitle(f"Edges ({len(self.edges)})")
        max_idx = max(0, len(self.nodes) - 1)
        if self.edge_from is not None:
            self.edge_from.setMaximum(max_idx)
        if self.edge_to is not None:
            self.edge_to.setMaximum(max_idx)
    def get_custom_ui_data(self):
        """Get current graph data including positions"""
        # If we have a draggable handler, get updated positions from it
        if self.draggable_graph and self.draggable_graph.positions:
            self.node_positions = self.draggable_graph.get_positions()
        return {
            "nodes": self.nodes.copy(),
            "edges": self.edges.copy(),
            "positions": {k: list(v) for k, v in self.node_positions.items()}
        }
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if isinstance(data, dict) and "nodes" in data and "edges" in data:
            return True, ""
        return False, "Invalid graph data structure"
    def compute_layout(self, nodes, edges, rotation=0.0, scale=1.0):
        """Compute default node positions"""
        if not nodes:
            return {}
        n = len(nodes)
        positions = {}
        # Detect Petersen-type graphs
        is_petersen_type = False
        if n % 2 == 0 and n >= 6:
            half = n // 2
            outer_cycle = all(((i, (i+1) % half) in edges or ((i+1) % half, i) in edges) for i in range(half))
            spokes = all(((i, half + i) in edges or (half + i, i) in edges) for i in range(half))
            if outer_cycle and spokes:
                is_petersen_type = True
        # Detect bipartite K_m,n
        is_bipartite = "K₃,₃" in str(nodes) or "K₂,₄" in str(nodes)
        if is_petersen_type:
            half = n // 2
            for i in range(half):
                angle = 2 * np.pi * i / half - np.pi / 2
                positions[i] = [1.5 * scale * np.cos(angle), 1.5 * scale * np.sin(angle)]
            for i in range(half):
                angle = 2 * np.pi * i / half - np.pi / 2
                positions[half + i] = [0.6 * scale * np.cos(angle), 0.6 * scale * np.sin(angle)]
        elif is_bipartite and n == 6:
            # Two rows for bipartite
            for i in range(3):
                positions[i] = [(i - 1) * scale * 1.2, 0.8 * scale]
            for i in range(3):
                positions[3 + i] = [(i - 1) * scale * 1.2, -0.8 * scale]
        else:
            # Default circular layout
            for i in range(n):
                angle = 2 * np.pi * i / n - np.pi / 2
                positions[i] = [scale * np.cos(angle), scale * np.sin(angle)]
        # Apply rotation
        if rotation != 0:
            rad = np.radians(rotation)
            c, s = np.cos(rad), np.sin(rad)
            for idx in positions:
                x, y = positions[idx]
                positions[idx] = [x * c - y * s, x * s + y * c]
        return positions
    def plot(self, data: Any, options: Dict[str, Any]):
        """Generate the matplotlib plot with draggable nodes"""
        plt.close('all')
        fig, ax = plt.subplots(figsize=(10, 8))
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        stored_positions = data.get("positions", {})
        if not nodes:
            ax.text(0.5, 0.5, "No nodes to display.\nAdd nodes or load a graph.",
                   ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return fig
        # Get options
        node_color = options.get('node_color', 'lightblue')
        node_stroke_color = options.get('node_stroke_color', 'black')   # NEW
        edge_color = options.get('edge_color', 'black')
        node_size = options.get('node_size', 0.5)
        font_size = options.get('font_size', 10)
        rotation = options.get('rotation_angle', 0.0)
        scale = options.get('graph_scale', 1.0)
        show_labels = options.get('show_labels', True)
        is_directed = options.get('directed', False) or self.is_directed
        # Store for interactive handler
        self.current_node_color = node_color
        self.current_node_stroke_color = node_stroke_color             # NEW
        self.current_edge_color = edge_color
        self.current_node_radius = node_size * 0.12
        # Compute or use stored positions
        stored_positions = {int(k): v for k, v in stored_positions.items()}
        if stored_positions and len(stored_positions) == len(nodes):
            positions = {k: list(v) for k, v in stored_positions.items()}
        else:
            positions = self.compute_layout(nodes, edges, rotation, scale)
        # Store positions
        self.node_positions = {k: list(v) for k, v in positions.items()}
        # Artist dictionaries for interactive handler
        node_circles = {}
        node_labels = {}
        edge_lines = {}
        ax.set_aspect('equal')
        # Draw edges first (below nodes)
        for from_node, to_node in edges:
            if from_node >= len(nodes) or to_node >= len(nodes):
                continue
            x1, y1 = positions[from_node]
            x2, y2 = positions[to_node]
            if is_directed:
                arrow = FancyArrowPatch(
                    (x1, y1), (x2, y2),
                    arrowstyle='-|>',
                    mutation_scale=15,
                    color=edge_color,
                    linewidth=2,
                    zorder=1,
                    shrinkA=self.current_node_radius * 72,
                    shrinkB=self.current_node_radius * 72
                )
                ax.add_patch(arrow)
                edge_lines[(from_node, to_node)] = arrow
            else:
                line, = ax.plot([x1, x2], [y1, y2],
                               color=edge_color, linewidth=2, zorder=1)
                edge_lines[(from_node, to_node)] = line
        # Draw nodes
        for i, label in enumerate(nodes):
            x, y = positions[i]
            circle = Circle(
                (x, y), self.current_node_radius,
                facecolor=node_color,
                edgecolor=node_stroke_color,          # NEW: use stroke color
                linewidth=2,
                zorder=2
            )
            ax.add_patch(circle)
            node_circles[i] = circle
            if show_labels:
                text = ax.text(x, y, label, ha='center', va='center',
                              fontsize=font_size, fontweight='bold', zorder=3)
                node_labels[i] = text
        # Calculate axis limits with padding
        all_x = [positions[i][0] for i in range(len(nodes))]
        all_y = [positions[i][1] for i in range(len(nodes))]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        margin = 0.3
        x_range = max(x_max - x_min, 0.5)
        y_range = max(y_max - y_min, 0.5)
        ax.set_xlim(x_min - margin * x_range, x_max + margin * x_range)
        ax.set_ylim(y_min - margin * y_range, y_max + margin * y_range)
        ax.axis('off')
        # Store data for interactive setup
        self._plot_data = {
            'ax': ax,
            'positions': positions,
            'node_circles': node_circles,
            'node_labels': node_labels,
            'edge_lines': edge_lines
        }
        return fig
    def setup_interactive(self, canvas):
        """Setup interactive dragging after plot is created"""
        if not hasattr(self, '_plot_data') or not self._plot_data:
            return
        # Disconnect old handler
        if self.draggable_graph:
            self.draggable_graph.disconnect()
        # Create new handler
        self.draggable_graph = DraggableGraph(
            self._plot_data['ax'],
            canvas,
            self
        )
        self.draggable_graph.set_data(
            self._plot_data['positions'],
            self._plot_data['node_circles'],
            self._plot_data['node_labels'],
            self._plot_data['edge_lines']
        )
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        """Generate TikZ code using current node positions"""
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        if not nodes:
            return "% No nodes defined"
        # Get current positions (from draggable handler if available)
        if self.draggable_graph and self.draggable_graph.positions:
            positions = self.draggable_graph.get_positions()
        elif self.node_positions:
            positions = self.node_positions
        else:
            rotation = options.get('rotation_angle', 0.0)
            scale = options.get('graph_scale', 1.0)
            positions = self.compute_layout(nodes, edges, rotation, scale)
        # Options
        tikz_zoom = options.get('tikz_zoom', 2.5)
        node_color = options.get('node_color', 'lightblue')
        node_stroke_color = options.get('node_stroke_color', 'black')  # NEW
        edge_color = options.get('edge_color', 'black')
        node_size = options.get('node_size', 0.5)
        show_labels = options.get('show_labels', True)
        is_directed = options.get('directed', False) or self.is_directed
        # Normalize positions to fit TikZ scale
        all_x = [positions[i][0] for i in range(len(nodes))]
        all_y = [positions[i][1] for i in range(len(nodes))]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        max_range = max(x_max - x_min, y_max - y_min, 0.01)
        # Scale positions
        scaled = {}
        for i in range(len(nodes)):
            x = (positions[i][0] - x_center) / max_range * tikz_zoom * 2
            y = (positions[i][1] - y_center) / max_range * tikz_zoom * 2
            scaled[i] = (x, y)
        # Build TikZ code
        lines = []
        lines.append("\\begin{tikzpicture}[")
        lines.append("  every node/.style={font=\\small\\bfseries},")
        if is_directed:
            lines.append("  >={Stealth},")
        # NEW: include draw=<stroke> in the node style
        lines.append(
            f"  main node/.style={{circle, draw={node_stroke_color}, "
            f"fill={node_color}, minimum size={node_size}cm, inner sep=1pt}}"
        )
        lines.append("]")
        lines.append("")
        lines.append("% Nodes")
        for i, label in enumerate(nodes):
            x, y = scaled[i]
            label_text = label if show_labels else ""
            lines.append(f"\\node[main node] (n{i}) at ({x:.3f}, {y:.3f}) {{{label_text}}};")
        lines.append("")
        lines.append("% Edges")
        arrow = "->" if is_directed else ""
        for from_node, to_node in edges:
            if from_node < len(nodes) and to_node < len(nodes):
                lines.append(f"\\draw[{arrow}, {edge_color}, thick] (n{from_node}) -- (n{to_node});")
        lines.append("")
        lines.append("\\end{tikzpicture}")
        return "\n".join(lines)
    def get_tikz_libraries(self) -> List[str]:
        return ["tikz", "arrows.meta"]