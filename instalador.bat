@echo off
if "%1"=="" (
    cmd /k "%~f0" run
    exit /b
)
setlocal EnableDelayedExpansion
title Instalador - Procesador de Caja Diaria
color 0F

echo.
echo  ================================================
echo   INSTALADOR - PROCESADOR DE CAJA DIARIA
echo  ================================================
echo.
echo  Este instalador configurara todo automaticamente.
echo  Necesitas conexion a internet.
echo.
pause

:: ── Verificar que NO esta en OneDrive ─────────────────────────────
echo [1/6] Verificando ubicacion del proyecto...
echo %~dp0 | findstr /i "onedrive" >nul
if %errorlevel%==0 (
    echo.
    echo  ERROR: El proyecto esta dentro de OneDrive.
    echo  Mueve la carpeta caja_pipeline a C:\ e intenta de nuevo.
    echo  Ruta actual: %~dp0
    echo.
    pause
    exit /b 1
)
echo  OK - Ubicacion correcta: %~dp0

:: ── Verificar Python ──────────────────────────────────────────────
echo.
echo [2/6] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  Python no encontrado. Abriendo pagina de descarga...
    echo.
    echo  INSTRUCCIONES:
    echo  1. Descarga Python 3.13 o superior
    echo  2. Durante la instalacion marca: "Add Python to PATH"
    echo  3. Cierra esta ventana y vuelve a ejecutar instalador.bat
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo  OK - %PYVER% encontrado

:: ── Verificar Tesseract ───────────────────────────────────────────
echo.
echo [3/6] Verificando Tesseract OCR...
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  Tesseract no encontrado. Buscando en ubicaciones comunes...
    set TESS_PATH=
    if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
        set TESS_PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR
    )
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        set TESS_PATH=C:\Program Files\Tesseract-OCR
    )
    if "!TESS_PATH!"=="" (
        echo.
        echo  Tesseract no esta instalado.
        echo  INSTRUCCIONES:
        echo  1. Se abrira la pagina de descarga
        echo  2. Descarga el instalador .exe de Windows
        echo  3. Durante la instalacion marca el idioma: Spanish
        echo  4. Cierra esta ventana y vuelve a ejecutar instalador.bat
        echo.
        start https://github.com/UB-Mannheim/tesseract/wiki
        pause
        exit /b 1
    ) else (
        echo  Tesseract encontrado en: !TESS_PATH!
        setx PATH "%PATH%;!TESS_PATH!" /M >nul 2>&1
        set PATH=%PATH%;!TESS_PATH!
        echo  OK - Tesseract agregado al PATH
    )
) else (
    echo  OK - Tesseract encontrado
)

:: ── Verificar idioma español ──────────────────────────────────────
echo.
echo [3b] Verificando idioma espanol en Tesseract...
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tessdata\spa.traineddata" (
    echo  OK - Idioma espanol instalado
) else if exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" (
    echo  OK - Idioma espanol instalado
) else (
    echo.
    echo  Falta el archivo de idioma espanol.
    echo  INSTRUCCIONES:
    echo  1. Se abrira la pagina de descarga del archivo spa.traineddata
    echo  2. Haz clic en "Download raw file"
    echo  3. Guardalo en la carpeta tessdata de Tesseract
    echo.
    start https://github.com/tesseract-ocr/tessdata/blob/main/spa.traineddata
    pause
    exit /b 1
)

:: ── Verificar Poppler ─────────────────────────────────────────────
echo.
echo [4/6] Verificando Poppler...
pdftoppm -v >nul 2>&1
if %errorlevel% neq 0 (
    set POPPLER_BIN=
    for /d %%d in ("C:\poppler\poppler-*") do (
        if exist "%%d\Library\bin\pdftoppm.exe" (
            set POPPLER_BIN=%%d\Library\bin
        )
    )
    if "!POPPLER_BIN!"=="" (
        echo.
        echo  Poppler no esta instalado.
        echo  INSTRUCCIONES:
        echo  1. Se abrira la pagina de descarga
        echo  2. Descarga el archivo .zip mas reciente
        echo  3. Descomprimelo y mueve la carpeta a C:\poppler\
        echo.
        start https://github.com/oschwartz10612/poppler-windows/releases
        pause
        exit /b 1
    ) else (
        setx PATH "%PATH%;!POPPLER_BIN!" /M >nul 2>&1
        set PATH=%PATH%;!POPPLER_BIN!
        echo  OK - Poppler agregado al PATH
    )
) else (
    echo  OK - Poppler encontrado
)

:: ── Crear entorno virtual ─────────────────────────────────────────
echo.
echo [5/6] Creando entorno virtual Python...
cd /d "%~dp0"
if exist "venv\" (
    echo  Entorno virtual ya existe, omitiendo...
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  ERROR al crear el entorno virtual.
        pause
        exit /b 1
    )
    echo  OK - Entorno virtual creado
)

:: ── Instalar librerías ────────────────────────────────────────────
echo.
echo [6/6] Instalando librerias Python...
echo  Esto puede tardar 2-3 minutos, por favor espera...
echo.
call venv\Scripts\activate
pip install flask pymupdf pdf2image pytesseract pillow ^
    google-auth google-auth-oauthlib google-api-python-client ^
    --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo  ERROR al instalar librerias. Verifica tu conexion a internet.
    pause
    exit /b 1
)
echo  OK - Librerias instaladas

:: ── Crear carpetas necesarias ─────────────────────────────────────
echo.
echo  Creando estructura de carpetas...
if not exist "credentials\"      mkdir credentials
if not exist "output\"           mkdir output
if not exist "temp\"             mkdir temp
if not exist "static\previews\"  mkdir static\previews
echo  OK - Carpetas creadas

:: ── Mostrar ruta de Tesseract para configurar pipeline.py ─────────
echo.
echo  ================================================
echo   ACCION REQUERIDA - PASO MANUAL
echo  ================================================
echo.
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
    echo  Abre pipeline.py con el Bloc de notas y busca:
    echo  TESSERACT_CMD = r"..."
    echo.
    echo  Cambiala por:
    echo  TESSERACT_CMD = r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
) else if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo  Abre pipeline.py con el Bloc de notas y busca:
    echo  TESSERACT_CMD = r"..."
    echo.
    echo  Cambiala por:
    echo  TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
) else (
    echo  Busca la ruta de tesseract.exe con este comando en CMD:
    echo  where /r C:\ tesseract.exe
    echo  Y actualiza TESSERACT_CMD en pipeline.py
)

:: ── Resumen final ─────────────────────────────────────────────────
echo.
echo  ================================================
echo   INSTALACION COMPLETADA
echo  ================================================
echo.
echo  Uso diario:
echo  1. Doble clic en iniciar.bat
echo  2. Arrastra el PDF y presiona Enter
echo  3. Revisa facturas en el navegador
echo  4. Clic en "Confirmar y mover archivos"
echo.
pause
