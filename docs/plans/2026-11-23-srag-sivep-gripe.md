# SRAG (SIVEP-Gripe) no modo local: plano de implementação

> **Para quem for executar:** use superpowers:subagent-driven-development ou superpowers:executing-plans,
> tarefa por tarefa. Os passos usam caixas (`- [ ]`) para acompanhar.

**Objetivo:** baixar os casos de Síndrome Respiratória Aguda Grave (SRAG) do SIVEP-Gripe e mostrá-los
em todas as telas do painel como mais um "agravo" (`SRAG`), **só no modo local**.

**Arquitetura:** o SRAG é gravado no mesmo formato dos agravos do SINAN
(`dados/parquet/SRAG/SRAG_<ano>.parquet`, com as colunas originais em MAIÚSCULAS e as mesmas colunas
derivadas). Assim visão geral, mapa, perfil e tabela funcionam sem mudança. Um módulo novo,
`sinan/srag.py`, descobre os arquivos na página do OpenDataSUS, baixa o Parquet nacional e o
converte para o formato do SINAN antes de chamar o `processar.derivar()` que já existe. A listagem
do SRAG entra na mesma `listagem_ftp.json`, mas é consultada separadamente da do FTP: se uma das duas
fontes falhar, a outra continua atualizando.

**Tecnologias:** Python, pyarrow, pandas, urllib (biblioteca padrão), FastAPI. Nenhuma dependência nova.

**Origem:** issue #60 (item 36 da seção 7.6 de `docs/analise/2026-11-analise-e-roadmap.md`) e
`docs/analise/2026-11-comparacao-painel-ses-rr.md`. Este plano cobre **só o SIVEP-Gripe**. O
SIVEP-Malária e o território adscrito (e-SUS APS) ficam para planos próprios. Já está decidido que a
entrada deles será por um **botão de importar arquivo** no modo local, mas ainda não temos arquivo de
exemplo nem dicionário de campos.

## Fonte de dados (conferida em 23/11/2026)

- Página: `https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026` (não há API CKAN; `api/3` dá 404).
  O nome da página muda a cada ano. Hoje, `srag-2019-a-2027` redireciona (307) para a lista geral, que
  não tem nenhum arquivo.
- **Onde estão os links:** no HTML bruto da página, os links não aparecem como `href` (estes apontam
  para `/resource/<id>`). Eles vêm num JSON embutido, um objeto por recurso, com `"format":"parquet"`,
  `"last_modified"`, `"name":"2026- Banco vivo  23/11/2026 - PARQUET"` e
  `"url":"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2026/INFLUD26-23-11-2026.parquet"`.
  Isso foi conferido com `curl` (88 KB). Não é preciso abrir as páginas `/resource/`.
- A data no nome do arquivo muda a cada publicação. Os anos 2019–2024 estão com `23-03-2026` (todos
  publicados juntos naquela semana), e 2025 e 2026 com `23-11-2026`, atualizados toda semana.
- O arquivo de 2026 tem 20 MB e 252.989 linhas (Brasil inteiro, 1 row group). Os anos 2020–2021 são
  bem maiores.

| Campo SRAG | Tipo no Parquet (2026) | Valores | Equivalente no SINAN |
|---|---|---|---|
| `SG_UF_NOT`, `SG_UF` | texto | sigla (`"RR"`) | código IBGE (`"14"`) |
| `CO_MUN_NOT`, `CO_MUN_RES` | texto | 6 dígitos (`"140010"`) | `ID_MUNICIP`, `ID_MN_RESI` (no SRAG, `ID_MUNICIP` é o **nome**) |
| `DT_NOTIFIC`, `DT_SIN_PRI` | timestamp | — | texto `AAAAMMDD` |
| `SEM_PRI` | texto | semana epidemiológica oficial | serve para conferir a `sem_epi` |
| `TP_IDADE` + `NU_IDADE_N` | texto + decimal | 1 dia, 2 mês, 3 ano | `NU_IDADE_N` = unidade×1000+valor (2 dia, 3 mês, 4 ano) |
| `CS_SEXO`, `CS_RACA`, `HOSPITAL` | texto | iguais ao SINAN | — |
| `CLASSI_FIN`, `CRITERIO` | decimal | 1–5, 1–4 | rótulos abaixo |
| `EVOLUCAO` | texto | 1, 2, 3, 9 | rótulos abaixo |

