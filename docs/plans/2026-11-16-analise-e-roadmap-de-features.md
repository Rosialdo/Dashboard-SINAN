# Análise do painel e roadmap de novas funcionalidades — Plano de trabalho

> **Como executar:** uma tarefa por vez, na ordem, marcando as caixas (`- [ ]`). Cada tarefa
> termina com uma seção pronta no relatório e um commit. Nenhuma tarefa altera código do painel.

**Objetivo:** produzir um relatório com o estado atual do painel, um diagnóstico por boas
práticas de dashboard, um benchmark com 5 referências e uma lista priorizada de novas
funcionalidades com roadmap em fases.

**Abordagem:** um único documento de saída, preenchido seção a seção. Toda afirmação sobre o
painel cita `arquivo:linha` do repositório; o que não puder ser provado no código entra como
"Suposição" ou "A validar". O diagnóstico visual usa capturas reais da tela, não leitura de CSS.

**Stack analisada:** Python (FastAPI, DuckDB, Parquet, Numba), interface em módulos JS nativos
e CSS sem build, testes com pytest, lint com ruff.

**Especificação:** o pedido original (5 etapas: levantamento, diagnóstico, benchmark, lista de
features, priorização). Não há documento de especificação separado.

**Saída:** `docs/analise/2026-11-analise-e-roadmap.md` (capturas em `docs/analise/capturas/`).

## Restrições globais

- **Não implementar nada.** Só são criados arquivos em `docs/analise/`. Nenhum arquivo de
  `sinan/`, `web/`, `tests/` ou da raiz é alterado.
- **Basear tudo no código real.** Cada funcionalidade listada cita `arquivo:linha`. Sem
  evidência no código, não entra como "existente".
- **Sinalizar suposições.** Toda suposição recebe o marcador `**Suposição:**` e toda dúvida
  para o usuário recebe `**A validar:**`, e ambas são repetidas na seção final do relatório.
- **Dois modos de uso.** O painel será **disponibilizado pela internet** (decisão do usuário),
  para várias pessoas ao mesmo tempo. Por isso segurança, controle de acesso, uso simultâneo e
  proteção de dados pessoais (LGPD) são critérios centrais da análise, e não "Não se aplica".
  **Suposição:** o modo local (dois cliques nos `.bat`, sem internet depois de baixar os
  dados) continua existindo ao lado do modo publicado; nenhuma proposta pode quebrá-lo.
- Toda proposta de feature respeita as demais regras do `CLAUDE.md`: texto de tela em
  **português simples**; só licenças permissivas (nada de GPL/AGPL/LGPL/SSPL/BUSL); dados
  salvos mantêm os rótulos oficiais do DATASUS; interface sem CDN.
- **Branches.** Este trabalho de análise é feito numa branch criada a partir da `develop`:
  `git switch -c analise/roadmap-features develop`, antes da Tarefa 1. Nada é commitado
  direto na `develop` nem na `main`. No roadmap, **cada feature tem a sua própria branch
  criada a partir da `develop`** (`feature/<nome-curto>`). `push` e PR só a pedido do usuário.
- Relatório em português. Não citar ferramentas de automação nem autoria no texto ou nos commits.
- Commits: mensagem em português, título no imperativo, sem linha de coautoria. Antes de cada
  commit: `uv run pytest` e `uv run ruff check .` passando.
- **Não usar `dados/` do usuário** para as capturas: baixar uma amostra pequena numa pasta
  temporária (ver Tarefa 2).

## Foco de revisão

Riscos que nenhuma tarefa isolada garante; cada um tem uma verificação na tarefa indicada.

1. **Funcionalidade presumida** — listar algo que o código não faz (ex.: "exporta PDF").
   Verificação na Tarefa 1, passo 5 (toda linha do inventário tem `arquivo:linha` que existe).
2. **Feature que quebra um dos dois modos de uso** — proposta que só funciona com internet
   (quebra o modo local) ou que só faz sentido com um usuário (quebra o modo publicado).
   Verificação na Tarefa 5, passo 3 (linha "Modo de uso" de cada ficha).
