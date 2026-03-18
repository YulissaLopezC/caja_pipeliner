"""
app.py — Servidor web local para validación visual de facturas
Ejecutar con: python app.py
Luego abrir: http://localhost:5000
"""

import json
import os
import shutil
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
    with open(ESTADO_FILE, encoding="utf-8") as f:
        return json.load(f)


def guardar_estado(facturas: list[dict]):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(facturas, f, ensure_ascii=False, indent=2)


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


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    if not ESTADO_FILE.exists():
        print("[!] No hay facturas procesadas. Ejecuta primero: python pipeline.py archivo.pdf")
    else:
        Timer(1.2, abrir_navegador).start()
        print("[✓] Abriendo interfaz en http://localhost:5000")
        print("    Presiona Ctrl+C para cerrar")
    app.run(debug=False, port=5000)
