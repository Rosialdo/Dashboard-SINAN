# Pendências dos planos do projeto: levantamento e lista por prioridade

> **Para quem for executar:** use superpowers:executing-plans (ou subagent-driven-development) tarefa por
> tarefa. Os passos usam caixas (`- [ ]`) para acompanhar.

**Objetivo:** juntar num só lugar tudo o que os planos e relatórios deixaram em aberto, conferir no código o
que de fato falta e registrar uma lista única, ordenada por prioridade, na seção 7 do relatório de roadmap.

**Abordagem:** ler as fontes abaixo, conferir cada item com um `grep` ou teste no código, e gravar a lista
como seção 7.6 de `docs/analise/2026-11-analise-e-roadmap.md` (que vale mais que as seções 5 e 6). Os planos
já executados ganham uma linha "Situação: concluído" no topo.

**Fontes:**

| Arquivo | Situação encontrada em 23/11/2026 |
|---|---|
| `docs/plans/2026-11-16-analise-e-roadmap-de-features.md` | executado (commits 8dfb385…0b42333, PR #3) |
| `docs/plans/2026-11-17-fase-0-publicacao.md` | executado (PRs #5 a #13) |
| `docs/plans/2026-11-17-containerizacao.md` | código executado (PRs #14 a #17); implantação na VPS pendente |
| `docs/analise/2026-11-analise-e-roadmap.md` §6, §7.2, §7.3, §7.5 | Fases 1 a 3 sem nenhuma entrega; pontos "a validar" abertos |
| `docs/analise/2026-11-comparacao-painel-ses-rr.md` §6 e "Pontos em aberto" | nada entrou no roadmap oficial |

As caixas dos três planos estão todas desmarcadas, mesmo com o trabalho feito: por isso a conferência é
pelo código e pelo git, não pelas caixas.

## Restrições globais

- Texto em português simples; nenhuma menção a assistente ou IA em arquivo, commit ou PR (`CLAUDE.md` §1).
- Branch a partir da `develop`: `git switch -c docs/pendencias-priorizadas develop`.
- Antes do commit: `uv run pytest` e `uv run ruff check .` passam.
- Só documentação muda neste plano; nenhum código.

## Foco de revisão

1. Item dado como pendente que já existe no código (ex.: N17 parece faltar, mas `nucleo/filtros.js:29`
   monta parâmetros de URL; conferir se é o link compartilhável ou só a chamada à API).
2. Item da comparação SES-RR que contradiz uma decisão já tomada (a "supressão < 5" foi descartada em §7.5).
3. Dependência quebrada na ordem (N21 antes de N20; N13 antes de N12).
4. Decisão que só o grupo pode tomar apresentada como tarefa de código.

---

## Lista por prioridade (resultado do levantamento)

Critério: primeiro o que bloqueia o site ir ao ar; depois decisões de terceiros que travam fases inteiras;
depois a ordem de fases já decidida em §7.3; por último as ideias da comparação SES-RR ainda não decididas.

### P0 — Bloqueia a publicação

| # | Pendência | Origem | Quem resolve |
|---|---|---|---|
| 1 | Conferir a VPS: arquitetura (`uname -m`), Docker ≥ 24 e Compose ≥ 2.20, `systemctl enable docker`, DNS de `painel.prism.ufrr.br`, portas 80/443 e saída para o FTP 21, memória (painel 1 GB, atualização 2 GB, proxy 256 MB), fuso do cron | containerização, "Pontos a validar na VPS" | equipe com acesso à VPS |
| 2 | Aceite do grupo para programas GPL do sistema base das imagens (`bash`, `glibc`, `busybox`) e para o `shellcheck` | containerização, idem | grupo |
| 3 | Implantar: `cp .env.exemplo .env`, `scripts/painel.sh iniciar`, conferir os 4 critérios de aceite finais na VPS (HTTPS, `status`, atualização sem 500) | containerização, Tarefa 4 e "Critérios de aceite finais" | equipe |
| 4 | Levar a `develop` para a `main` (54 commits à frente) | `CLAUDE.md` §2 | usuário |

### P1 — Decisões externas que travam fases

| # | Pendência | Trava | Origem |
|---|---|---|---|
| 5 | Confirmar com o CEP da UFRR o enquadramento na Resolução CNS 510/2016 | divulgação do estudo | roadmap §7.5 |
| 6 | Vigilância local: método do canal endêmico (quartis de 5 a 7 anos?) | N12, N13 (Fase 3) | roadmap §7.2, ponto 11 |
| 7 | Vigilância local: agravos e UFs principais | `.env` da atualização, N12/N13 | roadmap §7.2, ponto 8 |
| 8 | Se o servidor estiver em nome de empresa de algum autor, consultar sobre o Marco Civil | guarda de logs | roadmap §7.5 |

### P2 — Fase 1 (ordem de §7.3)

| # | Item | Branch sugerida | Depende de |
|---|---|---|---|
| 9 | N16 — Mapa com faixas de cor e melhor no celular | `feature/mapa-faixas` | – |
| 10 | N17 — Link com os filtros | `feature/link-filtros` | – |
| 11 | N11 — Variação em relação ao ano anterior | `feature/variacao-ano-anterior` | – |
| 12 | N22 — Imagem dos gráficos, impressão e aviso "Preparando o arquivo..." | `feature/imagem-impressao` | – |
| 13 | N15 — Primeira tela mais compacta (parte de filtros no celular) | `feature/primeira-tela` | – |
| 14 | Link para o InfoDengue do município (substitui a N14 descartada) | `feature/link-infodengue` | – |

### P3 — Fase 2

| # | Item | Depende de |
|---|---|---|
| 15 | N10 — Teclado e leitor de tela | – |
| 16 | N18 — Vários municípios e regionais de saúde | – |
| 17 | N20 — Filtro por semanas epidemiológicas | – |
| 18 | N21 — Clicar no gráfico para filtrar | N20 |
| 19 | N26 — Óbitos em investigação, incidência por sexo e idade (respeitar `CAMPOS_SENSIVEIS` no recorte por município) | – |
| 20 | N30 — Data de cada ano e "Limpar todos os filtros" | – |
| 21 | N24 — Filtros favoritos, só no navegador | N17 |

### P4 — Fase 3 (só depois do item 6)

| # | Item | Depende de |
|---|---|---|
| 22 | N12 — Diagrama de controle na curva semanal | item 6 |
| 23 | N13 — Nível de alerta por município | N12 |
| 24 | N19 — Tabulação cruzada | – |

### P5 — Ideias da comparação SES-RR, ainda sem decisão

Precisam de decisão do grupo antes de entrar numa fase.

| # | Ideia | Observação |
|---|---|---|
| 25 | Faixa de semanas incompletas na curva | esforço baixo; hoje só há o texto em `visao.js:16` |
| 26 | Qualidade e casos em aberto há mais de 60 dias por unidade notificadora | recorte por unidade aumenta o risco de identificação |
| 27 | Recortes indígena, migrante e de fronteira | taxa indígena depende de denominador do IBGE/SESAI |
| 28 | Nome das unidades via CNES | nova fonte de dados |
| 29 | Supressão de contagens < 5 | **conflita** com §7.5, que descartou o corte "menos de 5" |
| 30 | Medir a defasagem do DATASUS frente à base estadual e conversar com a SES | "Pontos em aberto" |
| 31 | Analisar subpainéis da SES (dengue, oropouche, tuberculose, IST/AIDS) e conferir se oropouche está no FTP | "Pontos em aberto" |

Fora do escopo ou descartado (não entram na lista): N02, N04 completo, N07 (§7.5); N14, N28 (descartadas);
N06, N25, N27, N29 (fora do horizonte).

---

### Tarefa 1: Conferir no código cada item de P2 a P4

**Arquivos:** só leitura.

- [x] **Passo 1:** para cada item, rodar a busca abaixo e anotar "existe" ou "falta".

| Item | Comando | "Falta" quando |
|---|---|---|
| N16 | `grep -n "faixa\|quantil" web/js/paginas/mapa.js` | nenhuma linha |
| N17 | `grep -rn "location.hash\|replaceState" web/js/nucleo` | o hash só guarda a página, sem filtros |
| N11 | `grep -rn "ano_anterior\|variacao" sinan web/js` | nenhuma linha |
| N22 | `grep -rln "@media print\|toDataURL\|Preparando o arquivo" web` | nenhuma linha |
| N20 | `grep -rn "semana" sinan/api/filtros.py` | sem parâmetro de semana |
| N30 | `grep -rn "Limpar todos" web/js` | nenhuma linha |
| N18 | `grep -rn "regional" sinan/api/filtros.py web/js/componentes/filtros.js` | nenhuma linha |

Resultado em 23/11/2026: todos "falta". A N17 também: os filtros ficam só no `localStorage` e o hash guarda apenas a tela.

- [x] **Passo 2:** item que "existe" sai da lista e ganha nota com o commit (`git log -S "<termo>" --oneline`).

### Tarefa 2: Registrar a lista e fechar os planos executados

**Arquivos:**
- Modificar: `docs/analise/2026-11-analise-e-roadmap.md` (nova seção 7.6 no fim)
- Modificar: `docs/plans/2026-11-16-analise-e-roadmap-de-features.md`, `docs/plans/2026-11-17-fase-0-publicacao.md`,
  `docs/plans/2026-11-17-containerizacao.md` (uma linha logo abaixo do título)

- [x] **Passo 1:** criar a branch `docs/pendencias-priorizadas` a partir da `develop`.
- [x] **Passo 2:** acrescentar "### 7.6 Pendências por prioridade (23/11/2026)" com as tabelas P0 a P5 acima,
  já ajustadas pela Tarefa 1.
- [x] **Passo 3:** nos dois primeiros planos, abaixo do título: `**Situação:** concluído (PRs #3; #5 a #13).`
  No da containerização: `**Situação:** código concluído (PRs #14 a #17); implantação na VPS pendente (ver roadmap §7.6, P0).`
- [x] **Passo 4:** `uv run pytest` e `uv run ruff check .` passam.
- [x] **Passo 5:** commit.

```bash
git add docs/analise/2026-11-analise-e-roadmap.md docs/plans/2026-11-16-analise-e-roadmap-de-features.md \
  docs/plans/2026-11-17-fase-0-publicacao.md docs/plans/2026-11-17-containerizacao.md \
  docs/plans/2026-11-23-pendencias-priorizadas.md
git commit -m "Registra as pendências dos planos por prioridade" \
  -m "Os planos já executados estavam com todas as caixas desmarcadas e as pendências espalhadas em cinco documentos. A seção 7.6 do roadmap junta tudo numa lista única, da publicação na VPS às ideias da comparação com a SES-RR."
```

### Tarefa 3: Revisão

- [ ] **Passo 1:** chamar o `reviewer` com este plano e a seção 7.6, pedindo atenção ao "Foco de revisão".
