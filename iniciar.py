"""Abre o dashboard no navegador (funciona sem internet)."""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))


def porta_livre(inicial: int = 8501) -> int:
    for porta in range(inicial, inicial + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:
                return porta
    return inicial


def abrir_quando_pronto(porta: int) -> None:
    for _ in range(120):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                break
        time.sleep(0.25)
    url = f"http://localhost:{porta}"
    print(f"\n  Dashboard aberto em {url}\n  Para encerrar, feche esta janela (ou Ctrl+C).\n")
    webbrowser.open(url)


def main() -> None:
    porta = porta_livre()
    if "--sem-navegador" not in sys.argv:
        threading.Thread(target=abrir_quando_pronto, args=(porta,), daemon=True).start()
    from sinan.processar import migrar_arquivos
    from sinan.web import app
    migrar_arquivos()  # ajusta dados gravados por versões anteriores
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    main()
