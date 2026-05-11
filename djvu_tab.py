import os
import sys
import ctypes
import subprocess
import math
import configparser
from PyQt5.QtGui import (
    QPixmap, QTransform, QFont, QPainter, QColor, QPen, QCursor
)
base_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = base_dir + ";" + os.environ["PATH"]
dll_path = os.path.join(base_dir, "libdjvulibre.dll")
ddjvu = ctypes.CDLL(dll_path)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QToolBar, QAction, QScrollArea, QSplitter, QListWidget,
    QListWidgetItem, QComboBox, QSpinBox, QPushButton,
    QLineEdit, QCheckBox, QSizePolicy, QFrame, QApplication,
    QMessageBox, QScrollBar
)
from PyQt5.QtGui import (
    QPixmap, QTransform, QFont, QPainter, QColor, QPen, QCursor
)
from PyQt5.QtCore import (
    Qt, QRect, QSize, QPoint, QObject, QEvent, QThread, pyqtSignal, QTimer
)


def _djvu_run(*args, **kwargs):
    """Wrapper around subprocess.run that suppresses the console window on Windows."""
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.run(*args, **kwargs)

# ========== Background search worker (unchanged) ==========
class SearchWorker(QThread):
    progress = pyqtSignal(list, int, int)
    finished = pyqtSignal(list)
    def __init__(self, djvu_path, page_count, query, match_case, cache):
        super().__init__()
        self.djvu_path   = djvu_path
        self.page_count  = page_count
        self.query       = query
        self.match_case  = match_case
        self.cache       = cache
        self._abort      = False
    def abort(self):
        self._abort = True
    def _get_lines(self, pg):
        if pg in self.cache:
            return self.cache[pg]
        try:
            r = _djvu_run(
                ["djvutxt.exe", f"--page={pg}", self.djvu_path],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace"
            )
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        except Exception:
            lines = []
        self.cache[pg] = lines
        return lines
    def run(self):
        q   = self.query
        mc  = self.match_case
        res = []
        for pg in range(1, self.page_count + 1):
            if self._abort:
                break
            for ln in self._get_lines(pg):
                hit = (q in ln) if mc else (q.lower() in ln.lower())
                if hit:
                    res.append((pg, ln))
            self.progress.emit(list(res), pg, self.page_count)
        if not self._abort:
            self.finished.emit(res)

# ========== Selection overlay (unchanged) ==========
HANDLE_SIZE = 8
class SelectionOverlay(QWidget):
    NONE = 0; BODY = 1; N = 2; S = 3; W = 4; E = 5; NW = 6; NE = 7; SW = 8; SE = 9
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.hide()
        self._rect     = QRect()
        self._drag     = self.NONE
        self._drag_origin = QPoint()
        self._rect_at_drag = QRect()
    def set_rect(self, rect: QRect):
        self._rect = rect.normalized()
        self.update()
        self.show()
    def clear(self):
        self._rect = QRect()
        self.hide()
    def rect_selection(self) -> QRect:
        return self._rect.normalized()
    def _handle_rects(self):
        r = self._rect.normalized()
        cx = r.left() + r.width()  // 2
        cy = r.top()  + r.height() // 2
        h  = HANDLE_SIZE
        def sq(x, y): return QRect(x - h, y - h, 2*h, 2*h)
        return {
            self.NW: sq(r.left(),  r.top()),
            self.N:  sq(cx,        r.top()),
            self.NE: sq(r.right(), r.top()),
            self.W:  sq(r.left(),  cy),
            self.E:  sq(r.right(), cy),
            self.SW: sq(r.left(),  r.bottom()),
            self.S:  sq(cx,        r.bottom()),
            self.SE: sq(r.right(), r.bottom()),
        }
    def _hit_test(self, pos: QPoint) -> int:
        for zone, rect in self._handle_rects().items():
            if rect.contains(pos):
                return zone
        if self._rect.normalized().contains(pos):
            return self.BODY
        return self.NONE
    _CURSOR_MAP = {
        NONE: Qt.ArrowCursor,   BODY: Qt.SizeAllCursor,
        N:    Qt.SizeVerCursor, S:    Qt.SizeVerCursor,
        W:    Qt.SizeHorCursor, E:    Qt.SizeHorCursor,
        NW:   Qt.SizeFDiagCursor, SE: Qt.SizeFDiagCursor,
        NE:   Qt.SizeBDiagCursor, SW: Qt.SizeBDiagCursor,
    }
    def paintEvent(self, _event):
        if self._rect.isEmpty():
            return
        r = self._rect.normalized()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(r, QColor(30, 120, 255, 45))
        p.setPen(QPen(QColor(30, 100, 255, 220), 1, Qt.SolidLine))
        p.drawRect(r)
        p.setBrush(QColor(255, 255, 255, 230))
        p.setPen(QPen(QColor(30, 100, 255, 200), 1))
        for rect in self._handle_rects().values():
            p.drawRect(rect)
        p.end()
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._drag           = self._hit_test(event.pos())
        self._drag_origin    = event.pos()
        self._rect_at_drag   = self._rect.normalized()
        event.accept()
    def mouseMoveEvent(self, event):
        if self._drag == self.NONE:
            zone = self._hit_test(event.pos())
            self.setCursor(self._CURSOR_MAP.get(zone, Qt.ArrowCursor))
            return
        dx = event.pos().x() - self._drag_origin.x()
        dy = event.pos().y() - self._drag_origin.y()
        r  = QRect(self._rect_at_drag)
        d = self._drag
        if d == self.BODY:
            r.translate(dx, dy)
        elif d == self.N:
            r.setTop(r.top() + dy)
        elif d == self.S:
            r.setBottom(r.bottom() + dy)
        elif d == self.W:
            r.setLeft(r.left() + dx)
        elif d == self.E:
            r.setRight(r.right() + dx)
        elif d == self.NW:
            r.setTopLeft(r.topLeft() + QPoint(dx, dy))
        elif d == self.NE:
            r.setTopRight(r.topRight() + QPoint(dx, dy))
        elif d == self.SW:
            r.setBottomLeft(r.bottomLeft() + QPoint(dx, dy))
        elif d == self.SE:
            r.setBottomRight(r.bottomRight() + QPoint(dx, dy))
        self._rect = r
        self.update()
        event.accept()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = self.NONE
            event.accept()

class LabelMouseFilter(QObject):
    def __init__(self, viewer):
        super().__init__(viewer)
        self.viewer    = viewer
        self._drawing  = False
        self._start    = QPoint()
    def eventFilter(self, obj, event):
        v = self.viewer
        if not v.rect_tool_enabled:
            return False
        t = event.type()
        if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if (v.selection_overlay.isVisible() and
                    v.selection_overlay.geometry().contains(event.pos()) and
                    v.selection_overlay._hit_test(
                        event.pos() - v.selection_overlay.pos()) != SelectionOverlay.NONE):
                return False
            self._drawing = True
            self._start   = event.pos()
            v.selection_overlay.set_rect(QRect(self._start, QSize(1, 1)))
            return True
        if t == QEvent.MouseMove and self._drawing:
            v.selection_overlay.set_rect(
                QRect(self._start, event.pos()).normalized()
            )
            return True
        if t == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            v.selection_overlay.set_rect(
                QRect(self._start, event.pos()).normalized()
            )
            v._copy_current_selection()
            return True
        return False


