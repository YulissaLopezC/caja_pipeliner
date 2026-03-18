# Procesador de Caja Diaria

Sistema automático para extraer, validar y organizar facturas desde el PDF de caja diaria.

---

## Estructura del proyecto

```
caja_pipeline/
├── run.py                  ← Lanzador principal (empieza aquí)
├── pipeline.py             ← Motor OCR y separación de PDF
├── app.py                  ← Servidor web de validación visual
├── gmail_watcher.py        ← Descarga automática desde Gmail
├── drive_uploader.py       ← Subida a Google Drive
│
├── credentials/
│   ├── gmail_credentials.json    ← OAuth2 de Gmail (tú lo descargas)
│   └── service_account.json      ← Service Account de Drive (tú lo descargas)
│
├── inbox/                  ← PDFs descargados de Gmail
├── temp/                   ← Páginas separadas (temporal)
├── output/                 ← Facturas renombradas y organizadas
├── static/previews/        ← Miniaturas para la interfaz web
└── templates/index.html    ← Interfaz de validación
```

---

## Instalación (una sola vez)

### 1. Instalar dependencias Python

```bash
pip install flask pymupdf pdf2image pytesseract pillow \
            google-auth google-auth-oauthlib \
            google-api-python-client
```

### 2. Instalar Tesseract OCR

Descarga desde: https://github.com/UB-Mannheim/tesseract/wiki

- Instala en: `C:\Program Files\Tesseract-OCR\`
- Durante la instalación, marca el idioma **Spanish (spa)**
- Verifica: abre CMD y ejecuta `tesseract --version`

### 3. Instalar Poppler (para pdf2image)

Descarga desde: https://github.com/oschwartz10612/poppler-windows/releases

- Extrae en: `C:\poppler\`
- Agrega `C:\poppler\Library\bin` a tu PATH de Windows

---

## Configuración de Gmail (una sola vez)

1. Ve a https://console.cloud.google.com/
2. Crea un proyecto nuevo → busca "Gmail API" → Habilitar
3. Ve a **Credenciales** → **+ Crear credencial** → **ID de cliente OAuth 2.0**
4. Tipo: **Aplicación de escritorio**
5. Descarga el JSON → guárdalo como `credentials/gmail_credentials.json`
6. Ejecuta: `python run.py --setup-gmail`
7. Se abrirá el navegador para autorizar el acceso → acepta

---

## Configuración de Google Drive (una sola vez)

1. En Google Cloud Console → **Credenciales** → **+ Crear credencial** → **Cuenta de servicio**
2. Dale un nombre → Crear
3. En la cuenta de servicio → pestaña **Claves** → Agregar clave → JSON
4. Guarda como `credentials/service_account.json`
5. Abre tu carpeta raíz en Drive → **Compartir** → pega el email de la cuenta de servicio
6. En `drive_uploader.py`, cambia `DRIVE_ROOT_ID` por el ID de tu carpeta:
   - Abre la carpeta en Drive → la URL tiene: `https://drive.google.com/drive/folders/ESTE_ID`

---

## Uso diario

### Opción A — Flujo completo automático (recomendado)
```bash
python run.py
```
Revisa Gmail → descarga el PDF → procesa → abre interfaz en el navegador.

### Opción B — Procesar PDF local
```bash
python run.py --pdf "C:\Descargas\CAJA_16-03-2026.pdf"
```

### Opción C — Pasos separados
```bash
# 1. Procesar el PDF
python pipeline.py "C:\Descargas\CAJA_16-03-2026.pdf"

# 2. Abrir interfaz de validación
python app.py

# 3. Después de confirmar en la interfaz, subir a Drive
python run.py --subir
```

---

## Interfaz de validación

Al ejecutar `app.py` se abre automáticamente http://localhost:5000

**Qué puedes hacer:**
- Ver miniatura de cada factura
- Corregir número, cliente o fecha si el OCR falló (campos en naranja = datos faltantes)
- Marcar facturas como **★ Especial** (para identificarlas en Drive)
- **✕ Excluir** facturas que no deben subirse (facturas de compra, abonos, etc.)
- Filtrar por estado: todas / a revisar / especiales / excluidas
- Hacer zoom en cualquier factura para verla al 100%
- **Confirmar y mover archivos** → genera los PDFs finales en `/output/`

---

## Ajustes importantes en pipeline.py

```python
RESUMEN_PAGES = 2   # Número de páginas del resumen (omitidas al separar)
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Si tu PDF tiene 3 páginas de resumen, cambia `RESUMEN_PAGES = 3`.

---

## Estructura de salida en /output/

```
output/
└── 9/
    └── 2026-03/
        └── H948.pdf
└── 54/
    └── 2026-03/
        └── H949.pdf
```

Esta misma estructura se replica en Google Drive.

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| OCR extrae texto incorrecto | Aumenta DPI en `pipeline.py`: `dpi=400` |
| No encuentra Tesseract | Verifica `TESSERACT_CMD` en `pipeline.py` |
| Error de Poppler | Verifica que `C:\poppler\Library\bin` esté en PATH |
| Gmail no encuentra correos | Cambia `dias_atras=3` en `gmail_watcher.py` |
| Carpeta Drive no encontrada | Verifica que el código de cliente coincida exactamente con el nombre de la carpeta |
