# Dashboard SINAN

Painel para explorar os dados de **doenças e agravos de notificação (SINAN)** do Ministério da
Saúde/DATASUS: curva epidêmica por semana epidemiológica, mapa de incidência por município,
perfil dos casos (idade, sexo, raça/cor), evolução, letalidade e exportação para Excel.

**Funciona sem internet.** A internet só é necessária para instalar e para baixar ou atualizar
os dados. Depois disso, tudo fica salvo no computador.

---

## Como usar (Windows)

| Passo | O que fazer | Precisa de internet? |
|---|---|---|
| 1 | Dê dois cliques em **`INSTALAR.bat`** (só na primeira vez) | Sim |
| 2 | Dê dois cliques em **`ABRIR_DASHBOARD.bat`**. O painel abre no navegador | Não |
| 3 | No menu da esquerda, vá em **⬇️ Baixar dados**, escolha UF, doenças e anos e clique em *Baixar e processar* | Sim |
| 4 | Volte ao **📊 Painel** e use os filtros | Não |

Para fechar o dashboard, feche a janela preta que abriu junto.

> A configuração inicial é **Roraima**, com dengue, chikungunya e zika dos últimos anos. Pode mudar
> tudo na tela *Baixar dados*.

### Levar para outro computador sem internet

Instale e baixe os dados em um computador com internet. Depois copie a pasta `dados/` para a mesma
pasta do projeto no outro computador, que também precisa ter rodado o `INSTALAR.bat` uma vez.

### Atualizar os dados

Os dados dos anos recentes são **preliminares** e o DATASUS os atualiza com frequência. Na tela
*Baixar dados*, clique em **Consultar o que existe no DATASUS**: a tabela "Dados no computador"
mostra o que tem versão nova. Depois clique em *Baixar e processar*, que só baixa o que mudou.

Também dá para atualizar sem abrir o painel, com dois cliques em `ATUALIZAR_DADOS.bat`. Ele usa a
última configuração escolhida.

---

## O que tem no painel

- **Indicadores:** notificações, casos confirmados, incidência por 100 mil habitantes, óbitos,
  letalidade e hospitalizações.
- **📈 Evolução no tempo:** curva epidêmica por semana epidemiológica comparando os anos, mais os
  totais por ano e por mês.
- **🗺️ Mapa e municípios:** mapa de incidência ou de número de casos e ranking dos municípios.
- **👥 Perfil dos casos:** pirâmide etária, raça/cor, classificação final, evolução e critério de
  confirmação.
- **📄 Dados e exportação:** tabela dos registros e exportação para Excel ou CSV.
- **🔎 Outras variáveis** (seção "Avançado", no fim do menu): qualquer campo da ficha de
  notificação (sinais, sintomas, exames, escolaridade...), com os rótulos oficiais do TabNet.

**Filtros:** doença, anos, UF, municípios, residência ou local de notificação, confirmados,
prováveis ou todas as notificações, sexo e faixa etária.

Na tela **ℹ️ Sobre os dados** estão as definições de cada número (confirmado, óbito, letalidade,
incidência, semana epidemiológica) e os cuidados de interpretação.

---

## De onde vêm os dados

| Dado | Fonte |
|---|---|
| Notificações (microdados anonimizados) | FTP do DATASUS, `ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS` (pastas FINAIS e PRELIM) |
| Rótulos das variáveis | Arquivos `.def`/`.cnv` do tabulador TabNet do SINAN (pasta `referencia/tabnet`) |
| Municípios, população e mapa | IBGE: localidades, estimativas anuais (tabela 6579), Censo 2022 e malha municipal (pasta `referencia`) |

Os arquivos do DATASUS são **nacionais** (um por doença por ano). O programa baixa o arquivo, guarda
só as UFs escolhidas (por residência **ou** notificação) e apaga o original.

**Observações importantes**

- Os arquivos de **dengue** do DATASUS não incluem os casos descartados. Para dengue, "todas as
  notificações" equivale a casos prováveis.
- Na **Amazônia Legal**, a malária é notificada no SIVEP-Malária, não no SINAN.
- Para validar números, compare com o TabNet: <http://tabnet.datasus.gov.br>.

---

## Para desenvolvedores