Rótulos oficiais (dicionário de dados SRAG 2019–2025):
- `CLASSI_FIN`: 1 "SRAG por influenza", 2 "SRAG por outro vírus respiratório", 3 "SRAG por outro agente etiológico", 4 "SRAG não especificado", 5 "SRAG por covid-19". **Vazio = caso ainda em investigação**, muito comum nas últimas semanas.
- `CRITERIO`: 1 "Laboratorial", 2 "Clínico epidemiológico", 3 "Clínico", 4 "Clínico imagem".
- `EVOLUCAO`: 1 "Cura", 2 "Óbito", 3 "Óbito por outras causas", 9 "Ignorado".

## Restrições gerais (de `CLAUDE.md`)

- Regras de autoria e de commits: seguir a seção 1 do `CLAUDE.md`.
- Branch `feature/srag` criada a partir da `develop`. Um commit por assunto, com mensagem em português (título no imperativo e corpo com o quê e o porquê).
- Antes de cada commit: `uv run pytest` e `uv run ruff check .` passando.
- Só licenças permissivas. Este plano não adiciona dependências.
- Os dados salvos mantêm os códigos originais. Os rótulos entram só nas colunas derivadas, como acontece com o `.cnv` no SINAN.
- O modo local tem que continuar funcionando com dois cliques e sem internet depois do download.
- No modo publicado, o SRAG não aparece nem responde a nenhuma rota (decisão da issue: "só no modo local").
- Os textos da tela ficam em português simples: "Síndrome respiratória aguda grave (SRAG)", sem "INFLUD" nem códigos.
- Rotas pesadas continuam síncronas (`def`). O SQL continua recebendo valores só por parâmetro.
- **Imports sem ciclo:** `download` importa `srag`, então `srag` **não** importa `download` (importa só `config`, `processar` e `agravos`). O `pipeline` usa `from . import srag` e chama `srag.baixar(...)`/`srag.processar(...)` pelo módulo, para o monkeypatch dos testes funcionar.

## Foco da revisão

1. **Publicação conjunta de todos os anos** (como em 23-03-2026). Nenhum ano deve ser baixado de novo nem aparecer como "nova" na tela se a data do arquivo dele não mudou. O teste fica na Tarefa 3.
2. **FTP do DATASUS fora do ar com o OpenDataSUS no ar, e o contrário.** A fonte que respondeu atualiza a listagem, e a outra mantém o que estava salvo. O teste fica na Tarefa 3.
3. **Ano antigo com outros tipos no Parquet** (datas em texto `dd/mm/aaaa` ou `date32`, idade em texto). A conversão deve dar a mesma data, semana e idade. O teste fica na Tarefa 2.
4. **Página do ano seguinte ainda inexistente ou já criada em janeiro.** A descoberta usa a primeira página que tiver arquivos. O teste fica na Tarefa 3.
5. **Painel publicado acessado por URL direta (`?agravo=SRAG`).** A resposta é 400 com a mensagem exata, e o SRAG não aparece no `/api/meta`. O teste fica na Tarefa 4.

---

### Tarefa 1: catálogo e rótulos do SRAG

**Arquivos:**
- Modificar: `sinan/agravos.py` (campos novos `rotulos` e `sem_classificacao`, entrada `SRAG`, conjunto `SO_LOCAL`)
- Modificar: `sinan/processar.py` (`derivar`)
- Teste: `tests/test_processar.py`

**Interfaces:**
- Produz:
  - `Agravo.rotulos: Mapping[str, Mapping[str, str]] | None = field(default=None, compare=False, hash=False)` (campo → código → rótulo). No catálogo, o valor é guardado em `types.MappingProxyType` para o dataclass `frozen` continuar realmente imutável.
  - `Agravo.sem_classificacao: str = "Ign/Branco"`: rótulo de `classificacao` quando o `CLASSI_FIN` está vazio.
  - `agravos.SO_LOCAL: frozenset[str] = frozenset({"SRAG"})`.
  - `AGRAVOS["SRAG"]` com `nome="Síndrome respiratória aguda grave (SRAG)"`, `arquivo_def=None`, `todos_casos=True` (toda ficha do SIVEP-Gripe já é um caso de SRAG hospitalizado ou óbito), `sem_classificacao="Em investigação"`, os `rotulos` da seção "Fonte de dados" e um `aviso` em português simples: os dados vêm do SIVEP-Gripe (OpenDataSUS), incluem só casos internados ou óbitos, e os dois últimos anos mudam toda semana.

- [ ] **Passo 1: escrever o teste que falha**

