# latex_document_wizard.py
"""
LaTeX Document Wizard - Widget version for embedding in tabs
uses JSON file in standard config directory.
"""

import json
import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QLineEdit, QTextEdit, QPushButton,
    QTabWidget, QGridLayout, QGroupBox, QFileDialog,
    QScrollArea, QSplitter, QMessageBox, QSizePolicy,
    QFormLayout, QToolButton, QDialog,
    QDialogButtonBox, QStatusBar, QToolBar,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor
from PyQt5.QtCore import Qt, QSize
import app_info

# ----------------------------------------------------------------------
# Helper functions for config file location (same as todo_file_path logic)
# ----------------------------------------------------------------------
def get_config_dir():
    """Return the platform-specific config directory for the application."""
    app_name = app_info.APP_NAME
    system = sys.platform.lower()

    if system.startswith('win'):
        appdata = os.environ.get('APPDATA')
        if appdata:
            config_dir = os.path.join(appdata, app_name)
        else:
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', app_name)
    elif system.startswith('darwin'):
        config_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    else:
        xdg = os.environ.get('XDG_CONFIG_HOME')
        if xdg:
            config_dir = os.path.join(xdg, app_name)
        else:
            config_dir = os.path.join(os.path.expanduser('~'), '.config', app_name)

    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_file_path():
    """Return full path to the JSON configuration file."""
    return os.path.join(get_config_dir(), "latex_wizard_config.json")