3. **Publicar na internet o que foi feito para uso local** — o servidor foi escrito para um
   usuário na própria máquina: qualquer visitante poderia baixar fichas individuais, disparar
   downloads ou apagar dados. Verificação na Tarefa 3, passo 4 (tabela de riscos de publicação,
   uma linha por rota) e na Tarefa 6, passo 2 (itens bloqueantes entram na Fase 0).
4. **Diagnóstico visual sem olhar a tela** — avaliar contraste, hierarquia e responsividade só
   pelo CSS. Verificação na Tarefa 2, passo 4 (cada tela tem captura em 3 variações).
5. **Benchmark de memória** — atribuir a uma ferramenta uma função que ela não tem.
   Verificação na Tarefa 4, passo 3 (cada linha tem link da documentação oficial consultada).

## Estrutura de arquivos

| Arquivo | Papel |
|---|---|
| `docs/analise/2026-11-analise-e-roadmap.md` | relatório único, seções 1 a 6 |
| `docs/analise/capturas/<tela>-<variação>.png` | capturas usadas no diagnóstico |

Seções fixas do relatório (os títulos exatos são usados nas verificações):
`## 1. Estado atual`, `## 2. Diagnóstico`, `## 3. Benchmark`, `## 4. Novas funcionalidades`,
`## 5. Priorização e roadmap`, `## 6. Suposições e pontos a validar`.

---

### Tarefa 1: Levantamento do estado atual

**Arquivos:**
- Criar: `docs/analise/2026-11-analise-e-roadmap.md` (com os 6 títulos de seção; preencher a 1)
- Ler: `README.md`, `pyproject.toml`, `iniciar.py`, `baixar_dados.py`, `*.bat`, `sinan/**`,
  `web/index.html`, `web/js/**`, `web/css/main.css`, `web/css/base/tema.css`, `tests/**`

**Produz:** na seção 1, três tabelas com estas colunas exatas, usadas pelas tarefas seguintes:
- **Inventário:** `ID (F01…) | Funcionalidade | Onde aparece (tela) | Interface (arquivo:linha) | Servidor (arquivo:linha) | Coberta por teste?`
- **Rotas:** `Método | Caminho | Arquivo | O que devolve | Usa cache? | Paginada?`
- **Dados:** `Fonte | Como chega | Como é atualizada | Arquivo responsável`

- [ ] **Passo 1: Stack e estrutura.** Registrar dependências e licenças a partir de
  `pyproject.toml`, e a árvore de pastas com o papel de cada uma (partir da tabela do
  `CLAUDE.md`, seção 5, conferindo cada linha contra o disco).

- [ ] **Passo 2: Tabela de rotas.** Uma linha para cada rota dos 5 arquivos de
  `sinan/api/rotas/` (`painel.py`: `/visao`, `/mapa`, `/perfil`; `dados.py`: `""`, `/listar`,
  `/atualizar`, `/status`, `/remover`; `meta.py`: `/meta`, `/geo`; `registros.py`: `/registros`,
  `/exportar`; `variaveis.py`: `/variaveis`, `/variavel`). Conferir os prefixos em
  `sinan/api/app.py`. Para "Usa cache?" procurar `memo` (`sinan/api/cache.py`).

- [ ] **Passo 3: Inventário de funcionalidades.** Percorrer as 7 telas de `web/js/paginas/`
  (`visao`, `mapa`, `perfil`, `variaveis`, `dados`, `atualizar`, `sobre`) e os 9 componentes de
  `web/js/componentes/`. Para cada coisa que o usuário consegue ver ou fazer, uma linha no
  inventário. Incluir obrigatoriamente, com evidência ou com "não existe":
  filtros disponíveis (`web/js/componentes/filtros.js`, `sinan/api/filtros.py`), indicadores
  mostrados (`kpis.js`, `servicos.indicadores`), tipos de gráfico (`graficos.js`, `barras.js`),
  mapa, tabela paginada, exportação (`/exportar`), alertas (`alertas.js`), tema claro/escuro
  (`tema.css`), preferências salvas (`guardar` em `nucleo/estado.js`), estados de
  carregamento/vazio/erro (`blocos.js`, `nucleo/api.js`), link compartilhável (`roteador.js`,
  `nucleo/navegacao.js`).

