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
painel pode consultar, exportar fichas, baixar e apagar dados. O público, pelas regras do projeto,
são profissionais de saúde e gestores, não programadores.

### 1.8 O que hoje pressupõe uso local

| Pressuposto | Evidência | Consequência ao publicar |
|---|---|---|
| Servidor escuta só na própria máquina | `iniciar.py:44` (`127.0.0.1`) | precisa de outra forma de subir o servidor |
| Só aceita pedidos com `Host` igual a `localhost` | `sinan/api/seguranca.py:20`, `sinan/api/seguranca.py:31-36` | atrás de um proxy com o domínio público, **todo pedido recebe 403**; com HTTPS, todo POST recebe 403 pela checagem de origem `http://` |
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
internet, não há login nem perfis. Pior: o painel não funciona publicado. O servidor só escuta em
`127.0.0.1` (`iniciar.py:44`), então precisa de um proxy na frente. Se o proxy repassar o domínio
público, **todo pedido recebe 403** (medido: `Host: painel.exemplo.gov.br` → 403), porque a lista de
hosts aceitos só tem `localhost` (`sinan/api/seguranca.py:20`). Se o proxy repassar o host local, as
consultas passam, mas **todo POST via HTTPS recebe 403**: a origem exigida é sempre `http://`
(`sinan/api/seguranca.py:36`), e o navegador manda `https://`. Para publicar, alguém terá que mexer nessa proteção, e afrouxá-la sem
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
| G20 | 9 | Não atende | `sinan/api/seguranca.py:20`, `sinan/api/seguranca.py:36` | O painel não funciona publicado: 403 em tudo com o domínio público, ou 403 em todo POST com HTTPS. |
| G21 | 9 | Não atende | `sinan/api/rotas/dados.py:109-129` | Qualquer visitante poderia apagar dados ou disparar downloads. |
| G22 | 9 | Não atende | – | Não há login nem perfis (consulta e administração). |
| G23 | 9 | Não atende | `sinan/api/rotas/registros.py:29-64` | Fichas individuais ficariam abertas a qualquer pessoa na internet. |
| G24 | 9 | Não atende | – | Não há limite de pedidos por visitante nem registro de quem acessou e exportou. |
| G25 | 9 | Atende em parte | `sinan/api/tarefa.py:49`, `sinan/processar.py:215` | A atualização de um administrador muda a configuração de todos, e o inventário é regravado sem proteção contra falha. |
| G26 | 9 | Não atende | `sinan/api/app.py:71`, `sinan/api/tarefa.py:37` | Mensagens internas de erro aparecem para qualquer visitante. |
| G27 | 1 | Não atende | `web/js/main.js:51`, `web/js/roteador.js:63-64`, `web/js/paginas/atualizar.js:97-99` | Textos falam em "no computador" e em abrir o `.bat`, o que confunde quem acessa pela internet. |

## 3. Benchmark

Cinco referências, consultadas em 16/11/2026 nas páginas oficiais. O painel do Ministério e a página
municipal do InfoDengue só montam o conteúdo com JavaScript, então foram vistos por captura de tela.
O painel do Ministério é um relatório Power BI público ("Sala Nacional de Arboviroses").

| Referência | Por que entra |
|---|---|
| TabNet / TabWin (DATASUS) | é a ferramenta que o público já usa com os mesmos dados |
| InfoDengue (Fiocruz/FGV) | alertas por cor, limiar epidêmico, correção do atraso de notificação |
| Painel de Monitoramento das Arboviroses (Ministério da Saúde) | painel oficial de gestão, público |
| Metabase | ferramenta aberta de painéis: filtros ligados, perguntas salvas, permissões |
| Power BI | ferramenta corporativa: filtro cruzado, envio por e-mail, restrição por perfil |

### 3.1 O que o painel já faz como as referências

| Função das referências | Onde está no painel |
|---|---|
| Casos por semana epidemiológica, um ano ao lado do outro (Painel MS, TabNet) | F02 |
| Incidência por 100 mil habitantes e letalidade (Painel MS, InfoDengue) | F01 |
| Mapa por município (Painel MS, InfoDengue) | F05 |
| Detalhar até o município, por residência ou notificação (TabNet, Painel MS) | F05, F06, F13 |
| Pirâmide por faixa etária e sexo (Painel MS) | F08 |
| Qualquer variável da ficha com os rótulos oficiais (TabNet) | F10 |
| CSV com ";" e vírgula decimal (TabNet) | F12 |
| Notas sobre dados preliminares e definições (TabNet, Painel MS) | F16, F19 |

### 3.2 O que as referências têm e o painel não