```python
def test_derivar_srag_usa_rotulos_proprios():
    df = _ficha_dengue(CLASSI_FIN=["5", "1", None], CRITERIO=["1", "3", None],
                       EVOLUCAO=["2", "3", "1"], HOSPITAL=["1", "2", "9"])
    out = derivar(df, cat.obter("SRAG"), 2026)
    assert out["classificacao"].tolist() == ["SRAG por covid-19", "SRAG por influenza", "Em investigação"]
    assert out["criterio_confirmacao"].tolist()[:2] == ["Laboratorial", "Clínico"]
    assert out["obito"].tolist() == [True, False, False]   # óbito por outras causas não conta
    assert set(out["situacao"]) == {"Notificado"} and out["confirmado"].all()
    assert out["hospitalizado"].tolist() == ["Sim", "Não", "Ign/Branco"]

def test_classificacao_vazia_continua_ign_branco_no_sinan():
    out = derivar(_ficha_dengue(CLASSI_FIN=[None]), cat.obter("DENG"), 2024)
    assert out["classificacao"].iloc[0] == "Ign/Branco"
```

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest tests/test_processar.py -k "srag or ign_branco" -v`. Resultado esperado: o teste do SRAG falha na primeira asserção, porque `obter("SRAG")` cai no agravo genérico (`notindivinet.def`). O de dengue já passa e serve de proteção.
- [ ] **Passo 3: implementar.** Em `derivar`, troque o `{}` passado ao `_mapear` de `CLASSI_FIN`, `CRITERIO` e do campo de evolução por `(agravo.rotulos or {}).get(<campo>, {})`. O `.def` continua tendo prioridade, porque o `_mapear` só usa o dicionário quando o conversor é `None`. Depois do mapeamento: `out["classificacao"] = out["classificacao"].mask(classi.isna(), agravo.sem_classificacao)`, só quando `classi is not None`. O `_mapear` troca qualquer vazio por "Ign/Branco", então a troca precisa vir depois dele.
- [ ] **Passo 4: rodar e ver passar.** `uv run pytest tests/test_processar.py -v`: todos passam.
- [ ] **Passo 5: commit.** `git add sinan/agravos.py sinan/processar.py tests/test_processar.py`, com a mensagem "Adiciona o SRAG ao catálogo com os rótulos do SIVEP-Gripe". No corpo, explique por que um `CLASSI_FIN` vazio vira "Em investigação" no SRAG.

### Tarefa 2: converter o Parquet do SIVEP-Gripe para o formato do painel

**Arquivos:**
- Criar: `sinan/srag.py`
- Modificar: `sinan/processar.py` (separa a gravação e o inventário do `processar_dbc`)
- Modificar: `tests/conftest.py` (`srag` em `_redirecionar`; fixtures `amostra_srag` e `dados_srag`)
- Teste: `tests/test_srag.py`

**Interfaces:**
- Consome: `Agravo.rotulos`, `Agravo.sem_classificacao` e `AGRAVOS["SRAG"]` (Tarefa 1).
- Produz em `sinan/processar.py`:
  - `gravar_parquet(lotes: Iterable[tuple[pd.DataFrame, pd.DataFrame]], agravo: cat.Agravo, ano: int, colunas: list[str]) -> int`: cada item é `(bruto, para_derivar)`. Grava em `.tmp`, troca de uma vez, cria o arquivo vazio com o esquema completo quando não há registros e apaga o `.tmp` se der erro. É o trecho que hoje está dentro de `processar_dbc`. **O `processar_dbc` continua dono do `iterar_dbf`:** ele passa `((l.reset_index(drop=True),) * 2 for l in lotes)` e mantém o `lotes.close()` no seu `finally`, antes do `unlink` do `.dbf`. Fechar o gerador externo não fecha o `iterar_dbf`, e no Windows o `.dbf` mapeado ficaria preso.
  - `registrar_inventario(agravo: str, ano: int, total: int, ufs: list[str], info: dict, arquivo: str) -> None`: o bloco final do `processar_dbc`, sem mudança.
- Produz em `sinan/srag.py`:
  - `para_sinan(df: pd.DataFrame) -> pd.DataFrame`: uma cópia com os nomes e formatos que o `derivar` espera. `DT_NOTIFIC`/`DT_SIN_PRI` viram `AAAAMMDD`, `ID_MUNICIP` ← `CO_MUN_NOT`, `ID_MN_RESI` ← `CO_MUN_RES`, `SG_UF_NOT`/`SG_UF` viram código IBGE (`config.UF_COD`), `NU_IDADE_N` ← `(TP_IDADE+1)*1000 + NU_IDADE_N`, e os demais campos ficam como estão.
  - `processar(caminho: Path, ano: int, ufs: list[str], info: dict | None = None, progresso: Callable[[float, str], None] | None = None) -> int`: lê com `pq.ParquetFile(caminho).iter_batches(batch_size=20_000)`. Com cerca de 190 colunas, um lote de 100 mil linhas passaria de 1 GB em textos no pandas quando a escolha é "BR". Filtra com `pyarrow.compute` as linhas com `SG_UF` **ou** `SG_UF_NOT` nas UFs pedidas (sem filtro quando `"BR"` está em `ufs`) e converte todas as colunas para texto:
    - colunas com `pa.types.is_temporal(tipo)` (timestamp **e** date32): `pc.strftime(col, "%Y-%m-%d")`, porque um cast direto daria `"2026-05-09 00:00:00.000000"`;
    - `pa.types.is_decimal(tipo)`: `pc.cast(col, pa.int64(), safe=False)` e depois texto, porque `decimal128(38,10)` viraria `"1.0000000000"` e os rótulos de chave `"1"` não pegariam;
    - o resto: `pa.string()`.

    Depois chama `gravar_parquet(((bruto, para_sinan(bruto)) ...), AGRAVOS["SRAG"], ano, colunas)` e `registrar_inventario`.
- Produz em `tests/conftest.py`:
  - `escrever_amostra_srag(caminho: Path, antiga: bool = False) -> Path`: um Parquet **sem dado real**, com 6 linhas (3 de RR e 3 de SP). Inclui `SEM_PRI` com a semana correta de cada data (ex.: 2026-05-09 → `"18"`, 2026-01-01 → `"53"`). Com `antiga=False`, usa os tipos de 2026: datas em timestamp, `CLASSI_FIN` em `decimal128(38, 10)` (o pior caso) e `NU_IDADE_N` em decimal. Com `antiga=True`, `DT_SIN_PRI` vem em texto `dd/mm/aaaa`, `DT_NOTIFIC` em `date32` e `NU_IDADE_N`/`CLASSI_FIN` em texto.
  - fixture `amostra_srag(tmp_path) -> Path`, que chama `escrever_amostra_srag(tmp_path / "INFLUD26.parquet")`;
  - fixture `dados_srag(tmp_path, monkeypatch) -> Path`: pasta própria com `_redirecionar(monkeypatch, tmp_path / "dados")` e `cache.limpar()` antes e depois. **Nunca** a `dados_teste` da sessão.

- [ ] **Passo 1: escrever os testes que falham** (`tests/test_srag.py`)

```python
def test_para_sinan_converte_uf_municipio_data_e_idade():
    df = pd.DataFrame({"SG_UF_NOT": ["RR"], "SG_UF": ["RR"], "CO_MUN_NOT": ["140010"],
                       "CO_MUN_RES": ["140010"], "DT_SIN_PRI": ["2026-05-09"],
                       "DT_NOTIFIC": ["2026-05-12"], "TP_IDADE": ["2"], "NU_IDADE_N": ["3"]})
    s = srag.para_sinan(df)
    assert s.loc[0, ["SG_UF", "ID_MN_RESI", "DT_SIN_PRI", "NU_IDADE_N"]].tolist() == \
        ["14", "140010", "20260509", "3003"]        # dia 9 de maio, não 5 de setembro
    assert df.loc[0, "SG_UF"] == "RR"             # o original não é alterado

