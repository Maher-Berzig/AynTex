# ============================================================================
# FILE: tools_tab.py
# ============================================================================
"""
Tools Tab Widget - Scientific Calculator, Calendar, and Quick Access Tools
Add this to a new file: tools_tab.py
"""
# Add these to the existing PyQt5.QtWidgets import at the top:
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QSplitter, QGridLayout, QLineEdit, QCalendarWidget,
                             QLabel, QCheckBox, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem,   # ← NEW
                             QComboBox, QSpinBox, QTextEdit,   # ← NEW
                             QGroupBox, QMenu, QInputDialog,   # ← NEW
                             QDialog, QDialogButtonBox)        # ← NEW
from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QBrush, QPixmap, QImage, QIcon
from PyQt5.QtWidgets import QFileDialog, QScrollArea, QApplication, QSizePolicy
import subprocess
import os
import sys
import math


from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class ResizableImageWidget(QWidget):
    """A resizable image widget with close button - frameless, fits entire image"""
    def __init__(self, pixmap, tools_tab=None, parent=None):
        super().__init__(parent)
        self.tools_tab = tools_tab 
        image = pixmap.toImage()        
        self.original_image = image
        self.original_pixmap = QPixmap.fromImage(image)   # ← force independent copy
        self.editable_pixmap = QPixmap.fromImage(image)   # ← force independent copy        
        self.current_scale = 1.0
        self.drawing_mode = None  # None, 'draw', or 'erase'
        self.last_point = None
        self.brush_size = 4
        self.brush_color = QColor(Qt.red)
        # Keep a mutable copy for drawing
        #self.editable_pixmap = pixmap.copy()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Image label — now subclassed for mouse events
        self.image_label = DrawableLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        self.image_label.setPixmap(self.editable_pixmap)
        self.image_label.setMinimumHeight(50)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMouseTracking(True)  
        layout.addWidget(self.image_label, 1)
        
        # ADD THESE — propagate mouse tracking up to container
        self.setMouseTracking(True)
        self.parent() and self.parent().setMouseTracking(True)
        

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(2)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(30, 24)
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setToolTip("Zoom In")
        btn_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(30, 24)
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setToolTip("Zoom Out")
        btn_layout.addWidget(zoom_out_btn)

        fit_btn = QPushButton("Fit")
        fit_btn.setFixedSize(40, 24)
        fit_btn.clicked.connect(self.fit_to_width)
        fit_btn.setToolTip("Fit to width")
        btn_layout.addWidget(fit_btn)

        reset_btn = QPushButton("1:1")
        reset_btn.setFixedSize(40, 24)
        reset_btn.clicked.connect(self.reset_size)
        reset_btn.setToolTip("Original size")
        btn_layout.addWidget(reset_btn)

        copy_btn = QPushButton("📋")
        copy_btn.setFixedSize(30, 24)
        copy_btn.setToolTip("Copy image to clipboard")
        copy_btn.clicked.connect(self.copy_image)
        btn_layout.addWidget(copy_btn)

        # --- Paintbrush button ---
        self.paintbrush_btn = QPushButton("✎")
        self.paintbrush_btn.setFixedSize(30, 24)
        self.paintbrush_btn.setToolTip("Draw on image (click to pick color)")
        self.paintbrush_btn.setCheckable(True)
        self.paintbrush_btn.clicked.connect(self.toggle_draw_mode)
        btn_layout.addWidget(self.paintbrush_btn)

        # --- Eraser button ---
        self.eraser_btn = QPushButton("▢")
        self.eraser_btn.setFixedSize(30, 24)
        self.eraser_btn.setToolTip("Erase drawings")
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.clicked.connect(self.toggle_erase_mode)
        btn_layout.addWidget(self.eraser_btn)

        # --- Erase All button ---
        self.erase_all_btn = QPushButton("⌫")
        self.erase_all_btn.setFixedSize(30, 24)
        self.erase_all_btn.setToolTip("Erase all drawings (reset to original)")
        self.erase_all_btn.clicked.connect(self.erase_all_drawings)
        btn_layout.addWidget(self.erase_all_btn)        



        # --- Brush size spinner (shown only in draw/erase mode) ---
        from PyQt5.QtWidgets import QSpinBox
        self.size_spinner = QSpinBox()
        self.size_spinner.setRange(1, 40)
        self.size_spinner.setValue(self.brush_size)
        self.size_spinner.setFixedSize(44, 24)
        self.size_spinner.setToolTip("Brush / eraser size")
        self.size_spinner.valueChanged.connect(lambda v: setattr(self, 'brush_size', v))
        self.size_spinner.setVisible(False)
        btn_layout.addWidget(self.size_spinner)

        btn_layout.addStretch()

        close_btn = QPushButton("✖")
        close_btn.setFixedSize(30, 24)
        close_btn.setStyleSheet("background: #f44336; color: white;")
        close_btn.clicked.connect(self.close_image)
        close_btn.setToolTip("Close image")
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        QApplication.processEvents()
        self.fit_to_width()

    # ------------------------------------------------------------------ #
    #  Draw / Erase mode toggles
    # ------------------------------------------------------------------ #
    def toggle_draw_mode(self):
        if self.paintbrush_btn.isChecked():
            # Ask for color
            from PyQt5.QtWidgets import QColorDialog
            color = QColorDialog.getColor(self.brush_color, self, "Pick brush color")
            if color.isValid():
                self.brush_color = color
            self.drawing_mode = 'draw'
            self.eraser_btn.setChecked(False)
            self.size_spinner.setVisible(True)
            self.image_label.setCursor(Qt.CrossCursor)
            self.paintbrush_btn.setStyleSheet("background: #c8e6c9;")  # Light green = active
        else:
            self._exit_drawing_mode()

    def toggle_erase_mode(self):
        if self.eraser_btn.isChecked():           
            self.drawing_mode = 'erase'
            self.paintbrush_btn.setChecked(False)
            self.paintbrush_btn.setStyleSheet("")
            self.size_spinner.setVisible(True)
            self.image_label.setCursor(Qt.CrossCursor)
            self.eraser_btn.setStyleSheet("background: #fff9c4;")  # Light yellow = active
        else:
            self._exit_drawing_mode()

    def erase_all_drawings(self):
        if self.tools_tab:
            # Call the method on ToolsTab, not on self
            self.tools_tab.reset_image_widget(self, QPixmap.fromImage(self.original_image))
        else:
            # Fallback: just reset pixmap and repaint
            self.editable_pixmap = QPixmap.fromImage(self.original_image)
            self.update_image()
            self.repaint()
        self._exit_drawing_mode()

    
    def _exit_drawing_mode(self):
        self.drawing_mode = None
        self.last_point = None
        self.paintbrush_btn.setChecked(False)
        self.eraser_btn.setChecked(False)
        self.paintbrush_btn.setStyleSheet("")
        self.eraser_btn.setStyleSheet("")
        self.size_spinner.setVisible(False)
        self.image_label.setCursor(Qt.ArrowCursor)

    # ------------------------------------------------------------------ #
    #  Drawing logic — called by DrawableLabel mouse events
    # ------------------------------------------------------------------ #
    def on_mouse_press(self, event):
        if self.drawing_mode and event.button() == Qt.LeftButton:
            self.last_point = self._to_pixmap_coords(event.pos())

    def on_mouse_move(self, event):
        if self.drawing_mode and (event.buttons() & Qt.LeftButton) and self.last_point:
            current_point = self._to_pixmap_coords(event.pos())
            self._paint_line(self.last_point, current_point)
            self.last_point = current_point

    def on_mouse_release(self, event):
        self.last_point = None

    def _to_pixmap_coords(self, label_pos):
        """Convert label widget coordinates → original pixmap coordinates"""
        from PyQt5.QtCore import QPoint
        lw = self.image_label.width()
        lh = self.image_label.height()
        pw = self.editable_pixmap.width()
        ph = self.editable_pixmap.height()
        # The pixmap is centered inside the label
        scaled_w = int(pw * self.current_scale)
        scaled_h = int(ph * self.current_scale)
        offset_x = (lw - scaled_w) // 2
        offset_y = (lh - scaled_h) // 2
        # Position relative to the scaled image
        rel_x = label_pos.x() - offset_x
        rel_y = label_pos.y() - offset_y
        # Map back to original pixmap space
        orig_x = int(rel_x / self.current_scale)
        orig_y = int(rel_y / self.current_scale)
        return QPoint(max(0, min(orig_x, pw - 1)),
                      max(0, min(orig_y, ph - 1)))

    def _paint_line(self, p1, p2):
        from PyQt5.QtGui import QPainter, QPen, QPainterPath, QPainterPathStroker
        from PyQt5.QtCore import Qt, QPointF
        #print(f"_paint_line called, mode={self.drawing_mode}, p1={p1}, p2={p2}")        
        if self.drawing_mode == 'erase':
            # Create eraser path
            path = QPainterPath()
            path.moveTo(QPointF(p1))
            path.lineTo(QPointF(p2))
            stroker = QPainterPathStroker()
            stroker.setWidth(self.brush_size * 2)
            stroker.setCapStyle(Qt.RoundCap)
            stroker.setJoinStyle(Qt.RoundJoin)
            eraser_shape = stroker.createStroke(path)
            
            # Create a white/transparent brush for erasing
            work = self.editable_pixmap.copy()
            rp = QPainter(work)
            rp.setClipPath(eraser_shape)
            
            # OPTION 1: Erase to white (reveals white background)
            rp.setCompositionMode(QPainter.CompositionMode_Source)
            rp.fillPath(eraser_shape, Qt.white)  # Fill with white
            
            # OPTION 2: Erase to transparent (if you want transparency support)
            # rp.setCompositionMode(QPainter.CompositionMode_Clear)
            # rp.fillPath(eraser_shape, Qt.transparent)
            
            rp.end()
            self.editable_pixmap = work
            
        else:
            # Draw mode - unchanged
            work = self.editable_pixmap.copy()
            pen = QPen()
            pen.setWidth(self.brush_size)
            color = self.brush_color if isinstance(self.brush_color, QColor) else QColor(self.brush_color)
            pen.setColor(color)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter = QPainter(work)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
            painter.end()
            self.editable_pixmap = work

        #print(f"from _paint_line: scaled pixmap in label after erase: {self.image_label.pixmap().cacheKey()}")
        #print(f"from _paint_line: editable cacheKey: {self.editable_pixmap.cacheKey()}")
        
        self.update_image()    
    # ------------------------------------------------------------------ #
    #  Existing methods (unchanged except update_image uses editable_pixmap)
    # ------------------------------------------------------------------ #
    def zoom_in(self):
        self.current_scale *= 1.25
        self.update_image()

    def zoom_out(self):
        self.current_scale /= 1.25
        if self.current_scale < 0.1:
            self.current_scale = 0.1
        self.update_image()

    def reset_size(self):
        self.current_scale = 1.0
        self.update_image()

    def fit_to_width(self):
        available_width = self.width() - 10
        if available_width <= 0:
            available_width = 400
        if self.editable_pixmap.width() > 0:
            self.current_scale = available_width / self.editable_pixmap.width()
        self.update_image()

    def update_image(self):
        if self.editable_pixmap.isNull():
            return
        new_width = int(self.editable_pixmap.width() * self.current_scale)
        new_height = int(self.editable_pixmap.height() * self.current_scale)
        if new_width <= 0 or new_height <= 0:
            return
        scaled_pixmap = self.editable_pixmap.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setMinimumHeight(scaled_pixmap.height())
        # Force repaint (critical when scaled size doesn't change)
        self.image_label.repaint()
        self.repaint()     
        self.image_label.updateGeometry()
        self.layout().activate()
        QApplication.processEvents()        
        

    def copy_image(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.editable_pixmap)  # Copy with drawings

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def close_image(self):
        self.deleteLater()


