"""
gmail_watcher.py — Descarga automáticamente el PDF de caja desde Gmail
Requisitos: pip install google-auth google-auth-oauthlib google-api-python-client

Primera vez: ejecutar con --setup para autenticarse con Gmail.
Luego: ejecutar normalmente para revisar correos nuevos.
"""

import base64
import os
import sys
import json
import pickle
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR    = Path(__file__).parent
CREDS_FILE  = BASE_DIR / "credentials" / "gmail_credentials.json"
TOKEN_FILE  = BASE_DIR / "credentials" / "token.pickle"
INBOX_DIR   = BASE_DIR / "inbox"

# Scopes necesarios (solo lectura de Gmail)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Palabras clave para identificar el correo de caja
ASUNTO_KEYWORDS = ["caja", "CAJA", "Caja"]


def autenticar() -> object:
    """Autentica con Gmail OAuth2. Guarda token para no pedir permisos cada vez."""
    creds = None
    TOKEN_FILE.parent.mkdir(exist_ok=True)

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"""
[!] No se encontró el archivo de credenciales de Gmail.

Para configurarlo:
1. Ve a https://console.cloud.google.com/
2. Crea un proyecto → Habilita "Gmail API"
3. Credenciales → OAuth 2.0 → Desktop app
4. Descarga el JSON y guárdalo en:
   {CREDS_FILE}

Luego ejecuta: python gmail_watcher.py --setup
""")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


def buscar_correo_caja(service, dias_atras: int = 2) -> list[dict]:
    """
    Busca correos con 'Caja' en el asunto de los últimos N días.
    Retorna lista de mensajes encontrados.
    """
    fecha_desde = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y/%m/%d")
    query = f"subject:caja has:attachment after:{fecha_desde}"

    result = service.users().messages().list(userId="me", q=query).execute()
    mensajes = result.get("messages", [])
    print(f"[✓] Correos encontrados con PDF de caja: {len(mensajes)}")
    return mensajes


def descargar_adjunto(service, mensaje_id: str) -> list[Path]:
    """Descarga todos los adjuntos PDF de un correo. Retorna rutas de archivos."""
    INBOX_DIR.mkdir(exist_ok=True)
    msg = service.users().messages().get(userId="me", id=mensaje_id).execute()
    archivos = []

    # Extraer asunto para el nombre
    headers = msg["payload"].get("headers", [])
    asunto  = next((h["value"] for h in headers if h["name"] == "Subject"), "sin_asunto")

    def buscar_adjuntos(parts):
        for part in parts:
            if part.get("parts"):
                buscar_adjuntos(part["parts"])
            mime = part.get("mimeType", "")
            nombre = part.get("filename", "")
            if "pdf" in mime.lower() or nombre.lower().endswith(".pdf"):
                att_id = part["body"].get("attachmentId")
                if att_id:
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=mensaje_id, id=att_id
                    ).execute()
                    data = base64.urlsafe_b64decode(att["data"])
                    dest = INBOX_DIR / nombre if nombre else INBOX_DIR / f"caja_{mensaje_id[:8]}.pdf"
                    dest.write_bytes(data)
                    archivos.append(dest)
                    print(f"[✓] Descargado: {dest.name}")

    partes = msg["payload"].get("parts", [])
    if partes:
        buscar_adjuntos(partes)
    else:
        # Correo sin partes (solo body)
        body = msg["payload"]["body"]
        if body.get("data"):
            data = base64.urlsafe_b64decode(body["data"])
            dest = INBOX_DIR / f"caja_{mensaje_id[:8]}.pdf"
            dest.write_bytes(data)
            archivos.append(dest)

    return archivos


def revisar_y_procesar(dias_atras: int = 1):
    """
    Flujo completo: revisa Gmail → descarga PDF → lanza pipeline.
    """
    service  = autenticar()
    mensajes = buscar_correo_caja(service, dias_atras)

    if not mensajes:
        print("[!] No se encontraron correos de caja nuevos.")
        return

    pdfs_descargados = []
    for msg in mensajes:
        archivos = descargar_adjunto(service, msg["id"])
        pdfs_descargados.extend(archivos)

    if not pdfs_descargados:
        print("[!] Los correos encontrados no tienen adjuntos PDF.")
        return

    # Procesar el más reciente
    pdf = pdfs_descargados[-1]
    print(f"\n[→] Procesando: {pdf.name}")
    subprocess.run([sys.executable, str(BASE_DIR / "pipeline.py"), str(pdf)], check=True)

    print(f"\n[→] Lanzando interfaz de validación...")
    subprocess.Popen([sys.executable, str(BASE_DIR / "app.py")])


if __name__ == "__main__":
    if "--setup" in sys.argv:
        print("Iniciando configuración de Gmail OAuth2...")
        autenticar()
        print("[✓] Autenticación completada. Token guardado.")
    else:
        dias = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        revisar_y_procesar(dias_atras=dias)
