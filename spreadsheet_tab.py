# spreadsheet.py
import sys
import re
import math
import statistics
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QToolBar,
    QPushButton, QComboBox, QStyledItemDelegate,
    QDialog, QListWidget, QDialogButtonBox, QSizePolicy,
    QMessageBox, QAction, QLabel, QTextEdit, QScrollArea, QSpinBox,
    QColorDialog, QFileDialog, QGridLayout, QCheckBox, QUndoStack, QUndoCommand
)
from PyQt5.QtGui import QFont, QPen, QPainter, QKeySequence, QColor, QIcon
from PyQt5.QtCore import Qt, QRect, QEvent, QTimer

import sys
import re
import math
import statistics
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QToolBar,
    QPushButton, QComboBox, QStyledItemDelegate,
    QDialog, QListWidget, QDialogButtonBox, QSizePolicy,
    QMessageBox, QAction, QLabel, QTextEdit, QScrollArea, QSpinBox,
    QColorDialog, QFileDialog, QGridLayout, QCheckBox, QUndoStack, QUndoCommand,
    QFrame
)
from PyQt5.QtGui import QFont, QPen, QPainter, QKeySequence, QColor
from PyQt5.QtCore import Qt, QRect, QEvent, QTimer

# -----------------------------
# Undo Commands
# -----------------------------
class CellEditCommand(QUndoCommand):
    def __init__(self, table, row, col, old_text, new_text, old_formula, new_formula, formulas_dict, description="Edit Cell"):
        super().__init__(description)
        self.table = table
        self.row = row
        self.col = col
        self.old_text = old_text
        self.new_text = new_text
        self.old_formula = old_formula
        self.new_formula = new_formula
        self.formulas_dict = formulas_dict

    def redo(self):
        item = self.table.item(self.row, self.col)
        if item:
            item.setText(self.new_text)
        if self.new_formula:
            self.formulas_dict[(self.row, self.col)] = self.new_formula
        elif (self.row, self.col) in self.formulas_dict:
            del self.formulas_dict[(self.row, self.col)]

    def undo(self):
        item = self.table.item(self.row, self.col)
        if item:
            item.setText(self.old_text)
        if self.old_formula:
            self.formulas_dict[(self.row, self.col)] = self.old_formula
        elif (self.row, self.col) in self.formulas_dict:
            del self.formulas_dict[(self.row, self.col)]


# class MultiCellEditCommand(QUndoCommand):
    # def __init__(self, table, changes, formulas_dict, description="Edit Multiple Cells"):
        # super().__init__(description)
        # self.table = table
        # self.changes = changes  # List of (row, col, old_text, new_text, old_formula, new_formula)
        # self.formulas_dict = formulas_dict

    # def redo(self):
        # for row, col, old_text, new_text, old_formula, new_formula in self.changes:
            # item = self.table.item(row, col)
            # if item:
                # item.setText(new_text)
            # if new_formula:
                # self.formulas_dict[(row, col)] = new_formula
            # elif (row, col) in self.formulas_dict:
                # del self.formulas_dict[(row, col)]

    # def undo(self):
        # for row, col, old_text, new_text, old_formula, new_formula in self.changes:
            # item = self.table.item(row, col)
            # if item:
                # item.setText(old_text)
            # if old_formula:
                # self.formulas_dict[(row, col)] = old_formula
            # elif (row, col) in self.formulas_dict:
                # del self.formulas_dict[(row, col)]


class MergeCellsCommand(QUndoCommand):
    def __init__(self, table, top_row, left_col, bottom_row, right_col, merged_cells_dict, 
                 old_texts, merged_text, description="Merge Cells"):
        super().__init__(description)
        self.table = table
        self.top_row = top_row
        self.left_col = left_col
        self.bottom_row = bottom_row
        self.right_col = right_col
        self.merged_cells_dict = merged_cells_dict
        self.old_texts = old_texts  # Dict of (row, col): text
        self.merged_text = merged_text
        self.row_span = bottom_row - top_row + 1
        self.col_span = right_col - left_col + 1

    def redo(self):
        # Store merge info
        self.merged_cells_dict[(self.top_row, self.left_col)] = (self.row_span, self.col_span)
        # Set span
        self.table.setSpan(self.top_row, self.left_col, self.row_span, self.col_span)
        # Set merged text in top-left cell
        item = self.table.item(self.top_row, self.left_col)
        if item:
            item.setText(self.merged_text)

    def undo(self):
        # Remove merge info
        if (self.top_row, self.left_col) in self.merged_cells_dict:
            del self.merged_cells_dict[(self.top_row, self.left_col)]
        # Remove span
        self.table.setSpan(self.top_row, self.left_col, 1, 1)
        # Restore old texts
        for (row, col), text in self.old_texts.items():
            item = self.table.item(row, col)
            if item:
                item.setText(text)


class UnmergeCellsCommand(QUndoCommand):
    def __init__(self, table, top_row, left_col, row_span, col_span, merged_cells_dict,
                 merged_text, description="Unmerge Cells"):
        super().__init__(description)
        self.table = table
        self.top_row = top_row
        self.left_col = left_col
        self.row_span = row_span
        self.col_span = col_span
        self.merged_cells_dict = merged_cells_dict
        self.merged_text = merged_text

    def redo(self):
        # Remove merge info
        if (self.top_row, self.left_col) in self.merged_cells_dict:
            del self.merged_cells_dict[(self.top_row, self.left_col)]
        # Remove span
        self.table.setSpan(self.top_row, self.left_col, 1, 1)

    def undo(self):
        # Restore merge info
        self.merged_cells_dict[(self.top_row, self.left_col)] = (self.row_span, self.col_span)
        # Restore span
        self.table.setSpan(self.top_row, self.left_col, self.row_span, self.col_span)
        # Restore merged text
        item = self.table.item(self.top_row, self.left_col)
        if item:
            item.setText(self.merged_text)


# -----------------------------
# Custom QLineEdit with always-visible cursor
# -----------------------------
class FormulaBarLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent

    def focusInEvent(self, event):
        """When formula bar gains focus, enable formula mode in table"""
        super().focusInEvent(event)
        if self.parent_widget and hasattr(self.parent_widget, 'table'):
            if self.text().startswith("="):
                self.parent_widget.table.formula_mode = True

    def focusOutEvent(self, event):
        """When formula bar loses focus, DON'T disable formula mode - let mouse events handle it"""
        super().focusOutEvent(event)
        # Don't disable formula_mode here - it's handled by mouse events and formula entry

    def keyPressEvent(self, event):
        """Handle key press events"""
        super().keyPressEvent(event)
        if self.parent_widget and hasattr(self.parent_widget, 'table'):
            if self.text().startswith("="):
                self.parent_widget.table.formula_mode = True
            else:
                self.parent_widget.table.formula_mode = False


# -----------------------------
# Custom QTableWidget
# -----------------------------
class SpreadsheetTable(QTableWidget):
    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self.dragging = False
        self.drag_start = None
        self.drag_end = None
        self.drag_cell = None
        self.viewport().installEventFilter(self)
        self.parent_widget = parent
        self.setMouseTracking(True)
        self.formula_mode = False
        # Track range selection for formula insertion
        self.range_selection_start = None
        self.range_selection_end = None
        self.is_selecting_range = False

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            r = self.currentRow()
            c = self.currentColumn()
            if r + 1 < self.rowCount():
                self.setCurrentCell(r + 1, c)
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Check if we're in formula mode using the flag (not focus)
        # This allows clicking cells to insert references even after focus moves
        if self.formula_mode and self.parent_widget:
            formula_text = self.parent_widget.formula_bar.text()
            if formula_text.startswith("="):
                # Get the cell that was clicked
                r = self.rowAt(event.y())
                c = self.columnAt(event.x())
                if r >= 0 and c >= 0:
                    # Start range selection
                    self.is_selecting_range = True
                    self.range_selection_start = (r, c)
                    self.range_selection_end = (r, c)
                    # Don't call super() to prevent cell selection change
                    event.accept()
                    return

        # Normal cell selection behavior (only when NOT in formula mode)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # If selecting range for formula
        if self.is_selecting_range:
            r = self.rowAt(event.y())
            c = self.columnAt(event.x())
            if r >= 0 and c >= 0:
                self.range_selection_end = (r, c)
                self.viewport().update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Complete range selection for formula
        if self.is_selecting_range and self.parent_widget:
            if self.range_selection_start and self.range_selection_end:
                r1, c1 = self.range_selection_start
                r2, c2 = self.range_selection_end

                # Normalize the range (ensure start <= end)
                min_r, max_r = min(r1, r2), max(r1, r2)
                min_c, max_c = min(c1, c2), max(c1, c2)

                # Generate cell or range reference
                if (min_r, min_c) == (max_r, max_c):
                    # Single cell
                    cell_ref = f"{self._col_to_letter(min_c)}{min_r + 1}"
                else:
                    # Range
                    start_ref = f"{self._col_to_letter(min_c)}{min_r + 1}"
                    end_ref = f"{self._col_to_letter(max_c)}{max_r + 1}"
                    cell_ref = f"{start_ref}:{end_ref}"

                # Insert into formula bar at cursor position
                formula_bar = self.parent_widget.formula_bar
                current_text = formula_bar.text()
                cursor_pos = formula_bar.cursorPosition()
                new_text = current_text[:cursor_pos] + cell_ref + current_text[cursor_pos:]
                formula_bar.setText(new_text)
                formula_bar.setCursorPosition(cursor_pos + len(cell_ref))
                formula_bar.setFocus()

            # Reset range selection
            self.is_selecting_range = False
            self.range_selection_start = None
            self.range_selection_end = None
            self.viewport().update()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _col_to_letter(self, col):
        """Convert column index to letter(s)"""
        result = ""
        while col >= 0:
            result = chr(ord('A') + col % 26) + result
            col = col // 26 - 1
        return result

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            r = self.rowAt(event.y())
            c = self.columnAt(event.x())
            item = self.item(r, c)
            if item:
                rect = self.visualItemRect(item)
                handle_size = 8
                handle_rect = QRect(
                    rect.right() - handle_size,
                    rect.bottom() - handle_size,
                    handle_size,
                    handle_size
                )
                if handle_rect.contains(event.pos()):
                    self.drag_start = (r, c)
                    self.drag_cell = (r, c)
                    self.dragging = True
                    self.drag_end = (r, c)
                    return True

        elif event.type() == QEvent.MouseMove:
            if self.dragging:
                r = self.rowAt(event.y())
                c = self.columnAt(event.x())
                if r is not None and c is not None:
                    self.drag_end = (r, c)
                    self.viewport().update()
                return True
            else:
                r = self.rowAt(event.y())
                c = self.columnAt(event.x())
                item = self.item(r, c)
                if item:
                    rect = self.visualItemRect(item)
                    handle_size = 8
                    handle_rect = QRect(
                        rect.right() - handle_size,
                        rect.bottom() - handle_size,
                        handle_size,
                        handle_size
                    )
                    if handle_rect.contains(event.pos()):
                        self.viewport().setCursor(Qt.CrossCursor)
                    else:
                        self.viewport().setCursor(Qt.ArrowCursor)

        elif event.type() == QEvent.MouseButtonRelease and self.dragging:
            self.dragging = False
            self.viewport().setCursor(Qt.ArrowCursor)
            if self.parent_widget and self.drag_cell and self.drag_end:
                if self.drag_cell != self.drag_end:
                    self.parent_widget.fill_formula_drag(self.drag_cell, self.drag_end)
            self.drag_start = None
            self.drag_end = None
            self.drag_cell = None
            self.viewport().update()
            return True

        return super().eventFilter(source, event)

    # def paintEvent(self, event):
        # super().paintEvent(event)
        # painter = QPainter(self.viewport())

        # r = self.currentRow()
        # c = self.currentColumn()
        # if r >= 0 and c >= 0:
            # item = self.item(r, c)
            # if item:
                # rect = self.visualItemRect(item)
                # pen = QPen(QColor(66, 133, 244), 2)
                # painter.setPen(pen)
                # painter.drawRect(rect)
                # handle_size = 6
                # handle_color = QColor(66, 133, 244)
                # painter.setBrush(handle_color)
                # painter.setPen(Qt.NoPen)
                # painter.drawRect(
                    # rect.right() - handle_size,
                    # rect.bottom() - handle_size,
                    # handle_size,
                    # handle_size
                # )

        # # Draw range selection highlight for formula mode
        # if self.is_selecting_range and self.range_selection_start and self.range_selection_end:
            # r1, c1 = self.range_selection_start
            # r2, c2 = self.range_selection_end
            # top_r, bottom_r = min(r1, r2), max(r1, r2)
            # left_c, right_c = min(c1, c2), max(c1, c2)

            # top_left_item = self.item(top_r, left_c)
            # bottom_right_item = self.item(bottom_r, right_c)
            # if top_left_item and bottom_right_item:
                # rect_top = self.visualItemRect(top_left_item).topLeft()
                # rect_bottom = self.visualItemRect(bottom_right_item).bottomRight()
                # painter.setBrush(QColor(100, 200, 100, 80))
                # painter.setPen(QPen(QColor(0, 150, 0), 2))
                # painter.drawRect(QRect(rect_top, rect_bottom))

        # if self.drag_start and self.drag_end:
            # if self.drag_cell:
                # r0, c0 = self.drag_cell
            # else:
                # r0, c0 = self.drag_start
            # r1, c1 = self.drag_end
            # top, left = min(r0, r1), min(c0, c1)
            # bottom, right = max(r0, r1), max(c0, c1)
            # top_left_item = self.item(top, left)
            # bottom_right_item = self.item(bottom, right)
            # if top_left_item and bottom_right_item:
                # rect_top = self.visualItemRect(top_left_item).topLeft()
                # rect_bottom = self.visualItemRect(bottom_right_item).bottomRight()
                # painter.setBrush(QColor(66, 133, 244, 50))
                # painter.setPen(QPen(QColor(66, 133, 244), 2, Qt.DashLine))
                # painter.drawRect(QRect(rect_top, rect_bottom))

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self.viewport())
        try:
            r = self.currentRow()
            c = self.currentColumn()

            if r >= 0 and c >= 0:
                item = self.item(r, c)
                if item:
                    rect = self.visualItemRect(item)
                    painter.setPen(QPen(QColor(66, 133, 244), 2))
                    painter.drawRect(rect)

                    handle_size = 6
                    painter.setBrush(QColor(66, 133, 244))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(
                        rect.right() - handle_size,
                        rect.bottom() - handle_size,
                        handle_size,
                        handle_size
                    )

            # Range selection
            if self.is_selecting_range and self.range_selection_start and self.range_selection_end:
                r1, c1 = self.range_selection_start
                r2, c2 = self.range_selection_end

                top_r, bottom_r = min(r1, r2), max(r1, r2)
                left_c, right_c = min(c1, c2), max(c1, c2)

                top_left_item = self.item(top_r, left_c)
                bottom_right_item = self.item(bottom_r, right_c)

                if top_left_item and bottom_right_item:
                    rect = QRect(
                        self.visualItemRect(top_left_item).topLeft(),
                        self.visualItemRect(bottom_right_item).bottomRight()
                    )
                    painter.setBrush(QColor(100, 200, 100, 80))
                    painter.setPen(QPen(QColor(0, 150, 0), 2))
                    painter.drawRect(rect)

            # Drag selection
            if self.drag_start and self.drag_end:
                r0, c0 = self.drag_cell if self.drag_cell else self.drag_start
                r1, c1 = self.drag_end

                top, left = min(r0, r1), min(c0, c1)
                bottom, right = max(r0, r1), max(c0, c1)

                top_left_item = self.item(top, left)
                bottom_right_item = self.item(bottom, right)

                if top_left_item and bottom_right_item:
                    rect = QRect(
                        self.visualItemRect(top_left_item).topLeft(),
                        self.visualItemRect(bottom_right_item).bottomRight()
                    )
                    painter.setBrush(QColor(66, 133, 244, 50))
                    painter.setPen(QPen(QColor(66, 133, 244), 2, Qt.DashLine))
                    painter.drawRect(rect)

        except Exception as e:
            print("paintEvent crash:", e)
            import traceback
            traceback.print_exc()

        finally:
            painter.end()   # 🔥 makes it crash-proof