# ========== Continuous View Widget ==========
class ContinuousPageWidget(QWidget):
    """Renders all pages stacked vertically for continuous scrolling.

    Uses a *virtual layout*: every page slot always has a known size so the
    scroll-bar geometry is correct even when only a small window of pages has
    been decoded.  Only pages present in ``_pixmap_cache`` (a dict mapping
    1-based page numbers to QPixmap) are painted; all other slots show a
    placeholder rectangle.
    """

    PAGE_GAP      = 12   # pixels between pages
    DEFAULT_W     = 1200 # fallback width  used before a page is decoded
    DEFAULT_H     = 1600 # fallback height used before a page is decoded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(80, 80, 80))
        self.setPalette(palette)

        # Public state – set by the viewer
        self._page_count  = 0
        self._pixmap_cache: dict = {}   # page_no (1-based) -> QPixmap (originals)
        self._page_sizes: dict  = {}    # page_no -> QSize of original pixmap
        self._zoom     = 100
        self._rotation = 0

        # Computed layout (rebuilt by _recompute_layout)
        self._page_rects: list = []     # index 0 = page 1
        self._total_height = 0
        self._max_width    = 0

    # ------------------------------------------------------------------
    # Public API used by DjvuTab
    # ------------------------------------------------------------------

    def setup(self, page_count: int, zoom: int, rotation: int):
        """Initialise / reinitialise for a new document or zoom/rotation change."""
        self._page_count  = page_count
        self._zoom        = zoom
        self._rotation    = rotation
        self._pixmap_cache.clear()
        self._page_sizes.clear()
        self._recompute_layout()

    def update_zoom_rotation(self, zoom: int, rotation: int):
        self._zoom     = zoom
        self._rotation = rotation
        self._recompute_layout()

    def put_page(self, page_no: int, pixmap: QPixmap):
        """Store a decoded pixmap and refresh the layout / repaint."""
        if pixmap.isNull():
            return
        self._pixmap_cache[page_no] = pixmap
        self._page_sizes[page_no]   = pixmap.size()
        # Re-layout only if the stored size changed (affects geometry)
        self._recompute_layout()
        rect = self.page_rect(page_no)
        if rect.isValid():
            self.update(rect.adjusted(-4, -4, 4, 4))   # repaint just this page

    def evict_pages(self, pages_to_keep):
        """Remove cached pixmaps for pages NOT in *pages_to_keep*."""
        to_drop = [pg for pg in list(self._pixmap_cache) if pg not in pages_to_keep]
        for pg in to_drop:
            del self._pixmap_cache[pg]
            # Keep _page_sizes so the layout stays correct

    def page_rect(self, page_no: int) -> QRect:
        idx = page_no - 1
        if 0 <= idx < len(self._page_rects):
            return self._page_rects[idx]
        return QRect()

    def page_at_y(self, y: int) -> int:
        """Return 1-based page number whose rect contains *y*, or -1."""
        for i, r in enumerate(self._page_rects):
            if r.top() <= y <= r.bottom():
                return i + 1
        # Fallback: nearest page above y
        best = 1
        for i, r in enumerate(self._page_rects):
            if r.top() <= y:
                best = i + 1
        return best

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_size(self, page_no: int) -> QSize:
        """Original (unscaled, unrotated) size of *page_no*."""
        if page_no in self._page_sizes:
            s = self._page_sizes[page_no]
            return s
        return QSize(self.DEFAULT_W, self.DEFAULT_H)

    def _scaled_size(self, page_no: int) -> QSize:
        base = self._base_size(page_no)
        if self._rotation in (90, 270):
            base_w, base_h = base.height(), base.width()
        else:
            base_w, base_h = base.width(), base.height()
        return QSize(int(base_w * self._zoom / 100),
                     int(base_h * self._zoom / 100))

    def _recompute_layout(self):
        if self._page_count == 0:
            self._page_rects   = []
            self._total_height = 0
            self._max_width    = 0
            self.resize(1, 1)
            return

        sizes = [self._scaled_size(pg) for pg in range(1, self._page_count + 1)]
        self._max_width = max((s.width() for s in sizes), default=self.DEFAULT_W)
        total_h = self.PAGE_GAP
        rects = []
        for sz in sizes:
            x = (self._max_width - sz.width()) // 2
            rects.append(QRect(x, total_h, sz.width(), sz.height()))
            total_h += sz.height() + self.PAGE_GAP
        self._page_rects   = rects
        self._total_height = total_h
        self.resize(self._max_width, self._total_height)
        self.update()

    def _render_page_pixmap(self, page_no: int, target_size: QSize) -> QPixmap:
        """Return a correctly-rotated, scaled pixmap for *page_no*, or null."""
        pm = self._pixmap_cache.get(page_no)
        if pm is None or pm.isNull():
            return QPixmap()
        if self._rotation != 0:
            pm = pm.transformed(QTransform().rotate(self._rotation),
                                Qt.SmoothTransformation)
        return pm.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        exposed = event.rect()
        try: 
            for idx, r in enumerate(self._page_rects):
                if not r.intersects(exposed):
                    continue
                page_no = idx + 1
                shadow = r.adjusted(3, 3, 3, 3)
                painter.fillRect(shadow, QColor(0, 0, 0, 60))

                scaled = self._render_page_pixmap(page_no, r.size())
                if not scaled.isNull():
                    painter.drawPixmap(r.topLeft(), scaled)
                else:
                    # Placeholder while the page is being decoded
                    painter.fillRect(r, QColor(240, 240, 240))
                    painter.setPen(QColor(160, 160, 160))
                    painter.drawRect(r)
                    painter.setPen(QColor(120, 120, 120))
                    painter.drawText(r, Qt.AlignCenter, f"Page {page_no}")
        finally:
            painter.end()


class ContinuousPageRenderer(QThread):
    """Background thread that renders a *window* of pages and emits them.

    Rendering starts at *focus_page* and expands outward (focus-1, focus+1,
    focus-2, focus+2, …) so that the pages the user is most likely to see
    are ready first.
    """
    page_ready = pyqtSignal(int, QPixmap)   # page_no (1-based), pixmap
    all_done   = pyqtSignal()

    def __init__(self, djvu_path: str, focus_page: int, pages_to_render: list,
                 temp_dir: str):
        super().__init__()
        self.djvu_path       = djvu_path
        self.focus_page      = focus_page
        self.pages_to_render = pages_to_render   # ordered list
        self.temp_dir        = temp_dir
        self._abort          = False

    def abort(self):
        self._abort = True

    # def run(self):
        # for pg in self.pages_to_render:
            # if self._abort:
                # return
            # tmp = os.path.join(self.temp_dir, f"cont_page_{pg}.ppm")
            # try:
                # _djvu_run(
                    # ["ddjvu.exe", "-format=ppm", "-size=1200x1600",
                     # f"-page={pg}", self.djvu_path, tmp],
                    # capture_output=True
                # )
                # pm = QPixmap(tmp)
                # if pm.isNull():
                    # pm = QPixmap()
            # except Exception:
                # pm = QPixmap()
            # if not self._abort:
                # self.page_ready.emit(pg, pm)
        # if not self._abort:
            # self.all_done.emit()

    def run(self):
        for pg in self.pages_to_render:
            if self._abort:
                return
            pm = QPixmap()
            try:
                result = _djvu_run(
                    ["ddjvu.exe", "-format=ppm", "-size=1200x1600",
                     f"-page={pg}", self.djvu_path],
                    capture_output=True,
                    check=True,
                    timeout=30
                )
                pm.loadFromData(result.stdout, "PPM")
            except Exception:
                pm = QPixmap()
            if not self._abort:
                self.page_ready.emit(pg, pm)
        if not self._abort:
            self.all_done.emit()

