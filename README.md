# AynTex — A LaTeX Editor with Arabic Support

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-green?logo=qt)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/License-MIT-yellow)

AynTex is a feature-rich, cross-platform LaTeX editor built with PyQt5. It is designed with bilingual (Arabic/English) documents in mind, offering first-class support for right-to-left text, Arabic LaTeX commands, and bidirectional workflows — while remaining a fully capable general-purpose LaTeX IDE.

---

## Screenshots

<img width="1366" height="694" alt="image" src="https://github.com/user-attachments/assets/0e1e5ac7-9a89-4433-af17-fec00e775a9d" />

---

## Features

### Editor
- Syntax highlighting for LaTeX (commands, environments, math, comments, references)
- Multi-file tabbed editing (horizontal, vertical, or tabbed layouts)
- Line numbers and code folding markers
- Bookmarks with per-file tracking and persistent storage
- Document structure tree (parts, chapters, sections, subsections…)
- Find & Replace dialog
- Auto-completion with CWL (Completion Word List) support
- Undo / Redo

### Compilation
- One-click compilation with **pdflatex**, **xelatex**, **lualatex**, or a fully custom command
- Backmatter compilation: **BibTeX**, **Biber**, **MakeIndex**, **Xindy**, **MakeGlossaries**
- Compile / Stop toggle button — no frozen UI during long builds
- Auto-refresh PDF after successful compilation
- Clickable log-file link in the output pane
- Automatic jump to the first error line in the editor
- Hang detection: kills the process if LaTeX waits for interactive input
- Configurable compilation timeout

### PDF Viewer
- Built-in PDF viewer with zoom control
- SyncTeX forward search (jump from editor line to PDF page)
- Recent PDF files list

### Arabic & RTL Support
- Full right-to-left interface mode
- Arabic command insertion dialog
- Bilingual (Arabic + English) text insertion tool
- RTL/LTR toggle per editor

### UI & Customisation
- Light, Dark, and Midnight themes (Dark/Midnight require `qdarkstyle`)
- Switchable UI language: **English** and **Arabic** (hot-swap, no restart needed)
- Configurable editor font and UI font (family + size)
- Dockable/toggleable panels: Symbols, LaTeX Commands, Document Tree, Bookmarks, Terminal
- Switchable layout: editor left / editor right
- Editor layout modes: tabbed, horizontal split, vertical split

### Other
- Single-instance guard — opens files in the running instance instead of launching a new one
- Session restore — reopens files from the last session
- Recent files list (up to 100 entries)
- Persistent settings stored in a platform-appropriate INI file
- Math symbol panel with icon buttons and tooltips
- LaTeX command panel with categorised command buttons

---

## Requirements

| Dependency | Version | Notes |
|---|---|---|
| Python | 3.8+ | |
| PyQt5 | 5.15+ | Core UI framework |
| PyQt5-sip | latest | Required by PyQt5 |
| qdarkstyle | 3.x | Optional — Dark/Midnight themes |
| A LaTeX distribution | any | TeX Live, MiKTeX, or MacTeX |

Install Python dependencies:

