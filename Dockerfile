# Imagem do painel publicado (servidor). O uso no computador com os .bat não depende dela.
# Mesma tag nos dois estágios: o .venv aponta para o Python da imagem.

FROM python:3.12.16-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
# o código não é instalado como pacote: vem de /app, que é a pasta atual
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12.16-slim-trixie
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin sinan \
    && mkdir /dados && chown sinan:sinan /dados
ENV SINAN_DADOS=/dados \
    NUMBA_CACHE_DIR=/tmp/numba \
    PYTHONUNBUFFERED=1 \
    TZ=America/Boa_Vista \
    PATH=/app/.venv/bin:$PATH
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY sinan/ sinan/
COPY web/ web/
COPY referencia/ referencia/
COPY baixar_dados.py ./
COPY scripts/atualizar_servidor.sh scripts/
USER sinan
EXPOSE 8501
# só o proxy alcança o painel (rede interna do compose); sem log de acesso para não guardar IPs
CMD ["uvicorn", "sinan.api:app", "--host", "0.0.0.0", "--port", "8501", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log", "--no-server-header"]
