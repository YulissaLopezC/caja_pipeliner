@echo off
if "%1"=="" (
    cmd /k "%~f0" run
    exit /b
)
cd /d "%~dp0"
call venv\Scripts\activate
echo.
echo  ================================
echo   PROCESADOR DE CAJA DIARIA
echo  ================================
echo.
echo  Arrastra el PDF aqui y presiona Enter:
set /p PDF="PDF: "
set PDF=%PDF:"=%
echo.
python run.py --pdf "%PDF%"
echo.
pause