- [ ] **Passo 4: Dados, atualização e perfis.** Preencher a tabela de dados (FTP do DATASUS em
  `sinan/download.py`; conversão em `sinan/pipeline.py` e `processar.py`; geografia em
  `/geo`; rótulos em `referencia/tabnet`). Registrar como a atualização é disparada (manual
  pela tela "Atualizar", `ATUALIZAR_DADOS.bat`, acompanhamento por `/status` em
  `sinan/api/tarefa.py`) e se existe atualização automática. Registrar os perfis de usuário
  que o código distingue; se não distingue nenhum, escrever isso e descrever o público a
  partir do `CLAUDE.md`, seção 3, e do que `sinan/api/seguranca.py` protege.
  Registrar também **o que hoje pressupõe uso local**: em que endereço o servidor escuta
  (`iniciar.py`, `sinan/api/app.py`), o que o `ProtecaoLocal` aceita e recusa, se existe
  login, onde ficam os dados (`sinan/config.py`) e o que é estado único do processo
  (`sinan/api/tarefa.py`, `sinan/api/cache.py`).

- [ ] **Passo 5: Verificar as evidências.** Rodar:

```bash
grep -oE '`[a-zA-Z_/.]+\.(py|js|css|html|bat):[0-9]+`' docs/analise/2026-11-analise-e-roadmap.md \
  | tr -d '`' | sort -u | while IFS=: read -r f n; do
    [ -f "$f" ] && [ "$(wc -l < "$f")" -ge "$n" ] || echo "EVIDÊNCIA INVÁLIDA: $f:$n"; done
