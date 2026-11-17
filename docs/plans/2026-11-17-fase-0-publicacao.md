# Fase 0 — Publicação só de leitura: plano de implementação

> **Como executar:** uma tarefa por vez, na ordem, marcando as caixas (`- [ ]`). Cada tarefa tem a
> sua branch, criada a partir da `develop`, e termina com testes passando e um commit.

**Objetivo:** deixar o painel pronto para ser publicado na VPS do grupo PRISM/UFRR como site aberto,
só de leitura e só com números agregados, sem quebrar o modo local.

**Abordagem:** uma variável de ambiente, `SINAN_MODO=publico`, liga o modo publicado. Nesse modo o
servidor aceita o domínio configurado, não monta as rotas de administração nem as de fichas, esconde
as telas correspondentes e não mostra detalhes de erros. Sem a variável, tudo continua como hoje.
Os dados são atualizados por cron com o `baixar_dados.py`.

**Stack:** Python 3.12, FastAPI/Starlette, Uvicorn, DuckDB, interface em módulos JS nativos; pytest e ruff.

**Especificação:** `docs/analise/2026-11-analise-e-roadmap.md`, seção 7 (decisões de 17/11/2026),
mais as fichas N01, N04, N05, N08 e N09 da seção 4.

## Restrições globais

- O modo local não muda: sem `SINAN_MODO`, todas as rotas, telas e textos continuam iguais, e os
  testes atuais passam sem alteração.
- No modo publicado nenhuma ficha individual sai do servidor: `/api/registros`, exportação de fichas
  (`xlsx`, `csv`, `csv_completo`), `/api/dados/*` e `/api/docs` não existem.
- Não afrouxar o `ProtecaoLocal`: outro domínio só é aceito se estiver em `SINAN_HOSTS`, e só no modo publicado.
- Nenhuma dependência nova. Textos de tela em português simples.
- Cada tarefa: branch `feature/<nome>` a partir da `develop`; antes do commit, `uv run pytest` e
  `uv run ruff check .`; mensagem em português, sem coautoria nem menção a IA; `push` e PR só a pedido.

## Variáveis de ambiente (contrato entre as tarefas)

| Variável | Valor | Lida por |
|---|---|---|
| `SINAN_MODO` | `publico` liga o modo publicado; qualquer outro valor ou ausente = local | `config.publico()` |
| `SINAN_HOSTS` | domínios aceitos, separados por vírgula, ex.: `painel.prism.ufrr.br` | `config.hosts_publicos()` |
| `SINAN_DADOS` | pasta de dados; ausente = `<raiz>/dados` | `config.PASTA_DADOS` |

## Foco de revisão

1. **Proxy que repassa o host local** (`Host: 127.0.0.1:8501`) com `Origin: https://painel...`:
   o POST não existe no modo publicado, mas os GET precisam passar. Teste na Tarefa 1.
2. **Rota de fichas acessível por outro caminho**: `/api/exportar?formato=xlsx` ou `csv` no modo
   publicado tem de ser recusado, e `formato=municipios` aceito. Teste na Tarefa 2.
3. **Interface que chama rota inexistente**: no modo publicado, abrir `#/dados` ou `#/atualizar` pelo
   endereço não pode mostrar erro de servidor; deve cair na Visão geral. Verificação na Tarefa 3.
4. **`SINAN_HOSTS` vazio com `SINAN_MODO=publico`**: o servidor não pode passar a aceitar qualquer
   host. Teste na Tarefa 1.
5. **Cron rodando enquanto alguém consulta**: o Parquet novo é trocado de uma vez
   (`sinan/processar.py:321`) e o cache se invalida pelo inventário. Verificação manual na Tarefa 6.

---

### Tarefa 1: Endereço público e pasta de dados configurável (N01)

Branch: `feature/endereco-publico`

**Arquivos:**
- Modificar: `sinan/config.py`, `sinan/api/seguranca.py`, `sinan/api/app.py:85`
- Testar: novo `tests/test_publicacao.py`