```bash
pip install PyQt5 PyQt5-sip
# Optional: dark theme support
pip install qdarkstyle
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/ayntex.git
cd ayntex

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

### Requirements file

```text
PyQt5>=5.15
PyQt5-sip
qdarkstyle>=3.0   # optional
```

---

## Project Structure

```
ayntex/
├── main.py                             # Application entry point
├── main_window.py                      # Main application window and integration hub
├── app_info.py                         # App metadata (name, version, paths)
├── config_manager.py                   # INI/QSettings persistence and configuration handling
├── settings_manager.py                 # Settings dialog and preferences UI
├── compilation_manager.py              # LaTeX compilation and process management
├── backmatter_compile.py               # Backmatter/Bibliography compilation helpers
├── bibtex_manager.py                   # BibTeX bibliography management
├── toolbar_manager.py                  # Toolbars, symbol panels, and quick actions
├── menu_manager.py                     # Menu bar and actions
├── layout_manager.py                   # Splitter and workspace layout management
├── side_panel.py                       # Dockable side panels and navigation widgets
├── editor_manager.py                   # Multi-tab editor handling
├── context_menu.py                     # Custom editor context menus
├── search_replace_dialog.py            # Find & Replace dialog
├── latex_highlighter.py                # LaTeX syntax highlighting
├── latex_completer_manager.py          # Auto-completion engine integration
├── cwl_manager.py                      # CWL completion file management
├── completion_settings_widget.py       # Completion settings UI widget
├── spell_checker.py                    # Spell checking integration
├── spell_worker.py                     # Background spell checking worker
├── file_watcher.py                     # External file modification monitoring
├── bookmarks_manager.py                # Bookmark management for editor/PDF navigation
├── pdf_manager.py                      # PDF synchronization and viewer coordination
├── pdf_viewer.py                       # Embedded PDF viewer widget
├── pdf_comparison.py                   # Compare rendered PDF outputs
├── djvu_tab.py                         # DjVu document viewing tab
├── latex_comparator.py                 # Compare LaTeX source documents
├── icons_manager.py                    # Icon loading, theming, and generation
├── style_manager.py                    # Theme and stylesheet management
├── translations.py                     # UI translations and localization strings
├── translations_database.py            # Translation database utilities
├── single_instance.py                  # Single-instance protection (QLocalServer)
├── terminal_widget.py                  # Embedded terminal widget
├── calculator_widget.py                # Built-in calculator widget
├── todo_list.py                        # Task and TODO management panel
├── tip_day.py                          # Tip-of-the-day system
├── feedback.py                         # User feedback/reporting utilities
├── help_manager.py                     # Help system and documentation access
├── insert_character.py                 # Special character insertion utilities
├── arabic_command_dialog.py            # Arabic LaTeX command insertion dialog
├── math_symbols_menu.py                # Mathematical symbol definitions/menu
├── latex_commands_menu.py              # LaTeX command definitions/menu
├── latex_document_wizard.py            # New LaTeX document/project wizard
├── spreadsheet_tab.py                  # Spreadsheet/data editing tab
├── tikz_plotter_tab.py                 # TikZ plotting and preview tab
├── tools_tab.py                        # Multi-tool utilities tab
├── ai_tab.py                           # AI assistant integration tab
├── ai_widget_lite.py                   # Lightweight AI interaction widget
├── online_ai_provider.py               # Online AI backend/provider interface
├── knowledge_database_integration.py   # Knowledge database integration layer
├── katex_loader.py                     # KaTeX loading and rendering utilities
├── test.py                             # Development/testing script
├── cwl/                                # CWL auto-completion definition files
├── icons/                              # Application icons and UI assets
├── katex/                              # Local KaTeX distribution
│   ├── contrib/                        # KaTeX contributed extensions
│   └── fonts/                          # KaTeX font assets
├── plugins/                            # Plotting and data visualization plugins
│   ├── __init__.py                     # Plugin package initializer
│   ├── barplot_plugin.py               # Bar plot generator
│   ├── bilinear_patch_plugin.py        # Bilinear patch visualization plugin
│   ├── boxplot_plugin.py               # Box plot generator
│   ├── contour_quiver_plugin.py        # Contour and vector field plotting
│   ├── errorbar_plugin.py              # Error bar plotting plugin
│   ├── function_plugin.py              # Function plotting plugin
│   ├── graph_drawing_plugin.py         # Graph drawing and visualization
│   ├── heatmap_plugin.py               # Heatmap visualization plugin
│   ├── histogram_plugin.py             # Histogram generator
│   ├── lineplot_plugin.py              # Line plot generator
│   ├── numerical_data_plugin.py        # Numerical dataset processing plugin
│   ├── piechart_plugin.py              # Pie chart generator
│   ├── polar_plugin.py                 # Polar coordinate plotting
│   ├── scatter_plugin.py               # Scatter plot generator
│   ├── stacked_area_plugin.py          # Stacked area chart generator
│   ├── surface3d_plugin.py             # 3D surface plotting plugin
│   └── surface_data_plugin.py          # Surface dataset utilities
└── tips/                               # Tip-of-the-day content files
```

---

## Configuration

AynTex stores its configuration in a platform-appropriate location:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\AynTex\config.ini` |
| macOS | `~/Library/Application Support/AynTex/config.ini` |
| Linux | `~/.config/AynTex/config.ini` |

The INI file is human-readable. Engine names are always stored in English (`pdflatex`, `xelatex`, etc.) regardless of the UI language.

---

## Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| New file | Ctrl+N |
| Open file | Ctrl+O |
| Save | Ctrl+S |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y |
| Find / Replace | Ctrl+F |
| Compile | F5 |
| Stop compilation | F5 (while compiling) |
| Refresh PDF | F6 |
| SyncTeX jump to PDF | F7 |
| Backmatter compile | F9 |
| Toggle toolbar | F10 |
| Toggle bookmark | F11 |

---

## Arabic / Bilingual Workflow

AynTex is designed to make Arabic LaTeX documents as smooth as possible:

1. Set the UI language to **Arabic** in Settings → Interface.
2. Enable RTL mode to flip the editor text alignment.
3. Use the **Arabic Command** toolbar button to insert formatted Arabic text blocks.
4. Use the **Bilingual** tool to insert mixed Arabic/English passages with proper directionality.
5. Choose **XeLaTeX** or **LuaLaTeX** as your engine (both handle Unicode and Arabic fonts natively).

A minimal Arabic document preamble:

```latex
\documentclass{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{arabic}
\setotherlanguage{english}
\newfontfamily\arabicfont{Amiri}[Script=Arabic]
\begin{document}
مرحباً بالعالم
\end{document}
```

---

## Adding a Custom Compilation Command

In Settings → Compiler, select **Custom** as the engine and enter your command using the available placeholders:

| Placeholder | Expands to |
|---|---|
| `%f` | Full filename (`document.tex`) |
| `%b` | Basename without extension (`document`) |
| `%d` | Directory path |

Examples:

```bash
# Full BibTeX cycle
pdflatex %f && bibtex %b && pdflatex %f && pdflatex %f

# LaTeX → DVI → PS → PDF
latex %f && dvips %b.dvi && ps2pdf %b.ps

# LuaLaTeX with shell escape
lualatex --shell-escape %f
```

---

## Single Instance Behaviour

If you try to open AynTex a second time while it is already running:

- The second process forwards any file arguments to the first instance and exits immediately.
- The running instance opens the file and brings its window to the front.
- No duplicate windows, no data loss.

---

## Contributing

Contributions are welcome. Please open an issue first to discuss major changes.

```bash
# Fork and clone
git clone https://github.com/your-username/ayntex.git

# Create a feature branch
git checkout -b feature/your-feature

# Commit and push
git commit -m "Add your feature"
git push origin feature/your-feature

# Open a Pull Request
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [PyQt5](https://riverbankcomputing.com/software/pyqt/) — Qt bindings for Python
- [TeX Live](https://www.tug.org/texlive/) / [MiKTeX](https://miktex.org/) — LaTeX distributions
- [SyncTeX](https://github.com/jlaurens/synctex) — Source↔PDF synchronisation
- [Polyglossia](https://ctan.org/pkg/polyglossia) — Multilingual LaTeX support
- [Amiri Font](https://www.amirifont.org/) — Arabic typeface