# ----------------------------------------------------------------------
# Helper classes (FixedWidthComboBox, TemplateManagerDialog, PackageManagerDialog, PackageOptionsDialog)
# ----------------------------------------------------------------------
class FixedWidthComboBox(QComboBox):
    """Custom combobox with fixed maximum width"""
    def __init__(self, max_width=200, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_width = max_width
        self.setMaximumWidth(max_width)


class TemplateManagerDialog(QDialog):
    """Dialog for managing document templates (uses parent wizard's JSON config)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Template Manager")
        self.resize(800, 600)
        self.parent_wizard = parent

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "<b>Manage Document Templates</b><br>"
            "Save, load, edit, and organize your LaTeX document templates."
        )
        layout.addWidget(info_label)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("➕ New from Current")
        self.btn_load = QPushButton("📂 Load")
        self.btn_save = QPushButton("💾 Save")
        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_export = QPushButton("📤 Export")
        self.btn_import = QPushButton("📥 Import")

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_export)
        toolbar.addWidget(self.btn_import)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Splitter for template list and preview
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Template list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("<b>Templates:</b>"))

        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self.on_template_selected)
        left_layout.addWidget(self.template_list)
        splitter.addWidget(left_widget)

        # Right side - Template details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("<b>Template Details:</b>"))

        info_form = QFormLayout()
        self.template_name = QLineEdit()
        self.template_desc = QTextEdit()
        self.template_desc.setMaximumHeight(80)
        info_form.addRow("Name:", self.template_name)
        info_form.addRow("Description:", self.template_desc)
        right_layout.addLayout(info_form)

        right_layout.addWidget(QLabel("<b>Configuration Preview:</b>"))
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setFont(QFont("Courier New", 9))
        right_layout.addWidget(self.template_preview)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)

        self.btn_new.clicked.connect(self.create_from_current)
        self.btn_load.clicked.connect(self.load_template)
        self.btn_save.clicked.connect(self.save_template)
        self.btn_delete.clicked.connect(self.delete_template)
        self.btn_export.clicked.connect(self.export_template)
        self.btn_import.clicked.connect(self.import_template)

        self.templates = {}
        self.load_all_templates()

    def load_all_templates(self):
        """Load all saved templates from parent wizard's config."""
        self.templates = getattr(self.parent_wizard, 'saved_templates', {})
        if not self.templates:
            # Add built-in templates if not present
            self.templates = {
                "Academic Article": {
                    "name": "Academic Article",
                    "description": "Standard academic article with abstract and bibliography",
                    "config": {
                        "document_class": "article",
                        "options": "a4paper,11pt",
                        "packages": ["amsmath", "graphicx", "hyperref", "natbib"],
                        "include_abstract": True,
                        "include_toc": False
                    }
                },
                "Technical Report": {
                    "name": "Technical Report",
                    "description": "Detailed technical report with table of contents and figures",
                    "config": {
                        "document_class": "report",
                        "options": "a4paper,12pt,twoside",
                        "packages": ["amsmath", "graphicx", "hyperref", "booktabs"],
                        "include_toc": True,
                        "include_lof": True,
                        "include_lot": True
                    }
                },
                "Beamer Presentation": {
                    "name": "Beamer Presentation",
                    "description": "Professional presentation slides",
                    "config": {
                        "document_class": "beamer",
                        "options": "",
                        "packages": ["graphicx"],
                        "theme": "Madrid",
                        "color": "dolphin"
                    }
                }
            }
        self.refresh_template_list()

    def refresh_template_list(self):
        self.template_list.clear()
        for name in sorted(self.templates.keys()):
            item = QListWidgetItem(name)
            if name in ["Academic Article", "Technical Report", "Beamer Presentation"]:
                item.setForeground(QColor("#007acc"))
            self.template_list.addItem(item)
        if self.template_list.count() > 0:
            self.template_list.setCurrentRow(0)

    def on_template_selected(self, current, previous):
        if not current:
            return
        name = current.text()
        template = self.templates.get(name, {})
        self.template_name.setText(template.get("name", ""))
        self.template_desc.setPlainText(template.get("description", ""))
        config = template.get("config", {})
        preview_lines = ["Document Configuration:", "-" * 40]
        for key, value in config.items():
            if isinstance(value, list):
                preview_lines.append(f"{key}: {', '.join(value)}")
            elif isinstance(value, bool):
                preview_lines.append(f"{key}: {'Yes' if value else 'No'}")
            else:
                preview_lines.append(f"{key}: {value}")
        self.template_preview.setPlainText("\n".join(preview_lines))

    def create_from_current(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Template", "Template name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.templates:
            reply = QMessageBox.question(self, "Overwrite?",
                                         f"Template '{name}' already exists. Overwrite?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        desc, ok = QInputDialog.getText(self, "Template Description", "Description (optional):")
        config = self.parent_wizard.gather_settings()
        self.templates[name] = {
            "name": name,
            "description": desc if ok else "",
            "config": config
        }
        self.save_all_templates()
        self.refresh_template_list()
        items = self.template_list.findItems(name, Qt.MatchExactly)
        if items:
            self.template_list.setCurrentItem(items[0])
        if hasattr(self.parent_wizard, 'show_status'):
            self.parent_wizard.show_status(f"Template '{name}' created", 2000)

    def load_template(self):
        current = self.template_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No template selected!")
            return
        name = current.text()
        template = self.templates.get(name)
        if not template:
            return
        reply = QMessageBox.question(self, "Load Template",
                                     f"Load template '{name}'? Current settings will be replaced.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            config = template.get("config", {})
            self.parent_wizard.apply_settings(config)
            if hasattr(self.parent_wizard, 'show_status'):
                self.parent_wizard.show_status(f"Template '{name}' loaded", 2000)
            QMessageBox.information(self, "Success", f"Template '{name}' loaded successfully!")

    def save_template(self):
        current = self.template_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No template selected!")
            return
        old_name = current.text()
        new_name = self.template_name.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Error", "Template name cannot be empty!")
            return
        if new_name != old_name and new_name in self.templates:
            QMessageBox.warning(self, "Error", "A template with this name already exists!")
            return
        template = self.templates.get(old_name, {})
        template["name"] = new_name
        template["description"] = self.template_desc.toPlainText()
        if new_name != old_name:
            self.templates[new_name] = template
            del self.templates[old_name]
        else:
            self.templates[new_name] = template
        self.save_all_templates()
        self.refresh_template_list()
        items = self.template_list.findItems(new_name, Qt.MatchExactly)
        if items:
            self.template_list.setCurrentItem(items[0])
        QMessageBox.information(self, "Success", "Template saved!")

    def delete_template(self):
        current = self.template_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No template selected!")
            return
        name = current.text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete template '{name}'? This cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.templates[name]
            self.save_all_templates()
            self.refresh_template_list()
            QMessageBox.information(self, "Success", f"Template '{name}' deleted")

    def export_template(self):
        current = self.template_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No template selected!")
            return
        name = current.text()
        template = self.templates.get(name)
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Template", f"{name}.template.json", "Template Files (*.template.json);;JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2)
                QMessageBox.information(self, "Success", f"Template exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def import_template(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Template", "", "Template Files (*.template.json);;JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                if not isinstance(template, dict) or "name" not in template:
                    raise ValueError("Invalid template format")
                name = template["name"]
                if name in self.templates:
                    reply = QMessageBox.question(self, "Overwrite?",
                                                 f"Template '{name}' already exists. Overwrite?",
                                                 QMessageBox.Yes | QMessageBox.No)
                    if reply != QMessageBox.Yes:
                        return
                self.templates[name] = template
                self.save_all_templates()
                self.refresh_template_list()
                items = self.template_list.findItems(name, Qt.MatchExactly)
                if items:
                    self.template_list.setCurrentItem(items[0])
                QMessageBox.information(self, "Success", f"Template '{name}' imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def save_all_templates(self):
        """Save templates to parent wizard's config and persist to disk."""
        self.parent_wizard.saved_templates = self.templates
        self.parent_wizard.save_config()


class PackageManagerDialog(QDialog):
    """Dialog for managing package categories and packages"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Package Manager")
        self.resize(700, 500)
        self.parent_wizard = parent

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "<b>Manage Package Categories and Packages</b><br>"
            "Add, edit, or remove package categories and their packages."
        )
        layout.addWidget(info_label)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("<b>Categories:</b>"))

        self.category_list = QListWidget()
        self.category_list.currentItemChanged.connect(self.on_category_selected)
        left_layout.addWidget(self.category_list)

        cat_buttons = QHBoxLayout()
        self.btn_add_cat = QPushButton("Add Category")
        self.btn_edit_cat = QPushButton("Rename")
        self.btn_del_cat = QPushButton("Delete")
        cat_buttons.addWidget(self.btn_add_cat)
        cat_buttons.addWidget(self.btn_edit_cat)
        cat_buttons.addWidget(self.btn_del_cat)
        left_layout.addLayout(cat_buttons)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.packages_label = QLabel("<b>Packages:</b>")
        right_layout.addWidget(self.packages_label)

        self.package_list = QListWidget()
        right_layout.addWidget(self.package_list)

        pkg_buttons = QHBoxLayout()
        self.btn_add_pkg = QPushButton("Add Package")
        self.btn_edit_pkg = QPushButton("Edit")
        self.btn_del_pkg = QPushButton("Delete")
        pkg_buttons.addWidget(self.btn_add_pkg)
        pkg_buttons.addWidget(self.btn_edit_pkg)
        pkg_buttons.addWidget(self.btn_del_pkg)
        right_layout.addLayout(pkg_buttons)

        splitter.addWidget(right_widget)
        splitter.setSizes([250, 450])
        layout.addWidget(splitter)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_changes)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.btn_add_cat.clicked.connect(self.add_category)
        self.btn_edit_cat.clicked.connect(self.edit_category)
        self.btn_del_cat.clicked.connect(self.delete_category)
        self.btn_add_pkg.clicked.connect(self.add_package)
        self.btn_edit_pkg.clicked.connect(self.edit_package)
        self.btn_del_pkg.clicked.connect(self.delete_package)

        self.load_current_config()

    def load_current_config(self):
        if hasattr(self.parent_wizard, 'package_categories'):
            self.categories = self.parent_wizard.package_categories.copy()
        else:
            self.categories = {
                "Mathematics": ["amsmath", "amssymb", "amsfonts", "mathtools", "bm", "cancel", "siunitx", "physics"],
                "Graphics & Figures": ["graphicx", "tikz", "pgfplots", "xcolor", "float", "wrapfig", "subcaption", "svg"],
                "Tables": ["array", "tabularx", "booktabs", "longtable", "multirow", "colortbl", "makecell"],
                "References & Citations": ["hyperref", "natbib", "biblatex", "url", "cleveref", "doi", "xurl"],
                "Layout & Formatting": ["geometry", "fancyhdr", "setspace", "parskip", "microtype", "titlesec", "multicol"],
                "Code & Algorithms": ["listings", "algorithm2e", "minted", "verbatim", "algorithmicx", "algpseudocode"],
                "Lists & Enumerations": ["enumitem", "paralist", "mdwlist"],
                "Advanced Typography": ["csquotes", "epigraph", "lettrine", "dropcaps"]
            }
        self.refresh_category_list()

    def refresh_category_list(self):
        self.category_list.clear()
        for category in sorted(self.categories.keys()):
            self.category_list.addItem(category)
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def on_category_selected(self, current, previous):
        if current:
            category = current.text()
            self.packages_label.setText(f"<b>Packages in '{category}':</b>")
            self.package_list.clear()
            for package in self.categories.get(category, []):
                self.package_list.addItem(package)

    def add_category(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Category", "Category name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.categories:
                QMessageBox.warning(self, "Error", "Category already exists!")
                return
            self.categories[name] = []
            self.refresh_category_list()
            items = self.category_list.findItems(name, Qt.MatchExactly)
            if items:
                self.category_list.setCurrentItem(items[0])

    def edit_category(self):
        from PyQt5.QtWidgets import QInputDialog
        current = self.category_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No category selected!")
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "Rename Category", "New name:", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name in self.categories:
                QMessageBox.warning(self, "Error", "Category already exists!")
                return
            self.categories[new_name] = self.categories.pop(old_name)
            self.refresh_category_list()

    def delete_category(self):
        current = self.category_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No category selected!")
            return
        category = current.text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete category '{category}' and all its packages?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.categories[category]
            self.refresh_category_list()

    def add_package(self):
        from PyQt5.QtWidgets import QInputDialog
        current = self.category_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Error", "No category selected!")
            return
        category = current.text()
        name, ok = QInputDialog.getText(self, "Add Package", "Package name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.categories[category]:
                QMessageBox.warning(self, "Error", "Package already exists in this category!")
                return
            self.categories[category].append(name)
            self.on_category_selected(current, None)

    def edit_package(self):
        from PyQt5.QtWidgets import QInputDialog
        cat_item = self.category_list.currentItem()
        pkg_item = self.package_list.currentItem()
        if not cat_item or not pkg_item:
            QMessageBox.warning(self, "Error", "No package selected!")
            return
        category = cat_item.text()
        old_name = pkg_item.text()
        new_name, ok = QInputDialog.getText(self, "Edit Package", "Package name:", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name in self.categories[category]:
                QMessageBox.warning(self, "Error", "Package already exists!")
                return
            idx = self.categories[category].index(old_name)
            self.categories[category][idx] = new_name
            self.on_category_selected(cat_item, None)

    def delete_package(self):
        cat_item = self.category_list.currentItem()
        pkg_item = self.package_list.currentItem()
        if not cat_item or not pkg_item:
            QMessageBox.warning(self, "Error", "No package selected!")
            return
        category = cat_item.text()
        package = pkg_item.text()
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete package '{package}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.categories[category].remove(package)
            self.on_category_selected(cat_item, None)

    def save_changes(self):
        self.accept()

    def get_categories(self):
        return self.categories


class PackageOptionsDialog(QDialog):
    def __init__(self, package_name, parent=None):
        super().__init__(parent)
        self.package_name = package_name
        self.setWindowTitle(f"Configure {package_name} Options")
        self.resize(400, 200)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Options for {package_name}:"))
        self.options_input = QLineEdit()
        self.options_input.setPlaceholderText("e.g., dvips, hidelinks")
        layout.addWidget(self.options_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_options(self):
        return self.options_input.text().strip()


# ----------------------------------------------------------------------
# Main Widget
# ----------------------------------------------------------------------
class LatexDocumentWizardWidget(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.package_options = {}
        self.saved_templates = {}          # will be loaded from JSON
        # Load package categories from JSON or defaults (must be before setup_ui)
        self.package_categories = self.load_package_config()
        self.setup_ui()
        # Load saved templates (overwrites self.saved_templates)
        self.load_templates_from_config()
        # Refresh UI if needed (e.g., after loading templates that might affect something)
        # (No need to refresh packages again because categories didn't change)

    # ------------------------------------------------------------------
    # Configuration file handling
    # ------------------------------------------------------------------
    def load_package_config(self):
        """Load package categories from JSON file or return defaults."""
        config_path = get_config_file_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "package_categories" in data:
                        return data["package_categories"]
            except Exception:
                pass
        # Default categories
        return {
            "Mathematics": ["amsmath", "amssymb", "amsfonts", "mathtools", "bm", "cancel", "siunitx", "physics"],
            "Graphics & Figures": ["graphicx", "tikz", "pgfplots", "xcolor", "float", "wrapfig", "subcaption", "svg"],
            "Tables": ["array", "tabularx", "booktabs", "longtable", "multirow", "colortbl", "makecell"],
            "References & Citations": ["hyperref", "natbib", "biblatex", "url", "cleveref", "doi", "xurl"],
            "Layout & Formatting": ["geometry", "fancyhdr", "setspace", "parskip", "microtype", "titlesec", "multicol"],
            "Code & Algorithms": ["listings", "algorithm2e", "minted", "verbatim", "algorithmicx", "algpseudocode"],
            "Lists & Enumerations": ["enumitem", "paralist", "mdwlist"],
            "Advanced Typography": ["csquotes", "epigraph", "lettrine", "dropcaps"]
        }

    def load_templates_from_config(self):
        """Load saved_templates from JSON file."""
        config_path = get_config_file_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "saved_templates" in data:
                        self.saved_templates = data["saved_templates"]
            except Exception:
                pass
        if not self.saved_templates:
            # Optionally add built-in templates
            self.saved_templates = {}

    def save_config(self):
        """Save both package_categories and saved_templates to JSON file."""
        config = {
            "package_categories": self.package_categories,
            "saved_templates": self.saved_templates
        }
        config_path = get_config_file_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.create_toolbar(main_layout)

        splitter = QSplitter(Qt.Vertical)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        self.init_document_tab()
        self.init_packages_tab()
        self.init_structure_tab()
        self.init_formatting_tab()
        self.init_beamer_tab()
        self.init_custom_tab()

        splitter.addWidget(self.tab_widget)

        output_widget = self.create_output_area()
        splitter.addWidget(output_widget)

        splitter.setSizes([500, 300])
        main_layout.addWidget(splitter)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("background: #f0f0f0; padding: 5px; border-top: 1px solid #d0d0d0;")
        main_layout.addWidget(self.status_label)

        self.connect_signals()

    def create_toolbar(self, parent_layout):
        toolbar_frame = QFrame()
        toolbar_frame.setFrameShape(QFrame.StyledPanel)
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setSpacing(5)

        toolbar.addWidget(QLabel("<b>File:</b> "))
        new_btn = QPushButton("🆕 New")
        new_btn.clicked.connect(self.new_document)
        toolbar.addWidget(new_btn)

        open_btn = QPushButton("📂 Open")
        open_btn.clicked.connect(self.load_template)
        toolbar.addWidget(open_btn)

        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_template)
        toolbar.addWidget(save_btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setFrameShadow(QFrame.Sunken)
        toolbar.addWidget(sep1)

        toolbar.addWidget(QLabel("<b>Tools:</b> "))
        template_mgr_btn = QPushButton("📋 Templates")
        template_mgr_btn.clicked.connect(self.open_template_manager)
        toolbar.addWidget(template_mgr_btn)

        pkg_mgr_btn = QPushButton("📦 Packages")
        pkg_mgr_btn.clicked.connect(self.open_package_manager)
        toolbar.addWidget(pkg_mgr_btn)

        validate_btn = QPushButton("✓ Validate")
        validate_btn.clicked.connect(self.validate_latex)
        toolbar.addWidget(validate_btn)

        toolbar.addStretch()
        parent_layout.addWidget(toolbar_frame)

    def create_output_area(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        controls = QHBoxLayout()
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setObjectName("primary")
        controls.addWidget(self.generate_btn)

        article_btn = QPushButton("Article")
        article_btn.clicked.connect(lambda: self.apply_template("article"))
        controls.addWidget(article_btn)

        report_btn = QPushButton("Report")
        report_btn.clicked.connect(lambda: self.apply_template("report"))
        controls.addWidget(report_btn)

        beamer_btn = QPushButton("Presentation")
        beamer_btn.clicked.connect(lambda: self.apply_template("beamer"))
        controls.addWidget(beamer_btn)

        self.btn_copy = QPushButton("Copy")
        self.btn_clear = QPushButton("Clear")
        self.btn_insert = QPushButton("Insert")
        self.btn_insert.setToolTip("Insert Latex code to Editor")
        self.btn_insert.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5cb85c, stop:1 #4cae4c);
                color: white;
                border-style: outset;
                border-width: 2px;
                border-radius: 4px;
                border-color: #3e8e3e;
                font-weight: bold;
                font-size: 8pt;
                padding: 0 10px;
                min-height: 22px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #6ec86e, stop:1 #5cb85c);
                border-color: #4cae4c;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3e8e3e, stop:1 #4cae4c);
                border-style: inset;
                border-color: #2e6e2e;
                padding-top: 2px;
                padding-bottom: 0px;
            }
            QPushButton:disabled {
                background: #cccccc;
                border-color: #aaaaaa;
                color: #888888;
            }
        """)

        controls.addWidget(self.btn_copy)
        controls.addWidget(self.btn_clear)
        controls.addWidget(self.btn_insert)

        layout.addLayout(controls)

        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Courier New", 10))
        self.output_text.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.output_text)

        self.stats_label = QLabel("Lines: 0 | Characters: 0")
        self.stats_label.setStyleSheet("color: #666; font-size: 8pt;")
        layout.addWidget(self.stats_label)

        return widget

    def create_scrollable_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        container = QWidget()
        scroll.setWidget(container)
        return scroll, container

    def init_document_tab(self):
        scroll, container = self.create_scrollable_tab()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        class_group = QGroupBox("Document Class")
        class_layout = QFormLayout()
        self.doc_class = FixedWidthComboBox(250)
        self.doc_class.addItems(["article", "report", "book", "letter", "beamer", "memoir", "scrartcl", "scrreprt", "scrbook"])
        self.doc_class.currentTextChanged.connect(self.on_class_changed)
        self.doc_options = QLineEdit()
        self.doc_options.setPlaceholderText("e.g., a4paper,12pt,twoside")
        self.doc_options.setMaximumWidth(400)
        class_layout.addRow("Class:", self.doc_class)
        class_layout.addRow("Options:", self.doc_options)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)

        encoding_group = QGroupBox("Encoding & Language")
        encoding_layout = QGridLayout()
        encoding_layout.addWidget(QLabel("Input Encoding:"), 0, 0)
        self.encoding_combo = FixedWidthComboBox(150)
        self.encoding_combo.addItems(["utf8", "latin1", "ascii", "none"])
        encoding_layout.addWidget(self.encoding_combo, 0, 1)
        encoding_layout.addWidget(QLabel("Font Encoding:"), 0, 2)
        self.font_enc_combo = FixedWidthComboBox(150)
        self.font_enc_combo.addItems(["T1", "OT1", "TS1", "none"])
        encoding_layout.addWidget(self.font_enc_combo, 0, 3)
        encoding_layout.addWidget(QLabel("Language:"), 1, 0)
        self.babel_combo = FixedWidthComboBox(150)
        self.babel_combo.addItems(["english", "french", "german", "spanish", "italian", "portuguese", "russian", "arabic", "none"])
        encoding_layout.addWidget(self.babel_combo, 1, 1)
        encoding_group.setLayout(encoding_layout)
        layout.addWidget(encoding_group)

        meta_group = QGroupBox("Document Metadata")
        meta_layout = QFormLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter document title")
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Enter author name(s)")
        self.date_input = QLineEdit()
        self.date_input.setText("\\today")
        self.date_input.setPlaceholderText("\\today or specific date")
        meta_layout.addRow("Title:", self.title_input)
        meta_layout.addRow("Author:", self.author_input)
        meta_layout.addRow("Date:", self.date_input)
        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Document")

    def init_packages_tab(self):
        scroll, container = self.create_scrollable_tab()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        manager_layout = QHBoxLayout()
        manager_layout.addWidget(QLabel("<i>Customize package categories and packages:</i>"))
        btn_pkg_manager = QPushButton("📦 Package Manager")
        btn_pkg_manager.clicked.connect(self.open_package_manager)
        manager_layout.addWidget(btn_pkg_manager)
        manager_layout.addStretch()
        layout.addLayout(manager_layout)

        self.package_checks = {}
        self.package_config_buttons = {}
        self.package_groups = {}
        self.refresh_package_ui(layout)

        custom_group = QGroupBox("Custom Packages")
        custom_layout = QVBoxLayout()
        self.custom_packages = QTextEdit()
        self.custom_packages.setMaximumHeight(100)
        self.custom_packages.setPlaceholderText(
            "Add custom packages (one per line):\n"
            "\\usepackage{package-name}\n"
            "\\usepackage[options]{package-name}"
        )
        custom_layout.addWidget(self.custom_packages)
        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Packages")

    def refresh_package_ui(self, parent_layout):
        # Remove old groups
        for group in self.package_groups.values():
            parent_layout.removeWidget(group)
            group.deleteLater()
        self.package_groups.clear()
        self.package_checks.clear()
        self.package_config_buttons.clear()

        # Rebuild from current categories
        for category, packages in self.package_categories.items():
            group = QGroupBox(category)
            group_layout = QGridLayout()
            group_layout.setSpacing(8)
            for i, pkg in enumerate(packages):
                row = i // 3
                col = (i % 3) * 2
                cb = QCheckBox(pkg)
                if pkg in ["amsmath", "graphicx", "hyperref", "geometry"]:
                    cb.setChecked(True)
                self.package_checks[pkg] = cb
                group_layout.addWidget(cb, row, col)
                if pkg in ["hyperref", "geometry", "graphicx", "listings", "biblatex"]:
                    config_btn = QToolButton()
                    config_btn.setText("⚙")
                    config_btn.setMaximumWidth(25)
                    config_btn.clicked.connect(lambda checked, p=pkg: self.configure_package(p))
                    self.package_config_buttons[pkg] = config_btn
                    group_layout.addWidget(config_btn, row, col + 1)
            group.setLayout(group_layout)
            self.package_groups[category] = group
            parent_layout.insertWidget(parent_layout.count() - 2, group)

    def init_structure_tab(self):
        scroll, container = self.create_scrollable_tab()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        struct_group = QGroupBox("Front Matter")
        struct_layout = QGridLayout()
        self.include_abstract = QCheckBox("Abstract")
        self.include_toc = QCheckBox("Table of Contents")
        self.include_lof = QCheckBox("List of Figures")
        self.include_lot = QCheckBox("List of Tables")
        self.include_lol = QCheckBox("List of Listings")
        self.include_acknowledgments = QCheckBox("Acknowledgments")
        struct_layout.addWidget(self.include_abstract, 0, 0)
        struct_layout.addWidget(self.include_toc, 0, 1)
        struct_layout.addWidget(self.include_lof, 0, 2)
        struct_layout.addWidget(self.include_lot, 1, 0)
        struct_layout.addWidget(self.include_lol, 1, 1)
        struct_layout.addWidget(self.include_acknowledgments, 1, 2)
        struct_group.setLayout(struct_layout)
        layout.addWidget(struct_group)

        back_group = QGroupBox("Back Matter")
        back_layout = QGridLayout()
        self.include_appendix = QCheckBox("Appendix")
        self.include_index = QCheckBox("Index")
        self.include_glossary = QCheckBox("Glossary")
        back_layout.addWidget(self.include_appendix, 0, 0)
        back_layout.addWidget(self.include_index, 0, 1)
        back_layout.addWidget(self.include_glossary, 0, 2)
        back_group.setLayout(back_layout)
        layout.addWidget(back_group)

        sections_group = QGroupBox("Document Sections")
        sections_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_add_section = QPushButton("Add Section")
        self.btn_add_subsection = QPushButton("Add Subsection")
        self.btn_clear_sections = QPushButton("Clear All")
        btn_layout.addWidget(self.btn_add_section)
        btn_layout.addWidget(self.btn_add_subsection)
        btn_layout.addWidget(self.btn_clear_sections)
        btn_layout.addStretch()
        self.sections_input = QTextEdit()
        self.sections_input.setMaximumHeight(150)
        self.sections_input.setPlaceholderText(
            "Add sections (one per line):\n"
            "\\section{Introduction}\n"
            "\\subsection{Background}\n"
            "\\subsubsection{Details}"
        )
        self.btn_add_section.clicked.connect(lambda: self.add_section_template("\\section{Title}"))
        self.btn_add_subsection.clicked.connect(lambda: self.add_section_template("\\subsection{Title}"))
        self.btn_clear_sections.clicked.connect(self.sections_input.clear)
        sections_layout.addLayout(btn_layout)
        sections_layout.addWidget(self.sections_input)
        sections_group.setLayout(sections_layout)
        layout.addWidget(sections_group)

        bib_group = QGroupBox("Bibliography")
        bib_layout = QFormLayout()
        self.bib_backend = QComboBox()
        self.bib_backend.addItems(["BibTeX", "BibLaTeX"])
        self.bib_style = FixedWidthComboBox(200)
        self.bib_style.addItems(["plain", "unsrt", "alpha", "abbrv", "ieeetr", "acm", "apa", "mla", "chicago", "nature"])
        self.bib_file = QLineEdit()
        self.bib_file.setPlaceholderText("references.bib")
        bib_layout.addRow("Backend:", self.bib_backend)
        bib_layout.addRow("Style:", self.bib_style)
        bib_layout.addRow("BibTeX file:", self.bib_file)
        bib_group.setLayout(bib_layout)
        layout.addWidget(bib_group)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Structure")

    def init_formatting_tab(self):
        scroll, container = self.create_scrollable_tab()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        geometry_group = QGroupBox("Page Geometry")
        geometry_layout = QFormLayout()
        self.paper_size = QComboBox()
        self.paper_size.addItems(["a4paper", "letterpaper", "a5paper", "b5paper", "executivepaper", "legalpaper"])
        self.orientation = QComboBox()
        self.orientation.addItems(["portrait", "landscape"])
        self.margins = QLineEdit()
        self.margins.setPlaceholderText("e.g., 2.5cm or top=3cm,bottom=2cm")
        geometry_layout.addRow("Paper Size:", self.paper_size)
        geometry_layout.addRow("Orientation:", self.orientation)
        geometry_layout.addRow("Margins:", self.margins)
        geometry_group.setLayout(geometry_layout)
        layout.addWidget(geometry_group)

        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout()
        self.font_size = QComboBox()
        self.font_size.addItems(["10pt", "11pt", "12pt", "14pt"])
        self.font_size.setCurrentText("11pt")
        self.font_family = QComboBox()
        self.font_family.addItems(["Default", "Times", "Palatino", "Helvetica", "Computer Modern", "Latin Modern"])
        self.line_spacing = QComboBox()
        self.line_spacing.addItems(["single", "onehalf", "double"])
        font_layout.addRow("Base Size:", self.font_size)
        font_layout.addRow("Font Family:", self.font_family)
        font_layout.addRow("Line Spacing:", self.line_spacing)
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        column_group = QGroupBox("Column Layout")
        column_layout = QFormLayout()
        self.columns = QComboBox()
        self.columns.addItems(["onecolumn", "twocolumn"])
        column_layout.addRow("Columns:", self.columns)
        column_group.setLayout(column_layout)
        layout.addWidget(column_group)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Formatting")

    def init_beamer_tab(self):
        scroll, container = self.create_scrollable_tab()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        theme_group = QGroupBox("Theme Configuration")
        theme_layout = QFormLayout()
        self.theme_combo = FixedWidthComboBox(250)
        themes = ["default", "AnnArbor", "Antibes", "Bergen", "Berkeley", "Berlin", "Boadilla", "CambridgeUS",
                  "Copenhagen", "Darmstadt", "Dresden", "Frankfurt", "Goettingen", "Hannover", "Ilmenau",
                  "JuanLesPins", "Luebeck", "Madrid", "Malmoe", "Marburg", "Montpellier", "PaloAlto",
                  "Pittsburgh", "Rochester", "Singapore", "Szeged", "Warsaw"]
        self.theme_combo.addItems(themes)
        self.color_combo = FixedWidthComboBox(200)
        colors = ["default", "albatross", "beaver", "beetle", "crane", "dolphin", "dove", "fly", "lily",
                  "orchid", "rose", "seagull", "seahorse", "whale", "wolverine"]
        self.color_combo.addItems(colors)
        self.font_combo = FixedWidthComboBox(200)
        fonts = ["default", "professionalfonts", "serif", "structurebold", "structureitalicserif", "structuresmallcapsserif"]
        self.font_combo.addItems(fonts)
        theme_layout.addRow("Presentation Theme:", self.theme_combo)
        theme_layout.addRow("Color Theme:", self.color_combo)
        theme_layout.addRow("Font Theme:", self.font_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        options_group = QGroupBox("Presentation Options")
        options_layout = QGridLayout()
        self.beamer_nav = QCheckBox("Show navigation symbols")
        self.beamer_nav.setChecked(True)
        self.beamer_trans = QCheckBox("Transparent overlays")
        self.beamer_foot = QCheckBox("Show footline")
        self.beamer_head = QCheckBox("Show headline")
        self.beamer_secpage = QCheckBox("Section title pages")
        self.beamer_subsecpage = QCheckBox("Subsection title pages")
        self.beamer_outline = QCheckBox("Outline at each section")
        self.beamer_numbers = QCheckBox("Frame numbers")
        options_layout.addWidget(self.beamer_nav, 0, 0)
        options_layout.addWidget(self.beamer_trans, 0, 1)
        options_layout.addWidget(self.beamer_foot, 0, 2)
        options_layout.addWidget(self.beamer_head, 1, 0)
        options_layout.addWidget(self.beamer_secpage, 1, 1)
        options_layout.addWidget(self.beamer_subsecpage, 1, 2)
        options_layout.addWidget(self.beamer_outline, 2, 0)
        options_layout.addWidget(self.beamer_numbers, 2, 1)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        frame_group = QGroupBox("Frame Templates")
        frame_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_add_frame = QPushButton("Add Frame")
        self.btn_add_frame.clicked.connect(self.add_frame_template)
        btn_layout.addWidget(self.btn_add_frame)
        btn_layout.addStretch()
        self.frames_input = QTextEdit()
        self.frames_input.setMaximumHeight(150)
        self.frames_input.setPlaceholderText(
            "Add frame templates:\n"
            "\\begin{frame}{Frame Title}\n"
            "  Content here\n"
            "\\end{frame}"
        )
        frame_layout.addLayout(btn_layout)
        frame_layout.addWidget(self.frames_input)
        frame_group.setLayout(frame_layout)
        layout.addWidget(frame_group)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Beamer")

    def init_custom_tab(self):
        scroll, container = self.create_scrollable_tab()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        preamble_group = QGroupBox("Custom Preamble Code")
        preamble_layout = QVBoxLayout()
        preamble_layout.addWidget(QLabel("Add custom commands, definitions, or configurations:"))
        self.custom_preamble = QTextEdit()
        self.custom_preamble.setFont(QFont("Courier New", 10))
        self.custom_preamble.setPlaceholderText(
            "% Custom commands\n"
            "\\newcommand{\\mycommand}[1]{\\textbf{#1}}\n\n"
            "% Custom environments\n"
            "\\newenvironment{myenv}{\\begin{quote}}{\\end{quote}}\n\n"
            "% Other custom LaTeX code..."
        )
        preamble_layout.addWidget(self.custom_preamble)
        preamble_group.setLayout(preamble_layout)
        layout.addWidget(preamble_group)

        body_group = QGroupBox("Custom Document Body")
        body_layout = QVBoxLayout()
        body_layout.addWidget(QLabel("Add custom content to the document body:"))
        self.custom_body = QTextEdit()
        self.custom_body.setFont(QFont("Courier New", 10))
        self.custom_body.setPlaceholderText(
            "% Your custom LaTeX content\n"
            "\\lipsum[1-3]\n"
            "\\begin{figure}[h]\n"
            "  \\centering\n"
            "  % figure content\n"
            "\\end{figure}"
        )
        body_layout.addWidget(self.custom_body)
        body_group.setLayout(body_layout)
        layout.addWidget(body_group)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Custom Code")

    def connect_signals(self):
        self.btn_insert.clicked.connect(self.insert_to_editor)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        self.btn_clear.clicked.connect(self.clear_output)
        self.output_text.textChanged.connect(self.update_statistics)
        self.generate_btn.clicked.connect(self.generate_latex)

    # ------------------------------------------------------------------
    # Core functionality (unchanged except for config saving)
    # ------------------------------------------------------------------
    def on_class_changed(self, class_name):
        if class_name == "beamer":
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "Beamer":
                    self.tab_widget.setCurrentIndex(i)
                    break

    def configure_package(self, package_name):
        dialog = PackageOptionsDialog(package_name, self)
        if dialog.exec_():
            options = dialog.get_options()
            if options:
                self.package_options[package_name] = options
                self.show_status(f"Options set for {package_name}: {options}", 3000)

    def add_section_template(self, template):
        cursor = self.sections_input.textCursor()
        cursor.movePosition(QTextCursor.End)
        if self.sections_input.toPlainText():
            cursor.insertText("\n")
        cursor.insertText(template)
        self.sections_input.setTextCursor(cursor)
        if self.main_window:
            self.main_window.editor_manager.on_text_changed()

    def add_frame_template(self):
        template = (
            "\\begin{frame}{Frame Title}\n"
            "  \\begin{itemize}\n"
            "    \\item Point 1\n"
            "    \\item Point 2\n"
            "  \\end{itemize}\n"
            "\\end{frame}\n"
        )
        cursor = self.frames_input.textCursor()
        cursor.movePosition(QTextCursor.End)
        if self.frames_input.toPlainText():
            cursor.insertText("\n")
        cursor.insertText(template)
        self.frames_input.setTextCursor(cursor)
        if self.main_window:
            self.main_window.editor_manager.on_text_changed()

    def generate_latex(self):
        try:
            lines = []
            doc_class = self.doc_class.currentText()
            lines.append("% " + "=" * 70)
            lines.append("% Generated by LaTeX Document Wizard")
            lines.append("% " + "=" * 70)
            lines.append("")
            options = []
            if self.doc_options.text().strip():
                options.append(self.doc_options.text().strip())
            if hasattr(self, 'font_size'):
                options.append(self.font_size.currentText())
            if hasattr(self, 'paper_size'):
                options.append(self.paper_size.currentText())
            if hasattr(self, 'orientation') and self.orientation.currentText() == "landscape":
                options.append("landscape")
            if hasattr(self, 'columns'):
                options.append(self.columns.currentText())
            if options:
                lines.append(f"\\documentclass[{','.join(options)}]{{{doc_class}}}")
            else:
                lines.append(f"\\documentclass{{{doc_class}}}")
            lines.append("")
            # Encoding
            lines.append("% Encoding and Language")
            if self.encoding_combo.currentText() != "none":
                lines.append(f"\\usepackage[{self.encoding_combo.currentText()}]{{inputenc}}")
            if self.font_enc_combo.currentText() != "none":
                lines.append(f"\\usepackage[{self.font_enc_combo.currentText()}]{{fontenc}}")
            if self.babel_combo.currentText() != "none":
                lines.append(f"\\usepackage[{self.babel_combo.currentText()}]{{babel}}")
            lines.append("")
            # Packages
            lines.append("% Packages")
            for pkg, cb in self.package_checks.items():
                if cb.isChecked():
                    if pkg in self.package_options:
                        lines.append(f"\\usepackage[{self.package_options[pkg]}]{{{pkg}}}")
                    else:
                        lines.append(f"\\usepackage{{{pkg}}}")
            lines.append("")
            custom = self.custom_packages.toPlainText().strip()
            if custom:
                lines.append("% Custom Packages")
                lines.append(custom)
                lines.append("")
            if hasattr(self, 'margins') and self.margins.text().strip():
                lines.append(f"\\usepackage[{self.margins.text().strip()}]{{geometry}}")
                lines.append("")
            if hasattr(self, 'font_family') and self.font_family.currentText() != "Default":
                font_map = {"Times": "\\usepackage{times}", "Palatino": "\\usepackage{palatino}",
                            "Helvetica": "\\usepackage{helvet}", "Latin Modern": "\\usepackage{lmodern}"}
                font_cmd = font_map.get(self.font_family.currentText())
                if font_cmd:
                    lines.append(font_cmd)
                    lines.append("")
            if hasattr(self, 'line_spacing') and self.line_spacing.currentText() != "single":
                lines.append("\\usepackage{setspace}")
                if self.line_spacing.currentText() == "onehalf":
                    lines.append("\\onehalfspacing")
                elif self.line_spacing.currentText() == "double":
                    lines.append("\\doublespacing")
                lines.append("")
            # Beamer specific
            if doc_class == "beamer":
                lines.append("% Beamer Configuration")
                theme = self.theme_combo.currentText()
                if theme != "default":
                    lines.append(f"\\usetheme{{{theme}}}")
                color = self.color_combo.currentText()
                if color != "default":
                    lines.append(f"\\usecolortheme{{{color}}}")
                font = self.font_combo.currentText()
                if font != "default":
                    lines.append(f"\\usefonttheme{{{font}}}")
                if not self.beamer_nav.isChecked():
                    lines.append("\\setbeamertemplate{navigation symbols}{}")
                if self.beamer_trans.isChecked():
                    lines.append("\\setbeamercovered{transparent}")
                if self.beamer_numbers.isChecked():
                    lines.append("\\setbeamertemplate{footline}[frame number]")
                lines.append("")
            if hasattr(self, 'custom_preamble'):
                custom_pre = self.custom_preamble.toPlainText().strip()
                if custom_pre:
                    lines.append("% Custom Preamble")
                    lines.append(custom_pre)
                    lines.append("")
            lines.append("\\begin{document}")
            lines.append("")
            title = self.title_input.text().strip()
            author = self.author_input.text().strip()
            date = self.date_input.text().strip()
            if title or author or date:
                if title:
                    lines.append(f"\\title{{{title}}}")
                if author:
                    lines.append(f"\\author{{{author}}}")
                if date:
                    lines.append(f"\\date{{{date}}}")
                lines.append("\\maketitle")
                lines.append("")
            if self.include_abstract.isChecked():
                lines.append("\\begin{abstract}")
                lines.append("Your abstract text here.")
                lines.append("\\end{abstract}")
                lines.append("")
            if self.include_toc.isChecked():
                lines.append("\\tableofcontents")
                if doc_class != "beamer":
                    lines.append("\\newpage")
                lines.append("")
            if self.include_lof.isChecked():
                lines.append("\\listoffigures")
                lines.append("")
            if self.include_lot.isChecked():
                lines.append("\\listoftables")
                lines.append("")
            if hasattr(self, 'include_lol') and self.include_lol.isChecked():
                lines.append("\\lstlistoflistings")
                lines.append("")
            if hasattr(self, 'include_acknowledgments') and self.include_acknowledgments.isChecked():
                lines.append("\\section*{Acknowledgments}")
                lines.append("Acknowledgment text here.")
                lines.append("")
            sections = self.sections_input.toPlainText().strip()
            if sections:
                lines.append("% Document Sections")
                lines.append(sections)
                lines.append("")
            if doc_class == "beamer":
                frames = self.frames_input.toPlainText().strip()
                if frames:
                    lines.append("% Presentation Frames")
                    lines.append(frames)
                    lines.append("")
            if hasattr(self, 'custom_body'):
                custom_content = self.custom_body.toPlainText().strip()
                if custom_content:
                    lines.append("% Custom Content")
                    lines.append(custom_content)
                    lines.append("")
            if hasattr(self, 'include_appendix') and self.include_appendix.isChecked():
                lines.append("\\appendix")
                lines.append("\\section{Appendix Title}")
                lines.append("Appendix content here.")
                lines.append("")
            bib_file = self.bib_file.text().strip()
            if bib_file:
                lines.append("% Bibliography")
                if hasattr(self, 'bib_backend') and self.bib_backend.currentText() == "BibLaTeX":
                    lines.append("\\printbibliography")
                else:
                    lines.append(f"\\bibliographystyle{{{self.bib_style.currentText()}}}")
                    lines.append(f"\\bibliography{{{bib_file}}}")
                lines.append("")
            if hasattr(self, 'include_glossary') and self.include_glossary.isChecked():
                lines.append("\\printglossaries")
                lines.append("")
            if self.include_index.isChecked():
                lines.append("\\printindex")
                lines.append("")
            lines.append("\\end{document}")
            self.output_text.setPlainText("\n".join(lines))
            self.show_status("LaTeX code generated successfully!", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"Error generating LaTeX:\n{str(e)}")
            self.show_status("Error generating LaTeX code", 3000)

    def validate_latex(self):
        content = self.output_text.toPlainText()
        errors = []
        warnings = []
        if "\\documentclass" not in content:
            errors.append("Missing \\documentclass command")
        if "\\begin{document}" not in content:
            errors.append("Missing \\begin{document}")
        if "\\end{document}" not in content:
            errors.append("Missing \\end{document}")
        if content.count("{") != content.count("}"):
            warnings.append("Unmatched braces detected")
        if "\\usepackage{hyperref}" in content and content.index("\\usepackage{hyperref}") < content.rfind("\\usepackage"):
            warnings.append("hyperref should typically be loaded last")
        if errors:
            QMessageBox.warning(self, "Validation Errors", "Errors found:\n" + "\n".join(f"• {e}" for e in errors))
        elif warnings:
            QMessageBox.information(self, "Validation Warnings", "Warnings:\n" + "\n".join(f"• {w}" for w in warnings))
        else:
            QMessageBox.information(self, "Validation", "No obvious errors detected!")

    def update_statistics(self):
        text = self.output_text.toPlainText()
        lines = text.count('\n') + (1 if text else 0)
        chars = len(text)
        self.stats_label.setText(f"Lines: {lines} | Characters: {chars}")

    def insert_to_editor(self):
        latex_code = self.output_text.toPlainText()
        if not latex_code.strip():
            QMessageBox.information(self, "Info", "No LaTeX code to insert. Generate first!")
            return
        try:
            if self.main_window and hasattr(self.main_window, 'editor_manager'):
                active_editor = self.main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    cursor.insertText(latex_code)
                    active_editor.setFocus()
                    self.main_window.editor_manager.on_text_changed()
                    self.show_status("✅ Inserted to editor!", 3000)
                else:
                    QMessageBox.warning(self, "Warning", "No active editor found!")
            else:
                QMessageBox.warning(self, "Warning", "Editor manager not available!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert:\n{str(e)}")

    def copy_to_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.show_status("Copied to clipboard!", 2000)

    def clear_output(self):
        reply = QMessageBox.question(self, "Clear Output", "Are you sure you want to clear the output?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.output_text.clear()
            self.show_status("Output cleared")

    def save_template(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Template", "", "JSON Files (*.json)")
        if filename:
            try:
                template = self.gather_settings()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2)
                self.show_status(f"Template saved: {filename}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    def load_template(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Template", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                self.apply_settings(template)
                self.show_status(f"Template loaded: {filename}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))

    def gather_settings(self):
        settings = {
            "document_class": self.doc_class.currentText(),
            "options": self.doc_options.text(),
            "encoding": self.encoding_combo.currentText(),
            "font_encoding": self.font_enc_combo.currentText(),
            "language": self.babel_combo.currentText(),
            "title": self.title_input.text(),
            "author": self.author_input.text(),
            "date": self.date_input.text(),
            "packages": [pkg for pkg, cb in self.package_checks.items() if cb.isChecked()],
            "package_options": self.package_options.copy(),
            "custom_packages": self.custom_packages.toPlainText(),
            "sections": self.sections_input.toPlainText(),
            "include_abstract": self.include_abstract.isChecked(),
            "include_toc": self.include_toc.isChecked(),
            "include_lof": self.include_lof.isChecked(),
            "include_lot": self.include_lot.isChecked(),
            "include_index": self.include_index.isChecked(),
        }
        if hasattr(self, 'font_size'):
            settings["font_size"] = self.font_size.currentText()
        if hasattr(self, 'paper_size'):
            settings["paper_size"] = self.paper_size.currentText()
        if hasattr(self, 'margins'):
            settings["margins"] = self.margins.text()
        if hasattr(self, 'font_family'):
            settings["font_family"] = self.font_family.currentText()
        if hasattr(self, 'line_spacing'):
            settings["line_spacing"] = self.line_spacing.currentText()
        if self.doc_class.currentText() == "beamer":
            settings["beamer_theme"] = self.theme_combo.currentText()
            settings["beamer_color"] = self.color_combo.currentText()
            settings["beamer_font"] = self.font_combo.currentText()
            settings["beamer_frames"] = self.frames_input.toPlainText()
        settings["bib_file"] = self.bib_file.text()
        settings["bib_style"] = self.bib_style.currentText()
        if hasattr(self, 'custom_preamble'):
            settings["custom_preamble"] = self.custom_preamble.toPlainText()
        if hasattr(self, 'custom_body'):
            settings["custom_body"] = self.custom_body.toPlainText()
        return settings

    def apply_settings(self, settings):
        if "document_class" in settings:
            self.doc_class.setCurrentText(settings["document_class"])
        if "options" in settings:
            self.doc_options.setText(settings["options"])
        if "encoding" in settings:
            self.encoding_combo.setCurrentText(settings["encoding"])
        if "font_encoding" in settings:
            self.font_enc_combo.setCurrentText(settings["font_encoding"])
        if "language" in settings:
            self.babel_combo.setCurrentText(settings["language"])
        if "title" in settings:
            self.title_input.setText(settings["title"])
        if "author" in settings:
            self.author_input.setText(settings["author"])
        if "date" in settings:
            self.date_input.setText(settings["date"])
        if "packages" in settings:
            for cb in self.package_checks.values():
                cb.setChecked(False)
            for pkg in settings["packages"]:
                if pkg in self.package_checks:
                    self.package_checks[pkg].setChecked(True)
        if "package_options" in settings:
            self.package_options = settings["package_options"].copy()
        if "custom_packages" in settings:
            self.custom_packages.setPlainText(settings["custom_packages"])
        if "sections" in settings:
            self.sections_input.setPlainText(settings["sections"])
        if "include_abstract" in settings:
            self.include_abstract.setChecked(settings["include_abstract"])
        if "include_toc" in settings:
            self.include_toc.setChecked(settings["include_toc"])
        if "include_lof" in settings:
            self.include_lof.setChecked(settings["include_lof"])
        if "include_lot" in settings:
            self.include_lot.setChecked(settings["include_lot"])
        if "include_index" in settings:
            self.include_index.setChecked(settings["include_index"])
        if hasattr(self, 'font_size') and "font_size" in settings:
            self.font_size.setCurrentText(settings["font_size"])
        if hasattr(self, 'paper_size') and "paper_size" in settings:
            self.paper_size.setCurrentText(settings["paper_size"])
        if hasattr(self, 'margins') and "margins" in settings:
            self.margins.setText(settings["margins"])
        if hasattr(self, 'font_family') and "font_family" in settings:
            self.font_family.setCurrentText(settings["font_family"])
        if hasattr(self, 'line_spacing') and "line_spacing" in settings:
            self.line_spacing.setCurrentText(settings["line_spacing"])
        if "beamer_theme" in settings:
            self.theme_combo.setCurrentText(settings["beamer_theme"])
        if "beamer_color" in settings:
            self.color_combo.setCurrentText(settings["beamer_color"])
        if "beamer_font" in settings:
            self.font_combo.setCurrentText(settings["beamer_font"])
        if "beamer_frames" in settings:
            self.frames_input.setPlainText(settings["beamer_frames"])
        if "bib_file" in settings:
            self.bib_file.setText(settings["bib_file"])
        if "bib_style" in settings:
            self.bib_style.setCurrentText(settings["bib_style"])
        if hasattr(self, 'custom_preamble') and "custom_preamble" in settings:
            self.custom_preamble.setPlainText(settings["custom_preamble"])
        if hasattr(self, 'custom_body') and "custom_body" in settings:
            self.custom_body.setPlainText(settings["custom_body"])

    def apply_template(self, template_name):
        if template_name == "article":
            self.doc_class.setCurrentText("article")
            self.doc_options.setText("a4paper,11pt")
            self.package_checks["amsmath"].setChecked(True)
            self.package_checks["graphicx"].setChecked(True)
            self.package_checks["hyperref"].setChecked(True)
            self.include_abstract.setChecked(True)
            self.include_toc.setChecked(True)
        elif template_name == "report":
            self.doc_class.setCurrentText("report")
            self.doc_options.setText("a4paper,12pt,twoside")
            self.include_toc.setChecked(True)
            self.include_lof.setChecked(True)
            self.include_lot.setChecked(True)
        elif template_name == "beamer":
            self.doc_class.setCurrentText("beamer")
            self.theme_combo.setCurrentText("Madrid")
            self.color_combo.setCurrentText("dolphin")
        self.show_status(f"Applied {template_name} template", 2000)

    def new_document(self):
        reply = QMessageBox.question(self, "New Document", "Clear all settings and start new?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.doc_class.setCurrentIndex(0)
            self.doc_options.clear()
            self.title_input.clear()
            self.author_input.clear()
            self.date_input.setText("\\today")
            self.sections_input.clear()
            self.output_text.clear()
            for pkg, cb in self.package_checks.items():
                cb.setChecked(pkg in ["amsmath", "graphicx", "hyperref"])
            self.show_status("New document started")

    def open_package_manager(self):
        dialog = PackageManagerDialog(self)
        if dialog.exec_():
            self.package_categories = dialog.get_categories()
            self.save_config()
            # Refresh the package UI
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "Packages":
                    scroll = self.tab_widget.widget(i)
                    container = scroll.widget()
                    layout = container.layout()
                    self.refresh_package_ui(layout)
                    break

    def open_template_manager(self):
        dialog = TemplateManagerDialog(self)
        dialog.exec_()

    def show_status(self, message, timeout=0):
        self.status_label.setText(message)
        if timeout > 0:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(timeout, lambda: self.status_label.setText("Ready"))

    def closeEvent(self, event):
        self.save_config()
        event.accept()


# ----------------------------------------------------------------------
# Integration function (kept as in original)
# ----------------------------------------------------------------------
def add_latex_wizard_tab_to_pdf_viewer(main_window):
    """Add LaTeX Document Wizard tab to PDF viewer"""
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
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info",
                "LaTeX Document Wizard is only available in tabbed mode. Switch to tabbed mode first.")
            return
        if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
            layout_manager._recreate_pdf_container()
        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
            from PyQt5.QtWidgets import QTabWidget
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(pdf_manager.close_pdf_tab)
            pdf_layout = layout_manager.pdf_container.layout()
            if pdf_layout is None:
                from PyQt5.QtWidgets import QVBoxLayout
                pdf_layout = QVBoxLayout(layout_manager.pdf_container)
                layout_manager.pdf_container.setLayout(pdf_layout)
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
        tabs_to_remove = ["Welcome", "No Pdfs", "No PDFs", "No PDF"]
        for i in reversed(range(tab_widget.count())):
            tab_text = tab_widget.tabText(i)
            if tab_text in tabs_to_remove:
                tab_widget.removeTab(i)
        possible_labels = {tr["latex_wizard"] for tr in translations.values()}
        existing_index = -1
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                existing_index = i
                break
        if existing_index >= 0:
            tab_widget.setCurrentIndex(existing_index)
            return
        latex_wizard = LatexDocumentWizardWidget(main_window)
        if not hasattr(main_window, '_latex_wizard_tabs'):
            main_window._latex_wizard_tabs = []
        main_window._latex_wizard_tabs.append(latex_wizard)
        tab_name = tr.get("latex_wizard", "LaTeX Wizard")
        tab_index = tab_widget.addTab(latex_wizard, tab_name)
        tab_widget.tabBar().setTabData(tab_index, "latex_wizard")
        icon = QIcon("icons/wizard.svg")
        tab_widget.setTabIcon(tab_index, icon)
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)
        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)
        tab_widget.setVisible(True)
        tab_widget.show()
        latex_wizard.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()
        main_window.update()
    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add LaTeX wizard:\n{str(e)}")
        import traceback
        traceback.print_exc()