```

Esperado: nenhuma linha de saída. E `grep -c '^| F[0-9]' docs/analise/2026-11-analise-e-roadmap.md`
devolve 15 ou mais.

- [ ] **Passo 6: Commit**

```bash
uv run pytest && uv run ruff check .
git add docs/analise/2026-11-analise-e-roadmap.md
git commit -m "Adiciona levantamento do estado atual do painel"
```

### Tarefa 2: Capturas das telas

**Arquivos:**
- Criar: `docs/analise/capturas/<tela>-<variação>.png`

**Consome:** lista das 7 telas da Tarefa 1.
**Produz:** 21 capturas nomeadas `<tela>-claro.png`, `<tela>-escuro.png`, `<tela>-celular.png`
(`<tela>` = identificador da tela em `PAGINAS`, `web/js/nucleo/estado.js`).

- [ ] **Passo 1: Amostra de dados em pasta temporária.** Baixar a menor amostra documentada
  (`uv run python baixar_dados.py --agravos DENG --anos 2024 --ufs RR`) apontando a pasta de
  dados para um diretório temporário. Ver em `sinan/config.py` como a pasta é configurada.
  **Avisar o usuário antes** (download pela internet). Se não houver internet, usar a pasta
  temporária dos testes (`tests/conftest.py`) e anotar a limitação na seção 6.

- [ ] **Passo 2: Subir o servidor com tempo limite**, na porta 8599, com o comando da seção 4
  do `CLAUDE.md` (ajustando o caminho do Python para o sistema em uso).

- [ ] **Passo 3: Capturar** cada tela com um navegador sem janela (Edge ou Chromium,
  `--headless --screenshot`), em 1366×768 claro, 1366×768 escuro e 390×844. Ver em
  `web/js/roteador.js` o formato do endereço de cada tela e em `web/css/base/tema.css` como o
  tema escuro é ativado.

- [ ] **Passo 4: Verificar.** `ls docs/analise/capturas/*.png | wc -l` devolve 21, e nenhuma
  captura está em branco (abrir cada uma). Tela que não renderizou vira achado do diagnóstico,
  não é descartada.

- [ ] **Passo 5: Commit**

```bash
git add docs/analise/capturas
git commit -m "Adiciona capturas das telas para o diagnóstico"
```

### Tarefa 3: Diagnóstico por boas práticas

**Arquivos:**
- Modificar: `docs/analise/2026-11-analise-e-roadmap.md` (seção 2)

**Consome:** inventário (IDs `F..`) e rotas da Tarefa 1; capturas da Tarefa 2.
**Produz:** tabela `ID (G01…) | Critério | Nota | Evidência | Lacuna observada`, em que cada
linha `G..` é uma lacuna que a Tarefa 5 pode transformar em feature.

Escala de nota: **Atende**, **Atende em parte**, **Não atende**, **Não se aplica**.

- [ ] **Passo 1: Avaliar os 9 critérios**, um subtítulo para cada, na ordem do pedido:

| # | Critério | Onde olhar | Pergunta que decide a nota |
|---|---|---|---|
| 1 | Hierarquia visual e regra dos 5 segundos | capturas de `visao`; `kpis.js`, `web/css/componentes/kpis.css` | Em 5 segundos dá para dizer quantos casos, a tendência e onde está o problema? |
| 2 | Gráfico certo para cada dado | `graficos.js`, `barras.js`, `paginas/perfil.js`, `paginas/mapa.js` | Série temporal em linha/coluna, categoria em barras ordenadas, mapa com taxa e não só contagem? |
| 3 | Filtros, detalhamento, comparação e contexto | `filtros.js`, `sinan/api/filtros.py`, `servicos.py`, `consultas.py` | Há comparação com período anterior, variação percentual, clique no gráfico/mapa que filtra, limite ou meta de referência? |
| 4 | Desempenho e estados | `sinan/api/cache.py`, `registros.py`, `consultas.py` (`conexao`), `blocos.js`, `nucleo/api.js` | Toda tela tem estado de carregando, vazio e erro? Medir o tempo de cada rota do painel com a amostra (`curl -w '%{time_total}'`), uma vez sozinha e uma vez com 10 pedidos simultâneos (`xargs -P 10`). O cache tem limite de tamanho? |
| 5 | Acessibilidade | `tema.css`, `web/index.html`, capturas | Contraste do texto ≥ 4,5:1 nos dois temas (calcular com os valores de `tema.css`)? Informação só por cor? Tudo alcançável por Tab, com foco visível e `aria-label`? |
| 6 | Responsividade | capturas `-celular`, regras `@media` em `web/css/` | Alguma tela tem rolagem horizontal, texto cortado ou tabela ilegível a 390 px? |
| 7 | Exportação, compartilhamento e alertas | `/exportar`, `nucleo/api.js` (`baixar`), `roteador.js`, `alertas.js` | Exporta só CSV de registros ou também o gráfico/tabela agregada? O endereço guarda os filtros? Há impressão/PDF? |
| 8 | Personalização | `guardar` em `nucleo/estado.js`, `tema.css` | O que fica salvo entre sessões? Há filtros favoritos ou tela inicial configurável? |
| 9 | Segurança e controle de acesso | `sinan/api/seguranca.py`, `app.py`, `rotas/dados.py`, `rotas/registros.py`, `tests/test_api.py` | Publicado na internet: quem não fez login consegue ver o quê? Quem pode baixar, atualizar e apagar dados? As fichas individuais (`/registros`, `/exportar`) expõem campos que identificam pessoas? O `ProtecaoLocal` continua funcionando atrás de um domínio público? |

- [ ] **Passo 2: Evidência em cada linha.** Toda nota cita `arquivo:linha` ou uma captura
  (`capturas/visao-celular.png`). Medições (tempo, contraste) entram com o número medido.

- [ ] **Passo 3: Registrar as lacunas** como `G01…`, uma por problema, escritas do ponto de
  vista de quem usa ("o gestor não consegue ver se os casos subiram em relação ao ano anterior").

- [ ] **Passo 4: Riscos de publicação na internet.** Dentro do critério 9, uma tabela com uma
  linha para cada uma das 14 rotas: `Rota | O que um visitante anônimo consegue fazer | Risco
  (Bloqueante / Alto / Médio / Baixo) | Evidência`. **Bloqueante** = não pode ir ao ar assim
  (ex.: apagar dados, disparar download, baixar fichas individuais sem login). Avaliar ainda,
  com evidência no código, e registrar cada falta como lacuna `G..`:
  login e perfis (ao menos "consulta" e "administração"); HTTPS e execução atrás de proxy;
  limite de pedidos por visitante; tamanho máximo de exportação; duas atualizações disparadas
  ao mesmo tempo (`tarefa.py`); leitura dos Parquet enquanto uma atualização grava;
  registro de quem acessou e exportou; campos pessoais nas fichas (LGPD); preferências hoje
  guardadas só no navegador (`guardar`). Como o sistema será publicado, tempo real,
  notificações e acesso por perfil **não** recebem "Não se aplica": recebem "Não atende" com
  a lacuna descrita.

- [ ] **Passo 5: Verificar.**
  `sed -n '/^## 2\./,/^## 3\./p' docs/analise/2026-11-analise-e-roadmap.md | grep -c '^### '`
  devolve 9; `grep -c '^| G[0-9]' docs/analise/2026-11-analise-e-roadmap.md`
  é ≥ 9; repetir o comando de evidências da Tarefa 1, passo 5, sem saída.

- [ ] **Passo 6: Commit**

```bash
git add docs/analise/2026-11-analise-e-roadmap.md
git commit -m "Adiciona diagnóstico do painel por boas práticas de dashboard"
```

### Tarefa 4: Benchmark com referências

**Arquivos:**
- Modificar: `docs/analise/2026-11-analise-e-roadmap.md` (seção 3)

**Consome:** inventário `F..` da Tarefa 1.
**Produz:** tabela `ID (B01…) | Referência | Função relevante | O painel tem? (F.. ou "não") | Link da fonte | Modo de uso (local, publicado ou os dois)`

Referências (3 do domínio, 2 de uso geral):

| Referência | Por que entra |
|---|---|
| TabNet / TabWin (DATASUS) | é a ferramenta que o público já usa com os mesmos dados |
| InfoDengue (Fiocruz/FGV) | alerta por níveis, incidência por semana, tendência |
| Painel de Monitoramento das Arboviroses (Ministério da Saúde) | painel oficial de gestão, indicadores e mapas |
| Metabase | filtros ligados, detalhamento por clique, perguntas salvas |
| Power BI | filtro cruzado entre gráficos, marcadores, exportação, dicas ricas |

Lista de referências confirmada pelo usuário.

- [ ] **Passo 1: Consultar a documentação ou a tela pública de cada referência** (precisa de
  internet). Anotar de 4 a 8 funções por referência, só as que fazem sentido para vigilância
  epidemiológica: diagrama de controle/canal endêmico, comparação entre anos, taxa por
  100 mil habitantes, tabulação cruzada linha × coluna, série por semana epidemiológica,
  detalhamento UF → município, filtro cruzado, exportação de imagem/planilha/PDF, visões
  salvas, dicionário de dados, indicadores de qualidade do preenchimento. Para Metabase e
  Power BI, anotar também as funções de uso pela internet: login e perfis de acesso,
  restrição de dados por perfil (ex.: por UF ou município), link público ou compartilhado,
  envio agendado por e-mail, alertas por limite e registro de acessos. Para os três painéis
  públicos, anotar o que eles mostram sem login e em que nível de detalhe (agregado ou ficha).

- [ ] **Passo 2: Cruzar com o inventário.** Para cada função, preencher "O painel tem?" com o
  ID `F..` correspondente ou "não". Só as linhas "não" e "em parte" recebem ID `B..`.

- [ ] **Passo 3: Verificar.** Toda linha `B..` tem link; 5 referências aparecem;
  `grep -c '^| B[0-9]' docs/analise/2026-11-analise-e-roadmap.md` é ≥ 10. Sem internet:
  parar, registrar o bloqueio na seção 6 e avisar o usuário — não preencher de memória.

- [ ] **Passo 4: Commit**

```bash
git add docs/analise/2026-11-analise-e-roadmap.md
git commit -m "Adiciona benchmark do painel com ferramentas de referência"
```

### Tarefa 5: Lista de novas funcionalidades

**Arquivos:**
- Modificar: `docs/analise/2026-11-analise-e-roadmap.md` (seção 4)

**Consome:** lacunas `G..` (Tarefa 3) e `B..` (Tarefa 4).
**Produz:** uma ficha por feature, com ID `N01…`, usada pela Tarefa 6.

- [ ] **Passo 1: Agrupar as lacunas em features.** Várias lacunas com a mesma solução viram
  uma feature só. Lacuna que é defeito (ex.: contraste abaixo do mínimo) entra como correção,
  marcada "Correção", e não como feature.

- [ ] **Passo 2: Escrever a ficha de cada feature** neste formato exato:

```markdown
#### N01 — <nome curto em português simples>
- **Descrição:** <1 a 2 frases>
- **Problema que resolve:** <necessidade do profissional de saúde ou gestor>
- **Origem:** <G.. e/ou B..>
- **Impacto:** Alto | Médio | Baixo — <motivo em uma frase>
- **Esforço:** P (até 1 dia) | M (2 a 5 dias) | G (mais de 1 semana) — <motivo>
- **Dependências técnicas:** <dados, pacotes novos com licença, outras features N..>
- **Arquivos afetados:** <caminhos reais; "novo: web/js/paginas/x.js" para arquivos a criar>
- **Modo de uso:** Os dois | Só publicado na internet | Só local — <o que muda em cada modo>
- **Muda regra epidemiológica?** Sim (exige teste e ajuste na tela "Sobre os dados") | Não
- **Branch:** `feature/<nome-curto>`, criada a partir da `develop`
```

Régua de impacto: **Alto** = muda uma decisão de gestão ou elimina uma ida ao TabNet;
**Médio** = economiza tempo em tarefa recorrente; **Baixo** = conforto.

- [ ] **Passo 3: Conferir contra as restrições.** Feature que quebra o modo local (o painel
  deixa de abrir ou de funcionar sem internet) ou que exige pacote de licença não permissiva
  sai da lista e vai para uma subseção "Descartadas", com o motivo. Feature "Só publicado na
  internet" (login, perfis, alertas por e-mail) é válida desde que fique desligada no modo
  local, e a ficha diz como. Toda lacuna de risco "Bloqueante" da Tarefa 3, passo 4, vira
  uma feature marcada **"Pré-requisito de publicação"**. Feature que depende de dado que o painel não baixa hoje (ex.: população para
  taxa de incidência — conferir primeiro em `sinan/processar.py` e `servicos.py` se já existe)
  declara a fonte e o tamanho do download em "Dependências técnicas".

- [ ] **Passo 4: Verificar.** Toda `G..` e toda `B..` aparece em alguma ficha, nas descartadas
  ou em "Fora do escopo" com motivo:

```bash
f=docs/analise/2026-11-analise-e-roadmap.md
for id in $(grep -oE '^\| [GB][0-9]+' $f | tr -d '| '); do
  [ "$(grep -c "\b$id\b" $f)" -ge 2 ] || echo "SEM DESTINO: $id"; done
```

Esperado: nenhuma saída. Cada ficha tem as 10 linhas (`grep -c '^- \*\*Modo de uso:'` e
`grep -c '^- \*\*Branch:'` iguais a `grep -c '^#### N'`), e nenhuma branch se repete
(`grep '^- \*\*Branch:' $f | sort | uniq -d` sem saída).

- [ ] **Passo 5: Commit**

```bash
git add docs/analise/2026-11-analise-e-roadmap.md
git commit -m "Adiciona lista de novas funcionalidades propostas para o painel"
```

### Tarefa 6: Priorização, roadmap e pontos a validar

**Arquivos:**
- Modificar: `docs/analise/2026-11-analise-e-roadmap.md` (seções 5 e 6)

**Consome:** fichas `N..` da Tarefa 5.

- [ ] **Passo 1: Matriz impacto × esforço.** Tabela 3×3 (linhas Alto/Médio/Baixo, colunas
  P/M/G) com os IDs `N..` em cada célula, e a classificação:
  **Ganhos rápidos** (Alto ou Médio, P), **Estratégicas** (Alto, M ou G),
  **Complementares** (Médio, M; Baixo, P), **Adiar** (Baixo, M ou G; Médio, G).

- [ ] **Passo 2: Fases de entrega.**
  - **Fase 0 — Correções e pré-requisitos de publicação:** itens marcados "Correção" e
    "Pré-requisito de publicação" na Tarefa 5. O painel só vai para a internet depois desta fase.
  - **Fase 1 — Primeira entrega:** ganhos rápidos sem dependência de outra feature.
  - **Fase 2 — Incremento:** estratégicas de esforço M e as complementares que dependem da Fase 1.
  - **Fase 3 — Evolução:** estratégicas de esforço G.
  
  Dentro de cada fase, ordenar respeitando "Dependências técnicas". Nenhuma feature entra
  numa fase anterior à de uma dependência. Cada linha do roadmap traz a branch da feature
  (`feature/<nome-curto>`, a partir da `develop`), uma feature por branch.

- [ ] **Passo 3: Critérios de aceite por fase.** De 3 a 6 critérios por fase, cada um
  observável na tela ou num teste — por exemplo "na Visão geral, cada indicador mostra a
  variação em relação ao mesmo período do ano anterior" — mais os critérios fixos de toda
  fase: `uv run pytest` e `uv run ruff check .` passam; o modo local continua abrindo com dois
  cliques e funcionando sem internet; todo texto novo está em português simples; cada número
  novo mostrado tem teste. A Fase 0 tem ainda: um visitante sem login não consegue ver fichas
  individuais, exportar, atualizar nem apagar dados (cada item com teste em `tests/test_api.py`).

- [ ] **Passo 4: Seção 6.** Reunir todas as ocorrências de `**Suposição:**` e `**A validar:**`
  do relatório numa lista numerada, cada uma com a decisão que depende dela. Incluir no mínimo:
  o modo local continua existindo ao lado do publicado; onde o sistema será hospedado e quem
  o administra; quem pode acessar (aberto ao público ou só com login) e quais perfis existem;
  se as fichas individuais ficam disponíveis pela internet ou só os números agregados (LGPD);
  quem atualiza os dados no servidor e com que frequência; quantas pessoas devem usar ao
  mesmo tempo; régua de impacto e de esforço; quais agravos e UFs são o uso principal; se
  impressão/PDF para reunião é necessidade real; telas pequenas (celular) são um uso real.

- [ ] **Passo 5: Verificar.**

```bash
f=docs/analise/2026-11-analise-e-roadmap.md
for id in $(grep -oE '^#### N[0-9]+' $f | grep -oE 'N[0-9]+'); do
  sed -n '/^## 5\./,/^## 6\./p' $f | grep -q "\b$id\b" || echo "FORA DO ROADMAP: $id"; done
[ "$(grep -cE '\*\*(Suposição|A validar):\*\*' $f)" -ge 9 ] || echo "FALTAM SUPOSIÇÕES"
git diff --name-only develop...HEAD | grep -v '^docs/'
[ "$(git branch --show-current)" = "analise/roadmap-features" ] || echo "BRANCH ERRADA"
```

Esperado: nenhuma saída (a penúltima linha prova que a branch só mudou arquivos de `docs/`).

- [ ] **Passo 6: Commit e entrega**

```bash
uv run pytest && uv run ruff check .
git add docs/analise/2026-11-analise-e-roadmap.md
git commit -m "Adiciona priorização e roadmap das novas funcionalidades"
```

Apresentar ao usuário a matriz, as fases e a lista da seção 6, e pedir as respostas dos
pontos "A validar" antes de qualquer plano de implementação.

---

## Decisões do usuário (já confirmadas)

1. **Referências do benchmark:** TabNet/TabWin, InfoDengue, painel de arboviroses do
   Ministério da Saúde, Metabase e Power BI.
2. **O sistema será disponibilizado pela internet.** Segurança, controle de acesso, uso
   simultâneo e LGPD entram como critérios centrais (Tarefa 3, passo 4) e os itens
   bloqueantes formam a Fase 0 do roadmap.
3. **Internet durante a análise:** liberado baixar a amostra (Dengue, Roraima, 2024) em pasta
   temporária e consultar as fontes oficiais do benchmark.
4. **Branches:** cada feature é desenvolvida numa branch própria criada a partir da
   `develop`. A análise usa `analise/roadmap-features`.

## Suposições deste plano (validar antes de executar)

1. **O modo local continua existindo** (dois cliques, sem internet) ao lado do modo publicado.
   Se o painel passar a ser só pela internet, a restrição "não quebrar o modo local" cai e a
   seção 3 do `CLAUDE.md` precisa ser atualizada.
2. **A própria análise não é uma "feature"**, mas segue a mesma regra e fica em
   `analise/roadmap-features`, a partir da `develop`.
3. **`push` e PR só a pedido.** O `CLAUDE.md` ainda manda trabalhar direto na `main` com
   `push`; a decisão 4 acima vale mais, e o `CLAUDE.md` deveria ser atualizado para refletir isso.
4. **Um relatório único** em `docs/analise/`, e não um arquivo por etapa.
