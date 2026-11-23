"""Junta download e tratamento em uma única chamada, usada pelo dashboard e pelo terminal."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from . import agravos as cat
from . import srag
from .download import FALHA_SINAN, FALHA_SRAG, baixar_arquivo, listagem_salva, listar_ftp
from .processar import ler_inventario, processar_dbc


@dataclass
class Resultado:
    sucesso: list[str] = field(default_factory=list)
    indisponiveis: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    pulados: list[str] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)  # fontes que não responderam (ficou a lista salva)


Aviso = Callable[[str, float, str], None]  # (tarefa, fração 0-1, mensagem)


def arquivo_mudou(agravo: str, salvo: dict, novo: dict) -> bool:
    """O arquivo publicado mudou desde o que foi baixado?

    No SRAG vale só a data do arquivo: a situação (preliminar/final) é deduzida da página e
    mudaria sozinha quando todos os anos são republicados juntos, sem nada novo.
    """
    if agravo == "SRAG":
        return salvo.get("data_ftp") != novo.get("data_ftp")
    return salvo.get("data_ftp") != novo.get("data_ftp") or salvo.get("situacao") != novo.get("situacao")


def precisa_atualizar(agravo: str, ano: int, info: dict, ufs: list[str]) -> bool:
    atual = ler_inventario().get(f"{agravo}_{ano}")
    if not atual:
        return True
    return arquivo_mudou(agravo, atual, info) or sorted(atual.get("ufs", [])) != sorted(ufs)


def atualizar(
    agravos: list[str],
    anos: list[int],
    ufs: list[str],
    manter_brutos: bool = False,
    forcar: bool = False,
    aviso: Aviso | None = None,
) -> Resultado:
    avisar = aviso or (lambda t, f, m: None)
    res = Resultado()
    avisar("Consultando o DATASUS", 0, "listando arquivos do FTP")
    try:
        listagem = listar_ftp()
    except Exception as e:  # sem internet: usa a última listagem, se houver
        listagem = listagem_salva()
        if not listagem:
            raise ConnectionError(f"Sem acesso ao FTP do DATASUS ({e}). Verifique a internet.") from e

    res.falhas = listagem.get("falhas", [])
    tarefas = [(a, ano) for a in agravos for ano in sorted(anos)]
    for i, (agravo, ano) in enumerate(tarefas, 1):
        rotulo = f"{cat.nome(agravo)} {ano}"
        titulo = f"[{i}/{len(tarefas)}] {rotulo}"
        info = listagem["arquivos"].get(agravo, {}).get(str(ano))
        if not info:
            fonte = FALHA_SRAG if agravo == "SRAG" else FALHA_SINAN
            if fonte in res.falhas:  # a fonte está fora do ar: não dá para dizer que o dado não existe
                res.erros.append(f"{rotulo}: sem acesso ao {fonte.split(' (')[0]} agora. Tente de novo mais tarde.")
            else:
                res.indisponiveis.append(rotulo)
            continue
        if not forcar and not precisa_atualizar(agravo, ano, info, ufs):
            res.pulados.append(rotulo)
            continue
        try:
            def prog_download(recebido: int, total: int) -> None:
                frac = recebido / total if total else 0
                avisar(titulo, frac * 0.7, f"baixando {recebido / 1e6:,.1f} de {total / 1e6:,.1f} MB")

            def prog_processar(f: float, m: str) -> None:
                avisar(titulo, 0.7 + 0.3 * f, m)

            if agravo == "SRAG":  # SIVEP-Gripe, do OpenDataSUS
                caminho = srag.baixar(info, prog_download)
                n = srag.processar(caminho, ano, ufs, info, prog_processar)
            else:
                caminho = baixar_arquivo(info["arquivo"], info["situacao"], prog_download)
                n = processar_dbc(caminho, agravo, ano, ufs, info, prog_processar)
            if not manter_brutos:
                caminho.unlink(missing_ok=True)
            res.sucesso.append(f"{rotulo}: {n:,} registros".replace(",", "."))
        except Exception as e:
            res.erros.append(f"{rotulo}: {e}")
    avisar("Concluído", 1, "")
    return res
