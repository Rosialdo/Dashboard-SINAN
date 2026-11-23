# Graph Report - Dashboard-SINAN  (2026-11-23)

## Corpus Check
- 109 files · ~424,604 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 722 nodes · 1725 edges · 31 communities (24 shown, 7 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 37 edges (avg confidence: 0.87)
- Token cost: 159,161 input · 0 output

## Community Hubs (Navigation)
- Componentes da interface
- Consultas DuckDB
- Rótulos TabNet e processamento
- Regras do projeto
- Download e descompressão DBC
- Roadmap e decisões
- Catálogo e tarefa de download
- Testes do modo publicado
- Testes da API
- Montagem do app FastAPI
- Testes de implantação
- Filtros do painel
- Testes do painel.sh
- Telas de análise
- Nomes amigáveis
- Cache e registros
- Tela Atualizar dados
- Script painel.sh
- Referências IBGE e FTP
- Fixtures de teste
- Testes da interface
- Proteção local (ASGI)
- Testes do tema
- Inicializador local
- Atualização do servidor
- Subagente scout
- N10 Acessibilidade
- N11 Variação anual
- N17 Link com filtros
- N22 Impressão
- Pacote dashboard-sinan

## God Nodes (most connected - your core abstractions)
1. `esc()` - 28 edges
2. `ico()` - 26 edges
3. `Filtro` - 23 edges
4. `fmt()` - 22 edges
5. `json_resp()` - 21 edges
6. `erroHtml()` - 19 edges
7. `_fonte()` - 18 edges
8. `termo()` - 18 edges
9. `_q()` - 17 edges
10. `derivar()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Rotas de fichas bloqueadas no modo publicado (/api/registros, exportar xlsx/csv, /api/docs)` --implements--> `Modo publicado (SINAN_MODO=publico)`  [INFERRED]
  docs/plans/2026-11-17-fase-0-publicacao.md → CLAUDE.md
- `Variável SINAN_MODO decidida em criar_app()` --implements--> `Modo publicado (SINAN_MODO=publico)`  [INFERRED]
  docs/plans/2026-11-17-fase-0-publicacao.md → CLAUDE.md
- `cliente_publico()` --calls--> `criar_app()`  [EXTRACTED]
  tests/test_publicacao.py → sinan/api/app.py
- `test_local_continua_recusando_dominio_de_fora()` --calls--> `criar_app()`  [EXTRACTED]
  tests/test_publicacao.py → sinan/api/app.py
- `test_publico_erro_interno_sem_detalhes()` --calls--> `criar_app()`  [EXTRACTED]
  tests/test_publicacao.py → sinan/api/app.py

## Import Cycles
- 3-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/dados.py -> sinan/api/__init__.py`
- 4-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/dados.py -> sinan/api/filtros.py -> sinan/api/__init__.py`
- 4-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/registros.py -> sinan/api/__init__.py`
- 4-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/dados.py -> sinan/api/tarefa.py -> sinan/api/__init__.py`
- 4-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/dados.py -> sinan/api/__init__.py`
- 4-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/painel.py -> sinan/api/__init__.py`
- 4-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/variaveis.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/dados.py -> sinan/api/filtros.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/meta.py -> sinan/api/filtros.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/painel.py -> sinan/api/filtros.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/registros.py -> sinan/api/filtros.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/variaveis.py -> sinan/api/filtros.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/registros.py -> sinan/api/servicos.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/dados.py -> sinan/api/tarefa.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/painel.py -> sinan/api/servicos.py -> sinan/api/__init__.py`
- 5-file cycle: `sinan/api/__init__.py -> sinan/api/app.py -> sinan/api/rotas/__init__.py -> sinan/api/rotas/variaveis.py -> sinan/api/servicos.py -> sinan/api/__init__.py`

## Hyperedges (group relationships)
- **Fase 0 revisada: pré-requisitos de publicação** — docs_analise_2026_11_analise_e_roadmap_n01_endereco_publico, docs_analise_2026_11_analise_e_roadmap_modo_publico, docs_analise_2026_11_analise_e_roadmap_n04_limites, docs_analise_2026_11_analise_e_roadmap_n05_erros, docs_analise_2026_11_analise_e_roadmap_n08_textos_internet, docs_analise_2026_11_analise_e_roadmap_n09_contraste_mapa [EXTRACTED 1.00]
- **Subagentes do projeto (scout, builder, reviewer)** — _claude_agents_scout, _claude_agents_builder, _claude_agents_reviewer [INFERRED 0.95]
- **Propostas para o gerente de UBS** — docs_analise_2026_11_comparacao_painel_ses_rr_indicadores_qualidade, docs_analise_2026_11_comparacao_painel_ses_rr_casos_em_aberto, docs_analise_2026_11_comparacao_painel_ses_rr_tela_esta_semana, docs_analise_2026_11_comparacao_painel_ses_rr_faixa_semanas_incompletas [EXTRACTED 1.00]
- **Proteção de dados no modo publicado** — claude_modo_publicado, claude_variaveis_sensiveis, docs_plans_2026_11_17_fase_0_publicacao_rotas_bloqueadas, docs_plans_2026_11_17_containerizacao_sem_log_ip, docs_plans_2026_11_17_fase_0_publicacao_sinan_modo [INFERRED 0.85]
- **Stack Docker Compose na VPS** — compose_servico_painel, compose_servico_atualizar, compose_servico_proxy, docs_plans_2026_11_17_containerizacao_imagem_sinan_painel, docs_plans_2026_11_17_containerizacao_caddy_ratelimit, readme_scripts_painel_sh [EXTRACTED 1.00]
- **Fluxo de atualização semanal dos dados** — readme_atualizacao_semanal, readme_scripts_painel_sh, compose_servico_atualizar, docs_plans_2026_11_17_containerizacao_atualizar_servidor_sh, docs_plans_2026_11_17_containerizacao_trava_flock, readme_ftp_datasus [EXTRACTED 1.00]

## Communities (31 total, 7 thin omitted)

### Community 0 - "Componentes da interface"
Cohesion: 0.09
Nodes (86): htmlAlertas(), ligarAlertas(), barrasHtml(), erroHtml(), esqueleto(), vazioHtml(), htmlCabecalho(), htmlRodape() (+78 more)

### Community 1 - "Consultas DuckDB"
Cohesion: 0.07
Nodes (64): DuckDBPyConnection, api_exportar(), api_registros(), _csv(), DataFrame, Filtros, ge, get (+56 more)

### Community 2 - "Rótulos TabNet e processamento"
Cohesion: 0.07
Nodes (55): Agravo, obter(), Variáveis do .def do TabNet que existem nos dados baixados. A posição nesta…, variaveis(), caminho_parquet(), _conversor(), _datas(), derivar() (+47 more)

### Community 3 - "Regras do projeto"
Cohesion: 0.06
Nodes (52): Cache (memo) só com resultados agregados, CLAUDE.md (instruções do projeto), Fluxo de branches feature/* a partir da develop com PR, Modo local (dois cliques nos .bat, offline), Modo publicado (SINAN_MODO=publico), Regra: nunca citar o assistente/IA no projeto, Ordenação com desempate em consultas paginadas, Textos de tela em português simples ('Não informado') (+44 more)

### Community 4 - "Download e descompressão DBC"
Cohesion: 0.07
Nodes (36): BaseModel, field_validator, njit, PedidoAtualizar, hosts_publicos(), Domínios aceitos no modo publicado (``SINAN_HOSTS``, separados por vírgula, sem…, _blast(), _construir() (+28 more)

### Community 5 - "Roadmap e decisões"
Cohesion: 0.06
Nodes (40): Subagente builder (implementação), Subagente reviewer (revisão), CLAUDE.md (regras do projeto), Painel SINAN: análise e roadmap, Benchmark de referências (TabNet, InfoDengue, Painel MS, Metabase, Power BI), Cron semanal com baixar_dados.py, Fase 0 revisada (pré-requisitos de publicação), InfoDengue (Fiocruz/FGV) (+32 more)

### Community 6 - "Catálogo e tarefa de download"
Cohesion: 0.12
Nodes (25): Aviso, _anos(), main(), Baixa e trata os dados do SINAN pelo terminal (precisa de internet). Sem…, nome(), Catálogo dos agravos disponíveis no FTP do SINAN. Para cada código de arquivo…, _executar(), iniciar() (+17 more)

### Community 7 - "Testes do modo publicado"
Cohesion: 0.07
Nodes (12): _pasta_dados(), Path, Pasta dos dados: ``SINAN_DADOS`` ou ``dados/`` dentro do projeto., cliente_publico(), municipio(), fixture, parametrize, Modo publicado (SINAN_MODO=publico): domínio configurável e só leitura. (+4 more)

### Community 8 - "Testes da API"
Cohesion: 0.09
Nodes (9): _converter(), Tipos do pandas/numpy que o json não conhece., parametrize, API do dashboard e proteção do servidor local (sinan/api/)., test_conversao_json_de_nat(), test_exportar(), test_paineis(), test_remover_valida_itens() (+1 more)

### Community 9 - "Montagem do app FastAPI"
Cohesion: 0.11
Nodes (21): FastAPI, RequestValidationError, Response, ArquivosInterface, criar_app(), _mensagem_validacao(), Monta a aplicação: rotas da API, erros, arquivos da interface e proteção local., Arquivos da pasta web/ sempre conferidos com o servidor ("no-cache"). A… (+13 more)

### Community 10 - "Testes de implantação"
Cohesion: 0.14
Nodes (20): SEM_BASH_FLOCK, SEM_DOCKER, _alvos(), compose(), _compose_config(), _estagio_final(), CompletedProcess, fixture (+12 more)

### Community 11 - "Filtros do painel"
Cohesion: 0.15
Nodes (20): Exception, anos(), area_base(), Contexto, lista(), Request, Filtros do painel: lê os parâmetros da URL e monta o ``consultas.Filtro``. As…, Filtro da consulta + área usada no cálculo da população (UFs). (+12 more)

### Community 12 - "Testes do painel.sh"
Cohesion: 0.13
Nodes (15): _em_ordem(), Projeto, CompletedProcess, fixture, Path, scripts/painel.sh com um docker e um git falsos (anotam as chamadas num…, _saida(), test_atualizar_dados_sem_imagem() (+7 more)

### Community 13 - "Telas de análise"
Cohesion: 0.15
Nodes (20): memo(), Data do inventário: muda sempre que um arquivo é baixado ou removido., Devolve o valor guardado para ``chave`` ou calcula e guarda (LRU)., _versao(), json_resp(), api_mapa(), api_perfil(), api_visao() (+12 more)

### Community 14 - "Nomes amigáveis"
Cohesion: 0.15
Nodes (17): grupo(), _limpar(), nome_amigavel(), _periodo(), Nomes amigáveis e grupos para as variáveis da ficha (tela "Outras variáveis").…, Sufixo " (até 2010)" / " (após 2010)" quando o .def tem versões por período., Troca os códigos de "sem resposta" do DATASUS por um texto que qualquer pessoa…, valor_simples() (+9 more)

### Community 15 - "Cache e registros"
Cohesion: 0.18
Nodes (11): Cache dos resultados agregados, invalidado quando os dados mudam., Servidor local do dashboard: entrega a interface (pasta web/) e uma API JSON.…, DataFrame, DataFrame -> lista de dicionários, com vazios como None., registros(), Rotas da API, um arquivo por assunto. Cada um expõe um ``router`` (APIRouter)., Tela "Dados e exportação": tabela paginada e download em Excel/CSV., Tela "Outras variáveis": qualquer campo da ficha, com os rótulos do TabNet. (+3 more)

### Community 16 - "Tela Atualizar dados"
Cohesion: 0.23
Nodes (15): post, api_atualizar(), api_dados(), api_listar_ftp(), api_remover(), api_status(), PedidoRemover, get (+7 more)

### Community 17 - "Script painel.sh"
Cohesion: 0.32
Nodes (13): ajuda(), avisar_endereco(), cmd_atualizar_dados(), cmd_implantar(), cmd_logs(), cmd_status(), estado(), exigir_env() (+5 more)

### Community 18 - "Referências IBGE e FTP"
Cohesion: 0.26
Nodes (11): FTP, baixar(), baixar_json(), gerar_mapa(), gerar_municipios(), gerar_populacao(), gerar_tabnet(), Gera os arquivos da pasta ``referencia/`` (uso do desenvolvedor). Esses… (+3 more)

### Community 19 - "Fixtures de teste"
Cohesion: 0.20
Nodes (11): MonkeyPatch, limpar(), cliente(), dados_teste(), fixture, Path, Ambiente de teste: uma pasta de dados temporária montada a partir da amostra…, Processa a amostra (só PR e SP) e devolve a pasta de dados de teste. (+3 more)

### Community 20 - "Testes da interface"
Cohesion: 0.18
Nodes (5): _exportados(), parametrize, Path, Interface (web/js): confere que os módulos se encaixam, sem precisar de…, test_imports_existem()

### Community 21 - "Proteção local (ASGI)"
Cohesion: 0.24
Nodes (6): ASGIApp, Receive, Scope, Send, ProtecaoLocal, Middleware ASGI que recusa pedidos que não vieram do próprio dashboard. -…

### Community 22 - "Testes do tema"
Cohesion: 0.31
Nodes (7): contraste(), _luz(), parametrize, Contraste das cores do tema (fórmula da WCAG), nos temas claro e escuro., test_contraste_do_texto(), test_contraste_dos_graficos(), test_formula_de_contraste()

### Community 23 - "Inicializador local"
Cohesion: 0.43
Nodes (6): abrir_quando_pronto(), main(), porta_livre(), Abre o dashboard no navegador (funciona sem internet)., migrar_arquivos(), Atualiza Parquets gravados pela versão 1.0 para os nomes de colunas atuais.

## Ambiguous Edges - Review These
- `Variáveis sensíveis ocultas no recorte por município` → `Supressão de contagens pequenas (< 5)`  [AMBIGUOUS]
  docs/analise/2026-11-comparacao-painel-ses-rr.md · relation: conceptually_related_to

## Knowledge Gaps
- **31 isolated node(s):** `dashboard-sinan`, `atualizar_servidor.sh script`, `SEXOS`, `CFG`, `graficos` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Variáveis sensíveis ocultas no recorte por município` and `Supressão de contagens pequenas (< 5)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `_conectar()` connect `Catálogo e tarefa de download` to `Referências IBGE e FTP`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `dbc_para_dbf()` connect `Download e descompressão DBC` to `Rótulos TabNet e processamento`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `dashboard-sinan`, `atualizar_servidor.sh script`, `SEXOS` to the rest of the system?**
  _31 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Componentes da interface` be split into smaller, more focused modules?**
  _Cohesion score 0.08526383526383527 - nodes in this community are weakly interconnected._
- **Should `Consultas DuckDB` be split into smaller, more focused modules?**
  _Cohesion score 0.06606990622335891 - nodes in this community are weakly interconnected._
- **Should `Rótulos TabNet e processamento` be split into smaller, more focused modules?**
  _Cohesion score 0.06885245901639345 - nodes in this community are weakly interconnected._