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

Base da avaliação: o código citado; capturas em `docs/analise/capturas/` (7 telas × tema claro,
tema escuro e celular de 390 px), feitas com chikungunya do Ceará, 2023 e 2024 (19.246
notificações, 184 municípios); e medições com o servidor rodando nesse notebook (Linux, Python
3.12). Escala: **Atende**, **Atende em parte**, **Não atende**, **Não se aplica**.

### 2.1 Hierarquia visual e regra dos 5 segundos — Atende em parte

O título diz o que se vê ("Chikungunya · Ceará · 2023 a 2024", `web/js/componentes/cabecalho.js:14`) e
os seis indicadores são grandes e legíveis (`web/js/componentes/kpis.js:32-38`). Mas em 5 segundos não
dá para dizer **se a situação piorou**: nenhum indicador traz variação em relação ao período anterior
(`sinan/api/servicos.py:16-26` não calcula nada disso). Os seis quadros têm o mesmo peso visual,
inclusive "Óbitos: 2" e "Letalidade: 0,07%". Num notebook (1366×768), filtros e indicadores ocupam a
tela inteira e a curva semanal só começa no rodapé (`capturas/visao-geral-claro.png`); no celular,
a primeira tela inteira é só filtro (`capturas/visao-geral-celular.png`).

### 2.2 Gráfico certo para cada dado — Atende em parte

Acertos: curva semanal com um ano por linha e os dois últimos em destaque (`web/js/paginas/visao.js:50-58`),
pirâmide etária (`web/js/paginas/perfil.js:47`), barras horizontais ordenadas para categorias
(`web/js/componentes/barras.js:6`), mapa que colore por incidência e não só por contagem
(`web/js/paginas/mapa.js:22`). Problemas:

- **Escala do mapa linear**: a cor vai do menor ao maior valor (`web/js/paginas/mapa.js:88-97`). Com
  Tamboril em 619 por 100 mil e a maioria abaixo de 50, quase todo o estado fica da mesma cor clara
  (`capturas/mapa-claro.png`). Classes por quantis ou faixas fixas mostrariam as diferenças.
- **"Zero casos" e "sem dado" quase iguais**: a cor de zero (`--rampa-0`, `web/css/base/tema.css:37`) e a
  de município sem dado (`--mapa-vazio`, `web/css/base/tema.css:34`) têm contraste de 1,02:1.
- **Sem referência de normalidade** na curva semanal: não há diagrama de controle nem limiar
  epidêmico, que é o padrão dos boletins de vigilância.
- "Situação das notificações" e "Classificação final" mostram quase a mesma coisa lado a lado
  (`capturas/perfil-claro.png`, `web/js/paginas/perfil.js:28-29`).

### 2.3 Filtros, detalhamento, comparação e contexto — Atende em parte

Os filtros são completos para o domínio: agravo, período com atalhos, município, residência ou
notificação, UF, sexo, faixa etária e tipo de contagem (`web/js/componentes/filtros.js:11-59`).
O mapa leva ao município e dele ao perfil (`web/js/paginas/mapa.js:197-200`). Os avisos de dados
preliminares dão contexto (`web/js/componentes/alertas.js:11-15`). Faltam:

- clicar num gráfico para filtrar (nenhum gráfico de `web/js/paginas/visao.js` ou
  `web/js/paginas/perfil.js` tem ação de clique);
- escolher **mais de um município** ou uma regional de saúde (a interface manda só um,
  `web/js/componentes/filtros.js:40`, embora o servidor aceite lista, `sinan/api/filtros.py:79`);
- comparar com o período anterior, com outra área ou com uma meta/limiar;
- cruzar duas variáveis (linha × coluna), a operação mais usada no TabNet.

### 2.4 Desempenho e estados de carregamento, vazio e erro — Atende em parte

Estados: toda tela de análise mostra esqueleto enquanto carrega e caixa de erro em português
(`web/js/componentes/blocos.js:7-13`); há tela própria quando ainda não há dados
(`web/js/roteador.js:62-66`) e quadros vazios dizem "Sem informação" (`web/js/paginas/perfil.js:40`).
O download de arquivos, porém, não mostra nada enquanto o servidor monta o Excel: a interface só
redireciona o navegador (`web/js/nucleo/api.js:17`).

Medições (amostra de 19.246 notificações):

| Pedido | Tempo |
|---|---|
| `/api/visao`, `/api/mapa`, `/api/perfil` com cache | 1 a 3 ms |
| `/api/perfil` sem cache, 10 pedidos simultâneos | 0,20 a 0,22 s |
| `/api/registros` (uma página) | 11 ms |
| `/api/exportar` CSV completo (2.904 linhas) | 0,08 s |
| `/api/exportar` Excel (2.904 linhas) | 0,5 s |
| `/api/exportar` Excel (19.246 linhas), sozinho | 2,8 s |
| `/api/exportar` Excel (19.246 linhas), **10 simultâneos** | **30,7 s cada** |

