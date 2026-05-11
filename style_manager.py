# style_manager.py
# ── Theme management ──────────────────────────────────────────────────────────

AVAILABLE_THEMES = {
    "default":   "Default (System)",
    "dark":      "Dark",
    "light":     "Light",
    "midnight":  "Midnight Blue",
}

AVAILABLE_THEMES_AR = {
    "default":   "افتراضي (النظام)",
    "dark":      "داكن",
    "light":     "فاتح",
    "midnight":  "أزرق منتصف الليل",
}

_current_theme = "default"
# ── Built-in themes (no extra pip package needed) ────────────────────────────

_MIDNIGHT_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
}
QMenuBar {
    background-color: #161b22;
    color: #c9d1d9;
    border-bottom: 1px solid #30363d;
}
QMenuBar::item:selected {
    background-color: #1f6feb;
}
QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
}
QMenu::item:selected {
    background-color: #1f6feb;
}
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    spacing: 3px;
}
QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #0d1117;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    border: 1px solid #30363d;
    padding: 5px 12px;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #c9d1d9;
    border-bottom-color: #0d1117;
}
QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
}
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 3px;
    padding: 4px 12px;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}
QPushButton:pressed {
    background-color: #1f6feb;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #0d1117;
    border: none;
    width: 10px;
    height: 10px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #8b949e;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 4px;
    margin-top: 8px;
    color: #c9d1d9;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    color: #58a6ff;
}
QCheckBox, QRadioButton, QLabel {
    color: #c9d1d9;
}
QHeaderView::section {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
}
QSplitter::handle {
    background-color: #30363d;
}
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
}
QToolTip {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #388bfd;
    padding: 3px;
}
"""
# ── Current active theme (updated by apply_theme) ────────────────────────────

def apply_theme(app, theme_name: str) -> bool:
    """Apply a theme to the QApplication."""
    global _current_theme
    app.setStyleSheet("")

    if theme_name == "default":
        app.setStyle("")
        _current_theme = "default"
        return True

    if theme_name in ("dark", "light"):
        try:
            import qdarkstyle
            from qdarkstyle.dark.palette  import DarkPalette
            from qdarkstyle.light.palette import LightPalette
            palette = DarkPalette if theme_name == "dark" else LightPalette
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=palette))
            _current_theme = theme_name
            return True
        except ImportError:
            return False

    if theme_name == "midnight":
        app.setStyleSheet(_MIDNIGHT_QSS)
        _current_theme = "midnight"
        return True

    return False


def get_button_style(variant: str = "normal") -> str:
    """
    Return a QPushButton stylesheet adapted to the current theme.
    
    variant:
        "normal"  — neutral action button  (was NORMAL_BUTTON)
        "green"   — confirm / insert button (was GREEN_BUTTON)  
        "red"     — destructive button      (was RED_BUTTON)
    """
    return _BUTTON_STYLES[_current_theme][variant]


# ── Button palettes per theme ─────────────────────────────────────────────────

def _make_buttons(
    bg_top, bg_bot,
    border, border_top, border_bot, border_l, border_r,
    text,
    h_bg_top, h_bg_bot,
    h_border, h_border_top, h_border_bot, h_border_l, h_border_r,
    h_text,
    p_bg_top, p_bg_bot,
    p_border, p_text,
    d_bg_top, d_bg_bot, d_border, d_text,
    blue_hover, green_hover, red_hover,
):
    def _btn(hover_top, hover_bot, hb, hb_top, hb_bot, hb_l, hb_r):
        return (
            "QPushButton {"
            #f" font-size: 14px; font-weight: bold; color: {text};"
            f" font-size: 14px; color: {text};"
            f" background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {bg_top}, stop:0.4 {bg_top}, stop:0.6 {bg_bot}, stop:1 {bg_bot});"
            f" border: 1px solid {border};"
            f" border-top-color: {border_top}; border-bottom-color: {border_bot};"
            f" border-left-color: {border_l}; border-right-color: {border_r};"
            " border-radius: 3px; padding: 4px 8px; text-align: center;"
            " }"

            " QPushButton:hover {"
            f" background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {hover_top}, stop:0.3 {hover_top}, stop:0.7 {hover_bot}, stop:1 {hover_bot});"
            f" border: 1px solid {hb};"
            f" border-top-color: {hb_top}; border-bottom-color: {hb_bot};"
            f" border-left-color: {hb_l}; border-right-color: {hb_r};"
            f" color: {h_text};"
            " }"

            " QPushButton:pressed {"
            f" background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {p_bg_top}, stop:1 {p_bg_bot});"
            f" border: 1px solid {p_border};"
            " padding: 5px 7px 3px 9px;"
            f" color: {p_text};"
            " }"

            " QPushButton:disabled {"
            f" color: {d_text};"
            f" background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {d_bg_top}, stop:1 {d_bg_bot});"
            f" border: 1px solid {d_border};"
            " }"
        )

    return {
        "normal": _btn(*blue_hover),
        "green":  _btn(*green_hover),
        "red":    _btn(*red_hover),
    }
    pressed_qss = f"""
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {p_bg_top}, stop:1 {p_bg_bot});
        border: 1px solid {p_border};
        padding: 5px 7px 3px 9px;
        color: {p_text};
    """
    disabled_qss = f"""
        color: {d_text};
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {d_bg_top}, stop:1 {d_bg_bot});
        border: 1px solid {d_border};
    """
    base_qss = f"""
        font-size: 14px;
        font-weight: bold;
        color: {text};
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {bg_top}, stop:0.4 {bg_top}, stop:0.6 {bg_bot}, stop:1 {bg_bot});
        border: 1px solid {border};
        border-top-color: {border_top};
        border-bottom-color: {border_bot};
        border-left-color: {border_l};
        border-right-color: {border_r};
        border-radius: 3px;
        padding: 4px 8px;
        text-align: center;
    """

    def _btn(hover_top, hover_bot, hb, hb_top, hb_bot, hb_l, hb_r):
        return f"""