| ID | Referência | Função relevante | O painel tem? | Link da fonte | Modo de uso (local, publicado ou os dois) |
|---|---|---|---|---|---|
| B01 | TabNet | Tabulação cruzada: uma variável na linha, outra na coluna, com filtros | não | <http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebbr.def> | os dois |
| B02 | TabNet | Agrupar por Região de Saúde (CIR) e por município de infecção | não (sem tabela de regionais em `referencia/`) | <http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebbr.def> | os dois |
| B03 | TabNet | Data de atualização de cada ano na nota técnica | em parte: F24 mostra só a data do download | <http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebbr.def> | os dois |
| B04 | InfoDengue | Nível de alerta em 4 cores por município, toda semana | não | <https://info.dengue.mat.br/informacoes/> | os dois |
| B05 | InfoDengue | Limiar epidêmico histórico (casos esperados por semana, faixa de 10% a 90%) — equivale ao canal endêmico | não | <https://info.dengue.mat.br/informacoes/> | os dois |
| B06 | InfoDengue | Correção do atraso de notificação (estimativa das últimas semanas) | não: só um aviso em texto (`web/js/paginas/visao.js:16`) | <https://info.dengue.mat.br/informacoes/> | os dois |
| B07 | InfoDengue | Página do município: incidência da semana, histórico colorido pelo alerta, mapa da região de saúde | em parte: F06 mostra o período inteiro | <https://info.dengue.mat.br/alerta/3304557/dengue> | os dois |
| B08 | InfoDengue | Relatórios por município e por regional, com indicadores e alertas | não | <https://info.dengue.mat.br/report/> | os dois |
| B09 | InfoDengue | API pública documentada (JSON/CSV) por município e semana | em parte: F22 existe, mas não é pensada para uso externo | <https://info.dengue.mat.br/services/api/doc> | publicado |
| B10 | InfoDengue, Metabase | Salvar o gráfico como imagem | não (`web/js/componentes/graficos.js:5`) | <https://www.metabase.com/docs/latest/questions/exporting-results> | os dois |
| B11 | Painel MS | Filtro por intervalo de semanas epidemiológicas | não: o período é só em anos (F13) | <https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/aedes-aegypti/monitoramento-das-arboviroses/painel-1> | os dois |
| B12 | Painel MS | Indicadores de óbitos em investigação e letalidade nos casos graves | em parte (F01) | <https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/aedes-aegypti/monitoramento-das-arboviroses/painel-1> | os dois |
| B13 | Painel MS | Incidência por faixa etária e sexo | não: o painel não calcula com esses filtros (`web/js/componentes/kpis.js:24`; `referencia/populacao.csv` não tem sexo nem idade) | <https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/aedes-aegypti/monitoramento-das-arboviroses/painel-1> | os dois |
| B14 | Painel MS, Power BI | Tabela Região → UF → Município × semana, que abre e fecha | não | <https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-matrix-visual> | os dois |
| B15 | Painel MS | Botão "Limpar filtros" para todos os filtros | em parte: limpa só os de "Mais filtros" (`web/js/componentes/filtros.js:55`) | <https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/aedes-aegypti/monitoramento-das-arboviroses/painel-1> | os dois |
| B16 | Metabase, Power BI | Filtro cruzado: clicar num gráfico filtra os outros | não | <https://www.metabase.com/docs/latest/dashboards/interactive> | os dois |
| B17 | Metabase | Exportar o painel inteiro em PDF | não | <https://www.metabase.com/docs/latest/questions/exporting-results> | os dois |
| B18 | Metabase | Perguntas e visões salvas para reabrir depois | não | <https://www.metabase.com/docs/latest/questions/introduction> | publicado (por pessoa); local (no navegador) |
| B19 | Metabase | Dicionário de dados com descrição de cada campo | em parte: nomes amigáveis (F10) e definições (F19), sem descrição por campo | <https://www.metabase.com/docs/latest/data-modeling/metadata-editing> | os dois |
| B20 | Metabase, Power BI | Login com contas e grupos de permissão | não | <https://www.metabase.com/docs/latest/people-and-groups/managing> | publicado |
| B21 | Metabase, Power BI | Restrição de dados por perfil (ex.: só a UF ou o município da pessoa) | não | <https://www.metabase.com/docs/latest/permissions/row-and-column-security> | publicado |
| B22 | Metabase | Link público ou painel incorporado em outro site, com filtros | não | <https://www.metabase.com/docs/latest/embedding/public-links> | publicado |
| B23 | Metabase, Power BI | Envio agendado por e-mail com anexo | não | <https://www.metabase.com/docs/latest/dashboards/subscriptions> | publicado |
| B24 | Metabase, Power BI | Alerta quando uma série passa de uma meta ou limite | não | <https://www.metabase.com/docs/latest/questions/alerts> | publicado |
| B25 | Metabase, Power BI | Registro de quem viu e baixou o quê | não | <https://www.metabase.com/docs/latest/usage-and-performance-tools/usage-analytics> | publicado |
| B26 | Power BI | Linhas de referência (média, percentil) e detecção de anomalias em séries | não | <https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-analytics-pane> | os dois |
| B27 | Power BI | Limite de linhas na exportação (150 mil em Excel, 30 mil em CSV), que o administrador pode desligar | não: CSV sem limite (`sinan/api/rotas/registros.py:51`) | <https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-export-data> | os dois |

### 3.3 Lições das referências para a publicação

- **Os três painéis públicos da área mostram só números agregados** e nenhum exige login. A ficha
  individual fica no TabWin ou atrás de acesso restrito. É um bom modelo para o painel publicado:
  agregados abertos, fichas só com login.
- **O Power BI desliga a restrição por perfil e a exportação de dados quando o relatório é público**
  (<https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-publish-to-web>), e o Metabase
  não aplica a restrição de linhas em links públicos. Quem publica separa a área aberta da área com login.
