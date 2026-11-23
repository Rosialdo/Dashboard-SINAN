# Fase 0 — Publicação só de leitura: plano de implementação

**Situação:** concluído (PRs #5 a #13).

> **Como executar:** uma tarefa por vez, marcando as caixas (`- [ ]`). Cada tarefa tem a sua branch e
> termina com testes passando, um commit e o PR para a `develop`.

**Objetivo:** deixar o painel pronto para ser publicado na VPS do grupo PRISM/UFRR como site aberto,
só de leitura e só com números agregados, sem quebrar o modo local.

**Abordagem:** a variável de ambiente `SINAN_MODO=publico` liga o modo publicado. O modo é decidido
**uma vez**, em `criar_app()`, e guardado em `app.state`: o servidor aceita o domínio configurado,
não monta as rotas de administração nem as de fichas, informa à interface quais telas esconder e
não mostra detalhes de erros. Sem a variável, tudo continua como hoje. Os dados são atualizados por
um script chamado pelo cron.

**Stack:** Python 3.12, FastAPI/Starlette, Uvicorn, DuckDB, interface em módulos JS nativos; pytest e ruff.

**Especificação:** `docs/analise/2026-11-analise-e-roadmap.md`, seção 7 (decisões de 17/11/2026),
mais as fichas N01, N04, N05, N08 e N09 da seção 4.

## Restrições globais

- O modo local não muda: sem `SINAN_MODO`, todas as rotas, telas e textos continuam iguais, e os
  testes atuais passam sem alteração.
- No modo publicado nenhuma ficha individual sai do servidor: `/api/registros`, exportação de fichas
  (`xlsx`, `csv`, `csv_completo`), `/api/dados/*` e `/api/docs` não existem ou recusam o pedido.
- Não afrouxar o `ProtecaoLocal`: outro domínio só é aceito se estiver em `SINAN_HOSTS`, e só no modo publicado.
- O modo é lido do ambiente só em `criar_app()`. Rotas usam `request.app.state.publico`, nunca `config.publico()`.
- Testes nunca recarregam o módulo `config` (`importlib.reload`): isso desfaz a pasta temporária do
  `tests/conftest.py` e faz os testes lerem a pasta `dados/` real.
- Nenhuma dependência nova. Textos de tela em português simples.
- Antes de cada commit: `uv run pytest` e `uv run ruff check .`. Mensagem em português, sem coautoria
  nem menção a IA.

## Ordem e branches

| Ordem | Tarefa | Branch | Sai de |
|---|---|---|---|
| 0 | Decisões no relatório e este plano | `docs/decisoes-publicacao` (já existe) | `develop` |
| 1 | Domínio configurável | `feature/endereco-publico` | `develop` com a Tarefa 0 |
| 2 | Modo publicado no servidor | `feature/modo-publico` | `develop` com a Tarefa 1 |
| 3 | Modo publicado na interface | `feature/interface-publica` | `develop` com a Tarefa 2 |
| 4 | Contorno do mapa sem cópias por combinação | `feature/geo-sem-copias` | `develop` (independente) |
| 5 | Contraste e cores do mapa | `feature/contraste-cores` | `develop` (independente) |
| 6 | Inventário gravado de forma segura | `correcao/inventario-atomico` | `develop` (independente) |
| 7 | Guia de implantação, script do cron e medição | `feature/guia-implantacao` | `develop` com todas as anteriores |

**As Tarefas 1, 2 e 3 dependem umas das outras:** cada uma só começa depois que a anterior foi
juntada na `develop`. Ao fim de cada uma: `push`, PR para a `develop` e esperar o merge autorizado pelo
usuário. As Tarefas 4, 5 e 6 podem andar em paralelo, a qualquer momento.

## Variáveis de ambiente (contrato entre as tarefas)

| Variável | Valor | Lida por |
|---|---|---|
| `SINAN_MODO` | `publico` liga o modo publicado; qualquer outro valor ou ausente = local | `config.publico()`, chamada só em `criar_app()` |
| `SINAN_HOSTS` | domínios aceitos, separados por vírgula, ex.: `painel.prism.ufrr.br`. Sem porta | `config.hosts_publicos()` |
| `SINAN_DADOS` | pasta de dados; ausente = `<raiz>/dados` | `config._pasta_dados()` na carga do módulo |

## Foco de revisão

1. **Proxy que repassa o host local** (`Host: 127.0.0.1:8501`) com `Origin: https://painel...`: os GET
   precisam passar. Teste na Tarefa 1.
2. **Ficha por outro caminho**: `/api/exportar?formato=xlsx`, `csv` e `csv_completo` recusados no modo
   publicado, `municipios` aceito. Teste na Tarefa 2.
3. **Tela local aberta pelo endereço** (`#/dados`, `#/atualizar`) no modo publicado: cai na Visão geral,
   sem erro. Verificação na Tarefa 3.
4. **Configuração errada na VPS** (`SINAN_HOSTS` vazio, com porta ou com espaços): o servidor não sobe
   e diz o motivo. Teste na Tarefa 1.
5. **Cron rodando enquanto alguém consulta**: nenhuma resposta 500 e nenhuma tela "dados ainda não
   foram carregados". Coberto pelas Tarefas 6 e 7.

---

### Tarefa 0: Decisões no relatório

Branch: `docs/decisoes-publicacao` (já criada, com a seção 7 do relatório, o `CLAUDE.md` com os dois
modos e este plano).

- [ ] **Passo 1:** `push` e PR para a `develop`.
- [ ] **Passo 2:** esperar o merge. Conferir que `docs/analise/2026-11-analise-e-roadmap.md` na `develop`
  tem a seção `## 7. Decisões tomadas (17/11/2026)`.

### Tarefa 1: Domínio configurável e pasta de dados (N01)

Branch: `feature/endereco-publico`

**Arquivos:**
- Modificar: `sinan/config.py`, `sinan/api/seguranca.py`, `sinan/api/app.py`
- Testar: novo `tests/test_publicacao.py`

**Interfaces:**
- Produz:
  - `config._pasta_dados(ambiente: Mapping[str, str]) -> Path` (função pura); `PASTA_DADOS = _pasta_dados(os.environ)`.
  - `config.publico() -> bool` e `config.hosts_publicos() -> set[str]`, que lê `SINAN_HOSTS`, tira
    espaços, passa para minúsculas, ignora itens vazios e lança `ValueError` se algum item tiver `:` (porta).
  - `criar_app()` grava `app.state.publico: bool` e `app.state.hosts: set[str]`. Com modo publicado e
    nenhum host, lança `RuntimeError("SINAN_MODO=publico exige SINAN_HOSTS com o domínio do painel, ex.: painel.prism.ufrr.br")`.
  - `ProtecaoLocal(app, hosts_extras: frozenset[str] = frozenset())`.
  - Fixture `cliente_publico` em `tests/test_publicacao.py`: com `monkeypatch.setenv("SINAN_MODO", "publico")`
    e `SINAN_HOSTS=painel.exemplo.br`, monta `criar_app()` e devolve `TestClient(app, base_url="https://painel.exemplo.br")`.
    Depende de `dados_teste`. As Tarefas 2 e 4 usam este fixture.

- [ ] **Passo 1: Testes que falham**, em `tests/test_publicacao.py`:
  - `test_publico_aceita_dominio_configurado`: `GET /api/meta` com `Origin: https://painel.exemplo.br` → 200.
  - `test_publico_recusa_outro_dominio`: `Host: outro.br` → 403.
  - `test_publico_aceita_host_local_do_proxy`: `Host: 127.0.0.1:8501` e `Origin: https://painel.exemplo.br` → 200.
  - `test_publico_recusa_post`: `POST /api/meta` com JSON → 403 (só GET, HEAD e OPTIONS no modo publicado).
  - `test_publico_sem_hosts_nao_sobe`: `SINAN_MODO=publico`, `SINAN_HOSTS=""` → `criar_app()` lança `RuntimeError` com "SINAN_HOSTS".
  - `test_hosts_normalizados`: `SINAN_HOSTS=" Painel.Exemplo.BR , ,b.br"` → `{"painel.exemplo.br", "b.br"}`;
    `SINAN_HOSTS="a.br:443"` → `ValueError`.
  - `test_local_continua_recusando_dominio_de_fora`: sem `SINAN_MODO`, `TestClient` com `base_url="https://painel.exemplo.br"` → 403.
  - `test_pasta_de_dados_pelo_ambiente`: `_pasta_dados({"SINAN_DADOS": "/srv/x"}) == Path("/srv/x")` e
    `_pasta_dados({}) == config.RAIZ / "dados"`.
- [ ] **Passo 2:** `uv run pytest tests/test_publicacao.py -v` → falham.
- [ ] **Passo 3: Implementar.** No `ProtecaoLocal.motivo_bloqueio`: host aceito se estiver em `HOSTS` ou
  em `hosts_extras`; origem aceita se for `http://{host}` ou, com `hosts_extras` não vazio,
  `https://{h}` para algum `h` de `hosts_extras`; com `hosts_extras` não vazio, método diferente de
  GET, HEAD e OPTIONS → "Ação não permitida.". Em `sinan/config.py`, os caminhos derivados
  (`PASTA_BRUTOS`, `PASTA_PARQUET`, `ARQ_*`) continuam calculados a partir de `PASTA_DADOS`.
- [ ] **Passo 4:** `uv run pytest` → tudo passa, com `tests/test_api.py` sem alteração.
- [ ] **Passo 5: Commit** "Permite publicar o painel num domínio configurado"; `push` e PR para a `develop`; esperar o merge.

### Tarefa 2: Modo publicado no servidor (N03' e N05)

Branch: `feature/modo-publico`, criada da `develop` depois do merge da Tarefa 1.

**Arquivos:**
- Modificar: `sinan/api/app.py`, `sinan/api/rotas/registros.py`, `sinan/api/rotas/meta.py`
- Testar: `tests/test_publicacao.py`

**Interfaces:**
- Consome: `app.state.publico` e o fixture `cliente_publico` (Tarefa 1).
- Produz: `/api/meta` devolve `"publico": bool` e `"telas_ocultas": list[str]` (`["dados", "atualizar"]`
  no modo publicado, `[]` no local). A Tarefa 3 usa os dois.

- [ ] **Passo 1: Testes que falham:**
  - `test_publico_sem_rotas_de_administracao`: `GET /api/dados` e `GET /api/dados/status` → 404.
  - `test_publico_sem_fichas`: `GET /api/registros?agravo=ACBI` e `GET /api/exportar?agravo=ACBI&formato=` com
    `xlsx`, `csv` e `csv_completo` → 403, com `erro == "Não disponível na versão publicada do painel."`.
  - `test_publico_exporta_resumo_por_municipio`: `formato=municipios` → 200 e `attachment` no `content-disposition`.
  - `test_publico_sem_documentacao`: `/api/docs` e `/api/openapi.json` → 404.
  - `test_publico_consultas_agregadas_funcionam`: `/api/visao`, `/api/mapa`, `/api/perfil` e `/api/variavel?id=0`, com `agravo=ACBI` → 200.
  - `test_publico_erro_interno_sem_detalhes`: `monkeypatch` faz `servicos.indicadores` lançar
    `RuntimeError("segredo")`; `cache.limpar()`; cliente com `raise_server_exceptions=False`;
    `GET /api/visao?agravo=ACBI` → 500, `segredo` não aparece na resposta, e o erro contém um código de 8 caracteres hexadecimais.
  - `test_meta_informa_o_modo`: `cliente_publico` → `publico is True` e `telas_ocultas == ["dados", "atualizar"]`;
    em outro teste, com o `cliente` de sempre → `publico is False` e `telas_ocultas == []`.
- [ ] **Passo 2:** os testes falham.
- [ ] **Passo 3: Implementar.** Em `criar_app`, com modo publicado: não incluir `dados.router`;
  `docs_url=None`, `openapi_url=None`; o tratador de erro interno devolve
  `"Erro interno (código {c}). Avise a equipe responsável pelo painel."`, com `c = uuid4().hex[:8]`, e
  imprime o código junto com o traceback. As rotas recebem `request: Request` e leem `request.app.state.publico`.
- [ ] **Passo 4:** `uv run pytest` passa.
- [ ] **Passo 5: Commit** "Adiciona o modo publicado, só de leitura e sem fichas"; `push` e PR; esperar o merge.

### Tarefa 3: Modo publicado na interface (N03' e N08)

Branch: `feature/interface-publica`, criada da `develop` depois do merge da Tarefa 2.

**Arquivos:**
- Modificar: `web/js/nucleo/navegacao.js`, `web/js/roteador.js`, `web/js/componentes/cabecalho.js`, `web/js/main.js`

**Interfaces:**
- Consome: `estado.meta.publico` e `estado.meta.telas_ocultas` (Tarefa 2). A regra de quais telas
  somem fica só no servidor; a interface obedece.

- [ ] **Passo 1: Implementar.**
  - `paginaAtual()` trata como inexistente toda tela em `estado.meta?.telas_ocultas` (cai em `visao-geral`);
    `montarMenu()` não lista essas telas.
  - Menu "Exportar" do cabeçalho e botões da tela "Dados": com `estado.meta.publico`, só a opção `municipios`.
  - Textos (exatos):
    - erro sem servidor (`web/js/main.js:51`), nos dois modos, porque nesse momento o modo ainda é
      desconhecido: "Não foi possível carregar o painel. Se ele roda no seu computador, feche e abra de
      novo o ABRIR_DASHBOARD.bat; se for o site, tente de novo em alguns minutos.";
    - sem dados (`web/js/roteador.js:63-65`), com `publico`: título "Os dados ainda não foram carregados",
      texto "O painel é atualizado toda semana. Volte mais tarde.", sem o botão "Atualizar dados";
    - rodapé (`web/js/componentes/cabecalho.js:46`), com `publico`: "Dados atualizados em ..." em vez de "Dados baixados em ...".
- [ ] **Passo 2:** `uv run pytest` passa (o `tests/test_interface.py` confere os `import`).
- [ ] **Passo 3: Conferir na tela.** Subir o servidor de teste (comando da seção 4 do `CLAUDE.md`) com
  `SINAN_MODO=publico SINAN_HOSTS=localhost SINAN_DADOS=<pasta temporária com dados>`: o menu tem 5 telas;
  `#/dados` e `#/atualizar` abrem a Visão geral; o Exportar tem só o resumo por município. Capturar a
  Visão geral e o menu Exportar. Repetir sem `SINAN_MODO`: o menu tem as 7 telas.
- [ ] **Passo 4: Commit** "Adapta a interface ao modo publicado"; `push` e PR; esperar o merge.

### Tarefa 4: Contorno do mapa sem cópias por combinação (N04, lacuna G10)

Branch: `feature/geo-sem-copias`

**Arquivos:** modificar `sinan/api/rotas/meta.py:49-61`; testar `tests/test_api.py`.

- [ ] **Passo 1: Testes que falham:**
  - `test_geo_recusa_uf_desconhecida`: `GET /api/geo?ufs=ZZ` → 400, com "UF" no `erro`.
  - `test_geo_memoria_limitada`: depois de 50 pedidos com combinações válidas diferentes de UFs
    (ex.: pares de `config.UFS.values()`), `len(meta._geo) <= 28`.
  - `test_geo_filtra_as_ufs_pedidas`: `ufs=PR` → toda feição tem `cod6` começando com `41`.
- [ ] **Passo 2:** falham.
- [ ] **Passo 3: Implementar.** Guardar só o GeoJSON completo (uma entrada) e filtrar as feições a cada
  pedido; sigla fora de `config.UFS.values()` → `ErroUsuario`.
- [ ] **Passo 4:** `uv run pytest` passa.
- [ ] **Passo 5: Commit** "Evita que o contorno do mapa ocupe memória a cada combinação de UFs".

### Tarefa 5: Contraste e cores do mapa (N09)

Branch: `feature/contraste-cores`

**Arquivos:** modificar `web/css/base/tema.css`, `web/js/paginas/mapa.js:93-115`, `web/css/paginas/mapa.css`;
testar novo `tests/test_tema.py`.

**Valores (fórmula de contraste WCAG):** `--muted` claro `#5b6b7a` (5,48 no cartão, 5,05 no fundo,
4,61 sobre `--mapa-vazio`); `--serie-ctx` claro `#848f9a` (3,29) e escuro `#6a7b8b` (3,91). O `--muted`
escuro atual dá 4,52 sobre `--mapa-vazio` e fica.

- [ ] **Passo 1: Testes que falham** em `tests/test_tema.py`, lendo as variáveis de `tema.css` nos dois temas:
  - `test_contraste_do_texto`: `--muted` sobre `--card` e sobre `--bg` ≥ 4,5; `--text-2` sobre `--card` ≥ 4,5.
  - `test_contraste_dos_graficos`: `--serie-ctx` sobre `--card` ≥ 3; `--muted` sobre `--mapa-vazio` ≥ 3 (listras da hachura).
  - `test_mapa_sem_dado_tem_hachura`: `mapa.js` contém `url(#sem-dado)`.
- [ ] **Passo 2:** falham.
- [ ] **Passo 3: Implementar:** trocar as cores; no mapa, município sem valor usa o padrão SVG
  `<pattern id="sem-dado">` com listras em `--muted` sobre `--mapa-vazio`, e a escala ganha o item "Sem dado"
  com a mesma hachura.
- [ ] **Passo 4:** `uv run pytest` passa; capturar `#/mapa` e `#/visao-geral` nos dois temas e conferir a hachura
  num município pequeno e as linhas dos anos antigos.
- [ ] **Passo 5: Commit** "Corrige contraste do texto secundário e distingue municípios sem dado".

### Tarefa 6: Inventário gravado de forma segura (parte da N06)

Branch: `correcao/inventario-atomico`

**Arquivos:** modificar `sinan/processar.py:213-215`; testar `tests/test_processar.py`.

- [ ] **Passo 1: Teste que falha:** `test_inventario_gravado_por_troca` — com `monkeypatch` em
  `pathlib.Path.replace` registrando as chamadas, `processar._salvar_inventario({"x": 1})` chama
  `replace` com destino `ARQ_INVENTARIO`, e o arquivo final tem o conteúdo esperado.
- [ ] **Passo 2:** falha.
- [ ] **Passo 3: Implementar:** gravar em `ARQ_INVENTARIO.with_suffix(".tmp")` e trocar com `replace`, como já
  é feito com os Parquet (`sinan/processar.py:289`, `sinan/processar.py:321`).
- [ ] **Passo 4:** `uv run pytest` passa.
- [ ] **Passo 5: Commit** "Grava o inventário por troca de arquivo".

### Tarefa 7: Guia de implantação, script do cron e medição com dengue de Roraima

Branch: `feature/guia-implantacao`, da `develop` com todas as tarefas anteriores.

**Arquivos:** criar `scripts/atualizar_servidor.sh`; modificar `README.md` (seção nova "Publicar no servidor")
e `docs/analise/2026-11-analise-e-roadmap.md` (seção 7.2, ponto 13).

- [ ] **Passo 1: Script `scripts/atualizar_servidor.sh`** (bash, `set -euo pipefail`):
  - lê `SINAN_DADOS` e `UV` (caminho absoluto do `uv`, obrigatório: o cron não carrega o `PATH`);
  - `ANO=$(date +%Y)` e chama `"$UV" run --frozen python baixar_dados.py --agravos DENG CHIK ZIKA --ufs RR --anos $((ANO-5))-$ANO "$@"`,
    a partir da pasta do projeto, para o ano novo entrar sozinho em janeiro;
  - `flock -n` num arquivo de trava, para duas execuções não se sobreporem;
  - acrescenta a saída com data em `$SINAN_DADOS/atualizacao.log`.
  - Conferir com `bash -n scripts/atualizar_servidor.sh` e uma execução com uma pasta temporária e `--anos` de teste.
- [ ] **Passo 2: Guia no `README.md`**, nesta ordem:
  - instalação: `uv sync --frozen`; o serviço e o cron rodam com o mesmo usuário (ex.: `sinan`);
  - systemd: `EnvironmentFile=/etc/sinan.env` (com `SINAN_MODO`, `SINAN_HOSTS`, `SINAN_DADOS`) e
    `ExecStart=/srv/sinan/.venv/bin/uvicorn sinan.api:app --host 127.0.0.1 --port 8501 --proxy-headers --forwarded-allow-ips 127.0.0.1`;
  - nginx com HTTPS; `proxy_set_header Host $host;`; `gzip on` para JSON, JS e CSS; cabeçalhos
    `X-Content-Type-Options nosniff`, `X-Frame-Options DENY` e `Referrer-Policy strict-origin-when-cross-origin`;
    `limit_req` **só em `location /api/`**, com `burst=30 nodelay` (a primeira abertura da página faz cerca de 47 pedidos);
  - cron, segunda às 3h: `0 3 * * 1 UV=/caminho/do/uv SINAN_DADOS=/srv/sinan-dados /srv/sinan/scripts/atualizar_servidor.sh`;
  - cópias de segurança: **nada da pasta de dados**. Guardar `/etc/sinan.env`, a unidade do systemd e a
    configuração do nginx. Para restaurar, rodar o script com `--forcar`.
- [ ] **Passo 3: Medição.** **Avisar o usuário antes:** baixa o arquivo nacional de dengue 2024 (288 MB).
  Rodar o script com `SINAN_DADOS` numa pasta temporária e `--anos 2024`; subir o servidor em modo publicado;
  medir `/api/visao`, `/api/mapa` e `/api/perfil` sem cache, 10 pedidos simultâneos, e a exportação `municipios`.
  Registrar no ponto 13 da seção 7.2 e marcar como resolvido. Esperado: abaixo de 1 s com 10 simultâneos.
- [ ] **Passo 4:** com o servidor de teste no ar, rodar o script com `--forcar` enquanto pede `/api/visao` e
  `/api/meta` em laço: nenhuma resposta 500, e `/api/meta` nunca volta com a lista de agravos vazia.
- [ ] **Passo 5:** `uv run pytest` e `uv run ruff check .` passam. **Commit** "Adiciona guia e script para
  publicar o painel no servidor"; `push` e PR.

---

## Fora deste plano

- N10 (teclado e leitor de tela): começo da Fase 2.
- Login, fichas com login, registro de acessos (N02, N07, N04 completo): só se o encarregado de dados decidir pelas fichas na internet.
- Configurar a VPS de verdade (domínio, certificado, usuário do serviço): feito pela equipe com o guia da Tarefa 7.
