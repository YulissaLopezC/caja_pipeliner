"""
run.py — Lanzador todo en uno
Uso:
    python run.py                         → Revisa Gmail, procesa y abre interfaz
    python run.py --pdf ruta/caja.pdf     → Procesa un PDF local directamente
    python run.py --subir                 → Solo sube a Drive (tras confirmar en interfaz)
    python run.py --setup-gmail           → Configura Gmail OAuth2 (primera vez)
"""

import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent


def main():
    args = sys.argv[1:]

    if "--setup-gmail" in args:
        subprocess.run([sys.executable, str(BASE_DIR / "gmail_watcher.py"), "--setup"])

    elif "--pdf" in args:
        idx = args.index("--pdf")
        pdf_path = args[idx + 1] if idx + 1 < len(args) else None
        if not pdf_path:
            print("[!] Indica la ruta del PDF: python run.py --pdf ruta/archivo.pdf")
            sys.exit(1)
        subprocess.run([sys.executable, str(BASE_DIR / "pipeline.py"), pdf_path], check=True)
        subprocess.run([sys.executable, str(BASE_DIR / "app.py")])

    elif "--subir" in args:
        subprocess.run([sys.executable, str(BASE_DIR / "drive_uploader.py")])

    else:
        # Flujo completo: Gmail → pipeline → interfaz
        subprocess.run([sys.executable, str(BASE_DIR / "gmail_watcher.py")], check=True)


if __name__ == "__main__":
    main()
