"""Monta a aplicação: rotas da API, erros, arquivos da interface e proteção local."""

from __future__ import annotations

import traceback
from pathlib import Path

import plotly
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from .. import consultas as cq
from .respostas import ErroUsuario, erro
from .rotas import ROUTERS
from .seguranca import ProtecaoLocal

PASTA_WEB = config.RAIZ / "web"
PLOTLY_JS = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"


class ArquivosInterface(StaticFiles):
    """Arquivos da pasta web/ sempre conferidos com o servidor ("no-cache").

    A interface tem vários módulos JavaScript: se o navegador guardasse alguns
    antigos depois de uma atualização, versões diferentes se misturariam.
    """

    def file_response(self, *args, **kwargs):
        resposta = super().file_response(*args, **kwargs)
        resposta.headers["Cache-Control"] = "no-cache"
        return resposta


def _mensagem_validacao(exc: RequestValidationError) -> str:
    """Erros de validação do FastAPI em português e numa linha só."""
    partes = []
    for e in exc.errors():
        campo = ".".join(str(p) for p in e.get("loc", ()) if p not in ("query", "body"))
        msg = e.get("msg", "valor inválido").removeprefix("Value error, ")
        partes.append(f"{campo}: {msg}" if campo else msg)
    return "Parâmetro inválido. " + "; ".join(partes)


def criar_app() -> FastAPI:
    app = FastAPI(
        title="Dashboard SINAN",
        description="API local do painel de doenças e agravos de notificação (SINAN/DATASUS).",
        # documentação interativa em /api/docs (precisa de internet para carregar o visual)
        docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json",
    )

    for router in ROUTERS:
        app.include_router(router, prefix="/api")

    # ---------------------------------------------------------------- erros
    @app.exception_handler(ErroUsuario)
    @app.exception_handler(cq.AgravoInvalido)
    async def _erro_usuario(_: Request, exc: Exception):
        return erro(str(exc), 400)

    @app.exception_handler(RequestValidationError)
    async def _erro_validacao(_: Request, exc: RequestValidationError):
        return erro(_mensagem_validacao(exc), 400)

    @app.exception_handler(Exception)
    async def _erro_interno(_: Request, exc: Exception):
        traceback.print_exception(exc)  # os detalhes ficam na janela preta, não na tela
        return erro(f"Erro interno ({type(exc).__name__}: {exc}). Veja os detalhes na janela do dashboard.", 500)

    # ---------------------------------------------------------------- interface
    @app.get("/", include_in_schema=False)
    def pagina():
        return FileResponse(PASTA_WEB / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/vendor/plotly.min.js", include_in_schema=False)
    def plotly_js():
        return FileResponse(PLOTLY_JS, headers={"Cache-Control": "max-age=86400"})

    app.mount("/static", ArquivosInterface(directory=PASTA_WEB), name="static")

    # ---------------------------------------------------------------- segurança
    app.add_middleware(ProtecaoLocal)
    return app


app = criar_app()