As consultas agregadas aguentam bem várias pessoas. A exportação não: dez downloads ao mesmo tempo
multiplicaram o tempo por dez. Isso acontece numa amostra de um estado; com dengue, o mesmo pedido
pode passar de um milhão de linhas, e só o Excel tem limite (`sinan/api/rotas/registros.py:19`,
`sinan/api/rotas/registros.py:51`). O cache guarda 200 resultados por processo
(`sinan/api/cache.py:11`). Já o cache do mapa não tem limite: um pedido a `/api/geo?ufs=ZZ123`
criou uma entrada nova (`sinan/api/rotas/meta.py:54-60`).

### 2.5 Acessibilidade — Atende em parte

Contraste calculado com as cores de `web/css/base/tema.css` (mínimo de 4,5:1 para texto e 3:1 para
elementos gráficos):

| Par de cores | Claro | Escuro |
|---|---|---|
| Texto secundário (`--muted`) sobre cartão | **4,12** | 5,39 |
| Texto secundário sobre fundo da página | **3,79** | – |
| Texto (`--text-2`) sobre cartão | 8,45 | 9,59 |
| Botão principal | 4,74 | 7,96 |
| Linhas dos anos antigos na curva (`--serie-ctx`) | **1,93** | **2,63** |
| Zero casos × sem dado no mapa | **1,02** | **1,16** |

O texto secundário do tema claro fica abaixo do mínimo, e ele é usado em subtítulos de cartão,
migalha e rodapé (`web/css/base/base.css:24`, `web/css/componentes/cabecalho.css:4`). Por teclado: há
foco visível (`web/css/base/base.css:15`), mas os municípios do mapa não recebem foco
(`web/js/paginas/mapa.js:98`), os títulos da tabela que ordenam são `th` com clique e sem foco
(`web/js/paginas/mapa.js:217-221`), e as dicas dos ícones "i" só aparecem com o mouse
(`web/js/componentes/dica.js:20`), embora tenham `aria-label` (`web/js/componentes/kpis.js:10`). Os
gráficos do Plotly não têm alternativa em texto ou tabela. Cor como única informação: a curva
semanal diferencia os anos por cor e espessura, com legenda (`web/js/paginas/visao.js:57-60`); é
aceitável para dois anos e fica difícil com cinco ou mais.

### 2.6 Responsividade — Atende em parte

Há regras para 1400, 1100, 900 e 520 px em nove arquivos de `web/css/` (por exemplo
`web/css/componentes/filtros.css:25-31`, `web/css/componentes/kpis.css:13-20`) e o menu vira gaveta
(`web/css/base/estrutura.css:38`). Não há rolagem horizontal da página. Mas no celular os filtros
abertos ocupam a primeira tela inteira (`capturas/visao-geral-celular.png`,
`capturas/dados-celular.png`); o mapa fica pequeno e a legenda cobre parte dele; e a tabela de
municípios corta as colunas de números, que só aparecem rolando a tabela para o lado
(`capturas/mapa-celular.png`).

### 2.7 Exportação, compartilhamento e alertas — Atende em parte

Exportação é um ponto forte: quatro formatos, CSV que abre direto no Excel em português
(`sinan/api/rotas/registros.py:24-26`) e Excel com resumos (`sinan/api/rotas/registros.py:54-61`). Faltam:
exportar um gráfico como imagem (a barra do Plotly está desligada, `web/js/componentes/graficos.js:5`),
imprimir ou gerar PDF da tela (não há regra de impressão em `web/css/`), e **link compartilhável**: o
endereço só guarda a tela (`web/js/nucleo/navegacao.js:5-8`), os filtros ficam no navegador
(`web/js/nucleo/filtros.js:23`). Alertas existem só como avisos fixos na tela
(`web/js/componentes/alertas.js:8`); não há alerta por limite de casos nem notificação. Como o painel
será publicado, alertas e envio periódico passam a fazer sentido: **Não atende** nesse ponto.

### 2.8 Personalização — Atende em parte

Ficam salvos o tema (`web/js/main.js:20-24`) e os últimos filtros (`web/js/nucleo/filtros.js:23`), os dois
no navegador (`web/js/nucleo/estado.js:19-22`). Não há filtros favoritos, tela inicial configurável
nem preferências ligadas a uma pessoa: quem troca de computador perde tudo. Avisos fechados voltam
ao recarregar a página (`web/js/nucleo/estado.js:28`).

### 2.9 Segurança e controle de acesso — Não atende (para uso pela internet)

