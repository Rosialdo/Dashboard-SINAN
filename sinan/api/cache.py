"""Cache dos resultados agregados, invalidado quando os dados mudam."""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable

from .. import config

LIMITE = 200  # só resultados agregados (pequenos); tabelas de registros não entram aqui
_cache: OrderedDict = OrderedDict()
_trava = threading.Lock()


def _versao() -> float:
    """Data do inventário: muda sempre que um arquivo é baixado ou removido."""
    try:
        return config.ARQ_INVENTARIO.stat().st_mtime
    except OSError:
        return 0.0


def memo[T](chave, calcular: Callable[[], T]) -> T:
    """Devolve o valor guardado para ``chave`` ou calcula e guarda (LRU)."""
    k = (chave, _versao())
    with _trava:
        if k in _cache:
            _cache.move_to_end(k)
            return _cache[k]
    valor = calcular()
    with _trava:
        _cache[k] = valor
        while len(_cache) > LIMITE:
            _cache.popitem(last=False)
    return valor


def limpar() -> None:
    with _trava:
        _cache.clear()