# -----------------------------
# Border delegate
# -----------------------------
class BorderDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        borders = index.data(Qt.UserRole)
        if not borders:
            return
        painter.setPen(QPen(Qt.black, 1))
        r = option.rect
        if "top" in borders: painter.drawLine(r.topLeft(), r.topRight())
        if "bottom" in borders: painter.drawLine(r.bottomLeft(), r.bottomRight())
        if "left" in borders: painter.drawLine(r.topLeft(), r.bottomLeft())
        if "right" in borders: painter.drawLine(r.topRight(), r.bottomRight())


# -----------------------------
# Function Dialog with Categories
# -----------------------------
class FunctionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Insert Function")
        self.resize(500, 400)
        layout = QVBoxLayout()

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter functions...")
        self.search_box.textChanged.connect(self.filter_functions)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        # Category selection
        cat_layout = QHBoxLayout()
        cat_label = QLabel("Category:")
        cat_layout.addWidget(cat_label)
        self.category_combo = QComboBox()

        # Define categories with functions
        self.categories = {
            "Math & Trig": [
                "SUM", "SUMIF", "SUMIFS", "SUMPRODUCT", "AVERAGE", "COUNT", "MAX", "MIN",
                "ROUND", "ROUNDUP", "ROUNDDOWN", "SQRT", "ABS", "POW", "POWER",
                "SIN", "COS", "TAN", "ASIN", "ACOS", "ATAN", "ATAN2",
                "CEILING", "FLOOR", "MOD", "PRODUCT", "QUOTIENT", "RAND", "RANDBETWEEN",
                "PI", "EXP", "LN", "LOG", "LOG10", "SIGN", "TRUNC", "INT",
                "DEGREES", "RADIANS", "FACT", "GCD", "LCM", "COMBIN", "PERMUT"
            ],
            "Statistical": [
                "AVERAGE", "AVERAGEA", "AVERAGEIF", "AVERAGEIFS", "MEDIAN", "MODE", "MODE.SNGL", "MODE.MULT",
                "STDEV", "STDEV.S", "STDEV.P", "STDEVP", "VAR", "VAR.S", "VAR.P", "VARP",
                "COUNT", "COUNTA", "COUNTBLANK", "COUNTIF", "COUNTIFS",
                "MAX", "MAXA", "MIN", "MINA", "LARGE", "SMALL",
                "PERCENTILE", "PERCENTILE.INC", "PERCENTILE.EXC",
                "QUARTILE", "QUARTILE.INC", "QUARTILE.EXC",
                "RANK", "RANK.AVG", "RANK.EQ", "PERCENTRANK", "PERCENTRANK.INC",
                "CORREL", "COVARIANCE.P", "COVARIANCE.S", "SLOPE", "INTERCEPT",
                "FORECAST", "TREND", "GROWTH", "LINEST", "LOGEST",
                "NORM.DIST", "NORM.INV", "NORM.S.DIST", "NORM.S.INV",
                "T.DIST", "T.INV", "CHISQ.DIST", "CHISQ.INV", "F.DIST", "F.INV",
                "CONFIDENCE", "CONFIDENCE.NORM", "CONFIDENCE.T"
            ],
            "Logical": [
                "IF", "IFS", "IFERROR", "IFNA", "AND", "OR", "NOT", "XOR",
                "TRUE", "FALSE", "SWITCH", "CHOOSE"
            ],
            "Text": [
                "CONCATENATE", "CONCAT", "TEXTJOIN", "LEFT", "RIGHT", "MID",
                "LEN", "LENB", "UPPER", "LOWER", "PROPER", "TRIM", "CLEAN",
                "SUBSTITUTE", "REPLACE", "REPLACEB", "FIND", "FINDB", "SEARCH", "SEARCHB",
                "TEXT", "VALUE", "FIXED", "DOLLAR", "CHAR", "CODE", "UNICODE", "UNICHAR",
                "REPT", "EXACT", "T", "N"
            ],
            "Date & Time": [
                "NOW", "TODAY", "DATE", "DATEVALUE", "TIME", "TIMEVALUE",
                "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
                "WEEKDAY", "WEEKNUM", "ISOWEEKNUM", "WORKDAY", "WORKDAY.INTL",
                "NETWORKDAYS", "NETWORKDAYS.INTL", "DATEDIF", "DAYS", "DAYS360",
                "EDATE", "EOMONTH", "YEARFRAC"
            ],
            "Lookup & Reference": [
                "VLOOKUP", "HLOOKUP", "XLOOKUP", "LOOKUP", "INDEX", "MATCH",
                "OFFSET", "INDIRECT", "CHOOSE", "ROW", "ROWS", "COLUMN", "COLUMNS",
                "ADDRESS", "AREAS", "HYPERLINK", "TRANSPOSE", "FORMULATEXT"
            ],
            "Financial": [
                "PMT", "PPMT", "IPMT", "FV", "PV", "NPV", "XNPV",
                "RATE", "NPER", "IRR", "XIRR", "MIRR",
                "DB", "DDB", "SLN", "SYD", "VDB",
                "EFFECT", "NOMINAL", "CUMIPMT", "CUMPRINC",
                "PRICE", "YIELD", "DISC", "INTRATE", "RECEIVED"
            ],
            "Information": [
                "ISBLANK", "ISERROR", "ISERR", "ISNA", "ISTEXT", "ISNUMBER",
                "ISLOGICAL", "ISREF", "ISFORMULA", "ISEVEN", "ISODD",
                "TYPE", "ERROR.TYPE", "NA", "INFO", "CELL", "SHEET", "SHEETS"
            ],
            "Database": [
                "DSUM", "DAVERAGE", "DCOUNT", "DCOUNTA", "DMAX", "DMIN",
                "DGET", "DPRODUCT", "DSTDEV", "DSTDEVP", "DVAR", "DVARP"
            ],
            "Engineering": [
                "BIN2DEC", "BIN2HEX", "BIN2OCT", "DEC2BIN", "DEC2HEX", "DEC2OCT",
                "HEX2BIN", "HEX2DEC", "HEX2OCT", "OCT2BIN", "OCT2DEC", "OCT2HEX",
                "CONVERT", "DELTA", "GESTEP", "COMPLEX", "IMREAL", "IMAGINARY",
                "IMSUM", "IMSUB", "IMPRODUCT", "IMDIV", "IMABS", "IMARGUMENT"
            ],
        }

        # Comprehensive function descriptions from Microsoft Excel documentation
        self.descriptions = {
            # Math & Trig Functions
            "SUM": "Adds all the numbers in a range of cells.\nSyntax: SUM(number1, [number2], ...)",
            "SUMIF": "Adds the cells specified by a given condition or criteria.\nSyntax: SUMIF(range, criteria, [sum_range])",
            "SUMIFS": "Adds the cells in a range that meet multiple criteria.\nSyntax: SUMIFS(sum_range, criteria_range1, criteria1, ...)",
            "SUMPRODUCT": "Returns the sum of the products of corresponding ranges or arrays.\nSyntax: SUMPRODUCT(array1, [array2], ...)",
            "AVERAGE": "Returns the average (arithmetic mean) of its arguments.\nSyntax: AVERAGE(number1, [number2], ...)",
            "AVERAGEA": "Returns the average of its arguments, including numbers, text, and logical values.\nSyntax: AVERAGEA(value1, [value2], ...)",
            "AVERAGEIF": "Returns the average of all cells in a range that meet a given criteria.\nSyntax: AVERAGEIF(range, criteria, [average_range])",
            "AVERAGEIFS": "Returns the average of all cells that meet multiple criteria.\nSyntax: AVERAGEIFS(average_range, criteria_range1, criteria1, ...)",
            "COUNT": "Counts the number of cells that contain numbers.\nSyntax: COUNT(value1, [value2], ...)",
            "COUNTA": "Counts the number of cells that are not empty.\nSyntax: COUNTA(value1, [value2], ...)",
            "COUNTBLANK": "Counts empty cells in a specified range of cells.\nSyntax: COUNTBLANK(range)",
            "COUNTIF": "Counts the number of cells within a range that meet the given condition.\nSyntax: COUNTIF(range, criteria)",
            "COUNTIFS": "Counts the number of cells within a range that meet multiple conditions.\nSyntax: COUNTIFS(criteria_range1, criteria1, ...)",
            "MAX": "Returns the maximum value in a list of arguments.\nSyntax: MAX(number1, [number2], ...)",
            "MAXA": "Returns the maximum value in a list of arguments, including numbers, text, and logical values.\nSyntax: MAXA(value1, [value2], ...)",
            "MIN": "Returns the minimum value in a list of arguments.\nSyntax: MIN(number1, [number2], ...)",
            "MINA": "Returns the smallest value in a list of arguments, including numbers, text, and logical values.\nSyntax: MINA(value1, [value2], ...)",
            "LARGE": "Returns the k-th largest value in a data set.\nSyntax: LARGE(array, k)",
            "SMALL": "Returns the k-th smallest value in a data set.\nSyntax: SMALL(array, k)",
            "ROUND": "Rounds a number to a specified number of digits.\nSyntax: ROUND(number, num_digits)",
            "ROUNDUP": "Rounds a number up, away from zero.\nSyntax: ROUNDUP(number, num_digits)",
            "ROUNDDOWN": "Rounds a number down, toward zero.\nSyntax: ROUNDDOWN(number, num_digits)",
            "SQRT": "Returns a positive square root.\nSyntax: SQRT(number)",
            "ABS": "Returns the absolute value of a number.\nSyntax: ABS(number)",
            "POW": "Returns the result of a number raised to a power.\nSyntax: POW(number, power)",
            "POWER": "Returns the result of a number raised to a power.\nSyntax: POWER(number, power)",
            "SIN": "Returns the sine of the given angle (in radians).\nSyntax: SIN(number)",
            "COS": "Returns the cosine of the given angle (in radians).\nSyntax: COS(number)",
            "TAN": "Returns the tangent of the given angle (in radians).\nSyntax: TAN(number)",
            "ASIN": "Returns the arcsine, or inverse sine, of a number. The arcsine is the angle whose sine is number.\nSyntax: ASIN(number)",
            "ACOS": "Returns the arccosine, or inverse cosine, of a number.\nSyntax: ACOS(number)",
            "ATAN": "Returns the arctangent, or inverse tangent, of a number.\nSyntax: ATAN(number)",
            "ATAN2": "Returns the arctangent from x- and y-coordinates.\nSyntax: ATAN2(x_num, y_num)",
            "CEILING": "Rounds a number to the nearest integer or to the nearest multiple of significance.\nSyntax: CEILING(number, significance)",
            "FLOOR": "Rounds a number down, toward zero, to the nearest multiple of significance.\nSyntax: FLOOR(number, significance)",
            "MOD": "Returns the remainder after number is divided by divisor.\nSyntax: MOD(number, divisor)",
            "PRODUCT": "Multiplies all the numbers given as arguments and returns the product.\nSyntax: PRODUCT(number1, [number2], ...)",
            "QUOTIENT": "Returns the integer portion of a division.\nSyntax: QUOTIENT(numerator, denominator)",
            "RAND": "Returns an evenly distributed random real number greater than or equal to 0 and less than 1.\nSyntax: RAND()",
            "RANDBETWEEN": "Returns a random integer number between the numbers you specify.\nSyntax: RANDBETWEEN(bottom, top)",
            "PI": "Returns the value of pi (3.14159265358979) accurate to 15 digits.\nSyntax: PI()",
            "EXP": "Returns e raised to the power of number. The constant e equals 2.71828182845904.\nSyntax: EXP(number)",
            "LN": "Returns the natural logarithm of a number. Natural logarithms are based on the constant e.\nSyntax: LN(number)",
            "LOG": "Returns the logarithm of a number to a specified base.\nSyntax: LOG(number, [base])",
            "LOG10": "Returns the base-10 logarithm of a number.\nSyntax: LOG10(number)",
            "SIGN": "Returns the sign of a number. Returns 1 if the number is positive, zero if the number is 0, and -1 if the number is negative.\nSyntax: SIGN(number)",
            "TRUNC": "Truncates a number to an integer by removing the fractional part of the number.\nSyntax: TRUNC(number, [num_digits])",
            "INT": "Rounds a number down to the nearest integer.\nSyntax: INT(number)",
            "DEGREES": "Converts radians into degrees.\nSyntax: DEGREES(angle)",
            "RADIANS": "Converts degrees into radians.\nSyntax: RADIANS(angle)",
            "FACT": "Returns the factorial of a number.\nSyntax: FACT(number)",
            "GCD": "Returns the greatest common divisor of two or more integers.\nSyntax: GCD(number1, [number2], ...)",
            "LCM": "Returns the least common multiple of integers.\nSyntax: LCM(number1, [number2], ...)",
            "COMBIN": "Returns the number of combinations for a given number of objects.\nSyntax: COMBIN(number, number_chosen)",
            "PERMUT": "Returns the number of permutations for a given number of objects.\nSyntax: PERMUT(number, number_chosen)",

            # Statistical Functions
            "MEDIAN": "Returns the median of the given numbers. The median is the number in the middle of a set of numbers.\nSyntax: MEDIAN(number1, [number2], ...)",
            "MODE": "Returns the most frequently occurring value in a range of data.\nSyntax: MODE(number1, [number2], ...)",
            "MODE.SNGL": "Returns the most frequently occurring value in a range of data.\nSyntax: MODE.SNGL(number1, [number2], ...)",
            "MODE.MULT": "Returns a vertical array of the most frequently occurring values in a range of data.\nSyntax: MODE.MULT(number1, [number2], ...)",
            "STDEV": "Estimates standard deviation based on a sample.\nSyntax: STDEV(number1, [number2], ...)",
            "STDEV.S": "Estimates standard deviation based on a sample.\nSyntax: STDEV.S(number1, [number2], ...)",
            "STDEV.P": "Calculates standard deviation based on the entire population.\nSyntax: STDEV.P(number1, [number2], ...)",
            "STDEVP": "Calculates standard deviation based on the entire population.\nSyntax: STDEVP(number1, [number2], ...)",
            "VAR": "Estimates variance based on a sample.\nSyntax: VAR(number1, [number2], ...)",
            "VAR.S": "Estimates variance based on a sample.\nSyntax: VAR.S(number1, [number2], ...)",
            "VAR.P": "Calculates variance based on the entire population.\nSyntax: VAR.P(number1, [number2], ...)",
            "VARP": "Calculates variance based on the entire population.\nSyntax: VARP(number1, [number2], ...)",
            "PERCENTILE": "Returns the k-th percentile of values in a range.\nSyntax: PERCENTILE(array, k)",
            "PERCENTILE.INC": "Returns the k-th percentile of values in a range, where k is in the range 0..1, inclusive.\nSyntax: PERCENTILE.INC(array, k)",
            "PERCENTILE.EXC": "Returns the k-th percentile of values in a range, where k is in the range 0..1, exclusive.\nSyntax: PERCENTILE.EXC(array, k)",
            "QUARTILE": "Returns the quartile of a data set.\nSyntax: QUARTILE(array, quart)",
            "QUARTILE.INC": "Returns the quartile of a data set, based on percentile values from 0..1, inclusive.\nSyntax: QUARTILE.INC(array, quart)",
            "QUARTILE.EXC": "Returns the quartile of the data set, based on percentile values from 0..1, exclusive.\nSyntax: QUARTILE.EXC(array, quart)",
            "RANK": "Returns the rank of a number in a list of numbers.\nSyntax: RANK(number, ref, [order])",
            "RANK.AVG": "Returns the rank of a number in a list of numbers. If more than one value has the same rank, the average rank is returned.\nSyntax: RANK.AVG(number, ref, [order])",
            "RANK.EQ": "Returns the rank of a number in a list of numbers.\nSyntax: RANK.EQ(number, ref, [order])",
            "PERCENTRANK": "Returns the rank of a value in a data set as a percentage of the data set.\nSyntax: PERCENTRANK(array, x, [significance])",
            "PERCENTRANK.INC": "Returns the rank of a value in a data set as a percentage (0..1, inclusive) of the data set.\nSyntax: PERCENTRANK.INC(array, x, [significance])",
            "CORREL": "Returns the correlation coefficient between two data sets.\nSyntax: CORREL(array1, array2)",
            "COVARIANCE.P": "Returns population covariance, the average of the products of deviations for each data point pair.\nSyntax: COVARIANCE.P(array1, array2)",
            "COVARIANCE.S": "Returns the sample covariance, the average of the products of deviations for each data point pair in two data sets.\nSyntax: COVARIANCE.S(array1, array2)",
            "SLOPE": "Returns the slope of the linear regression line through data points.\nSyntax: SLOPE(known_y's, known_x's)",
            "INTERCEPT": "Returns the intercept of the linear regression line through data points.\nSyntax: INTERCEPT(known_y's, known_x's)",
            "FORECAST": "Calculates or predicts a future value by using existing values.\nSyntax: FORECAST(x, known_y's, known_x's)",
            "TREND": "Returns values along a linear trend.\nSyntax: TREND(known_y's, [known_x's], [new_x's], [const])",
            "GROWTH": "Calculates predicted exponential growth by using existing data.\nSyntax: GROWTH(known_y's, [known_x's], [new_x's], [const])",
            "LINEST": "Returns the parameters of a linear trend.\nSyntax: LINEST(known_y's, [known_x's], [const], [stats])",
            "LOGEST": "Returns the parameters of an exponential trend.\nSyntax: LOGEST(known_y's, [known_x's], [const], [stats])",
            "NORM.DIST": "Returns the normal cumulative distribution for the specified mean and standard deviation.\nSyntax: NORM.DIST(x, mean, standard_dev, cumulative)",
            "NORM.INV": "Returns the inverse of the normal cumulative distribution.\nSyntax: NORM.INV(probability, mean, standard_dev)",
            "NORM.S.DIST": "Returns the standard normal cumulative distribution.\nSyntax: NORM.S.DIST(z, cumulative)",
            "NORM.S.INV": "Returns the inverse of the standard normal cumulative distribution.\nSyntax: NORM.S.INV(probability)",
            "T.DIST": "Returns the Student's t-distribution.\nSyntax: T.DIST(x, deg_freedom, cumulative)",
            "T.INV": "Returns the t-value of the Student's t-distribution.\nSyntax: T.INV(probability, deg_freedom)",
            "CHISQ.DIST": "Returns the chi-squared distribution.\nSyntax: CHISQ.DIST(x, deg_freedom, cumulative)",
            "CHISQ.INV": "Returns the inverse of the chi-squared distribution.\nSyntax: CHISQ.INV(probability, deg_freedom)",
            "F.DIST": "Returns the F probability distribution.\nSyntax: F.DIST(x, deg_freedom1, deg_freedom2, cumulative)",
            "F.INV": "Returns the inverse of the F probability distribution.\nSyntax: F.INV(probability, deg_freedom1, deg_freedom2)",
            "CONFIDENCE": "Returns the confidence interval for a population mean.\nSyntax: CONFIDENCE(alpha, standard_dev, size)",
            "CONFIDENCE.NORM": "Returns the confidence interval for a population mean, using a normal distribution.\nSyntax: CONFIDENCE.NORM(alpha, standard_dev, size)",
            "CONFIDENCE.T": "Returns the confidence interval for a population mean, using a Student's t distribution.\nSyntax: CONFIDENCE.T(alpha, standard_dev, size)",

            # Logical Functions
            "IF": "Specifies a logical test to perform. Returns one value if the condition is TRUE and another value if it's FALSE.\nSyntax: IF(logical_test, value_if_true, [value_if_false])",
            "IFS": "Checks whether one or more conditions are met and returns a value that corresponds to the first TRUE condition.\nSyntax: IFS(logical_test1, value_if_true1, [logical_test2, value_if_true2], ...)",
            "IFERROR": "Returns a value you specify if a formula evaluates to an error; otherwise, returns the result of the formula.\nSyntax: IFERROR(value, value_if_error)",
            "IFNA": "Returns the value you specify if the expression resolves to #N/A, otherwise returns the result of the expression.\nSyntax: IFNA(value, value_if_na)",
            "AND": "Returns TRUE if all of its arguments are TRUE.\nSyntax: AND(logical1, [logical2], ...)",
            "OR": "Returns TRUE if any argument is TRUE.\nSyntax: OR(logical1, [logical2], ...)",
            "NOT": "Reverses the logic of its argument.\nSyntax: NOT(logical)",
            "XOR": "Returns a logical Exclusive OR of all arguments.\nSyntax: XOR(logical1, [logical2], ...)",
            "TRUE": "Returns the logical value TRUE.\nSyntax: TRUE()",
            "FALSE": "Returns the logical value FALSE.\nSyntax: FALSE()",
            "SWITCH": "Evaluates an expression against a list of values and returns the result corresponding to the first matching value.\nSyntax: SWITCH(expression, value1, result1, [default or value2, result2], ...)",
            "CHOOSE": "Uses index_num to return a value from the list of value arguments.\nSyntax: CHOOSE(index_num, value1, [value2], ...)",

            # Text Functions
            "CONCATENATE": "Joins several text items into one text item.\nSyntax: CONCATENATE(text1, [text2], ...)",
            "CONCAT": "Combines the text from multiple ranges and/or strings, but it doesn't provide delimiter or IgnoreEmpty arguments.\nSyntax: CONCAT(text1, [text2], ...)",
            "TEXTJOIN": "Joins text from multiple ranges and/or strings, and includes a delimiter you specify between each text value.\nSyntax: TEXTJOIN(delimiter, ignore_empty, text1, [text2], ...)",
            "LEFT": "Returns the specified number of characters from the start of a text string.\nSyntax: LEFT(text, [num_chars])",
            "RIGHT": "Returns the specified number of characters from the end of a text string.\nSyntax: RIGHT(text, [num_chars])",
            "MID": "Returns a specific number of characters from a text string, starting at the position you specify.\nSyntax: MID(text, start_num, num_chars)",
            "LEN": "Returns the number of characters in a text string.\nSyntax: LEN(text)",
            "LENB": "Returns the number of bytes used to represent the characters in a text string.\nSyntax: LENB(text)",
            "UPPER": "Converts text to uppercase.\nSyntax: UPPER(text)",
            "LOWER": "Converts all uppercase letters in a text string to lowercase.\nSyntax: LOWER(text)",
            "PROPER": "Capitalizes the first letter in each word of a text value.\nSyntax: PROPER(text)",
            "TRIM": "Removes all spaces from text except for single spaces between words.\nSyntax: TRIM(text)",
            "CLEAN": "Removes all nonprintable characters from text.\nSyntax: CLEAN(text)",
            "SUBSTITUTE": "Substitutes new_text for old_text in a text string.\nSyntax: SUBSTITUTE(text, old_text, new_text, [instance_num])",
            "REPLACE": "Replaces part of a text string with a different text string.\nSyntax: REPLACE(old_text, start_num, num_chars, new_text)",
            "REPLACEB": "Replaces part of a text string, based on the number of bytes you specify.\nSyntax: REPLACEB(old_text, start_num, num_bytes, new_text)",
            "FIND": "Finds one text value within another (case-sensitive).\nSyntax: FIND(find_text, within_text, [start_num])",
            "FINDB": "Finds one text value within another (case-sensitive), using bytes.\nSyntax: FINDB(find_text, within_text, [start_num])",
            "SEARCH": "Finds one text value within another (not case-sensitive).\nSyntax: SEARCH(find_text, within_text, [start_num])",
            "SEARCHB": "Finds one text value within another (not case-sensitive), using bytes.\nSyntax: SEARCHB(find_text, within_text, [start_num])",
            "TEXT": "Formats a number and converts it to text.\nSyntax: TEXT(value, format_text)",
            "VALUE": "Converts a text argument to a number.\nSyntax: VALUE(text)",
            "FIXED": "Formats a number as text with a fixed number of decimals.\nSyntax: FIXED(number, [decimals], [no_commas])",
            "DOLLAR": "Converts a number to text, using the $ (dollar) currency format.\nSyntax: DOLLAR(number, [decimals])",
            "CHAR": "Returns the character specified by the code number.\nSyntax: CHAR(number)",
            "CODE": "Returns a numeric code for the first character in a text string.\nSyntax: CODE(text)",
            "UNICODE": "Returns the number (code point) that corresponds to the first character of the text.\nSyntax: UNICODE(text)",
            "UNICHAR": "Returns the Unicode character that is referenced by the given numeric value.\nSyntax: UNICHAR(number)",
            "REPT": "Repeats text a given number of times.\nSyntax: REPT(text, number_times)",
            "EXACT": "Checks to see if two text values are identical.\nSyntax: EXACT(text1, text2)",
            "T": "Converts its arguments to text.\nSyntax: T(value)",
            "N": "Returns a value converted to a number.\nSyntax: N(value)",

            # Date & Time Functions
            "NOW": "Returns the serial number of the current date and time.\nSyntax: NOW()",
            "TODAY": "Returns the serial number of today's date.\nSyntax: TODAY()",
            "DATE": "Returns the serial number of a particular date.\nSyntax: DATE(year, month, day)",
            "DATEVALUE": "Converts a date in the form of text to a serial number.\nSyntax: DATEVALUE(date_text)",
            "TIME": "Returns the serial number of a particular time.\nSyntax: TIME(hour, minute, second)",
            "TIMEVALUE": "Converts a time in the form of text to a serial number.\nSyntax: TIMEVALUE(time_text)",
            "YEAR": "Returns the year corresponding to a date.\nSyntax: YEAR(serial_number)",
            "MONTH": "Returns the month of a date represented by a serial number.\nSyntax: MONTH(serial_number)",
            "DAY": "Returns the day of a date represented by a serial number.\nSyntax: DAY(serial_number)",
            "HOUR": "Returns the hour of a time value.\nSyntax: HOUR(serial_number)",
            "MINUTE": "Returns the minutes of a time value.\nSyntax: MINUTE(serial_number)",
            "SECOND": "Returns the seconds of a time value.\nSyntax: SECOND(serial_number)",
            "WEEKDAY": "Returns the day of the week corresponding to a date.\nSyntax: WEEKDAY(serial_number, [return_type])",
            "WEEKNUM": "Returns the week number of a specific date.\nSyntax: WEEKNUM(serial_number, [return_type])",
            "ISOWEEKNUM": "Returns the number of the ISO week number of the year for a given date.\nSyntax: ISOWEEKNUM(date)",
            "WORKDAY": "Returns the serial number of the date before or after a specified number of workdays.\nSyntax: WORKDAY(start_date, days, [holidays])",
            "WORKDAY.INTL": "Returns the serial number of the date before or after a specified number of workdays using parameters to indicate which and how many days are weekend days.\nSyntax: WORKDAY.INTL(start_date, days, [weekend], [holidays])",
            "NETWORKDAYS": "Returns the number of whole workdays between two dates.\nSyntax: NETWORKDAYS(start_date, end_date, [holidays])",
            "NETWORKDAYS.INTL": "Returns the number of whole workdays between two dates using parameters to indicate which and how many days are weekend days.\nSyntax: NETWORKDAYS.INTL(start_date, end_date, [weekend], [holidays])",
            "DATEDIF": "Calculates the number of days, months, or years between two dates.\nSyntax: DATEDIF(start_date, end_date, unit)",
            "DAYS": "Returns the number of days between two dates.\nSyntax: DAYS(end_date, start_date)",
            "DAYS360": "Calculates the number of days between two dates based on a 360-day year.\nSyntax: DAYS360(start_date, end_date, [method])",
            "EDATE": "Returns the serial number of the date that is the indicated number of months before or after the start date.\nSyntax: EDATE(start_date, months)",
            "EOMONTH": "Returns the serial number of the last day of the month before or after a specified number of months.\nSyntax: EOMONTH(start_date, months)",
            "YEARFRAC": "Returns the year fraction representing the number of whole days between start_date and end_date.\nSyntax: YEARFRAC(start_date, end_date, [basis])",

            # Lookup & Reference Functions
            "VLOOKUP": "Looks in the first column of an array and moves across the row to return the value of a cell.\nSyntax: VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup])",
            "HLOOKUP": "Searches for a value in the top row of a table, and then returns a value in the same column from a row you specify.\nSyntax: HLOOKUP(lookup_value, table_array, row_index_num, [range_lookup])",
            "XLOOKUP": "Searches a range or an array, and returns an item corresponding to the first match it finds. If a match doesn't exist, then XLOOKUP can return the closest (approximate) match.\nSyntax: XLOOKUP(lookup_value, lookup_array, return_array, [if_not_found], [match_mode], [search_mode])",
            "LOOKUP": "Looks up values in a vector or array.\nSyntax: LOOKUP(lookup_value, lookup_vector, [result_vector])",
            "INDEX": "Uses an index to choose a value from a reference or array.\nSyntax: INDEX(array, row_num, [column_num])",
            "MATCH": "Looks up values in a reference or array.\nSyntax: MATCH(lookup_value, lookup_array, [match_type])",
            "OFFSET": "Returns a reference offset from a given reference.\nSyntax: OFFSET(reference, rows, cols, [height], [width])",
            "INDIRECT": "Returns a reference indicated by a text value.\nSyntax: INDIRECT(ref_text, [a1])",
            "ROW": "Returns the row number of a reference.\nSyntax: ROW([reference])",
            "ROWS": "Returns the number of rows in a reference.\nSyntax: ROWS(array)",
            "COLUMN": "Returns the column number of a reference.\nSyntax: COLUMN([reference])",
            "COLUMNS": "Returns the number of columns in a reference.\nSyntax: COLUMNS(array)",
            "ADDRESS": "Returns a reference as text to a single cell in a worksheet.\nSyntax: ADDRESS(row_num, column_num, [abs_num], [a1], [sheet_text])",
            "AREAS": "Returns the number of areas in a reference.\nSyntax: AREAS(reference)",
            "HYPERLINK": "Creates a shortcut or jump that opens a document stored on a network server, an intranet, or the Internet.\nSyntax: HYPERLINK(link_location, [friendly_name])",
            "TRANSPOSE": "Returns the transpose of an array.\nSyntax: TRANSPOSE(array)",
            "FORMULATEXT": "Returns the formula at the given reference as text.\nSyntax: FORMULATEXT(reference)",

            # Financial Functions
            "PMT": "Calculates the payment for a loan based on constant payments and a constant interest rate.\nSyntax: PMT(rate, nper, pv, [fv], [type])",
            "PPMT": "Returns the payment on the principal for a given period for an investment based on periodic, constant payments and a constant interest rate.\nSyntax: PPMT(rate, per, nper, pv, [fv], [type])",
            "IPMT": "Returns the interest payment for an investment for a given period.\nSyntax: IPMT(rate, per, nper, pv, [fv], [type])",
            "FV": "Returns the future value of an investment.\nSyntax: FV(rate, nper, pmt, [pv], [type])",
            "PV": "Returns the present value of an investment.\nSyntax: PV(rate, nper, pmt, [fv], [type])",
            "NPV": "Returns the net present value of an investment based on a series of periodic cash flows and a discount rate.\nSyntax: NPV(rate, value1, [value2], ...)",
            "XNPV": "Returns the net present value for a schedule of cash flows that is not necessarily periodic.\nSyntax: XNPV(rate, values, dates)",
            "RATE": "Returns the interest rate per period of an annuity.\nSyntax: RATE(nper, pmt, pv, [fv], [type], [guess])",
            "NPER": "Returns the number of periods for an investment.\nSyntax: NPER(rate, pmt, pv, [fv], [type])",
            "IRR": "Returns the internal rate of return for a series of cash flows.\nSyntax: IRR(values, [guess])",
            "XIRR": "Returns the internal rate of return for a schedule of cash flows that is not necessarily periodic.\nSyntax: XIRR(values, dates, [guess])",
            "MIRR": "Returns the internal rate of return where positive and negative cash flows are financed at different rates.\nSyntax: MIRR(values, finance_rate, reinvest_rate)",
            "DB": "Returns the depreciation of an asset for a specified period by using the fixed-declining balance method.\nSyntax: DB(cost, salvage, life, period, [month])",
            "DDB": "Returns the depreciation of an asset for a specified period by using the double-declining balance method or some other method that you specify.\nSyntax: DDB(cost, salvage, life, period, [factor])",
            "SLN": "Returns the straight-line depreciation of an asset for one period.\nSyntax: SLN(cost, salvage, life)",
            "SYD": "Returns the sum-of-years' digits depreciation of an asset for a specified period.\nSyntax: SYD(cost, salvage, life, per)",
            "VDB": "Returns the depreciation of an asset for a specified or partial period by using a declining balance method.\nSyntax: VDB(cost, salvage, life, start_period, end_period, [factor], [no_switch])",
            "EFFECT": "Returns the effective annual interest rate.\nSyntax: EFFECT(nominal_rate, npery)",
            "NOMINAL": "Returns the annual nominal interest rate.\nSyntax: NOMINAL(effect_rate, npery)",
            "CUMIPMT": "Returns the cumulative interest paid between two periods.\nSyntax: CUMIPMT(rate, nper, pv, start_period, end_period, type)",
            "CUMPRINC": "Returns the cumulative principal paid on a loan between two periods.\nSyntax: CUMPRINC(rate, nper, pv, start_period, end_period, type)",
            "PRICE": "Returns the price per $100 face value of a security that pays periodic interest.\nSyntax: PRICE(settlement, maturity, rate, yld, redemption, frequency, [basis])",
            "YIELD": "Returns the yield on a security that pays periodic interest.\nSyntax: YIELD(settlement, maturity, rate, pr, redemption, frequency, [basis])",
            "DISC": "Returns the discount rate for a security.\nSyntax: DISC(settlement, maturity, pr, redemption, [basis])",
            "INTRATE": "Returns the interest rate for a fully invested security.\nSyntax: INTRATE(settlement, maturity, investment, redemption, [basis])",
            "RECEIVED": "Returns the amount received at maturity for a fully invested security.\nSyntax: RECEIVED(settlement, maturity, investment, discount, [basis])",

            # Information Functions
            "ISBLANK": "Returns TRUE if the value is blank.\nSyntax: ISBLANK(value)",
            "ISERROR": "Returns TRUE if the value is any error value.\nSyntax: ISERROR(value)",
            "ISERR": "Returns TRUE if the value is any error value except #N/A.\nSyntax: ISERR(value)",
            "ISNA": "Returns TRUE if the value is the #N/A error value.\nSyntax: ISNA(value)",
            "ISTEXT": "Returns TRUE if the value is text.\nSyntax: ISTEXT(value)",
            "ISNUMBER": "Returns TRUE if the value is a number.\nSyntax: ISNUMBER(value)",
            "ISLOGICAL": "Returns TRUE if the value is a logical value.\nSyntax: ISLOGICAL(value)",
            "ISREF": "Returns TRUE if the value is a reference.\nSyntax: ISREF(value)",
            "ISFORMULA": "Returns TRUE if there is a reference to a cell that contains a formula.\nSyntax: ISFORMULA(reference)",
            "ISEVEN": "Returns TRUE if the number is even.\nSyntax: ISEVEN(number)",
            "ISODD": "Returns TRUE if the number is odd.\nSyntax: ISODD(number)",
            "TYPE": "Returns a number indicating the data type of a value.\nSyntax: TYPE(value)",
            "ERROR.TYPE": "Returns a number corresponding to an error type.\nSyntax: ERROR.TYPE(error_val)",
            "NA": "Returns the error value #N/A.\nSyntax: NA()",
            "INFO": "Returns information about the current operating environment.\nSyntax: INFO(type_text)",
            "CELL": "Returns information about the formatting, location, or contents of a cell.\nSyntax: CELL(info_type, [reference])",
            "SHEET": "Returns the sheet number of the referenced sheet.\nSyntax: SHEET([value])",
            "SHEETS": "Returns the number of sheets in a reference.\nSyntax: SHEETS([reference])",

            # Database Functions
            "DSUM": "Adds the numbers in the field column of records in the database that match the criteria.\nSyntax: DSUM(database, field, criteria)",
            "DAVERAGE": "Returns the average of selected database entries.\nSyntax: DAVERAGE(database, field, criteria)",
            "DCOUNT": "Counts the cells that contain numbers in a database.\nSyntax: DCOUNT(database, field, criteria)",
            "DCOUNTA": "Counts nonblank cells in a database.\nSyntax: DCOUNTA(database, field, criteria)",
            "DMAX": "Returns the maximum value from selected database entries.\nSyntax: DMAX(database, field, criteria)",
            "DMIN": "Returns the minimum value from selected database entries.\nSyntax: DMIN(database, field, criteria)",
            "DGET": "Extracts from a database a single record that matches the specified criteria.\nSyntax: DGET(database, field, criteria)",
            "DPRODUCT": "Multiplies the values in the field column of records in the database that match the criteria.\nSyntax: DPRODUCT(database, field, criteria)",
            "DSTDEV": "Estimates the standard deviation based on a sample of selected database entries.\nSyntax: DSTDEV(database, field, criteria)",
            "DSTDEVP": "Calculates the standard deviation based on the entire population of selected database entries.\nSyntax: DSTDEVP(database, field, criteria)",
            "DVAR": "Estimates variance based on a sample from selected database entries.\nSyntax: DVAR(database, field, criteria)",
            "DVARP": "Calculates variance based on the entire population of selected database entries.\nSyntax: DVARP(database, field, criteria)",

            # Engineering Functions
            "BIN2DEC": "Converts a binary number to decimal.\nSyntax: BIN2DEC(number)",
            "BIN2HEX": "Converts a binary number to hexadecimal.\nSyntax: BIN2HEX(number, [places])",
            "BIN2OCT": "Converts a binary number to octal.\nSyntax: BIN2OCT(number, [places])",
            "DEC2BIN": "Converts a decimal number to binary.\nSyntax: DEC2BIN(number, [places])",
            "DEC2HEX": "Converts a decimal number to hexadecimal.\nSyntax: DEC2HEX(number, [places])",
            "DEC2OCT": "Converts a decimal number to octal.\nSyntax: DEC2OCT(number, [places])",
            "HEX2BIN": "Converts a hexadecimal number to binary.\nSyntax: HEX2BIN(number, [places])",
            "HEX2DEC": "Converts a hexadecimal number to decimal.\nSyntax: HEX2DEC(number)",
            "HEX2OCT": "Converts a hexadecimal number to octal.\nSyntax: HEX2OCT(number, [places])",
            "OCT2BIN": "Converts an octal number to binary.\nSyntax: OCT2BIN(number, [places])",
            "OCT2DEC": "Converts an octal number to decimal.\nSyntax: OCT2DEC(number)",
            "OCT2HEX": "Converts an octal number to hexadecimal.\nSyntax: OCT2HEX(number, [places])",
            "CONVERT": "Converts a number from one measurement system to another.\nSyntax: CONVERT(number, from_unit, to_unit)",
            "DELTA": "Tests whether two values are equal.\nSyntax: DELTA(number1, [number2])",
            "GESTEP": "Tests whether a number is greater than a threshold value.\nSyntax: GESTEP(number, [step])",
            "COMPLEX": "Converts real and imaginary coefficients into a complex number.\nSyntax: COMPLEX(real_num, i_num, [suffix])",
            "IMREAL": "Returns the real coefficient of a complex number.\nSyntax: IMREAL(inumber)",
            "IMAGINARY": "Returns the imaginary coefficient of a complex number.\nSyntax: IMAGINARY(inumber)",
            "IMSUM": "Returns the sum of complex numbers.\nSyntax: IMSUM(inumber1, [inumber2], ...)",
            "IMSUB": "Returns the difference between two complex numbers.\nSyntax: IMSUB(inumber1, inumber2)",
            "IMPRODUCT": "Returns the product of complex numbers.\nSyntax: IMPRODUCT(inumber1, [inumber2], ...)",
            "IMDIV": "Returns the quotient of two complex numbers.\nSyntax: IMDIV(inumber1, inumber2)",
            "IMABS": "Returns the absolute value (modulus) of a complex number.\nSyntax: IMABS(inumber)",
            "IMARGUMENT": "Returns the argument theta, an angle expressed in radians.\nSyntax: IMARGUMENT(inumber)",
        }

        # Add "All" category
        self.categories["All"] = self.get_all_functions()

        self.category_combo.addItem("All")
        self.category_combo.addItems([k for k in self.categories.keys() if k != "All"])
        self.category_combo.currentTextChanged.connect(self.update_function_list)
        cat_layout.addWidget(self.category_combo)
        layout.addLayout(cat_layout)

        # Function list
        label = QLabel("Select a function:")
        layout.addWidget(label)
        self.list_widget = QListWidget()
        self.update_function_list("All")
        layout.addWidget(self.list_widget)

        # Description
        desc_label = QLabel("Description:")
        layout.addWidget(desc_label)
        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(100)
        layout.addWidget(self.desc_text)

        self.list_widget.currentItemChanged.connect(self.show_description)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_all_functions(self):
        all_funcs = set()
        for key, funcs in self.categories.items():
            if key != "All" and isinstance(funcs, list):
                all_funcs.update(funcs)
        return sorted(all_funcs)

    def update_function_list(self, category):
        self.list_widget.clear()
        if category == "All":
            self.list_widget.addItems(sorted(self.categories.get("All", [])))
        else:
            self.list_widget.addItems(self.categories.get(category, []))
        if hasattr(self, 'search_box') and self.search_box.text():
            self.filter_functions(self.search_box.text())

    def filter_functions(self, search_text):
        search_text = search_text.upper()
        current_category = self.category_combo.currentText()
        if current_category == "All":
            all_functions = sorted(self.categories.get("All", []))
        else:
            all_functions = self.categories.get(current_category, [])

        if search_text:
            filtered = [f for f in all_functions if search_text in f.upper()]
        else:
            filtered = all_functions

        self.list_widget.clear()
        self.list_widget.addItems(filtered)

    def show_description(self, current, previous):
        if current:
            func = current.text()
            desc = self.descriptions.get(func, f"{func} function - No description available.")
            self.desc_text.setText(desc)

    def selected_function(self):
        item = self.list_widget.currentItem()
        return item.text() if item else None


