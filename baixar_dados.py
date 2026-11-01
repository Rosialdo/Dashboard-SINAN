"""Baixa e trata os dados do SINAN pelo terminal (precisa de internet).

Sem argumentos, usa a configuração salva pelo dashboard (ou o padrão:
Roraima; dengue, chikungunya e zika; últimos 6 anos).

Exemplos:
    python baixar_dados.py
    python baixar_dados.py --agravos DENG CHIK --anos 2020-2025 --ufs RR AM
    python baixar_dados.py --listar
"""

from __future__ import annotations

import argparse
import sys

from sinan import agravos as cat
from sinan.config import carregar_config, salvar_config
from sinan.pipeline import atualizar


def _anos(texto: list[str]) -> list[int]:
    anos: set[int] = set()
    for t in texto:
        if "-" in t:
            a, b = t.split("-", 1)
            anos.update(range(int(a), int(b) + 1))
        else:
            anos.add(int(t))
    return sorted(anos)


def main() -> int:
    cfg = carregar_config()
    p = argparse.ArgumentParser(description="Baixa e trata dados do SINAN/DATASUS")
    p.add_argument("--agravos", nargs="+", help="códigos, ex.: DENG CHIK ZIKA (veja --listar)")
    p.add_argument("--anos", nargs="+", help="ex.: 2024 ou 2020-2025")
    p.add_argument("--ufs", nargs="+", help="siglas, ex.: RR AM (BR = Brasil inteiro, muito pesado)")
    p.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se já estiver atualizado")
    p.add_argument("--manter-brutos", action="store_true", help="não apaga os .dbc baixados")
    p.add_argument("--listar", action="store_true", help="mostra os códigos dos agravos")
    a = p.parse_args()

    if a.listar:
        for cod, ag in sorted(cat.AGRAVOS.items()):
            print(f"  {cod:5} {ag.nome}")
        return 0

    agravos = [x.upper() for x in (a.agravos or cfg["agravos"])]
    anos = _anos(a.anos) if a.anos else cfg["anos"]
    ufs = [x.upper() for x in (a.ufs or cfg["ufs"])]
    if a.agravos or a.anos or a.ufs:
        salvar_config({**cfg, "agravos": agravos, "anos": anos, "ufs": ufs})

    print(f"UFs: {', '.join(ufs)} | Anos: {anos[0]}-{anos[-1]} | Agravos: {', '.join(agravos)}\n")
    ultimo = [""]

    def aviso(tarefa: str, frac: float, msg: str) -> None:
        linha = f"\r{tarefa:45.45} {frac * 100:5.1f}%  {msg:40.40}"
        if tarefa != ultimo[0] and ultimo[0]:
            print()
        ultimo[0] = tarefa
        sys.stdout.write(linha)
        sys.stdout.flush()

    try:
        res = atualizar(agravos, anos, ufs, a.manter_brutos or cfg.get("manter_brutos", False), a.forcar, aviso)
    except ConnectionError as e:
        print(f"\nERRO: {e}")
        return 1
    print("\n")
    for s in res.sucesso:
        print(f"  OK          {s}")
    for s in res.pulados:
        print(f"  Atualizado  {s} (nada mudou no DATASUS)")
    for s in res.indisponiveis:
        print(f"  Não existe  {s}")
    for s in res.erros:
        print(f"  ERRO        {s}")
    return 1 if res.erros else 0


if __name__ == "__main__":
    sys.exit(main())