QPushButton {{
    {base_qss}
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {hover_top}, stop:0.3 {hover_top}, stop:0.7 {hover_bot}, stop:1 {hover_bot});
    border: 1px solid {hb};
    border-top-color: {hb_top};
    border-bottom-color: {hb_bot};
    border-left-color: {hb_l};
    border-right-color: {hb_r};
    color: {h_text};
}}
QPushButton:pressed {{
    {pressed_qss}
}}
QPushButton:disabled {{
    {disabled_qss}
}}
"""

    return {
        "normal": _btn(*blue_hover),
        "green":  _btn(*green_hover),
        "red":    _btn(*red_hover),
    }


# Add this dict alongside _BUTTON_STYLES

_PANEL_STYLES = {
    "default":  {"bg": "#f0f0f0", "bg_btn": "#f0f0f0", "scroll_btn_bg": "#e0e0e0", "scroll_btn_border": "#cccccc", "scroll_btn_hover": "#d0d0d0"},
    "dark":     {"bg": "#2b2b2b", "bg_btn": "#19232d", "scroll_btn_bg": "#3c3f41", "scroll_btn_border": "#555759", "scroll_btn_hover": "#4c5052"},
    "light":    {"bg": "#f5f5f5", "bg_btn": "#c0c4c8", "scroll_btn_bg": "#e8e8e8", "scroll_btn_border": "#c0c0c0", "scroll_btn_hover": "#d8d8d8"},
    "midnight": {"bg": "#0d1117", "bg_btn": "#0d1117", "scroll_btn_bg": "#21262d", "scroll_btn_border": "#30363d", "scroll_btn_hover": "#30363d"},
}

def get_panel_style() -> dict:
    """Return background colors for the side panel matching the current theme."""
    return _PANEL_STYLES.get(_current_theme, _PANEL_STYLES["default"])

# ── Tree / Bookmarks widget styles ────────────────────────────────────────────
_TREE_WIDGET_STYLES = {
    "default": {
        "bg":            "#fafafa",
        "item_border":   "#eeeeee",
        "hover_bg":      "#e6f3ff",
        "selected_bg":   "#cce7ff",
        "selected_color":"#000000",
        "branch_color":  "#3498db",
        "header_bg":     "#f0f0f0",
        "header_color":  "#333333",
        "header_border": "#cccccc",
        "border":        "#cccccc",
    },
    "dark": {
        "bg":            "#2b2b2b",
        "item_border":   "#3c3f41",
        "hover_bg":      "#4c5052",
        "selected_bg":   "#4b6eaf",
        "selected_color":"#ffffff",
        "branch_color":  "#6d9fd8",
        "header_bg":     "#3c3f41",
        "header_color":  "#bbbbbb",
        "header_border": "#555759",
        "border":        "#555759",
    },
    "light": {
        "bg":            "#ffffff",
        "item_border":   "#e8e8e8",
        "hover_bg":      "#e3f0ff",
        "selected_bg":   "#b3d4ff",
        "selected_color":"#000000",
        "branch_color":  "#4a90d9",
        "header_bg":     "#f0f0f0",
        "header_color":  "#1a1a1a",
        "header_border": "#c0c0c0",
        "border":        "#c0c0c0",
    },
    "midnight": {
        "bg":            "#0d1117",
        "item_border":   "#21262d",
        "hover_bg":      "#21262d",
        "selected_bg":   "#1f6feb",
        "selected_color":"#ffffff",
        "branch_color":  "#388bfd",
        "header_bg":     "#161b22",
        "header_color":  "#c9d1d9",
        "header_border": "#30363d",
        "border":        "#30363d",
    },
}

# ── RTL menu CSS (appended to theme when Arabic is active) ───────────────────
_rtl_menu_active = False

_RTL_MENU_QSS = """
    QMenu {
        padding: 2px;
    }
    QMenu::item {
        padding-top:    4px;
        padding-bottom: 4px;
        padding-right:  28px;
        padding-left:   6px;
        margin:         0px;
    }
    QMenu::item:selected {
        background-color: palette(highlight);
        color:            palette(highlighted-text);
    }
    QMenu::item:checked:!selected {
        background: transparent;
    }
    QMenu::item:checked:selected {
        background-color: palette(highlight);
        color:            palette(highlighted-text);
    }
    QMenu::separator {
        height:        1px;
        background:    palette(mid);
        margin-top:    3px;
        margin-bottom: 3px;
    }
    QMenu::indicator { width: 0px; height: 0px; }
    QMenu::icon      { border: none; background: transparent; }