**Interfaces:**
- Produz: `config.publico() -> bool`, `config.hosts_publicos() -> set[str]` (lidos do ambiente a cada
  chamada, para os testes usarem `monkeypatch.setenv`); `config.PASTA_DADOS` vindo de `SINAN_DADOS`;
  `ProtecaoLocal(app, hosts_extras: set[str] = frozenset())`; um fixture `cliente_publico` em
  `tests/test_publicacao.py` que monta `criar_app()` com `SINAN_MODO=publico` e
  `SINAN_HOSTS=painel.exemplo.br` e um `TestClient(base_url="https://painel.exemplo.br")`.

- [ ] **Passo 1: Testes que falham**, em `tests/test_publicacao.py`:
  - `test_publico_aceita_dominio_configurado`: `GET /api/meta` com `Host: painel.exemplo.br` e
    `Origin: https://painel.exemplo.br` → 200.
  - `test_publico_recusa_outro_dominio`: `Host: outro.br` → 403.
  - `test_publico_aceita_host_local_do_proxy`: `Host: 127.0.0.1:8501` com `Origin: https://painel.exemplo.br` → 200.
  - `test_publico_sem_hosts_nao_aceita_qualquer_um`: `SINAN_MODO=publico`, `SINAN_HOSTS` vazio, `Host: outro.br` → 403.
  - `test_local_continua_recusando_https_de_fora`: sem `SINAN_MODO`, `Host: painel.exemplo.br` → 403.
  - `test_pasta_de_dados_pelo_ambiente`: com `SINAN_DADOS=/tmp/x`, `importlib.reload(config)` dá
    `PASTA_DADOS == Path("/tmp/x")` e `ARQ_INVENTARIO == Path("/tmp/x/inventario.json")`; recarregar de
    novo sem a variável ao final.
- [ ] **Passo 2:** `uv run pytest tests/test_publicacao.py -v` → falham.
- [ ] **Passo 3: Implementar.** Em `ProtecaoLocal.motivo_bloqueio`: host aceito se estiver em `HOSTS`
  ou em `hosts_extras`; origem aceita se for `http://{host}`, ou, quando `hosts_extras` não está vazio,
  `https://{h}` para algum `h` de `hosts_extras` (é o caso do proxy que repassa o host local).
  Em `criar_app`: `ProtecaoLocal` recebe `config.hosts_publicos()` só se `config.publico()`.
- [ ] **Passo 4:** `uv run pytest` → tudo passa, inclusive `tests/test_api.py` sem alteração.
- [ ] **Passo 5: Commit** "Permite publicar o painel num domínio configurado".

### Tarefa 2: Modo público só de leitura no servidor (N03' e N05)

Branch: `feature/modo-publico`

**Arquivos:**
- Modificar: `sinan/api/app.py`, `sinan/api/rotas/registros.py`, `sinan/api/rotas/meta.py`
- Testar: `tests/test_publicacao.py`

**Interfaces:**
- Consome: `config.publico()` e o fixture `cliente_publico` da Tarefa 1.
- Produz: `/api/meta` passa a devolver `"publico": bool`, usado pela Tarefa 3.

- [ ] **Passo 1: Testes que falham:**
  - `test_publico_sem_rotas_de_administracao`: `GET /api/dados`, `GET /api/dados/status` → 404;
    `POST /api/dados/remover` com JSON → 404 ou 405 (a rota não existe).
  - `test_publico_sem_fichas`: `GET /api/registros?agravo=ACBI` → 404; `GET /api/exportar?agravo=ACBI&formato=xlsx`,
    `csv` e `csv_completo` → 404, com `{"erro": ...}` em português.
  - `test_publico_exporta_resumo_por_municipio`: `formato=municipios` → 200 e anexo CSV.
  - `test_publico_sem_documentacao`: `GET /api/docs` e `/api/openapi.json` → 404.
  - `test_publico_consultas_agregadas_funcionam`: `/api/visao`, `/api/mapa`, `/api/perfil`, `/api/variavel` com `agravo=ACBI` → 200.
  - `test_publico_erro_interno_sem_detalhes`: com `monkeypatch` fazendo `servicos.indicadores` lançar
    `RuntimeError("segredo")`, `GET /api/visao?agravo=ACBI` (limpar o cache antes; cliente com
    `raise_server_exceptions=False`) → 500, e o texto
    `segredo` não aparece na resposta; a mensagem tem um código de 8 caracteres.
  - `test_meta_informa_o_modo`: `/api/meta` → `publico` é `True` no cliente público e `False` no `cliente`.