# -----------------------------
# Search and Replace Dialog
# -----------------------------
class SearchReplaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowTitle("Search and Replace")
        self.resize(400, 200)

        layout = QVBoxLayout()

        # Search field
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Find:"))
        self.search_input = QLineEdit()
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Replace field
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        # Options
        options_layout = QHBoxLayout()
        self.case_sensitive = QCheckBox("Case sensitive")
        self.whole_cell = QCheckBox("Match entire cell")
        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.whole_cell)
        layout.addLayout(options_layout)

        # Buttons
        button_layout = QHBoxLayout()

        find_next_btn = QPushButton("Find Next")
        find_next_btn.clicked.connect(self.find_next)
        button_layout.addWidget(find_next_btn)

        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.replace_current)
        button_layout.addWidget(replace_btn)

        replace_all_btn = QPushButton("Replace All")
        replace_all_btn.clicked.connect(self.replace_all)
        button_layout.addWidget(replace_all_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.current_match = None
        self.search_start_row = 0
        self.search_start_col = 0

    def find_next(self):
        if not self.parent_widget:
            return

        search_text = self.search_input.text()
        if not search_text:
            self.status_label.setText("Enter search text")
            return

        table = self.parent_widget.table
        rows = self.parent_widget.rows
        cols = self.parent_widget.cols

        # Start from current cell or last found position
        start_row = table.currentRow() if table.currentRow() >= 0 else 0
        start_col = table.currentColumn() + 1 if table.currentColumn() >= 0 else 0

        case_sensitive = self.case_sensitive.isChecked()
        whole_cell = self.whole_cell.isChecked()

        # Search through all cells
        for i in range(rows * cols):
            row = (start_row + (start_col + i) // cols) % rows
            col = (start_col + i) % cols

            item = table.item(row, col)
            if item:
                cell_text = item.text()
                compare_search = search_text if case_sensitive else search_text.lower()
                compare_cell = cell_text if case_sensitive else cell_text.lower()

                found = False
                if whole_cell:
                    found = compare_cell == compare_search
                else:
                    found = compare_search in compare_cell

                if found:
                    table.setCurrentCell(row, col)
                    self.current_match = (row, col)
                    self.status_label.setText(f"Found at {chr(ord('A') + col)}{row + 1}")
                    return

        self.status_label.setText("No match found")
        self.current_match = None

    def replace_current(self):
        if not self.parent_widget or not self.current_match:
            self.find_next()
            return

        row, col = self.current_match
        table = self.parent_widget.table
        item = table.item(row, col)

        if item:
            search_text = self.search_input.text()
            replace_text = self.replace_input.text()
            case_sensitive = self.case_sensitive.isChecked()
            whole_cell = self.whole_cell.isChecked()

            cell_text = item.text()

            if whole_cell:
                item.setText(replace_text)
            else:
                if case_sensitive:
                    new_text = cell_text.replace(search_text, replace_text, 1)
                else:
                    # Case-insensitive replace
                    pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                    new_text = pattern.sub(replace_text, cell_text, 1)
                item.setText(new_text)

            self.status_label.setText(f"Replaced at {chr(ord('A') + col)}{row + 1}")
            self.find_next()

    def replace_all(self):
        if not self.parent_widget:
            return

        search_text = self.search_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            self.status_label.setText("Enter search text")
            return

        table = self.parent_widget.table
        rows = self.parent_widget.rows
        cols = self.parent_widget.cols

        case_sensitive = self.case_sensitive.isChecked()
        whole_cell = self.whole_cell.isChecked()

        count = 0
        for row in range(rows):
            for col in range(cols):
                item = table.item(row, col)
                if item:
                    cell_text = item.text()
                    compare_search = search_text if case_sensitive else search_text.lower()
                    compare_cell = cell_text if case_sensitive else cell_text.lower()

                    if whole_cell:
                        if compare_cell == compare_search:
                            item.setText(replace_text)
                            count += 1
                    else:
                        if compare_search in compare_cell:
                            if case_sensitive:
                                new_text = cell_text.replace(search_text, replace_text)
                            else:
                                pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                                new_text = pattern.sub(replace_text, cell_text)
                            item.setText(new_text)
                            count += 1

        self.status_label.setText(f"Replaced {count} occurrence(s)")


# -----------------------------
# LaTeX Export Dialog
# -----------------------------
class LatexExportDialog(QDialog):
    def __init__(self, latex_code, parent=None):
        super().__init__(parent)
        self.latex_code = latex_code
        self.setWindowTitle("LaTeX Export")
        self.resize(600, 400)

        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        text_edit = QTextEdit()
        text_edit.setPlainText(self.latex_code)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier", 10))
        scroll.setWidget(text_edit)
        layout.addWidget(scroll)

        button_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.latex_code)
        QMessageBox.information(self, "Copied", "LaTeX code copied to clipboard!")


# -----------------------------
# SpreadsheetWidget
# -----------------------------
class SpreadsheetWidget(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # Reference to main application window


        self.rows = 50
        self.cols = 26
        self.formulas = {}
        self.clipboard = []
        self.clipboard_source = None  # Track source for paste linked
        self.updating = False
        self.cell_dependencies = {}
        self.merged_cells = {}  # Track merged cells: (row, col) -> (row_span, col_span)

        # Initialize undo stack
        self.undo_stack = QUndoStack(self)
        self.setup_ui()
        
    def setup_ui(self):        
        #central = QWidget()
        #self.setCentralWidget(central)
        main_layout = QVBoxLayout(self)

        # First Toolbar - Edit and Data Operations
        toolbar1 = QToolBar("Edit Toolbar")
        toolbar1.setMovable(False)
        #self.addToolBar(Qt.TopToolBarArea, toolbar1)

        # Edit operations
        copy_action = toolbar1.addAction("Copy", self.copy)
        copy_action.setShortcut(QKeySequence.Copy)
        cut_action = toolbar1.addAction("Cut", self.cut)
        cut_action.setShortcut(QKeySequence.Cut)
        paste_action = toolbar1.addAction("Paste", self.paste)
        paste_action.setShortcut(QKeySequence.Paste)
        toolbar1.addAction("Paste Linked", self.paste_linked)
        delete_action = toolbar1.addAction("Delete", self.delete_cells)
        delete_action.setShortcut(QKeySequence.Delete)
        toolbar1.addAction("Search/Replace", self.show_search_replace)
        
        toolbar1.addSeparator()
        
        # Undo and Redo
        undo_action = toolbar1.addAction("Undo", self.undo_stack.undo)
        undo_action.setShortcut(QKeySequence.Undo)
        redo_action = toolbar1.addAction("Redo", self.undo_stack.redo)
        redo_action.setShortcut(QKeySequence.Redo)
        
        toolbar1.addSeparator()

        # Insert/Remove operations
        operations_label = QLabel("")
        toolbar1.addWidget(operations_label)
        self.operations_combo = QComboBox()
        self.operations_combo.addItems([
            "Select Operation...",
            "Insert Row",
            "Insert Column",
            "Remove Row",
            "Remove Column",
            "Insert Cell (Shift Right)",
            "Insert Cell (Shift Down)",
            "Remove Cell (Shift Left)",
            "Remove Cell (Shift Up)"
        ])
        self.operations_combo.currentTextChanged.connect(self.perform_operation)
        toolbar1.addWidget(self.operations_combo)

        toolbar1.addSeparator()

        # Sort operations
        sort_label = QLabel("")
        toolbar1.addWidget(sort_label)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Select Sort...",
            "Sort Ascending (A→Z, 0→9)",
            "Sort Descending (Z→A, 9→0)"
        ])
        self.sort_combo.currentTextChanged.connect(self.perform_sort)
        toolbar1.addWidget(self.sort_combo)

        main_layout.addWidget(toolbar1)

        # Force toolbar break - second toolbar on new line
        #self.addToolBarBreak(Qt.TopToolBarArea)

        # Second Toolbar - Formatting Operations (on separate line)
        toolbar2 = QToolBar("Formatting Toolbar")
        toolbar2.setMovable(False)
        #self.addToolBar(Qt.TopToolBarArea, toolbar2)

        # Font formatting
        toolbar2.addAction("Bold", self.set_bold)
        toolbar2.addAction("Italic", self.set_italic)
        toolbar2.addAction("Normal", self.set_normal)
        toolbar2.addSeparator()

        # Alignment
        toolbar2.addAction("Left", self.set_align_left)
        toolbar2.addAction("Center", self.set_align_center)
        toolbar2.addAction("Right", self.set_align_right)
        toolbar2.addSeparator()

        # Border
        border_label = QLabel("Border:")
        toolbar2.addWidget(border_label)
        self.border_combo = QComboBox()
        self.border_combo.addItems([
            "None", "Top", "Bottom", "Left", "Right",
            "Top & Bottom", "Left & Right", "All (Box)"
        ])
        self.border_combo.currentTextChanged.connect(self.set_border_combobox)
        toolbar2.addWidget(self.border_combo)
        toolbar2.addSeparator()

        # Colors
        toolbar2.addAction("Fill Color", self.set_fill_color)
        toolbar2.addAction("Text Color", self.set_text_color)
        toolbar2.addSeparator()

        # Merge cells
        toolbar2.addAction("Merge Cells", self.merge_cells)
        toolbar2.addAction("Unmerge Cells", self.unmerge_cells)
        toolbar2.addSeparator()

        # Functions
        toolbar2.addAction("Insert Function", self.insert_function)
        
        main_layout.addWidget(toolbar2)

        # Formula bar layout
        formula_layout = QHBoxLayout()

        # Cell reference label
        self.cell_ref_label = QLabel("A1")
        self.cell_ref_label.setMinimumWidth(50)
        self.cell_ref_label.setFrameStyle(QLabel.Panel | QLabel.Sunken)
        formula_layout.addWidget(self.cell_ref_label)

        # Formula bar buttons - create a button group
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)

        self.btn_cancel = QPushButton("✗")
        self.btn_cancel.setMaximumWidth(30)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_formula)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
                border-right: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                color: #999;
            }
        """)
        button_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("✓")
        self.btn_ok.setMaximumWidth(30)
        self.btn_ok.setEnabled(False)
        self.btn_ok.clicked.connect(self.formula_entered)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-left: none;
                border-right: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                color: #999;
            }
        """)
        button_layout.addWidget(self.btn_ok)

        self.btn_fx = QPushButton("fx")
        self.btn_fx.setMaximumWidth(30)
        self.btn_fx.setEnabled(False)
        self.btn_fx.clicked.connect(self.insert_function)
        self.btn_fx.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                border-left: none;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                color: #999;
            }
        """)
        button_layout.addWidget(self.btn_fx)
        formula_layout.addWidget(button_widget)

        self.formula_bar = FormulaBarLineEdit(self)
        self.formula_bar.returnPressed.connect(self.formula_entered)
        self.formula_bar.textChanged.connect(self.on_formula_bar_changed)
        formula_layout.addWidget(self.formula_bar)

        main_layout.addLayout(formula_layout)

        # Table
        self.table = SpreadsheetTable(self.rows, self.cols, self)
        self.table.setItemDelegate(BorderDelegate())

        # Enable selection of entire rows and columns
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)

        # Connect header clicks to select entire column/row
        self.table.horizontalHeader().sectionClicked.connect(self.select_column)
        self.table.verticalHeader().sectionClicked.connect(self.select_row)

        headers = [chr(ord('A') + i) for i in range(self.cols)]
        self.table.setHorizontalHeaderLabels(headers)

        for r in range(self.rows):
            for c in range(self.cols):
                item = QTableWidgetItem("")
                self.table.setItem(r, c, item)

        self.table.currentCellChanged.connect(self.cell_selected)
        self.table.itemChanged.connect(self.on_item_changed)

        main_layout.addWidget(self.table)

        # Bottom toolbar - Export/Insert operations
        bottom_layout = QHBoxLayout()
        
        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom_layout.addWidget(spacer_left)

        # Export CSV button
        export_csv_btn = QPushButton("📄 Export CSV")
        export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        export_csv_btn.clicked.connect(self.export_csv)
        bottom_layout.addWidget(export_csv_btn)

        # Insert LaTeX button (replaces Export LaTeX)
        insert_latex_btn = QPushButton("📝 Insert LaTeX")
        insert_latex_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        insert_latex_btn.clicked.connect(self.insert_latex_to_editor)
        insert_latex_btn.setToolTip("Insert table as LaTeX code into the editor")
        bottom_layout.addWidget(insert_latex_btn)

        # Copy LaTeX button
        copy_latex_btn = QPushButton("📋 Copy LaTeX")
        copy_latex_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #7B1FA2; }
        """)
        copy_latex_btn.clicked.connect(self.copy_latex_to_clipboard)
        copy_latex_btn.setToolTip("Copy LaTeX code to clipboard")
        bottom_layout.addWidget(copy_latex_btn)

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom_layout.addWidget(spacer_right)

        main_layout.addLayout(bottom_layout)
    def generate_latex(self):
        """Generate LaTeX code from the spreadsheet data"""
        # Find the actual data range
        max_row = 0
        max_col = 0
        for r in range(self.rows):
            for c in range(self.cols):
                item = self.table.item(r, c)
                if item and item.text():
                    max_row = max(max_row, r)
                    max_col = max(max_col, c)

        if max_row == 0 and max_col == 0:
            item = self.table.item(0, 0)
            if not item or not item.text():
                return None  # No data

        # Generate LaTeX
        latex = "\\begin{table}[h]\n"
        latex += "\\centering\n"
        latex += "\\begin{tabular}{|" + "c|" * (max_col + 1) + "}\n"
        latex += "\\hline\n"

        for r in range(max_row + 1):
            row_data = []
            for c in range(max_col + 1):
                item = self.table.item(r, c)
                text = item.text() if item else ""
                # Escape LaTeX special characters
                text = text.replace("\\", "\\textbackslash ")
                text = text.replace("&", "\\&")
                text = text.replace("%", "\\%")
                text = text.replace("$", "\\$")
                text = text.replace("#", "\\#")
                text = text.replace("_", "\\_")
                text = text.replace("{", "\\{")
                text = text.replace("}", "\\}")
                text = text.replace("~", "\\textasciitilde ")
                text = text.replace("^", "\\textasciicircum ")
                row_data.append(text)
            latex += " & ".join(row_data) + " \\\\\n"
            latex += "\\hline\n"

        latex += "\\end{tabular}\n"
        latex += "\\caption{Table Caption}\n"
        latex += "\\label{tab:mytable}\n"
        latex += "\\end{table}"

        return latex

    def insert_latex_to_editor(self):
        """Insert LaTeX table code into the active editor"""
        latex = self.generate_latex()
        
        if not latex:
            QMessageBox.information(self, "Info", "No data to convert. Please enter some data in the spreadsheet first.")
            return

        try:
            if hasattr(self.main_window, 'editor_manager'):
                active_editor = self.main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    cursor.insertText("\n" + latex + "\n")
                    active_editor.setFocus()
                    
                    # Mark as modified
                    if hasattr(self.main_window.editor_manager, 'on_text_changed'):
                        self.main_window.editor_manager.on_text_changed()
                    
                    QMessageBox.information(self, "Success", "LaTeX table inserted into editor!")
                    #print("✅ Inserted LaTeX table into editor")
                else:
                    QMessageBox.warning(self, "Warning", "No active editor found! Please open a document first.")
            else:
                QMessageBox.warning(self, "Warning", "Editor manager not available!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert LaTeX:\n{str(e)}")

    def copy_latex_to_clipboard(self):
        """Copy LaTeX table code to clipboard"""
        latex = self.generate_latex()
        
        if not latex:
            QMessageBox.information(self, "Info", "No data to convert. Please enter some data in the spreadsheet first.")
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(latex)
        QMessageBox.information(self, "Copied", "LaTeX code copied to clipboard!")
        
    def on_formula_bar_changed(self):
        """Enable/disable buttons based on formula bar content"""
        text = self.formula_bar.text()
        has_formula = text.startswith("=")
        self.btn_cancel.setEnabled(has_formula)
        self.btn_ok.setEnabled(has_formula)
        self.btn_fx.setEnabled(has_formula)

        # Update formula mode in table
        self.table.formula_mode = has_formula

    def select_column(self, column):
        """Select entire column when header is clicked"""
        self.table.clearSelection()
        for row in range(self.rows):
            self.table.item(row, column).setSelected(True)

    def select_row(self, row):
        """Select entire row when header is clicked"""
        self.table.clearSelection()
        for col in range(self.cols):
            self.table.item(row, col).setSelected(True)

    def cancel_formula(self):
        """Clear formula bar content"""
        self.formula_bar.clear()
        self.table.formula_mode = False
        self.table.setFocus()

    def show_search_replace(self):
        """Show the search and replace dialog"""
        dialog = SearchReplaceDialog(self)
        dialog.exec_()

    def set_text_color(self):
        """Set text color for selected cells"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.updating = True
            for i in self.table.selectedIndexes():
                it = self.table.item(i.row(), i.column())
                it.setForeground(color)
            self.updating = False

    def merge_cells(self):
        """Merge selected cells"""
        sel = self.table.selectedIndexes()
        if not sel:
            self.main_window.update_status_bar("Please select cells to merge")
            return

        rows = sorted(set(i.row() for i in sel))
        cols = sorted(set(i.column() for i in sel))

        if len(rows) < 2 and len(cols) < 2:
            self.main_window.update_status_bar("Please select at least 2 cells to merge")
            return

        top_row = min(rows)
        bottom_row = max(rows)
        left_col = min(cols)
        right_col = max(cols)

        # Check if any cells in the selection are already part of a merged region
        for r in range(top_row, bottom_row + 1):
            for c in range(left_col, right_col + 1):
                # Check if this cell is the top-left of a merged region
                if (r, c) in self.merged_cells:
                    self.main_window.update_status_bar("Selection contains already merged cells. Unmerge first.")
                    return
                # Check if this cell is part of another merged region
                for (mr, mc), (rs, cs) in self.merged_cells.items():
                    if mr <= r < mr + rs and mc <= c < mc + cs:
                        self.main_window.update_status_bar("Selection contains already merged cells. Unmerge first.")
                        return

        # Collect old texts for undo
        old_texts = {}
        merged_content = []
        for r in range(top_row, bottom_row + 1):
            for c in range(left_col, right_col + 1):
                item = self.table.item(r, c)
                text = item.text() if item else ""
                old_texts[(r, c)] = text
                if text:
                    merged_content.append(text)

        # Combine content (join non-empty cells with space)
        merged_text = " ".join(merged_content)

        # Create and execute the merge command
        cmd = MergeCellsCommand(
            self.table, top_row, left_col, bottom_row, right_col,
            self.merged_cells, old_texts, merged_text, "Merge Cells"
        )
        self.undo_stack.push(cmd)

        self.main_window.update_status_bar(f"Merged cells from {chr(ord('A') + left_col)}{top_row + 1} to {chr(ord('A') + right_col)}{bottom_row + 1}")

    def unmerge_cells(self):
        """Unmerge selected cells"""
        row = self.table.currentRow()
        col = self.table.currentColumn()

        if row < 0 or col < 0:
            self.main_window.update_status_bar("Please select a merged cell to unmerge")
            return

        # Find if this cell is the top-left of a merged region
        if (row, col) in self.merged_cells:
            row_span, col_span = self.merged_cells[(row, col)]
            merged_text = self.table.item(row, col).text() if self.table.item(row, col) else ""

            cmd = UnmergeCellsCommand(
                self.table, row, col, row_span, col_span,
                self.merged_cells, merged_text, "Unmerge Cells"
            )
            self.undo_stack.push(cmd)

            self.main_window.update_status_bar(f"Unmerged cells at {chr(ord('A') + col)}{row + 1}")
        else:
            # Check if this cell is part of a merged region (but not the top-left)
            for (mr, mc), (rs, cs) in self.merged_cells.items():
                if mr <= row < mr + rs and mc <= col < mc + cs:
                    # Found the merge region, unmerge from its top-left
                    merged_text = self.table.item(mr, mc).text() if self.table.item(mr, mc) else ""

                    cmd = UnmergeCellsCommand(
                        self.table, mr, mc, rs, cs,
                        self.merged_cells, merged_text, "Unmerge Cells"
                    )
                    self.undo_stack.push(cmd)

                    self.main_window.update_status_bar(f"Unmerged cells at {chr(ord('A') + mc)}{mr + 1}")
                    return

            self.main_window.update_status_bar("Selected cell is not part of a merged region")

    def cell_selected(self, row, col, prev_row, prev_col):
        # Don't update formula bar if we're selecting range for formula
        if hasattr(self.table, 'is_selecting_range') and self.table.is_selecting_range:
            # Update cell reference label only
            if row >= 0 and col >= 0:
                cell_ref = f"{chr(ord('A') + col)}{row + 1}"
                self.cell_ref_label.setText(cell_ref)
            return

        if row >= 0 and col >= 0:
            cell_ref = f"{chr(ord('A') + col)}{row + 1}"
            self.cell_ref_label.setText(cell_ref)
            # Show cell info in status bar
            self.main_window.update_status_bar(f"Cell: {cell_ref}")

            # Only update formula bar if NOT in formula mode
            if not self.table.formula_mode:
                formula = self.formulas.get((row, col))
                if formula:
                    self.formula_bar.setText(formula)
                else:
                    item = self.table.item(row, col)
                    self.formula_bar.setText(item.text() if item else "")

    def formula_entered(self):
        """Process formula when Enter is pressed in formula bar"""
        r = self.table.currentRow()
        c = self.table.currentColumn()
        if r < 0 or c < 0:
            return

        text = self.formula_bar.text()
        item = self.table.item(r, c)
        old_text = item.text() if item else ""
        old_formula = self.formulas.get((r, c))

        if text.startswith("="):
            self.formulas[(r, c)] = text
            try:
                result = self.evaluate(text[1:])
                self.updating = True
                self.table.item(r, c).setText(str(result))
                self.updating = False

                # Track dependencies
                deps = self.get_formula_dependencies(text)
                for dep in deps:
                    if dep not in self.cell_dependencies:
                        self.cell_dependencies[dep] = []
                    if (r, c) not in self.cell_dependencies[dep]:
                        self.cell_dependencies[dep].append((r, c))

                # Create undo command
                cmd = CellEditCommand(
                    self.table, r, c, old_text, str(result),
                    old_formula, text, self.formulas, "Enter Formula"
                )
                self.undo_stack.push(cmd)

                self.main_window.update_status_bar(f"Formula evaluated successfully: {result}")
            except Exception as e:
                self.updating = True
                self.table.item(r, c).setText("#ERROR")
                self.updating = False
                self.main_window.update_status_bar(f"Error: {str(e)}")
        else:
            new_formula = None
            self.formulas.pop((r, c), None)
            self.updating = True
            self.table.item(r, c).setText(text)
            self.updating = False

            # Create undo command
            cmd = CellEditCommand(
                self.table, r, c, old_text, text,
                old_formula, new_formula, self.formulas, "Enter Value"
            )
            self.undo_stack.push(cmd)

            self.main_window.update_status_bar("Value entered")

        # Disable formula mode
        self.table.formula_mode = False

        # Move to next row
        if r + 1 < self.rows:
            self.table.setCurrentCell(r + 1, c)

    # -----------------------------
    # Formula evaluation
    # -----------------------------
    def evaluate(self, expr):
        """
        Evaluate a spreadsheet expression.
        Handles:
          - Arithmetic:  +  -  *  /  ^  (and Python ** as alias for ^)
          - Unary minus / plus
          - String literals in double or single quotes
          - Cell references  (A1, $B$2, etc.)
          - Range-returning functions  (SUM, AVERAGE, …)
          - Nested function calls of arbitrary depth
          - Boolean literals TRUE / FALSE
        """
        expr = expr.strip()
        if not expr:
            return ""
        tokens = self._tokenize(expr)
        result, pos = self._parse_expr(tokens, 0)
        return result


    # ------------------------------------------------------------------ #
    #  Tokeniser                                                           #
    # ------------------------------------------------------------------ #
    def _tokenize(self, expr):
        """
        Break *expr* into a list of tokens.
        Each token is a (type, value) pair where type is one of:
          'NUM', 'STR', 'BOOL', 'CELL', 'FUNC', 'OP', 'LPAREN',
          'RPAREN', 'COMMA', 'COLON'
        """
        tokens = []
        i = 0
        n = len(expr)
        while i < n:
            c = expr[i]

            # --- whitespace ---
            if c.isspace():
                i += 1
                continue

            # --- string literal ---
            if c in ('"', "'"):
                quote = c
                j = i + 1
                while j < n and expr[j] != quote:
                    if expr[j] == '\\':
                        j += 1          # skip escaped char
                    j += 1
                tokens.append(('STR', expr[i+1:j]))
                i = j + 1
                continue

            # --- number ---
            if c.isdigit() or (c == '.' and i+1 < n and expr[i+1].isdigit()):
                j = i
                while j < n and (expr[j].isdigit() or expr[j] == '.'):
                    j += 1
                if j < n and expr[j] in ('e', 'E'):
                    j += 1
                    if j < n and expr[j] in ('+', '-'):
                        j += 1
                    while j < n and expr[j].isdigit():
                        j += 1
                tokens.append(('NUM', float(expr[i:j])))
                i = j
                continue

            # --- identifiers: function names, cell refs, TRUE/FALSE ---
            if c.isalpha() or c == '$':
                j = i
                while j < n and (expr[j].isalnum() or expr[j] in ('$', '_', '.')):
                    j += 1
                word = expr[i:j]
                upper = word.upper().replace('$', '')
                if upper == 'TRUE':
                    tokens.append(('BOOL', True))
                elif upper == 'FALSE':
                    tokens.append(('BOOL', False))
                elif j < n and expr[j] == '(':
                    tokens.append(('FUNC', word.upper()))
                elif re.match(r'^\$?[A-Za-z]+\$?[0-9]+$', word):
                    tokens.append(('CELL', word))
                else:
                    # Treat unknown identifiers as 0 (safe fallback)
                    tokens.append(('NUM', 0))
                i = j
                continue

            # --- two-char operators ---
            if i+1 < n and expr[i:i+2] in ('<=', '>=', '<>', '!=', '**'):
                op = expr[i:i+2]
                tokens.append(('OP', '!=' if op in ('<>', '!=') else op))
                i += 2
                continue

            # --- single-char tokens ---
            if c in '+-*/^<>=':
                tokens.append(('OP', c))
                i += 1
            elif c == '(':
                tokens.append(('LPAREN', '('))
                i += 1
            elif c == ')':
                tokens.append(('RPAREN', ')'))
                i += 1
            elif c == ',':
                tokens.append(('COMMA', ','))
                i += 1
            elif c == ':':
                tokens.append(('COLON', ':'))
                i += 1
            elif c == '%':
                # percentage: divide preceding number by 100
                tokens.append(('OP', '%'))
                i += 1
            elif c == '&':
                # string concatenation operator
                tokens.append(('OP', '&'))
                i += 1
            else:
                i += 1          # skip unknown char silently

        return tokens


    # ------------------------------------------------------------------ #
    #  Recursive-descent parser                                            #
    # ------------------------------------------------------------------ #
    def _parse_expr(self, tokens, pos):
        """
        expr := term { ('+' | '-' | '&' | '<' | '>' | '<=' | '>=' | '!=' | '=') term }
        Returns (value, new_pos).
        """
        left, pos = self._parse_term(tokens, pos)
        while pos < len(tokens) and tokens[pos][0] == 'OP' and tokens[pos][1] in (
                '+', '-', '&', '<', '>', '<=', '>=', '!=', '='):
            op = tokens[pos][1]
            pos += 1
            right, pos = self._parse_term(tokens, pos)
            if op == '+':
                try:
                    left = float(left) + float(right)
                except (TypeError, ValueError):
                    left = str(left) + str(right)
            elif op == '-':
                left = float(left) - float(right)
            elif op == '&':
                left = str(left) + str(right)
            elif op == '<':
                left = float(left) < float(right)
            elif op == '>':
                left = float(left) > float(right)
            elif op == '<=':
                left = float(left) <= float(right)
            elif op == '>=':
                left = float(left) >= float(right)
            elif op in ('!=', '<>'):
                left = left != right
            elif op == '=':
                left = left == right
        return left, pos


    def _parse_term(self, tokens, pos):
        """
        term := factor { ('*' | '/' | '^' | '**' | '%') factor }
        """
        left, pos = self._parse_factor(tokens, pos)
        while pos < len(tokens) and tokens[pos][0] == 'OP' and tokens[pos][1] in ('*', '/', '^', '**', '%'):
            op = tokens[pos][1]
            pos += 1
            if op == '%':
                # unary-ish postfix percent
                left = float(left) / 100.0
            else:
                right, pos = self._parse_factor(tokens, pos)
                if op == '*':
                    left = float(left) * float(right)
                elif op == '/':
                    divisor = float(right)
                    if divisor == 0:
                        raise ZeroDivisionError("Division by zero")
                    left = float(left) / divisor
                elif op in ('^', '**'):
                    left = float(left) ** float(right)
        return left, pos


    def _parse_factor(self, tokens, pos):
        """
        factor := [unary] ( number | string | bool | cell_ref | func_call | '(' expr ')' )
        """
        if pos >= len(tokens):
            return 0, pos

        tok_type, tok_val = tokens[pos]

        # --- unary minus / plus ---
        if tok_type == 'OP' and tok_val in ('-', '+'):
            pos += 1
            val, pos = self._parse_factor(tokens, pos)
            return (-float(val) if tok_val == '-' else float(val)), pos

        # --- literals ---
        if tok_type == 'NUM':
            return tok_val, pos + 1

        if tok_type == 'STR':
            return tok_val, pos + 1

        if tok_type == 'BOOL':
            return tok_val, pos + 1

        # --- cell reference ---
        if tok_type == 'CELL':
            cell = self.parse_cell_reference(tok_val)
            if cell:
                r, c = cell
                item = self.table.item(r, c)
                if item and item.text():
                    raw = item.text()
                    try:
                        return float(raw), pos + 1
                    except ValueError:
                        return raw, pos + 1
            return 0, pos + 1

        # --- function call ---
        if tok_type == 'FUNC':
            func_name = tok_val
            pos += 1                    # consume FUNC token
            # consume '('
            if pos < len(tokens) and tokens[pos][0] == 'LPAREN':
                pos += 1
            # parse argument list
            args, pos = self._parse_args(tokens, pos)
            # consume ')'
            if pos < len(tokens) and tokens[pos][0] == 'RPAREN':
                pos += 1
            result = self._call_function(func_name, args)
            return result, pos

        # --- parenthesised sub-expression ---
        if tok_type == 'LPAREN':
            pos += 1
            val, pos = self._parse_expr(tokens, pos)
            if pos < len(tokens) and tokens[pos][0] == 'RPAREN':
                pos += 1
            return val, pos

        return 0, pos + 1               # safe fallback


    # ------------------------------------------------------------------ #
    #  Argument list parser                                                #
    # ------------------------------------------------------------------ #
    def _parse_args(self, tokens, pos):
        """
        Parse a comma-separated argument list *inside* parentheses.
        Handles ranges (A1:B3) by expanding them into a flat list of
        cell values.  Returns (list_of_values, new_pos).
        """
        args = []
        n = len(tokens)

        if pos >= n or tokens[pos][0] == 'RPAREN':
            return args, pos

        while True:
            # Check for range  CELL : CELL  before evaluating as expression
            if (pos + 2 < n
                    and tokens[pos][0] == 'CELL'
                    and tokens[pos+1][0] == 'COLON'
                    and tokens[pos+2][0] == 'CELL'):
                start_ref = tokens[pos][1]
                end_ref   = tokens[pos+2][1]
                range_str = f"{start_ref}:{end_ref}"
                cells = self.parse_range(range_str)
                for r, c in cells:
                    item = self.table.item(r, c)
                    if item and item.text():
                        try:
                            args.append(float(item.text()))
                        except ValueError:
                            args.append(item.text())
                pos += 3
            else:
                val, pos = self._parse_expr(tokens, pos)
                args.append(val)

            if pos >= n or tokens[pos][0] != 'COMMA':
                break
            pos += 1   # consume comma

        return args, pos


    # ------------------------------------------------------------------ #
    #  Unified function dispatcher                                         #
    # ------------------------------------------------------------------ #
    def _call_function(self, func_name, args):
        """
        Dispatch a parsed function call.  *args* is a flat list of already-
        evaluated values (numbers, strings, booleans).
        """
        def nums(lst):
            """Extract numeric values from a mixed list."""
            result = []
            for v in lst:
                try:
                    result.append(float(v))
                except (TypeError, ValueError):
                    pass
            return result

        n_args = len(args)
        F = func_name.upper()

        # ---- Math & Trig ----
        if F == 'SUM':
            return sum(nums(args))
        if F == 'PRODUCT':
            p = 1.0
            for v in nums(args): p *= v
            return p
        if F == 'AVERAGE' or F == 'AVG':
            nv = nums(args)
            return statistics.mean(nv) if nv else 0
        if F == 'MEDIAN':
            nv = nums(args)
            return statistics.median(nv) if nv else 0
        if F in ('MODE', 'MODE.SNGL'):
            nv = nums(args)
            return statistics.mode(nv) if nv else 0
        if F == 'COUNT':
            return len(nums(args))
        if F == 'COUNTA':
            return sum(1 for v in args if v != '' and v is not None)
        if F == 'COUNTBLANK':
            return sum(1 for v in args if v == '' or v is None)
        if F in ('MAX', 'MAXA'):
            nv = nums(args); return max(nv) if nv else 0
        if F in ('MIN', 'MINA'):
            nv = nums(args); return min(nv) if nv else 0
        if F == 'ABS':
            return abs(float(args[0]))
        if F == 'SQRT':
            return math.sqrt(float(args[0]))
        if F in ('POW', 'POWER'):
            return math.pow(float(args[0]), float(args[1]))
        if F == 'EXP':
            return math.exp(float(args[0]))
        if F in ('LN', 'LOG.NATURAL'):
            return math.log(float(args[0]))
        if F == 'LOG10':
            return math.log10(float(args[0]))
        if F == 'LOG':
            base = float(args[1]) if n_args > 1 else 10.0
            return math.log(float(args[0]), base)
        if F == 'SIN':
            return math.sin(float(args[0]))
        if F == 'COS':
            return math.cos(float(args[0]))
        if F == 'TAN':
            return math.tan(float(args[0]))
        if F == 'ASIN':
            return math.asin(float(args[0]))
        if F == 'ACOS':
            return math.acos(float(args[0]))
        if F == 'ATAN':
            return math.atan(float(args[0]))
        if F == 'ATAN2':
            return math.atan2(float(args[0]), float(args[1]))
        if F == 'DEGREES':
            return math.degrees(float(args[0]))
        if F == 'RADIANS':
            return math.radians(float(args[0]))
        if F == 'PI':
            return math.pi
        if F == 'ROUND':
            d = int(args[1]) if n_args > 1 else 0
            return round(float(args[0]), d)
        if F == 'ROUNDUP':
            d = int(args[1]) if n_args > 1 else 0
            factor = 10 ** d
            return math.ceil(float(args[0]) * factor) / factor
        if F == 'ROUNDDOWN':
            d = int(args[1]) if n_args > 1 else 0
            factor = 10 ** d
            return math.floor(float(args[0]) * factor) / factor
        if F in ('TRUNC', 'INT'):
            return math.trunc(float(args[0]))
        if F == 'CEILING':
            sig = float(args[1]) if n_args > 1 else 1.0
            return math.ceil(float(args[0]) / sig) * sig
        if F == 'FLOOR':
            sig = float(args[1]) if n_args > 1 else 1.0
            return math.floor(float(args[0]) / sig) * sig
        if F == 'MOD':
            return float(args[0]) % float(args[1])
        if F == 'QUOTIENT':
            return int(float(args[0]) / float(args[1]))
        if F == 'SIGN':
            v = float(args[0]); return 1 if v > 0 else (-1 if v < 0 else 0)
        if F == 'FACT':
            return math.factorial(int(float(args[0])))
        if F == 'RAND':
            import random; return random.random()
        if F == 'RANDBETWEEN':
            import random; return random.randint(int(float(args[0])), int(float(args[1])))
        if F == 'GCD':
            import math as _m
            result = int(float(args[0]))
            for v in args[1:]: result = _m.gcd(result, int(float(v)))
            return result
        if F == 'LCM':
            import math as _m
            result = int(float(args[0]))
            for v in args[1:]: result = result * int(float(v)) // _m.gcd(result, int(float(v)))
            return result
        if F == 'COMBIN':
            import math as _m
            return _m.comb(int(float(args[0])), int(float(args[1])))
        if F == 'PERMUT':
            import math as _m
            return _m.perm(int(float(args[0])), int(float(args[1])))

        # ---- Statistical ----
        if F in ('STDEV', 'STDEV.S'):
            nv = nums(args); return statistics.stdev(nv) if len(nv) > 1 else 0
        if F in ('STDEVP', 'STDEV.P'):
            nv = nums(args); return statistics.pstdev(nv) if nv else 0
        if F in ('VAR', 'VAR.S'):
            nv = nums(args); return statistics.variance(nv) if len(nv) > 1 else 0
        if F in ('VARP', 'VAR.P'):
            nv = nums(args); return statistics.pvariance(nv) if nv else 0
        if F in ('LARGE', 'SMALL'):
            nv = sorted(nums(args[:-1]), reverse=(F == 'LARGE'))
            k = int(float(args[-1]))
            return nv[k-1] if 1 <= k <= len(nv) else '#NUM!'
        if F in ('SUMPRODUCT',):
            # requires an even number of args split into two equal halves
            half = n_args // 2
            a = nums(args[:half]); b = nums(args[half:])
            return sum(x*y for x, y in zip(a, b))

        # ---- Logical ----
        if F == 'IF':
            cond = args[0] if n_args > 0 else False
            true_val  = args[1] if n_args > 1 else True
            false_val = args[2] if n_args > 2 else False
            # Treat numeric 0 as falsy, everything else truthy
            is_true = bool(cond) if not isinstance(cond, (int, float)) else (cond != 0)
            return true_val if is_true else false_val
        if F == 'IFERROR':
            return args[0] if n_args > 0 and not isinstance(args[0], str) or (
                n_args > 0 and isinstance(args[0], str) and not args[0].startswith('#')
            ) else (args[1] if n_args > 1 else '')
        if F == 'AND':
            return all(bool(v) for v in args)
        if F == 'OR':
            return any(bool(v) for v in args)
        if F == 'NOT':
            return not bool(args[0])
        if F == 'XOR':
            return sum(bool(v) for v in args) % 2 == 1
        if F == 'TRUE':
            return True
        if F == 'FALSE':
            return False

        # ---- Text ----
        if F in ('CONCATENATE', 'CONCAT'):
            return ''.join(str(a) for a in args)
        if F == 'TEXTJOIN':
            delim = str(args[0]) if n_args > 0 else ''
            ignore_empty = bool(args[1]) if n_args > 1 else True
            parts = [str(a) for a in args[2:]]
            if ignore_empty:
                parts = [p for p in parts if p]
            return delim.join(parts)
        if F == 'LEN':
            return len(str(args[0]))
        if F == 'LEFT':
            k = int(float(args[1])) if n_args > 1 else 1
            return str(args[0])[:k]
        if F == 'RIGHT':
            k = int(float(args[1])) if n_args > 1 else 1
            return str(args[0])[-k:] if k else ''
        if F == 'MID':
            s = str(args[0]); start = int(float(args[1])) - 1; length = int(float(args[2]))
            return s[start:start+length]
        if F == 'UPPER':
            return str(args[0]).upper()
        if F == 'LOWER':
            return str(args[0]).lower()
        if F == 'PROPER':
            return str(args[0]).title()
        if F == 'TRIM':
            return ' '.join(str(args[0]).split())
        if F == 'SUBSTITUTE':
            s = str(args[0]); old = str(args[1]); new = str(args[2])
            if n_args > 3:
                # replace nth occurrence only
                nth = int(float(args[3])); idx = -1
                for _ in range(nth):
                    idx = s.find(old, idx+1)
                    if idx == -1: return s
                return s[:idx] + new + s[idx+len(old):]
            return s.replace(old, new)
        if F == 'REPLACE':
            s = str(args[0]); start = int(float(args[1])) - 1
            length = int(float(args[2])); new = str(args[3])
            return s[:start] + new + s[start+length:]
        if F in ('FIND', 'SEARCH'):
            find = str(args[0]); within = str(args[1])
            start = int(float(args[2])) - 1 if n_args > 2 else 0
            if F == 'SEARCH':
                idx = within.lower().find(find.lower(), start)
            else:
                idx = within.find(find, start)
            if idx == -1: raise ValueError('#VALUE!')
            return idx + 1
        if F == 'REPT':
            return str(args[0]) * int(float(args[1]))
        if F == 'EXACT':
            return str(args[0]) == str(args[1])
        if F == 'VALUE':
            try: return float(str(args[0]).replace(',', ''))
            except: raise ValueError('#VALUE!')
        if F == 'CHAR':
            return chr(int(float(args[0])))
        if F == 'CODE':
            s = str(args[0]); return ord(s[0]) if s else 0
        if F == 'T':
            return str(args[0]) if isinstance(args[0], str) else ''
        if F == 'N':
            try: return float(args[0])
            except: return 0

        # ---- Date & Time ----
        if F == 'NOW':
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if F == 'TODAY':
            return datetime.now().strftime("%Y-%m-%d")
        if F == 'YEAR':
            try:
                return datetime.strptime(str(args[0])[:10], "%Y-%m-%d").year
            except: return '#VALUE!'
        if F == 'MONTH':
            try:
                return datetime.strptime(str(args[0])[:10], "%Y-%m-%d").month
            except: return '#VALUE!'
        if F == 'DAY':
            try:
                return datetime.strptime(str(args[0])[:10], "%Y-%m-%d").day
            except: return '#VALUE!'

        # ---- Information ----
        if F == 'ISNUMBER':
            try: float(args[0]); return True
            except: return False
        if F == 'ISTEXT':
            return isinstance(args[0], str) and not (lambda v: (float(v), True)[1]
                if (lambda:False)() else False)()
        if F == 'ISBLANK':
            return args[0] == '' or args[0] is None
        if F == 'ISERROR':
            return isinstance(args[0], str) and args[0].startswith('#')
        if F == 'ISEVEN':
            return int(float(args[0])) % 2 == 0
        if F == 'ISODD':
            return int(float(args[0])) % 2 != 0
        if F == 'NA':
            return '#N/A'

        # ---- Lookup ----
        if F == 'ROW':
            if n_args > 0 and isinstance(args[0], str):
                cell = self.parse_cell_reference(str(args[0]))
                if cell: return cell[0] + 1
            return self.table.currentRow() + 1
        if F == 'COLUMN':
            if n_args > 0 and isinstance(args[0], str):
                cell = self.parse_cell_reference(str(args[0]))
                if cell: return cell[1] + 1
            return self.table.currentColumn() + 1

        # ---- COUNTIF / SUMIF (simple) ----
        if F == 'COUNTIF':
            # args come pre-expanded as individual cell values + criteria at end
            criteria = str(args[-1]) if args else ''
            values = args[:-1]
            count = 0
            for v in values:
                try:
                    if criteria.startswith('>='):
                        if float(v) >= float(criteria[2:]): count += 1
                    elif criteria.startswith('<='):
                        if float(v) <= float(criteria[2:]): count += 1
                    elif criteria.startswith('>'):
                        if float(v) > float(criteria[1:]): count += 1
                    elif criteria.startswith('<'):
                        if float(v) < float(criteria[1:]): count += 1
                    elif criteria.startswith('<>') or criteria.startswith('!='):
                        if str(v) != criteria[2:]: count += 1
                    else:
                        if str(v) == criteria: count += 1
                except (TypeError, ValueError):
                    if str(v) == criteria: count += 1
            return count

        raise ValueError(f"Unknown function: {func_name}")



    def parse_cell_reference(self, ref):
        ref = ref.replace("$", "")
        match = re.match(r'^([A-Z]+)([0-9]+)$', ref)
        if match:
            col_str, row_str = match.groups()
            col = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(col_str))) - 1
            row = int(row_str) - 1
            if 0 <= row < self.rows and 0 <= col < self.cols:
                return (row, col)
        return None

    def parse_range(self, range_str):
        parts = range_str.split(":")
        if len(parts) != 2:
            return []

        start_cell = self.parse_cell_reference(parts[0].strip())
        end_cell = self.parse_cell_reference(parts[1].strip())

        if not start_cell or not end_cell:
            return []

        r1, c1 = start_cell
        r2, c2 = end_cell

        cells = []
        for r in range(min(r1, r2), max(r1, r2) + 1):
            for c in range(min(c1, c2), max(c1, c2) + 1):
                cells.append((r, c))
        return cells

    # def evaluate_function(self, expr):
        # """Evaluate range functions like SUM, AVERAGE, etc."""
        # expr_upper = expr.upper()

        # # Extract function name and arguments
        # match = re.match(r'(\w+)\s*\((.*)\)', expr, re.IGNORECASE)
        # if not match:
            # raise ValueError("Invalid function syntax")

        # func_name = match.group(1).upper()
        # args_str = match.group(2).strip()

        # # Parse range
        # cells = self.parse_range(args_str)
        # if not cells:
            # raise ValueError("Invalid range")

        # # Get values
        # values = []
        # for r, c in cells:
            # item = self.table.item(r, c)
            # if item and item.text():
                # try:
                    # values.append(float(item.text()))
                # except:
                    # pass

        # if not values and func_name != "COUNT":
            # return 0

        # # Apply function
        # if func_name == "SUM":
            # return sum(values)
        # elif func_name == "AVERAGE":
            # return statistics.mean(values) if values else 0
        # elif func_name == "COUNT":
            # return len(values)
        # elif func_name == "MAX":
            # return max(values) if values else 0
        # elif func_name == "MIN":
            # return min(values) if values else 0

        # raise ValueError("Unknown function")

    # def evaluate_if(self, expr):
        # match = re.match(r'IF\((.*),(.*),(.*)\)', expr, re.IGNORECASE)
        # if not match:
            # raise ValueError("Invalid IF syntax")
        # condition = match.group(1).strip()
        # true_val = match.group(2).strip()
        # false_val = match.group(3).strip()

        # cond_result = self.evaluate(condition)
        # if cond_result:
            # return self.evaluate(true_val)
        # else:
            # return self.evaluate(false_val)

    # def evaluate_string_function(self, expr):
        # match = re.match(r'(\w+)\((.*)\)', expr, re.IGNORECASE)
        # if not match:
            # raise ValueError("Invalid function syntax")

        # func_name = match.group(1).upper()
        # args_str = match.group(2)

        # if func_name == "LEN":
            # text = args_str.strip('"\'')
            # return len(text)
        # elif func_name in ["UPPER", "LOWER"]:
            # text = args_str.strip('"\'')
            # return text.upper() if func_name == "UPPER" else text.lower()

        # raise ValueError("Unsupported string function")

    # def evaluate_datetime_function(self, expr):
        # match = re.match(r'(\w+)\((.*)\)', expr, re.IGNORECASE)
        # if not match:
            # match = re.match(r'(\w+)\(\)', expr, re.IGNORECASE)
            # if match:
                # func_name = match.group(1).upper()
                # now = datetime.now()
                # if func_name == "NOW":
                    # return now.strftime("%Y-%m-%d %H:%M:%S")
                # elif func_name == "TODAY":
                    # return now.strftime("%Y-%m-%d")
        # raise ValueError("Invalid datetime function")

    # def evaluate_logical_function(self, expr):
        # match = re.match(r'(\w+)\((.*)\)', expr, re.IGNORECASE)
        # if not match:
            # raise ValueError("Invalid function syntax")

        # func_name = match.group(1).upper()
        # args_str = match.group(2)

        # if func_name == "AND":
            # args = [self.evaluate(arg.strip()) for arg in args_str.split(",")]
            # return all(args)
        # elif func_name == "OR":
            # args = [self.evaluate(arg.strip()) for arg in args_str.split(",")]
            # return any(args)
        # elif func_name == "NOT":
            # return not self.evaluate(args_str.strip())

        # raise ValueError("Unknown logical function")

    # def evaluate_math_function(self, expr):
        # match = re.match(r'(\w+)\((.*)\)', expr, re.IGNORECASE)
        # if not match:
            # raise ValueError("Invalid function syntax")

        # func_name = match.group(1).upper()
        # args_str = match.group(2)

        # if func_name == "SQRT":
            # return math.sqrt(self.evaluate(args_str))
        # elif func_name == "ABS":
            # return abs(self.evaluate(args_str))
        # elif func_name == "ROUND":
            # args = [self.evaluate(arg.strip()) for arg in args_str.split(",")]
            # return round(args[0], int(args[1]) if len(args) > 1 else 0)
        # elif func_name == "SIN":
            # return math.sin(self.evaluate(args_str))
        # elif func_name == "COS":
            # return math.cos(self.evaluate(args_str))
        # elif func_name == "TAN":
            # return math.tan(self.evaluate(args_str))
        # elif func_name == "LOG":
            # return math.log(self.evaluate(args_str))
        # elif func_name == "EXP":
            # return math.exp(self.evaluate(args_str))
        # elif func_name == "POW":
            # args = [self.evaluate(arg.strip()) for arg in args_str.split(",")]
            # return math.pow(args[0], args[1])

        # raise ValueError("Unknown math function")

    # -----------------------------
    # Formula drag-fill
    # -----------------------------
    def fill_formula_drag(self, start_cell, end_cell):
        r0, c0 = start_cell
        r1, c1 = end_cell

        source_formula = self.formulas.get(start_cell)
        if not source_formula:
            source_text = self.table.item(r0, c0).text()
            for r in range(min(r0, r1), max(r0, r1) + 1):
                for c in range(min(c0, c1), max(c0, c1) + 1):
                    if (r, c) != start_cell:
                        self.table.item(r, c).setText(source_text)
            return

        for r in range(min(r0, r1), max(r0, r1) + 1):
            for c in range(min(c0, c1), max(c0, c1) + 1):
                if (r, c) != start_cell:
                    new_formula = self.adjust_formula(source_formula, r0, c0, r, c)
                    self.formulas[(r, c)] = new_formula
                    try:
                        result = self.evaluate(new_formula[1:])
                        self.table.item(r, c).setText(str(result))
                    except:
                        self.table.item(r, c).setText("#ERROR")

    def adjust_formula(self, formula, src_r, src_c, dst_r, dst_c):
        def adjust_ref(match):
            ref = match.group(0)
            if "$" in ref:
                return ref
            cell = self.parse_cell_reference(ref)
            if cell:
                r, c = cell
                new_r = r + (dst_r - src_r)
                new_c = c + (dst_c - src_c)
                if 0 <= new_r < self.rows and 0 <= new_c < self.cols:
                    return f"{chr(ord('A') + new_c)}{new_r + 1}"
            return ref
        return re.sub(r'[$]?[A-Z]+[$]?[0-9]+', adjust_ref, formula)

    # -----------------------------
    # Export methods
    # -----------------------------
    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "", "CSV Files (*.csv)")
        if filename:
            with open(filename, 'w') as f:
                for r in range(self.rows):
                    row_data = []
                    for c in range(self.cols):
                        item = self.table.item(r, c)
                        row_data.append(item.text() if item else "")
                    f.write(",".join(row_data) + "\n")
            self.main_window.update_status_bar(f"Exported to {filename}")

    # def export_latex(self):
        # max_row = 0
        # max_col = 0
        # for r in range(self.rows):
            # for c in range(self.cols):
                # item = self.table.item(r, c)
                # if item and item.text():
                    # max_row = max(max_row, r)
                    # max_col = max(max_col, c)

        # latex = "\\begin{table}[h]\n"
        # latex += "\\centering\n"
        # latex += "\\begin{tabular}{|" + "c|" * (max_col + 1) + "}\n"
        # latex += "\\hline\n"

        # for r in range(max_row + 1):
            # row_data = []
            # for c in range(max_col + 1):
                # item = self.table.item(r, c)
                # text = item.text() if item else ""
                # text = text.replace("\\", "\\textbackslash ")
                # text = text.replace("&", "\\&")
                # text = text.replace("%", "\\%")
                # text = text.replace("$", "\\$")
                # text = text.replace("#", "\\#")
                # text = text.replace("_", "\\_")
                # text = text.replace("{", "\\{")
                # text = text.replace("}", "\\}")
                # text = text.replace("~", "\\textasciitilde ")
                # text = text.replace("^", "\\textasciicircum ")
                # row_data.append(text)
            # latex += " & ".join(row_data) + " \\\\\n"
            # latex += "\\hline\n"

        # latex += "\\end{tabular}\n"
        # latex += "\\caption{Spreadsheet Data}\n"
        # latex += "\\label{tab:spreadsheet}\n"
        # latex += "\\end{table}"

        # dialog = LatexExportDialog(latex, self)
        # dialog.exec_()

    def get_formula_dependencies(self, formula):
        dependencies = []
        refs = re.findall(r'[$]?[A-Z]+[$]?[0-9]+', formula)
        for ref in refs:
            cell_ref = self.parse_cell_reference(ref)
            if cell_ref:
                dependencies.append(cell_ref)
        return dependencies

    def insert_function(self):
        dlg = FunctionDialog()
        if dlg.exec_():
            fn = dlg.selected_function()
            if fn:
                self.formula_bar.setText(f"={fn}()")
                self.formula_bar.setCursorPosition(len(fn) + 2)
                self.formula_bar.setFocus()
                self.table.formula_mode = True

    def on_item_changed(self, item):
        if not self.updating:
            # Remove formula for this cell if user typed a direct value
            self.formulas.pop((item.row(), item.column()), None)
            # Update all dependent cells (cells that reference this one)
            if (item.row(), item.column()) in self.cell_dependencies:
                self.updating = True
                for dep_r, dep_c in self.cell_dependencies[(item.row(), item.column())]:
                    if (dep_r, dep_c) in self.formulas:
                        try:
                            formula = self.formulas[(dep_r, dep_c)]
                            result = self.evaluate(formula[1:])
                            self.table.item(dep_r, dep_c).setText(str(result))
                        except:
                            self.table.item(dep_r, dep_c).setText("#ERROR")
                self.updating = False

    # -----------------------------
    # Formatting methods
    # -----------------------------
    def set_border_combobox(self, text):
        mapping = {
            "None": set(),
            "Top": {"top"},
            "Bottom": {"bottom"},
            "Left": {"left"},
            "Right": {"right"},
            "Top & Bottom": {"top", "bottom"},
            "Left & Right": {"left", "right"},
            "All (Box)": {"top", "bottom", "left", "right"}
        }
        sel = mapping.get(text, set())
        for i in self.table.selectedIndexes():
            self.table.item(i.row(), i.column()).setData(Qt.UserRole, sel)
        self.table.viewport().update()

    def _apply_font(self, modify_fn):
        self.updating = True
        for i in self.table.selectedIndexes():
            it = self.table.item(i.row(), i.column())
            f = it.font()
            modify_fn(f)
            it.setFont(f)
        self.updating = False

    def set_bold(self):
        self._apply_font(lambda f: f.setBold(True))

    def set_italic(self):
        self._apply_font(lambda f: f.setItalic(True))

    def set_normal(self):
        self._apply_font(lambda f: f.setBold(False) or f.setItalic(False))

    def _apply_alignment(self, align):
        self.updating = True
        for i in self.table.selectedIndexes():
            it = self.table.item(i.row(), i.column())
            it.setTextAlignment(align)
        self.updating = False

    def set_align_left(self):
        self._apply_alignment(Qt.AlignLeft | Qt.AlignVCenter)

    def set_align_center(self):
        self._apply_alignment(Qt.AlignCenter)

    def set_align_right(self):
        self._apply_alignment(Qt.AlignRight | Qt.AlignVCenter)

    def set_fill_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.updating = True
            for i in self.table.selectedIndexes():
                it = self.table.item(i.row(), i.column())
                it.setBackground(color)
            self.updating = False

    # -----------------------------
    # Clipboard methods
    # -----------------------------
    def copy(self):
        sel = self.table.selectedIndexes()
        if not sel:
            return
        rows = sorted(set(i.row() for i in sel))
        cols = sorted(set(i.column() for i in sel))
        # Store source location for paste linked
        self.clipboard_source = (rows[0], cols[0])
        self.clipboard = []
        for r in rows:
            row_data = []
            for c in cols:
                it = self.table.item(r, c)
                row_data.append((it.text(), self.formulas.get((r, c))))
            self.clipboard.append(row_data)

    def cut(self):
        self.copy()
        rows = sorted(set(i.row() for i in self.table.selectedIndexes()))
        cols = sorted(set(i.column() for i in self.table.selectedIndexes()))
        for r_idx, row_data in enumerate(self.clipboard):
            for c_idx, (_, f) in enumerate(row_data):
                r = rows[0] + r_idx
                c = cols[0] + c_idx
                self.table.item(r, c).setText("")
                self.formulas.pop((r, c), None)

    def paste(self):
        if not self.clipboard:
            return
        start_row = self.table.currentRow()
        start_col = self.table.currentColumn()
        for r_idx, row_data in enumerate(self.clipboard):
            for c_idx, (val, _) in enumerate(row_data):
                r = start_row + r_idx
                c = start_col + c_idx
                if r < self.rows and c < self.cols:
                    self.table.item(r, c).setText(val)

    def delete_cells(self):
        sel = self.table.selectedIndexes()
        for i in sel:
            r, c = i.row(), i.column()
            self.table.item(r, c).setText("")
            self.formulas.pop((r, c), None)

    def paste_linked(self):
        """Paste with formulas that link to the source cells (live links)"""
        if not self.clipboard or not self.clipboard_source:
            return

        start_row = self.table.currentRow()
        start_col = self.table.currentColumn()
        src_row, src_col = self.clipboard_source

        self.updating = True
        for r_idx, row_data in enumerate(self.clipboard):
            for c_idx, (_, formula) in enumerate(row_data):
                dest_r = start_row + r_idx
                dest_c = start_col + c_idx
                if dest_r < self.rows and dest_c < self.cols:
                    # Create a reference formula to the source cell
                    source_r = src_row + r_idx
                    source_c = src_col + c_idx
                    source_ref = f"{chr(ord('A') + source_c)}{source_r + 1}"

                    # Always create a simple reference formula (live link)
                    link_formula = f"={source_ref}"
                    self.formulas[(dest_r, dest_c)] = link_formula

                    # Add to dependencies so changes in source update destination
                    if (source_r, source_c) not in self.cell_dependencies:
                        self.cell_dependencies[(source_r, source_c)] = []
                    if (dest_r, dest_c) not in self.cell_dependencies[(source_r, source_c)]:
                        self.cell_dependencies[(source_r, source_c)].append((dest_r, dest_c))

                    # Evaluate the formula to show current value
                    try:
                        result = self.evaluate(link_formula[1:])
                        self.table.item(dest_r, dest_c).setText(str(result))
                    except:
                        self.table.item(dest_r, dest_c).setText("#ERROR")

        self.updating = False
        self.main_window.update_status_bar("Pasted with live links - changes in source cells will update destination")

    # -----------------------------
    # Cell/Row/Column operations
    # -----------------------------
    def perform_operation(self, operation):
        """Handle cell/row/column operations from combo box"""
        if operation == "Select Operation...":
            return

        if operation == "Insert Row":
            self.insert_row()
        elif operation == "Insert Column":
            self.insert_column()
        elif operation == "Remove Row":
            self.remove_row()
        elif operation == "Remove Column":
            self.remove_column()
        elif operation == "Insert Cell (Shift Right)":
            self.insert_cell_shift_right()
        elif operation == "Insert Cell (Shift Down)":
            self.insert_cell_shift_down()
        elif operation == "Remove Cell (Shift Left)":
            self.remove_cell_shift_left()
        elif operation == "Remove Cell (Shift Up)":
            self.remove_cell_shift_up()

        # Reset combo box
        self.operations_combo.setCurrentIndex(0)

    def perform_sort(self, sort_type):
        """Handle sort operations"""
        if sort_type == "Select Sort...":
            return

        sel = self.table.selectedIndexes()

        # Check if entire column is selected (by clicking column header)
        if not sel:
            # Try to get the current column
            current_col = self.table.currentColumn()
            if current_col >= 0:
                # Select entire column
                sel = [self.table.model().index(r, current_col) for r in range(self.rows)]
            else:
                self.main_window.update_status_bar("Please select cells, a column, or a row to sort")
                self.sort_combo.setCurrentIndex(0)
                return

        # Get selected range
        rows = sorted(set(i.row() for i in sel))
        cols = sorted(set(i.column() for i in sel))

        # Determine if this is a column sort or row sort
        is_column_sort = len(cols) == 1 or len(cols) < len(rows)
        is_row_sort = len(rows) == 1 or len(rows) < len(cols)

        ascending = "Ascending" in sort_type

        if is_column_sort and not is_row_sort:
            # Sort by column (sort rows based on first column's values)
            col_to_sort = cols[0]

            # Collect row data
            data = []
            for r in rows:
                row_data = []
                for c in cols:
                    item = self.table.item(r, c)
                    row_data.append(item.text() if item else "")
                data.append((r, row_data))

            # Sort data based on the first column
            try:
                # Try numeric sort
                data.sort(key=lambda x: float(x[1][0]) if x[1][0] else float('inf'), reverse=not ascending)
            except:
                # Fallback to text sort
                data.sort(key=lambda x: str(x[1][0]).lower(), reverse=not ascending)

            # Write sorted data back
            self.updating = True
            for idx, (orig_row, row_data) in enumerate(data):
                target_row = rows[idx]
                for c_idx, c in enumerate(cols):
                    self.table.item(target_row, c).setText(row_data[c_idx])
            self.updating = False

            self.main_window.update_status_bar(f"Sorted column {'ascending' if ascending else 'descending'}")

        elif is_row_sort:
            # Sort by row (sort columns based on first row's values)
            row_to_sort = rows[0]

            # Collect column data
            data = []
            for c in cols:
                col_data = []
                for r in rows:
                    item = self.table.item(r, c)
                    col_data.append(item.text() if item else "")
                data.append((c, col_data))

            # Sort data based on the first row
            try:
                # Try numeric sort
                data.sort(key=lambda x: float(x[1][0]) if x[1][0] else float('inf'), reverse=not ascending)
            except:
                # Fallback to text sort
                data.sort(key=lambda x: str(x[1][0]).lower(), reverse=not ascending)

            # Write sorted data back
            self.updating = True
            for idx, (orig_col, col_data) in enumerate(data):
                target_col = cols[idx]
                for r_idx, r in enumerate(rows):
                    self.table.item(r, target_col).setText(col_data[r_idx])
            self.updating = False

            self.main_window.update_status_bar(f"Sorted row {'ascending' if ascending else 'descending'}")

        self.sort_combo.setCurrentIndex(0)

    def insert_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.insertRow(current_row)
            for c in range(self.cols):
                self.table.setItem(current_row, c, QTableWidgetItem(""))
            self.rows += 1
            self.main_window.update_status_bar(f"Inserted row at position {current_row + 1}")

    def insert_column(self):
        current_col = self.table.currentColumn()
        if current_col >= 0:
            self.table.insertColumn(current_col)
            for r in range(self.rows):
                self.table.setItem(r, current_col, QTableWidgetItem(""))
            self.cols += 1
            headers = [chr(ord('A') + i) if i < 26 else f"A{chr(ord('A') + i - 26)}" for i in range(self.cols)]
            self.table.setHorizontalHeaderLabels(headers)
            self.main_window.update_status_bar(f"Inserted column at position {current_col + 1}")

    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            self.rows -= 1
            self.main_window.update_status_bar(f"Removed row {current_row + 1}")

    def remove_column(self):
        current_col = self.table.currentColumn()
        if current_col >= 0:
            self.table.removeColumn(current_col)
            self.cols -= 1
            headers = [chr(ord('A') + i) if i < 26 else f"A{chr(ord('A') + i - 26)}" for i in range(self.cols)]
            self.table.setHorizontalHeaderLabels(headers)
            self.main_window.update_status_bar(f"Removed column {current_col + 1}")

    def insert_cell_shift_right(self):
        r = self.table.currentRow()
        c = self.table.currentColumn()
        if r >= 0 and c >= 0:
            # Shift cells right in the row
            for col in range(self.cols - 1, c, -1):
                if col > c:
                    source_item = self.table.item(r, col - 1)
                    text = source_item.text() if source_item else ""
                    self.table.item(r, col).setText(text)
            self.table.item(r, c).setText("")
            self.main_window.update_status_bar("Inserted cell (shifted right)")

    def insert_cell_shift_down(self):
        r = self.table.currentRow()
        c = self.table.currentColumn()
        if r >= 0 and c >= 0:
            # Shift cells down in the column
            for row in range(self.rows - 1, r, -1):
                if row > r:
                    source_item = self.table.item(row - 1, c)
                    text = source_item.text() if source_item else ""
                    self.table.item(row, c).setText(text)
            self.table.item(r, c).setText("")
            self.main_window.update_status_bar("Inserted cell (shifted down)")

    def remove_cell_shift_left(self):
        r = self.table.currentRow()
        c = self.table.currentColumn()
        if r >= 0 and c >= 0:
            # Shift cells left in the row
            for col in range(c, self.cols - 1):
                source_item = self.table.item(r, col + 1)
                text = source_item.text() if source_item else ""
                self.table.item(r, col).setText(text)
            self.table.item(r, self.cols - 1).setText("")
            self.main_window.update_status_bar("Removed cell (shifted left)")

    def remove_cell_shift_up(self):
        r = self.table.currentRow()
        c = self.table.currentColumn()
        if r >= 0 and c >= 0:
            # Shift cells up in the column
            for row in range(r, self.rows - 1):
                source_item = self.table.item(row + 1, c)
                text = source_item.text() if source_item else ""
                self.table.item(row, c).setText(text)
            self.table.item(self.rows - 1, c).setText("")
            self.main_window.update_status_bar("Removed cell (shifted up)")




# -----------------------------
# Standalone Main Window (for running spreadsheet.py directly)
# -----------------------------
class SpreadsheetMainWindow(QMainWindow):
    """Main window for standalone spreadsheet application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spreadsheet Application")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create spreadsheet widget as central widget
        self.spreadsheet = SpreadsheetWidget(main_window=None)
        #self.setCentralWidget(self.spreadsheet)
        
        self.main_window.update_status_bar("Ready")




