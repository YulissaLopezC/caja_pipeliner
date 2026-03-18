# Procesador de Caja Diaria

Sistema automático para extraer, validar y organizar facturas desde el PDF de caja diaria.

---

## Estructura del proyecto

```
caja_v2/
├── run.py                  ← Lanzador principal (empieza aquí)
├── pipeline.py             ← Motor OCR y separación de PDF
├── app.py                  ← Servidor web de validación visual
├── gmail_watcher.py        ← Descarga automática desde Gmail
├── drive_uploader.py       ← Subida a Google Drive
├── instalador.bat          ← Instalación automática en PC nuevo
├── iniciar.bat             ← Acceso directo para uso diario
│
├── credentials/            ← Credenciales de Google (NO subir a GitHub)
│   └── gmail_credentials.json
│
├── temp/                   ← Páginas temporales (se borran solas)
├── output/                 ← Facturas renombradas + resumen_facturas.csv
├── static/previews/        ← Miniaturas para la interfaz (se regeneran solas)
└── templates/index.html    ← Interfaz de validación visual
```

---

## Instalación en PC nuevo

### Paso 1 — Instalar Python
- Descarga desde: https://www.python.org/downloads/
- ⚠️ Durante la instalación marca: **Add Python to PATH**
- Verifica: `python --version`

### Paso 2 — Instalar Tesseract OCR
- Descarga desde: https://github.com/UB-Mannheim/tesseract/wiki
- Durante la instalación marca el idioma: **Spanish**
- Busca la ruta del ejecutable:
```
where /r C:\ tesseract.exe
```
- Agrega esa carpeta al PATH de Windows
- Descarga el idioma español desde:
  https://github.com/tesseract-ocr/tessdata/blob/main/spa.traineddata
- Guarda `spa.traineddata` en la carpeta `tessdata` de Tesseract
- Verifica: `tesseract --version`

### Paso 3 — Instalar Poppler
- Descarga desde: https://github.com/oschwartz10612/poppler-windows/releases
- Extrae en `C:\poppler\` → debe quedar: `C:\poppler\poppler-XX.XX.X\Library\bin\`
- Agrega esa ruta al PATH de Windows
- Verifica: `pdftoppm -v`

### Paso 4 — Ejecutar el instalador
- Extrae el proyecto en `C:\` (no dentro de OneDrive)
- Doble clic en `instalador.bat`
- Crea el entorno virtual e instala todas las librerías automáticamente

### Paso 5 — Configurar rutas en pipeline.py
Abre `pipeline.py` con el Bloc de notas y actualiza estas dos líneas:

```python
TESSERACT_CMD = r"C:\ruta\a\tesseract.exe"
POPPLER_PATH  = r"C:\poppler\poppler-XX.XX.X\Library\bin"
```

El instalador te muestra la ruta correcta de Tesseract al finalizar.

---

## Uso diario

**La forma más simple — doble clic en `iniciar.bat`:**
1. Arrastra el PDF de la caja a la ventana negra
2. Presiona Enter
3. Se abre el navegador con la interfaz de validación
4. Revisa las facturas, corrige las que tengan ⚠
5. Haz clic en **Confirmar y mover archivos**

**O desde CMD (con el entorno virtual activo):**
```
cd C:\caja_v2
venv\Scripts\activate
python run.py --pdf "C:\ruta\al\CAJA_16-03-2026.pdf"
```

Para subir a Drive después de confirmar:
```
python run.py --subir
```

---

## Interfaz de validación (http://localhost:5000)

- **Franja verde** = OCR leyó todo correctamente
- **Franja naranja** = falta algún dato, revisar manualmente
- **Franja azul** = corregida manualmente

Acciones disponibles:
- Editar número de factura, código de cliente o fecha directamente
- **★ Especial** — marcar facturas para identificarlas fácilmente
- **✕ Excluir** — excluir páginas que no son facturas de venta
- Zoom — clic sobre la imagen para verla al 100%
- **Confirmar y mover archivos** — mueve todo a `/output/`

---

## Archivos generados en /output/

```
output/
├── H948.pdf
├── H949.pdf
├── H950.pdf
└── resumen_facturas.csv    ← Resumen con número, cliente, fecha y nombre
```

---

## Configuración de Gmail (una sola vez)

1. Ve a https://console.cloud.google.com/
2. Crea un proyecto → busca **Gmail API** → Habilitar
3. Credenciales → **+ Crear credencial** → **ID de cliente OAuth 2.0**
4. Tipo: **Aplicación de escritorio**
5. Descarga el JSON → guárdalo como `credentials/gmail_credentials.json`
6. Ejecuta:
```
python gmail_watcher.py --setup
```
7. Se abre el navegador → acepta los permisos

---

## Configuración de Google Drive (una sola vez)

La conexión con Drive usa las mismas credenciales de Gmail (OAuth2).

1. Agrega el permiso de Drive en `gmail_watcher.py`:
```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive"
]
```
2. Borra el token anterior: `del credentials\token.pickle`
3. Vuelve a autorizar: `python gmail_watcher.py --setup`
4. En `drive_uploader.py` verifica:
   - `CARPETA_RAIZ_NOMBRE` = nombre exacto de tu carpeta raíz en Drive
   - `AÑO_CARPETA` = año actual (ej: "2026")
   - Las carpetas de clientes deben llamarse `CODIGO_NombreCliente` (ej: `9_Lanis Grill`)

---

## Ajustes importantes en pipeline.py

```python
RESUMEN_PAGES = 2     # Páginas de resumen al inicio del PDF (se omiten)
TESSERACT_CMD = r"..."  # Ruta a tesseract.exe
POPPLER_PATH  = r"..."  # Ruta a la carpeta bin de Poppler
```

---

## Notas importantes

- El proyecto **no debe estar dentro de OneDrive** — causa errores de permisos
- El `venv/` no es portable entre PCs — siempre recrearlo con `instalador.bat`
- Las credenciales de Google son únicas por cuenta — configurarlas en cada PC
- `temp/` y `static/previews/` se limpian solas con cada ejecución
- `output/` se acumula — bórrala después de confirmar que las facturas están en Drive

---

## Solución de problemas

| Problema | Solución |
|---|---|
| Ventana se cierra sola | Usar `iniciar.bat` — tiene `pause` al final |
| `tesseract` no reconocido | Agregar carpeta de Tesseract al PATH |
| `pdftoppm` no reconocido | Agregar carpeta bin de Poppler al PATH |
| Error de Poppler en OCR | Verificar `POPPLER_PATH` en `pipeline.py` |
| `ModuleNotFoundError` | Activar entorno virtual: `venv\Scripts\activate` |
| `PermissionError` en temp | El proyecto está dentro de OneDrive — moverlo a `C:\` |
| `pipeline.py` vacío | Volver a descargar el ZIP original |
| Muestra facturas anteriores | Borrar `estado.json` y procesar PDF nuevo |
| Entorno virtual roto | Borrar carpeta `venv\` y ejecutar `instalador.bat` |