```
iniciar.py           sobe o servidor local (FastAPI + Uvicorn) e abre o navegador
baixar_dados.py      download e tratamento pelo terminal
sinan/
  api/               servidor do painel (FastAPI)
    app.py           monta a aplicação: rotas, erros, arquivos da interface, segurança
    rotas/           um arquivo por tela: meta, painel, variaveis, registros, dados
    filtros.py       filtros da URL (dependência ctx: Filtros)
    servicos.py      cálculos usados por mais de uma rota
    tarefa.py        download em segundo plano · cache.py · seguranca.py · respostas.py
  consultas.py       consultas DuckDB direto nos Parquet
  download.py        FTP do DATASUS (com retomada de download)
  dbc.py             descompressor de .dbc (tradução do blast.c, licença zlib, acelerado com Numba)
  dbf.py             leitor rápido de DBF com filtro por UF (numpy)
  processar.py       .dbc -> Parquet + colunas derivadas
  tabnet.py          leitura dos rótulos oficiais (.def/.cnv)
  rotulos.py         nomes amigáveis das variáveis e "Não informado"
  agravos.py         catálogo das doenças e regras de confirmação
  pipeline.py        junta download + tratamento
web/                 interface: HTML, CSS e módulos JavaScript nativos (sem build), Plotly local
  js/main.js         ponto de entrada
  js/roteador.js     monta a tela atual
  js/nucleo/         estado, filtros, API, utilidades
  js/componentes/    filtros, indicadores, gráficos, cabeçalho, avisos...
  js/paginas/        uma tela por arquivo
  css/main.css       importa os estilos na ordem: base/ (cores do tema, estrutura), componentes/, paginas/
tests/               testes automáticos (pytest), com uma amostra real de .dbc em tests/fixtures
referencia/          municípios, população, mapa e rótulos (já vêm prontos)
scripts/gerar_referencias.py   regenera a pasta referencia/
scripts/atualizar_servidor.sh  atualização dos dados do painel publicado (roda no container)
scripts/painel.sh   gerencia o painel publicado (status, iniciar, atualizar-dados, implantar...)
Dockerfile, compose.yaml, deploy/caddy/   painel publicado com Docker (veja "Publicar com Docker")
dados/               criado ao baixar (não vai para o git)
```

- Python **3.12**. O `uv` instala a versão certa sozinho.
- Instalar tudo, inclusive as ferramentas de desenvolvimento: `uv sync`.
- Rodar: `uv run python iniciar.py`, ou
  `uv run python baixar_dados.py --agravos DENG CHIK --anos 2020-2025 --ufs RR`.
  Use `--listar` para ver os códigos das doenças.
- Testes e qualidade: `uv run pytest` e `uv run ruff check .`.
- Documentação interativa da API: com o painel aberto, acesse `/api/docs` (precisa de internet só
  para carregar o visual dessa página).
- **Nova rota na API:** crie a função em `sinan/api/rotas/<assunto>.py` com `@router.get(...)`. Para
  receber os filtros do painel, use o parâmetro `ctx: Filtros`. Um arquivo novo de rotas precisa
  entrar em `ROUTERS` (`sinan/api/rotas/__init__.py`).
- **Nova tela:** crie `web/js/paginas/<tela>.js` exportando `montar(raiz, pedido)` e registre-a em
  `PAGINAS` (`web/js/nucleo/estado.js`) e em `MONTADORES` (`web/js/roteador.js`). Se a tela tiver estilos próprios,
  crie `web/css/paginas/<tela>.css` e acrescente o `@import` em `web/css/main.css`.
- Cada Parquet tem **todas as colunas originais** da ficha (em maiúsculas, como texto) e as colunas
  derivadas em minúsculas (`data_notificacao`, `sem_epi`, `faixa_etaria`, `situacao`, `confirmado`,
  `obito`, ...). Dá para analisar direto com pandas ou DuckDB.
- **Segurança do servidor local:** ele só escuta em `127.0.0.1`, só aceita `Host` localhost, recusa
  pedidos com `Origin` de outro site e só aceita POST com JSON. Assim, uma página aberta no navegador
  não consegue disparar downloads nem apagar dados. No modo publicado, aceita também os domínios de
  `SINAN_HOSTS` e só pedidos de leitura (veja "Publicar com Docker").
- **Licenças:** só dependências permissivas (MIT, BSD, Apache, zlib). Por isso o leitor de `.dbc` é
  próprio, em vez do `pyreaddbc` (AGPL).
- Nunca versione o `.env` (já está no `.gitignore`).

## Publicar com Docker

O mesmo painel pode virar um site aberto, **só de leitura e só com números agregados**. Nesse modo não
existem as telas "Dados e exportação" e "Atualizar dados", nenhuma ficha individual sai do servidor (só o
resumo por município é exportado) e os dados são atualizados por uma tarefa agendada. O uso no computador
com os arquivos `.bat` não muda e não precisa de Docker.

