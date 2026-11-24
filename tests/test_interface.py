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


_PAGINA = re.compile(r'^\s*"([\w-]+)":\s*\{[^}]*secao:\s*"([^"]+)"', re.M)


def _paginas() -> list[tuple[str, str]]:
    """(id, seção) na ordem do menu, lidos de PAGINAS em nucleo/estado.js."""
    return _PAGINA.findall((WEB / "js" / "nucleo" / "estado.js").read_text(encoding="utf-8"))


def test_menu_poe_variaveis_no_fim_como_avancado():
    paginas = _paginas()
    assert paginas[-1] == ("variaveis", "AVANÇADO")
    analise = [i for i, s in paginas if s == "ANÁLISE"]
    assert "variaveis" not in analise
    assert analise[:3] == ["visao-geral", "mapa", "perfil"]


def test_variaveis_continua_com_montador():
    roteador = (WEB / "js" / "roteador.js").read_text(encoding="utf-8")
    assert '"variaveis": variaveis.montar' in roteador


def test_perfil_aponta_para_outras_variaveis():
    perfil = (WEB / "js" / "paginas" / "perfil.js").read_text(encoding="utf-8")
    assert 'href="#/variaveis"' in perfil


def test_qualidade_no_menu_depois_do_perfil():
    ids = [i for i, _ in _paginas()]
    assert ("qualidade", "ANÁLISE") in _paginas()
    assert ids.index("qualidade") == ids.index("perfil") + 1


def test_qualidade_tem_montador():
    roteador = (WEB / "js" / "roteador.js").read_text(encoding="utf-8")
    assert '"qualidade": qualidade.montar' in roteador


def test_qualidade_explica_base_e_referencia():
    tela = (WEB / "js" / "paginas" / "qualidade.js").read_text(encoding="utf-8")
    for texto in ("fichas avaliáveis", "sem data de encerramento registrada",
                  "referência provisória", "dados disponíveis até"):
        assert texto in tela


def test_sobre_explica_os_prazos():
    sobre = (WEB / "js" / "paginas" / "sobre.js").read_text(encoding="utf-8")
    for texto in ("60 dias", "Digitação", "sem data de encerramento registrada", "referência provisória"):
        assert texto in sobre


def test_mapa_tem_incidencia_suavizada():
    mapa = (WEB / "js/paginas/mapa.js").read_text(encoding="utf-8")
    assert 'data-medida="incidencia_suavizada"' in mapa
    assert '"incidencia_suavizada"' in mapa.split("function tabelaMunicipios")[1]  # coluna da tabela
    assert "Number.isFinite" in mapa.split("function desenharMapa")[1]  # escala só com números
    sobre = (WEB / "js/paginas/sobre.js").read_text(encoding="utf-8")
    assert "Incidência suavizada" in sobre
    assert ("A incidência não aparece com filtro de sexo ou faixa etária, "
            "nem na contagem pelo município de notificação, porque a população não corresponde aos casos.") in sobre


def test_painel_lateral_mostra_incidencia_suavizada():
    mapa = (WEB / "js/paginas/mapa.js").read_text(encoding="utf-8")
    lateral = mapa.split("function desenharLateral")[1].split("function tabelaMunicipios")[0]
    assert "incidencia_suavizada" in lateral and "Incidência suavizada" in lateral
    assert "inc != null" in lateral  # sem município, o bloco da área some quando o topo não tem incidência


def test_visao_explica_curva_oculta():
    t = (WEB / "js/paginas/visao.js").read_text(encoding="utf-8")
    assert "contagens_ocultas" in t and "proteger a privacidade" in t


def test_visao_explica_mes_oculto():
    t = (WEB / "js/paginas/visao.js").read_text(encoding="utf-8")
    assert "casos por mês de um município" in t and "d.mes" in t


def test_sobre_explica_canal_endemico():
    t = (WEB / "js/paginas/sobre.js").read_text(encoding="utf-8")
    assert "Faixa histórica" in t and "1,5 vez a mediana" in t and "5 anos" in t and "provisório" in t and "1 em cada 4 anos" in t


def test_curva_semanal_tem_caixa_de_anos_anteriores():
    v = (WEB / "js/paginas/visao.js").read_text(encoding="utf-8")
    s = (WEB / "js/paginas/sobre.js").read_text(encoding="utf-8")
    assert "Mostrar anos anteriores" in v and 'type="checkbox"' in v
    assert "Mostrar anos anteriores" in s