# -----------------------------
# Integration function to add spreadsheet as a tab
# -----------------------------
def add_spreadsheet_tab_to_pdf_viewer(main_window):
    """Add the spreadsheet tab to the PDF viewer"""
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
                "Spreadsheet tab is only available in tabbed mode. Switch to tabbed mode first.")
            return

        # Initialize pdf_tabs if needed
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

        # Remove unwanted tabs
        tabs_to_remove = ["Welcome", "No Pdfs", "No PDFs"]
        for i in reversed(range(tab_widget.count())):
            tab_text = tab_widget.tabText(i)
            if tab_text in tabs_to_remove:
                tab_widget.removeTab(i)

        # Check if Spreadsheet tab already exists
        possible_labels = {
            tr["spreadsheet"] for tr in translations.values()
        }                        
            
        existing_index = -1
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                existing_index = i
                break

        if existing_index >= 0:
            tab_widget.setCurrentIndex(existing_index)
            #print(f"✅ Switched to existing Spreadsheet tab")
            return

        # Create new spreadsheet tab
        spreadsheet_tab = SpreadsheetWidget(main_window)

        # Store reference
        if not hasattr(main_window, '_spreadsheet_tabs'):
            main_window._spreadsheet_tabs = []
        main_window._spreadsheet_tabs.append(spreadsheet_tab)

        # Add to tab widget
        tab_name = tr.get("spreadsheet", "Spreadsheet")
        tab_index = tab_widget.addTab(spreadsheet_tab, tab_name)   
        tab_widget.tabBar().setTabData(tab_index, "spreadsheet")          

        # ✅ Set SVG icon properly
        icon = QIcon("icons/spreadsheet.svg")
        tab_widget.setTabIcon(tab_index, icon)        
        
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)

        # Ensure visibility
        tab_widget.show()
        tab_widget.setVisible(True)
        spreadsheet_tab.show()
        layout_manager.pdf_container.update()

        #print(f"✅ Spreadsheet tab added at index {tab_index}")

    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add spreadsheet tab:\n{str(e)}")
        import traceback
        traceback.print_exc()