def test_para_sinan_aceita_data_em_texto_brasileiro_e_idade_vazia():
    df = pd.DataFrame({"SG_UF": ["RR"], "DT_SIN_PRI": ["09/05/2026"], "TP_IDADE": [None], "NU_IDADE_N": [None]})
    s = srag.para_sinan(df)
    assert s.loc[0, "DT_SIN_PRI"] == "20260509" and pd.isna(s.loc[0, "NU_IDADE_N"])

@pytest.mark.parametrize("antiga", [False, True])
def test_processar_srag_filtra_uf_e_deriva(dados_srag, tmp_path, antiga):
    amostra = escrever_amostra_srag(tmp_path / "amostra.parquet", antiga)
    n = srag.processar(amostra, 2026, ["RR"], {"arquivo": "INFLUD26-23-11-2026.parquet",
                       "situacao": "preliminar", "data_ftp": "23-11-2026"})
    t = pq.read_table(processar.caminho_parquet("SRAG", 2026)).to_pandas()
    assert n == len(t) == 3
    assert set(t["uf_res"]) == {"RR"} and t["SG_UF"].eq("RR").all()   # original em sigla
    assert t["CLASSI_FIN"].iloc[0] == "5" and t["classificacao"].iloc[0] == "SRAG por covid-19"
    assert (t["sem_epi"].astype(str) == t["SEM_PRI"]).all()           # mesma regra do SIVEP
    assert t["idade"].notna().all() and t["data_sintomas"].notna().all()
    assert processar.ler_inventario()["SRAG_2026"]["data_ftp"] == "23-11-2026"

