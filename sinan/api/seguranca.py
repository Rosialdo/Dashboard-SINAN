"""Proteção do servidor local contra outros sites abertos no mesmo navegador."""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from .respostas import erro


class ProtecaoLocal:
    """Middleware ASGI que recusa pedidos que não vieram do próprio dashboard.

    - ``Host`` precisa ser localhost/127.0.0.1 (bloqueia "DNS rebinding");
    - se o navegador mandar ``Origin``, ela precisa ser o próprio dashboard;
    - POST só com ``Content-Type: application/json``: o navegador é obrigado a
      pedir permissão (CORS) antes de enviar isso de outro site, e o servidor
      nunca dá essa permissão.

    No modo publicado (``hosts_extras`` não vazio) aceita também esses domínios,
    com origem ``https://``, e só pedidos de leitura (GET, HEAD, OPTIONS).
    """

    HOSTS = {"localhost", "127.0.0.1", "[::1]"}

    def __init__(self, app: ASGIApp, hosts_extras: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.hosts_extras = hosts_extras

    @staticmethod
    def _nome_host(host: str) -> str:
        if host.startswith("["):  # IPv6: [::1]:8501
            return host.split("]", 1)[0] + "]"
        return host.rsplit(":", 1)[0]

    def motivo_bloqueio(self, metodo: str, cab: dict[str, str]) -> str | None:
        host = cab.get("host", "")
        if self._nome_host(host).lower() not in self.HOSTS | self.hosts_extras:
            return "Host não permitido."
        origem = cab.get("origin")
        # atrás do proxy com HTTPS o navegador manda https://, e o Host pode ser o local
        if origem is not None and origem != f"http://{host}" and origem not in {f"https://{h}" for h in self.hosts_extras}:
            return "Origem não permitida."
        if self.hosts_extras and metodo not in ("GET", "HEAD", "OPTIONS"):
            return "Ação não permitida."
        if metodo not in ("GET", "HEAD", "OPTIONS"):
            tipo = cab.get("content-type", "").split(";", 1)[0].strip().lower()
            if tipo != "application/json":
                return "Envie os dados como JSON."
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            cab = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
            motivo = self.motivo_bloqueio(scope["method"], cab)
            if motivo:
                await erro(motivo, 403)(scope, receive, send)
                return
        await self.app(scope, receive, send)
