@echo off
echo Building FontEase...

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Install requirements if needed
pip install -r requirements.txt

REM Build the executable with proper module imports
pyinstaller --clean --onefile --windowed --icon=assets\icon.ico --name="FontEase" ^
            --add-data "assets;assets" ^
            --add-data "LICENSE;." ^
            --hidden-import="src.core" ^
            --hidden-import="src.models" ^
            --hidden-import="src.ui" ^
            --hidden-import="src.utilities" ^
            --version-file=version_info.txt ^
            src\main.py

echo Build completed. Executable is in the dist directory.
pause