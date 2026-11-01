"""Gera os arquivos da pasta ``referencia/`` (uso do desenvolvedor).

Esses arquivos já vêm prontos no repositório para que o dashboard funcione
sem internet. Só é preciso rodar este script de novo para atualizar a
população do IBGE ou os rótulos do TabNet:

    uv run python scripts/gerar_referencias.py
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import urllib.request
import zipfile
from ftplib import FTP
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REF = RAIZ / "referencia"
TABNET = REF / "tabnet"

IBGE = "https://servicodados.ibge.gov.br/api"


def baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=300) as r:
        dados = r.read()
    if dados[:2] == b"\x1f\x8b":
        dados = gzip.decompress(dados)
    return dados


def baixar_json(url: str):
    return json.loads(baixar(url).decode("utf-8"))


# ---------------------------------------------------------------- TabNet
def gerar_tabnet() -> None:
    """Copia os arquivos .def e .cnv (rótulos oficiais) do tabulador do SINAN."""
    TABNET.mkdir(parents=True, exist_ok=True)
    ftp = FTP("ftp.datasus.gov.br", timeout=120)
    ftp.login()
    ftp.cwd("/dissemin/publicos/SINAN/AUXILIAR")
    total = 0
    for nome_zip in ["TAB_SINANNET.zip", "TAB_SINANONLINE.zip"]:
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {nome_zip}", buf.write)
        with zipfile.ZipFile(buf) as z:
            for info in z.infolist():
                nome = Path(info.filename).name
                ext = nome.lower().rsplit(".", 1)[-1]
                if ext not in ("def", "cnv") or nome.startswith("-"):
                    continue
                if info.file_size > 300_000:  # tabelas enormes (unidades, CBO...) não são usadas
                    continue
                texto = z.read(info).decode("latin-1")
                (TABNET / nome.lower()).write_text(texto, encoding="utf-8")
                total += 1
    ftp.quit()
    print(f"TabNet: {total} arquivos de rótulos")


# ------------------------------------------------------------ Municípios
def gerar_municipios() -> list[dict]:
    dados = baixar_json(f"{IBGE}/v1/localidades/municipios")
    linhas = []
    for m in dados:
        micro = m.get("microrregiao") or {}
        uf = (micro.get("mesorregiao") or {}).get("UF") or m["regiao-imediata"]["regiao-intermediaria"]["UF"]
        linhas.append({
            "cod6": str(m["id"])[:6],
            "cod7": str(m["id"]),
            "municipio": m["nome"],
            "uf": uf["sigla"],
            "uf_cod": str(uf["id"]),
            "uf_nome": uf["nome"],
            "regiao": uf["regiao"]["nome"],
        })
    linhas.sort(key=lambda r: r["cod7"])
    with open(REF / "municipios.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"Municípios: {len(linhas)}")
    return linhas


# ------------------------------------------------------------- População
def _serie(url: str) -> dict[str, dict[int, int]]:
    out: dict[str, dict[int, int]] = {}
    for var in baixar_json(url):
        for res in var["resultados"]:
            for s in res["series"]:
                cod = s["localidade"]["id"][:6]
                for ano, v in s["serie"].items():
                    if v and v.isdigit():
                        out.setdefault(cod, {})[int(ano)] = int(v)
    return out


def gerar_populacao(municipios: list[dict]) -> None:
    """Estimativas anuais do IBGE (tabela 6579) + Censo 2022 (tabela 4714).

    Anos sem estimativa (2007, 2010, 2023...) são interpolados linearmente;
    anos fora da série repetem o valor mais próximo.
    """
    periodos = [p["id"] for p in baixar_json(f"{IBGE}/v3/agregados/6579/periodos")]
    pop: dict[str, dict[int, int]] = {}
    for ano in periodos:
        parte = _serie(f"{IBGE}/v3/agregados/6579/periodos/{ano}/variaveis/9324?localidades=N6[all]")
        for cod, serie in parte.items():
            pop.setdefault(cod, {}).update(serie)
        print(f"  população {ano}: {len(parte)} municípios")
    censo = _serie(f"{IBGE}/v3/agregados/4714/periodos/2022/variaveis/93?localidades=N6[all]")
    for cod, serie in censo.items():
        pop.setdefault(cod, {}).update(serie)

    anos = range(2000, 2031)
    linhas = []
    for m in municipios:
        serie = pop.get(m["cod6"], {})
        if not serie:
            continue
        conhecidos = sorted(serie)
        for ano in anos:
            if ano in serie:
                v = serie[ano]
            elif ano < conhecidos[0]:
                v = serie[conhecidos[0]]
            elif ano > conhecidos[-1]:
                v = serie[conhecidos[-1]]
            else:
                a = max(k for k in conhecidos if k < ano)
                b = min(k for k in conhecidos if k > ano)
                v = round(serie[a] + (serie[b] - serie[a]) * (ano - a) / (b - a))
            linhas.append((m["cod6"], ano, v))
    with open(REF / "populacao.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cod6", "ano", "populacao"])
        w.writerows(linhas)
    print(f"População: {len(linhas)} linhas")


# ------------------------------------------------------------------ Mapa
def gerar_mapa() -> None:
    url = (f"{IBGE}/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson"
           "&intrarregiao=municipio&qualidade=minima")
    geo = baixar_json(url)
    for f in geo["features"]:
        cod7 = str(f["properties"].get("codarea"))
        f["properties"] = {"cod6": cod7[:6]}
        f["id"] = cod7[:6]
    texto = json.dumps(geo, separators=(",", ":"))
    (REF / "municipios.geojson").write_text(texto, encoding="utf-8")
    print(f"Mapa: {len(geo['features'])} municípios, {len(texto) / 1e6:.1f} MB")


if __name__ == "__main__":
    REF.mkdir(exist_ok=True)
    etapas = sys.argv[1:] or ["tabnet", "municipios", "mapa"]
    if "tabnet" in etapas:
        gerar_tabnet()
    if "municipios" in etapas:
        gerar_populacao(gerar_municipios())
    if "mapa" in etapas:
        gerar_mapa()