- [ ] **Passo 2:** os testes falham.
- [ ] **Passo 3: Implementar.** Em `criar_app`, se `config.publico()`: não incluir `dados.router`;
  `docs_url=None`, `openapi_url=None`; o tratador de erro interno devolve
  `"Erro interno (código {c}). Avise a equipe responsável pelo painel."`, com `c = uuid4().hex[:8]`, e
  imprime o código junto com o traceback. Em `registros.py`: `api_registros` e `api_exportar` com
  formato diferente de `municipios` devolvem `erro("Não disponível na versão publicada do painel.", 404)`.
  Em `api_meta`: `"publico": config.publico()`.
- [ ] **Passo 4:** `uv run pytest` passa.
- [ ] **Passo 5: Commit** "Adiciona o modo publicado, só de leitura e sem fichas".

### Tarefa 3: Interface do modo publicado (N03' e N08)

Branch: `feature/interface-publica`

**Arquivos:**
- Modificar: `web/js/nucleo/estado.js`, `web/js/nucleo/navegacao.js`, `web/js/roteador.js`,
  `web/js/componentes/cabecalho.js`, `web/js/main.js`
- Testar: `tests/test_interface.py`

**Interfaces:**
- Consome: `estado.meta.publico` (Tarefa 2).
- Produz: `PAGINAS[id].local = true` marca as telas que só existem no modo local (`dados` e `atualizar`).

- [ ] **Passo 1: Teste que falha** em `tests/test_interface.py`: `test_telas_locais_marcadas` — lê
  `web/js/nucleo/estado.js` e confere que as linhas de `"dados"` e `"atualizar"` em `PAGINAS` contêm
  `local: true`, e que `roteador.js` e `navegacao.js` usam `local` (texto `.local`).
- [ ] **Passo 2:** o teste falha.
- [ ] **Passo 3: Implementar.**
  - `paginaAtual()` trata tela com `local` como inexistente quando `estado.meta?.publico` (cai em `visao-geral`);
    `montarMenu()` não lista essas telas no modo publicado.
  - Menu "Exportar" do cabeçalho: no modo publicado, só a opção `municipios`.
  - Textos no modo publicado (texto exato):
    - erro sem servidor (`web/js/main.js:51`): "Não foi possível carregar o painel. Tente de novo em alguns minutos.";
    - sem dados (`web/js/roteador.js:63-65`): título "Os dados ainda não foram carregados", texto
      "O painel é atualizado toda semana. Volte mais tarde.", sem o botão para "Atualizar dados";
    - rodapé (`web/js/componentes/cabecalho.js:46`): "Dados atualizados em ..." em vez de "Dados baixados em ...".
- [ ] **Passo 4:** `uv run pytest` passa. Subir o servidor de teste (comando da seção 4 do `CLAUDE.md`)
  com `SINAN_MODO=publico SINAN_HOSTS=localhost` e uma pasta de dados temporária; abrir `#/dados` e
  `#/atualizar` e conferir que caem na Visão geral; capturar a Visão geral e o menu Exportar.
  Repetir sem `SINAN_MODO` e conferir que o menu tem as 7 telas.
- [ ] **Passo 5: Commit** "Adapta a interface ao modo publicado".

### Tarefa 4: Validação de UFs no mapa (N04 reduzido)

Branch: `feature/valida-ufs-mapa`

**Arquivos:** modificar `sinan/api/rotas/meta.py:52-61`; testar `tests/test_api.py`.

- [ ] **Passo 1: Teste que falha:** `test_geo_recusa_uf_desconhecida` — `GET /api/geo?ufs=ZZ` → 400 com
  `erro` contendo "UF"; e `test_geo_nao_guarda_pedidos_invalidos` — depois de 5 pedidos com UFs
  inventadas, `len(meta._geo)` não cresce.
- [ ] **Passo 2:** falha.
- [ ] **Passo 3: Implementar:** antes de consultar o dicionário, recusar com `ErroUsuario` qualquer sigla
  fora de `config.UFS.values()`.
- [ ] **Passo 4:** `uv run pytest` passa.
- [ ] **Passo 5: Commit** "Recusa UFs desconhecidas no contorno do mapa".

