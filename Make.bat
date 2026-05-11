REM build
pyinstaller --clean --noconsole --noconfirm --exclude-module PySide2 --exclude-module PySide2.QtCore --exclude-module PySide2.QtWidgets --add-data "C:/AynTex/cwl;cwl" --add-data "C:/AynTex/plugins;plugins" --add-data "C:/AynTex/tips;tips" --add-data "C:/AynTex/icons;icons" --add-data "C:/AynTex/katex;katex" --add-binary "C:/AynTex/libdjvulibre.dll;." --add-binary "C:/AynTex/libdjvulibre-21.dll;." --add-binary "C:/AynTex/libgcc_s_seh-1.dll;." --add-binary "C:/AynTex/libjpeg.dll;." --add-binary "C:/AynTex/libstdc++-6.dll;." --add-binary "C:/AynTex/libtiff.dll;." --add-binary "C:/AynTex/libwinpthread-1.dll;." --add-binary "C:/AynTex/libz.dll;." --add-binary "C:/AynTex/ddjvu.exe;." --add-binary "C:/AynTex/djvused.exe;." --add-binary "C:/AynTex/djvutxt.exe;." --icon="C:/AynTex/AynTexlogo.ico" --add-data "C:/AynTex/D050000L.otf;." --add-data "C:/AynTex/FontAwesome.otf;." --add-data "C:/AynTex/STIXTwoMath-Regular.otf;." --name "Ayntex" main.py


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
