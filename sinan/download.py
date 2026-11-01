"""Download dos arquivos .dbc do FTP do DATASUS."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from ftplib import FTP, all_errors
from pathlib import Path
from typing import Callable

from .config import ARQ_LISTAGEM_FTP, FTP_HOST, FTP_PASTAS, PASTA_BRUTOS, PASTA_DADOS

PADRAO = re.compile(r"^([A-Z]+?)BR(\d{2})\.DBC$", re.I)


def _ano(aa: str) -> int:
    n = int(aa)
    return 2000 + n if n <= 50 else 1900 + n


def _conectar() -> FTP:
    ftp = FTP(FTP_HOST, timeout=90)
    ftp.login()
    ftp.voidcmd("TYPE I")
    return ftp


def listar_ftp() -> dict:
    """Lista os arquivos disponíveis no FTP e salva a listagem para uso offline.

    Retorna {"atualizado_em": ..., "arquivos": {"DENG": {"2024": {...}}}}.
    Se um ano existir em FINAIS e em PRELIM, vale o FINAIS.
    """
    ftp = _conectar()
    arquivos: dict[str, dict[str, dict]] = {}
    try:
        for situacao in ("preliminar", "final"):  # final por último para ter prioridade
            ftp.cwd(FTP_PASTAS[situacao])
            linhas: list[str] = []
            ftp.retrlines("LIST", linhas.append)
            for linha in linhas:
                partes = linha.split()
                if not partes:
                    continue
                nome = partes[-1]
                m = PADRAO.match(nome)
                if not m:
                    continue
                tamanho = next((int(p) for p in partes[2:4] if p.isdigit()), 0)
                arquivos.setdefault(m.group(1).upper(), {})[str(_ano(m.group(2)))] = {
                    "arquivo": nome,
                    "situacao": situacao,
                    "tamanho": tamanho,
                    "data_ftp": " ".join(partes[:2]),
                }
    finally:
        try:
            ftp.quit()
        except all_errors:
            pass
    listagem = {"atualizado_em": datetime.now().isoformat(timespec="seconds"), "arquivos": arquivos}
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQ_LISTAGEM_FTP.write_text(json.dumps(listagem, indent=1), encoding="utf-8")
    return listagem


def listagem_salva() -> dict | None:
    try:
        return json.loads(ARQ_LISTAGEM_FTP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def baixar_arquivo(
    nome: str,
    situacao: str,
    progresso: Callable[[int, int], None] | None = None,
    tentativas: int = 4,
) -> Path:
    """Baixa um .dbc com retomada em caso de queda de conexão."""
    PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_BRUTOS / nome
    parcial = destino.with_suffix(".parcial")
    ultimo_erro: Exception | None = None

    for tentativa in range(tentativas):
        try:
            ftp = _conectar()
            ftp.cwd(FTP_PASTAS[situacao])
            total = ftp.size(nome) or 0
            if destino.exists() and destino.stat().st_size == total:
                ftp.quit()
                return destino
            ja = parcial.stat().st_size if parcial.exists() else 0
            if ja > total:
                ja = 0
            modo = "ab" if ja else "wb"
            with open(parcial, modo) as fh:
                recebido = ja

                def escrever(bloco: bytes) -> None:
                    nonlocal recebido
                    fh.write(bloco)
                    recebido += len(bloco)
                    if progresso:
                        progresso(recebido, total)

                ftp.retrbinary(f"RETR {nome}", escrever, blocksize=256 * 1024, rest=ja or None)
            try:
                ftp.quit()
            except all_errors:
                pass
            if parcial.stat().st_size != total:
                raise IOError("download incompleto")
            parcial.replace(destino)
            return destino
        except all_errors as e:  # inclui OSError e erros de FTP
            ultimo_erro = e
            time.sleep(3 * (tentativa + 1))
    raise ConnectionError(f"Não foi possível baixar {nome}: {ultimo_erro}")
