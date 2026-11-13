"""Rotas da API, um arquivo por assunto. Cada um expõe um ``router`` (APIRouter)."""

from . import dados, meta, painel, registros, variaveis

ROUTERS = [meta.router, painel.router, variaveis.router, registros.router, dados.router]