# ------------------------------------------------------------------ #
#  Helper: QLabel subclass that forwards mouse events to parent widget
# ------------------------------------------------------------------ #
class DrawableLabel(QLabel):
    def __init__(self, drawing_widget, parent=None):
        super().__init__(parent)
        self.drawing_widget = drawing_widget
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.drawing_widget.on_mouse_press(event)

    def mouseMoveEvent(self, event):
        self.drawing_widget.on_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.drawing_widget.on_mouse_release(event)


# ─────────────────────────────────────────────────────────────
# Theme-aware palette for TabularMaker
# ─────────────────────────────────────────────────────────────

def _tabular_colors() -> dict:
    try:
        from style_manager import _current_theme as _t
    except ImportError:
        _t = "default"

    _P = {
        "default": dict(
            header_bg=QColor(210, 225, 245), header_fg=QColor(20,  20,  20),
            data_bg  =QColor(255, 255, 255), data_fg  =QColor(20,  20,  20),
            alt_bg   =QColor(245, 248, 255),
            sep_bg   =QColor(170, 185, 210), sep_fg   =QColor(90,  90,  90),
            border   =QColor(30,  100, 200), partial  =QColor(180, 60,  20),
            prev_bg  ="#f5f5f5",             prev_fg  ="#1e1e1e",
            prev_bdr ="#aaaaaa",
        ),
        "dark": dict(
            header_bg=QColor(55,  65,  82),  header_fg=QColor(190, 200, 215),
            data_bg  =QColor(43,  43,  43),  data_fg  =QColor(187, 187, 187),
            alt_bg   =QColor(50,  52,  58),
            sep_bg   =QColor(33,  40,  55),  sep_fg   =QColor(120, 135, 155),
            border   =QColor(80,  140, 220), partial  =QColor(210, 100, 40),
            prev_bg  ="#1e1e1e",             prev_fg  ="#9cdcfe",
            prev_bdr ="#555759",
        ),
        "light": dict(
            header_bg=QColor(220, 235, 250), header_fg=QColor(20,  20,  20),
            data_bg  =QColor(250, 250, 252), data_fg  =QColor(20,  20,  20),
            alt_bg   =QColor(238, 244, 255),
            sep_bg   =QColor(185, 205, 228), sep_fg   =QColor(55,  55,  55),
            border   =QColor(30,  100, 200), partial  =QColor(170, 60,  20),
            prev_bg  ="#ffffff",             prev_fg  ="#1a1a1a",
            prev_bdr ="#c0c0c0",
        ),
        "midnight": dict(
            header_bg=QColor(22,  27,  34),  header_fg=QColor(88,  166, 255),
            data_bg  =QColor(13,  17,  23),  data_fg  =QColor(201, 209, 217),
            alt_bg   =QColor(17,  22,  30),
            sep_bg   =QColor(9,   13,  19),  sep_fg   =QColor(56,  139, 253),
            border   =QColor(56,  139, 253), partial  =QColor(210, 100, 40),
            prev_bg  ="#010409",             prev_fg  ="#c9d1d9",
            prev_bdr ="#30363d",
        ),
    }
    return _P.get(_t, _P["default"])


# ─────────────────────────────────────────────────────────────
# Combo delegate — used for the alignment header row
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# Event filter: redirect right-clicks on any cell editor to the
# table's viewport so our custom context menu always appears.
# ─────────────────────────────────────────────────────────────
class _EditorContextFilter(QObject):
    """Installed on every editor widget created by our delegates.
    Intercepts QEvent::ContextMenu and forwards it as a
    customContextMenuRequested signal on the table viewport instead,
    so TabularMaker.show_context_menu() is always called.
    """
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self._table = table

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ContextMenu:
            # Map the global position to the viewport's local coordinates
            vp = self._table.viewport()
            local_pos = vp.mapFromGlobal(event.globalPos())
            self._table.customContextMenuRequested.emit(local_pos)
            return True          # eat the event so Qt's own menu never shows
        return False


class ComboDelegate(QStyledItemDelegate):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self.options)
        combo.setContextMenuPolicy(Qt.NoContextMenu)
        # Find the owning QTableWidget by walking up the parent chain
        table = parent
        while table and not isinstance(table, QTableWidget):
            table = table.parent()
        if table:
            combo.installEventFilter(_EditorContextFilter(table, combo))
        return combo

    def setEditorData(self, editor, index):
        val = index.data(Qt.EditRole) or index.data(Qt.DisplayRole) or ''
        i = editor.findText(val)
        editor.setCurrentIndex(max(0, i))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

    def paint(self, painter, option, index):
        clr = _tabular_colors()
        painter.save()
        painter.fillRect(option.rect, clr['header_bg'])
        opt = option.__class__(option)
        opt.palette.setColor(opt.palette.Text, clr['header_fg'])
        super().paint(painter, opt, index)
        painter.restore()


# ─────────────────────────────────────────────────────────────
# Delegate for plain data cells — redirects right-click to our
# custom context menu instead of QLineEdit's native one.
# ─────────────────────────────────────────────────────────────
class DataDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if editor is not None:
            editor.setContextMenuPolicy(Qt.NoContextMenu)
            table = parent
            while table and not isinstance(table, QTableWidget):
                table = table.parent()
            if table:
                editor.installEventFilter(_EditorContextFilter(table, editor))
        return editor


