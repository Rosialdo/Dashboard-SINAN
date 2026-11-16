# Painel SINAN: análise e roadmap de novas funcionalidades

Relatório produzido a partir do código da branch `develop` (commit `2de2d46`) em novembro de 2026.
Toda afirmação sobre o painel cita `arquivo:linha`. O que não pôde ser comprovado no código está
marcado como **Suposição:** ou **A validar:**, e tudo isso está reunido na seção 6.

Contexto decisivo: o painel foi escrito para rodar **no computador de uma pessoa**, sem internet,
e **será disponibilizado pela internet** para várias pessoas. Boa parte do diagnóstico trata dessa
mudança.

## 1. Estado atual

### 1.1 Stack

| Camada | Tecnologia | Evidência |
|---|---|---|
| Linguagem | Python 3.12 (`>=3.12,<3.13`) | `pyproject.toml:7` |
| Servidor | FastAPI + Starlette + Uvicorn | `pyproject.toml:15-19`, `iniciar.py:44` |
| Consultas | DuckDB lendo Parquet direto do disco, um cursor por thread | `sinan/consultas.py:49`, `sinan/consultas.py:82` |
| Armazenamento | Parquet (zstd) por agravo e ano, inventário em JSON | `sinan/processar.py:218`, `sinan/processar.py:303`, `sinan/config.py:17-22` |
| Leitura do DATASUS | descompressor `.dbc` próprio (Numba) e leitor DBF com numpy | `sinan/dbc.py`, `sinan/dbf.py` |
| Interface | módulos JavaScript nativos, sem build e sem framework | `web/js/main.js:1-9` |
| Gráficos | Plotly servido localmente (sem CDN) | `sinan/api/app.py:78`, `web/index.html:17` |
| Mapa | SVG desenhado à mão a partir de GeoJSON do IBGE | `web/js/paginas/mapa.js:70` |
| Excel | openpyxl | `sinan/api/rotas/registros.py:56` |
| Testes | pytest (55 funções de teste em 7 arquivos), ruff | `pyproject.toml:22-27` |

Todas as dependências declaradas têm licença permissiva, conforme o comentário de `pyproject.toml:8`.

### 1.2 Estrutura de pastas

| Pasta | Papel |
|---|---|
| `sinan/` | download do FTP (`download.py`), `.dbc`→Parquet (`dbc.py`, `dbf.py`, `processar.py`, `pipeline.py`), rótulos (`tabnet.py`, `rotulos.py`), consultas (`consultas.py`), catálogo de agravos (`agravos.py`), caminhos (`config.py`) |
| `sinan/api/` | servidor: `app.py` monta tudo; `rotas/` uma por tela; `filtros.py`, `servicos.py`, `cache.py`, `tarefa.py`, `seguranca.py`, `respostas.py` |
| `web/js/` | `main.js`, `roteador.js`, `nucleo/` (estado, filtros, API), `componentes/` (9), `paginas/` (7) |
| `web/css/` | `main.css` importa `base/`, `componentes/` e `paginas/`; cores em `base/tema.css` |
| `referencia/` | tabelas do TabNet, municípios, população e malha do IBGE |
| `dados/` | dados baixados (fora do git); caminho fixo em `sinan/config.py:17` |
| `tests/` | testes com pasta de dados temporária (`tests/conftest.py:23-35`) |
| raiz | `iniciar.py`, `baixar_dados.py`, `INSTALAR.bat`, `ABRIR_DASHBOARD.bat`, `ATUALIZAR_DADOS.bat` |

### 1.3 Rotas

Todas as rotas da API têm o prefixo `/api` (`sinan/api/app.py:56`).