Para uso local, a proteção é correta e testada: `ProtecaoLocal` recusa outros `Host`, outras origens
e POST que não seja JSON (`sinan/api/seguranca.py:31-41`, `tests/test_api.py:71-91`); a entrada é
validada (`sinan/api/rotas/dados.py:31-62`) e o SQL usa parâmetros (`sinan/consultas.py:109-127`). Para a
internet, não há login nem perfis. Pior: atrás de um domínio público **todo pedido recebe 403**
(medido: `Host: painel.exemplo.gov.br` → 403), porque a lista de hosts aceitos só tem `localhost`
(`sinan/api/seguranca.py:20`). Para publicar, alguém terá que mexer nessa proteção, e afrouxá-la sem
colocar login no lugar abriria as rotas abaixo.

**Riscos de publicação, rota a rota** (supondo a proteção ajustada para aceitar o domínio, sem login):

| Rota | O que um visitante anônimo consegue fazer | Risco | Evidência |
|---|---|---|---|
| `POST /api/dados/remover` | apagar qualquer ano de qualquer agravo do servidor | **Bloqueante** | `sinan/api/rotas/dados.py:123-129`, `sinan/processar.py:245-249` |
| `POST /api/dados/atualizar` | disparar downloads de centenas de MB e trocar a configuração de todos (incluindo `BR`) | **Bloqueante** | `sinan/api/rotas/dados.py:109-115`, `sinan/api/tarefa.py:49` |
| `POST /api/dados/listar` | fazer o servidor conectar ao FTP do DATASUS sem limite | Alto | `sinan/api/rotas/dados.py:100-106` |
| `GET /api/exportar` | baixar a ficha completa (145 colunas, inclusive ano de nascimento, unidade de saúde e datas) sem limite de linhas, e derrubar o servidor com pedidos simultâneos | **Bloqueante** | `sinan/api/rotas/registros.py:50-64`, medição em 2.4 |
| `GET /api/registros` | ler fichas individuais, 50 por vez, sem limite de páginas | Alto | `sinan/api/rotas/registros.py:29-36` |
| `GET /api/geo` | encher a memória do servidor com valores inventados de `ufs` | Médio | `sinan/api/rotas/meta.py:49-60` |
| `GET /api/dados`, `GET /api/dados/status` | ver o inventário, a configuração e as mensagens de erro internas das atualizações | Médio | `sinan/api/rotas/dados.py:65-92`, `sinan/api/tarefa.py:37` |
| `GET /api/docs` | ver a lista completa de rotas, inclusive as de administração | Baixo | `sinan/api/app.py:52` |
| `GET /api/visao`, `/api/mapa`, `/api/perfil` | consultar números agregados | Baixo | `sinan/api/rotas/painel.py` |
| `GET /api/variaveis`, `/api/variavel` | consultar distribuições agregadas | Baixo | `sinan/api/rotas/variaveis.py` |
| `GET /api/meta` | ver agravos, anos e municípios disponíveis | Baixo | `sinan/api/rotas/meta.py:19` |
| qualquer rota com erro | ler o texto da exceção interna | Baixo | `sinan/api/app.py:71` |

Outros pontos verificados no código:

- **Uso simultâneo**: só uma atualização por vez (`sinan/api/tarefa.py:46-48`), mas ela vale para
  todos e salva a escolha de quem a disparou como configuração geral (`sinan/api/tarefa.py:49`).
- **Leitura durante a gravação**: o Parquet novo é gravado em arquivo temporário e trocado de uma vez
  (`sinan/processar.py:289`, `sinan/processar.py:321`), o que protege as consultas. A remoção apaga o
  arquivo direto (`sinan/processar.py:246`) e o inventário é regravado sem arquivo temporário
  (`sinan/processar.py:215`).
- **Dados pessoais (LGPD)**: os microdados do DATASUS são públicos e sem nome, mas trazem ano de
  nascimento, sexo, raça, datas e município, que combinados podem identificar pessoas em municípios
  pequenos. **A validar:** se as fichas individuais (`/api/registros`, `/api/exportar`) ficam disponíveis
  na internet ou só os números agregados.
- **Sem HTTPS, sem limite de pedidos por visitante e sem registro de acessos** em nenhuma parte do código.
- **Preferências** só no navegador (`web/js/nucleo/estado.js:19-22`).

**Lacunas encontradas**