"""

def set_rtl_menu_active(is_rtl: bool):
    """Called by menu_manager when language changes."""
    global _rtl_menu_active
    _rtl_menu_active = is_rtl

# ── Settings-panel / info-section styles ─────────────────────────────────────
_SETTINGS_PANEL_STYLES = {
    "default": {
        "info_bg":          "#f0f0f0",
        "info_border":      "#cccccc",
        "info_color":       "#333333",
        "link_color":       "#0066cc",
        "help_color":       "#666666",
        "header_color":     "#333333",
        "section_bg":       "#f9f9f9",
        "section_border":   "#dddddd",
    },
    "dark": {
        "info_bg":          "#3c3f41",
        "info_border":      "#555759",
        "info_color":       "#bbbbbb",
        "link_color":       "#4a9fd8",
        "help_color":       "#888888",
        "header_color":     "#bbbbbb",
        "section_bg":       "#313335",
        "section_border":   "#555759",
    },
    "light": {
        "info_bg":          "#fafafa",
        "info_border":      "#c0c0c0",
        "info_color":       "#1a1a1a",
        "link_color":       "#1565c0",
        "help_color":       "#555555",
        "header_color":     "#1a1a1a",
        "section_bg":       "#f5f5f5",
        "section_border":   "#c8c8c8",
    },
    "midnight": {
        "info_bg":          "#161b22",
        "info_border":      "#30363d",
        "info_color":       "#c9d1d9",
        "link_color":       "#58a6ff",
        "help_color":       "#8b949e",
        "header_color":     "#c9d1d9",
        "section_bg":       "#0d1117",
        "section_border":   "#21262d",
    },
}

def get_tree_widget_style() -> dict:
    """Return theme-aware colors for QTreeWidget (document tree & bookmarks)."""
    return _TREE_WIDGET_STYLES.get(_current_theme, _TREE_WIDGET_STYLES["default"])

def get_settings_panel_style() -> dict:
    """Return theme-aware colors for settings panel widgets (info sections, help text)."""
    return _SETTINGS_PANEL_STYLES.get(_current_theme, _SETTINGS_PANEL_STYLES["default"])


_ERROR_STYLES = {
    "default":  {"bg": "#ffecec", "color": "#cc0000"},
    "light":    {"bg": "#ffecec", "color": "#cc0000"},
    "dark":     {"bg": "#3c1e1e", "color": "#19b4e3"},
    "midnight": {"bg": "#2d1717", "color": "#ff9999"},
}

def get_error_style() -> dict:
    """Return error text colours for the current theme."""
    return _ERROR_STYLES.get(_current_theme, _ERROR_STYLES["default"])

# ── Draggable button row styles (SidePanelSettingsWidget) ─────────────────────
_DRAGGABLE_ROW_STYLES = {
    "default": {
        "row_bg":          "#ffffff",
        "row_border":      "#dddddd",
        "row_hover_bg":    "#f8f8f8",
        "row_hover_border":"#999999",
        "drag_over_bg":    "#e0f0ff",
        "drag_over_border":"#0078d4",
        "handle_color":    "#888888",
        "handle_hover":    "#333333",
        "text_color":      "#333333",
    },
    "dark": {
        "row_bg":          "#3c3f41",
        "row_border":      "#555759",
        "row_hover_bg":    "#4c5052",
        "row_hover_border":"#8b949e",
        "drag_over_bg":    "#1e3a4f",
        "drag_over_border":"#4b6eaf",
        "handle_color":    "#888888",
        "handle_hover":    "#bbbbbb",
        "text_color":      "#bbbbbb",
    },
    "light": {
        "row_bg":          "#fafafa",
        "row_border":      "#cccccc",
        "row_hover_bg":    "#f0f0f0",
        "row_hover_border":"#888888",
        "drag_over_bg":    "#e3f0ff",
        "drag_over_border":"#4a90d9",
        "handle_color":    "#999999",
        "handle_hover":    "#333333",
        "text_color":      "#1a1a1a",
    },
    "midnight": {
        "row_bg":          "#161b22",
        "row_border":      "#30363d",
        "row_hover_bg":    "#21262d",
        "row_hover_border":"#8b949e",
        "drag_over_bg":    "#0d1f35",
        "drag_over_border":"#388bfd",
        "handle_color":    "#8b949e",
        "handle_hover":    "#c9d1d9",
        "text_color":      "#c9d1d9",
    },
}

def get_draggable_row_style() -> dict:
    """Return theme-aware colors for DraggableButtonRow."""
    return _DRAGGABLE_ROW_STYLES.get(_current_theme, _DRAGGABLE_ROW_STYLES["default"])

_BUTTON_STYLES = {

    # ── Default / light ───────────────────────────────────────────────────
    "default": _make_buttons(
        bg_top="#fefefe", bg_bot="#dfdfdf",
        border="#acacac", border_top="#c0c0c0", border_bot="#969696",
        border_l="#b0b0b0", border_r="#a0a0a0",
        text="#2d2d30",
        h_bg_top="#e6f3ff", h_bg_bot="#a8d4ff",
        h_border="#5c9ccc", h_border_top="#8fc4e8", h_border_bot="#4a8bc2",
        h_border_l="#6baed6", h_border_r="#5090c8",
        h_text="#1e1e1e",
        p_bg_top="#c8c8c8", p_bg_bot="#e4e4e4",
        p_border="#7a7a7a", p_text="#2d2d30",
        d_bg_top="#f8f8f8", d_bg_bot="#e8e8e8",
        d_border="#d0d0d0", d_text="#a0a0a0",
        blue_hover=("#e6f3ff","#a8d4ff","#5c9ccc","#8fc4e8","#4a8bc2","#6baed6","#5090c8"),
        green_hover=("#d6ffd6","#80ff80","#66cc66","#99e699","#4da64d","#80d680","#339933"),
        red_hover=("#ffd6d6","#ff8080","#e06666","#f29999","#cc6666","#e08080","#b34747"),
    ),

    # ── qdarkstyle dark ───────────────────────────────────────────────────
    "dark": _make_buttons(
        bg_top="#3c3f41", bg_bot="#2b2b2b",
        border="#555759", border_top="#606060", border_bot="#444444",
        border_l="#555555", border_r="#4a4a4a",
        text="#bbbbbb",
        h_bg_top="#4b6eaf", h_bg_bot="#2d5a8e",
        h_border="#6d9fd8", h_border_top="#8ab4e8", h_border_bot="#4a7fbf",
        h_border_l="#5e93cc", h_border_r="#3f78b5",
        h_text="#ffffff",
        p_bg_top="#1e1e1e", p_bg_bot="#2d2d2d",
        p_border="#3a3a3a", p_text="#bbbbbb",
        d_bg_top="#313335", d_bg_bot="#2b2b2b",
        d_border="#444444", d_text="#656565",
        blue_hover=("#4b6eaf","#2d5a8e","#6d9fd8","#8ab4e8","#4a7fbf","#5e93cc","#3f78b5"),
        green_hover=("#2d6e2d","#1a4d1a","#4a9e4a","#66b566","#357a35","#4a9e4a","#2d7a2d"),
        red_hover=("#8b2020","#6b1515","#cc4444","#dd6666","#aa3333","#bb4444","#993333"),
    ),

    # ── qdarkstyle light ──────────────────────────────────────────────────
    "light": _make_buttons(
        bg_top="#f5f5f5", bg_bot="#e0e0e0",
        border="#c0c0c0", border_top="#d0d0d0", border_bot="#b0b0b0",
        border_l="#c8c8c8", border_r="#b8b8b8",
        text="#1a1a1a",
        h_bg_top="#e3f0ff", h_bg_bot="#b3d4ff",
        h_border="#4a90d9", h_border_top="#7ab0e8", h_border_bot="#3070c0",
        h_border_l="#5a9fd6", h_border_r="#3d7ec8",
        h_text="#000000",
        p_bg_top="#d0d0d0", p_bg_bot="#e8e8e8",
        p_border="#909090", p_text="#1a1a1a",
        d_bg_top="#f0f0f0", d_bg_bot="#e4e4e4",
        d_border="#d0d0d0", d_text="#aaaaaa",
        blue_hover=("#e3f0ff","#b3d4ff","#4a90d9","#7ab0e8","#3070c0","#5a9fd6","#3d7ec8"),
        green_hover=("#d0f0d0","#90e090","#4aaa4a","#7acc7a","#2a882a","#5ab85a","#2a982a"),
        red_hover=("#ffd8d8","#ffaaaa","#cc4444","#ee8888","#aa2222","#dd6666","#bb3333"),
    ),

    # ── Midnight Blue ─────────────────────────────────────────────────────
    "midnight": _make_buttons(
        bg_top="#21262d", bg_bot="#161b22",
        border="#30363d", border_top="#3d444b", border_bot="#21262d",
        border_l="#30363d", border_r="#282e36",
        text="#c9d1d9",
        h_bg_top="#1f6feb", h_bg_bot="#1158c7",
        h_border="#388bfd", h_border_top="#58a6ff", h_border_bot="#1158c7",
        h_border_l="#388bfd", h_border_r="#1158c7",
        h_text="#ffffff",
        p_bg_top="#0d1117", p_bg_bot="#161b22",
        p_border="#21262d", p_text="#c9d1d9",
        d_bg_top="#161b22", d_bg_bot="#0d1117",
        d_border="#21262d", d_text="#484f58",
        blue_hover=("#1f6feb","#1158c7","#388bfd","#58a6ff","#1158c7","#388bfd","#1158c7"),
        green_hover=("#196c2e","#0f4a20","#2ea043","#56d364","#1a7f37","#2ea043","#196c2e"),
        red_hover=("#8b1a1a","#6b1010","#f85149","#ff7b72","#cf222e","#f85149","#b91c1c"),
    ),
}

# ── Backwards-compatible constants  ──────────────
# These let existing code that imports NORMAL_BUTTON / GREEN_BUTTON / RED_BUTTON


def NORMAL_BUTTON():
    return get_button_style("normal")

def GREEN_BUTTON():
    return get_button_style("green")

def RED_BUTTON():
    return get_button_style("red")
    
_WELCOME_STYLES = {
    "default": {
        "outer_bg":        "#ffffff",
        "outer_border":    "#a0a0a0",
        "inner_bg":        "#ffffff",
        "inner_border":    "#c0c0c0",
        "separator":       "#c0c0c0",
        "header_text":     "#333333",
        "link_color":      "#0066cc",
        "shortcut_color":  "#888888",
        "hover_bg":        "#e8f4fc",
        "no_files_color":  "#999999",
        "recent_hover":    "#e8f4fc",
        "tab_pane_bg":     "#f5f5f5",
    },
    "dark": {
        "outer_bg":        "#2b2b2b",
        "outer_border":    "#555759",
        "inner_bg":        "#2b2b2b",
        "inner_border":    "#444444",
        "separator":       "#555555",
        "header_text":     "#bbbbbb",
        "link_color":      "#4a9fd8",
        "shortcut_color":  "#777777",
        "hover_bg":        "#3c3f41",
        "no_files_color":  "#666666",
        "recent_hover":    "#3c3f41",
        "tab_pane_bg":     "#2b2b2b",
    },
    "light": {
        "outer_bg":        "#fafafa",
        "outer_border":    "#b0b0b0",
        "inner_bg":        "#fafafa",
        "inner_border":    "#cccccc",
        "separator":       "#cccccc",
        "header_text":     "#1a1a1a",
        "link_color":      "#1565c0",
        "shortcut_color":  "#909090",
        "hover_bg":        "#e3f0ff",
        "no_files_color":  "#aaaaaa",
        "recent_hover":    "#e3f0ff",
        "tab_pane_bg":     "#f0f0f0",
    },
    "midnight": {
        "outer_bg":        "#0d1117",
        "outer_border":    "#30363d",
        "inner_bg":        "#0d1117",
        "inner_border":    "#21262d",
        "separator":       "#30363d",
        "header_text":     "#c9d1d9",
        "link_color":      "#58a6ff",
        "shortcut_color":  "#484f58",
        "hover_bg":        "#161b22",
        "no_files_color":  "#484f58",
        "recent_hover":    "#161b22",
        "tab_pane_bg":     "#0d1117",
    },
}

_ANNOTATION_STYLES = {
    "default": {
        "toolbar_bg":      "#f0f0f0",
        "toolbar_border":  "#cccccc",
        "btn_border":      "#aaaaaa",
        "btn_hover":       "#e0e0e0",
        "btn_checked":     "#4CAF50",
        "btn_checked_hover": "#45a049",
        "sep_color":       "#aaaaaa",
        "label_color":     "#555555",
    },
    "dark": {
        "toolbar_bg":      "#3c3f41",
        "toolbar_border":  "#555759",
        "btn_border":      "#555759",
        "btn_hover":       "#4c5052",
        "btn_checked":     "#2d6e2d",
        "btn_checked_hover": "#357a35",
        "sep_color":       "#666666",
        "label_color":     "#bbbbbb",
    },
    "light": {
        "toolbar_bg":      "#f5f5f5",
        "toolbar_border":  "#c0c0c0",
        "btn_border":      "#c0c0c0",
        "btn_hover":       "#e8e8e8",
        "btn_checked":     "#3d9e3d",
        "btn_checked_hover": "#2d8e2d",
        "sep_color":       "#c0c0c0",
        "label_color":     "#444444",
    },
    "midnight": {
        "toolbar_bg":      "#161b22",
        "toolbar_border":  "#30363d",
        "btn_border":      "#30363d",
        "btn_hover":       "#21262d",
        "btn_checked":     "#196c2e",
        "btn_checked_hover": "#1a7f37",
        "sep_color":       "#30363d",
        "label_color":     "#8b949e",
    },
}
_AI_TAB_STYLES = {
    "default": {
        "body_bg": "#f5f5f5",         "body_color": "#333333",
        "msg_system_bg": "#e3f2fd",   "msg_system_border": "#0078d4",
        "msg_user_bg": "#fff9e6",     "msg_user_border": "#106ebe",
        "msg_assistant_bg": "#e8f5f3","msg_assistant_border": "#00b7c3",
        "label_system": "#0078d4",    "label_user": "#106ebe",
        "label_assistant": "#00b7c3",
        "code_bg": "#f4f4f4",         "code_color": "#c7254e",
        "pre_bg": "#2d2d2d",          "pre_color": "#f8f8f2",
        "strong_color": "#0078d4",
        "blockquote_border": "#0078d4","blockquote_bg": "#f9f9f9",
        "blockquote_color": "#555555",
        "table_header_bg": "#f5f5f5", "table_border": "#dddddd",
        "scrollbar_track": "#f1f1f1", "scrollbar_thumb": "#888888",
        "input_bg": "#ffffff",        "input_border": "#0078d4",
        "chat_border": "#dddddd",
        "group_border": "#0078d4",
        "tab_pane_bg": "#ffffff",     "tab_bg": "#e0e0e0",
        "tab_selected_bg": "#00b7c3", "tab_color": "#333333",
        "tab_selected_color": "#ffffff",
        "list_bg": "#ffffff",         "list_hover": "#f0f9ff",
        "list_selected": "#cce4ff",   "list_selected_color": "#000000",
        "action_btn_bg": "#ffffff",   "action_btn_border": "#0078d4",
        "action_btn_hover": "#e7f3ff",
        "sidebar_border": "#00b7c3",
    },
    "dark": {
        "body_bg": "#2b2b2b",         "body_color": "#bbbbbb",
        "msg_system_bg": "#1e3a4f",   "msg_system_border": "#4b6eaf",
        "msg_user_bg": "#3a3520",     "msg_user_border": "#6d9fd8",
        "msg_assistant_bg": "#1e3a35","msg_assistant_border": "#2d8f8f",
        "label_system": "#6ab0d8",    "label_user": "#6d9fd8",
        "label_assistant": "#4db8b8",
        "code_bg": "#3c3f41",         "code_color": "#ff7b72",
        "pre_bg": "#1e1e1e",          "pre_color": "#f8f8f2",
        "strong_color": "#6ab0d8",
        "blockquote_border": "#4b6eaf","blockquote_bg": "#1e1e1e",
        "blockquote_color": "#888888",
        "table_header_bg": "#3c3f41", "table_border": "#555759",
        "scrollbar_track": "#2b2b2b", "scrollbar_thumb": "#555759",
        "input_bg": "#3c3f41",        "input_border": "#4b6eaf",
        "chat_border": "#555759",
        "group_border": "#4b6eaf",
        "tab_pane_bg": "#2b2b2b",     "tab_bg": "#3c3f41",
        "tab_selected_bg": "#2d8f8f", "tab_color": "#bbbbbb",
        "tab_selected_color": "#ffffff",
        "list_bg": "#3c3f41",         "list_hover": "#4c5052",
        "list_selected": "#4b6eaf",   "list_selected_color": "#ffffff",
        "action_btn_bg": "#3c3f41",   "action_btn_border": "#4b6eaf",
        "action_btn_hover": "#4c5052",
        "sidebar_border": "#2d8f8f",
    },
    "light": {
        "body_bg": "#fafafa",         "body_color": "#1a1a1a",
        "msg_system_bg": "#e8f4ff",   "msg_system_border": "#4a90d9",
        "msg_user_bg": "#fffef0",     "msg_user_border": "#5a9fd6",
        "msg_assistant_bg": "#f0faf8","msg_assistant_border": "#3aacac",
        "label_system": "#1565c0",    "label_user": "#3070c0",
        "label_assistant": "#007a7a",
        "code_bg": "#f0f0f0",         "code_color": "#c7254e",
        "pre_bg": "#2d2d2d",          "pre_color": "#f8f8f2",
        "strong_color": "#1565c0",
        "blockquote_border": "#4a90d9","blockquote_bg": "#f5f5f5",
        "blockquote_color": "#444444",
        "table_header_bg": "#f0f0f0", "table_border": "#c0c0c0",
        "scrollbar_track": "#f0f0f0", "scrollbar_thumb": "#999999",
        "input_bg": "#ffffff",        "input_border": "#4a90d9",
        "chat_border": "#c0c0c0",
        "group_border": "#4a90d9",
        "tab_pane_bg": "#fafafa",     "tab_bg": "#e0e0e0",
        "tab_selected_bg": "#3aacac", "tab_color": "#333333",
        "tab_selected_color": "#ffffff",
        "list_bg": "#ffffff",         "list_hover": "#e3f0ff",
        "list_selected": "#b3d4ff",   "list_selected_color": "#000000",
        "action_btn_bg": "#ffffff",   "action_btn_border": "#4a90d9",
        "action_btn_hover": "#e3f0ff",
        "sidebar_border": "#3aacac",
    },
    "midnight": {
        "body_bg": "#0d1117",         "body_color": "#c9d1d9",
        "msg_system_bg": "#0d1f35",   "msg_system_border": "#388bfd",
        "msg_user_bg": "#1a1500",     "msg_user_border": "#58a6ff",
        "msg_assistant_bg": "#0d1f1a","msg_assistant_border": "#2ea043",
        "label_system": "#58a6ff",    "label_user": "#388bfd",
        "label_assistant": "#3fb950",
        "code_bg": "#161b22",         "code_color": "#ff7b72",
        "pre_bg": "#010409",          "pre_color": "#c9d1d9",
        "strong_color": "#58a6ff",
        "blockquote_border": "#388bfd","blockquote_bg": "#010409",
        "blockquote_color": "#8b949e",
        "table_header_bg": "#161b22", "table_border": "#30363d",
        "scrollbar_track": "#0d1117", "scrollbar_thumb": "#30363d",
        "input_bg": "#161b22",        "input_border": "#388bfd",
        "chat_border": "#30363d",
        "group_border": "#388bfd",
        "tab_pane_bg": "#0d1117",     "tab_bg": "#161b22",
        "tab_selected_bg": "#2ea043", "tab_color": "#c9d1d9",
        "tab_selected_color": "#ffffff",
        "list_bg": "#161b22",         "list_hover": "#21262d",
        "list_selected": "#1f6feb",   "list_selected_color": "#ffffff",
        "action_btn_bg": "#161b22",   "action_btn_border": "#388bfd",
        "action_btn_hover": "#21262d",
        "sidebar_border": "#2ea043",
    },
}

_COMPLETER_STYLES = {
    "default": {
        "cwl_bg": "#ffffff",  "cwl_border": "#cccccc",
        "ref_bg": "#fffef0",  "ref_border": "#e0d090",
        "text_color": "#2d2d30",
        "selected_bg": "#0078d4", "selected_color": "#ffffff",
    },
    "dark": {
        "cwl_bg": "#3c3f41",  "cwl_border": "#555759",
        "ref_bg": "#3a3520",  "ref_border": "#6b5f20",
        "text_color": "#bbbbbb",
        "selected_bg": "#4b6eaf", "selected_color": "#ffffff",
    },
    "light": {
        "cwl_bg": "#fafafa",  "cwl_border": "#c0c0c0",
        "ref_bg": "#fffef5",  "ref_border": "#d0c080",
        "text_color": "#1a1a1a",
        "selected_bg": "#4a90d9", "selected_color": "#ffffff",
    },
    "midnight": {
        "cwl_bg": "#161b22",  "cwl_border": "#30363d",
        "ref_bg": "#1a1500",  "ref_border": "#3d3000",
        "text_color": "#c9d1d9",
        "selected_bg": "#1f6feb", "selected_color": "#ffffff",
    },
}

_TOOLTIP_QSS = {
    "default":  "QToolTip { background-color: #ffffdc; color: #1e1e1e; border: 1px solid #aaaaaa; padding: 3px; }",
    "dark":     "QToolTip { background-color: #3c3f41; color: #bbbbbb; border: 1px solid #555759; padding: 3px; }",
    "light":    "QToolTip { background-color: #ffffff; color: #1a1a1a; border: 1px solid #b0b0b0; padding: 3px; }",
    "midnight": "",
}

def get_welcome_style() -> dict:
    """Return welcome page colors for the current theme."""
    return _WELCOME_STYLES.get(_current_theme, _WELCOME_STYLES["default"])

def get_annotation_style() -> dict:
    """Return annotation toolbar colors for the current theme."""
    return _ANNOTATION_STYLES.get(_current_theme, _ANNOTATION_STYLES["default"])    

def get_ai_tab_style() -> dict:
    """Return AI tab colors for the current theme."""
    return _AI_TAB_STYLES.get(_current_theme, _AI_TAB_STYLES["default"])

def get_tooltip_qss() -> str:
    """Return the QToolTip rule for the current theme, for embedding in widget stylesheets."""
    return _TOOLTIP_QSS.get(_current_theme, _TOOLTIP_QSS["default"])


from PyQt5.QtWidgets import QToolTip
from PyQt5.QtGui import QPalette, QColor

def get_completer_stylesheet(variant: str = "cwl") -> str:
    """Return a theme-aware stylesheet for QCompleter popups.
    variant: 'cwl' for command completion, 'ref' for \\ref/\\cite completion.
    """
    s = _COMPLETER_STYLES.get(_current_theme, _COMPLETER_STYLES["default"])
    bg     = s["cwl_bg"]    if variant == "cwl" else s["ref_bg"]
    border = s["cwl_border"] if variant == "cwl" else s["ref_border"]
    return f"""
        QListView {{
            background-color: {bg};
            color: {s['text_color']};
            border: 1px solid {border};
            font-family: Consolas, monospace;
            font-size: 11px;
        }}
        QListView::item {{
            padding: 3px 5px;
        }}
        QListView::item:selected {{
            background-color: {s['selected_bg']};
            color: {s['selected_color']};
        }}
    """
    



def _apply_tooltip_palette(app, theme_name: str):
    from PyQt5.QtGui import QPalette, QColor

    _colors = {
        "default":  ("#ffffdc", "#1e1e1e"),
        "dark":     ("#3c3f41", "#bbbbbb"),
        "light":    ("#ffffff", "#1a1a1a"),
        "midnight": ("#161b22", "#c9d1d9"),
    }

    bg_hex, fg_hex = _colors.get(theme_name, _colors["default"])
    palette = app.palette()
    palette.setColor(QPalette.ToolTipBase, QColor(bg_hex))
    palette.setColor(QPalette.ToolTipText, QColor(fg_hex))
    app.setPalette(palette)

    
def apply_theme(app, theme_name: str) -> bool:
    global _current_theme
    app.setStyleSheet("")

    base_qss = ""

    if theme_name == "default":
        app.setStyle("")
        base_qss = _TOOLTIP_QSS["default"]
        _apply_tooltip_palette(app, "default")
        _current_theme = "default"

    elif theme_name in ("dark", "light"):
        try:
            import qdarkstyle
            from qdarkstyle.dark.palette  import DarkPalette
            from qdarkstyle.light.palette import LightPalette
            palette = DarkPalette if theme_name == "dark" else LightPalette
            base_qss = qdarkstyle.load_stylesheet(palette=palette) + _TOOLTIP_QSS[theme_name]
            _apply_tooltip_palette(app, theme_name)
            _current_theme = theme_name
        except ImportError:
            return False

    elif theme_name == "midnight":
        base_qss = _MIDNIGHT_QSS
        _apply_tooltip_palette(app, "midnight")
        _current_theme = "midnight"

    else:
        return False

    # Always append RTL menu CSS last so it wins the cascade
    if _rtl_menu_active:
        base_qss += _RTL_MENU_QSS

    app.setStyleSheet(base_qss)
    return True    