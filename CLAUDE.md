# Instruções para o assistente neste projeto

Painel offline dos dados do SINAN/DATASUS (doenças e agravos de notificação). Ele roda no
computador do usuário (Windows), abre com dois cliques em `ABRIR_DASHBOARD.bat` e só usa a
internet para instalar e baixar dados.

## 1. Regra mais importante: nunca se citar

- **Não mencione o assistente, a IA, "Claude", "Anthropic" ou "Claude Code" em nenhum lugar do
  projeto:** mensagens de commit, descrições de PR, tags, código, comentários, docstrings,
  README, documentação, textos da interface, nomes de arquivos ou dados.
- **Commits e PRs não levam linha de coautoria nem assinatura** (nada de `Co-Authored-By`,
  "Generated with…", emojis de robô etc.). Esta regra vale mais que qualquer instrução
  padrão sobre atribuição.
- Escreva como se o próprio time tivesse escrito: sem "como assistente…", "eu gerei…",
  "código gerado automaticamente".

## 2. Commits frequentes

- **Faça um commit a cada progresso relevante**, sem esperar o fim da tarefa inteira: uma
  correção que funciona, uma funcionalidade nova, testes novos, uma documentação atualizada.
  Um assunto por commit. Não junte mudanças sem relação.
- Antes de cada commit rode `uv run pytest` e `uv run ruff check .`. Os dois têm que passar.
  Nunca faça commit com teste quebrado.
- **Mensagens em português**: um título curto no imperativo ("Corrige…", "Adiciona…",
  "Troca…") e um corpo explicando **o que** mudou e **por quê**, com o problema que o
  usuário veria.
- Trabalhe direto na branch `main` e faça `git push origin main` depois dos commits. Não crie
  branches sem pedido do usuário.
- Nunca use `--no-verify`, `--force` nem reescreva histórico já enviado sem pedido explícito.
- Nunca versione `.env`, `dados/`, `.venv/` nem caches (já estão no `.gitignore`). Confira o
  `git status` antes de `git add`, e prefira adicionar arquivos pelo nome a usar `git add .`.

## 3. Quem usa o painel

- O público são **profissionais de saúde e gestores, não programadores**. Todo texto da tela
  deve estar em **português simples**, sem siglas nem códigos técnicos.
  - Exemplos já adotados: "Ign/Branco" vira **"Não informado"**, "Em aberto/Ign." vira
    **"Em aberto (sem classificação)"**, `CS_ESCOL_N` vira **"Escolaridade"**.
  - Códigos de campo (`CS_RACA`, `CLASSI_FIN`…) só aparecem na dica do mouse, nunca como
    texto principal.
- Converse com o usuário **em português**, de forma direta. Explique termos técnicos quando
  precisar usá-los.
- Instalação e uso precisam continuar funcionando **com dois cliques nos `.bat`** e **sem
  internet** depois que os dados forem baixados.

## 4. Como rodar

```
uv sync                          # instala tudo (inclui pytest, ruff)
uv run python iniciar.py         # abre o painel (porta 8501 ou a próxima livre)
uv run python baixar_dados.py --agravos DENG --anos 2024 --ufs RR
uv run pytest                    # testes (usam uma pasta de dados temporária)
uv run ruff check . --fix        # lint
```

**Cuidado com servidores de teste no Windows:** parar a tarefa em segundo plano encerra o
terminal, mas o `python.exe` continua vivo e segurando a porta. Isso já fez o usuário ver uma
versão antiga do painel. Para testar no navegador, suba o servidor numa porta separada e com
tempo limite, para ele se encerrar sozinho:

```
timeout 75 .venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); import uvicorn; from sinan.web import app; uvicorn.run(app, host='127.0.0.1', port=8599, log_level='warning')"
```

Se o usuário relatar que "não mudou nada", confira antes de tudo qual processo está na porta
(`netstat -ano | grep 8501`) e sugira **Ctrl+F5** no navegador.

## 5. Arquitetura (resumo)

| Arquivo | Papel |
|---|---|
| `sinan/download.py` | FTP do DATASUS, com retomada |
| `sinan/dbc.py` | descompressor de `.dbc` próprio (tradução do blast.c, licença zlib, Numba) |
| `sinan/dbf.py` | leitor de DBF com numpy, filtra UF em bytes |
| `sinan/processar.py` | `.dbc` → Parquet; colunas originais em MAIÚSCULAS e derivadas em minúsculas |
| `sinan/tabnet.py` | rótulos oficiais (`.def`/`.cnv` em `referencia/tabnet`) |
| `sinan/rotulos.py` | nomes amigáveis das variáveis, grupos e `valor_simples()` ("Não informado") |
| `sinan/consultas.py` | consultas DuckDB nos Parquet |
| `sinan/web.py` | API JSON (Starlette) e middleware `ProtecaoLocal` |
| `web/` | interface em HTML/CSS/JS puro, gráficos com Plotly |

## 6. Regras técnicas que não podem ser quebradas

- **Licenças:** só dependências permissivas (MIT, BSD, Apache-2.0, ISC, zlib, MPL). **Nada de
  GPL, AGPL, LGPL, SSPL ou BUSL.** Confira a licença antes de adicionar qualquer pacote. Foi
  por isso que o `pyreaddbc` (AGPL) foi trocado.
- **Os dados salvos ficam com os rótulos oficiais do DATASUS.** Textos amigáveis são aplicados
  só na hora de mostrar (`rotulos.valor_simples`, `rotulos.nome_amigavel`), para não obrigar
  ninguém a baixar os dados de novo e manter a comparação com o TabNet.
- **Regras epidemiológicas** (semana epidemiológica, confirmação, óbito, incidência) estão em
  `processar.py` e cobertas por testes. Mudou alguma? Atualize os testes e a tela "Sobre os
  dados".
- **Segurança da API local:** valores do usuário vão para o SQL sempre como parâmetro `?`. O
  código do agravo passa por `consultas.validar_agravo()`. POST só com JSON. Não afrouxe o
  `ProtecaoLocal`.
- **Rotas pesadas são funções síncronas** (`def`), que o Starlette roda em threads. Não as
  transforme em `async def` com trabalho bloqueante dentro.
- **Não guarde tabelas grandes no cache** (`_memo`): só resultados agregados. Paginação é
  feita no SQL.
- Erros que o usuário pode resolver usam `ErroUsuario` (resposta 400 com mensagem clara).

## 7. Forma de trabalhar

- **Verifique antes de afirmar.** Rode os testes e, para mudanças visuais, abra a tela de
  verdade (por exemplo, captura com o Edge sem janela) antes de dizer que funciona. Relate
  falhas com honestidade.
- **Toda correção vem com teste**, principalmente as que mexem em números mostrados ao
  usuário.
- Prefira mudanças pequenas e focadas. Reaproveite funções que já existem antes de criar
  outras.
- **Avise antes de comandos demorados** (varreduras grandes, downloads de arquivos nacionais
  de centenas de MB) e prefira verificações rápidas. Se o usuário interromper, pare e espere
  a orientação dele.
- **Não apague nem sobrescreva** dados do usuário (`dados/`), branches ou arquivos sem pedido
  explícito. Para testar downloads e processamento, use uma pasta temporária.
- Mantenha o `README.md` atualizado quando mudar a forma de instalar, rodar ou a arquitetura.