| ID | Critério | Nota | Evidência | Lacuna observada |
|---|---|---|---|---|
| G01 | 1 | Atende em parte | `sinan/api/servicos.py:16-26` | O gestor não consegue ver se os casos subiram ou caíram em relação ao mesmo período do ano anterior. |
| G02 | 1, 6 | Atende em parte | `capturas/visao-geral-claro.png`, `capturas/visao-geral-celular.png` | Na primeira tela do notebook e do celular não aparece nenhum gráfico; filtros e indicadores ocupam tudo. |
| G03 | 2 | Atende em parte | `web/js/paginas/mapa.js:88-97` | Um município com incidência muito alta deixa todos os outros com a mesma cor; não dá para ver onde está o problema. |
| G04 | 2, 5 | Não atende | `web/css/base/tema.css:34`, `web/css/base/tema.css:37` | No mapa não se distingue município com zero casos de município sem dado. |
| G05 | 2, 3 | Não atende | `web/js/paginas/visao.js:50` | Não há como saber se o número de casos da semana está acima do esperado (sem diagrama de controle nem limiar). |
| G06 | 3 | Não atende | `web/js/paginas/visao.js`, `web/js/paginas/perfil.js` | Clicar numa semana, faixa etária ou categoria não filtra o resto do painel. |
| G07 | 3 | Atende em parte | `web/js/componentes/filtros.js:40` | Não dá para escolher vários municípios nem uma regional de saúde. |
| G08 | 3 | Não atende | – | Não há tabulação cruzada (ex.: faixa etária × evolução), o principal uso do TabNet. |
| G09 | 4, 9 | Não atende | `sinan/api/rotas/registros.py:51`, medição em 2.4 | Dez exportações simultâneas levam 30 s cada, e o CSV não tem limite de linhas; com várias pessoas o servidor fica lento para todas. |
| G10 | 4, 9 | Não atende | `sinan/api/rotas/meta.py:49-60` | O cache do mapa cresce sem limite com valores inventados. |
| G11 | 4 | Não atende | `web/js/nucleo/api.js:17` | Ao exportar, a pessoa não vê que o arquivo está sendo preparado e clica de novo. |
| G12 | 5 | Não atende | `web/css/base/tema.css:13`, `web/css/base/base.css:24` | Texto secundário do tema claro abaixo do contraste mínimo (4,12 e 3,79). |
| G13 | 5 | Não atende | `web/js/paginas/mapa.js:98`, `web/js/paginas/mapa.js:217`, `web/js/componentes/dica.js:20` | Quem usa só o teclado não escolhe município no mapa, não ordena a tabela e não lê as dicas. |
| G14 | 5 | Não atende | `web/js/componentes/graficos.js:23` | Gráficos sem alternativa em texto ou tabela para leitor de tela. |
| G15 | 6 | Atende em parte | `capturas/mapa-celular.png` | No celular o mapa é pequeno, a legenda cobre parte dele e a tabela esconde as colunas de números. |
| G16 | 7 | Não atende | `web/js/nucleo/navegacao.js:5-8` | Não dá para mandar a um colega um link que abra o painel com os mesmos filtros. |
| G17 | 7 | Não atende | `web/js/componentes/graficos.js:5` | Não dá para salvar um gráfico como imagem nem imprimir a tela para uma reunião. |
| G18 | 7 | Não atende | `web/js/componentes/alertas.js:8` | Ninguém é avisado quando os casos passam de um limite ou quando chegam dados novos. |
| G19 | 8 | Atende em parte | `web/js/nucleo/estado.js:19-22` | Filtros favoritos e preferências não acompanham a pessoa entre computadores. |
| G20 | 9 | Não atende | `sinan/api/seguranca.py:20` | O painel não abre atrás de um domínio público (403 em tudo). |
| G21 | 9 | Não atende | `sinan/api/rotas/dados.py:109-129` | Qualquer visitante poderia apagar dados ou disparar downloads. |
| G22 | 9 | Não atende | – | Não há login nem perfis (consulta e administração). |
| G23 | 9 | Não atende | `sinan/api/rotas/registros.py:29-64` | Fichas individuais ficariam abertas a qualquer pessoa na internet. |
| G24 | 9 | Não atende | – | Não há limite de pedidos por visitante nem registro de quem acessou e exportou. |
| G25 | 9 | Atende em parte | `sinan/api/tarefa.py:49`, `sinan/processar.py:215` | A atualização de um administrador muda a configuração de todos, e o inventário é regravado sem proteção contra falha. |
| G26 | 9 | Não atende | `sinan/api/app.py:71`, `sinan/api/tarefa.py:37` | Mensagens internas de erro aparecem para qualquer visitante. |
| G27 | 1 | Não atende | `web/js/main.js:51`, `web/js/roteador.js:63-64`, `web/js/paginas/atualizar.js:97-99` | Textos falam em "no computador" e em abrir o `.bat`, o que confunde quem acessa pela internet. |

## 3. Benchmark

## 4. Novas funcionalidades

## 5. Priorização e roadmap

## 6. Suposições e pontos a validar
