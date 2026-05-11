from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QPushButton, QGridLayout, QApplication, QTextEdit
)
import sys
import math

# class CalculatorTab(QWidget):
    # def __init__(self, editor: QTextEdit):
        # super().__init__()
        # layout = QVBoxLayout(self)

        # # Calculator
        # self.calculator = CalculatorWidget(insert_callback=lambda res: self.insert_into_editor(editor, res))
        # layout.addWidget(self.calculator)

        # # Here you can also add the actual PDF viewer widget below the calculator
        # # e.g. self.pdf_viewer = SomePDFViewer()
        # # layout.addWidget(self.pdf_viewer)

    # def insert_into_editor(self, editor: QTextEdit, result: str):
        # cursor = editor.textCursor()
        # cursor.insertText(result)
        # editor.setTextCursor(cursor)


class CalculatorWidget(QWidget):
    def __init__(self, insert_callback=None):
        super().__init__()
        self.insert_callback = insert_callback  # function to insert result into editor

        self.layout = QVBoxLayout(self)

        # Display
        self.display = QLineEdit()
        self.display.setReadOnly(False)
        self.layout.addWidget(self.display)

        # Calculator buttons
        buttons = [
            ['7', '8', '9', '/', 'sqrt'],
            ['4', '5', '6', '*', '^'],
            ['1', '2', '3', '-', 'sin'],
            ['0', '.', '=', '+', 'cos'],
        ]

        grid = QGridLayout()
        for r, row in enumerate(buttons):
            for c, btn_text in enumerate(row):
                button = QPushButton(btn_text)
                button.clicked.connect(lambda _, t=btn_text: self.on_button_click(t))
                grid.addWidget(button, r, c)
        self.layout.addLayout(grid)

        # Insert button
        self.insert_btn = QPushButton("Insert Result into Editor")
        self.insert_btn.clicked.connect(self.insert_result)
        self.layout.addWidget(self.insert_btn)

    def on_button_click(self, text):
        try:
            if text == '=':
                result = eval(self.display.text(), {"__builtins__": None}, math.__dict__)
                self.display.setText(str(result))
            elif text == 'sqrt':
                self.display.setText(str(math.sqrt(float(self.display.text()))))
            elif text == 'sin':
                self.display.setText(str(math.sin(math.radians(float(self.display.text())))))
            elif text == 'cos':
                self.display.setText(str(math.cos(math.radians(float(self.display.text())))))
            elif text == '^':
                self.display.setText(self.display.text() + '**')
            else:
                self.display.setText(self.display.text() + text)
        except Exception as e:
            self.display.setText("Error")

    def insert_result(self):
        if self.insert_callback:
            self.insert_callback(self.display.text())


    app = QApplication(sys.argv)
    editor = QTextEdit()

    pdf_tab = PDFViewerTab(editor)
    pdf_tab.show()

    sys.exit(app.exec_())
if __name__ == "__main__":
    main()    
