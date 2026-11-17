"""Contraste das cores do tema (fórmula da WCAG), nos temas claro e escuro."""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).parents[1] / "web"
CSS = (WEB / "css" / "base" / "tema.css").read_text(encoding="utf-8")


def _tema(seletor: str) -> dict[str, str]:
    bloco = re.search(re.escape(seletor) + r"[^{]*\{(.*?)\}", CSS, re.S).group(1)
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", bloco))


TEMAS = {"claro": _tema(":root"), "escuro": _tema('[data-theme="dark"]')}


def _luz(cor: str) -> float:
    c = [int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste(a: str, b: str) -> float:
    x, y = sorted([_luz(a), _luz(b)], reverse=True)
    return (x + 0.05) / (y + 0.05)


def test_formula_de_contraste():
    assert round(contraste("#000000", "#ffffff"), 1) == 21.0


@pytest.mark.parametrize("tema", TEMAS)
def test_contraste_do_texto(tema):
    t = TEMAS[tema]
    assert contraste(t["--muted"], t["--card"]) >= 4.5
    assert contraste(t["--muted"], t["--bg"]) >= 4.5
    assert contraste(t["--text-2"], t["--card"]) >= 4.5


@pytest.mark.parametrize("tema", TEMAS)
def test_contraste_dos_graficos(tema):
    t = TEMAS[tema]
    assert contraste(t["--serie-ctx"], t["--card"]) >= 3
    assert contraste(t["--muted"], t["--mapa-vazio"]) >= 3  # listras da hachura "sem dado"


def test_mapa_sem_dado_tem_hachura():
    assert "url(#sem-dado)" in (WEB / "js" / "paginas" / "mapa.js").read_text(encoding="utf-8")
