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
app.py               dashboard (Streamlit)
iniciar.py           abre o dashboard no navegador
baixar_dados.py      download e tratamento pelo terminal
sinan/
  download.py        FTP do DATASUS (com retomada de download)
  dbf.py             leitor rápido de DBF com filtro por UF (numpy)
  processar.py       .dbc -> Parquet + colunas derivadas
  tabnet.py          leitura dos rótulos oficiais (.def/.cnv)
  agravos.py         catálogo das doenças e regras de confirmação
  consultas.py       consultas DuckDB usadas pelo painel
  pipeline.py        junta download + tratamento
referencia/          municípios, população, mapa e rótulos (já vêm prontos)
scripts/gerar_referencias.py   regenera a pasta referencia/
dados/               criado ao baixar (não vai para o git)
```

- Python **3.12**: é a versão mais nova em que o leitor de `.dbc` (`pyreaddbc`) tem instalador
  pronto para Windows. O `uv` cuida disso sozinho.
- Rodar pelo terminal: `uv run python iniciar.py`, ou
  `uv run python baixar_dados.py --agravos DENG CHIK --anos 2020-2025 --ufs RR`.
  Use `--listar` para ver os códigos das doenças.
- Cada Parquet tem **todas as colunas originais** da ficha (em maiúsculas, como texto) e as colunas
  derivadas em minúsculas (`data_notificacao`, `sem_epi`, `faixa_etaria`, `situacao`, `confirmado`,
  `obito`, ...). Dá para analisar direto com pandas ou DuckDB.

## Licença

MIT. Os dados são públicos, do Ministério da Saúde e do IBGE.