def test_processar_srag_uf_sem_casos_gera_arquivo_vazio(dados_srag, amostra_srag):
    assert srag.processar(amostra_srag, 2026, ["AC"]) == 0
    nomes = pq.read_schema(processar.caminho_parquet("SRAG", 2026)).names
    assert {"CLASSI_FIN", "SG_UF", "CO_MUN_RES", "hospitalizado"} <= set(nomes)   # originais + derivadas
```

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest tests/test_srag.py -v`. Resultado esperado: FAIL com `ModuleNotFoundError: sinan.srag`.
- [ ] **Passo 3: implementar** `gravar_parquet` e `registrar_inventario`, extraídos de `processar_dbc` com o mesmo tratamento de erro. Depois implementar `sinan/srag.py` e acrescentar `srag` à tupla de módulos de `_redirecionar` (`tests/conftest.py:31`). **Datas em `para_sinan`:** primeiro `pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")`; o que sobrar vazio é preenchido com `format="%d/%m/%Y"`. Não use `dayfirst=True` com `format="mixed"`, porque `"2026-05-09"` viraria 5 de setembro.
- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -v`: tudo passa, inclusive `test_processar_dbc_filtra_ufs` e os dois testes do inventário, que garantem que a extração não mudou o comportamento do SINAN.
- [ ] **Passo 5: commit.** "Converte o Parquet do SIVEP-Gripe para o formato do painel". No corpo, explique que o SRAG reaproveita as colunas derivadas e por isso aparece em todas as telas.

### Tarefa 3: listar e baixar o SRAG, independente do FTP

**Arquivos:**
- Modificar: `sinan/srag.py`, `sinan/download.py` (`listar_ftp`), `sinan/pipeline.py` (`atualizar`, `precisa_atualizar`), `sinan/api/rotas/dados.py` (`_situacao_dados`), `sinan/config.py` (`SRAG_PAGINA`)
- Criar: `tests/fixtures/srag_pagina.html`. É o HTML real da página, salvo **antes** de escrever `ler_listagem` com `curl -s https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026 -o tests/fixtures/srag_pagina.html`. São cerca de 88 KB, só com metadados públicos. Confira que ele tem `"url":"https://s3...INFLUD26-...parquet"`.
- Teste: `tests/test_srag.py`

**Interfaces:**
- Consome: `srag.processar` (Tarefa 2).
- Produz:
  - `config.SRAG_PAGINA = "https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026"`: a última opção da descoberta.
  - `srag.paginas(hoje: date) -> list[str]`: devolve `[.../srag-2019-a-{hoje.year + 1}, .../srag-2019-a-{hoje.year}, SRAG_PAGINA]`, sem repetidos e nessa ordem.
  - `srag.ler_listagem(html: str) -> dict[str, dict]`: busca com a regex `"url":"(https://[^"]+/SRAG/(\d{4})/INFLUD\d{2}-(\d{2}-\d{2}-\d{4})\.parquet)"`, que captura a URL inteira, e devolve `{"2026": {"arquivo": <url completa>, "situacao": ..., "tamanho": 0, "data_ftp": "23-11-2026"}}`.
    - Se o mesmo ano aparecer duas vezes, vale a data mais recente, comparada **como data** (`datetime.strptime(d, "%d-%m-%Y")`), nunca como texto: comparando o texto, `"23-11-2026"` sairia maior que `"16-12-2026"`.
    - A `situacao` serve **só para exibir**: "preliminar" para os dois anos mais recentes da página e "final" para os outros.
  - `srag.listar(hoje: date | None = None) -> dict[str, dict]`: tenta cada endereço de `paginas()` (`urllib.request`, timeout de 60 s) e devolve o primeiro `ler_listagem` que não vier vazio. Uma página inexistente redireciona para a lista geral e volta vazia. Se nenhuma servir, levanta `ConnectionError`.
  - `srag.baixar(info: dict, progresso: Callable[[int, int], None] | None = None, tentativas: int = 4) -> Path`: grava em `PASTA_BRUTOS/<nome do arquivo>.parcial` e só troca para o nome final quando o tamanho recebido bate com o `Content-Length`. Comentário obrigatório: `# shortcut: sem retomada (Range); se os anos grandes (2020–2021) falharem muito, retomar como em download.baixar_arquivo`.
  - `download.listar_ftp()` passa a juntar duas fontes consultadas **separadamente**:
    - `_listar_sinan() -> dict` é o laço do FTP de hoje, e `srag.listar()` é a do SRAG;
    - a parte que falhar é copiada da `listagem_salva()`, quando existir, e seu nome entra em `listagem["falhas"]`: `"DATASUS (FTP)"` ou `"OpenDataSUS (SRAG)"`;
    - só quando **as duas** falham é que levanta o erro. O `/api/dados/listar` só devolve 502 nesse caso.
  - `pipeline.arquivo_mudou(agravo: str, salvo: dict, novo: dict) -> bool`:
    - no SRAG, compara **só** a `data_ftp`;
    - nos outros agravos, compara `data_ftp` ou `situacao`, como hoje.

    É usada pelo `precisa_atualizar` e pelo `_situacao_dados` (`sinan/api/rotas/dados.py:75`) para marcar "nova". Assim uma publicação conjunta de todos os anos não manda baixar de novo nem acusa "nova" sem motivo.
  - Em `pipeline.atualizar`, quando `agravo == "SRAG"`, usa `srag.baixar(info, prog_download)` e `srag.processar(...)` no lugar de `baixar_arquivo`/`processar_dbc`. O resto (contagem, apagar o bruto) continua igual.

