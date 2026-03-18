"""
app.py — Servidor web local para validación visual de facturas
Ejecutar con: python app.py
Luego abrir: http://localhost:5000
"""

import json
import os
import shutil
import csv
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ESTADO_FILE = BASE_DIR / "estado.json"

app = Flask(__name__, static_folder="static", template_folder="templates")

def cargar_estado() -> list[dict]:
    if not ESTADO_FILE.exists():
        return []
    try:
        with open(ESTADO_FILE, encoding="utf-8") as f:
            contenido = f.read().strip()
        # Si hay contenido duplicado, quedarse solo con el primer JSON válido
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(contenido)
        return data
    except Exception as e:
        print(f"[!] Error leyendo estado.json: {e}")
        return []


def guardar_estado(facturas: list[dict]):
    # Limpiar caracteres de control inválidos del texto OCR
    import re
    def limpiar(obj):
        if isinstance(obj, str):
            return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', obj)
        if isinstance(obj, dict):
            return {k: limpiar(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [limpiar(i) for i in obj]
        return obj

    facturas_limpias = limpiar(facturas)
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(facturas_limpias, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    facturas = cargar_estado()
    total     = len(facturas)
    con_error = sum(1 for f in facturas if f.get("confianza") == "baja")
    especiales = sum(1 for f in facturas if f.get("especial"))
    return render_template("index.html",
                           facturas=facturas,
                           total=total,
                           con_error=con_error,
                           especiales=especiales)


@app.route("/api/facturas")
def api_facturas():
    return jsonify(cargar_estado())


@app.route("/api/actualizar/<int:factura_id>", methods=["POST"])
def actualizar(factura_id: int):
    """Actualiza los campos de una factura (desde la UI)."""
    facturas = cargar_estado()
    data = request.json

    for f in facturas:
        if f["id"] == factura_id:
            if "numero_factura" in data:
                f["numero_factura"] = data["numero_factura"]
                f["nombre_final"] = f"{data['numero_factura']}.pdf"
            if "codigo_cliente" in data:
                f["codigo_cliente"] = data["codigo_cliente"]
            if "fecha" in data:
                f["fecha"] = data["fecha"]
            if "especial" in data:
                f["especial"] = data["especial"]
            if "excluir" in data:
                f["excluir"] = data["excluir"]
            f["confianza"] = "corregida"
            break

    guardar_estado(facturas)
    return jsonify({"ok": True})


@app.route("/api/confirmar", methods=["POST"])
def confirmar():
    """
    Renombra y mueve todos los archivos aprobados a /output/
    Estructura: output/CODIGO_CLIENTE/FECHA/NUMERO.pdf
    """
    facturas = cargar_estado()
    resultados = []

    for f in facturas:
        if f.get("excluir"):
            resultados.append({"id": f["id"], "estado": "excluida"})
            continue

        origen = Path(f["archivo_temp"])
        if not origen.exists():
            resultados.append({"id": f["id"], "estado": "archivo_no_encontrado"})
            continue

        codigo = f.get("codigo_cliente") or "SIN_CLIENTE"
        fecha  = f.get("fecha") or "SIN_FECHA"
        nombre = f.get("nombre_final") or f"factura_{f['id']}.pdf"

        # Carpeta destino: output/CODIGO/YYYY-MM/
        destino_dir = OUTPUT_DIR
        destino_dir.mkdir(parents=True, exist_ok=True)

        destino = destino_dir / nombre

        # Evitar sobrescritura
        if destino.exists():
            base = nombre.replace(".pdf", "")
            destino = destino_dir / f"{base}_dup.pdf"

        shutil.copy2(str(origen), str(destino))
        f["archivo_final"] = str(destino)
        f["procesada"] = True
        resultados.append({
            "id": f["id"],
            "estado": "ok",
            "destino": str(destino),
            "especial": f.get("especial", False)
        })

    guardar_estado(facturas)

    ok      = sum(1 for r in resultados if r["estado"] == "ok")
    errores = [r for r in resultados if r["estado"] not in ("ok", "excluida")]

    # Generar CSV con los datos finales confirmados
    csv_path = OUTPUT_DIR / "resumen_facturas.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "numero_factura", "codigo_cliente", "fecha", "nombre_final"
        ])
        writer.writeheader()
        for fac in facturas:
            if not fac.get("excluir"):
                writer.writerow({
                    "numero_factura": fac.get("numero_factura", ""),
                    "codigo_cliente": fac.get("codigo_cliente", ""),
                    "fecha":          fac.get("fecha", ""),
                    "nombre_final":   fac.get("nombre_final", "")
                })

    return jsonify({
        "ok": True,
        "procesadas": ok,
        "excluidas": sum(1 for r in resultados if r["estado"] == "excluida"),
        "errores": errores,
        "output_dir": str(OUTPUT_DIR)
    })


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


def abrir_navegador():
    webbrowser.open("http://localhost:5000")

@app.route("/api/unir", methods=["POST"])
def unir():
    """
    Une dos páginas en un solo PDF.
    La nota se agrega al final de la factura principal.
    La nota queda marcada como excluida.
    """
    data = request.json
    id_factura = data.get("id_factura")  # La factura principal
    id_nota    = data.get("id_nota")     # La nota que se une

    facturas = cargar_estado()

    factura = next((f for f in facturas if f["id"] == id_factura), None)
    nota    = next((f for f in facturas if f["id"] == id_nota), None)

    if not factura or not nota:
        return jsonify({"ok": False, "error": "Factura o nota no encontrada"})

    archivo_factura = Path(factura["archivo_temp"])
    archivo_nota    = Path(nota["archivo_temp"])

    if not archivo_factura.exists() or not archivo_nota.exists():
        return jsonify({"ok": False, "error": "Archivos temporales no encontrados"})

    try:
        import fitz

        # Abrir ambos PDFs
        doc_factura = fitz.open(str(archivo_factura))
        doc_nota    = fitz.open(str(archivo_nota))

        # Insertar la nota al final de la factura
        doc_factura.insert_pdf(doc_nota)
        doc_nota.close()

        # Guardar en archivo temporal primero, luego reemplazar
        temp_path = archivo_factura.parent / f"_temp_union_{archivo_factura.name}"
        doc_factura.save(str(temp_path))
        doc_factura.close()

        # Reemplazar el original con el fusionado
        import os
        os.replace(str(temp_path), str(archivo_factura))

        # Marcar la nota como excluida
        for f in facturas:
            if f["id"] == id_nota:
                f["excluir"] = True
                f["unida_con"] = factura["nombre_final"]

        guardar_estado(facturas)
        return jsonify({
            "ok": True,
            "mensaje": f"Nota unida a {factura['nombre_final']}"
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
    
if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    if not ESTADO_FILE.exists():
        print("[!] No hay facturas procesadas. Ejecuta primero: python pipeline.py archivo.pdf")
    else:
        Timer(1.2, abrir_navegador).start()
        print("[✓] Abriendo interfaz en http://localhost:5000")
        print("    Presiona Ctrl+C para cerrar")
    app.run(debug=False, port=5000)
