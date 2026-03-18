"""
drive_uploader.py — Sube las facturas procesadas a Google Drive
Las carpetas de clientes ya existen en Drive; este script las localiza por código.

Requisitos: pip install google-api-python-client google-auth

Uso: python drive_uploader.py
     (se ejecuta automáticamente tras confirmar en la interfaz web)
"""

import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR     = Path(__file__).parent
ESTADO_FILE  = BASE_DIR / "estado.json"
CREDS_FILE   = BASE_DIR / "credentials" / "service_account.json"

# ID de la carpeta raíz en Drive que contiene las carpetas de clientes
# Ejemplo: https://drive.google.com/drive/folders/1ABC123xyz → ID = "1ABC123xyz"
DRIVE_ROOT_ID = "TU_FOLDER_ID_AQUI"

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_service():
    creds = service_account.Credentials.from_service_account_file(
        str(CREDS_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def buscar_carpeta(service, nombre: str, parent_id: str) -> str | None:
    """Busca una carpeta por nombre dentro de un padre. Retorna su ID o None."""
    q = (
        f"name='{nombre}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and trashed=false"
    )
    res = service.files().list(q=q, fields="files(id,name)").execute()
    archivos = res.get("files", [])
    return archivos[0]["id"] if archivos else None


def subir_factura(service, local_path: str, codigo_cliente: str, nombre_archivo: str) -> dict:
    """
    Sube un archivo PDF a la carpeta del cliente en Drive.
    Las carpetas de clientes deben existir ya en DRIVE_ROOT_ID.

    Estructura esperada en Drive:
        /Facturas/
            /9 - Lanis Grill/
            /54 - Rest. Español/
            /77 - Pub The Harp/
            ...
    """
    # Buscar carpeta del cliente (por código exacto o nombre que empiece con el código)
    carpeta_id = _buscar_carpeta_cliente(service, str(codigo_cliente))

    if not carpeta_id:
        print(f"  [!] Carpeta de cliente '{codigo_cliente}' no encontrada en Drive. Saltando.")
        return {"estado": "carpeta_no_encontrada", "cliente": codigo_cliente}

    # Subir el archivo
    metadata = {
        "name": nombre_archivo,
        "parents": [carpeta_id]
    }
    media = MediaFileUpload(local_path, mimetype="application/pdf", resumable=True)
    archivo = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,webViewLink,name"
    ).execute()

    return {
        "estado": "ok",
        "nombre": archivo["name"],
        "link": archivo.get("webViewLink"),
        "id": archivo["id"]
    }


def _buscar_carpeta_cliente(service, codigo: str) -> str | None:
    """
    Busca la carpeta del cliente en Drive.
    Primero por nombre exacto (ej: "9"), luego por prefijo (ej: "9 - Lanis Grill").
    """
    # Intento 1: nombre exacto
    folder_id = buscar_carpeta(service, codigo, DRIVE_ROOT_ID)
    if folder_id:
        return folder_id

    # Intento 2: nombre que empiece con el código seguido de espacio o guion
    q = (
        f"name contains '{codigo}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{DRIVE_ROOT_ID}' in parents and trashed=false"
    )
    res = service.files().list(q=q, fields="files(id,name)").execute()
    carpetas = res.get("files", [])

    # Filtrar carpetas cuyo nombre empieza con el código
    for c in carpetas:
        nombre = c["name"]
        if nombre == codigo or nombre.startswith(f"{codigo} ") or nombre.startswith(f"{codigo}-"):
            return c["id"]

    return None


def subir_todas():
    """Lee el estado.json y sube todas las facturas confirmadas a Drive."""
    if not ESTADO_FILE.exists():
        print("[!] No hay estado.json. Ejecuta primero pipeline.py y confirma en la interfaz.")
        return

    with open(ESTADO_FILE, encoding="utf-8") as f:
        facturas = json.load(f)

    service = get_service()
    ok = 0
    errores = []

    for factura in facturas:
        if factura.get("excluir"):
            print(f"  [—] {factura.get('nombre_final')} — excluida")
            continue

        archivo_final = factura.get("archivo_final")
        if not archivo_final or not Path(archivo_final).exists():
            print(f"  [!] {factura.get('nombre_final')} — archivo local no encontrado")
            continue

        codigo   = factura.get("codigo_cliente")
        nombre   = factura.get("nombre_final")
        especial = factura.get("especial", False)

        if especial:
            nombre = f"⚡ {nombre}"  # Prefijo visual para especiales en Drive

        print(f"  ↑ Subiendo {nombre} → cliente {codigo}...", end=" ")
        resultado = subir_factura(service, archivo_final, str(codigo), nombre)

        if resultado["estado"] == "ok":
            print(f"✓ {resultado.get('link', '')}")
            ok += 1
        else:
            print(f"✗ {resultado['estado']}")
            errores.append(resultado)

    print(f"\n[✓] Subidas: {ok} | Errores: {len(errores)}")
    if errores:
        print("Errores:")
        for e in errores:
            print(f"  - Cliente {e.get('cliente')}: {e.get('estado')}")


if __name__ == "__main__":
    subir_todas()