# ========== Main DjVu Tab Widget ==========
class DjvuTab(QWidget):
    app_name = "Ayntex"
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("DjVu Viewer")
        self.page            = 1
        self.page_count      = 1
        self.zoom            = 100
        self.rotation        = 0
        # temp file in config dir
        config_dir = self._get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        #self.temp_image = os.path.join(config_dir, "temp_page.ppm")
        self.original_pixmap = QPixmap()
        # Search
        self.search_results  = []
        self.search_index    = -1
        self.page_text_cache = {}
        self._search_worker  = None
        self._search_query   = ""
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._start_background_search)
        # Rect-select
        self.rect_tool_enabled = False
        # Hand tool
        self.hand_tool_enabled = False
        self._pan_active = False
        self._pan_start_pos = QPoint()
        self._pan_start_scrollbars = (0, 0)  # (horizontal, vertical) values
        
        # Continuous mode
        self._continuous_mode      = False
        # Windowed page cache: only CACHE_RADIUS pages on each side of the
        # current page are kept in memory.  Older pages are evicted to keep
        # RAM usage bounded.
        self.CACHE_RADIUS          = 2    # keep prev-2 … current … next+2
        self._cont_renderer        = None
        self._cont_scroll_timer    = QTimer(self)
        self._cont_scroll_timer.setSingleShot(True)
        self._cont_scroll_timer.timeout.connect(self._sync_page_from_scroll)
        # UI setup
        self._setup_ui()
        self.setAcceptDrops(True)
        self._drag_active = False
        self.toolbar_visible = True


    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Toolbar container with horizontal scroll
        toolbar_scroll = QScrollArea()
        toolbar_scroll.setWidgetResizable(True)
        toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        toolbar_scroll.setFrameShape(QFrame.NoFrame)
        toolbar_scroll.setStyleSheet("QScrollArea { background-color: white; border: none; }")
        self.toolbar_container = toolbar_scroll
        toolbar_widget = self._create_toolbar_widget()
        toolbar_scroll.setWidget(toolbar_widget)
        main_layout.addWidget(toolbar_scroll)

        # --- Splitter: sidebar + scroll area ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # Left panel (search results)
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(4, 4, 4, 4)
        self.results_label = QLabel("No search performed yet.")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet("color:#666;font-size:12px;padding:2px;")
        sidebar_layout.addWidget(self.results_label)
        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        self.results_list.itemClicked.connect(self._sidebar_item_clicked)
        sidebar_layout.addWidget(self.results_list)
        close_sidebar_btn = QPushButton("Close")
        close_sidebar_btn.clicked.connect(self.sidebar_widget.hide)
        sidebar_layout.addWidget(close_sidebar_btn)
        self.splitter.addWidget(self.sidebar_widget)
        self.sidebar_widget.hide()

        # Right area: stacked single-page scroll + continuous scroll
        # ---- Single-page view ----
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(1, 1)
        self.image_label.setMouseTracking(True)

        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ---- Continuous view ----
        self.cont_page_widget = ContinuousPageWidget()

        self.cont_scroll_area = QScrollArea()
        self.cont_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.cont_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cont_scroll_area.setWidgetResizable(False)
        self.cont_scroll_area.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.cont_scroll_area.setWidget(self.cont_page_widget)
        self.cont_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cont_scroll_area.hide()
        # Track scroll position changes to update page indicator
        self.cont_scroll_area.verticalScrollBar().valueChanged.connect(
            self._on_cont_scroll_changed)


        # After creating self.scroll_area and self.cont_scroll_area
        self.scroll_area.viewport().installEventFilter(self)
        self.cont_scroll_area.viewport().installEventFilter(self)

        # Put both into a container that switches between them
        self._view_container = QWidget()
        _vc_layout = QVBoxLayout(self._view_container)
        _vc_layout.setContentsMargins(0, 0, 0, 0)
        _vc_layout.setSpacing(0)
        _vc_layout.addWidget(self.scroll_area)
        _vc_layout.addWidget(self.cont_scroll_area)
        self._view_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.splitter.addWidget(self.sidebar_widget)   # already added above – skip
        # (already added sidebar above; now add view container)
        self.splitter.addWidget(self._view_container)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([0, 1])
        main_layout.addWidget(self.splitter, 1)

        # Selection overlay and event filter
        self.selection_overlay = SelectionOverlay(self.image_label)
        self._mouse_filter = LabelMouseFilter(self)
        self.image_label.installEventFilter(self._mouse_filter)
        self.image_label.installEventFilter(self)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Inside _setup_ui, after creating toolbar_scroll
        self.toolbar_widget = toolbar_widget   # store reference
        self.toolbar_container = toolbar_scroll   # store the scroll area that contains the toolbar
        self.toolbar_visible = True   # initial state        

    # ------------------------------------------------------------------ #
    #  Continuous mode helpers                                             #
    # ------------------------------------------------------------------ #
    def toggle_toolbar(self):
        """Toggle toolbar visibility."""
        self.set_toolbar_visible(not self.toolbar_visible)

    def set_toolbar_visible(self, visible):
        """Show/hide toolbar and force layout update."""
        if self.toolbar_visible == visible:
            return
        self.toolbar_visible = visible
        self.toolbar_container.setVisible(visible)
        # Force layout recalc
        self.toolbar_container.updateGeometry()
        # Notify parent window to relayout
        if self.parent():
            self.parent().layout().activate()
    
    def _enter_continuous_mode(self):
        self._continuous_mode = True
        self.scroll_area.hide()
        self.cont_scroll_area.show()
        self._rebuild_continuous_view()

    def _exit_continuous_mode(self):
        self._continuous_mode = False
        self.cont_scroll_area.hide()
        self.scroll_area.show()
        self._abort_cont_renderer()
        self.render_page()

    def _toggle_continuous_mode(self, checked):
        if checked:
            if self.rect_tool_enabled:
                self.rect_btn.setChecked(False) 
            self._enter_continuous_mode()
        else:
            self._exit_continuous_mode()

    # def _abort_cont_renderer(self):
        # if self._cont_renderer and self._cont_renderer.isRunning():
            # self._cont_renderer.abort()
            # self._cont_renderer.quit()
            # self._cont_renderer.wait(500)
        # self._cont_renderer = None

    def _abort_cont_renderer(self):
        if self._cont_renderer and self._cont_renderer.isRunning():
            self._cont_renderer.abort()
            self._cont_renderer.quit()
            for _ in range(20):
                if self._cont_renderer.wait(100):
                    break
                QApplication.processEvents()
            if self._cont_renderer.isRunning():
                self._cont_renderer.terminate()
                self._cont_renderer.wait(1000)
        self._cont_renderer = None

    # ------------------------------------------------------------------
    # Window helpers
    # ------------------------------------------------------------------

    def _window_pages(self, focus: int) -> list:
        """Return a list of page numbers within CACHE_RADIUS of *focus*."""
        lo = max(1, focus - self.CACHE_RADIUS)
        hi = min(self.page_count, focus + self.CACHE_RADIUS)
        return list(range(lo, hi + 1))

    def _ordered_render_pages(self, focus: int, pages_to_render: list) -> list:
        """Return *pages_to_render* ordered outward from *focus*."""
        ordered = sorted(pages_to_render, key=lambda pg: abs(pg - focus))
        return ordered

    # ------------------------------------------------------------------
    # Rebuild / renderer management
    # ------------------------------------------------------------------

    def _rebuild_continuous_view(self):
        """Initialise the widget for the current document and start rendering."""
        if not hasattr(self, "djvu_path"):
            return
        self._abort_cont_renderer()
        # Tell the widget about the new document (clears its cache)
        self.cont_page_widget.setup(self.page_count, self.zoom, self.rotation)
        QTimer.singleShot(50, self._scroll_to_current_page)
        # Kick off rendering for the initial window
        self._start_window_renderer(self.page)

    def _start_window_renderer(self, focus: int):
        """Abort any running renderer and start a new one for the window around *focus*."""
        self._abort_cont_renderer()
        window = self._window_pages(focus)
        # Only render pages not already in the widget's cache
        missing = [pg for pg in window
                   if pg not in self.cont_page_widget._pixmap_cache]
        if not missing:
            return
        ordered = self._ordered_render_pages(focus, missing)
        config_dir = self._get_config_dir()
        renderer = ContinuousPageRenderer(
            self.djvu_path, focus, ordered, config_dir
        )
        renderer.page_ready.connect(self._on_cont_page_ready)
        renderer.all_done.connect(self._on_cont_all_done)
        self._cont_renderer = renderer
        renderer.start()

    def _on_cont_page_ready(self, page_no: int, pixmap: QPixmap):
        """Receive a decoded page, store it, and evict pages outside the window."""
        self.cont_page_widget.put_page(page_no, pixmap)
        # Evict pages outside the current window to bound memory usage
        keep = set(self._window_pages(self.page))
        self.cont_page_widget.evict_pages(keep)

    def _on_cont_all_done(self):
        pass  # pages were delivered one-by-one via page_ready

    # ------------------------------------------------------------------
    # Scroll / sync helpers
    # ------------------------------------------------------------------

    # def _scroll_to_current_page(self):
        # r = self.cont_page_widget.page_rect(self.page)
        # if r.isValid():
            # self.cont_scroll_area.verticalScrollBar().setValue(r.top())

    def _scroll_to_current_page(self):
        if not hasattr(self, 'cont_page_widget'):
            return
        r = self.cont_page_widget.page_rect(self.page)
        if r.isValid():
            self.cont_scroll_area.verticalScrollBar().setValue(r.top())
        else:
            # If rect is invalid, rebuild the view (should rarely happen)
            self._rebuild_continuous_view()            

    def _on_cont_scroll_changed(self, value):
        """Debounce scroll events to avoid updating on every pixel."""
        self._cont_scroll_timer.start(80)

    def _sync_page_from_scroll(self):
        """Determine the most-visible page, update the indicator, and refresh
        the render window if the focus page has changed."""
        sb         = self.cont_scroll_area.verticalScrollBar()
        viewport_h = self.cont_scroll_area.viewport().height()
        mid_y      = sb.value() + viewport_h // 2
        pg         = self.cont_page_widget.page_at_y(mid_y)
        if pg < 1:
            pg = 1
        if pg != self.page:
            self.page = pg
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(pg)
            self.page_spinbox.blockSignals(False)
            # Start rendering the new window (eviction happens in _on_cont_page_ready)
            self._start_window_renderer(self.page)

    def _refresh_continuous_zoom_rotation(self):
        """Called when zoom or rotation changes while in continuous mode."""
        self.cont_page_widget.update_zoom_rotation(self.zoom, self.rotation)
        QTimer.singleShot(30, self._scroll_to_current_page)

    # ------------------------------------------------------------------ #
    #  Recent files                                                        #
    # ------------------------------------------------------------------ #
    def _get_recent_ini_path(self):
        config_dir = self._get_config_dir()
        return os.path.join(config_dir, "recent_djvu.ini")

    def _load_recent_files(self):
        ini = self._get_recent_ini_path()
        cfg = configparser.ConfigParser()
        cfg.read(ini, encoding="utf-8")
        files = []
        if "Recent" in cfg:
            for key in sorted(cfg["Recent"]):
                path = cfg["Recent"][key]
                if os.path.exists(path):
                    files.append(path)
        return files[:10]

    def _save_recent_files(self, files):
        ini = self._get_recent_ini_path()
        os.makedirs(os.path.dirname(ini), exist_ok=True)
        cfg = configparser.ConfigParser()
        cfg["Recent"] = {f"file{i}": p for i, p in enumerate(files[:10])}
        with open(ini, "w", encoding="utf-8") as f:
            cfg.write(f)

    def _add_to_recent(self, path):
        files = self._load_recent_files()
        if path in files:
            files.remove(path)
        files.insert(0, path)
        files = files[:10]
        self._save_recent_files(files)
        self._refresh_recent_combo()

        
    def _refresh_recent_combo(self):
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem("Recent files…")
        for path in self._load_recent_files():
            self.recent_combo.addItem(os.path.basename(path), userData=path)
        self.recent_combo.blockSignals(False)

    def _on_recent_selected(self, index):
        if index <= 0:
            return
        path = self.recent_combo.itemData(index)
        self.recent_combo.blockSignals(True)
        self.recent_combo.setCurrentIndex(0)
        self.recent_combo.blockSignals(False)
        if path and os.path.exists(path):
            self._open_djvu_file(path)
        else:
            QMessageBox.warning(self, "Not found", f"File no longer exists:\n{path}")
            files = self._load_recent_files()
            if path in files:
                files.remove(path)
            self._save_recent_files(files)
            self._refresh_recent_combo()

    # ------------------------------------------------------------------ #
    #  Drag-and-drop                                                       #
    # ------------------------------------------------------------------ #
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.djvu', '.djv')):
                    self._drag_active = True
                    self.update()
                    event.acceptProposedAction()
                    return
        event.ignore()

    # def dragLeaveEvent(self, event):
        # self._drag_active = False
        # self.update()
        # event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        self._drag_active = False
        self.update()
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        djvu_file = None
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.djvu', '.djv')):
                djvu_file = file_path
                break
        if djvu_file and os.path.exists(djvu_file):
            event.acceptProposedAction()
            self._open_djvu_file(djvu_file)
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drag_active:
            painter = QPainter(self)
            try:
                painter.fillRect(self.rect(), QColor(100, 150, 255, 30))
                painter.setPen(QPen(QColor(100, 150, 255), 3, Qt.DashLine))
                painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
            finally:
                painter.end()

    # ------------------------------------------------------------------ #
    #  Open file                                                           #
    # ------------------------------------------------------------------ #
    def _open_djvu_file(self, path):
        self.djvu_path = path
        self.page = 1
        self.search_results = []
        self.search_index = -1
        self.page_text_cache = {}
        self._search_query = ""
        # Clear any previous status bar message
        if self.main_window:
            self.main_window.update_status_bar(None, timeout=0, show_extras=False)
        self.sidebar_widget.hide()
        self._clear_selection()
        self._abort_worker()
        self._abort_cont_renderer()
        # Reset the continuous-view widget for the new document
        self.cont_page_widget.setup(0, self.zoom, self.rotation)
        self._add_to_recent(path)
        self.detect_page_count()
        #self.populate_pages()
        if self._continuous_mode:
            self._rebuild_continuous_view()
        else:
            self.render_page()

    # def eventFilter(self, obj, event):
        # if obj == self.image_label and event.type() == QEvent.Resize:
            # self._sync_overlay_size()
        # return super().eventFilter(obj, event)
        
    def eventFilter(self, obj, event):
        if obj == self.image_label and event.type() == QEvent.Resize:
            self._sync_overlay_size()        
        # Hand tool panning logic
        if self.hand_tool_enabled:
            # Determine which scroll area is the target
            scroll_area = None
            if obj == self.scroll_area.viewport():
                scroll_area = self.scroll_area
            elif obj == self.cont_scroll_area.viewport():
                scroll_area = self.cont_scroll_area
            if scroll_area:
                if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._pan_active = True
                    self._pan_start_pos = event.pos()
                    self._pan_start_scrollbars = (
                        scroll_area.horizontalScrollBar().value(),
                        scroll_area.verticalScrollBar().value()
                    )
                    # Set closed hand cursor
                    scroll_area.viewport().setCursor(Qt.ClosedHandCursor)
                    return True
                elif event.type() == QEvent.MouseMove and self._pan_active:
                    delta = event.pos() - self._pan_start_pos
                    new_h = self._pan_start_scrollbars[0] - delta.x()
                    new_v = self._pan_start_scrollbars[1] - delta.y()
                    scroll_area.horizontalScrollBar().setValue(new_h)
                    scroll_area.verticalScrollBar().setValue(new_v)
                    return True
                elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self._pan_active:
                    self._pan_active = False
                    self._update_hand_cursor()  # restore open hand
                    return True
                elif event.type() == QEvent.Leave:
                    if not self._pan_active:
                        self._update_hand_cursor()
                elif event.type() == QEvent.Enter:
                    if not self._pan_active:
                        self._update_hand_cursor()
        
        # Existing rect tool logic (if any) – make sure it doesn't interfere
        # For rect tool, we already have LabelMouseFilter; we keep that as is.
        # But we should avoid both tools active simultaneously.
        
        # Pass other events to the base implementation
        return super().eventFilter(obj, event)        

    def _update_hand_cursor(self):
        if not self.hand_tool_enabled:
            # Restore default cursor on both viewports
            self.scroll_area.viewport().setCursor(Qt.ArrowCursor)
            self.cont_scroll_area.viewport().setCursor(Qt.ArrowCursor)
            return
        # Set open hand cursor when tool is active but not dragging
        cursor = Qt.OpenHandCursor
        self.scroll_area.viewport().setCursor(cursor)
        self.cont_scroll_area.viewport().setCursor(cursor)

    def _sync_overlay_size(self):
        self.selection_overlay.setGeometry(0, 0,
            self.image_label.width(), self.image_label.height())

    # def _get_config_directory(self):
        # system = sys.platform.lower()
        # if system.startswith('win'):
            # appdata = os.environ.get('APPDATA')
            # if appdata:
                # return os.path.join(appdata, self.app_name)
            # return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', self.app_name)
        # elif system.startswith('darwin'):
            # return os.path.join(os.path.expanduser('~'), 'Library',
                                # 'Application Support', self.app_name)
        # else:
            # xdg = os.environ.get('XDG_CONFIG_HOME')
            # if xdg:
                # return os.path.join(xdg, self.app_name)
            # return os.path.join(os.path.expanduser('~'), '.config', self.app_name)
            
    def _get_config_dir(self):
        """Return the configuration directory from the main window's ConfigManager."""
        if self.main_window and hasattr(self.main_window, 'config_manager'):
            return self.main_window.config_manager.config_dir
        # Fallback (should not happen in normal usage)
        return os.path.join(os.path.expanduser('~'), '.config', self.app_name)            

    # ------------------------------------------------------------------ #
    #  Toolbar                                                             #
    # ------------------------------------------------------------------ #
    def _create_toolbar_widget(self):
        """Create a two-row toolbar widget with grouped functions."""
        main_window = self.get_main_window()
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(4, 8, 4, 8)
        main_layout.setSpacing(4)

        # ----- Row 1: File & Selection tools -----
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(6)

        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.open_file)
        open_btn.setFixedWidth(60)
        open_btn.setToolTip("Open djvu file")
        row1_layout.addWidget(open_btn)

        self.recent_combo = QComboBox()       
        self.recent_combo.setMinimumWidth(100)
        self.recent_combo.setMaximumWidth(200)
        self.recent_combo.setToolTip("Open a recently viewed file")
        self._refresh_recent_combo()
        self.recent_combo.currentIndexChanged.connect(self._on_recent_selected)
        self.recent_combo.highlighted[int].connect(self._on_recent_highlighted_index)
        row1_layout.addWidget(self.recent_combo)
        row1_layout.addWidget(self._separator())

        prev_btn = QPushButton("◀")
        prev_btn.clicked.connect(self.prev_page)
        prev_btn.setToolTip("Previous page")
        row1_layout.addWidget(prev_btn)

        self.page_spinbox = QSpinBox()
        self.page_spinbox.setButtonSymbols(QSpinBox.NoButtons)
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(max(1, self.page_count))  # will update later
        self.page_spinbox.setValue(1)        
        self.page_spinbox.setToolTip("Enter page number (1-based)")
        self.page_spinbox.setMinimumWidth(70)
        self.page_spinbox.setMaximumWidth(100)
        self.page_spinbox.setAlignment(Qt.AlignCenter)
        #self.page_spinbox.setButtonSymbols(QSpinBox.UpDownArrows)  # show +/- buttons
        self.page_spinbox.valueChanged.connect(self._page_spinbox_changed)
        row1_layout.addWidget(self.page_spinbox)        
        
        
        next_btn = QPushButton("▶")
        next_btn.clicked.connect(self.next_page)
        next_btn.setToolTip("Next page")
        row1_layout.addWidget(next_btn)
        row1_layout.addWidget(self._separator())

        copy_page_btn = QPushButton("")
        main_window.icons_manager.apply_icon_to_button(copy_page_btn, "copy_p")
        copy_page_btn.clicked.connect(self.copy_page)
        copy_page_btn.setFixedWidth(40)
        copy_page_btn.setToolTip("Copy the entire page as image")
        row1_layout.addWidget(copy_page_btn)

        self.copy_sel_btn = QPushButton("")
        main_window.icons_manager.apply_icon_to_button(self.copy_sel_btn, "copy_s")
        self.copy_sel_btn.clicked.connect(self._copy_current_selection)
        self.copy_sel_btn.setFixedWidth(40)
        self.copy_sel_btn.setToolTip("Copy selected rectangle as image")
        self.copy_sel_btn.setEnabled(False)
        row1_layout.addWidget(self.copy_sel_btn)

        self.copy_text_btn = QPushButton("")
        main_window.icons_manager.apply_icon_to_button(self.copy_text_btn, "select_t")
        self.copy_text_btn.clicked.connect(self._copy_selected_text)
        self.copy_text_btn.setFixedWidth(40)
        self.copy_text_btn.setToolTip("Copy text from selection")
        self.copy_text_btn.setEnabled(False)
        row1_layout.addWidget(self.copy_text_btn)

        self.rect_btn = QPushButton("")
        main_window.icons_manager.apply_icon_to_button(self.rect_btn, "select_text")
        self.rect_btn.setCheckable(True)
        self.rect_btn.toggled.connect(self._toggle_rect_tool)
        self.rect_btn.setFixedWidth(40)
        self.rect_btn.setToolTip("Select text with a resizable rectangle")
        row1_layout.addWidget(self.rect_btn)

        clear_sel_btn = QPushButton("")
        main_window.icons_manager.apply_icon_to_button(clear_sel_btn, "clear_page")
        clear_sel_btn.clicked.connect(self._clear_selection)
        clear_sel_btn.setFixedWidth(40)
        clear_sel_btn.setToolTip("Delete the selection rectangle")
        row1_layout.addWidget(clear_sel_btn)

        row1_layout.addStretch()
        main_layout.addWidget(row1)

        # ----- Row 2: Zoom, Fit, Rotation, Continuous, Search -----
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(6)

        zoom_out_btn = QPushButton("−")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setToolTip("Zoom out")
        row2_layout.addWidget(zoom_out_btn)

        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(10, 400)
        self.zoom_spin.setValue(100)
        self.zoom_spin.setSuffix(" %")
        self.zoom_spin.valueChanged.connect(self.set_zoom)
        self.zoom_spin.setButtonSymbols(QSpinBox.NoButtons)
        row2_layout.addWidget(self.zoom_spin)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setToolTip("Zoom in")
        row2_layout.addWidget(zoom_in_btn)
        row2_layout.addWidget(self._separator())

        fit_width_btn = QPushButton("↔")
        fit_width_btn.clicked.connect(self.fit_width)
        fit_width_btn.setToolTip("Fit width")
        row2_layout.addWidget(fit_width_btn)

        fit_page_btn = QPushButton("↕")
        fit_page_btn.clicked.connect(self.fit_page)
        fit_page_btn.setToolTip("Fit page")
        row2_layout.addWidget(fit_page_btn)
        
        
        hand_btn = QPushButton("✋")
        self.hand_btn = hand_btn
        hand_btn.setCheckable(True)
        hand_btn.toggled.connect(self._toggle_hand_tool)        
        hand_btn.setToolTip("Pan the view (drag to scroll in any direction)")
        row2_layout.addWidget(hand_btn)        

        # ---- Continuous scroll button (NEW) ----
        #row2_layout.addWidget(self._separator())
        cont_btn = QPushButton("📜")        
        self.cont_btn = cont_btn 
        cont_btn.setCheckable(True)        
        cont_btn.setToolTip(
            "Continuous scroll: display all pages stacked vertically.\n"
            "Scroll the mouse wheel to move between pages seamlessly."
        )
        cont_btn.toggled.connect(self._toggle_continuous_mode)
        # Style it to stand out a little when checked
        cont_btn.setStyleSheet(
            "QPushButton {color: gray; font-size: 14px; letter-spacing: 1px; }"
            "QPushButton:checked { background-color: green; color: green; font-weight: bold; }"
            
        )
        row2_layout.addWidget(cont_btn)
        #row2_layout.addWidget(self._separator())

        rotate_left_btn  = QPushButton("⟲")
        rotate_left_btn.clicked.connect(lambda: self.rotate(-90))
        rotate_left_btn.setToolTip("Rotate left")
        row2_layout.addWidget(rotate_left_btn)

        rotate_right_btn = QPushButton("⟳")
        rotate_right_btn.clicked.connect(lambda: self.rotate(90))
        rotate_right_btn.setToolTip("Rotate right")
        row2_layout.addWidget(rotate_right_btn)
        row2_layout.addWidget(self._separator())

        search_prev_btn = QPushButton("◀?")
        search_prev_btn.clicked.connect(self.search_prev)
        search_prev_btn.setToolTip("Previous search result")
        row2_layout.addWidget(search_prev_btn)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search text…")
        self.search_field.setMinimumWidth(180)
        self.search_field.setMaximumWidth(240)
        self.search_field.returnPressed.connect(self.search_next)
        self.search_field.textChanged.connect(self._on_query_changed)
        row2_layout.addWidget(self.search_field)

        search_next_btn = QPushButton("?▶")
        search_next_btn.clicked.connect(self.search_next)
        search_next_btn.setToolTip("Next search result")
        row2_layout.addWidget(search_next_btn)

        find_all_btn = QPushButton("All")
        find_all_btn.clicked.connect(self.find_all)
        find_all_btn.setFixedWidth(30)
        find_all_btn.setToolTip("Find all matches")
        row2_layout.addWidget(find_all_btn)

        self.match_case_cb = QCheckBox("Aa")
        self.match_case_cb.setToolTip("Match case")
        self.match_case_cb.stateChanged.connect(self._on_query_changed)
        row2_layout.addWidget(self.match_case_cb)

        btn_width = 25
        for btn in (prev_btn, next_btn, fit_width_btn, fit_page_btn,
                    search_next_btn, search_prev_btn, hand_btn, 
                    rotate_left_btn, rotate_right_btn, cont_btn,
                    zoom_in_btn, zoom_out_btn):
            btn.setFixedWidth(btn_width)

        # Status bar label removed – status will be shown in main window's status bar
        row2_layout.addStretch()
        main_layout.addWidget(row2)

        container.setMinimumHeight(80)
        return container


    def _page_spinbox_changed(self, value):
        """Called when user changes spinbox value (typed or arrows)."""
        # Clamp to valid range (spinbox already enforces min/max, but double-check)
        if value < 1 or value > self.page_count:
            return
        if value != self.page:
            self.page = value            
            if self._continuous_mode:
                self._scroll_to_current_page()
            else:
                self.render_page()

    def get_main_window(self):
        """Return the main window reference."""
        return self.main_window
    
    def _on_recent_highlighted_index(self, index):
        """Show full path of highlighted recent file in status bar using index."""
        if not self.main_window:
            return
        if index == 0:  # "Recent files…" item
            self.main_window.update_status_bar("Select a recently opened file", 2000)
            return
        # Get the full path stored as user data
        path = self.recent_combo.itemData(index)
        if path and isinstance(path, str):
            self.main_window.update_status_bar(path, 3000)
        else:
            # Fallback: show the displayed basename
            text = self.recent_combo.itemText(index)
            self.main_window.update_status_bar(f"File: {text}", 2000)
        def get_main_window(self):
            parent = self.parent()
            while parent:
                if hasattr(parent, 'editor_manager'):
                    return parent
                parent = parent.parent()
            return None

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setFixedWidth(2)
        return line

    # ------------------------------------------------------------------ #
    #  Search sidebar                                                      #
    # ------------------------------------------------------------------ #
    def _populate_sidebar(self, query):
        self.results_list.clear()
        if not self.search_results:
            self.results_label.setText(f'No results for "{query}".')
            self.sidebar_widget.show()
            total = self.splitter.width()
            self.splitter.setSizes([200, total - 200])
            return
        self.results_label.setText(f'{len(self.search_results)} occurrence(s) of "{query}":')
        for idx, (pg, line_text) in enumerate(self.search_results):
            preview = line_text.strip()[:60] or f"(page {pg})"
            item = QListWidgetItem(f"  p.{pg}  {preview}")
            item.setData(Qt.UserRole, idx)
            item.setFont(QFont("Monospace", 9))
            item.setToolTip(line_text.strip())
            self.results_list.addItem(item)
        self.sidebar_widget.show()
        total = self.splitter.width()
        self.splitter.setSizes([max(200, total // 3), total - max(200, total // 3)])

    def _sidebar_item_clicked(self, item):
        idx = item.data(Qt.UserRole)
        if idx is None:
            return
        self.search_index = idx
        pg, line_text = self.search_results[idx]
        self.page = pg
        self._update_search_status()
        if self._continuous_mode:
            self._scroll_to_current_page()
        else:
            self.render_page(highlight_line=line_text)

    # ------------------------------------------------------------------ #
    #  File handling                                                       #
    # ------------------------------------------------------------------ #
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open DjVu", "", "DjVu Files (*.djvu *.djv)")
        if not path:
            return
        self.djvu_path       = path
        self.page            = 1
        self.search_results  = []
        self.search_index    = -1
        self.page_text_cache = {}
        self._search_query   = ""
        if self.main_window:
            self.main_window.update_status_bar(None, timeout=0, show_extras=False)
        self.sidebar_widget.hide()
        self._clear_selection()
        self._abort_worker()
        self._abort_cont_renderer()
        # Reset the continuous-view widget for the new document
        self.cont_page_widget.setup(0, self.zoom, self.rotation)
        self._add_to_recent(path)
        self.detect_page_count()
        #self.populate_pages()
        if self._continuous_mode:
            self._rebuild_continuous_view()
        else:
            self.render_page()

    def detect_page_count(self):
        try:
            r = _djvu_run(["djvused.exe", self.djvu_path, "-e", "n"],
                               capture_output=True, text=True)
            self.page_count = int(r.stdout.strip())
        except Exception:
            self.page_count = 1
        # Update spinbox range and suffix
        if hasattr(self, 'page_spinbox'):
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setMaximum(self.page_count)
            self.page_spinbox.setSuffix(f" / {self.page_count}")
            self.page_spinbox.blockSignals(False)


    # ------------------------------------------------------------------ #
    #  Rendering (single-page mode)                                        #
    # ------------------------------------------------------------------ #
    # def render_page(self, highlight_line=None):
        # if not hasattr(self, "djvu_path"):
            # return
        # _djvu_run(["ddjvu.exe", "-format=ppm", "-size=1200x1600",
                        # f"-page={self.page}", self.djvu_path, self.temp_image])
        # if os.path.exists(self.temp_image):
            # pixmap = QPixmap(self.temp_image)
            # if pixmap.isNull():
                # self.image_label.setText("Rendering failed"); return
            # self.original_pixmap = pixmap
            # self._apply_transform_and_display(highlight_line=highlight_line)
        # self.page_spinbox.blockSignals(True)
        # self.page_spinbox.setValue(self.page)
        # self.page_spinbox.blockSignals(False)
        # QTimer.singleShot(0, self._sync_overlay_size)

    def render_page(self, highlight_line=None):
        if not hasattr(self, "djvu_path"):
            return

        try:
            result = _djvu_run(
                ["ddjvu.exe", "-format=ppm", "-size=1200x1600",
                 f"-page={self.page}", self.djvu_path],
                capture_output=True,
                check=True,
                timeout=30
            )
            pixmap = QPixmap()
            if not pixmap.loadFromData(result.stdout, "PPM"):
                pixmap = QPixmap()   # keep null
        except Exception:
            pixmap = QPixmap()

        if pixmap.isNull():
            self.image_label.setText(f"Failed to render page {self.page}")
            self.original_pixmap = QPixmap()
        else:
            self.original_pixmap = pixmap
            self._apply_transform_and_display(highlight_line=highlight_line)

        self.page_spinbox.blockSignals(True)
        self.page_spinbox.setValue(self.page)
        self.page_spinbox.blockSignals(False)

        QTimer.singleShot(0, self._sync_overlay_size)

    def _apply_transform_and_display(self, highlight_line=None):
        if self.original_pixmap.isNull():
            return
        pixmap = self.original_pixmap
        if self.rotation != 0:
            pixmap = pixmap.transformed(QTransform().rotate(self.rotation), Qt.SmoothTransformation)
        w = int(pixmap.width()  * self.zoom / 100)
        h = int(pixmap.height() * self.zoom / 100)
        pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if highlight_line:
            pixmap = self._draw_highlight(pixmap, highlight_line)
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        QTimer.singleShot(0, self._sync_overlay_size)

    def _draw_highlight(self, pixmap, line_text):
        if not line_text.strip():
            return pixmap
        lines = self._get_page_lines(self.page)
        if not lines:
            return pixmap
        mc = self.match_case_cb.isChecked()
        matched_idx = None
        for i, ln in enumerate(lines):
            hit = (line_text.strip() in ln) if mc else (line_text.strip().lower() in ln.lower())
            if hit:
                matched_idx = i; break
        if matched_idx is None:
            return pixmap
        n      = len(lines)
        pm_h   = pixmap.height(); pm_w = pixmap.width()
        band_h = max(18, pm_h // n)
        y_top  = max(0, min(int(matched_idx / n * pm_h), pm_h - band_h))
        result = QPixmap(pixmap)
        p = QPainter(result)
        try:
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.fillRect(QRect(0, y_top, pm_w, band_h), QColor(255, 230, 0, 130))
            p.setPen(QPen(QColor(220, 140, 0, 200), 2))
            p.drawRect(QRect(0, y_top, pm_w - 1, band_h))
        finally:
            p.end()
        return result

    def _get_page_lines(self, page_no):
        if page_no in self.page_text_cache:
            return self.page_text_cache[page_no]
        try:
            r = _djvu_run(["djvutxt.exe", f"--page={page_no}", self.djvu_path],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        except Exception:
            lines = []
        self.page_text_cache[page_no] = lines
        return lines

    # ------------------------------------------------------------------ #
    #  Search background                                                   #
    # ------------------------------------------------------------------ #
    def _abort_worker(self):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.abort()
            self._search_worker.quit()          # harmless even if no event loop
            # Wait up to 2 seconds, processing events to avoid UI freeze
            for _ in range(20):                 # 20 * 100 ms = 2 seconds
                if self._search_worker.wait(100):
                    break
                QApplication.processEvents()
            # If still running, terminate (last resort) and wait again
            if self._search_worker.isRunning():
                self._search_worker.terminate()
                self._search_worker.wait(1000)
        self._search_worker = None

        
        
    def _on_query_changed(self):
        self.search_results = []
        self.search_index   = -1
        self._search_query  = ""
        if self.main_window:
            self.main_window.update_status_bar(None, timeout=0, show_extras=False)
        self._abort_worker()
        self._debounce_timer.start(400)

    def _start_background_search(self):
        query = self.search_field.text().strip()
        if not query or not hasattr(self, "djvu_path"):
            return
        self._search_query = query
        if self.main_window:
            self.main_window.update_status_bar("Searching…", timeout=0, show_extras=False)
        self._abort_worker()
        worker = SearchWorker(
            self.djvu_path, self.page_count, query,
            self.match_case_cb.isChecked(), self.page_text_cache
        )
        worker.progress.connect(self._on_search_progress)
        worker.finished.connect(self._on_search_finished)
        self._search_worker = worker
        worker.start()

    def _on_search_progress(self, results, pages_done, total):
        self.search_results = results
        pct = int(pages_done / total * 100)
        n   = len(results)
        if self.main_window:
            self.main_window.update_status_bar(f"Searching… {pct}% ({n} found)", timeout=0, show_extras=False)

    def _on_search_finished(self, results):
        self.search_results = results
        n = len(results)
        q = self._search_query
        if n:
            self._update_search_status()
        else:
            if self.main_window:
                self.main_window.update_status_bar(f'"{q}" not found', timeout=3000, show_extras=False)

    def _ensure_search_ready(self, query):
        if self._search_query != query:
            self._debounce_timer.stop()
            self._start_background_search()
        if self._search_worker and self._search_worker.isRunning():
            if self.search_results:
                return True
            for _ in range(160):
                self._search_worker.wait(50)
                QApplication.processEvents()
                if self.search_results:
                    return True
                if not self._search_worker.isRunning():
                    break
        if not self.search_results and self.main_window:
            self.main_window.update_status_bar(f'"{query}" not found', timeout=3000, show_extras=False)
        return bool(self.search_results)

    def search_next(self):
        query = self.search_field.text().strip()
        if not query: return
        if not self._ensure_search_ready(query):
            return
        self.search_index = (self.search_index + 1) % len(self.search_results)
        pg, line_text = self.search_results[self.search_index]
        self.page = pg
        self._update_search_status()
        self._highlight_sidebar_row()
        if self._continuous_mode:
            self._scroll_to_current_page()
        else:
            self.render_page(highlight_line=line_text)

    def search_prev(self):
        query = self.search_field.text().strip()
        if not query: return
        if not self._ensure_search_ready(query):
            return
        self.search_index = (self.search_index - 1) % len(self.search_results)
        pg, line_text = self.search_results[self.search_index]
        self.page = pg
        self._update_search_status()
        self._highlight_sidebar_row()
        if self._continuous_mode:
            self._scroll_to_current_page()
        else:
            self.render_page(highlight_line=line_text)

    def find_all(self):
        query = self.search_field.text().strip()
        if not query: return
        if not self._ensure_search_ready(query):
            self._populate_sidebar(query)
            return
        if self._search_worker and self._search_worker.isRunning():
            if self.main_window:
                self.main_window.update_status_bar("Waiting for search to complete…", timeout=0, show_extras=False)
            self._search_worker.wait(30000)
            QApplication.processEvents()
        self.search_index = 0 if self.search_results else -1
        self._populate_sidebar(query)
        self._update_search_status()
        if self.search_results:
            pg, line_text = self.search_results[0]
            self.page = pg
            if self._continuous_mode:
                self._scroll_to_current_page()
            else:
                self.render_page(highlight_line=line_text)

    def _update_search_status(self):
        if self.search_results and self.search_index >= 0:
            n = len(self.search_results)
            still = self._search_worker and self._search_worker.isRunning()
            suffix = "+" if still else ""
            msg = f"{self.search_index+1} / {n}{suffix}"
            if self.main_window:
                self.main_window.update_status_bar(msg, timeout=0, show_extras=False)
        else:
            if self.main_window:
                self.main_window.update_status_bar(None, timeout=0, show_extras=False)

    def _highlight_sidebar_row(self):
        if not self.search_results or self.search_index < 0: return
        if self.sidebar_widget.isVisible() and self.search_index < self.results_list.count():
            self.results_list.setCurrentRow(self.search_index)

    # ------------------------------------------------------------------ #
    #  Navigation                                                          #
    # ------------------------------------------------------------------ #
    def next_page(self):
        if self.page < self.page_count:
            self.page += 1
            if self._continuous_mode:                
                self.page_spinbox.blockSignals(True)
                self.page_spinbox.setValue(self.page)
                self.page_spinbox.blockSignals(False)
                self._scroll_to_current_page()
                self._start_window_renderer(self.page) 
            else:
                self.render_page()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            if self._continuous_mode:
                self.page_spinbox.blockSignals(True)
                self.page_spinbox.setValue(self.page)
                self.page_spinbox.blockSignals(False)
                self._scroll_to_current_page()
                self._start_window_renderer(self.page) 
            else:
                self.render_page()

    # def page_selected(self, index):
        # self.page = index + 1
        # if self._continuous_mode:
            # self._scroll_to_current_page()
        # else:
            # self.render_page()

    def page_selected(self, index):
        self.page = index + 1
        if self._continuous_mode:
            # Ensure the continuous widget is properly set up
            if self.cont_page_widget._page_count == 0:
                self._rebuild_continuous_view()
            else:
                self._scroll_to_current_page()
                # Start rendering the window around the newly selected page
                self._start_window_renderer(self.page)
        else:
            self.render_page()            

    # ------------------------------------------------------------------ #
    #  Copy                                                                #
    # ------------------------------------------------------------------ #
    def copy_page(self):
        if not self.original_pixmap.isNull():
            QApplication.clipboard().setPixmap(self.original_pixmap)

    def _copy_current_selection(self):
        pm = self.image_label.pixmap()
        if pm is None or pm.isNull():
            return
        if not self.selection_overlay.isVisible():
            return
        sel = self.selection_overlay.rect_selection()
        if sel.isEmpty():
            return
        lw, lh   = self.image_label.width(), self.image_label.height()
        pw, ph   = pm.width(), pm.height()
        off_x    = (lw - pw) // 2
        off_y    = (lh - ph) // 2
        r = sel.translated(-off_x, -off_y)
        r = r.intersected(QRect(0, 0, pw, ph))
        if r.isEmpty():
            return
        cropped = pm.copy(r)
        QApplication.clipboard().setPixmap(cropped)
        self.copy_sel_btn.setEnabled(True)
        self.copy_text_btn.setEnabled(True)

    def _copy_selected_text(self):
        if not hasattr(self, "djvu_path"):
            return
        if not self.selection_overlay.isVisible():
            return
        sel = self.selection_overlay.rect_selection()
        if sel.isEmpty():
            return
        pm = self.image_label.pixmap()
        if pm is None or pm.isNull():
            return
        lw, lh = self.image_label.width(), self.image_label.height()
        pw, ph = pm.width(), pm.height()
        off_x  = (lw - pw) // 2
        off_y  = (lh - ph) // 2
        r_zoom = sel.translated(-off_x, -off_y).intersected(QRect(0, 0, pw, ph))
        if r_zoom.isEmpty():
            return
        scale  = 100.0 / self.zoom
        orig_w = self.original_pixmap.width()
        orig_h = self.original_pixmap.height()
        def rotate_rect_back(rx, ry, rw, rh, angle, img_w, img_h):
            if angle == 0:
                return rx, ry, rw, rh
            if angle == 90:
                return ry, img_w - rx - rw, rh, rw
            if angle == 180:
                return img_w - rx - rw, img_h - ry - rh, rw, rh
            if angle == 270:
                return img_h - ry - rh, rx, rh, rw
            return rx, ry, rw, rh
        zx = int(r_zoom.x() * scale)
        zy = int(r_zoom.y() * scale)
        zw = int(r_zoom.width()  * scale)
        zh = int(r_zoom.height() * scale)
        rot_w = (orig_h if self.rotation in (90, 270) else orig_w)
        rot_h = (orig_w if self.rotation in (90, 270) else orig_h)
        ox, oy, ow, oh = rotate_rect_back(zx, zy, zw, zh,
                                           self.rotation, rot_w, rot_h)
        page_w_px, page_h_px = self._get_page_native_size(self.page)
        if page_w_px is None:
            self._fallback_copy_text()
            return
        sx = page_w_px / orig_w
        sy = page_h_px / orig_h
        djvu_x0 = int(ox * sx)
        djvu_y0 = int((orig_h - oy - oh) * sy)
        djvu_x1 = int((ox + ow) * sx)
        djvu_y1 = int((orig_h - oy) * sy)
        text = self._extract_text_in_bbox(self.page, djvu_x0, djvu_y0, djvu_x1, djvu_y1)
        if text is None:
            text = self._fallback_copy_text(return_only=True)
        if text:
            QApplication.clipboard().setText(text)
            if self.main_window:
                self.main_window.update_status_bar("Text copied", timeout=2000, show_extras=False)
        else:
            if self.main_window:
                self.main_window.update_status_bar("No text layer found", timeout=2500, show_extras=False)

    def _get_page_native_size(self, page_no):
        try:
            r = _djvu_run(
                ["djvused.exe", self.djvu_path, "-e",
                 f"select {page_no}; print-page-info"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            w = h = None
            for token in r.stdout.split(','):
                token = token.strip()
                if token.startswith('width='):
                    w = int(token.split('=')[1])
                elif token.startswith('height='):
                    h = int(token.split('=')[1])
            if w and h:
                return w, h
        except Exception:
            pass
        return None, None

    def _extract_text_in_bbox(self, page_no, x0, y0, x1, y1):
        try:
            r = _djvu_run(
                ["djvused.exe", self.djvu_path, "-e",
                 f"select {page_no}; print-txt"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
        except Exception:
            return None
        raw = r.stdout.strip()
        if not raw or raw.startswith("No") or "hidden-text" not in raw:
            return None
        import re
        words = []
        pattern = re.compile(
            r'\(word\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"([^"]*)"\s*\)',
            re.DOTALL
        )
        for m in pattern.finditer(raw):
            wx0, wy0, wx1, wy1 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            word_text = m.group(5)
            if wx1 >= x0 and wx0 <= x1 and wy1 >= y0 and wy0 <= y1:
                words.append((wx0, wy1, word_text))
        if not words:
            return ""
        words.sort(key=lambda w: (-w[1], w[0]))
        return " ".join(w[2] for w in words)

    def _fallback_copy_text(self, return_only=False):
        try:
            r = _djvu_run(
                ["djvutxt.exe", f"--page={self.page}", self.djvu_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            text = r.stdout.strip()
        except Exception:
            text = ""
        if return_only:
            return text or None
        if text:
            QApplication.clipboard().setText(text)
            if self.main_window:
                self.main_window.update_status_bar("Full-page text copied", timeout=2000, show_extras=False)
        else:
            if self.main_window:
                self.main_window.update_status_bar("No text layer found", timeout=2500, show_extras=False)

    # ------------------------------------------------------------------ #
    #  Zoom / Fit                                                          #
    # ------------------------------------------------------------------ #
    def zoom_in(self):
        self.zoom = min(400, self.zoom + 10)
        self.zoom_spin.blockSignals(True); self.zoom_spin.setValue(self.zoom); self.zoom_spin.blockSignals(False)
        if self._continuous_mode:
            self._refresh_continuous_zoom_rotation()
        else:
            self._apply_transform_and_display()

    def zoom_out(self):
        self.zoom = max(10, self.zoom - 10)
        self.zoom_spin.blockSignals(True); self.zoom_spin.setValue(self.zoom); self.zoom_spin.blockSignals(False)
        if self._continuous_mode:
            self._refresh_continuous_zoom_rotation()
        else:
            self._apply_transform_and_display()

    def set_zoom(self, value):
        self.zoom = value
        if self._continuous_mode:
            self._refresh_continuous_zoom_rotation()
        else:
            self._apply_transform_and_display()

    def fit_width(self):
        if self._continuous_mode:
            vp_w = self.cont_scroll_area.viewport().width()
            # Use any cached page as a reference for the base width
            ref_pm = next(
                (pm for pm in self.cont_page_widget._pixmap_cache.values()
                 if pm and not pm.isNull()), None)
            if ref_pm is None or ref_pm.isNull():
                return
            pm_w = ref_pm.height() if self.rotation in (90, 270) else ref_pm.width()
            if pm_w == 0: return
            self.zoom = max(10, min(400, int(vp_w / pm_w * 100)))
            self.zoom_spin.blockSignals(True); self.zoom_spin.setValue(self.zoom); self.zoom_spin.blockSignals(False)
            self._refresh_continuous_zoom_rotation()
        else:
            if self.original_pixmap.isNull(): return
            vp_w = self.scroll_area.viewport().width()
            pm_w = (self.original_pixmap.height() if self.rotation in (90, 270)
                    else self.original_pixmap.width())
            if pm_w == 0: return
            self.zoom = max(10, min(400, int(vp_w / pm_w * 100)))
            self.zoom_spin.blockSignals(True); self.zoom_spin.setValue(self.zoom); self.zoom_spin.blockSignals(False)
            self._apply_transform_and_display()

    def fit_page(self):
        if self._continuous_mode:
            vp = self.cont_scroll_area.viewport().size()
            ref_pm = next(
                (pm for pm in self.cont_page_widget._pixmap_cache.values()
                 if pm and not pm.isNull()), None)
            if ref_pm is None or ref_pm.isNull(): return
            pw, ph = ((ref_pm.height(), ref_pm.width()) if self.rotation in (90, 270)
                      else (ref_pm.width(), ref_pm.height()))
            if pw == 0 or ph == 0: return
            self.zoom = max(10, min(400, int(min(vp.width() / pw, vp.height() / ph) * 100)))
            self.zoom_spin.blockSignals(True); self.zoom_spin.setValue(self.zoom); self.zoom_spin.blockSignals(False)
            self._refresh_continuous_zoom_rotation()
        else:
            if self.original_pixmap.isNull(): return
            area = self.scroll_area.viewport().size()
            src = self.original_pixmap
            pw, ph = ((src.height(), src.width()) if self.rotation in (90, 270)
                      else (src.width(), src.height()))
            if pw == 0 or ph == 0: return
            self.zoom = max(10, min(400, int(min(area.width() / pw, area.height() / ph) * 100)))
            self.zoom_spin.blockSignals(True); self.zoom_spin.setValue(self.zoom); self.zoom_spin.blockSignals(False)
            self._apply_transform_and_display()

    # ------------------------------------------------------------------ #
    #  Rotation                                                            #
    # ------------------------------------------------------------------ #
    def rotate(self, angle):
        self.rotation = (self.rotation + angle) % 360
        if self._continuous_mode:
            self._refresh_continuous_zoom_rotation()
        else:
            self._apply_transform_and_display()

    # ------------------------------------------------------------------ #
    #  Rect select                                                         #
    # ------------------------------------------------------------------ #
    # def _toggle_rect_tool(self, checked):
        # self.rect_tool_enabled = checked
        # self.image_label.setCursor(Qt.CrossCursor if checked else Qt.ArrowCursor)

    def _toggle_rect_tool(self, checked):
        self.rect_tool_enabled = checked
        if checked and self.hand_tool_enabled:
            self.hand_btn.blockSignals(True)
            self.hand_btn.setChecked(False)
            self.hand_btn.blockSignals(False)
            self._toggle_hand_tool(False)
        if checked and self._continuous_mode:
            self.cont_btn.setChecked(False)   # this will call _toggle_continuous_mode(False)
            
        self.image_label.setCursor(Qt.CrossCursor if checked else Qt.ArrowCursor)        

    def _clear_selection(self):
        self.selection_overlay.clear()
        self.copy_sel_btn.setEnabled(False)
        self.copy_text_btn.setEnabled(False)


    def _toggle_hand_tool(self, checked):
        self.hand_tool_enabled = checked
        if checked and self.rect_tool_enabled:
            # Disable rect tool if it was active
            self.rect_btn.blockSignals(True)
            self.rect_btn.setChecked(False)
            self.rect_btn.blockSignals(False)
            self._toggle_rect_tool(False)
        # Set appropriate cursor on the view widgets
        self._update_hand_cursor()
    # ------------------------------------------------------------------ #
    #  Cleanup                                                             #
    # ------------------------------------------------------------------ #
    def closeEvent(self, event):
        self._abort_worker()
        self._abort_cont_renderer()
        super().closeEvent(event)
        # Force a final event loop iteration to allow any pending signals to finish
        QApplication.processEvents()
        super().closeEvent(event)        




# ------------------------------------------------------------------ #
#  Integration helper (unchanged public API)                          #
# ------------------------------------------------------------------ #
def add_djvu_tab_to_pdf_viewer(main_window):
    """Add a DjVu viewer tab to the PDF viewer's tab widget."""
    lang = main_window.menu_language
    translations = main_window.translations
    tr = translations[lang]
    try:
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
                "DjVu viewer tab is only available in tabbed mode. Switch to tabbed mode first.")
            return
        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
            from PyQt5.QtWidgets import QTabWidget
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(pdf_manager.close_pdf_tab)
            pdf_layout = layout_manager.pdf_container.layout()
            if pdf_layout:
                while pdf_layout.count():
                    item = pdf_layout.takeAt(0)
                    if item.widget():
                        widget = item.widget()
                        widget.setParent(None)
                        widget.deleteLater()
                pdf_layout.addWidget(pdf_manager.pdf_tabs)
        tab_widget = pdf_manager.pdf_tabs
        if tab_widget is None:
            QMessageBox.critical(main_window, "Error", "Could not initialize PDF tabs")
            return
        unwanted = ["Welcome", "No Pdfs", "No PDFs"]
        for i in reversed(range(tab_widget.count())):
            if tab_widget.tabText(i) in unwanted:
                tab_widget.removeTab(i)
        possible_labels = {tr["djvu_tab"] for tr in translations.values()}
        djvu_tab_index = -1
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                djvu_tab_index = i
                break
        if djvu_tab_index >= 0:
            new_name = tr.get("djvu_tab", "DjVu Viewer")
            tab_widget.setTabText(djvu_tab_index, new_name)
            tab_widget.setCurrentIndex(djvu_tab_index)
            main_window._djvu_tab_index = djvu_tab_index
            return
            
        from djvu_tab import DjvuTab
        djvu_tab = DjvuTab(main_window, main_window=main_window)
        
        # After creating djvu_tab = DjvuTab(main_window)
        if hasattr(main_window, 'menu_djvu_toolbar_toggle_action'):
            visible = main_window.menu_djvu_toolbar_toggle_action.isChecked()
            djvu_tab.set_toolbar_visible(visible)        
        
        if not hasattr(main_window, '_djvu_tabs'):
            main_window._djvu_tabs = []
        main_window._djvu_tabs.append(djvu_tab)
        tab_name = tr.get("djvu_tab", "DjVu Viewer")
        new_index = tab_widget.addTab(djvu_tab, tab_name)
        tab_widget.tabBar().setTabData(new_index, "djvu_tab")
        main_window._djvu_tab_index = new_index
        tab_widget.tabBar().setTabData(new_index, "tools_tab")
        from PyQt5.QtGui import QIcon
        if os.path.exists("icons/djvu.svg"):
            tab_widget.setTabIcon(new_index, QIcon("icons/djvu.svg"))
        tab_widget.setCurrentIndex(new_index)
        tab_widget.setTabsClosable(True)
        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)
        tab_widget.show()
        layout_manager.pdf_container.update()
        djvu_tab.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()
    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add DjVu viewer tab:\n{str(e)}")
        import traceback
        traceback.print_exc()