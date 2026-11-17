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
- **🔎 Outras variáveis:** qualquer campo da ficha de notificação (sinais, sintomas, exames,
  escolaridade...), com os rótulos oficiais do TabNet.
- **📄 Dados e download:** tabela dos registros e exportação para Excel ou CSV.

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
scripts/atualizar_servidor.sh  atualização semanal do painel publicado (cron)
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
  `SINAN_HOSTS` e só pedidos de leitura (veja "Publicar no servidor").
- **Licenças:** só dependências permissivas (MIT, BSD, Apache, zlib). Por isso o leitor de `.dbc` é
  próprio, em vez do `pyreaddbc` (AGPL).
- Nunca versione o `.env` (já está no `.gitignore`).

## Publicar no servidor

O mesmo código roda como site aberto, **só de leitura e só com números agregados**, quando a variável
`SINAN_MODO=publico` está definida. Nesse modo não existem as telas "Dados e exportação" e "Atualizar
dados", nenhuma ficha individual sai do servidor (só o resumo por município é exportado) e os dados
são atualizados por uma tarefa agendada. Sem a variável, o painel continua o mesmo do computador.

| Variável | Exemplo | Para quê |
|---|---|---|
| `SINAN_MODO` | `publico` | liga o modo publicado |
| `SINAN_HOSTS` | `painel.prism.ufrr.br` | domínios aceitos, separados por vírgula, sem porta. Sem ela o servidor não sobe |
| `SINAN_DADOS` | `/srv/sinan-dados` | pasta dos dados (o padrão é `dados/` dentro do projeto) |

Exemplo para Linux com systemd e nginx. Use um usuário próprio (aqui `sinan`) para o serviço **e** para o cron.

**1. Instalar**

```
sudo -u sinan git clone https://github.com/Rosialdo/Dashboard-SINAN.git /srv/sinan
cd /srv/sinan && sudo -u sinan uv sync --frozen
```

**2. Variáveis** em `/etc/sinan.env`:

```
SINAN_MODO=publico
SINAN_HOSTS=painel.prism.ufrr.br
SINAN_DADOS=/srv/sinan-dados
```

**3. Serviço** em `/etc/systemd/system/sinan.service` (aponta direto para o `.venv`, sem `uv run`, para
não sincronizar dependências a cada início):

```
[Unit]
Description=Painel SINAN
After=network.target

[Service]
User=sinan
WorkingDirectory=/srv/sinan
EnvironmentFile=/etc/sinan.env
ExecStart=/srv/sinan/.venv/bin/uvicorn sinan.api:app --host 127.0.0.1 --port 8501 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`sudo systemctl enable --now sinan`. Se faltar `SINAN_HOSTS`, o motivo aparece em `journalctl -u sinan`.

**4. nginx com HTTPS** (certificado, por exemplo, com o certbot). O limite de pedidos vale só para a API:
a primeira abertura da página baixa cerca de 47 arquivos, e um limite no site todo bloquearia a própria página.

```
limit_req_zone $binary_remote_addr zone=sinan_api:10m rate=10r/s;

server {
    listen 443 ssl;
    server_name painel.prism.ufrr.br;
    # ssl_certificate e ssl_certificate_key: do certbot

    gzip on;
    gzip_types application/json application/javascript text/css image/svg+xml;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /api/ {
        limit_req zone=sinan_api burst=30 nodelay;
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**5. Atualização semanal** (`sudo -u sinan crontab -e`), toda segunda às 3h. O script calcula os
últimos 6 anos a cada execução (o ano novo entra sozinho em janeiro), não deixa duas execuções se
sobreporem e grava o resultado em `$SINAN_DADOS/atualizacao.log`. O painel mostra os dados novos sem
reiniciar.

```
0 3 * * 1 UV=/home/sinan/.local/bin/uv SINAN_DADOS=/srv/sinan-dados /srv/sinan/scripts/atualizar_servidor.sh
```

Para carregar os dados pela primeira vez, rode o mesmo comando à mão.

**6. Cópias de segurança.** Não copie a pasta de dados: ela se refaz pelo DATASUS, e restaurar só parte
dela pode deixar o painel vazio. Guarde `/etc/sinan.env`, `/etc/systemd/system/sinan.service` e a
configuração do nginx. Para restaurar os dados, rode o script com `--forcar` no fim.

## Licença

MIT. Os dados são públicos, do Ministério da Saúde e do IBGE.