| Método | Caminho | Arquivo | O que devolve | Usa cache? | Paginada? |
|---|---|---|---|---|---|
| GET | `/api/meta` | `sinan/api/rotas/meta.py:19` | agravos, anos, UFs, municípios, faixas, data do último download | em parte (anos e UFs, `sinan/api/filtros.py:49`) | não |
| GET | `/api/geo` | `sinan/api/rotas/meta.py:52` | contorno dos municípios das UFs pedidas | dicionário próprio, sem limite (`sinan/api/rotas/meta.py:49`) | não |
| GET | `/api/visao` | `sinan/api/rotas/painel.py:15` | indicadores e séries por semana, ano e mês | sim (`sinan/api/rotas/painel.py:26`) | não |
| GET | `/api/mapa` | `sinan/api/rotas/painel.py:29` | indicadores e tabela de todos os municípios da área | sim (`sinan/api/rotas/painel.py:35`) | não |
| GET | `/api/perfil` | `sinan/api/rotas/painel.py:38` | indicadores, pirâmide e seis distribuições | sim (`sinan/api/rotas/painel.py:53`) | não |
| GET | `/api/variaveis` | `sinan/api/rotas/variaveis.py:19` | lista de variáveis da ficha | sim (`sinan/api/rotas/variaveis.py:22`) | não |
| GET | `/api/variavel` | `sinan/api/rotas/variaveis.py:25` | distribuição dos casos numa variável | sim (`sinan/api/rotas/variaveis.py:45`) | não |
| GET | `/api/registros` | `sinan/api/rotas/registros.py:29` | fichas individuais (17 colunas) | só o total (`sinan/api/rotas/registros.py:33`) | sim, 50 por página no SQL |
| GET | `/api/exportar` | `sinan/api/rotas/registros.py:39` | arquivo Excel ou CSV | não | não; `csv` e `csv_completo` sem limite de linhas (`sinan/api/rotas/registros.py:51`) |
| GET | `/api/dados` | `sinan/api/rotas/dados.py:95` | inventário local, catálogo do DATASUS, andamento | não | não |
| POST | `/api/dados/listar` | `sinan/api/rotas/dados.py:100` | consulta o FTP do DATASUS | não | não |
| POST | `/api/dados/atualizar` | `sinan/api/rotas/dados.py:109` | inicia download e processamento em segundo plano | não | não |
| GET | `/api/dados/status` | `sinan/api/rotas/dados.py:118` | andamento da atualização | não | não |
| POST | `/api/dados/remover` | `sinan/api/rotas/dados.py:123` | apaga anos de agravos do disco | não (limpa o cache) | não |

Fora da API: página inicial (`sinan/api/app.py:74`), Plotly (`sinan/api/app.py:78`), arquivos da
interface (`sinan/api/app.py:82`) e documentação interativa da API em `/api/docs` (`sinan/api/app.py:52`).

### 1.4 Telas

Sete telas, registradas em `web/js/nucleo/estado.js:8-16` e `web/js/roteador.js:25-33`. As cinco
primeiras têm a barra de filtros; "Atualizar dados" e "Sobre os dados" não.

| Tela (id) | Arquivo | O que mostra |
|---|---|---|
| Visão geral (`visao-geral`) | `web/js/paginas/visao.js` | 6 indicadores, curva semanal por ano, barras por ano e por mês |
| Mapa e municípios (`mapa`) | `web/js/paginas/mapa.js` | indicadores, mapa colorido, painel do município, tabela de municípios |
| Perfil dos casos (`perfil`) | `web/js/paginas/perfil.js` | indicadores, pirâmide etária, seis distribuições em barras |
| Outras variáveis (`variaveis`) | `web/js/paginas/variaveis.js` | lista agrupada de campos da ficha e a distribuição do escolhido |
| Dados e exportação (`dados`) | `web/js/paginas/dados.js` | botões de download e tabela de fichas paginada |
| Atualizar dados (`atualizar`) | `web/js/paginas/atualizar.js` | escolha do que baixar, andamento, inventário e remoção |
| Sobre os dados (`sobre`) | `web/js/paginas/sobre.js` | fonte, definições e cuidados de interpretação |

### 1.5 Inventário de funcionalidades