- [ ] **Passo 1: salvar a fixture HTML e escrever os testes que falham**

```python
PAGINA = (Path(__file__).parent / "fixtures" / "srag_pagina.html").read_text(encoding="utf-8")

def test_ler_listagem_na_pagina_real():
    l = srag.ler_listagem(PAGINA)
    assert {"2019", "2024", "2026"} <= set(l)
    assert l["2026"]["arquivo"].startswith("https://s3.") and l["2026"]["arquivo"].endswith(".parquet")
    assert l["2026"]["situacao"] == "preliminar" and l["2019"]["situacao"] == "final"

def test_ler_listagem_compara_datas_como_data():
    html = '"url":"https://x/SRAG/2026/INFLUD26-16-12-2026.parquet" "url":"https://x/SRAG/2026/INFLUD26-23-11-2026.parquet"'
    assert srag.ler_listagem(html)["2026"]["data_ftp"] == "16-12-2026"

def test_listar_usa_a_primeira_pagina_com_arquivos(monkeypatch):
    # urlopen falso: 2027 devolve a lista geral (sem arquivos), 2026 devolve PAGINA
    assert srag.listar(date(2026, 11, 23))["2026"]["data_ftp"] == "23-11-2026"

def test_publicacao_conjunta_nao_manda_baixar_de_novo():
    salvo = {"data_ftp": "23-03-2026", "situacao": "final"}
    assert not pipeline.arquivo_mudou("SRAG", salvo, {"data_ftp": "23-03-2026", "situacao": "preliminar"})
    assert pipeline.arquivo_mudou("SRAG", salvo, {"data_ftp": "30-03-2026", "situacao": "final"})
    assert pipeline.arquivo_mudou("DENG", salvo, {"data_ftp": "23-03-2026", "situacao": "preliminar"})

def test_listar_ftp_mantem_srag_salvo_quando_o_opendatasus_falha(dados_srag, monkeypatch):
    # _listar_sinan falso devolve {"DENG": {...}}; download.srag.listar levanta ConnectionError;
    # listagem salva tinha "SRAG": {"2026": {"data_ftp": "16-11-2026", ...}}
    l = download.listar_ftp()
    assert l["arquivos"]["SRAG"]["2026"]["data_ftp"] == "16-11-2026" and "DENG" in l["arquivos"]
    assert l["falhas"] == ["OpenDataSUS (SRAG)"]

def test_listar_ftp_atualiza_srag_quando_o_ftp_falha(dados_srag, monkeypatch):
    # _listar_sinan falso levanta ConnectionError; listagem salva tinha "DENG"; srag.listar devolve 2026
    l = download.listar_ftp()
    assert l["arquivos"]["SRAG"]["2026"]["data_ftp"] == "23-11-2026" and "DENG" in l["arquivos"]
    assert l["falhas"] == ["DATASUS (FTP)"]

def test_listar_ftp_falha_so_com_as_duas_fontes_fora(dados_srag, monkeypatch):
    with pytest.raises(ConnectionError):
        download.listar_ftp()

def test_baixar_interrompido_nao_deixa_arquivo_final(dados_srag, monkeypatch):
    # urlopen falso: Content-Length 100, entrega 40 bytes e levanta OSError
    with pytest.raises(ConnectionError):
        srag.baixar({"arquivo": "https://x/SRAG/2026/INFLUD26-23-11-2026.parquet"}, tentativas=1)
    assert not (srag.PASTA_BRUTOS / "INFLUD26-23-11-2026.parquet").exists()

def test_atualizar_srag_usa_o_caminho_proprio(dados_srag, amostra_srag, monkeypatch):
    # monkeypatch em pipeline.listar_ftp (o pipeline importa o nome direto) com "SRAG": {"2026": info};
    # monkeypatch em srag.baixar devolvendo uma cópia de amostra_srag
    res = pipeline.atualizar(["SRAG"], [2026], ["RR"])
    assert res.sucesso == ["Síndrome respiratória aguda grave (SRAG) 2026: 3 registros"]
    assert pipeline.atualizar(["SRAG"], [2026], ["RR"]).pulados   # mesma data: não baixa de novo
```

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest tests/test_srag.py -v`. Resultado esperado: os testes novos falham com `AttributeError` (`ler_listagem`, `arquivo_mudou`, `baixar`) ou `KeyError: 'SRAG'`.
- [ ] **Passo 3: implementar** conforme as interfaces acima.
- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -v` e `uv run ruff check .`.
- [ ] **Passo 5: conferir de verdade, com aviso ao usuário antes** (cerca de 20 MB): `SINAN_DADOS=<scratchpad>/dados uv run python baixar_dados.py --agravos SRAG --anos 2026 --ufs RR`.
  - Resultado esperado: `OK  Síndrome respiratória aguda grave (SRAG) 2026: N registros`, com N > 0. Rodando de novo, sai `Atualizado ... (nada mudou no DATASUS)`.
  - No Parquet gerado, a proporção de linhas com `sem_epi` igual a `SEM_PRI` (entre as que têm `DT_SIN_PRI`) tem que ser de 100% ou explicada linha a linha.
