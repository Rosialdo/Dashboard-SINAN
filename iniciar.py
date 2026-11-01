"""Abre o dashboard no navegador (funciona sem internet)."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def porta_livre(inicial: int = 8501) -> int:
    for porta in range(inicial, inicial + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:
                return porta
    return inicial


def main() -> None:
    porta = porta_livre()
    url = f"http://localhost:{porta}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(RAIZ / "app.py"),
         "--server.port", str(porta), "--server.address", "localhost",
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        cwd=RAIZ,
    )
    for _ in range(120):  # espera o servidor subir (até ~60 s)
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                break
        if proc.poll() is not None:
            sys.exit("O dashboard não conseguiu iniciar. Veja a mensagem acima.")
        time.sleep(0.5)
    print(f"\n  Dashboard aberto em {url}\n  Para encerrar, feche esta janela (ou Ctrl+C).\n")
    webbrowser.open(url)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