# ─────────────────────────────────────────────────────────────
# Custom Table — paints LaTeX borders as coloured lines
# ─────────────────────────────────────────────────────────────
class TableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.owner = None
        self._selection_start = None

    def mousePressEvent(self, event):
        idx = self.indexAt(event.pos())
        if idx.isValid() and idx.row() >= 1 and idx.column() >= 1:
            self._selection_start = idx
        else:
            self._selection_start = None
        # Always call super so Qt can track clicks for double-click detection
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._selection_start:
            current = self.indexAt(event.pos())
            if current.isValid() and current.row() >= 1 and current.column() >= 1:
                selection = QItemSelection(self._selection_start, current)
                self.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._selection_start = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        idx = self.indexAt(event.pos())
        if not idx.isValid():
            super().mouseDoubleClickEvent(event)
            return
        r, c = idx.row(), idx.column()
        # For a merged cell Qt reports the clicked visual position, but the
        # item and its flags live on the top-left anchor of the span.
        # Scan upward/leftward to find that anchor.
        found = False
        for tr in range(r, -1, -1):
            for tc in range(c, -1, -1):
                if self.rowSpan(tr, tc) + tr > r and self.columnSpan(tr, tc) + tc > c:
                    r, c = tr, tc
                    found = True
                    break
            if found:
                break
        item = self.item(r, c)
        if item is None:
            return
        if not (item.flags() & Qt.ItemIsEditable):
            return
        self._open_editor(item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Insert:
            idx = self.currentIndex()
            if idx.isValid():
                r, c = idx.row(), idx.column()
                # Resolve span anchor (same logic as mouseDoubleClickEvent)
                found = False
                for tr in range(r, -1, -1):
                    for tc in range(c, -1, -1):
                        if self.rowSpan(tr, tc) + tr > r and self.columnSpan(tr, tc) + tc > c:
                            r, c = tr, tc
                            found = True
                            break
                    if found:
                        break
                item = self.item(r, c)
                if item is not None and (item.flags() & Qt.ItemIsEditable):
                    self._open_editor(item)
                    return
        super().keyPressEvent(event)

    def _open_editor(self, item):
        """Open the cell editor for *item* programmatically.
        Deferred via QTimer so it runs after the triggering event fully
        completes and the view's state machine is back to NoState.
        Uses the protected edit(index, trigger, event) overload which
        bypasses editTriggers gating entirely.
        """
        r, c = self.row(item), self.column(item)
        idx = self.model().index(r, c)
        def _do_edit():
            # QAbstractItemView.edit(index, trigger, event) — protected overload
            # that skips the trigger-gating check done by the public edit(index).
            self.edit(idx, QAbstractItemView.AllEditTriggers, None)
        QTimer.singleShot(0, _do_edit)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.owner:
            return
        owner = self.owner
        vp = self.viewport()
        p = QPainter(vp)
        try:
            p.setRenderHint(QPainter.Antialiasing, False)

            clr = _tabular_colors()
            PAD_H    = 3       # horizontal inset from column edge
            PAD_V    = 0       # vertical padding (0 = full cell height)
            DBL_GAP  = 4       # gap between double-rule lines

            def _x(col): return self.columnViewportPosition(col)
            def _y(row): return self.rowViewportPosition(row)
            def _cw(col): return self.columnWidth(col)
            def _rh(row): return self.rowHeight(row)

            if owner.num_rows == 0 or owner.num_cols == 0:
                return

            # Data area extents (row 0 = header, col 0 = row-border header)
            x_left  = _x(1)
            x_right = _x(owner.num_cols) + _cw(owner.num_cols)
            y_top   = _y(1) + PAD_V
            y_bot   = _y(owner.num_rows) + _rh(owner.num_rows) - PAD_V

            # ── Vertical borders per data column ─────────────────────
            for c in range(owner.num_cols):
                col_x         = _x(c + 1)
                col_right_edge = col_x + _cw(c + 1)

                # Left border of column c
                left_val = owner.col_left_borders[c]
                if left_val == 1:
                    x = col_x + PAD_H
                    p.setPen(QPen(clr['border'], 1.5))
                    p.drawLine(x, y_top, x, y_bot)
                elif left_val == 2:
                    x1 = col_x + PAD_H
                    x2 = col_x + PAD_H + DBL_GAP
                    p.setPen(QPen(clr['border'], 1.5))
                    p.drawLine(x1, y_top, x1, y_bot)
                    p.drawLine(x2, y_top, x2, y_bot)

                # Right border of column c
                right_val = owner.col_right_borders[c]
                if right_val == 1:
                    x = col_right_edge - PAD_H
                    p.setPen(QPen(clr['border'], 1.5))
                    p.drawLine(x, y_top, x, y_bot)
                elif right_val == 2:
                    x1 = col_right_edge - PAD_H - DBL_GAP
                    x2 = col_right_edge - PAD_H
                    p.setPen(QPen(clr['border'], 1.5))
                    p.drawLine(x1, y_top, x1, y_bot)
                    p.drawLine(x2, y_top, x2, y_bot)

            # ── Global right border ──────────────────────────────────
            # if owner.right_border:
                # x = x_right - PAD_H
                # p.setPen(QPen(clr['border'], 1.5))
                # p.drawLine(x, y_top, x, y_bot)

            # ── Horizontal borders (above each data row) ─────────────
            for r in range(owner.num_rows):
                border = owner.row_borders[r]
                if border in ('none', ''):
                    continue
                y = _y(r + 1)
                is_partial = r'\cline' in border or r'\cmidrule' in border
                is_addlinespace = r'\addlinespace' in border

                if is_addlinespace:
                    # Draw a dashed/dotted line to represent whitespace
                    pen = QPen(clr['partial'], 1, Qt.DashLine)
                    p.setPen(pen)
                    p.drawLine(x_left, y, x_right, y)
                elif is_partial:
                    lo, hi = owner.cline_ranges.get(r, (1, owner.num_cols))
                    lo_col = lo - 1
                    hi_col = hi - 1
                    px0 = _x(lo_col + 1)
                    px1 = _x(hi_col + 1) + _cw(hi_col + 1)
                    p.setPen(QPen(clr['partial'], 2))
                    p.drawLine(px0, y, px1, y)
                else:
                    p.setPen(QPen(clr['border'], 2))
                    p.drawLine(x_left, y, x_right, y)

            # ── Bottom border ────────────────────────────────────────
            if owner.bottom_border not in ('none', ''):
                y = y_bot
                p.setPen(QPen(clr['border'], 2))
                p.drawLine(x_left, y, x_right, y)

        finally:
            p.end()


# ─────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────

class TabularMaker(QWidget):

    ALIGN_OPTIONS = ['l', 'c', 'r',
                     'p{2cm}', 'p{3cm}', 'p{4cm}', 'p{5cm}',
                     'X']

    # Row border options — both plain and booktabs in one combined list
    BORDERS_PLAIN    = ['none', r'\hline', r'\cline{…}',
                        r'\toprule', r'\midrule', r'\bottomrule', r'\addlinespace']
    BORDERS_BOOKTABS = ['none', r'\toprule', r'\midrule', r'\bottomrule',
                        r'\hline', r'\cline{…}', r'\cmidrule(lr){…}', r'\addlinespace']

    # Booktabs-specific commands (auto-enable booktabs checkbox)
    BOOKTABS_TRIGGERS = {r'\toprule', r'\midrule', r'\bottomrule', r'\cmidrule(lr){…}', r'\addlinespace'}

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        self.num_rows     = 5
        self.num_cols     = 5
        self.use_booktabs = False
        self.right_border = False
        self.bottom_border = 'none'

        self.col_alignments   = ['c'] * 5
        self.col_left_borders = [0] * 5   # 0=none, 1=single, 2=double
        self.col_right_borders = [0] * 5
        self.row_borders      = ['none'] * 5
        self.cline_ranges     = {}
        self.multicolumns     = {}  # (r,c) -> {'span':n,'align':'c'} or {'skip':True}
        self.multirows        = {}  # (r,c) -> {'span':n,'width':'*','content':''} or {'skip':True}

        self._updating = False
        self.setup_ui()

    # ── Column classification ─────────────────────────────────
    def _data_col_indices(self):
        return list(range(self.num_cols))

    # ── Alignment → Qt flag + pixel width ────────────────────
    @staticmethod
    def _align_to_qt(align: str):
        import re
        if align == 'l':
            return Qt.AlignLeft | Qt.AlignVCenter, 90
        if align == 'r':
            return Qt.AlignRight | Qt.AlignVCenter, 90
        if align == 'c':
            return Qt.AlignCenter, 90
        if align == 'X':
            return Qt.AlignLeft | Qt.AlignVCenter, 120
        m = re.match(r'p\{([\d.]+)\s*(cm|mm|in|pt)\}', align)
        if m:
            val = float(m.group(1))
            unit = m.group(2)
            px = {'cm': 37.8, 'mm': 3.78, 'in': 96.0, 'pt': 1.33}
            w = max(50, int(val * px.get(unit, 37.8)))
            return Qt.AlignLeft | Qt.AlignTop, w
        return Qt.AlignCenter, 90

    # ── Border helpers ────────────────────────────────────────
    def _border_options(self):
        return self.BORDERS_BOOKTABS if self.use_booktabs else self.BORDERS_PLAIN

    def _border_to_latex(self, text, row_idx):
        if text in ('none', ''):
            return ''
        if r'{…}' in text:
            lo, hi = self.cline_ranges.get(row_idx, (1, self.num_cols))
            return text.replace('{…}', f'{{{lo}-{hi}}}')
        return text

    # ── UI construction ───────────────────────────────────────
    def setup_ui(self):
        clr = _tabular_colors()
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Top bar
        top = QHBoxLayout()
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(self.num_rows)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 40)
        self.cols_spin.setValue(self.num_cols)

        apply_btn = QPushButton("Apply")
        apply_btn.setFixedHeight(24)
        apply_btn.clicked.connect(self.apply_dimensions)

        self.booktabs_cb = QCheckBox("booktabs")
        self.booktabs_cb.setToolTip("Use \\toprule/\\midrule/\\bottomrule and add %\\usepackage{booktabs}")
        self.booktabs_cb.toggled.connect(self.on_booktabs_toggled)

        insert_btn = QPushButton("📝  Insert to Editor")
        insert_btn.setFixedHeight(26)
        insert_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5cb85c, stop:1 #4cae4c);
                color: white; border-style: outset; border-width: 2px;
                border-radius: 4px; border-color: #3e8e3e;
                font-weight: bold; font-size: 8pt; padding: 0 10px; min-height: 22px;
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #6ec86e,stop:1 #5cb85c); border-color: #4cae4c; }
            QPushButton:pressed { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3e8e3e,stop:1 #4cae4c); border-style: inset; border-color: #2e6e2e; padding-top: 2px; }
            QPushButton:disabled { background: #cccccc; border-color: #aaaaaa; color: #888888; }
        """)
        insert_btn.clicked.connect(self.insert_to_editor)

        for lbl, spin in (("Rows:", self.rows_spin), ("Cols:", self.cols_spin)):
            top.addWidget(QLabel(lbl))
            top.addWidget(spin)
        top.addWidget(apply_btn)
        top.addSpacing(10)
        top.addWidget(self.booktabs_cb)
        top.addStretch()
        top.addWidget(insert_btn)
        root.addLayout(top)

        # Editable table
        self.table = TableWidget()
        self.table.owner = self
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.setAlternatingRowColors(False)
        self.table.setMinimumHeight(220)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setDragDropMode(QAbstractItemView.NoDragDrop)

        # Make real Qt headers visible but paper-thin so they act only as
        # resize-handle strips.  Interactive mode enables drag-to-resize.
        hh = self.table.horizontalHeader()
        hh.setVisible(True)
        hh.setFixedHeight(5)
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setMinimumSectionSize(30)
        hh.setSectionsMovable(False)
        hh.setHighlightSections(False)

        vh = self.table.verticalHeader()
        vh.setVisible(True)
        vh.setFixedWidth(5)
        vh.setSectionResizeMode(QHeaderView.Interactive)
        vh.setMinimumSectionSize(18)
        vh.setSectionsMovable(False)
        vh.setHighlightSections(False)

        # Style applied via _apply_header_strip_style() called in build_table
        root.addWidget(self.table, 1)

        # LaTeX preview
        prev_lbl = QLabel("LaTeX preview:")
        prev_lbl.setStyleSheet("font-weight:bold; padding-top:4px;")
        root.addWidget(prev_lbl)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Courier New", 9))
        self.preview.setFixedHeight(130)
        self._style_preview(clr)
        root.addWidget(self.preview)

        self.build_table()

    def _style_preview(self, clr=None):
        if clr is None:
            clr = _tabular_colors()
        self.preview.setStyleSheet(
            f"background:{clr['prev_bg']}; color:{clr['prev_fg']}; "
            f"border:1px solid {clr['prev_bdr']}; padding:4px;")

    # ── Build / rebuild table ─────────────────────────────────
    def build_table(self):
        self._updating = True
        clr = _tabular_colors()

        rows = self.num_rows + 1
        cols = self.num_cols + 1

        self.table.clearSpans()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        # Headers stay visible (set up in setup_ui for resize handles);
        # just keep section count in sync — no need to touch visibility here.

        # Table-wide default: DataDelegate (suppresses native editor context menu)
        self.table.setItemDelegate(DataDelegate(self.table))
        # Row 0 and col 0 override with combo delegates
        self.table.setItemDelegateForRow(0, ComboDelegate(self.ALIGN_OPTIONS, self.table))
        self.table.setItemDelegateForColumn(0, ComboDelegate(self._border_options(), self.table))

        self.table.setRowHeight(0, 28)
        for r in range(1, rows):
            self.table.setRowHeight(r, 26)
        self.table.setColumnWidth(0, 185)

        # Corner cell
        corner = QTableWidgetItem(" border / align")
        corner.setToolTip(
            "Top row = column alignment (l, c, r, p{..}, X)\n"
            "Left column = row border\n"
            "Right-click header row for column borders\n"
            "Right-click data cells for multicolumn/multirow/cline")
        corner.setFlags(Qt.NoItemFlags)
        corner.setBackground(QBrush(clr['header_bg']))
        corner.setForeground(QBrush(clr['header_fg']))
        corner.setFont(QFont("", 7))
        corner.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(0, 0, corner)

        # Alignment header (row 0)
        for c in range(self.num_cols):
            item = QTableWidgetItem(self.col_alignments[c])
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QBrush(clr['header_bg']))
            item.setForeground(QBrush(clr['header_fg']))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            font = QFont(); font.setBold(True)
            item.setFont(font)
            self.table.setItem(0, c + 1, item)

        # Row-border header (col 0)
        for r in range(self.num_rows):
            item = QTableWidgetItem(self.row_borders[r])
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QBrush(clr['header_bg']))
            item.setForeground(QBrush(clr['header_fg']))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.table.setItem(r + 1, 0, item)

        # Data cells
        for r in range(self.num_rows):
            for c in range(self.num_cols):
                existing = self.table.item(r + 1, c + 1)
                txt = existing.text() if existing else ''
                item = QTableWidgetItem(txt)
                self.table.setItem(r + 1, c + 1, item)

        # Re-apply multicolumn spans
        for (r, c), mc in self.multicolumns.items():
            if 'span' in mc and r < self.num_rows and c < self.num_cols:
                self.table.setSpan(r + 1, c + 1, 1, mc['span'])

        # Re-apply multirow spans
        for (r, c), mr in self.multirows.items():
            if 'span' in mr and r < self.num_rows and c < self.num_cols:
                self.table.setSpan(r + 1, c + 1, mr['span'], 1)

        self._updating = False

        for c in range(self.num_cols):
            self._apply_col_style(c, reset_size=True)

        self._apply_header_strip_style()
        self.update_preview()

    # ── Per-column style ──────────────────────────────────────
    def _apply_col_style(self, data_col, reset_size=False):
        """Apply colours/alignment to a data column.
        reset_size=True resets the column width to the alignment default
        (used on initial build and on alignment change); False preserves
        whatever width the user has dragged it to.
        """
        if data_col >= self.num_cols:
            return
        clr = _tabular_colors()
        align_str = self.col_alignments[data_col]
        qt_align, col_w = self._align_to_qt(align_str)
        table_col = data_col + 1

        if reset_size:
            self.table.setColumnWidth(table_col, col_w)

        for r in range(self.num_rows):
            item = self.table.item(r + 1, table_col)
            if item is None:
                item = QTableWidgetItem('')
                self.table.setItem(r + 1, table_col, item)

            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            bg = clr['data_bg'] if r % 2 == 0 else clr['alt_bg']
            item.setBackground(QBrush(bg))
            item.setForeground(QBrush(clr['data_fg']))
            item.setTextAlignment(int(qt_align))

        hdr = self.table.item(0, table_col)
        if hdr:
            hdr.setBackground(QBrush(clr['header_bg']))

    # ── Cell-change handler ───────────────────────────────────
    def on_cell_changed(self, row, col):
        if self._updating:
            return
        item = self.table.item(row, col)
        if not item:
            return
        text = item.text().strip()

        if row == 0 and col > 0:
            idx = col - 1
            if idx < len(self.col_alignments):
                self.col_alignments[idx] = text
                self._apply_col_style(idx, reset_size=True)

        elif col == 0 and row > 0:
            idx = row - 1
            if idx < len(self.row_borders):
                import re
                m = re.search(r'\{(\d+)-(\d+)\}', text)
                if m:
                    self.cline_ranges[idx] = (int(m.group(1)), int(m.group(2)))
                    placeholder = (r'\cmidrule(lr){…}' if self.use_booktabs
                                   else r'\cline{…}')
                    text = placeholder
                    self._updating = True
                    item.setText(text)
                    self._updating = False
                self.row_borders[idx] = text
                # Auto-enable booktabs if a booktabs command is used
                if text in self.BOOKTABS_TRIGGERS and not self.use_booktabs:
                    self.booktabs_cb.setChecked(True)

        self.update_preview()
        self.table.viewport().update()

    # ── Dimension apply ───────────────────────────────────────
    def apply_dimensions(self):
        nr = self.rows_spin.value()
        nc = self.cols_spin.value()

        saved = {}
        for r in range(self.num_rows):
            for c in range(self.num_cols):
                it = self.table.item(r + 1, c + 1)
                if it:
                    saved[(r, c)] = it.text()

        self.num_rows = nr
        self.num_cols = nc

        self.col_alignments    = (self.col_alignments    + ['c'] * nc)[:nc]
        self.col_left_borders  = (self.col_left_borders  + [0] * nc)[:nc]
        self.col_right_borders = (self.col_right_borders + [0] * nc)[:nc]
        self.row_borders       = (self.row_borders       + ['none'] * nr)[:nr]
        self.cline_ranges      = {k: v for k, v in self.cline_ranges.items() if k < nr}
        self.multicolumns      = {k: v for k, v in self.multicolumns.items()
                                  if k[0] < nr and k[1] < nc}
        self.multirows         = {k: v for k, v in self.multirows.items()
                                  if k[0] < nr and k[1] < nc}

        self.build_table()

        self._updating = True
        for (r, c), txt in saved.items():
            if r < nr and c < nc:
                self.table.setItem(r + 1, c + 1, QTableWidgetItem(txt))
        self._updating = False
        self.update_preview()

    # ── Booktabs ──────────────────────────────────────────────
    def on_booktabs_toggled(self, checked):
        self.use_booktabs = checked
        self.table.setItemDelegateForColumn(0, ComboDelegate(self._border_options(), self.table))
        self.update_preview()

    # ── Refresh after theme change ────────────────────────────
    def refresh_theme(self):
        clr = _tabular_colors()
        self._style_preview(clr)
        self._updating = True
        for c in range(self.num_cols):
            hdr = self.table.item(0, c + 1)
            if hdr:
                hdr.setBackground(QBrush(clr['header_bg']))
                hdr.setForeground(QBrush(clr['header_fg']))
        for r in range(self.num_rows):
            bdr = self.table.item(r + 1, 0)
            if bdr:
                bdr.setBackground(QBrush(clr['header_bg']))
                bdr.setForeground(QBrush(clr['header_fg']))
        self._updating = False
        for c in range(self.num_cols):
            self._apply_col_style(c)
        self._apply_header_strip_style()
        self.table.viewport().update()

    def _apply_header_strip_style(self):
        """Re-style the thin resize-handle header strips to match the theme.
        Text is hidden by setting color == background — avoids font-size:0
        which triggers QFont::setPixelSize<=0 warnings and an infinite repaint loop.
        """
        clr = _tabular_colors()
        bg = clr['header_bg']
        r0, g0, b0 = bg.red(), bg.green(), bg.blue()
        rh = min(255, int(r0 * 0.85))
        gh = min(255, int(g0 * 0.92))
        bh = min(255, int(b0 * 1.10))
        normal = 'rgb(%d,%d,%d)' % (r0, g0, b0)
        hover  = 'rgb(%d,%d,%d)' % (rh, gh, bh)
        hh_style = (
            'QHeaderView { background: ' + normal + '; border: none; }'
            'QHeaderView::section:horizontal {'
            '  background: ' + normal + '; color: ' + normal + ';'
            '  border: none; padding: 0px; }'
            'QHeaderView::section:horizontal:hover {'
            '  background: ' + hover + '; color: ' + hover + '; }'
        )
        vh_style = (
            'QHeaderView { background: ' + normal + '; border: none; }'
            'QHeaderView::section:vertical {'
            '  background: ' + normal + '; color: ' + normal + ';'
            '  border: none; padding: 0px; }'
            'QHeaderView::section:vertical:hover {'
            '  background: ' + hover + '; color: ' + hover + '; }'
        )
        self.table.horizontalHeader().setStyleSheet(hh_style)
        self.table.verticalHeader().setStyleSheet(vh_style)

    # ── Safe span reset (Qt rejects setSpan(r,c,1,1)) ────────
    def _clear_span(self, table_row, table_col):
        """Collapse a merged cell back to 1×1 without triggering Qt's warning.
        Rebuilds the entire span table minus the target cell.
        """
        keep_mc = {k: v for k, v in self.multicolumns.items()
                   if 'span' in v and (k[0] + 1 != table_row or k[1] + 1 != table_col)}
        keep_mr = {k: v for k, v in self.multirows.items()
                   if 'span' in v and (k[0] + 1 != table_row or k[1] + 1 != table_col)}

        self.table.clearSpans()
        for (dr, dc), mc in keep_mc.items():
            self.table.setSpan(dr + 1, dc + 1, 1, mc['span'])
        for (dr, dc), mr in keep_mr.items():
            self.table.setSpan(dr + 1, dc + 1, mr['span'], 1)

    # ── Single unified context menu ───────────────────────────
    def show_context_menu(self, pos):
        menu = QMenu(self)

        clicked_item = self.table.itemAt(pos)
        if clicked_item is None:
            return
        click_row = self.table.row(clicked_item)
        click_col = self.table.column(clicked_item)

        data_r = max(0, click_row - 1)
        data_c = max(0, click_col - 1)

        # ── Resolve span extents for border targeting ─────────────────
        # If the clicked cell is inside a multicolumn span, the RIGHT border
        # must go on the LAST column of the span (not the clicked col).
        # If inside a multirow span, the BOTTOM border goes on the LAST row.
        border_col = data_c   # default: right border on clicked col
        border_row = data_r   # default: bottom border on clicked row

        # Find the anchor of any multicolumn covering this cell (same row)
        for tc in range(data_c, -1, -1):
            mc = self.multicolumns.get((data_r, tc), {})
            if 'span' in mc and tc + mc['span'] > data_c:
                border_col = tc + mc['span'] - 1
                break

        # Find the anchor of any multirow covering this cell (same col)
        for tr in range(data_r, -1, -1):
            mr = self.multirows.get((tr, data_c), {})
            if 'span' in mr and tr + mr['span'] > data_r:
                border_row = tr + mr['span'] - 1
                break

        # ── Section: Column borders ───────────────────────────────────
        menu.addSection(f"Column {data_c + 1} borders")

        left_sub  = menu.addMenu(f"Left border  (col {data_c + 1})")
        right_sub = menu.addMenu(f"Right border (col {border_col + 1})")
        left_acts  = {}
        right_acts = {}
        for label, val in [("None", 0), ("Single  |", 1), ("Double  ||", 2)]:
            a = left_sub.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.col_left_borders[data_c] == val)
            left_acts[a] = val
            b = right_sub.addAction(label)
            b.setCheckable(True)
            b.setChecked(self.col_right_borders[border_col] == val)
            right_acts[b] = val

        # Global right border lives inside the right-border submenu
        # right_sub.addSeparator()
        # rb_act = right_sub.addAction("Global table right border  |")
        # rb_act.setCheckable(True)
        # rb_act.setChecked(self.right_border)

        # ── Section: Row borders ──────────────────────────────────────
        menu.addSection(f"Row {data_r + 1} borders")

        top_sub = menu.addMenu(f"Top border  (row {data_r + 1})")
        bot_sub = menu.addMenu(f"Bottom border (row {border_row + 1})")
        top_border_acts = {}
        bot_border_acts = {}
        top_cline_acts  = set()
        bot_cline_acts  = set()

        _cline_labels = {r'\cline{…}', r'\cmidrule(lr){…}'}

        for opt in self._border_options():
            label = opt if opt != 'none' else 'none  (no rule)'
            # Top border — always on clicked row
            a = top_sub.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.row_borders[data_r] == opt)
            if opt in _cline_labels:
                top_cline_acts.add(a)
            else:
                top_border_acts[a] = opt
            # Bottom border — on last row of span
            b = bot_sub.addAction(label)
            b.setCheckable(True)
            cur_bot = (self.bottom_border if border_row == self.num_rows - 1
                       else self.row_borders[border_row + 1])
            b.setChecked(cur_bot == opt)
            if opt in _cline_labels:
                bot_cline_acts.add(b)
            else:
                bot_border_acts[b] = opt

        # ── Section: Merge cells ──────────────────────────────────────
        menu.addSection("Merge cells")

        mc_in = self.multicolumns.get((data_r, data_c), {})
        mr_in = self.multirows.get((data_r, data_c), {})

        mc_act    = menu.addAction(r"\multicolumn — merge columns (set range)…")
        rm_mc_act = menu.addAction(r"Remove \multicolumn")
        rm_mc_act.setEnabled(bool(mc_in) and not mc_in.get('skip'))

        mr_act    = menu.addAction(r"\multirow — merge rows (set range)…")
        rm_mr_act = menu.addAction(r"Remove \multirow")
        rm_mr_act.setEnabled(bool(mr_in) and not mr_in.get('skip'))

        # ── Execute ───────────────────────────────────────────────────
        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        # Column left border
        if chosen in left_acts:
            self.col_left_borders[data_c] = left_acts[chosen]
            self.update_preview()
            self.table.viewport().update()
            return

        # Column right border — on last col of span
        if chosen in right_acts:
            self.col_right_borders[border_col] = right_acts[chosen]
            self.update_preview()
            self.table.viewport().update()
            return

        # Global right border toggle
        # if chosen == rb_act:
            # self.right_border = not self.right_border
            # self.update_preview()
            # self.table.viewport().update()
            # return

        # Top border — cline/cmidrule → open range dialog
        if chosen in top_cline_acts:
            self._pick_cline_range(data_r, target='top')
            return

        # Top border — plain rule
        if chosen in top_border_acts:
            val = top_border_acts[chosen]
            self._apply_row_border(data_r, val)
            return

        # Bottom border — cline/cmidrule → open range dialog on last row of span
        if chosen in bot_cline_acts:
            target_r = self.num_rows if border_row == self.num_rows - 1 else border_row + 1
            self._pick_cline_range(target_r)
            return

        # Bottom border — plain rule on last row of span
        if chosen in bot_border_acts:
            val = bot_border_acts[chosen]
            if border_row == self.num_rows - 1:
                self.bottom_border = val
                self.update_preview()
                self.table.viewport().update()
            else:
                self._apply_row_border(border_row + 1, val)
            return

        # \multicolumn
        if chosen == mc_act:
            self._do_multicolumn(data_r, data_c)
            return

        # Remove \multicolumn
        if chosen == rm_mc_act:
            span = mc_in.get('span', 1)
            self._updating = True
            for ci in range(span):
                self.multicolumns.pop((data_r, data_c + ci), None)
            self._clear_span(data_r + 1, data_c + 1)
            self._updating = False
            self.update_preview()
            return

        # \multirow
        if chosen == mr_act:
            self._do_multirow(data_r, data_c)
            return

        # Remove \multirow
        if chosen == rm_mr_act:
            span = mr_in.get('span', 1)
            self._updating = True
            for ri in range(span):
                self.multirows.pop((data_r + ri, data_c), None)
            self._clear_span(data_r + 1, data_c + 1)
            self._updating = False
            self.update_preview()

    # ── Helper: apply a plain (non-cline) border to a row ────
    def _apply_row_border(self, data_row, val):
        self.row_borders[data_row] = val
        self._updating = True
        it = self.table.item(data_row + 1, 0)
        if it:
            it.setText(val)
        self._updating = False
        if val in self.BOOKTABS_TRIGGERS and not self.use_booktabs:
            self.booktabs_cb.setChecked(True)
        self.update_preview()
        self.table.viewport().update()

    # ── \multicolumn range dialog ─────────────────────────────
    def _do_multicolumn(self, data_r, data_c):
        """Dialog: starting col (pre-filled), ending col, alignment → apply."""
        d = QDialog(self)
        d.setWindowTitle(r'\multicolumn — set column range')
        form = QFormLayout(d)

        start_sp = QSpinBox(); start_sp.setRange(1, self.num_cols); start_sp.setValue(data_c + 1)
        end_sp   = QSpinBox(); end_sp.setRange(1, self.num_cols);   end_sp.setValue(min(data_c + 2, self.num_cols))
        align_cb = QComboBox(); align_cb.addItems(['c', 'l', 'r'])

        # Pre-fill from existing multicolumn if present
        existing = self.multicolumns.get((data_r, data_c), {})
        if 'span' in existing:
            end_sp.setValue(data_c + existing['span'])
            idx = align_cb.findText(existing.get('align', 'c'))
            if idx >= 0:
                align_cb.setCurrentIndex(idx)

        form.addRow("Start column (1-based):", start_sp)
        form.addRow("End column   (1-based):", end_sp)
        form.addRow("Alignment:", align_cb)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(d.accept); btns.rejected.connect(d.reject)
        form.addRow(btns)

        if d.exec_() != QDialog.Accepted:
            return

        c0    = start_sp.value() - 1
        c1    = end_sp.value() - 1
        if c1 < c0:
            c0, c1 = c1, c0
        span  = c1 - c0 + 1
        align = align_cb.currentText()

        # Clear old entries for that row before applying new span
        for ci in range(self.num_cols):
            self.multicolumns.pop((data_r, ci), None)
        self._clear_span(data_r + 1, c0 + 1)

        self._updating = True
        self.multicolumns[(data_r, c0)] = {'span': span, 'align': align}
        for ci in range(1, span):
            self.multicolumns[(data_r, c0 + ci)] = {'skip': True}
        self.table.setSpan(data_r + 1, c0 + 1, 1, span)
        self._updating = False
        self.update_preview()

    # ── \multirow range dialog ────────────────────────────────
    def _do_multirow(self, data_r, data_c):
        """Dialog: starting row (pre-filled), ending row, width → apply."""
        d = QDialog(self)
        d.setWindowTitle(r'\multirow — set row range')
        form = QFormLayout(d)

        start_sp = QSpinBox(); start_sp.setRange(1, self.num_rows); start_sp.setValue(data_r + 1)
        end_sp   = QSpinBox(); end_sp.setRange(1, self.num_rows);   end_sp.setValue(min(data_r + 2, self.num_rows))
        width_ed = QLineEdit('*')

        # Pre-fill from existing multirow if present
        existing = self.multirows.get((data_r, data_c), {})
        if 'span' in existing:
            end_sp.setValue(data_r + existing['span'])
            width_ed.setText(existing.get('width', '*'))

        form.addRow("Start row (1-based):", start_sp)
        form.addRow("End row   (1-based):", end_sp)
        form.addRow("Width (e.g. * or 3cm):", width_ed)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(d.accept); btns.rejected.connect(d.reject)
        form.addRow(btns)

        if d.exec_() != QDialog.Accepted:
            return

        r0    = start_sp.value() - 1
        r1    = end_sp.value() - 1
        if r1 < r0:
            r0, r1 = r1, r0
        span  = r1 - r0 + 1
        width = width_ed.text().strip() or '*'

        # Clear old entries for that column before applying new span
        for ri in range(self.num_rows):
            self.multirows.pop((ri, data_c), None)
        self._clear_span(r0 + 1, data_c + 1)

        self._updating = True
        self.multirows[(r0, data_c)] = {'span': span, 'width': width}
        for ri in range(1, span):
            self.multirows[(r0 + ri, data_c)] = {'skip': True}
        self.table.setSpan(r0 + 1, data_c + 1, span, 1)
        self._updating = False
        self.update_preview()

    # ── \cline range picker dialog ────────────────────────────
    def _pick_cline_range(self, data_row, target='top'):
        """Open the cline/cmidrule range dialog.
        target='top'  → sets row_borders[data_row] (rule above that row).
        target_row == self.num_rows means the global bottom_border.
        """
        placeholder = r'\cmidrule(lr){…}' if self.use_booktabs else r'\cline{…}'
        rule = r'\cmidrule' if self.use_booktabs else r'\cline'
        is_bottom_border = (data_row >= self.num_rows)

        title = (f'{rule} range — bottom of table'
                 if is_bottom_border
                 else f'{rule} range — above row {data_row + 1}')
        d = QDialog(self)
        d.setWindowTitle(title)
        form = QFormLayout(d)

        lo_sp = QSpinBox(); lo_sp.setRange(1, self.num_cols)
        hi_sp = QSpinBox(); hi_sp.setRange(1, self.num_cols); hi_sp.setValue(self.num_cols)
        prev_lo, prev_hi = self.cline_ranges.get(data_row, (1, self.num_cols))
        lo_sp.setValue(prev_lo); hi_sp.setValue(prev_hi)

        form.addRow("From column:", lo_sp)
        form.addRow("To column:",   hi_sp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(d.accept); btns.rejected.connect(d.reject)
        form.addRow(btns)

        if d.exec_() != QDialog.Accepted:
            return

        self.cline_ranges[data_row] = (lo_sp.value(), hi_sp.value())
        if is_bottom_border:
            self.bottom_border = placeholder
        else:
            self.row_borders[data_row] = placeholder
            self._updating = True
            it = self.table.item(data_row + 1, 0)
            if it:
                it.setText(placeholder)
            self._updating = False
        self.update_preview()
        self.table.viewport().update()

    # ── LaTeX generation ──────────────────────────────────────
    def generate_latex(self):
        lines = []
        if self.use_booktabs:
            lines.append('%\\usepackage{booktabs}')

        # Column spec
        spec_parts = []
        for i in range(self.num_cols):
            if self.col_left_borders[i] == 1:
                spec_parts.append('|')
            elif self.col_left_borders[i] == 2:
                spec_parts.append('||')
            spec_parts.append(self.col_alignments[i])
            if self.col_right_borders[i] == 1:
                spec_parts.append('|')
            elif self.col_right_borders[i] == 2:
                spec_parts.append('||')
        spec = ''.join(spec_parts)
        if self.right_border:
            spec += '|'

        lines.append(f'\\begin{{tabular}}{{{spec}}}')

        for r in range(self.num_rows):
            cmd = self._border_to_latex(self.row_borders[r], r)
            if cmd:
                lines.append(cmd)

            parts = []
            c = 0
            while c < self.num_cols:
                mc = self.multicolumns.get((r, c))
                if mc and mc.get('skip'):
                    c += 1
                    continue
                mr = self.multirows.get((r, c))
                if mr and mr.get('skip'):
                    parts.append('')
                    c += 1
                    continue

                it = self.table.item(r + 1, c + 1)
                content = it.text() if it else ''

                if mc and 'span' in mc:
                    cell_text = f"\\multicolumn{{{mc['span']}}}{{{mc['align']}}}{{{content}}}"
                    c += mc['span']
                elif mr and 'span' in mr:
                    width = mr.get('width', '*')
                    cell_text = f"\\multirow{{{mr['span']}}}{{{width}}}{{{content}}}"
                    c += 1
                else:
                    cell_text = content
                    c += 1
                parts.append(cell_text)

            lines.append('  ' + ' & '.join(parts) + r'  \\')

        bot = self._border_to_latex(self.bottom_border, self.num_rows)
        if bot:
            lines.append(bot)
        lines.append('\\end{tabular}')
        return '\n'.join(lines)

    def update_preview(self):
        if self._updating:
            return
        try:
            self.preview.setPlainText(self.generate_latex())
        except Exception as e:
            self.preview.setPlainText(f'% Error: {e}')

    # ── Insert to editor ──────────────────────────────────────
    def insert_to_editor(self):
        try:
            latex = self.generate_latex()
            if hasattr(self.main_window, 'editor_manager'):
                ed = self.main_window.editor_manager.get_active_editor()
                if ed:
                    ed.textCursor().insertText(latex)
                    ed.setFocus()
                    if hasattr(self.main_window.editor_manager, 'on_text_changed'):
                        self.main_window.editor_manager.on_text_changed()
                    return
            QMessageBox.warning(self, 'Warning', 'No active editor found.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))            
            
class ScientificCalculator(QWidget):
    """Scientific calculator with result insertion"""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.current_input = ""
        self.result = ""
        self.setup_ui()
    
    def setup_ui(self):
        from style_manager import get_button_style
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # --- 3D frame around the display ---
        display_frame = QFrame()
        display_frame.setFrameShape(QFrame.Box)
        #display_frame.setFrameShape(QFrame.Panel)   # Panel shape
        display_frame.setFrameShadow(QFrame.Sunken)  # Sunken gives a recessed 3D look
        display_frame.setLineWidth(2)               # Width of the frame border
        #display_frame.setMidLineWidth(1)            # Optional: creates an extra line for a "groove" effect

        display_frame.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                 stop:0 #9a9a9a,
                                                 stop:1 #8a8a8a);
                border-top: 2px solid #7a7a7a;
                border-left: 2px solid #7a7a7a;
                border-right: 2px solid #9a9a9a;
                border-bottom: 2px solid #9a9a9a;
                border-radius: 4px;
            }
        """)

        # Layout inside the frame to hold the display
        frame_layout = QVBoxLayout(display_frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)  # Small margin between frame and display        
        
        # Display
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setMinimumHeight(40)
        font = QFont("Courier", 12)
        self.display.setFont(font)
        #self.display.setStyleSheet("background: white; padding: 5px;")
        self.display.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #00ffaa;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px;
            }
        """)        
        frame_layout.addWidget(self.display)
        
        # Add the framed display to the main layout
        layout.addWidget(display_frame)        
        
        # ✅ Two buttons: Insert to Editor and Insert from Editor
        buttons_layout = QHBoxLayout()
        
        insert_to_btn = QPushButton("📝 Insert to Editor")
        insert_to_btn.clicked.connect(self.insert_result_to_editor)
        insert_to_btn.setMinimumHeight(30)
        insert_to_btn.setToolTip("Insert calculator result into the editor")
        buttons_layout.addWidget(insert_to_btn)
        
        insert_from_btn = QPushButton("📥 Insert from Editor")
        insert_from_btn.clicked.connect(self.insert_from_editor)
        insert_from_btn.setMinimumHeight(30)
        insert_from_btn.setToolTip("Copy selected number from editor to calculator")
        buttons_layout.addWidget(insert_from_btn)
        
        layout.addLayout(buttons_layout)
        
        # Calculator buttons
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(2)
        
        # Button definitions: (text, row, col, colspan, style)
        buttons = [
            ('C', 0, 0, 1, 'clear'), ('⌫', 0, 1, 1, 'clear'), ('(', 0, 2, 1, 'op'), (')', 0, 3, 1, 'op'),
            ('sin', 1, 0, 1, 'func'), ('cos', 1, 1, 1, 'func'), ('tan', 1, 2, 1, 'func'), ('/', 1, 3, 1, 'op'),
            ('7', 2, 0, 1, 'num'), ('8', 2, 1, 1, 'num'), ('9', 2, 2, 1, 'num'), ('*', 2, 3, 1, 'op'),
            ('4', 3, 0, 1, 'num'), ('5', 3, 1, 1, 'num'), ('6', 3, 2, 1, 'num'), ('-', 3, 3, 1, 'op'),
            ('1', 4, 0, 1, 'num'), ('2', 4, 1, 1, 'num'), ('3', 4, 2, 1, 'num'), ('+', 4, 3, 1, 'op'),
            ('0', 5, 0, 1, 'num'), ('.', 5, 1, 1, 'num'), ('π', 5, 2, 1, 'const'), ('=', 5, 3, 1, 'equals'),
            ('sqrt', 6, 0, 1, 'func'), ('^', 6, 1, 1, 'op'), ('log', 6, 2, 1, 'func'), ('ln', 6, 3, 1, 'func'),
        ]
        
        # Replace the per-style setStyleSheet calls in the buttons loop:
        for btn_text, row, col, colspan, style in buttons:
            btn = QPushButton(btn_text)
            btn.setMinimumHeight(35)
            btn.clicked.connect(lambda checked, t=btn_text: self.on_button_click(t))

            if style == 'num':
                btn.setProperty('calc_style', 'num')
            elif style == 'op':
                btn.setProperty('calc_style', 'op')
            elif style == 'func':
                btn.setProperty('calc_style', 'func')
            elif style == 'const':
                btn.setProperty('calc_style', 'const')
            elif style == 'equals':
                btn.setProperty('calc_style', 'equals')
            elif style == 'clear':
                btn.setProperty('calc_style', 'clear')

            buttons_layout.addWidget(btn, row, col, 1, colspan)

        # After the loop, apply styles via the helper:
        self._apply_calc_button_styles()
        layout.addLayout(buttons_layout)

    def _apply_calc_button_styles(self):
        """Apply theme-aware styles to all calculator buttons."""
        from style_manager import get_button_style, _current_theme

        # Base colors per theme for each calculator button role
        _CALC_COLORS = {
            "default":  {
                "num":    ("background:#f0f0f0; font-weight:bold;", ),
                "op":     ("background:#ffa500; color:white; font-weight:bold;", ),
                "func":   ("background:#4CAF50; color:white;", ),
                "const":  ("background:#2196F3; color:white;", ),
                "equals": ("background:#f44336; color:white; font-weight:bold;", ),
                "clear":  ("background:#9E9E9E; color:white;", ),
            },
            "dark": {
                "num":    ("background:#3c3f41; color:#bbbbbb; font-weight:bold;", ),
                "op":     ("background:#b36b00; color:white; font-weight:bold;", ),
                "func":   ("background:#2d6e2d; color:white;", ),
                "const":  ("background:#1a4f8a; color:white;", ),
                "equals": ("background:#8b2020; color:white; font-weight:bold;", ),
                "clear":  ("background:#555759; color:white;", ),
            },
            "light": {
                "num":    ("background:#f0f0f0; font-weight:bold;", ),
                "op":     ("background:#e69500; color:white; font-weight:bold;", ),
                "func":   ("background:#3d9e3d; color:white;", ),
                "const":  ("background:#1a7acc; color:white;", ),
                "equals": ("background:#cc2200; color:white; font-weight:bold;", ),
                "clear":  ("background:#808080; color:white;", ),
            },
            "midnight": {
                "num":    ("background:#21262d; color:#c9d1d9; font-weight:bold;", ),
                "op":     ("background:#9a4f00; color:white; font-weight:bold;", ),
                "func":   ("background:#196c2e; color:white;", ),
                "const":  ("background:#0d419d; color:white;", ),
                "equals": ("background:#8b1a1a; color:white; font-weight:bold;", ),
                "clear":  ("background:#30363d; color:#c9d1d9;", ),
            },
        }

        colors = _CALC_COLORS.get(_current_theme, _CALC_COLORS["default"])

        # Find the grid layout containing calc buttons
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, type(self.layout())) or item is None:
                continue
            widget = item.widget()
            if widget is None:
                # It's a layout item (QGridLayout for buttons)
                layout_item = item.layout() if hasattr(item, 'layout') else None

        # Walk all QPushButton children that have calc_style property
        for btn in self.findChildren(QPushButton):
            calc_style = btn.property('calc_style')
            if calc_style and calc_style in colors:
                btn.setStyleSheet(f"QPushButton {{ {colors[calc_style][0]} }}")

    def refresh_button_styles(self):
        """Called by theme switcher to refresh all calculator button styles."""
        self._apply_calc_button_styles()
    
    def on_button_click(self, text):
        if text == 'C':
            self.current_input = ""
            self.result = ""
        elif text == '⌫':
            self.current_input = self.current_input[:-1]
        elif text == '=':
            self.calculate()
        elif text == 'π':
            self.current_input += str(math.pi)
        elif text in ['sin', 'cos', 'tan', 'sqrt', 'log', 'ln']:
            self.current_input += text + '('
        elif text == '^':
            self.current_input += '**'
        else:
            self.current_input += text
        
        self.display.setText(self.current_input if self.current_input else self.result)
    
    def calculate(self):
        try:
            # Replace functions with math module equivalents
            expression = self.current_input
            expression = expression.replace('sin(', 'math.sin(')
            expression = expression.replace('cos(', 'math.cos(')
            expression = expression.replace('tan(', 'math.tan(')
            expression = expression.replace('sqrt(', 'math.sqrt(')
            expression = expression.replace('log(', 'math.log10(')
            expression = expression.replace('ln(', 'math.log(')
            
            result = eval(expression)
            self.result = str(result)
            self.display.setText(f"{self.current_input} = {self.result}")
            self.current_input = self.result
        except Exception as e:
            self.display.setText(f"Error: {str(e)}")
            self.result = ""
    
    def insert_result_to_editor(self):
        """Insert calculator result into the active editor"""
        if not self.result:
            QMessageBox.information(self, "Info", "No result to insert. Calculate first!")
            return
        
        try:
            # Get active editor
            if hasattr(self.main_window, 'editor_manager'):
                active_editor = self.main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    cursor.insertText(self.result)
                    active_editor.setFocus()
                    #print(f"✅ Inserted result: {self.result}")
                    # Mark as modified
                    self.main_window.editor_manager.on_text_changed()

                else:
                    QMessageBox.warning(self, "Warning", "No active editor found!")
            else:
                QMessageBox.warning(self, "Warning", "Editor manager not available!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert result:\n{str(e)}")
    
    def insert_from_editor(self):
        """Copy selected number from editor to calculator"""
        try:
            # Get active editor
            if hasattr(self.main_window, 'editor_manager'):
                active_editor = self.main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    selected_text = cursor.selectedText().strip()
                    
                    if not selected_text:
                        QMessageBox.information(self, "Info", "Please select a number in the editor first!")
                        return
                    
                    # Try to validate it's a number or expression
                    try:
                        # Test if it's a valid number/expression
                        float(selected_text.replace(',', '.'))
                        # If valid, set as current input
                        self.current_input = selected_text.replace(',', '.')
                        self.display.setText(self.current_input)
                        #print(f"✅ Inserted from editor: {self.current_input}")
                    except ValueError:
                        # Maybe it's an expression, just paste it
                        self.current_input = selected_text
                        self.display.setText(self.current_input)
                        print(f"✅ Inserted expression from editor: {self.current_input}")
                else:
                    QMessageBox.warning(self, "Warning", "No active editor found!")
            else:
                QMessageBox.warning(self, "Warning", "Editor manager not available!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert from editor:\n{str(e)}")


class CalendarWidget(QWidget):
    """Calendar with date/time insertion"""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        
        # ✅ Set to show full month and highlight today
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.calendar.setMinimumDate(QDate(1900, 1, 1))
        self.calendar.setMaximumDate(QDate(2100, 12, 31))
        
        # ✅ Style today's date with background color
        from PyQt5.QtGui import QTextCharFormat, QColor, QBrush
        today_format = QTextCharFormat()
        today_format.setBackground(QBrush(QColor(135, 206, 250)))  # Light blue
        today_format.setForeground(QBrush(QColor(0, 0, 0)))  # Black text
        self.calendar.setDateTextFormat(QDate.currentDate(), today_format)
        
        

        # ✅ Create a custom format for Friday
        friday_format = QTextCharFormat()        
        friday_format.setForeground(QBrush(QColor(76, 155, 80)))  # Blue text (choose any color)
        saturday_format = QTextCharFormat()
        saturday_format.setForeground(QBrush(QColor(0, 0, 0))) 

        # Apply it only to Friday
        self.calendar.setWeekdayTextFormat(Qt.Friday, friday_format)
        self.calendar.setWeekdayTextFormat(Qt.Saturday, saturday_format)

        
        self.calendar.clicked.connect(self.on_date_selected)
        layout.addWidget(self.calendar)
        
        # Selected date display
        info_layout = QHBoxLayout()
        self.date_label = QLabel("Selected: " + QDate.currentDate().toString("yyyy-MM-dd"))
        self.date_label.setStyleSheet("font-weight: bold; padding: 5px;")
        info_layout.addWidget(self.date_label)
        layout.addLayout(info_layout)
        
        # Options
        self.include_time_checkbox = QCheckBox("Include current time")
        self.include_time_checkbox.setChecked(False)
        layout.addWidget(self.include_time_checkbox)
        
        # Insert buttons
        buttons_layout = QHBoxLayout()
        
        insert_date_btn = QPushButton("📅 Insert Date")
        insert_date_btn.clicked.connect(self.insert_date_to_editor)
        insert_date_btn.setMinimumHeight(30)
        buttons_layout.addWidget(insert_date_btn)
        
        insert_today_btn = QPushButton("📆 Insert Today")
        insert_today_btn.clicked.connect(self.insert_today_to_editor)
        insert_today_btn.setMinimumHeight(30)
        buttons_layout.addWidget(insert_today_btn)
        
        layout.addLayout(buttons_layout)
    
    def on_date_selected(self, date):
        """Update label when date is clicked"""
        self.date_label.setText(f"Selected: {date.toString('yyyy-MM-dd')}")
    
    def insert_date_to_editor(self):
        """Insert selected date into editor"""
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        if self.include_time_checkbox.isChecked():
            time_str = QTime.currentTime().toString("HH:mm:ss")
            date_str = f"{date_str} {time_str}"
        
        self._insert_text(date_str)
        # Mark as modified
        self.main_window.editor_manager.on_text_changed()

    
    def insert_today_to_editor(self):
        """Insert today's date into editor"""
        date_str = QDate.currentDate().toString("yyyy-MM-dd")
        
        if self.include_time_checkbox.isChecked():
            time_str = QTime.currentTime().toString("HH:mm:ss")
            date_str = f"{date_str} {time_str}"
        
        self._insert_text(date_str)
        # Mark as modified
        self.main_window.editor_manager.on_text_changed()        
    
    def _insert_text(self, text):
        """Helper to insert text into active editor"""
        try:
            if hasattr(self.main_window, 'editor_manager'):
                active_editor = self.main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    cursor.insertText(text)
                    active_editor.setFocus()
                    #print(f"✅ Inserted date: {text}")
                    # Mark as modified
                    self.main_window.editor_manager.on_text_changed()
                else:
                    QMessageBox.warning(self, "Warning", "No active editor found!")
            else:
                QMessageBox.warning(self, "Warning", "Editor manager not available!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert date:\n{str(e)}")


class ToolsTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.image_widgets = []  # Track image widgets
        self.setup_ui()
    
    def setup_ui(self):
        from PyQt5.QtWidgets import QScrollArea
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ✅ IMAGE AREA - At the very top
        image_area_frame = QFrame()
        image_area_frame.setFrameShape(QFrame.StyledPanel)
        self.image_area_layout = QVBoxLayout(image_area_frame)
        self.image_area_layout.setContentsMargins(0, 0, 0, 0)

        
        # Container for multiple images
        self.images_container = QWidget()
        self.images_layout = QVBoxLayout(self.images_container)
        self.images_layout.setContentsMargins(0, 0, 0, 0)
        self.images_layout.setSpacing(5)  # Small gap between multiple images
        self.images_layout.setAlignment(Qt.AlignTop)  # Align images to top
        self.image_area_layout.addWidget(self.images_container)
        
        layout.addWidget(image_area_frame)
        
        # ✅ BUTTONS ROW - Modified with Open and Paste buttons
        tools_title = QLabel("Tools")
        tools_title.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                padding: 6px 4px;
            }
        """)
        tools_title.setAlignment(Qt.AlignLeft)

        layout.addWidget(tools_title)        
        tools_frame = QFrame()
        tools_frame.setFrameShape(QFrame.StyledPanel)
        tools_layout = QHBoxLayout(tools_frame)
        
        explorer_btn = QPushButton("📁 Explorer")
        explorer_btn.clicked.connect(self.open_explorer)
        explorer_btn.setMinimumHeight(35)
        tools_layout.addWidget(explorer_btn)
        
        browser_btn = QPushButton("🌐 Browser")
        browser_btn.clicked.connect(self.open_browser)
        browser_btn.setMinimumHeight(35)
        tools_layout.addWidget(browser_btn)
        
        paint_btn = QPushButton("🎨 Paint")
        paint_btn.clicked.connect(self.open_paint)
        paint_btn.setMinimumHeight(35)
        tools_layout.addWidget(paint_btn)
        
        # ✅ NEW: Open Image button
        open_image_btn = QPushButton("🖼️ Open Image")
        open_image_btn.clicked.connect(self.open_image)
        open_image_btn.setMinimumHeight(35)
        open_image_btn.setToolTip("Open image from file (JPG, PNG, BMP, SVG)")
        tools_layout.addWidget(open_image_btn)
        
        new_btn = QPushButton("🆕 New")
        new_btn.clicked.connect(self.new_blank_image)
        new_btn.setMinimumHeight(35)
        new_btn.setToolTip("Create a new blank white image")
        tools_layout.addWidget(new_btn)        
        
        # ✅ NEW: Paste Image button
        paste_image_btn = QPushButton("📋 Paste Image")
        paste_image_btn.clicked.connect(self.paste_image)
        paste_image_btn.setMinimumHeight(35)
        paste_image_btn.setToolTip("Paste image from clipboard")
        tools_layout.addWidget(paste_image_btn)
        
        layout.addWidget(tools_frame)
        
        # Rest of the existing UI (calculator, calendar)
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        layout.addWidget(self.create_separator())

        # ── Tabular Maker ──────────────────────────────────────────
        tabular_frame = QFrame()
        tabular_frame.setFrameShape(QFrame.StyledPanel)
        tabular_frame_layout = QVBoxLayout(tabular_frame)
        tabular_frame_layout.setContentsMargins(0, 0, 0, 0)
        tabular_title = QLabel("Tabular Maker")
        tabular_title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        tabular_frame_layout.addWidget(tabular_title)
        self.tabular_maker = TabularMaker(self.main_window)
        tabular_frame_layout.addWidget(self.tabular_maker)
        splitter.addWidget(tabular_frame)

        
        # Calculator
        calc_frame = QFrame()
        calc_frame.setFrameShape(QFrame.StyledPanel)
        calc_layout = QVBoxLayout(calc_frame)
        calc_layout.setContentsMargins(0, 0, 0, 0)
        calc_title = QLabel("Scientific Calculator")
        calc_title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        calc_layout.addWidget(calc_title)
        self.calculator = ScientificCalculator(self.main_window)
        calc_layout.addWidget(self.calculator)
        splitter.addWidget(calc_frame)
 
         
        splitter.setHandleWidth(8)        
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(150, 150, 150, 0.3);
            }
        """)

        layout.addWidget(splitter)

        
        # Calendar
        calendar_frame = QFrame()
        calendar_frame.setFrameShape(QFrame.StyledPanel)
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(0, 0, 0, 0)
        calendar_title = QLabel("Calendar")
        calendar_title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        calendar_layout.addWidget(calendar_title)
        self.calendar_widget = CalendarWidget(self.main_window)
        calendar_layout.addWidget(self.calendar_widget)
        splitter.addWidget(calendar_frame)
        
        splitter.setSizes([600, 400])
        # AFTER
        #splitter.setSizes([550, 550, 400])
        layout.addWidget(splitter)
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def refresh_styles(self):
        """Called by theme switcher to refresh all themed widgets."""
        # Refresh tabular maker colors
        if hasattr(self, 'tabular_maker'):
            self.tabular_maker.refresh_theme()
        
        # Refresh calculator button styles
        if hasattr(self, 'calculator'):
            self.calculator.refresh_button_styles()
        
    def new_blank_image(self):
        """Create a new blank white image and add it below existing images"""
        # Choose a default size (e.g., 800x650)
        width, height = 800, 650
        if self.image_widgets:
            # Optionally match the size of the last image
            last = self.image_widgets[-1]
            width = last.original_pixmap.width()
            height = last.original_pixmap.height()
        blank = QPixmap(width, height)
        blank.fill(Qt.white)
        self.add_image_widget(blank)
    

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        # 🔥 IMPORTANT: enforce real height
        line.setFixedHeight(8)

        line.setStyleSheet("""
            QFrame {
                border: none;
                background-color: rgba(150, 150, 150, 0.4);
                margin: 0px;
            }
        """)
        return line    
    # ✅ NEW METHOD: Open image from file
    def open_image(self):
        """Open image file and display it"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Image",
                "",
                "Image Files (*.jpg *.jpeg *.png *.bmp *.svg);;All Files (*)"
            )
            
            if file_path:
                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    QMessageBox.warning(self, "Error", "Failed to load image!")
                    return
                
                self.add_image_widget(pixmap)
                #print(f"✅ Opened image: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open image:\n{str(e)}")
    
    # ✅ NEW METHOD: Paste image from clipboard
    def paste_image(self):
        """Paste image from clipboard"""
        try:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasImage():
                image = clipboard.image()
                if image.isNull():
                    QMessageBox.information(self, "Info", "No valid image in clipboard!")
                    return
                
                pixmap = QPixmap.fromImage(image)
                self.add_image_widget(pixmap)
                #print("✅ Pasted image from clipboard")
            else:
                QMessageBox.information(self, "Info", "No image found in clipboard!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to paste image:\n{str(e)}")



    def reset_image_widget(self, old_widget, original_pixmap):
        """Replace an image widget with a fresh copy of the original"""
        index = self.images_layout.indexOf(old_widget)
        if index < 0:
            return
        # Remove old
        self.images_layout.removeWidget(old_widget)
        old_widget.deleteLater()
        if old_widget in self.image_widgets:
            self.image_widgets.remove(old_widget)
        # Create new
        new_widget = ResizableImageWidget(original_pixmap, tools_tab=self)
        self.images_layout.insertWidget(index, new_widget)
        self.image_widgets.append(new_widget)
        # Force layout update
        self.images_layout.activate()
        self.images_container.updateGeometry()
        #print("✅ Image widget reset")        

    
    # ✅ NEW METHOD: Add image widget to display area
    def add_image_widget(self, pixmap):
        """Add a resizable image widget to the images area"""
        try:
            #print(f"DEBUG add_image_widget called, existing count: {len(self.image_widgets)}")
            image_widget = ResizableImageWidget(pixmap, tools_tab=self)
            self.images_layout.addWidget(image_widget)
            self.image_widgets.append(image_widget)
            self.images_container.setMouseTracking(True)
            # Connect close signal to remove from list
            image_widget.destroyed.connect(lambda: self.remove_image_widget(image_widget))
            #print(f"✅ Added image widget id={id(image_widget)} (total: {len(self.image_widgets)})")
            
        except Exception as e:
            print(f"Error adding image widget: {e}")
    
    # ✅ NEW METHOD: Remove image widget from tracking
    def remove_image_widget(self, widget):
        """Remove image widget from tracking list"""
        if widget in self.image_widgets:
            self.image_widgets.remove(widget)
            #print(f"✅ Removed image widget (remaining: {len(self.image_widgets)})")
    

    def open_explorer(self):
        """Open file explorer in the folder of the current .tex file (foreground)."""
        try:
            # 1. Get the current file path using EditorManager's reliable method
            editor_manager = self.main_window.editor_manager
            current_file = editor_manager.get_current_file_path() if editor_manager else None

            # 2. Determine target folder
            if current_file and os.path.exists(current_file):
                target_folder = os.path.dirname(current_file)
                # For Windows "select" mode, we need the full file path
                target_file = current_file
            else:
                # Fallback: use the directory of the last opened file (if any)
                fallback_folder = None
                if editor_manager and hasattr(editor_manager, 'last_opened_directory'):
                    fallback_folder = editor_manager.last_opened_directory
                if not fallback_folder or not os.path.exists(fallback_folder):
                    fallback_folder = os.path.expanduser("~")
                target_folder = fallback_folder
                target_file = None
                #print("No current file – opening fallback folder:", target_folder)

            # 3. Open explorer (foreground)
            if sys.platform == 'win32':
                if target_file and os.path.isfile(target_file):
                    # Opens the folder with the file selected – usually brings window to front
                    subprocess.Popen(['explorer', '/select,', target_file])
                else:
                    subprocess.Popen(['explorer', target_folder])
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', target_folder])
            else:  # Linux / other Unix
                subprocess.Popen(['xdg-open', target_folder])

            #print(f"✅ Opened file explorer at: {target_folder}")

        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Failed to open explorer:\n{str(e)}"
            )
    
    def open_browser(self):
        """Open web browser"""
        try:
            import webbrowser
            webbrowser.open('https://www.google.com')
            #print("✅ Opened web browser")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open browser:\n{str(e)}")
    
    def open_paint(self):
        """Open paint application"""
        try:
            if sys.platform == 'win32':
                subprocess.Popen('mspaint')
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-a', 'Preview'])
            else:
                for app in ['kolourpaint', 'pinta', 'gimp']:
                    try:
                        subprocess.Popen([app])
                        #print(f"✅ Opened {app}")
                        return
                    except FileNotFoundError:
                        continue
                QMessageBox.information(self, "Info", 
                    "No paint application found. Install kolourpaint, pinta, or gimp.")
                return
            #print("✅ Opened paint application")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open paint:\n{str(e)}")

# Integration function to add to your PDF manager or main window
def add_tools_tab_to_pdf_viewer(main_window):
    """Add the tools tab to the PDF viewer - FIXED to prevent empty tabs"""
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
        
        # Ensure PDF container exists
        if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
            layout_manager._recreate_pdf_container()
        
        # For tabbed mode only
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info", 
                "Tools tab is only available in tabbed mode. Switch to tabbed mode first.")
            return
        
        # ✅ Initialize pdf_tabs if needed WITHOUT recreating container
        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
            #print("DEBUG: Creating pdf_tabs QTabWidget...")
            from PyQt5.QtWidgets import QTabWidget
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)            
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(pdf_manager.close_pdf_tab)
            
            # Add to PDF container layout
            pdf_layout = layout_manager.pdf_container.layout()
            if pdf_layout:
                # Clear existing widgets (welcome tab)
                while pdf_layout.count():
                    item = pdf_layout.takeAt(0)
                    if item.widget():
                        widget = item.widget()
                        widget.setParent(None)
                        widget.deleteLater()
                # Add the new tab widget
                pdf_layout.addWidget(pdf_manager.pdf_tabs)
                #print("DEBUG: Added pdf_tabs to layout")
        
        tab_widget = pdf_manager.pdf_tabs
        
        if tab_widget is None:
            QMessageBox.critical(main_window, "Error", "Could not initialize PDF tabs")
            return
        
        # ✅ Remove unwanted tabs (Welcome, No Pdfs, etc.)
        tabs_to_remove = ["Welcome", "No Pdfs", "No PDFs"]
        for i in reversed(range(tab_widget.count())):
            tab_text = tab_widget.tabText(i)
            if tab_text in tabs_to_remove:
                tab_widget.removeTab(i)
                #print(f"DEBUG: Removed '{tab_text}' tab")
        
        # ✅ Check if Tools tab already exists and is valid
        possible_labels = {
            tr["tools_tab"] for tr in translations.values()
        }        
        existing_tools_index = -1
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                existing_tools_index = i
                break

        
        if existing_tools_index >= 0:
            # Tools tab exists, just switch to it
            new_name = tr.get("tools_tab", "Accessories")
            tab_widget.setTabText(existing_tools_index, new_name)            
            tab_widget.setCurrentIndex(existing_tools_index)
            main_window._pdf_tools_tab_index = existing_tools_index
            #print(f"✅ Switched to existing Tools tab at index {existing_tools_index}")
            return
        
        # Create new tools tab
        from tools_tab import ToolsTab
        tools_tab = ToolsTab(main_window)
        
        # Store reference to prevent garbage collection
        if not hasattr(main_window, '_tools_tabs'):
            main_window._tools_tabs = []
        main_window._tools_tabs.append(tools_tab)
        
        # Add to tab widget
        tab_name = tr.get("tools_tab", "Accessories")
        tab_index = tab_widget.addTab(tools_tab, tab_name)
        tab_widget.tabBar().setTabData(tab_index, "tools_tab") 
        
        main_window._pdf_tools_tab_index = tab_index
        
        tab_widget.tabBar().setTabData(tab_index, "tools_tab")
        
        # ✅ Set SVG icon properly
        icon = QIcon("icons/accessories.svg")
        tab_widget.setTabIcon(tab_index, icon)        
        
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)
        
        # Ensure it's in the layout
        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:            
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)
        
        # Force visibility
        tab_widget.show()
        tab_widget.setVisible(True)
        tools_tab.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()
        
    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add tools tab:\n{str(e)}")
        import traceback
        traceback.print_exc()