### Tarefa 5: Contraste e cores do mapa (N09)

Branch: `feature/contraste-cores`

**Arquivos:** modificar `web/css/base/tema.css`, `web/js/paginas/mapa.js:93-99`,
`web/css/paginas/mapa.css`; testar novo `tests/test_tema.py`.

**Valores (calculados pela fórmula WCAG):** `--muted` claro `#5b6b7a` (5,48 no cartão, 5,05 no fundo);
`--serie-ctx` claro `#848f9a` (3,29) e escuro `#6a7b8b` (3,91).

- [ ] **Passo 1: Teste que falha** em `tests/test_tema.py`: `test_contraste_do_tema` lê as variáveis de
  `tema.css` dos dois temas e confere: `--muted` sobre `--card` e sobre `--bg` ≥ 4,5;
  `--text-2` sobre `--card` ≥ 4,5; `--serie-ctx` sobre `--card` ≥ 3. E `test_mapa_sem_dado_tem_hachura`:
  `mapa.js` contém `url(#sem-dado)`.
- [ ] **Passo 2:** falha.
- [ ] **Passo 3: Implementar:** trocar as três cores; no mapa, município sem valor usa um padrão SVG de
  listras (`<pattern id="sem-dado">`, listras na cor `--eixo` sobre `--mapa-vazio`) e a escala ganha um
  item "Sem dado" com a mesma hachura.
- [ ] **Passo 4:** `uv run pytest` passa; capturar `#/mapa` e `#/visao-geral` nos dois temas e conferir a
  hachura e as linhas dos anos antigos.
- [ ] **Passo 5: Commit** "Corrige contraste do texto secundário e distingue municípios sem dado".

### Tarefa 6: Guia de implantação e medição com dengue de Roraima

Branch: `feature/guia-implantacao`

**Arquivos:** modificar `README.md` (seção nova "Publicar no servidor"); modificar
`docs/analise/2026-11-analise-e-roadmap.md`, seção 7.2, ponto 13.

- [ ] **Passo 1: Guia no `README.md`**, com, nesta ordem:
  - serviço do Uvicorn (systemd) com `SINAN_MODO=publico`, `SINAN_HOSTS`, `SINAN_DADOS` e
    `uv run uvicorn sinan.api:app --host 127.0.0.1 --port 8501 --proxy-headers --forwarded-allow-ips 127.0.0.1`;
  - nginx com HTTPS, `proxy_set_header Host $host;` e `limit_req` (ex.: 10 pedidos/s por IP, rajada 30);
  - cron semanal, segunda às 3h:
    `cd /srv/sinan && SINAN_DADOS=/srv/sinan-dados uv run python baixar_dados.py --agravos DENG CHIK ZIKA --ufs RR`;
  - cópia de segurança: só `configuracao.json` e `inventario.json` (os Parquet se refazem com o cron).
- [ ] **Passo 2: Medição.** **Avisar o usuário antes:** baixa o arquivo nacional de dengue 2024 (288 MB).
  Numa pasta temporária, `SINAN_DADOS=<tmp> uv run python baixar_dados.py --agravos DENG --anos 2024 --ufs RR`;
  subir o servidor em modo publicado e repetir as medições da seção 2.4 só com rotas existentes
  (`/api/visao`, `/api/mapa`, `/api/perfil` sem cache, 10 simultâneos; exportação `municipios`).
  Registrar os números no ponto 13 da seção 7.2 e marcar como resolvido.
  Esperado: `/api/visao` sem cache abaixo de 1 s com 10 simultâneos.
- [ ] **Passo 3:** com o servidor de teste no ar, rodar o `baixar_dados.py` de novo com `--forcar`
  enquanto pede `/api/visao` em laço: nenhuma resposta 500.
- [ ] **Passo 4:** `uv run pytest` e `uv run ruff check .` passam.
- [ ] **Passo 5: Commit** "Adiciona guia para publicar o painel no servidor".

---

## Fora deste plano

- N10 (teclado e leitor de tela): começo da Fase 2.
- Login, fichas com login, registro de acessos (N02, N07, N04 completo): só se o encarregado de dados decidir pelas fichas na internet.
- Configurar a VPS de verdade (domínio, certificado, usuário do serviço): feito pela equipe com o guia da Tarefa 6.
