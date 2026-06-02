# Changelog

v1.1
## [1.1] - 2026-06-02

### Fixed

#### File watching
- Fixed false "File modified on disk" warnings after saving files.
- Fixed incorrect detection of external file changes.
- Improved reliability of file change monitoring across platforms.

#### Editor
- Fixed cursor and scroll position jumping after saving.
- Improved editor stability during compilation.
- Recent Files menu now closes automatically.
- Fixed Highlighter color of the comments.

### Menu
- Creates a copy of the current document under a new name without changing the active file.

#### Compilation
- Fixed PDF viewer not updating after successful compilation.
- Fixed stale PDF content being displayed.
- Fixed cursor position changes after compilation.

#### PDF Viewer
- Fixed scroll position being lost when PDFs were refreshed.
- Fixed page and zoom spinboxes sometimes becoming unresponsive.
- Fixed focus handling issues inside PDF tabs.
- Fixed Alt+Left and Alt+Right navigation errors.
- Improved PDF reload behavior and navigation stability.

### Improved
- Better preservation of editor state during UI updates.
- More reliable automatic PDF refreshing.
- Improved focus management throughout the application.

v1.0
## [1.0] - 2026-05-11
-   Initial release