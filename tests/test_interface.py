"""Interface (web/js): confere que os módulos se encaixam, sem precisar de navegador.

Um import com nome errado só quebraria ao abrir a página; aqui ele vira teste.
"""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).parents[1] / "web"
MODULOS = sorted((WEB / "js").rglob("*.js"))

_IMPORT = re.compile(r'^import\s+(?:\{([^}]*)\}|\*\s+as\s+\w+)\s+from\s+"([^"]+)";', re.M)
_EXPORT_DECL = re.compile(r"^export\s+(?:async\s+)?(?:function\*?|const|let|class)\s+([\w$]+)", re.M)
_EXPORT_LISTA = re.compile(r"^export\s+\{([^}]*)\}", re.M)


def _exportados(arquivo: Path) -> set[str]:
    texto = arquivo.read_text(encoding="utf-8")
    nomes = set(_EXPORT_DECL.findall(texto))
    for lista in _EXPORT_LISTA.findall(texto):
        nomes |= {p.split(" as ")[-1].strip() for p in lista.split(",") if p.strip()}
    return nomes


def test_ha_modulos():
    assert (WEB / "js" / "main.js") in MODULOS
    assert len(MODULOS) > 10


@pytest.mark.parametrize("arquivo", MODULOS, ids=lambda p: p.relative_to(WEB).as_posix())
def test_imports_existem(arquivo):
    texto = arquivo.read_text(encoding="utf-8")
    for nomes, origem in _IMPORT.findall(texto):
        alvo = (arquivo.parent / origem).resolve()
        assert origem.startswith("."), f"{origem}: use caminho relativo (sem internet não há CDN)"
        assert alvo.exists(), f"{arquivo.name} importa {origem}, que não existe"
        if nomes:
            faltando = {n.split(" as ")[0].strip() for n in nomes.split(",") if n.strip()} - _exportados(alvo)
            assert not faltando, f"{arquivo.name} importa {faltando} de {origem}, que não exporta"


def test_index_carrega_main_como_modulo():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="/static/js/main.js"></script>' in html
    assert "app.js" not in html


def test_servidor_entrega_os_modulos(cliente):
    for arquivo in MODULOS:
        caminho = "/static/" + arquivo.relative_to(WEB).as_posix()
        r = cliente.get(caminho)
        assert r.status_code == 200, caminho
        assert "javascript" in r.headers["content-type"], caminho
        # sempre confere com o servidor: evita misturar módulos de versões diferentes
        assert r.headers["cache-control"] == "no-cache", caminho


# ---------------------------------------------------------------- estilos (web/css)
ESTILOS = sorted((WEB / "css").rglob("*.css"))
_IMPORT_CSS = re.compile(r'@import\s+url\("([^"]+)"\);')


def test_index_carrega_os_estilos():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="/static/css/main.css">' in html
    assert "app.css" not in html


def test_todo_css_esta_importado_e_existe():
    principal = WEB / "css" / "main.css"
    importados = [(principal.parent / i).resolve() for i in _IMPORT_CSS.findall(principal.read_text(encoding="utf-8"))]
    assert all(p.exists() for p in importados), "main.css importa arquivo que não existe"
    soltos = {p.resolve() for p in ESTILOS} - set(importados) - {principal.resolve()}
    assert not soltos, f"arquivos CSS que ninguém importa: {sorted(p.name for p in soltos)}"
    # o tema vem primeiro: os outros arquivos usam as variáveis de cor dele
    assert importados[0].name == "tema.css"


def test_servidor_entrega_os_estilos(cliente):
    for arquivo in ESTILOS:
        r = cliente.get("/static/" + arquivo.relative_to(WEB).as_posix())
        assert r.status_code == 200 and "text/css" in r.headers["content-type"], arquivo.name