No servidor (a VPS do grupo PRISM/UFRR) tudo roda com Docker Compose: o painel, o Caddy (que cuida do
HTTPS e é a única porta aberta) e a atualização dos dados. O script `scripts/painel.sh` faz todo o
gerenciamento.

**O que o servidor precisa**

- Docker com o Compose v2, ligado na inicialização (`sudo systemctl enable docker`), para o painel voltar
  sozinho depois de reiniciar a máquina; e o `git`;
- um domínio (ex.: `painel.prism.ufrr.br`) com o DNS apontando para o servidor **antes** de ligar o painel,
  senão o certificado HTTPS não é emitido;
- portas 80 e 443 abertas para a internet e saída liberada para `ftp.datasus.gov.br`;
- o usuário que roda o script no grupo `docker` (isso equivale a ser administrador do servidor: escolha bem
  quem entra nele).

**Instalar**

```
git clone https://github.com/Rosialdo/Dashboard-SINAN.git
cd Dashboard-SINAN
cp .env.exemplo .env          # e troque SINAN_HOSTS pelo domínio do painel
scripts/painel.sh iniciar
scripts/painel.sh atualizar-dados
```

A primeira atualização baixa os arquivos nacionais de dengue, chikungunya e zika dos últimos 6 anos
(centenas de MB por ano, só no caso da dengue) e pode levar horas. O painel fica no ar enquanto isso.

**Comandos do `scripts/painel.sh`**

| Comando | O que faz |
|---|---|
| `status` | mostra se o painel está no ar, o uso de CPU e memória, o tamanho dos dados e a data da última atualização |
| `iniciar` / `parar` / `reiniciar` | liga, desliga (os dados ficam guardados) e reinicia relendo o `.env` |
| `logs [painel\|proxy] [-f]` | últimas mensagens; `-f` continua acompanhando |
| `atualizar-dados [--forcar]` | baixa os dados agora; `--forcar` baixa tudo de novo. Duas atualizações nunca rodam ao mesmo tempo |
| `implantar` | baixa a versão nova do código (branch do `SINAN_RAMO`), troca o painel e, se ele não ficar saudável, volta para a versão anterior do painel. A volta não desfaz mudanças no `compose.yaml` nem no `deploy/caddy/Caddyfile`: essas se voltam à mão, com o `git` |
| `ajuda` | lista os comandos |

O script sai com código 0 quando deu tudo certo e com outro número quando algo falhou. Um monitoramento
pode rodar `scripts/painel.sh status` de tempos em tempos e avisar quando o código não for 0.

**Atualização semanal**, toda segunda às 3h (no relógio do servidor), com `crontab -e`:

```
0 3 * * 1 /caminho/do/Dashboard-SINAN/scripts/painel.sh atualizar-dados > /dev/null
```

O painel mostra os dados novos sem reiniciar. Os erros chegam pelo e-mail do cron, se o servidor tiver
um configurado; quando a atualização falha, o script manda junto as últimas linhas do registro. O registro completo, com a hora de Boa Vista, fica no volume de dados:

```
docker compose run --rm --no-deps --entrypoint tail atualizar -n 50 /dados/atualizacao.log
```

Os logs dos containers ficam limitados a 30 MB por serviço e não guardam o IP de quem consulta.

**Configuração (`.env`)**

| Variável | Exemplo | Para quê |
|---|---|---|
| `SINAN_HOSTS` | `painel.prism.ufrr.br` | domínio do painel: um só, sem `https://`, sem porta e sem aspas. Obrigatória |
| `SINAN_RAMO` | `main` | branch usada pelo `implantar`: `main` ou `develop` |

O `compose.yaml` já define o resto: `SINAN_MODO=publico` (liga o modo publicado) e `SINAN_DADOS=/dados`
(pasta dos dados, num volume do Docker). Fora do Docker, as mesmas três variáveis `SINAN_MODO`,
`SINAN_HOSTS` e `SINAN_DADOS` funcionam do mesmo jeito.

**Cópias de segurança.** Não copie a pasta de dados: ela se refaz pelo DATASUS, e restaurar só parte dela
pode deixar o painel vazio. Guarde o `.env` (é o único arquivo que só existe no servidor); o
`compose.yaml` e o `deploy/caddy/Caddyfile` vêm do git. Para restaurar: clone o projeto, coloque o `.env`
de volta, rode `scripts/painel.sh iniciar` e `scripts/painel.sh atualizar-dados --forcar`. Os
certificados HTTPS se refazem sozinhos, mas não apague o volume deles sem motivo: o Let's Encrypt limita
quantos certificados novos um domínio recebe por semana.

## Licença

MIT. Os dados são públicos, do Ministério da Saúde e do IBGE.