- [ ] **Passo 6: commit.** "Baixa o SRAG do OpenDataSUS sem depender do FTP do DATASUS". No corpo, diga que uma fonte fora do ar não trava a outra e que uma republicação sem mudança não baixa de novo.

### Tarefa 4: o SRAG fica só no modo local

**Arquivos:**
- Modificar: `sinan/api/filtros.py` (`contexto`), `sinan/api/rotas/meta.py` (`api_meta`), `sinan/api/rotas/variaveis.py`
- Modificar: `tests/conftest.py` (fixtures `cliente_local_com_srag` e `cliente_publico_com_srag`, com pasta própria e um `SRAG_2026.parquet` gerado pela amostra da Tarefa 2 com `srag.processar`, e `cache.limpar()` antes e depois, porque o cache guarda por agravo, sem a pasta)
- Teste: `tests/test_publicacao.py`

**Interfaces:**
- Consome: `agravos.SO_LOCAL` (Tarefa 1).
- Produz:
  - No modo publicado, `contexto()` e a rota de variáveis levantam `ErroUsuario(f"{cat.nome(agravo)} só está disponível no painel instalado no computador.")` quando `agravo in SO_LOCAL`. Isso cobre `/visao`, `/mapa`, `/perfil`, `/variavel`, `/registros` e `/exportar`, que usam `Filtros`, além de `/variaveis`.
  - O `api_meta` pula os códigos de `SO_LOCAL` dentro do laço (`meta.py:24`), antes do `ufs_presentes` e do cálculo de `atualizado_em`, que passa a considerar só o inventário dos agravos mostrados.
  - No modo local nada muda.

- [ ] **Passo 1: escrever os testes que falham**

```python
def test_publico_esconde_srag(cliente_publico_com_srag):
    meta = cliente_publico_com_srag.get("/api/meta", headers=H).json()
    assert "SRAG" not in [a["codigo"] for a in meta["agravos"]]
    r = cliente_publico_com_srag.get("/api/visao?agravo=SRAG", headers=H)
    assert r.status_code == 400
    assert r.json()["erro"] == "Síndrome respiratória aguda grave (SRAG) só está disponível no painel instalado no computador."
    assert cliente_publico_com_srag.get("/api/variaveis?agravo=SRAG", headers=H).status_code == 400

def test_local_mostra_srag(cliente_local_com_srag):
    assert "SRAG" in [a["codigo"] for a in cliente_local_com_srag.get("/api/meta").json()["agravos"]]
    assert cliente_local_com_srag.get("/api/visao?agravo=SRAG").status_code == 200
```

