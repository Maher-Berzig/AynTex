REM build
pyinstaller ^
    --clean ^
    --noconsole ^
    --noconfirm ^
    --name "Ayntex" ^
    --icon="icons/ayntexlogo.ico" ^
    --hidden-import=fitz ^
    --exclude-module PySide2 ^
    --exclude-module PySide2.QtCore ^
    --exclude-module PySide2.QtWidgets ^
    --add-data "cwl;cwl" ^
    --add-data "plugins;plugins" ^
    --add-data "tips;tips" ^
    --add-data "icons;icons" ^
    --add-data "katex;katex" ^
    --add-data "D050000L.otf;." ^
    --add-data "FontAwesome.otf;." ^
    --add-data "STIXTwoMath-Regular.otf;." ^
    --add-data "C:\PySchool\3.10-32-bit\Lib\site-packages\spellchecker\resources;spellchecker\resources" ^
    --add-binary "libdjvulibre.dll;." ^
    --add-binary "libdjvulibre-21.dll;." ^
    --add-binary "libgcc_s_seh-1.dll;." ^
    --add-binary "libjpeg.dll;." ^
    --add-binary "libstdc++-6.dll;." ^
    --add-binary "libtiff.dll;." ^
    --add-binary "libwinpthread-1.dll;." ^
    --add-binary "libz.dll;." ^
    --add-binary "ddjvu.exe;." ^
    --add-binary "djvused.exe;." ^
    --add-binary "djvutxt.exe;." ^
    main.py


REM REM The following code lines serve to move subfolders (cwl, icons, plugins, tips, katex) from SRC_BASE to DST_BASE:
@echo off
set SRC_BASE=%CD%\dist\Ayntex\_internal
set DST_BASE=%CD%\dist\Ayntex
set RETRIES=30
set SLEEP=1

:TRY_MOVE
robocopy "%SRC_BASE%\cwl"  "%DST_BASE%\cwl"  /E /MOVE /R:0 /W:0 /NFL /NDL /NJH /NJS /NC /NS
if %ERRORLEVEL% LEQ 7 goto NEXT1
timeout /T %SLEEP% /NOBREAK >nul
set /A RETRIES-=1
if %RETRIES% GTR 0 goto TRY_MOVE
echo Failed moving cwl — directory busy or access denied
exit /b 1
:NEXT1

robocopy "%SRC_BASE%\icons" "%DST_BASE%\icons" /E /MOVE /R:0 /W:0 /NFL /NDL /NJH /NJS /NC /NS
if %ERRORLEVEL% GTR 7 (
  echo Failed moving icons
  exit /b 1
)

robocopy "%SRC_BASE%\plugins" "%DST_BASE%\plugins" /E /MOVE /R:0 /W:0 /NFL /NDL /NJH /NJS /NC /NS
if %ERRORLEVEL% GTR 7 (
  echo Failed moving plugins
  exit /b 1
)

robocopy "%SRC_BASE%\tips" "%DST_BASE%\tips" /E /MOVE /R:0 /W:0 /NFL /NDL /NJH /NJS /NC /NS
if %ERRORLEVEL% GTR 7 (
  echo Failed moving tips
  exit /b 1
)

robocopy "%SRC_BASE%\katex" "%DST_BASE%\katex" /E /MOVE /R:0 /W:0 /NFL /NDL /NJH /NJS /NC /NS
if %ERRORLEVEL% GTR 7 (
  echo Failed moving katex
  exit /b 1
)

echo Move completed successfully.
