# Containerização do painel publicado: plano de implementação

**Situação:** código concluído (PRs #14 a #17); implantação na VPS pendente (ver `docs/analise/2026-11-analise-e-roadmap.md`, §7.6, P0).

> **Como executar:** uma tarefa por vez, marcando as caixas (`- [ ]`). Cada tarefa tem a sua branch,
> criada da `develop`, e termina com os testes passando, um commit e o PR para a `develop`.

**Objetivo:** publicar o painel na VPS do grupo PRISM/UFRR com Docker Compose: o painel, um proxy com
HTTPS automático e a atualização semanal dos dados, controlados por um único script `scripts/painel.sh`.

**Abordagem:** uma imagem (`sinan-painel:atual`) serve para dois serviços do compose: `painel` (Uvicorn,
sempre no ar, numa rede sem saída para a internet) e `atualizar` (roda o `baixar_dados.py` e termina). O
Caddy é a única porta aberta. O cron do próprio servidor chama `scripts/painel.sh atualizar-dados` toda
segunda às 3h. O código Python não muda (exceção prevista só na Tarefa 2, Passo 6, se o DuckDB ignorar o
limite de memória do container).

**Stack:** Python 3.12, FastAPI/Uvicorn, DuckDB, Parquet, `uv`/`uv.lock` (sem mudança); Docker Engine e
Compose v2; Caddy com o módulo de limite de pedidos; bash.

**Especificação:** o pedido de containerização de 17/11/2026, mais `docs/plans/2026-11-17-fase-0-publicacao.md`
(variáveis `SINAN_MODO`, `SINAN_HOSTS`, `SINAN_DADOS`) e `docs/analise/2026-11-analise-e-roadmap.md`, seção 7.

**Substitui** a tarefa de systemd, cron e guia de implantação da Fase 0 (no arquivo da Fase 0 ela é a
**Tarefa 7**, já juntada no PR #12). As Tarefas 1 a 6 da Fase 0 estão na `develop` e são pré-requisito.
O que essa tarefa deixou e muda aqui: a seção "Publicar no servidor" do `README.md` (systemd + nginx) é
trocada por "Publicar com Docker", e `scripts/atualizar_servidor.sh` passa a rodar dentro do container.

## Restrições globais

- O modo local não muda: `ABRIR_DASHBOARD.bat`, `INSTALAR.bat` e `ATUALIZAR_DADOS.bat` não são tocados e
  não dependem de Docker. `iniciar.py` e `baixar_dados.py` não mudam.
- Nenhuma dependência Python nova; `pyproject.toml` e `uv.lock` não mudam.
- Imagens e ferramentas só com licença permitida no `CLAUDE.md` (tabela abaixo). Nada de GPL, AGPL, LGPL,
  SSPL ou BUSL **como dependência do projeto**; veja o ponto de licenças em "Pontos a validar".
- No modo publicado nenhuma ficha individual sai do servidor: o container roda sempre com `SINAN_MODO=publico`.
- O painel não tem porta publicada no host. Só o proxy publica 80 e 443.
- **Nenhum IP de quem consulta é guardado:** o Caddy fica sem log de acesso, e o Uvicorn roda com
  `--no-access-log` (com `--proxy-headers` ele gravaria o IP real no `docker logs`).
- **Logs com tamanho limitado:** os três serviços usam
  `logging: {driver: json-file, options: {max-size: "10m", max-file: "3"}}` (o padrão do Docker não faz rotação).
- `scripts/painel.sh`: bash, `set -euo pipefail`. No host, só usa Docker com Compose v2, `git` (no `implantar`)
  e utilitários básicos do sistema (`sed`, `tr`); nada de `flock`, `curl` ou `jq`. Mensagens em português
  simples, saída ≠ 0 em falha, recusa rodar sem `.env` (exceto `ajuda`).
- Scripts `.sh` com fim de linha LF: `.gitattributes` ganha `*.sh text eol=lf`.
- Nenhum comando apaga o volume de dados (`docker compose down -v`, `docker volume rm`) nem o volume de
  certificados do Caddy.
- Antes de cada commit: `uv run pytest` e `uv run ruff check .`. Mensagem em português, título no imperativo,
  sem coautoria nem menção a IA.

## Imagens e ferramentas (licenças)

| Item | Onde | Licença |
|---|---|---|
| `python:3.12-slim-trixie` (tag fixada com a versão, ex. `3.12.N-slim-trixie`) | build e imagem final | Python: PSF-2.0. Sistema base Debian: pacotes com licenças variadas (veja "Pontos a validar") |
| `ghcr.io/astral-sh/uv:0.11.19` (mesma versão do `uv` usado no projeto) | só no estágio de build | MIT ou Apache-2.0 |
| `caddy:<2.x.y>-builder` e `caddy:<2.x.y>` (mesma tag nos dois; a última 2.x no dia) | imagem do proxy | Apache-2.0 (imagem base Alpine: veja "Pontos a validar") |
| `github.com/mholt/caddy-ratelimit`, fixado por hash de commit | compilado no Caddy | Apache-2.0 |
| `xcaddy` (já vem na imagem `-builder`) | só no build do proxy | Apache-2.0 |
| `tzdata`, só se não vier na imagem slim (Tarefa 1, Passo 4) | imagem final | domínio público |
| Docker Engine (Moby) e Docker Compose v2 | VPS | Apache-2.0 |
| `flock` (util-linux), já presente na imagem Debian | dentro do container de atualização | GPL-2.0, ferramenta do sistema base, não ligada ao código |
| `shellcheck` | só na máquina de quem desenvolve, para conferir os scripts; não vai para a imagem | GPL-3.0 (veja "Pontos a validar") |

O limite de pedidos **não existe no Caddy padrão**: é o módulo `caddy-ratelimit`, por isso o proxy tem um
`Dockerfile` próprio de dois estágios.

## Arquivos

| Arquivo | Papel |
|---|---|
| `Dockerfile` | imagem do painel: estágio `build` (uv) e estágio final (só `.venv` e código, usuário `sinan`) |
| `.dockerignore` | lista do que **entra** no contexto (`*` e exceções), para `.env`, `dados/` e o resto nunca entrarem |
| `.gitattributes` | ganha `*.sh text eol=lf` |
| `compose.yaml` | serviços `painel`, `atualizar` (perfil `ferramentas`) e `proxy`; volumes `dados`, `caddy_dados`, `caddy_config`; redes `interna` e `default` |
| `deploy/caddy/Dockerfile` | Caddy compilado com `caddy-ratelimit` |
| `deploy/caddy/Caddyfile` | domínio, HTTPS, compressão, cabeçalhos, limite em `/api/*` |
| `.env.exemplo` | modelo do `.env` (versionado); o `.env` já está no `.gitignore` |
| `scripts/atualizar_servidor.sh` | passa a rodar dentro do container (`python` direto, sem `UV`) |
| `scripts/painel.sh` | gerenciamento na VPS |
| `tests/test_implantacao.py` | confere `Dockerfile`, `compose.yaml` e `atualizar_servidor.sh` (os testes com Docker pulam se não houver Docker) |
| `tests/test_painel_sh.py` | confere o `painel.sh` com um `docker` e um `git` falsos (pulam sem bash ou no Windows) |
| `README.md` | seção "Publicar com Docker" no lugar de "Publicar no servidor" |

## Ordem e branches

| Ordem | Tarefa | Branch | Sai de |
|---|---|---|---|
| 1 | Imagem do painel | `feature/imagem-docker` | `develop` |
| 2 | Compose, proxy e atualização | `feature/compose-proxy` | `develop` com a Tarefa 1 juntada |
| 3 | Script de gerenciamento | `feature/script-painel` | `develop` com a Tarefa 2 juntada |
| 4 | README e aceite final | `feature/docs-docker` | `develop` com a Tarefa 3 juntada |

**As quatro são sequenciais:** cada uma usa nomes definidos na anterior (imagem, serviços, script). Ao fim
de cada uma: `push`, PR para a `develop` e esperar o merge autorizado pelo usuário antes de começar a próxima.

## Contrato entre as tarefas

| Nome | Valor | Definido em | Usado em |
|---|---|---|---|
| imagem do painel | `sinan-painel:atual`; `sinan-painel:anterior` guarda a versão anterior durante o `implantar` | Tarefa 2 (`image:` no compose) | Tarefa 3 |
| usuário no container | `sinan`, UID `10001` | Tarefa 1 | Tarefa 2 (dono do volume) |
| pasta do código | `WORKDIR /app` (o `uvicorn sinan.api:app`, o healthcheck e o entrypoint relativo dependem dela); `PATH` começa com `/app/.venv/bin` | Tarefa 1 | Tarefas 2 e 3 |
| pasta de dados | `/dados` (`SINAN_DADOS=/dados`), já criada na imagem com dono `sinan` | Tarefa 1 | Tarefas 2 e 3 |
| fuso | `TZ=America/Boa_Vista` na imagem (datas do log e do "Dados atualizados em") | Tarefa 1 | Tarefas 2 e 4 |
| porta interna | `8501` | Tarefa 1 (`CMD`) | Tarefa 2 (Caddy: `reverse_proxy painel:8501`) |
| saúde | `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/meta', timeout=5)"` (responde 200 mesmo com a pasta de dados vazia, conferido) | Tarefa 2 (`healthcheck`) | Tarefa 1 (conferência), Tarefa 3 (`status`) |
| serviços | `painel`, `atualizar`, `proxy` | Tarefa 2 | Tarefa 3 |
| variáveis do `.env` | `SINAN_HOSTS` (um domínio só, sem porta, obrigatório), `SINAN_RAMO` (`main` ou `develop`, padrão `main`) | Tarefa 2 | Tarefas 3 e 4 |
| trava da atualização | arquivo `/dados/.atualizando` com `flock -n`; ocupada → mensagem "Já existe uma atualização em andamento." e saída 1 | Tarefa 2 | Tarefa 3 |
| log da atualização | `/dados/atualizacao.log` (e também na saída do comando); linhas `== <data> início` e `== <data> fim (código N)` | Tarefa 2 | Tarefa 4 (README) |

## Atualização semanal: cron no host ou agendador no compose

| | (a) cron no host → `scripts/painel.sh atualizar-dados` | (b) serviço agendador no compose |
|---|---|---|
| Peças novas | nenhuma: uma linha no `crontab` | um container a mais, sempre ligado: `cron` instalado na imagem (pacote a mais, e o processo teria que rodar como root) ou um agendador como o Ofelia (MIT), que precisa do socket do Docker montado, o que dá a ele poder de root sobre a VPS |
| Memória | só durante a atualização | um processo parado o tempo todo |
| Trava contra execução dupla | `flock` no volume, dentro do container: vale para o cron e para quem roda à mão | a mesma, mas o agendador e o comando manual seriam dois caminhos diferentes |
| Hora | relógio do host | fuso do container |
| Saída | o cron e o `painel.sh` mostram a mesma saída; também fica em `/dados/atualizacao.log` | só no log do container agendador |

**Recomendação: (a).** É menor, não abre o socket do Docker para ninguém, e o comando do cron é o mesmo que
a equipe roda à mão. Em vez de `docker compose run --rm painel ...`, o cron usa o serviço `atualizar`
(mesma imagem e volume, perfil `ferramentas`, que não sobe com o `up`), porque ele precisa de internet
(FTP do DATASUS) e de mais memória que o painel, e o painel fica numa rede sem saída.

O ano é calculado a cada execução (`--anos $((ANO-5))-$ANO`), e os agravos e a UF vão explícitos na
linha de comando (`--agravos DENG CHIK ZIKA --ufs RR`), então o `configuracao.json` salvo não decide nada.
Argumentos extras vão no fim; o `argparse` fica com o último valor de cada opção, então
`atualizar --agravos ZIKA --anos 2024` troca os padrões (usado nas verificações).

**Atualização com o painel no ar (já conferido no código, não fica para a Tarefa 4):** os Parquet e o
inventário são gravados num arquivo temporário e trocados com `replace` (`sinan/processar.py:217-221`,
`:249-251`, `:300-332`); o DuckDB roda em memória (`sinan/consultas.py:40`), sem arquivo `.duckdb`
compartilhado entre os containers; e a medição da seção 7.4 do relatório já reprocessou a zika com 940
pedidos chegando, sem nenhum erro. O volume é o mesmo nos dois containers, então a troca é vista igual.
**Se o Aceite 3 falhar mesmo assim:** parar, investigar com a causa na mão (superpowers:systematic-debugging),
e corrigir em Python numa branch `correcao/<nome>` à parte, com teste, antes de seguir.

## Limite de pedidos

Dos cerca de 47 pedidos da primeira carga, só 2 ou 3 são `/api/*` (`/api/meta` e `/api/visao`; o mapa soma
`/api/mapa` e `/api/geo`): os outros são os 25 módulos JS, os 17 CSS, a página e o Plotly, que ficam fora do
limite. Com 100 pedidos de API a cada 10 s por IP, uma rede inteira atrás de um IP só (laboratório,
secretaria com NAT) aguenta dezenas de pessoas abrindo o painel ao mesmo tempo. O número é conferido no
navegador na Tarefa 2, Passo 8. O problema real é um proxy da UFRR na frente da VPS (veja "Pontos a validar").

## Foco de revisão

1. **Volume de dados criado como root:** o volume nomeado vazio herda dono e permissões de `/dados` da
   imagem só se a pasta existir na imagem com dono `sinan`. Senão, a primeira atualização falha com
   "Permission denied". Conferido na Tarefa 2, Passo 5.
2. **Numba sem pasta gravável:** `sinan/dbc.py` usa `@njit(cache=True)`, que grava cache ao lado do código;
   em `/app`, que é de root, o usuário `sinan` não grava. Com `NUMBA_CACHE_DIR=/tmp/numba` na imagem o
   cache vai para `/tmp`. Conferido na Tarefa 1, Passo 4, descompactando a amostra como `sinan`.
3. **Domínio pelo proxy:** o Caddy repassa o `Host` original (`painel.prism.ufrr.br`), que precisa estar em
   `SINAN_HOSTS`; o healthcheck usa `127.0.0.1:8501`, que o `ProtecaoLocal` já aceita. Um `Host` diferente
   dá 403 em tudo. Conferido na Tarefa 2, Passo 7 (`curl` pelo HTTPS → 200).
4. **`atualizar-dados` antes do primeiro `iniciar`:** sem a imagem local, o Compose tentaria baixar
   `sinan-painel:atual` do Docker Hub ("pull access denied"). O `atualizar` tem `pull_policy: never` e o
   `painel.sh` manda rodar o `iniciar` antes. Teste na Tarefa 3.
5. **`.env` errado:** sem `SINAN_HOSTS` o `docker compose config` já falha dizendo o nome da variável (teste
   na Tarefa 2); com porta ou com dois domínios, o painel não fica saudável e o `iniciar` sai com código ≠ 0
   e manda olhar os logs (Tarefa 3, Passo 6); `SINAN_RAMO` com aspas, espaço ou CRLF é limpo, e um valor
   estranho é recusado mostrando o que foi lido (teste na Tarefa 3).

---

### Tarefa 1: Imagem do painel

Branch: `feature/imagem-docker`

**Arquivos:**
- Criar: `Dockerfile`, `.dockerignore`, `tests/test_implantacao.py`

**Interfaces:**
- Produz: imagem com `WORKDIR /app`, código em `/app`, `.venv` em `/app/.venv`, usuário `sinan` (UID 10001),
  `/dados` com dono `sinan`,
  `ENV SINAN_DADOS=/dados NUMBA_CACHE_DIR=/tmp/numba PYTHONUNBUFFERED=1 TZ=America/Boa_Vista PATH=/app/.venv/bin:$PATH`,
  `EXPOSE 8501` e
  `CMD ["uvicorn", "sinan.api:app", "--host", "0.0.0.0", "--port", "8501", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log", "--no-server-header"]`
  (`*` porque o painel só é alcançável pela rede interna do compose, onde o único cliente é o proxy).

- [ ] **Passo 1: Testes que falham**, em `tests/test_implantacao.py` (só leitura de texto, rodam em qualquer máquina):
  - `test_imagem_final_sem_compilador_e_sem_root`: o trecho do `Dockerfile` depois do último `FROM` tem
    `USER sinan` e `WORKDIR /app`, e não contém `uv sync`, `gcc` nem `build-essential`.
  - `test_imagem_usa_lock_sem_dev`: o `Dockerfile` contém `uv sync --frozen --no-dev --no-install-project`.
  - `test_imagem_nao_guarda_ip`: o `CMD` contém `--no-access-log`.
  - `test_dockerignore_deixa_fora_segredos_e_dados`: a primeira linha útil do `.dockerignore` é `*`, e entre
    as exceções (`!…`) não há `.env`, `dados`, `.venv`, `.git`, `tests` nem `docs`.
- [ ] **Passo 2:** `uv run pytest tests/test_implantacao.py -v` → falham (arquivos não existem).
- [ ] **Passo 3: Implementar.**
  - Estágio `build` em `python:3.12.N-slim-trixie`: `COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /usr/local/bin/uv`;
    `ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/.venv`;
    `WORKDIR /app`; copia `pyproject.toml uv.lock .python-version` e roda
    `uv sync --frozen --no-dev --no-install-project` (o código não é instalado: vem de `/app`, que é a pasta
    atual). O `pyproject.toml` não tem `[build-system]` e o `.python-version` é `3.12`, que aceita qualquer
    3.12.x da imagem (conferido). Todas as dependências têm wheel pronta, então nenhum compilador é instalado.
  - Estágio final na **mesma tag** (o `.venv` aponta para `/usr/local/bin/python3.12`): cria o usuário,
    `mkdir /dados && chown sinan:sinan /dados`, `WORKDIR /app`, copia o `.venv` do build e, com dono root,
    só `sinan/ web/ referencia/ baixar_dados.py scripts/atualizar_servidor.sh` para `/app`.
  - `.dockerignore`: `*` e as exceções `!pyproject.toml !uv.lock !.python-version !sinan/ !web/ !referencia/
    !baixar_dados.py !scripts/atualizar_servidor.sh`, mais `**/__pycache__` no fim.
- [ ] **Passo 4: Conferir a imagem.**
  - `docker build -t sinan-painel:teste .` → termina sem erro.
  - `docker run --rm sinan-painel:teste id -u` → `10001`; `docker run --rm sinan-painel:teste pwd` → `/app`.
  - `docker run --rm sinan-painel:teste sh -c 'command -v gcc cc uv || echo sem-compilador'` → `sem-compilador`.
  - `docker run --rm sinan-painel:teste ls -A /app` → `.venv baixar_dados.py referencia scripts sinan web`.
  - Fuso: `docker run --rm sinan-painel:teste date +%z` → `-0400`. Se der `+0000`, a imagem slim não tem
    `tzdata`: instalar no estágio final com `apt-get install -y --no-install-recommends tzdata` e apagar
    `/var/lib/apt/lists/*` no mesmo `RUN`.
  - Numba como usuário sem privilégios:
    `docker run --rm -v "$PWD/tests/fixtures:/f:ro" sinan-painel:teste python -c "import os; from sinan.dbc import dbc_para_dbf; dbc_para_dbf('/f/ACBIBR06.dbc', '/tmp/a.dbf'); print(os.path.getsize('/tmp/a.dbf'))"`
    → imprime o mesmo número que o mesmo comando com `uv run python` e `tests/fixtures/ACBIBR06.dbc` no host.
  - Saúde com a pasta vazia: `docker run -d --name sinan-teste -e SINAN_MODO=publico -e SINAN_HOSTS=localhost sinan-painel:teste`;
    depois de ~5 s, `docker exec sinan-teste <comando de saúde do contrato>` → código 0;
    `docker logs sinan-teste` não tem nenhuma linha `GET /api/meta` (sem log de acesso);
    `docker rm -f sinan-teste`.
  - `docker image ls sinan-painel:teste` → anotar o tamanho no PR.
- [ ] **Passo 5:** `uv run pytest` e `uv run ruff check .` passam.
- [ ] **Passo 6: Commit** "Adiciona a imagem Docker do painel"
  (corpo: imagem em dois estágios para a VPS, sem compiladores, sem root e sem registrar o IP de quem
  consulta; o modo local não muda). `push`, PR para a `develop`, esperar o merge.

### Tarefa 2: Compose, proxy com HTTPS e atualização no container

Branch: `feature/compose-proxy`, da `develop` depois do merge da Tarefa 1.

**Arquivos:**
- Criar: `compose.yaml`, `deploy/caddy/Dockerfile`, `deploy/caddy/Caddyfile`, `.env.exemplo`
- Modificar: `scripts/atualizar_servidor.sh`, `.gitattributes`, `tests/test_implantacao.py`

**Interfaces:**
- Consome: a imagem e o contrato da Tarefa 1.
- Produz: serviços `painel`, `atualizar`, `proxy`; `image: sinan-painel:atual`; variáveis `SINAN_HOSTS` e
  `SINAN_RAMO`; trava e log da atualização (tabela do contrato).

- [ ] **Passo 1: Testes que falham**, em `tests/test_implantacao.py`. Os que usam Docker têm
  `@pytest.mark.skipif(shutil.which("docker") is None, reason="sem Docker")` e rodam
  `docker compose --profile ferramentas --env-file <tmp>/.env config --format json` num ambiente sem
  variáveis `SINAN_*` (sem `--profile ferramentas` o `config` não mostra o `atualizar`):
  - `test_compose_painel_so_na_rede_interna`: com `SINAN_HOSTS=painel.exemplo.br` no `.env` temporário,
    `painel` não tem `ports`, só está na rede `interna`, `networks.interna.internal is True`,
    `restart == "unless-stopped"`, tem `mem_limit`, o volume `dados` montado em `/dados`, o `healthcheck.test`
    contém `/api/meta`, e `environment` tem `SINAN_MODO=publico`, `SINAN_DADOS=/dados`, `SINAN_HOSTS=painel.exemplo.br`.
  - `test_compose_proxy_unica_porta_aberta`: só o `proxy` publica portas, e são exatamente 80 e 443.
  - `test_compose_atualizar_so_sob_demanda`: `atualizar` tem `profiles == ["ferramentas"]`, a mesma imagem
    `sinan-painel:atual`, `pull_policy == "never"`, `entrypoint == ["bash", "scripts/atualizar_servidor.sh"]`,
    o volume `dados` em `/dados` e está na rede `default` (precisa de internet).
  - `test_compose_logs_com_rotacao`: nos três serviços, `logging.options == {"max-size": "10m", "max-file": "3"}`.
  - `test_compose_sem_dominio_falha`: `.env` vazio → `docker compose config` sai ≠ 0 e a saída de erro contém `SINAN_HOSTS`.
  - `test_atualizacao_calcula_anos`: `scripts/atualizar_servidor.sh` contém `--anos "$((ANO - 5))-$ANO"`,
    `flock -n` e não contém `UV`.
  - `test_atualizacao_registra_fim_mesmo_com_erro` (pula sem `bash` ou `flock`, e no Windows): `PATH` com um
    `python` falso que imprime `baixando` e sai com 3; roda `bash scripts/atualizar_servidor.sh` a partir da
    raiz com `SINAN_DADOS=<tmp>` → código 3, a saída tem `baixando`, e `<tmp>/atualizacao.log` tem uma linha
    com `início` e outra com `fim (código 3)`.
  - `test_atualizacao_recusa_execucao_dupla` (mesmas condições): com `<tmp>/.atualizando` travado por um
    `flock` do próprio teste (`subprocess.Popen(["flock", trava, "sleep", "5"])`), o script sai com 1 e a
    saída de erro tem "Já existe uma atualização em andamento.".
- [ ] **Passo 2:** `uv run pytest tests/test_implantacao.py -v` → os novos falham.
- [ ] **Passo 3: Implementar.**
  - `compose.yaml` (sem a chave `version`; um bloco `x-logs` com a configuração de log, reaproveitado nos
    três serviços com `logging: *logs`):
    - `painel`: `build: .`, `image: sinan-painel:atual`, `environment` com `SINAN_MODO: publico`,
      `SINAN_DADOS: /dados`, `SINAN_HOSTS: ${SINAN_HOSTS:?defina SINAN_HOSTS no .env com o domínio do painel}`;
      `volumes: [dados:/dados]`; `networks: [interna]`; `restart: unless-stopped`; `mem_limit: 1g`;
      `healthcheck` com o comando do contrato, `interval: 30s`, `timeout: 10s`, `retries: 3`, `start_period: 30s`.
    - `atualizar`: `image: sinan-painel:atual` (sem `build`), `pull_policy: never`,
      `entrypoint: ["bash", "scripts/atualizar_servidor.sh"]` (não depende do bit de execução nem do fim de
      linha salvo no Windows), `environment: {SINAN_DADOS: /dados}`, mesmo volume, `networks: [default]`,
      `profiles: [ferramentas]`, `mem_limit: 2g`.
    - `proxy`: `build: deploy/caddy`, `ports: ["80:80", "443:443"]`, `environment: {SINAN_HOSTS: ${SINAN_HOSTS:?...}}`,
      `volumes`: `./deploy/caddy/Caddyfile:/etc/caddy/Caddyfile:ro`, `caddy_dados:/data` (certificados),
      `caddy_config:/config`; `networks: [interna, default]`; `depends_on: {painel: {condition: service_healthy}}`;
      `restart: unless-stopped`; `mem_limit: 256m`.
    - `networks: {interna: {internal: true}}`; `volumes: {dados: {}, caddy_dados: {}, caddy_config: {}}`.
  - `deploy/caddy/Dockerfile`: `FROM caddy:<tag>-builder AS build` → `RUN xcaddy build --with github.com/mholt/caddy-ratelimit@<hash>`;
    `FROM caddy:<tag>` → `COPY --from=build /usr/bin/caddy /usr/bin/caddy`. Tag e hash fixos, anotados no PR.
  - `deploy/caddy/Caddyfile`:
    - global: `order rate_limit before basic_auth`;
    - site `{$SINAN_HOSTS}`: `encode zstd gzip`; `header` com `X-Content-Type-Options nosniff`,
      `X-Frame-Options DENY`, `Referrer-Policy strict-origin-when-cross-origin`,
      `Strict-Transport-Security "max-age=31536000"` e `-Server`;
    - `rate_limit` com uma zona `api`: `match { path /api/* }`, `key {remote_host}`, `events 100`, `window 10s`
      (veja "Limite de pedidos");
    - `reverse_proxy painel:8501` (o Caddy já repassa o `Host` original e o `X-Forwarded-*`);
    - `handle_errors 429` responde com `Content-Type: application/json` e
      `{"erro": "Muitos pedidos em pouco tempo. Espere alguns segundos e tente de novo."}`;
    - sem log de acesso (não guardar IP de quem consulta).
  - `.env.exemplo`, com um comentário por linha: `SINAN_HOSTS=painel.prism.ufrr.br` ("um domínio só, sem
    https://, sem porta e sem aspas; o DNS dele precisa apontar para este servidor") e `SINAN_RAMO=main`
    ("branch usada pelo scripts/painel.sh implantar: main ou develop").
  - `.gitattributes`: acrescentar `*.sh text eol=lf`.
  - `scripts/atualizar_servidor.sh`: comentário do topo diz que roda dentro do container (serviço `atualizar`);
    tira `UV`; exige `SINAN_DADOS`; mantém `ANO`, os agravos, a UF e o `"$@"`; com a trava ocupada escreve
    "Já existe uma atualização em andamento." no log e na saída de erro e sai com 1. A chamada fica assim,
    para o `set -e` não encerrar o script antes de gravar o fim quando o download falha:

    ```bash
    echo "== $(date '+%F %T') início" | tee -a "$LOG"
    set +e
    python baixar_dados.py --agravos DENG CHIK ZIKA --ufs RR --anos "$((ANO - 5))-$ANO" "$@" 2>&1 | tee -a "$LOG"
    codigo=${PIPESTATUS[0]}
    set -e
    echo "== $(date '+%F %T') fim (código $codigo)" | tee -a "$LOG"
    exit "$codigo"
    ```
- [ ] **Passo 4:** `uv run pytest tests/test_implantacao.py -v` passa (sem pular, nesta máquina com Docker).
- [ ] **Passo 5: Subir de verdade, com dados pequenos.** **Avisar o usuário antes:** baixa zika 2024 do FTP.
  - `cp .env.exemplo .env` e `SINAN_HOSTS=localhost` (o Caddy usa um certificado próprio para `localhost`).
  - `docker compose run --rm --no-deps --entrypoint caddy proxy validate --config /etc/caddy/Caddyfile --adapter caddyfile` → "Valid configuration".
  - `docker compose up -d --build --wait --wait-timeout 180` → sai com 0; `docker compose ps` mostra `painel` `(healthy)`.
  - `docker compose run --rm -T atualizar --agravos ZIKA --anos 2024` → sai com 0 (prova do volume gravável
    e do Numba no fluxo real); o fim do log mostra a hora de Boa Vista.
  - Trava no fluxo real: rodar o mesmo comando duas vezes ao mesmo tempo (`&` no primeiro) → o segundo sai
    com 1 e "Já existe uma atualização em andamento."
- [ ] **Passo 6: Memória do DuckDB.**
  `docker compose exec -T painel python -c "import duckdb; print(duckdb.sql(\"select current_setting('memory_limit')\").fetchone())"`
  → um valor abaixo de 1 GB (o DuckDB calcula 80% da memória que enxerga; o que não se sabe é se a versão
  2.0.0 enxerga o limite do container ou a memória da máquina inteira). Se vier maior: em
  `sinan/consultas.py:40`, `duckdb.connect(config={"memory_limit": ...})` com o valor de uma variável
  `SINAN_DUCKDB_MEMORIA` (sem ela, nada muda no modo local); `SINAN_DUCKDB_MEMORIA: 700MB` no `painel` do compose;
  teste `test_limite_de_memoria_do_duckdb` em `tests/test_consultas.py` (com a variável, `current_setting('memory_limit')`
  da conexão reflete o valor); commit separado "Permite limitar a memória do DuckDB no servidor".
- [ ] **Passo 7: Conferir o proxy.**
  - `curl -sk -o /dev/null -w '%{http_code}' https://localhost/api/meta` → `200`.
  - `curl -sk -D - -o /dev/null -H 'Accept-Encoding: gzip' https://localhost/vendor/plotly.min.js` → tem
    `Content-Encoding: gzip`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e não tem `Server:`.
  - `curl -s -o /dev/null -w '%{http_code}' http://localhost/` → `308` (redireciona para HTTPS).
  - `curl -s --max-time 3 http://localhost:8501/` falha (painel sem porta no host).
  - `curl -sk -o /dev/null -w '%{http_code}' https://localhost/api/registros?agravo=ZIKA` → `403`.
  - `docker compose logs painel proxy` não tem nenhum IP de cliente.
- [ ] **Passo 8: Conferir o limite.** 150 pedidos seguidos a `https://localhost/api/meta` → aparece `429`, com
  corpo JSON que tem `erro`; 150 pedidos seguidos a `https://localhost/static/js/main.js` → nenhum `429`.
  Abrir `https://localhost` no navegador (captura com o Edge sem janela, com o registro de rede) → a Visão
  geral carrega sem erro; anotar no PR quantos pedidos a carga fez e quantos foram `/api/*`. Se forem mais
  de 10 de API, rever o `events` antes do merge.
- [ ] **Passo 9:** `docker compose down` (sem `-v`); `uv run pytest` e `uv run ruff check .` passam.
- [ ] **Passo 10: Commit** "Adiciona o compose com proxy HTTPS e atualização dos dados em container"
  (corpo: painel só na rede interna, Caddy como única porta, limite só na API, logs com rotação e sem IP,
  atualização com trava, anos calculados e fim registrado mesmo com erro). `push`, PR, esperar o merge.

### Tarefa 3: Script de gerenciamento `scripts/painel.sh`

Branch: `feature/script-painel`, da `develop` depois do merge da Tarefa 2.

**Arquivos:**
- Criar: `scripts/painel.sh` (executável: `git update-index --chmod=+x`), `tests/test_painel_sh.py`

**Interfaces:**
- Consome: serviços, imagem, variáveis e comando de saúde da Tarefa 2.
- Produz: `scripts/painel.sh <subcomando>`; códigos de saída: 0 tudo certo, 1 falha, 2 uso errado
  (subcomando ou opção desconhecida, com a ajuda impressa).

Comportamento (o script sempre entra na raiz do projeto: `cd "$(dirname "$0")/.."`):

| Subcomando | Comandos | Sai com ≠ 0 quando |
|---|---|---|
| (todos menos `ajuda`) | antes de tudo: `.env` existe, senão "Arquivo .env não encontrado. Crie com: cp .env.exemplo .env e preencha o domínio." | sem `.env`; `docker compose version` falha |
| `status` | `docker compose ps` (estado, saúde e tempo no ar); `docker stats --no-stream` dos containers do projeto; `docker compose exec -T painel du -sh /dados`; `atualizado_em` lido de `/api/meta` com `docker compose exec -T painel python -c ...` ("nunca" se vazio). Cada linha de informação usa `|| echo "não disponível"` | saúde do `painel` (`docker inspect -f '{{.State.Health.Status}}'` do id de `docker compose ps -q painel`) diferente de `healthy`, ou estado do `proxy` diferente de `running`: "O painel está fora do ar (saúde: X)." |
| `iniciar` | `docker compose up -d --wait --wait-timeout 180`; imprime `https://<SINAN_HOSTS>`; se `atualizado_em` vier vazio, avisa "Ainda não há dados. Rode: scripts/painel.sh atualizar-dados" | o `up` falha: "O painel não ficou pronto. Veja: scripts/painel.sh logs painel" |
| `parar` | `docker compose down` (nunca `-v`) | o comando falha |
| `reiniciar` | `docker compose up -d --force-recreate --wait --wait-timeout 180` (relê o `.env`) | igual ao `iniciar` |
| `logs [servico] [-f]` | `docker compose logs --tail 200 [-f] [servico]` | serviço fora de `painel`, `proxy` → uso errado |
| `atualizar-dados [--forcar]` | se `docker image inspect sinan-painel:atual` falhar: "A imagem do painel ainda não existe. Rode primeiro: scripts/painel.sh iniciar" e saída 1; senão `docker compose run --rm -T atualizar [--forcar]` | qualquer outro argumento → uso errado; sem imagem; código do container ≠ 0 |
| `implantar` | veja abaixo | `.git` com mudanças, `SINAN_RAMO` inválido, `pull` falha, ou saúde falha (com volta) |
| `ajuda` | lista os subcomandos com uma linha cada | nunca |

`implantar`, nesta ordem:
1. Lê `SINAN_RAMO` do `.env`: a última linha `SINAN_RAMO=`, sem `\r`, sem aspas simples ou duplas e sem
   espaços (`sed -n 's/^SINAN_RAMO=//p' .env | tail -n 1 | tr -d "\r\"' "`); vazio vira `main`. Outro valor
   que não `main` ou `develop` → "SINAN_RAMO inválido no .env: 'X'. Use main ou develop." e saída 1.
2. Recusa se `git status --porcelain` não for vazio.
3. `git fetch origin "$RAMO"`, `git switch "$RAMO"`, `git pull --ff-only origin "$RAMO"`.
4. Se `docker image inspect sinan-painel:atual` existir, `docker tag sinan-painel:atual sinan-painel:anterior`.
5. `docker compose build`; `docker compose up -d --wait --wait-timeout 180`.
6. Deu certo: `docker image prune -f` (só imagens sem nome; o `:anterior` fica para a próxima volta) e saída 0.
7. Falhou: `docker tag sinan-painel:anterior sinan-painel:atual`, `docker compose up -d --wait --wait-timeout 180 painel`,
   mensagem "A versão nova não ficou saudável. O painel voltou para a versão anterior. Veja: scripts/painel.sh logs painel"
   e saída 1. Comentário no script:
   `# shortcut: a volta troca só a imagem; compose.yaml e Caddyfile ficam na versão nova do git. Se a mudança for neles, volte o commit à mão.`

- [ ] **Passo 1: Testes que falham**, em `tests/test_painel_sh.py`, com
  `pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="precisa de bash")`.
  Fixture `projeto(tmp_path)`: copia `scripts/painel.sh` para `tmp_path/scripts/`, cria `tmp_path/bin/docker`
  e `tmp_path/bin/git` falsos e roda o script com `PATH=tmp_path/bin:` + `PATH` original. Os falsos anotam
  cada chamada (`"$*"`, uma por linha) em `$FALSO_LOG`; o `docker` falso responde:
  `.State.Health.Status` → `$FALSO_SAUDE`; `.State.Status` → `running`; `compose ps -q` → `abc123`;
  `image inspect` → sai com 1 se o arquivo `$FALSO_SEM_IMAGEM` existir; `compose up` → sai com 1 e apaga o
  arquivo `$FALSO_UP_FALHA` se ele existir; tudo o mais → saída 0 sem texto. O `git` falso sai com 0 sem texto.
  - `test_recusa_sem_env`: sem `.env`, `status` → código 1 e a saída contém `cp .env.exemplo .env`; nenhuma chamada ao `docker compose`.
  - `test_ajuda_sem_env`: sem `.env`, `ajuda` → código 0 e a saída contém `status`, `iniciar`, `parar`,
    `reiniciar`, `logs`, `atualizar-dados` e `implantar`.
  - `test_subcomando_desconhecido`: `voar` → código 2 e a saída contém `atualizar-dados`.
  - `test_status_saudavel_sai_0`: `.env` presente, `FALSO_SAUDE=healthy` → código 0.
  - `test_status_painel_fora_do_ar`: `FALSO_SAUDE=unhealthy` → código 1 e a saída contém "fora do ar".
  - `test_atualizar_dados_repassa_forcar`: `atualizar-dados --forcar` → o log tem `compose run --rm -T atualizar --forcar`;
    `atualizar-dados --anos 2020` → código 2.
  - `test_atualizar_dados_sem_imagem`: `$FALSO_SEM_IMAGEM` criado → código 1, saída contém `scripts/painel.sh iniciar`,
    e nenhum `compose run` no log.
  - `test_implantar_volta_a_imagem_anterior`: `.env` com `SINAN_RAMO=develop`, arquivo `$FALSO_UP_FALHA` criado →
    código 1, saída contém "versão anterior", e no log, nesta ordem: `pull --ff-only origin develop`,
    `tag sinan-painel:atual sinan-painel:anterior`, `compose build`, `tag sinan-painel:anterior sinan-painel:atual`;
    nenhum `image prune`.
  - `test_implantar_limpa_imagens_quando_da_certo`: `.env` com `SINAN_RAMO="develop"\r` (aspas e CRLF) → código 0,
    o log tem `pull --ff-only origin develop` e termina com `image prune -f`.
  - `test_implantar_recusa_ramo_estranho`: `SINAN_RAMO=teste` → código 1, a saída contém `'teste'`, e nenhum `pull` no log.
- [ ] **Passo 2:** `uv run pytest tests/test_painel_sh.py -v` → falham.
- [ ] **Passo 3:** implementar `scripts/painel.sh` conforme a tabela, com `set -euo pipefail`, uma função por subcomando e um `case` no fim.
- [ ] **Passo 4:** `uv run pytest tests/test_painel_sh.py -v` passa;
  `shellcheck scripts/painel.sh scripts/atualizar_servidor.sh` sem avisos (sem `shellcheck` instalado:
  `docker run --rm -v "$PWD:/mnt:ro" koalaman/shellcheck:stable /mnt/scripts/painel.sh /mnt/scripts/atualizar_servidor.sh`).
- [ ] **Passo 5: Conferir com o Docker de verdade** (`.env` com `SINAN_HOSTS=localhost`, dados da Tarefa 2):
  `scripts/painel.sh iniciar` → 0; `status` → 0, mostra `healthy`, tamanho do volume e a data da última
  atualização; `docker compose stop painel` e `status` → 1; `reiniciar` → 0; `logs painel` mostra linhas;
  `parar` → 0 e `docker volume ls` ainda tem o volume de dados.
- [ ] **Passo 6: `.env` errado:** `SINAN_HOSTS=localhost:8443` e `scripts/painel.sh reiniciar` → código ≠ 0 e a
  mensagem manda ver os logs; `logs painel` mostra "SINAN_HOSTS não aceita porta". Voltar o `.env`.
- [ ] **Passo 7: Volta da implantação**, sem tocar no GitHub. **Atenção:** as tags de imagem são globais no
  Docker, então este teste sobrescreve `sinan-painel:atual` e `sinan-painel:anterior` da pasta principal.
  `scripts/painel.sh parar`; clonar o projeto numa pasta temporária `A` (faz o papel do `origin`) e clonar `A`
  em `B`; em `B`, `.env` com `SINAN_HOSTS=localhost` e `SINAN_RAMO=develop`, e `scripts/painel.sh iniciar` → 0.
  Em `A`, na `develop`, um commit que quebra a subida (`raise RuntimeError("teste")` no começo de `criar_app()`).
  Em `B`, `scripts/painel.sh implantar` → código 1 com "versão anterior", e `scripts/painel.sh status` → 0.
  Depois: `scripts/painel.sh parar` em `B`, apagar `A` e `B`, e **na pasta principal** `docker compose build`
  para refazer a imagem a partir do código dela.
- [ ] **Passo 8:** `uv run pytest` e `uv run ruff check .` passam.
- [ ] **Passo 9: Commit** "Adiciona o script de gerenciamento do painel no servidor"
  (corpo: status com código de saída para monitoramento, implantação com volta automática se a versão nova
  não ficar saudável e limpeza das imagens antigas). `push`, PR, esperar o merge.

### Tarefa 4: README "Publicar com Docker" e aceite final

Branch: `feature/docs-docker`, da `develop` depois do merge da Tarefa 3.

**Arquivos:**
- Modificar: `README.md` (trocar a seção "Publicar no servidor" por "Publicar com Docker"; citar os arquivos
  novos na parte "Para desenvolvedores")

- [ ] **Passo 1: Escrever a seção**, nesta ordem, em português simples:
  - o que é: o mesmo painel, só leitura e só números agregados; o computador do Windows continua com os `.bat`;
  - o que a VPS precisa: Docker com Compose v2 e o serviço ligado na inicialização (`systemctl enable docker`,
    para o painel voltar sozinho depois de reiniciar a máquina), `git`, domínio com DNS apontando para ela,
    portas 80 e 443 abertas, saída para `ftp.datasus.gov.br`; o usuário que roda o script precisa estar no grupo `docker`;
  - instalar: `git clone`, `cp .env.exemplo .env`, editar `SINAN_HOSTS`, `scripts/painel.sh iniciar`,
    `scripts/painel.sh atualizar-dados` (avisar que a primeira carga baixa os arquivos nacionais de dengue,
    centenas de MB por ano, e pode levar horas);
  - a tabela de subcomandos do `painel.sh` (da Tarefa 3) e o significado do código de saída do `status` para monitoramento;
  - atualização semanal: `crontab -e` com `0 3 * * 1 /caminho/do/projeto/scripts/painel.sh atualizar-dados > /dev/null`
    (a hora é a do relógio da VPS; erros chegam pelo e-mail do cron, se houver); o log completo, com a hora de Boa Vista:
    `docker compose run --rm --no-deps --entrypoint tail atualizar -n 50 /dados/atualizacao.log`;
  - logs: limitados a 30 MB por serviço e sem IP de quem consulta;
  - cópias de segurança: **não copiar a pasta de dados**; guardar `compose.yaml`, `.env` e
    `deploy/caddy/Caddyfile` (os dois versionados vêm do git; o `.env` é o único que só existe na VPS).
    Para restaurar: `iniciar` e `atualizar-dados --forcar`. Os certificados se refazem sozinhos, mas não
    apague o volume `caddy_dados` sem motivo (o Let's Encrypt limita quantos certificados novos por semana);
  - a tabela de variáveis (`SINAN_MODO`, `SINAN_HOSTS`, `SINAN_DADOS`) continua, dizendo que no Docker só
    `SINAN_HOSTS` e `SINAN_RAMO` são preenchidos pela equipe.
- [ ] **Passo 2: Aceite 4 — modo local sem Docker:** com o Docker parado, `uv run python iniciar.py --sem-navegador`
  numa porta livre abre a Visão geral com os dados de `dados/`; `git diff develop -- '*.bat' iniciar.py baixar_dados.py pyproject.toml uv.lock`
  vazio. (No Windows do usuário: dois cliques no `ABRIR_DASHBOARD.bat`.)
- [ ] **Passo 3: Aceite 1 — máquina limpa:** `docker compose down`, `docker image rm sinan-painel:atual sinan-painel:anterior`,
  clone novo numa pasta temporária, `cp .env.exemplo .env`, `SINAN_HOSTS=localhost`, `scripts/painel.sh iniciar` → 0 e
  `curl -sk -o /dev/null -w '%{http_code}' https://localhost/` → `200`. (O HTTPS com certificado público só se
  confere na VPS; veja "Pontos a validar".)
- [ ] **Passo 4: Aceite 2:** `status` → 0; `docker compose stop painel` → `status` → 1; `iniciar` → 0.
- [ ] **Passo 5: Aceite 3 — atualização com o painel no ar:** com zika 2024 carregado, rodar em paralelo
  `docker compose run --rm -T atualizar --forcar --agravos ZIKA --anos 2024` e um laço de **300 pedidos no
  total**: 150 voltas, cada uma com um pedido a `/api/visao?agravo=ZIKA` e outro a `/api/meta` pelo HTTPS e
  `sleep 0.5` entre as voltas (4 pedidos por segundo, abaixo do limite de 10), contando os códigos com
  `sort | uniq -c` → só `200`; nenhum `/api/meta` com `"agravos": []`. Se aparecer 500 ou a lista vazia,
  seguir o que diz "Atualização com o painel no ar".
- [ ] **Passo 6:** `uv run pytest` e `uv run ruff check .` passam; `scripts/painel.sh parar`.
- [ ] **Passo 7: Commit** "Documenta a publicação do painel com Docker"
  (corpo: troca o guia com systemd e nginx pelo compose e pelo scripts/painel.sh, com instalação, cron,
  cópias de segurança e restauração). `push`, PR, esperar o merge.

---

## Critérios de aceite finais

1. Numa máquina limpa com Docker, `cp .env.exemplo .env`, editar o domínio e rodar `scripts/painel.sh iniciar`
   deixa o painel no ar em HTTPS (Tarefa 4, Passo 3; com certificado público, na VPS).
2. `scripts/painel.sh status` sai com 0 com tudo saudável e com ≠ 0 se o painel cair (Tarefa 3, testes e
   Passo 5; Tarefa 4, Passo 4).
3. A atualização de dados roda com o painel no ar sem nenhuma resposta 500 (Tarefa 4, Passo 5).
4. O modo local pelo `.bat` continua funcionando sem Docker (Tarefa 4, Passo 2).

## Pontos a validar na VPS (antes da Tarefa 4 ou durante a implantação)

- **Sistema e arquitetura:** distribuição e versão; `uname -m`. A imagem foi testada em `x86_64`; em `aarch64`
  (ARM) as wheels de `numba`/`llvmlite`/`duckdb` existem, mas é preciso repetir a conferência da Tarefa 1, Passo 4.
- **Docker:** Engine ≥ 24 e Compose v2 ≥ 2.20 (`--wait-timeout` do `up`); `systemctl enable docker` (sem isso,
  o `restart: unless-stopped` não traz nada de volta depois de reiniciar a máquina); o usuário do cron no grupo
  `docker` (que equivale a root na VPS: decidir quem entra nele).
- **Domínio e DNS:** nome definitivo (ex.: `painel.prism.ufrr.br`) com registro A/AAAA para a VPS **antes** do
  primeiro `iniciar`, senão o Caddy não consegue o certificado e tenta de novo em intervalos crescentes.
- **Portas:** 80 e 443 de entrada abertas no firewall da VPS e da UFRR (a 80 é usada pelo Let's Encrypt e
  para redirecionar a HTTPS); saída para `ftp.datasus.gov.br` (porta 21 e portas passivas) e para o Let's Encrypt.
- **Proxy da UFRR na frente:** se houver, o limite de pedidos veria um IP só para todo mundo; nesse caso a chave
  do `rate_limit` precisa ser o IP repassado pelo proxy da UFRR, e o HTTPS talvez termine nele.
- **Memória e disco:** limites propostos: painel 1 GB, atualização 2 GB, proxy 256 MB. Medir o pico da
  primeira carga de dengue com `docker stats` e ajustar (e o `SINAN_DUCKDB_MEMORIA`, se a Tarefa 2 o criou);
  espaço em disco para os `.dbc` nacionais (apagados depois do processamento) e para os Parquet.
- **Fuso do cron:** `timedatectl` na VPS; "segunda às 3h" é no relógio do host. Os logs do container já saem
  na hora de Boa Vista.
- **Licenças do sistema base:** as imagens `python:slim` (Debian) e `caddy` (Alpine) trazem programas do
  sistema com GPL/LGPL (ex.: `bash`, `glibc`, `busybox`, `util-linux`). Eles não são dependências do código e
  só rodam lado a lado com ele, mas a regra do `CLAUDE.md` não trata desse caso: confirmar com o grupo que
  está aceito. O mesmo vale para o `shellcheck` (GPL-3.0), que só é usado para conferir os scripts e não vai
  para a imagem; se não for aceito, o passo do `shellcheck` sai do plano.

## Fora deste plano

- Monitoramento externo (alerta quando o `status` falhar): o código de saída já serve para isso.
- Atualização sem nenhuma interrupção no `implantar` (dois containers alternando): a troca leva segundos.
- Imagem publicada num registro (GHCR) e build pela integração contínua: o build é feito na própria VPS.
- Agravos e UF da atualização configuráveis no `.env`: continuam fixos (DENG, CHIK, ZIKA; RR), como hoje.