- Login, restrição por perfil, registro de acessos e envio com anexo são **pagos** no Metabase
  (Pro, a partir de US$ 575/mês, <https://www.metabase.com/pricing/>) e no Power BI (Pro/Premium).
  Fazer o próprio painel com essas funções evita custo por usuário, mas é trabalho de desenvolvimento.
- O que diferencia o InfoDengue é a leitura epidemiológica: limiar, alerta e correção do atraso.
  Nenhuma ferramenta genérica (Metabase, Power BI) traz isso pronto.

## 4. Novas funcionalidades

Régua de impacto: **Alto** = muda uma decisão de gestão, elimina uma ida ao TabNet ou impede a
publicação; **Médio** = economiza tempo numa tarefa recorrente; **Baixo** = conforto.
Esforço: **P** até 1 dia, **M** de 2 a 5 dias, **G** mais de 1 semana, para uma pessoa que já conhece o código.
**Suposição:** as estimativas de esforço incluem os testes e a atualização do `README.md`, e não incluem
infraestrutura do servidor (domínio, certificado, máquina).

A numeração vai de N01 a N30 sem N23 (o item foi incorporado à N22), num total de 29 fichas.
Marcadores no título: **Pré-requisito de publicação** (o painel não pode ir para a internet sem isso)
e **Correção** (defeito, não funcionalidade nova).

### 4.1 Pré-requisitos de publicação

#### N01 — Endereço público configurável · Pré-requisito de publicação
- **Descrição:** o servidor passa a aceitar o domínio onde for publicado e a rodar atrás de um proxy com HTTPS, definidos numa configuração; sem ela, continua só local.
- **Problema que resolve:** hoje o painel não funciona fora do computador (403 em todo pedido com o domínio público, ou em todo POST com HTTPS).
- **Origem:** G20
- **Impacto:** Alto — sem isso não há publicação.
- **Esforço:** M — mexe na proteção de segurança, que tem testes, e precisa de um guia de implantação.
- **Dependências técnicas:** nenhuma dependência nova; o HTTPS fica no proxy (ex.: Caddy, Apache-2.0; ou nginx, BSD). **A validar:** onde o sistema será hospedado.
- **Arquivos afetados:** `sinan/api/seguranca.py`, `iniciar.py`, `sinan/config.py`, `tests/test_api.py`, `README.md`
- **Modo de uso:** Os dois — no local nada muda; no publicado, a lista de hosts e origens aceitos vem da configuração.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/endereco-publico`, criada a partir da `develop`

#### N02 — Login e perfis de acesso · Pré-requisito de publicação
- **Descrição:** contas com dois perfis, "consulta" e "administração"; só administração vê a tela "Atualizar dados" e usa as rotas `/api/dados/*`.
- **Problema que resolve:** hoje qualquer visitante poderia apagar dados ou disparar downloads de centenas de MB.
- **Origem:** G21, G22, B20
- **Impacto:** Alto — fecha os dois riscos bloqueantes de administração.
- **Esforço:** G — contas, senhas, sessão, telas de entrada e testes de permissão rota a rota.
- **Dependências técnicas:** N01; senhas com `hashlib.scrypt` (biblioteca padrão); sessão com `SessionMiddleware` do Starlette (precisa de `itsdangerous`, BSD). **A validar:** se haverá login do governo (gov.br) ou contas próprias.
- **Arquivos afetados:** novo: `sinan/api/acesso.py`, novo: `sinan/api/rotas/conta.py`, novo: `web/js/paginas/entrar.js`; `sinan/api/app.py`, `sinan/api/rotas/dados.py`, `web/js/nucleo/estado.js`, `web/js/roteador.js`, `tests/test_api.py`
- **Modo de uso:** Só publicado — no local o login fica desligado e a pessoa é tratada como administradora.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/login-perfis`, criada a partir da `develop`

#### N03 — Área aberta só com números agregados · Pré-requisito de publicação
- **Descrição:** sem login, o painel mostra indicadores, gráficos e mapa; fichas individuais e exportação de fichas exigem login, e um perfil pode ficar restrito à sua UF ou aos seus municípios.
- **Problema que resolve:** fichas com ano de nascimento, sexo, datas e município ficariam abertas na internet (risco LGPD).
- **Origem:** G23, B21
- **Impacto:** Alto — segue o modelo dos painéis públicos da área (seção 3.3).
- **Esforço:** M — a restrição por UF entra no `Filtro`, que já monta todo o SQL.
- **Dependências técnicas:** N02. **A validar:** se as fichas ficam disponíveis pela internet mesmo com login.
- **Arquivos afetados:** `sinan/api/filtros.py`, `sinan/api/rotas/registros.py`, `sinan/consultas.py`, `web/js/paginas/dados.js`, `web/js/componentes/cabecalho.js`, `tests/test_api.py`
- **Modo de uso:** Só publicado — no local tudo continua liberado.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/area-aberta-agregada`, criada a partir da `develop`

#### N04 — Limites de exportação e de pedidos · Pré-requisito de publicação
- **Descrição:** limite de linhas também no CSV, no máximo duas exportações pesadas ao mesmo tempo (as demais esperam com aviso), limite de pedidos por visitante, e `ufs` do mapa validado contra a lista de UFs.
- **Problema que resolve:** dez exportações simultâneas levaram 30 s cada; com dengue, um pedido pode ter milhões de linhas e travar o servidor para todos.
- **Origem:** G09, G10, G24, B27
- **Impacto:** Alto — protege o painel para todos os usuários.
- **Esforço:** M — limite e fila são simples; o limite por visitante precisa de testes de concorrência.
- **Dependências técnicas:** nenhuma dependência nova (`threading.Semaphore`, contagem em memória). **Suposição:** um único processo do servidor; com vários, o limite por visitante vai para o proxy.
- **Arquivos afetados:** `sinan/api/rotas/registros.py`, `sinan/api/rotas/meta.py`, `sinan/api/seguranca.py`, `tests/test_api.py`
- **Modo de uso:** Os dois — no local, os limites protegem o computador da pessoa contra arquivos enormes.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/limites-exportacao`, criada a partir da `develop`

#### N05 — Erros sem detalhes internos · Pré-requisito de publicação
- **Descrição:** no modo publicado, erro interno mostra só uma mensagem geral e um código para o suporte; a documentação da API fica restrita à administração.
- **Problema que resolve:** mensagens de exceção e a lista de rotas de administração apareceriam para qualquer visitante.
- **Origem:** G26
- **Impacto:** Médio — reduz o que um atacante aprende sobre o servidor.
- **Esforço:** P — dois pontos do código.
- **Dependências técnicas:** N01 (saber se está publicado), N02 (perfil de administração).
- **Arquivos afetados:** `sinan/api/app.py`, `sinan/api/tarefa.py`, `tests/test_api.py`
- **Modo de uso:** Os dois — no local a mensagem completa continua útil.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/erros-sem-detalhes`, criada a partir da `develop`

### 4.2 Correções

#### N09 — Contraste e cores do mapa · Correção
- **Descrição:** escurecer o texto secundário do tema claro para pelo menos 4,5:1, dar cor própria a "sem dado" no mapa (hachura ou cinza com contorno) e reforçar as linhas dos anos antigos.
- **Problema que resolve:** subtítulos com contraste 3,79 a 4,12; zero casos e sem dado indistinguíveis (1,02).
- **Origem:** G04, G12
- **Impacto:** Médio — leitura e interpretação do mapa.
- **Esforço:** P — só variáveis de `tema.css` e uma regra no mapa.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `web/css/base/tema.css`, `web/js/paginas/mapa.js`, `web/css/paginas/mapa.css`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/contraste-cores`, criada a partir da `develop`

#### N10 — Uso pelo teclado e gráficos legíveis por leitor de tela · Correção
- **Descrição:** municípios do mapa e títulos da tabela alcançáveis por Tab, dicas que abrem com o foco, e um botão "ver em tabela" em cada gráfico.
- **Problema que resolve:** quem não usa mouse não escolhe município nem ordena a tabela; leitores de tela não leem os gráficos.
- **Origem:** G13, G14
- **Impacto:** Médio — exigência de acessibilidade para sistema público.
- **Esforço:** M — mexe em mapa, tabela, dicas e no componente de gráficos.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `web/js/paginas/mapa.js`, `web/js/componentes/dica.js`, `web/js/componentes/graficos.js`, `web/js/paginas/visao.js`, `web/js/paginas/perfil.js`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/acessibilidade-teclado`, criada a partir da `develop`

### 4.3 Leitura epidemiológica

#### N11 — Variação em relação ao ano anterior
- **Descrição:** cada indicador mostra a variação percentual em relação ao mesmo período (mesmas semanas epidemiológicas) do ano anterior, com seta e texto ("+35% em relação a 2023").
- **Problema que resolve:** em 5 segundos o gestor não sabe se a situação piorou.
- **Origem:** G01
- **Impacto:** Alto — é a primeira pergunta de quem abre o painel.
- **Esforço:** M — o "mesmo período" do ano em curso precisa cortar pelas semanas já notificadas.
- **Dependências técnicas:** dados do ano anterior baixados; quando faltarem, a variação não aparece.
- **Arquivos afetados:** `sinan/api/servicos.py`, `sinan/consultas.py`, `web/js/componentes/kpis.js`, `web/js/paginas/sobre.js`, `tests/test_consultas.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não, mas a definição de "mesmo período" vai para a tela "Sobre os dados".
- **Branch:** `feature/variacao-ano-anterior`, criada a partir da `develop`

#### N12 — Diagrama de controle na curva semanal
- **Descrição:** faixa de casos esperados por semana (canal endêmico), calculada com os anos anteriores, desenhada atrás da curva do ano atual.
- **Problema que resolve:** não há como saber se a semana está acima do esperado.
- **Origem:** G05, B05, B26
- **Impacto:** Alto — é a ferramenta clássica para declarar epidemia.
- **Esforço:** G — escolher e validar o método (quartis ou média ± 2 desvios, excluindo anos epidêmicos), com testes contra um caso publicado.
- **Dependências técnicas:** pelo menos 5 anos de dados do agravo (download maior). **A validar:** qual método a vigilância local usa.
- **Arquivos afetados:** `sinan/consultas.py`, `sinan/api/rotas/painel.py`, `web/js/paginas/visao.js`, `web/js/paginas/sobre.js`, `tests/test_consultas.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Sim (exige teste e ajuste na tela "Sobre os dados")
- **Branch:** `feature/diagrama-controle`, criada a partir da `develop`

#### N13 — Nível de alerta por município
- **Descrição:** cada município recebe uma cor de alerta na semana (abaixo, dentro ou acima do esperado), no mapa e na tabela.
- **Problema que resolve:** o gestor estadual não vê quais municípios entraram em situação de epidemia.
- **Origem:** B04, G18
- **Impacto:** Alto — orienta para onde mandar equipe e insumos.
- **Esforço:** G — usa o diagrama de controle por município, com regra para municípios pequenos.
- **Dependências técnicas:** N12.
- **Arquivos afetados:** `sinan/api/servicos.py`, `web/js/paginas/mapa.js`, `web/js/paginas/sobre.js`, `tests/test_consultas.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Sim (exige teste e ajuste na tela "Sobre os dados")
- **Branch:** `feature/alerta-municipio`, criada a partir da `develop`

#### N14 — Estimativa das últimas semanas (atraso de notificação)
- **Descrição:** mostrar, tracejado, quantos casos as últimas semanas devem ter quando as notificações atrasadas chegarem.
- **Problema que resolve:** a curva parece cair no fim por atraso, e isso pode levar a concluir que a epidemia acabou.
- **Origem:** B06
- **Impacto:** Médio — hoje há um aviso em texto que já reduz o erro de leitura.
- **Esforço:** G — método estatístico (como o do InfoDengue) e validação.
- **Dependências técnicas:** N12; dados preliminares atualizados com frequência. **A validar:** se vale o esforço frente aos alertas do InfoDengue.
- **Arquivos afetados:** `sinan/consultas.py`, `web/js/paginas/visao.js`, `web/js/paginas/sobre.js`, `tests/test_consultas.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Sim (exige teste e ajuste na tela "Sobre os dados")
- **Branch:** `feature/estimativa-atraso`, criada a partir da `develop`

#### N26 — Novos indicadores: óbitos em investigação e incidência por sexo e idade
- **Descrição:** indicador de óbitos em investigação e cálculo da incidência quando há filtro de sexo ou faixa etária.
- **Problema que resolve:** hoje a incidência some com esses filtros e os óbitos em investigação não aparecem.
- **Origem:** B12, B13
- **Impacto:** Médio — usados nos boletins.
- **Esforço:** M — precisa de uma tabela nova de população.
- **Dependências técnicas:** população por município, sexo e faixa etária (IBGE), novo arquivo em `referencia/`.
- **Arquivos afetados:** `sinan/consultas.py`, `sinan/api/servicos.py`, `sinan/config.py`, `web/js/componentes/kpis.js`, `web/js/paginas/sobre.js`, `tests/test_consultas.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Sim (exige teste e ajuste na tela "Sobre os dados")
- **Branch:** `feature/novos-indicadores`, criada a partir da `develop`

### 4.4 Visualização e navegação

#### N15 — Primeira tela mais compacta
- **Descrição:** filtros recolhidos numa linha de resumo (que abre ao tocar) e indicadores em faixa mais baixa, para a curva aparecer na primeira tela do notebook e do celular.
- **Problema que resolve:** hoje filtros e indicadores ocupam toda a primeira tela.
- **Origem:** G02, G15
- **Impacto:** Alto — aplica a regra dos 5 segundos.
- **Esforço:** M — CSS e componente de filtros, conferido nas três larguras com capturas.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `web/js/componentes/filtros.js`, `web/css/componentes/filtros.css`, `web/css/componentes/kpis.css`, `web/css/base/estrutura.css`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/primeira-tela`, criada a partir da `develop`

#### N16 — Mapa com faixas de cor e melhor no celular
- **Descrição:** cores por faixas (quantis ou cortes fixos) com legenda de faixas, e no celular legenda abaixo do mapa e tabela só com município e a medida escolhida.
- **Problema que resolve:** um município extremo deixa todos os outros com a mesma cor; no celular a legenda cobre o mapa.
- **Origem:** G03, G15
- **Impacto:** Alto — o mapa passa a mostrar onde está o problema.
- **Esforço:** P — troca da função de cor e da legenda.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `web/js/paginas/mapa.js`, `web/css/paginas/mapa.css`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/mapa-faixas`, criada a partir da `develop`

#### N17 — Link com os filtros
- **Descrição:** os filtros entram no endereço (`#/mapa?agravo=DENG&ini=2023...`), e um botão "Copiar link" copia esse endereço.
- **Problema que resolve:** não dá para mandar a um colega o painel aberto no mesmo recorte.
- **Origem:** G16, B22
- **Impacto:** Alto — no modo publicado, é a forma de compartilhar.
- **Esforço:** P — a interface já monta esses parâmetros para a API (`web/js/nucleo/filtros.js:27`).
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `web/js/nucleo/navegacao.js`, `web/js/nucleo/filtros.js`, `web/js/main.js`, `web/js/componentes/cabecalho.js`
- **Modo de uso:** Os dois — no local o link serve para guardar um recorte.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/link-filtros`, criada a partir da `develop`

#### N18 — Vários municípios e regionais de saúde
- **Descrição:** escolher mais de um município e agrupar por regional de saúde (CIR) nos filtros, no mapa e na tabela.
- **Problema que resolve:** coordenadores de regional não conseguem ver a sua região.
- **Origem:** G07, B02
- **Impacto:** Alto — é a unidade de gestão das secretarias estaduais.
- **Esforço:** M — o servidor já aceita lista de municípios; falta a tabela de regionais e a interface.
- **Dependências técnicas:** tabela oficial de regiões de saúde por município (Ministério da Saúde/IBGE), novo CSV em `referencia/`.
- **Arquivos afetados:** `web/js/componentes/filtros.js`, `web/js/nucleo/estado.js`, `sinan/api/filtros.py`, `sinan/api/rotas/meta.py`, `sinan/config.py`, `tests/test_api.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/regionais-saude`, criada a partir da `develop`

#### N19 — Tabulação cruzada
- **Descrição:** tela nova onde a pessoa escolhe uma variável para as linhas e outra para as colunas (ex.: município × semana, faixa etária × evolução), com totais e exportação.
- **Problema que resolve:** hoje é preciso voltar ao TabNet para cruzar duas variáveis.
- **Origem:** G08, B01, B14
- **Impacto:** Alto — elimina a ida ao TabNet, com rótulos oficiais já prontos.
- **Esforço:** G — tela nova, rota nova e limites de tamanho da tabela.
- **Dependências técnicas:** reaproveita `rotulos`, `tabnet.ler_cnv` e `consultas.contagem`.
- **Arquivos afetados:** novo: `sinan/api/rotas/tabulacao.py`, novo: `web/js/paginas/tabulacao.js`; `sinan/consultas.py`, `sinan/api/rotas/__init__.py`, `web/js/nucleo/estado.js`, `web/js/roteador.js`, `tests/test_api.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/tabulacao-cruzada`, criada a partir da `develop`

#### N20 — Filtro por semanas epidemiológicas
- **Descrição:** escolher um intervalo de semanas (ex.: semanas 1 a 20) além dos anos.
- **Problema que resolve:** boletins comparam "até a semana X"; hoje o período é só em anos inteiros.
- **Origem:** B11
- **Impacto:** Médio — usado em boletins e comparações.
- **Esforço:** M — o `Filtro` ganha dois campos e todas as consultas passam a respeitá-los.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `sinan/consultas.py`, `sinan/api/filtros.py`, `web/js/componentes/filtros.js`, `web/js/nucleo/filtros.js`, `tests/test_consultas.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/filtro-semanas`, criada a partir da `develop`

#### N21 — Clicar no gráfico para filtrar
- **Descrição:** clicar numa barra (faixa etária, raça, ano) ou num município aplica esse filtro em todo o painel, com um aviso de filtro ativo.
- **Problema que resolve:** explorar os dados exige voltar aos filtros a cada pergunta.
- **Origem:** G06, B16
- **Impacto:** Médio — acelera a exploração.
- **Esforço:** M — só categorias que já são filtros podem filtrar.
- **Dependências técnicas:** N20 para clicar em semanas.
- **Arquivos afetados:** `web/js/paginas/visao.js`, `web/js/paginas/perfil.js`, `web/js/componentes/barras.js`, `web/js/nucleo/filtros.js`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/clique-filtra`, criada a partir da `develop`

### 4.5 Exportação, compartilhamento e alertas

#### N22 — Imagem dos gráficos, impressão e aviso de andamento
- **Descrição:** botão para salvar cada gráfico como imagem, estilo de impressão que gera um PDF limpo da tela, e aviso "Preparando o arquivo..." durante a exportação.
- **Problema que resolve:** levar gráficos para reunião e boletim exige captura de tela; na exportação, a pessoa clica de novo achando que não funcionou.
- **Origem:** G11, G17, B10, B17
- **Impacto:** Médio — tarefa recorrente de quem faz boletim.
- **Esforço:** P — o Plotly já salva imagem; a impressão é uma regra `@media print`.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `web/js/componentes/graficos.js`, `web/js/nucleo/api.js`, novo: `web/css/base/impressao.css`, `web/css/main.css`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/imagem-impressao`, criada a partir da `develop`

#### N24 — Filtros favoritos
- **Descrição:** salvar recortes com nome ("Dengue · Regional Norte · 2024") e abrir com um clique.
- **Problema que resolve:** quem acompanha os mesmos recortes refaz os filtros toda vez.
- **Origem:** G19, B18
- **Impacto:** Médio — economiza tempo diário.
- **Esforço:** M — guarda no navegador no modo local e na conta no modo publicado.
- **Dependências técnicas:** N17 (o favorito é um link); N02 para guardar na conta.
- **Arquivos afetados:** `web/js/nucleo/estado.js`, `web/js/componentes/filtros.js`, `sinan/api/rotas/conta.py` (criado em N02)
- **Modo de uso:** Os dois — local no navegador; publicado na conta da pessoa.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/favoritos`, criada a partir da `develop`

#### N25 — Alertas e boletim por e-mail
- **Descrição:** a pessoa assina um recorte e recebe por e-mail um resumo semanal e um aviso quando um município entra em alerta.
- **Problema que resolve:** ninguém é avisado sem abrir o painel.
- **Origem:** G18, B23, B24
- **Impacto:** Médio — antecipa a resposta, mas depende de alguém agir.
- **Esforço:** G — envio de e-mail, agendamento e descadastro.
- **Dependências técnicas:** N02, N06, N13; servidor de e-mail (SMTP) da instituição, com `smtplib` da biblioteca padrão. **A validar:** se a instituição fornece SMTP.
- **Arquivos afetados:** novo: `sinan/avisos.py`; `sinan/api/rotas/conta.py` (criado em N02), `sinan/api/tarefa.py`, `tests/test_api.py`
- **Modo de uso:** Só publicado — desligado no local.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/alertas-email`, criada a partir da `develop`

#### N27 — Relatório do município ou da regional
- **Descrição:** página pronta para imprimir com indicadores, curva com diagrama de controle, mapa da regional e perfil, para um município ou regional.
- **Problema que resolve:** montar o boletim semanal hoje exige juntar várias telas.
- **Origem:** B07, B08
- **Impacto:** Médio — produto final de muitas secretarias.
- **Esforço:** G — tela nova que junta várias outras.
- **Dependências técnicas:** N12, N18, N22.
- **Arquivos afetados:** novo: `web/js/paginas/relatorio.js`; `web/js/nucleo/estado.js`, `web/js/roteador.js`, `sinan/api/rotas/painel.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/relatorio-municipio`, criada a partir da `develop`

### 4.6 Operação do modo publicado

#### N06 — Atualização agendada e segura
- **Descrição:** o administrador agenda a atualização (ex.: toda segunda); a configuração de download deixa de ser alterada por quem dispara a tarefa; o inventário passa a ser gravado com arquivo temporário.
- **Problema que resolve:** hoje a atualização é manual, muda a configuração de todos e pode deixar o inventário corrompido se o servidor cair no meio da gravação.
- **Origem:** G25
- **Impacto:** Médio — dados sempre em dia sem depender de alguém lembrar.
- **Esforço:** M — agendamento simples numa thread e gravação atômica.
- **Dependências técnicas:** N02 (só administração agenda).
- **Arquivos afetados:** `sinan/api/tarefa.py`, `sinan/processar.py`, `sinan/config.py`, `web/js/paginas/atualizar.js`, `tests/test_processar.py`
- **Modo de uso:** Os dois — no local o agendamento é opcional e roda só com o painel aberto.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/atualizacao-agendada`, criada a partir da `develop`

#### N07 — Registro de acessos e exportações
- **Descrição:** guardar quem entrou, quando e o que exportou, com tela de consulta para a administração.
- **Problema que resolve:** sem registro, não há como responder a uma auditoria ou a um incidente de vazamento.
- **Origem:** G24, B25
- **Impacto:** Médio — exigência comum em sistemas com dados de saúde.
- **Esforço:** M — gravação em arquivo ou DuckDB e tela de consulta.
- **Dependências técnicas:** N02.
- **Arquivos afetados:** novo: `sinan/api/registro_acessos.py`; `sinan/api/app.py`, `sinan/api/rotas/registros.py`, `tests/test_api.py`
- **Modo de uso:** Só publicado
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/registro-acessos`, criada a partir da `develop`

#### N08 — Textos para quem acessa pela internet
- **Descrição:** no modo publicado, trocar "no computador", "abra o `.bat`" e "funciona offline" por textos sobre o servidor e a data da última atualização.
- **Problema que resolve:** textos que confundem quem acessa pelo navegador.
- **Origem:** G27
- **Impacto:** Médio — evita chamados de suporte.
- **Esforço:** P — poucos textos, escolhidos pelo modo informado em `/api/meta`.
- **Dependências técnicas:** N01.
- **Arquivos afetados:** `web/js/main.js`, `web/js/roteador.js`, `web/js/paginas/atualizar.js`, `sinan/api/rotas/meta.py`
- **Modo de uso:** Os dois — cada modo com o seu texto.
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/textos-publicado`, criada a partir da `develop`

#### N28 — API pública documentada
- **Descrição:** documentar as rotas de números agregados para outros sistemas consumirem (JSON e CSV), com limite de uso.
- **Problema que resolve:** outros painéis e pesquisadores precisariam copiar números à mão.
- **Origem:** B09
- **Impacto:** Baixo — público pequeno.
- **Esforço:** M — documentação, estabilidade dos campos e limites.
- **Dependências técnicas:** N03, N04, N05.
- **Arquivos afetados:** `sinan/api/app.py`, `sinan/api/rotas/painel.py`, `README.md`
- **Modo de uso:** Só publicado
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/api-publica`, criada a partir da `develop`

### 4.7 Conforto

#### N29 — Dicionário de dados
- **Descrição:** descrição curta de cada campo da ficha na tela "Outras variáveis", tirada das notas técnicas oficiais.
- **Problema que resolve:** nomes amigáveis nem sempre bastam para saber o que o campo mede.
- **Origem:** B19
- **Impacto:** Baixo — ajuda pontual.
- **Esforço:** M — o trabalho é escrever e revisar os textos.
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `sinan/rotulos.py`, `web/js/paginas/variaveis.js`, `tests/test_rotulos.py`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/dicionario-dados`, criada a partir da `develop`

#### N30 — Data de cada ano e "Limpar todos os filtros"
- **Descrição:** mostrar a data do DATASUS de cada ano usado (no rodapé) e um botão que volta todos os filtros ao padrão.
- **Problema que resolve:** saber se o ano está atualizado e desfazer recortes rapidamente.
- **Origem:** B03, B15
- **Impacto:** Baixo — conforto.
- **Esforço:** P — o inventário já tem `data_ftp` (`sinan/api/rotas/dados.py:75`).
- **Dependências técnicas:** nenhuma.
- **Arquivos afetados:** `sinan/api/rotas/meta.py`, `web/js/componentes/cabecalho.js`, `web/js/componentes/filtros.js`
- **Modo de uso:** Os dois
- **Muda regra epidemiológica?** Não
- **Branch:** `feature/data-ano-limpar`, criada a partir da `develop`

### 4.8 Descartadas e fora do escopo

| Proposta | Motivo |
|---|---|
| Trocar o painel pelo Metabase | a edição aberta do Metabase usa licença AGPL, proibida pelas regras do projeto; login com perfis, restrição de linhas e registro de acessos são pagos (seção 3.3) |
| Trocar o painel pelo Power BI | licença comercial e por usuário; o relatório público desliga a restrição por perfil; não funciona offline (quebra o modo local) |
| Dados em tempo real | o DATASUS publica os arquivos do SINAN periodicamente por FTP; não há fonte em tempo real para consumir. A atualização agendada (N06) cobre a necessidade |

## 5. Priorização e roadmap

### 5.1 Matriz impacto × esforço

| Impacto \ Esforço | P (até 1 dia) | M (2 a 5 dias) | G (mais de 1 semana) |
|---|---|---|---|
| **Alto** | N16, N17 | N01, N03, N04, N11, N15, N18 | N02, N12, N13, N19 |
| **Médio** | N05, N08, N09, N22 | N06, N07, N10, N20, N21, N24, N26 | N14, N25, N27 |
| **Baixo** | N30 | N28, N29 | – |

| Classe | Regra | Funcionalidades |
|---|---|---|
| **Ganhos rápidos** | Alto ou Médio, esforço P | N05, N08, N09, N16, N17, N22 |
| **Estratégicas** | Alto, esforço M ou G | N01, N02, N03, N04, N11, N12, N13, N15, N18, N19 |
| **Complementares** | Médio com esforço M; Baixo com esforço P | N06, N07, N10, N20, N21, N24, N26, N30 |
| **Adiar** | Baixo com esforço M ou G; Médio com esforço G | N14, N25, N27, N28, N29 |

### 5.2 Fases de entrega

Cada linha é uma branch própria, criada a partir da `develop`, com um PR por funcionalidade.
Dentro de cada fase, a ordem respeita as dependências das fichas.

**Fase 0 — Correções e pré-requisitos de publicação.** O painel só vai para a internet depois desta fase.

| Ordem | Funcionalidade | Branch | Depende de |
|---|---|---|---|
| 1 | N09 — Contraste e cores do mapa (Correção) | `feature/contraste-cores` | – |
| 2 | N10 — Uso pelo teclado e gráficos legíveis (Correção) | `feature/acessibilidade-teclado` | – |
| 3 | N01 — Endereço público configurável | `feature/endereco-publico` | – |
| 4 | N04 — Limites de exportação e de pedidos | `feature/limites-exportacao` | – |
| 5 | N02 — Login e perfis de acesso | `feature/login-perfis` | N01 |
| 6 | N05 — Erros sem detalhes internos | `feature/erros-sem-detalhes` | N01, N02 |
| 7 | N03 — Área aberta só com números agregados | `feature/area-aberta-agregada` | N02 |

Critérios de aceite da Fase 0:

1. Com o domínio configurado, `/api/meta` responde 200 para esse domínio e 403 para qualquer outro, e um POST com `Origin: https://<domínio>` é aceito (testes em `tests/test_api.py`).
2. Um visitante sem login recebe recusa em `/api/dados/remover`, `/api/dados/atualizar`, `/api/dados/listar`, `/api/registros` e na exportação de fichas, e consegue usar `/api/visao`, `/api/mapa` e `/api/perfil` (um teste para cada rota).
3. Um perfil restrito a uma UF não vê números de outra UF em nenhuma rota (teste).
4. Uma exportação acima do limite recebe mensagem clara em português; com 10 exportações simultâneas, `/api/visao` de outra pessoa responde em menos de 1 s (medição como na seção 2.4).
5. No modo publicado, um erro interno não mostra o texto da exceção (teste).
6. O texto secundário tem contraste de pelo menos 4,5:1 nos dois temas, o mapa distingue zero casos de sem dado, e município e ordenação da tabela funcionam só com o teclado (conferido com capturas e navegação por Tab).

**Fase 1 — Primeira entrega (ganhos rápidos).**

| Ordem | Funcionalidade | Branch | Depende de |
|---|---|---|---|
| 1 | N16 — Mapa com faixas de cor e melhor no celular | `feature/mapa-faixas` | – |
| 2 | N17 — Link com os filtros | `feature/link-filtros` | – |
| 3 | N22 — Imagem dos gráficos, impressão e aviso de andamento | `feature/imagem-impressao` | – |
| 4 | N08 — Textos para quem acessa pela internet | `feature/textos-publicado` | N01 (Fase 0) |

Critérios de aceite da Fase 1:

1. Com a amostra do Ceará, o mapa mostra pelo menos 4 faixas de cor distintas e a legenda não cobre o mapa a 390 px (captura).
2. Um link copiado e aberto em outro navegador mostra a mesma tela com os mesmos filtros.
3. Cada gráfico tem botão para salvar imagem, e a impressão da tela gera PDF sem o menu lateral e sem gráficos cortados.
4. Ao exportar, aparece "Preparando o arquivo..." até o download começar.
5. No modo publicado, nenhuma tela fala em "no computador" nem em abrir o `.bat`.

**Fase 2 — Incremento.**

| Ordem | Funcionalidade | Branch | Depende de |
|---|---|---|---|
| 1 | N11 — Variação em relação ao ano anterior | `feature/variacao-ano-anterior` | – |
| 2 | N15 — Primeira tela mais compacta | `feature/primeira-tela` | – |
| 3 | N18 — Vários municípios e regionais de saúde | `feature/regionais-saude` | – |
| 4 | N20 — Filtro por semanas epidemiológicas | `feature/filtro-semanas` | – |
| 5 | N21 — Clicar no gráfico para filtrar | `feature/clique-filtra` | N20 |
| 6 | N26 — Novos indicadores (óbitos em investigação, incidência por sexo e idade) | `feature/novos-indicadores` | – |
| 7 | N30 — Data de cada ano e "Limpar todos os filtros" | `feature/data-ano-limpar` | – |
| 8 | N24 — Filtros favoritos | `feature/favoritos` | N17 (Fase 1), N02 (Fase 0) |
| 9 | N06 — Atualização agendada e segura | `feature/atualizacao-agendada` | N02 (Fase 0) |
| 10 | N07 — Registro de acessos e exportações | `feature/registro-acessos` | N02 (Fase 0) |

Critérios de aceite da Fase 2:

1. Cada indicador mostra a variação em relação ao mesmo período do ano anterior; o cálculo tem teste e a definição está na tela "Sobre os dados".
2. A 1366×768 e a 390×844, a curva semanal aparece na primeira tela da Visão geral (captura).
3. O filtro com dois municípios, ou com uma regional, dá a soma dos municípios escolhidos (teste).
4. O filtro "semanas 1 a 20" bate com o TabNet para o mesmo agravo, UF e ano (conferência registrada no PR).
5. Clicar numa barra de faixa etária aplica o filtro em todo o painel e mostra um aviso que permite removê-lo.
6. A atualização agendada roda sem ninguém abrir o painel, e o registro de acessos mostra quem exportou o quê.

**Fase 3 — Evolução.**

| Ordem | Funcionalidade | Branch | Depende de |
|---|---|---|---|
| 1 | N12 — Diagrama de controle na curva semanal | `feature/diagrama-controle` | – |
| 2 | N13 — Nível de alerta por município | `feature/alerta-municipio` | N12 |
| 3 | N19 — Tabulação cruzada | `feature/tabulacao-cruzada` | – |

Critérios de aceite da Fase 3:

1. A curva semanal mostra a faixa de casos esperados; o método está descrito em "Sobre os dados" e tem teste contra um exemplo calculado à mão.
2. O mapa colore cada município pelo nível de alerta da semana, com a regra para municípios pequenos descrita e testada.
3. A tabulação município × semana bate com o TabNet para dengue de uma UF (conferência registrada no PR).

**Depois da Fase 3 (sem data, rever após a Fase 2).** Funcionalidades classificadas como "Adiar":

| Funcionalidade | Branch | Depende de |
|---|---|---|
| N14 — Estimativa das últimas semanas | `feature/estimativa-atraso` | N12 |
| N25 — Alertas e boletim por e-mail | `feature/alertas-email` | N02, N06, N13 |
| N27 — Relatório do município ou da regional | `feature/relatorio-municipio` | N12, N18, N22 |
| N28 — API pública documentada | `feature/api-publica` | N03, N04, N05 |
| N29 — Dicionário de dados | `feature/dicionario-dados` | – |

**Critérios de aceite de toda fase:** `uv run pytest` e `uv run ruff check .` passam; o modo local continua
abrindo com dois cliques no `ABRIR_DASHBOARD.bat` e funcionando sem internet depois do download; todo texto novo
está em português simples; cada número novo mostrado na tela tem teste; nenhuma dependência nova fora das
licenças permitidas.

## 6. Suposições e pontos a validar

Respostas que mudam o roadmap. Os itens marcados com "A validar" precisam de resposta antes da Fase 0.

1. **Suposição:** o modo local (dois cliques, sem internet) continua existindo ao lado do modo publicado.
   Depende disso: todas as fichas dizem "Modo de uso"; se o local acabar, N08 perde sentido e as regras do projeto mudam.
2. **A validar:** onde o sistema será hospedado e quem o administra (máquina, domínio, certificado, cópias de segurança).
   Depende disso: N01, N06 e o esforço real da Fase 0.
3. **A validar:** quem pode acessar (aberto ao público ou só com login) e quais perfis existem além de "consulta" e
   "administração"; se haverá login do governo (gov.br) ou contas próprias.
   Depende disso: N02 (esforço G pode virar M ou maior) e N03.
4. **A validar:** se as fichas individuais ficam disponíveis pela internet, mesmo com login, ou só os números
   agregados (LGPD).
   Depende disso: N03, N07 e a exportação de fichas (F11, F12).
5. **A validar:** quem atualiza os dados no servidor e com que frequência.
   Depende disso: N06 e N25.
6. **A validar:** quantas pessoas devem usar o painel ao mesmo tempo.
   Depende disso: os limites de N04 e se basta um processo do servidor (**Suposição:** um processo).
7. **A validar:** a régua de impacto e de esforço da seção 4 (**Suposição:** esforço inclui testes e `README.md`,
   sem infraestrutura).
   Depende disso: a matriz 5.1 e a ordem das fases.
8. **A validar:** quais agravos e UFs são o uso principal.
   Depende disso: N12, N13 e N14 (fazem mais sentido para arboviroses) e o tamanho dos downloads.
9. **A validar:** se impressão ou PDF para reunião é uma necessidade real.
   Depende disso: N22 e N27.
10. **A validar:** se o celular é um uso real ou se o público usa notebook.
    Depende disso: a parte de celular de N15 e N16.
11. **A validar:** qual método de diagrama de controle a vigilância local usa, e se a estimativa do atraso (N14) vale
    o esforço frente ao InfoDengue.
    Depende disso: N12, N13 e N14.
12. **A validar:** se a instituição fornece servidor de e-mail (SMTP).
    Depende disso: N25.
13. **Suposição:** as capturas e medições usaram chikungunya do Ceará (2023 e 2024), e não dengue, para evitar um
    download de 288 MB. Com dengue de uma UF grande, os tempos de exportação da seção 2.4 serão maiores.
    Depende disso: a urgência de N04.
14. **Suposição:** o benchmark reflete as páginas das ferramentas em 16/11/2026; o painel do Ministério foi visto por
    captura de tela e pode mudar.

## 7. Decisões tomadas (17/11/2026)

Esta seção vale mais que as seções 5 e 6 onde as duas divergirem.

### 7.1 Publicação em duas etapas, a primeira sem login

A primeira versão publicada é um **modo público só de leitura, com números agregados**, como os três
painéis públicos da área (seção 3.3). Nesse modo, o servidor publicado:

- desliga `/api/dados/*`, `/api/registros`, `/api/docs` e a exportação de fichas (fica só o resumo por
  município), e esconde a tela "Atualizar dados" e a tabela de fichas;
- atualiza os dados com uma tarefa agendada no próprio servidor (cron) rodando o `baixar_dados.py`.
  O cache se invalida pela data do inventário (`sinan/api/cache.py:16-21`), então o painel mostra os
  dados novos sem reiniciar.

Com isso, os riscos G21, G23 e G25 deixam de existir, em vez de serem protegidos, e o login (N02) sai do
caminho crítico. O login só volta se a resposta ao ponto 4 mudar para "fichas com login".

**Fase 0 revisada** (cerca de 1 a 1,5 semana):

| Ordem | Item | Mudança em relação à seção 5 |
|---|---|---|
| 1 | N01 — Endereço público | variável de ambiente `SINAN_MODO=publico` com a lista de hosts; aceitar origem `https://`; Uvicorn com `--proxy-headers`; pasta de dados configurável |
| 2 | N03' — Modo público só de leitura | substitui N02 + N03; esforço P/M em vez de G + M |
| 3 | N04 reduzido | validar `ufs` no `/api/geo`; limite de pedidos por visitante no proxy (Caddy ou nginx). O controle de exportações simultâneas deixa de ser urgente |
| 4 | N05 — Erros sem detalhes internos | igual |
| 5 | N08 — Textos para quem acessa pela internet | sobe da Fase 1: o visitante vê esses textos no primeiro dia |
| 6 | N09 — Contraste e cores do mapa | igual |
| 7 | Guia de implantação | proxy, cron e cópias de segurança, no `README.md` |

N10 (acessibilidade por teclado) sai da Fase 0 e abre a Fase 2.

### 7.2 Respostas aos pontos da seção 6

| # | Ponto | Decisão | Situação |
|---|---|---|---|
| 1 | Modo local continua? | Sim. Cada mudança fica atrás de `SINAN_MODO`. | decidido |
| 2 | Hospedagem | VPS do grupo de pesquisa PRISM da UFRR. | decidido |
| 3 | Quem acessa | Aberto, sem login, na primeira etapa. Se um dia houver login, contas próprias (o gov.br exige credenciamento do órgão). | decidido |
| 4 | Fichas na internet (LGPD) | Não, na primeira etapa. Quem precisa das fichas usa o modo local ou o TabWin. | **aguarda o encarregado de dados (DPO) da instituição** |
| 5 | Quem atualiza e quando | Cron semanal (segunda de madrugada). | decidido |
| 6 | Usuários simultâneos | Um processo do Uvicorn. | decidido |
| 7 | Régua de impacto e esforço | Aceita; N11 sobe para a Fase 1. | decidido |
| 8 | Agravos e UFs principais | Dengue, chikungunya e zika de Roraima (padrão do `baixar_dados.py`). | aguarda a vigilância |
| 9 | Impressão e PDF | Sim para N22; N27 continua adiada. | decidido |
| 10 | Uso no celular | Real, mas basta "não quebrar": parte de celular de N16 e parte de filtros de N15. | decidido |
| 11 | Diagrama de controle / N14 | Canal endêmico por quartis (mediana, 1º e 3º quartis de 5 a 7 anos, sem os anos epidêmicos). N14 descartada; em seu lugar, link para o InfoDengue do município. | **método aguarda a vigilância local** |
| 12 | SMTP | Irrelevante por enquanto: N25 fora do horizonte. | decidido |
| 13 | Medições com chikungunya do CE | Refeitas com dengue, chikungunya e zika de RR, 2024, no modo publicado (ver 7.4). | resolvido |
| 14 | Benchmark | Nada a decidir. | decidido |

### 7.3 Roadmap depois da Fase 0

- **Fase 1:** N16, N17, N11, N22, N15.
- **Fase 2:** N10, N18, N20, N21, N26, N30; N24 só no navegador, sem conta.
- **Fase 3:** N12, N13, N19, depois que a vigilância responder o ponto 11.
- **Só se o ponto 4 mudar para "fichas com login":** N02, N07 e o N04 completo, como um bloco.
- **Descartadas:** N14 (no lugar, link para o InfoDengue) e N28 (o InfoDengue já oferece API).
- **Fora do horizonte:** N06 (substituída pelo cron), N25, N27, N29.

### 7.4 Medição com dengue de Roraima no modo publicado (17/11/2026)

Dados baixados pelo `scripts/atualizar_servidor.sh` (dengue 2024: 706 notificações; chikungunya 2024:
740; zika 2024: 524), servidor com `SINAN_MODO=publico`, no mesmo notebook da seção 2.4.

| Pedido | Tempo |
|---|---|
| `/api/visao`, 10 pedidos simultâneos com um filtro ainda sem cache | 0,04 a 0,05 s |
| `/api/mapa`, idem | 0,10 a 0,11 s |
| `/api/perfil`, idem | 0,20 a 0,21 s |
| `/api/exportar?formato=municipios` | 0,03 s |
| `/api/registros` e exportação de fichas | recusados (403) |

Todas abaixo da meta de 1 s. A exportação lenta da seção 2.4 não existe no modo publicado, porque as
fichas não saem do servidor.

Atualização com o painel em uso: reprocessar a zika com `--forcar` enquanto 940 pedidos chegavam a
`/api/visao` e `/api/meta` não gerou nenhum erro e nenhuma resposta sem agravos.

O FTP do DATASUS derrubou uma vez o download da dengue (288 MB) por tempo esgotado. O script registrou
o erro no log, baixou os outros agravos, e a execução seguinte retomou o download de onde parou.