- [ ] **Passo 2: rodar e ver falhar.** `uv run pytest tests/test_publicacao.py -v`. Resultado esperado: `test_publico_esconde_srag` falha (o SRAG aparece no meta e a visão responde 200).
- [ ] **Passo 3: implementar** conforme a interface. O teste vai às rotas por URL direta, então o bloqueio precisa estar nas rotas, não só na lista do meta.
- [ ] **Passo 4: rodar e ver passar.** `uv run pytest -v`.
- [ ] **Passo 5: commit.** "Mantém o SRAG fora do painel publicado".

### Tarefa 5: textos, avisos na tela e conferência

**Arquivos:**
- Modificar: `web/js/paginas/sobre.js` (lista de cuidados), `web/js/paginas/atualizar.js` (aviso de falha e de estimativa), `README.md` (fontes e exemplo do `baixar_dados.py`), `sinan/api/rotas/dados.py` (`_situacao_dados` devolve `listagem_falhas`)
- Modificar: `CLAUDE.md` (comando do servidor de teste), em commit separado

- [ ] **Passo 1: textos.** Em "Sobre os dados", acrescente um item: "Síndrome respiratória aguda grave (SRAG) vem do SIVEP-Gripe (OpenDataSUS), não do SINAN. Inclui só casos internados ou óbitos, e os anos mais recentes mudam toda semana. Casos sem classificação aparecem como \"Em investigação\". Disponível apenas no painel instalado no computador." No README, acrescente o SRAG às fontes, com o exemplo `--agravos SRAG`.
- [ ] **Passo 2: avisos em "Atualizar dados".**
  - `_situacao_dados` passa a devolver `"listagem_falhas": (listagem or {}).get("falhas", [])`. Com essa lista preenchida, `atualizar.js` mostra, junto da data da listagem: "Não foi possível consultar agora: DATASUS (FTP). Mostrando a última lista salva dessa fonte.".
  - Quando algum agravo marcado tiver tamanho 0 para algum ano, a estimativa de download ganha o complemento "(sem estimativa para: <nomes>)".
  - Teste em `tests/test_api.py`: `GET /api/dados` devolve `listagem_falhas == []` quando a listagem salva não tem `falhas`.
- [ ] **Passo 3: commit.** "Explica a origem do SRAG e avisa quando uma fonte não respondeu".
- [ ] **Passo 4: corrigir o `CLAUDE.md`.** No comando do servidor de teste, troque `from sinan.web import app` por `from sinan.api import app` (o módulo `sinan.web` não existe mais). Commit: "Corrige o comando do servidor de teste no CLAUDE.md".
- [ ] **Passo 5: conferir na tela.** Com os dados da Tarefa 3, suba o servidor na porta 8599 com o comando corrigido e `timeout 75`, e tire capturas com o navegador sem janela de:
  - "Atualizar dados": o SRAG aparece no catálogo com os anos, e o complemento "sem estimativa" aparece ao marcá-lo;
  - "Visão geral" com SRAG/RR 2026: curva semanal, total e mapa sem erro;
  - "Perfil": classificação com "SRAG por covid-19" e "Em investigação", e nenhum código cru.

  Relate o que não estiver certo.
- [ ] **Passo 6:** `uv run pytest` e `uv run ruff check .`. Resultado esperado: tudo passa (o `tests/test_interface.py` confere os imports).

## Fora deste plano (de propósito)

- **"Outras variáveis" para o SRAG:** a tela depende do `.def` do TabNet, que não existe para o SIVEP-Gripe, e por isso a lista fica vazia. Ela só entra se alguém pedir, com um `.def` próprio.
- **Tamanho real do download do SRAG:** a página traz `"size": null`. Um `HEAD` por ano daria o tamanho, mas custaria cerca de 8 pedidos a cada listagem. Por enquanto fica só o aviso "sem estimativa".
- **Retomada do download do SRAG pela metade:** fica com o comentário `shortcut:` da Tarefa 3.
- **SIVEP-Malária e território do e-SUS APS:** ficam para planos próprios, com o botão de importar arquivo, quando houver arquivo de exemplo e o aval do encarregado de dados.