| ID | Funcionalidade | Onde aparece (tela) | Interface (arquivo:linha) | Servidor (arquivo:linha) | Coberta por teste? |
|---|---|---|---|---|---|
| F01 | Seis indicadores no topo: notificações, confirmados (com % das notificações), incidência, óbitos, letalidade, hospitalizados (ou última notificação), cada um com explicação no ícone "i" | Visão, Mapa, Perfil | `web/js/componentes/kpis.js:15` | `sinan/api/servicos.py:16`, `sinan/consultas.py:165` | sim, só presença (`tests/test_api.py:22`) |
| F02 | Curva por semana epidemiológica, uma linha por ano, último e penúltimo ano em destaque | Visão | `web/js/paginas/visao.js:50` | `sinan/consultas.py:182` | rota sim; valores da semana em `tests/test_processar.py:21` |
| F03 | Barras de casos por ano de notificação | Visão | `web/js/paginas/visao.js:35` | `sinan/consultas.py:211` | rota sim |
| F04 | Barras de casos por mês de início dos sintomas | Visão | `web/js/paginas/visao.js:40` | `sinan/consultas.py:189` | rota sim |
| F05 | Mapa dos municípios colorido por incidência ou casos, com zoom, arrasto, tela cheia e dica ao passar o mouse | Mapa | `web/js/paginas/mapa.js:70`, `web/js/paginas/mapa.js:121` | `sinan/api/servicos.py:30`, `sinan/api/rotas/meta.py:52` | rota sim; desenho não |
| F06 | Painel lateral com os números do município clicado e botão para filtrar por ele | Mapa | `web/js/paginas/mapa.js:172` | `sinan/api/rotas/painel.py:29` | não |
| F07 | Tabela de municípios (inclusive os sem casos) com busca e ordenação por coluna | Mapa | `web/js/paginas/mapa.js:204` | `sinan/api/servicos.py:30` | não |
| F08 | Pirâmide etária por sexo | Perfil | `web/js/paginas/perfil.js:47` | `sinan/consultas.py:226` | rota sim |
| F09 | Distribuições em barras: raça/cor, situação, classificação, evolução, critério, hospitalização | Perfil | `web/js/paginas/perfil.js:12`, `web/js/componentes/barras.js:6` | `sinan/api/rotas/painel.py:46-51` | rota sim |
| F10 | Qualquer variável da ficha, agrupada por assunto, com busca e rótulos oficiais do TabNet | Outras variáveis | `web/js/paginas/variaveis.js:11` | `sinan/api/rotas/variaveis.py:19`, `sinan/api/servicos.py:95` | sim (`tests/test_api.py:39`) |
| F11 | Tabela de fichas individuais, 50 por página, mais recentes primeiro | Dados | `web/js/paginas/dados.js:39` | `sinan/api/rotas/registros.py:29`, `sinan/consultas.py:238` | sim, inclusive ordem estável (`tests/test_api.py:136`) |
| F12 | Exportação: Excel (fichas + resumos por município, semana e ano), CSV de colunas principais, CSV da ficha completa, CSV por município | Todas com filtros (menu Exportar) e Dados | `web/js/componentes/cabecalho.js:15`, `web/js/paginas/dados.js:28` | `sinan/api/rotas/registros.py:39` | sim, 3 de 4 formatos (`tests/test_api.py:46`) |
| F13 | Filtros: agravo, período com atalhos, um município, residência ou notificação, UFs, sexo, faixa etária, tipo de contagem (confirmados, prováveis, notificações) | Telas de análise | `web/js/componentes/filtros.js:11` | `sinan/api/filtros.py:56` | validação sim (`tests/test_api.py:116`) |
| F14 | Filtros lembrados entre sessões (no navegador) | Telas de análise | `web/js/nucleo/filtros.js:23`, `web/js/nucleo/estado.js:26-27` | – | não |
| F15 | Tema claro e escuro, que segue o sistema e fica salvo | Menu lateral | `web/js/main.js:20`, `web/index.html:11` | – | não |
| F16 | Avisos de dados preliminares e avisos específicos do agravo, que podem ser fechados | Telas de análise | `web/js/componentes/alertas.js:8` | `sinan/api/rotas/meta.py:27-30` | não |
| F17 | Baixar dados do DATASUS: consultar o catálogo, escolher UFs, agravos e anos, ver tamanho estimado, acompanhar o andamento | Atualizar dados | `web/js/paginas/atualizar.js:12`, `web/js/paginas/atualizar.js:67` | `sinan/api/rotas/dados.py:100`, `sinan/api/rotas/dados.py:109`, `sinan/api/tarefa.py:44` | só validação de entrada (`tests/test_api.py:100`) |
| F18 | Inventário dos dados baixados (versão nova no DATASUS?) e remoção | Atualizar dados | `web/js/paginas/atualizar.js:131` | `sinan/api/rotas/dados.py:65`, `sinan/api/rotas/dados.py:123` | validação sim (`tests/test_api.py:94`) |
| F19 | Página explicando fonte, definições e cuidados de interpretação | Sobre os dados | `web/js/paginas/sobre.js:3` | – | não |
| F20 | Estados de carregamento (esqueleto), erro e vazio; tela própria quando não há dados | Todas | `web/js/componentes/blocos.js:7-13`, `web/js/roteador.js:62` | `sinan/api/respostas.py` | mensagens de erro sim (`tests/test_api.py:53`) |
| F21 | Endereço por tela (`#/mapa`) — os filtros **não** vão no endereço | Todas | `web/js/nucleo/navegacao.js:5` | – | não |
| F22 | Documentação interativa da API | `/api/docs` | – | `sinan/api/app.py:52` | sim (`tests/test_api.py:107`) |
| F23 | Proteção do servidor local contra outros sites | – | – | `sinan/api/seguranca.py:10` | sim (`tests/test_api.py:71-91`) |
| F24 | Rodapé com a data do último download e nota sobre o cálculo da incidência | Telas de análise | `web/js/componentes/cabecalho.js:44`, `web/js/roteador.js:35` | `sinan/api/rotas/meta.py:36` | não |
| F25 | Menu lateral que vira gaveta em telas estreitas | Todas | `web/js/main.js:43-45`, `web/css/base/estrutura.css:38` | – | não |
| F26 | Erro inesperado da interface aparece na tela em vez de página em branco | Todas | `web/js/main.js:29-36` | `sinan/api/app.py:68-71` | não |

