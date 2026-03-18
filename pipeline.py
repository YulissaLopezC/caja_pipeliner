"""
pipeline.py — Motor principal del procesador de cajas diarias
Extrae facturas del PDF, aplica OCR y lanza la interfaz de validación.
"""

import os
import re
import json
import shutil
import subprocess
import sys
import csv
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
TEMP_DIR   = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"
STATIC_DIR = BASE_DIR / "static"

# Ajusta esta ruta si Tesseract está en otro lugar
TESSERACT_CMD = r"C:\Users\yulis\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

RESUMEN_PAGES = 2  # Las primeras N páginas son resumen de caja (se omiten)


# ── Limpieza ───────────────────────────────────────────────────────────────────

def limpiar_temp():
    if TEMP_DIR.exists():
        for archivo in TEMP_DIR.iterdir():
            try:
                archivo.unlink()
            except:
                pass
        try:
            TEMP_DIR.rmdir()
        except:
            pass
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "previews").mkdir(parents=True, exist_ok=True)


# ── Separación del PDF ─────────────────────────────────────────────────────────

def separar_paginas(pdf_path: str) -> list:
    """Extrae cada página de factura como PDF individual en TEMP_DIR."""
    doc = fitz.open(pdf_path)
    total = len(doc)
    paginas = []

    for i in range(RESUMEN_PAGES, total):
        nuevo = fitz.open()
        nuevo.insert_pdf(doc, from_page=i, to_page=i)
        dest = TEMP_DIR / f"pagina_{i+1:03d}.pdf"
        nuevo.save(dest)
        nuevo.close()
        paginas.append(dest)

    doc.close()
    print(f"[✓] PDF separado: {len(paginas)} facturas encontradas (omitidas {RESUMEN_PAGES} páginas de resumen)")
    return paginas


# ── OCR ────────────────────────────────────────────────────────────────────────

def _texto_directo(pdf_path: Path) -> str:
    """Intenta extracción directa de texto (rápida)."""
    doc = fitz.open(str(pdf_path))
    texto = doc[0].get_text()
    doc.close()
    return texto.strip()


def _texto_ocr(pdf_path: Path) -> str:
    """OCR con Tesseract sobre imagen de alta resolución."""
    imgs = convert_from_path(str(pdf_path), dpi=300, poppler_path=POPPLER_PATH)
    if not imgs:
        return ""
    img = imgs[0].convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    return pytesseract.image_to_string(img, lang="spa", config="--psm 6")


def extraer_texto(pdf_path: Path) -> str:
    texto = _texto_directo(pdf_path)
    if len(texto) > 80:
        return texto
    return _texto_ocr(pdf_path)


# ── Parseo de campos ───────────────────────────────────────────────────────────

def parsear_factura(texto: str) -> dict:
    """Extrae número de factura, código de cliente y fecha del texto OCR."""
    resultado = {
        "numero_factura": None,
        "codigo_cliente": None,
        "fecha": None,
        "confianza": "alta"
    }

    # Número de factura: "Factura: H948"
    m = re.search(r"[Ff]actura\s*[:\-]?\s*(H\d+)", texto)
    if m:
        resultado["numero_factura"] = m.group(1).strip()

    # Código de cliente: "Codi Client: 9"
    m = re.search(r"[Cc]odi\s+[Cc]lient\s*[:\-]?\s*(\d+)", texto)
    if m:
        resultado["codigo_cliente"] = m.group(1).strip()

    # Fecha: "Fecha: 16-03-2026"
    m = re.search(r"[Ff]echa\s*[:\-]?\s*(\d{1,2}[\-/]\d{2}[\-/]\d{4})", texto)
    if m:
        raw = m.group(1).replace("/", "-")
        try:
            dt = datetime.strptime(raw, "%d-%m-%Y")
            resultado["fecha"] = dt.strftime("%Y-%m-%d")
        except ValueError:
            resultado["fecha"] = raw

    # Marcar confianza baja si faltan campos
    faltantes = [k for k, v in resultado.items() if v is None and k != "confianza"]
    if faltantes:
        resultado["confianza"] = "baja"
        resultado["faltantes"] = faltantes

    return resultado


# ── Miniatura para la vista previa ─────────────────────────────────────────────

def generar_preview(pdf_path: Path, nombre: str) -> str:
    """Genera PNG de preview y lo guarda en static/previews/."""
    imgs = convert_from_path(str(pdf_path), dpi=120, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
    if not imgs:
        return ""
    dest = STATIC_DIR / "previews" / f"{nombre}.png"
    imgs[0].save(dest, "PNG")
    return f"previews/{nombre}.png"


# ── Procesamiento completo ─────────────────────────────────────────────────────

def procesar_pdf(pdf_path: str) -> list:
    """Pipeline completo: separa → OCR → parsea → genera previews."""
    limpiar_temp()
    paginas = separar_paginas(pdf_path)
    facturas = []

    for i, pagina in enumerate(paginas):
        print(f"  Procesando página {i+1}/{len(paginas)}: {pagina.name}", end=" ")
        texto = extraer_texto(pagina)
        datos = parsear_factura(texto)

        nombre_temp = pagina.stem
        preview = generar_preview(pagina, nombre_temp)

        factura = {
            "id": i,
            "archivo_temp": str(pagina),
            "preview": preview,
            "texto_ocr": texto[:500],
            **datos,
            "nombre_final": f"{datos['numero_factura']}.pdf" if datos["numero_factura"] else f"SIN_NUMERO_{i+1}.pdf",
            "especial": False,
            "excluir": False,
        }
        facturas.append(factura)
        estado = "✓" if datos["confianza"] == "alta" else "⚠"
        print(f"[{estado}] → {factura['nombre_final']}")

    # Guardar estado JSON
    estado_path = BASE_DIR / "estado.json"
    with open(estado_path, "w", encoding="utf-8") as f:
        json.dump(facturas, f, ensure_ascii=False, indent=2)

    # Generar CSV resumen
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / "resumen_facturas.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "numero_factura", "codigo_cliente", "fecha", "nombre_final"
        ])
        writer.writeheader()
        for fac in facturas:
            writer.writerow({
                "numero_factura": fac.get("numero_factura", ""),
                "codigo_cliente": fac.get("codigo_cliente", ""),
                "fecha":          fac.get("fecha", ""),
                "nombre_final":   fac.get("nombre_final", "")
            })

    print(f"\n[✓] {len(facturas)} facturas procesadas")
    print(f"[✓] CSV generado en {csv_path}")
    print(f"[✓] Estado guardado en {estado_path}")
    return facturas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pipeline.py ruta/al/archivo.pdf")
        sys.exit(1)

    pdf = sys.argv[1]
    if not os.path.exists(pdf):
        print(f"[✗] No se encuentra el archivo: {pdf}")
        sys.exit(1)

    procesar_pdf(pdf)
    print("\nAhora ejecuta: python app.py")
