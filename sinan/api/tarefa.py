"""Download e processamento em segundo plano (só um por vez).

A interface acompanha o andamento consultando ``/api/dados/status``.
"""

from __future__ import annotations

import threading
import traceback

from .. import config
from ..pipeline import atualizar
from . import cache

_estado = {"rodando": False, "tarefa": "", "fracao": 0.0, "mensagem": "", "resultado": None, "erro": None}
_trava = threading.Lock()


def estado() -> dict:
    """Cópia do andamento atual (segura para ler de outra thread)."""
    with _trava:
        return dict(_estado)


def _executar(agravos: list[str], anos: list[int], ufs: list[str], forcar: bool) -> None:
    def aviso(tarefa: str, frac: float, msg: str) -> None:
        with _trava:
            _estado.update(tarefa=tarefa, fracao=round(frac, 4), mensagem=msg)
    try:
        cfg = config.carregar_config()
        res = atualizar(agravos, anos, ufs, cfg.get("manter_brutos", False), forcar, aviso)
        with _trava:
            _estado["resultado"] = res.__dict__
    except Exception as e:
        traceback.print_exc()
        with _trava:
            _estado["erro"] = str(e)
    finally:
        cache.limpar()
        with _trava:
            _estado["rodando"] = False


def iniciar(agravos: list[str], anos: list[int], ufs: list[str], forcar: bool) -> bool:
    """Começa a atualização. Devolve False se já houver uma em andamento."""
    with _trava:
        if _estado["rodando"]:
            return False
        config.salvar_config({**config.carregar_config(), "agravos": agravos, "anos": anos, "ufs": ufs})
        _estado.update(rodando=True, tarefa="Iniciando", fracao=0.0, mensagem="", resultado=None, erro=None)
        threading.Thread(target=_executar, args=(agravos, anos, ufs, forcar), daemon=True).start()
    return True
