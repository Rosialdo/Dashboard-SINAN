"""Junta download e tratamento em uma única chamada, usada pelo dashboard e pelo terminal."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import agravos as cat
from .download import baixar_arquivo, listagem_salva, listar_ftp
from .processar import ler_inventario, processar_dbc


@dataclass
class Resultado:
    sucesso: list[str] = field(default_factory=list)
    indisponiveis: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    pulados: list[str] = field(default_factory=list)


Aviso = Callable[[str, float, str], None]  # (tarefa, fração 0-1, mensagem)


def precisa_atualizar(agravo: str, ano: int, info: dict, ufs: list[str]) -> bool:
    atual = ler_inventario().get(f"{agravo}_{ano}")
    if not atual:
        return True
    return (atual.get("data_ftp") != info.get("data_ftp")
            or atual.get("situacao") != info.get("situacao")
            or sorted(atual.get("ufs", [])) != sorted(ufs))


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

    tarefas = [(a, ano) for a in agravos for ano in sorted(anos)]
    for i, (agravo, ano) in enumerate(tarefas, 1):
        rotulo = f"{cat.nome(agravo)} {ano}"
        titulo = f"[{i}/{len(tarefas)}] {rotulo}"
        info = listagem["arquivos"].get(agravo, {}).get(str(ano))
        if not info:
            res.indisponiveis.append(rotulo)
            continue
        if not forcar and not precisa_atualizar(agravo, ano, info, ufs):
            res.pulados.append(rotulo)
            continue
        try:
            def prog_download(recebido: int, total: int) -> None:
                frac = recebido / total if total else 0
                avisar(titulo, frac * 0.7, f"baixando {recebido / 1e6:,.1f} de {total / 1e6:,.1f} MB")

            caminho = baixar_arquivo(info["arquivo"], info["situacao"], prog_download)
            n = processar_dbc(caminho, agravo, ano, ufs, info,
                              lambda f, m: avisar(titulo, 0.7 + 0.3 * f, m))
            if not manter_brutos:
                caminho.unlink(missing_ok=True)
            res.sucesso.append(f"{rotulo}: {n:,} registros".replace(",", "."))
        except Exception as e:
            res.erros.append(f"{rotulo}: {e}")
    avisar("Concluído", 1, "")
    return res