**O que não existe** (procurado e não encontrado): login ou perfis de usuário; comparação com o
período anterior ou variação percentual; diagrama de controle ou limiar epidêmico; clique em
gráfico que filtra os demais; tabulação cruzada (linha × coluna); exportação de gráfico como imagem
ou da tela em PDF; regra de impressão no CSS; link que guarde os filtros; mais de um município no
filtro pela interface (o servidor aceita lista, `sinan/api/filtros.py:79`, mas a tela envia um só,
`web/js/componentes/filtros.js:40`); atualização automática ou agendada; registro de quem acessou.

### 1.6 Dados e atualização

| Fonte | Como chega | Como é atualizada | Arquivo responsável |
|---|---|---|---|
| Microdados do SINAN (`.dbc`, finais e preliminares) | FTP público do DATASUS, filtrado pelas UFs escolhidas e gravado como Parquet | manual: tela "Atualizar dados", `ATUALIZAR_DADOS.bat` ou `baixar_dados.py`; só baixa o que mudou | `sinan/download.py`, `sinan/pipeline.py:33`, `sinan/processar.py:253`, `sinan/config.py:24-28` |
| Municípios e população (IBGE) | CSV versionado em `referencia/`, carregado uma vez em memória | junto com o código | `sinan/config.py:13-14`, `sinan/consultas.py:35-46` |
| Malha municipal (IBGE) | GeoJSON em `referencia/` | junto com o código | `sinan/config.py:15`, `sinan/api/rotas/meta.py:57` |
| Rótulos oficiais (TabNet `.def`/`.cnv`) | arquivos em `referencia/tabnet` | junto com o código | `sinan/tabnet.py`, `sinan/config.py:12` |

Fluxo de atualização: o pedido valida agravos, anos e UFs (`sinan/api/rotas/dados.py:25-50`), salva
a escolha como configuração global (`sinan/api/tarefa.py:49`) e roda numa thread
(`sinan/api/tarefa.py:44-52`). A interface consulta o andamento a cada segundo
(`web/js/paginas/atualizar.js:67-81`). Não há atualização em tempo real nem agendada. As consultas
leem os Parquet a cada pedido (`sinan/consultas.py:82`), e o cache é invalidado quando o inventário
muda (`sinan/api/cache.py:16-21`).

### 1.7 Perfis de usuário

O código **não distingue perfis**: não há login nem conceito de usuário. Qualquer pessoa que abre o
painel pode consultar, exportar fichas, baixar e apagar dados. O público, pelo `CLAUDE.md` (seção 3),
são profissionais de saúde e gestores, não programadores.

### 1.8 O que hoje pressupõe uso local

| Pressuposto | Evidência | Consequência ao publicar |
|---|---|---|
| Servidor escuta só na própria máquina | `iniciar.py:44` (`127.0.0.1`) | precisa de outra forma de subir o servidor |
| Só aceita pedidos com `Host` igual a `localhost` | `sinan/api/seguranca.py:20`, `sinan/api/seguranca.py:31-33` | atrás de um domínio público, **todo pedido recebe 403** |
| Sem login | nenhuma rota usa autenticação (`sinan/api/rotas/`) | qualquer visitante faz tudo |
| Uma pasta de dados fixa | `sinan/config.py:17` | não dá para separar dados por instalação sem mudar código |
| Uma atualização por vez, estado global | `sinan/api/tarefa.py:15`, `sinan/api/tarefa.py:46-48` | a escolha de um usuário muda a configuração de todos (`sinan/api/tarefa.py:49`) |
| Cache e mapa em memória do processo | `sinan/api/cache.py:11`, `sinan/api/rotas/meta.py:49` | cada processo tem o seu; o do mapa cresce sem limite |
| Preferências só no navegador | `web/js/nucleo/estado.js:19-22` | nada acompanha o usuário entre computadores |
| Mensagem de erro interno mostra o texto da exceção | `sinan/api/app.py:71` | detalhes internos aparecem para qualquer visitante |
| Textos que mandam abrir o `.bat` ou falam "no computador" | `web/js/main.js:51`, `web/js/roteador.js:63-64`, `web/js/paginas/atualizar.js:97-99` | não fazem sentido para quem acessa pela internet |

## 2. Diagnóstico

## 3. Benchmark

## 4. Novas funcionalidades

## 5. Priorização e roadmap

## 6. Suposições e pontos a validar
