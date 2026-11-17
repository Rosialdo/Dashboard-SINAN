#!/usr/bin/env bash
# Gerencia o painel publicado na VPS (Docker Compose). Rode "scripts/painel.sh ajuda".
# Códigos de saída: 0 tudo certo, 1 falha, 2 uso errado. Servem para monitoramento.
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGEM=sinan-painel:atual
ANTERIOR=sinan-painel:anterior
ESPERA=(--wait --wait-timeout 180)

ajuda() {
  cat <<'FIM'
Uso: scripts/painel.sh <comando>

  status                       mostra se o painel está no ar, memória, tamanho dos dados e a data da última atualização
  iniciar                      liga o painel
  parar                        desliga o painel (os dados ficam guardados)
  reiniciar                    desliga e liga de novo, relendo o .env
  logs [painel|proxy] [-f]     mostra as últimas mensagens (-f continua acompanhando)
  atualizar-dados [--forcar]   baixa os dados do DATASUS agora (--forcar baixa tudo de novo)
  implantar                    baixa a versão nova do código, troca o painel e volta para a anterior se der errado
  ajuda                        mostra esta lista
FIM
}

falha() { echo "ERRO: $*" >&2; exit 1; }
uso() { echo "ERRO: $*" >&2; ajuda >&2; exit 2; }

# valor de uma variável do .env, sem aspas, espaços nem o \r de arquivos salvos no Windows
ler_env() { sed -n "s/^$1=//p" .env | tail -n 1 | tr -d "\r\"' "; }

exigir_env() {
  [[ -f .env ]] || falha "Arquivo .env não encontrado. Crie com: cp .env.exemplo .env e preencha o domínio."
  docker compose version > /dev/null 2>&1 || falha "Docker Compose v2 não encontrado. Instale o Docker com o plugin compose."
}

# texto curto de estado de um serviço; vazio se o container não existir
estado() {
  local id
  id=$(docker compose ps -q "$1" 2> /dev/null || true)
  [[ -n "$id" ]] || { echo "desligado"; return; }
  docker inspect -f "$2" "$id" 2> /dev/null || echo "desconhecido"
}

atualizado_em() {
  docker compose exec -T painel python -c \
    "import json, urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8501/api/meta', timeout=5))['atualizado_em'] or 'nunca')" \
    2> /dev/null || echo "não disponível"
}

cmd_status() {
  docker compose ps --format 'table {{.Service}}\t{{.Status}}' || echo "não disponível"
  echo
  local ids
  ids=$(docker compose ps -q 2> /dev/null || true)
  if [[ -n "$ids" ]]; then
    # shellcheck disable=SC2086  # um id por palavra
    docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' $ids || echo "uso de CPU e memória: não disponível"
  fi
  echo
  echo "Tamanho dos dados: $(docker compose exec -T painel du -sh /dados 2> /dev/null | cut -f1 || echo 'não disponível')"
  echo "Última atualização dos dados: $(atualizado_em)"

  local saude proxy
  saude=$(estado painel '{{.State.Health.Status}}')
  proxy=$(estado proxy '{{.State.Status}}')
  [[ "$saude" == healthy ]] || falha "O painel está fora do ar (saúde: $saude)."
  [[ "$proxy" == running ]] || falha "O proxy está fora do ar (estado: $proxy)."
  echo "Tudo no ar."
}

subir() {
  docker compose up -d "${ESPERA[@]}" "$@" || falha "O painel não ficou pronto. Veja: scripts/painel.sh logs painel"
}

avisar_endereco() {
  echo "Painel no ar em https://$(ler_env SINAN_HOSTS)"
  [[ "$(atualizado_em)" != nunca ]] || echo "Ainda não há dados. Rode: scripts/painel.sh atualizar-dados"
}

cmd_logs() {
  local servico="" seguir=()
  for a in "$@"; do
    case "$a" in
      painel | proxy) servico=$a ;;
      -f) seguir=(-f) ;;
      *) uso "Opção desconhecida para logs: $a" ;;
    esac
  done
  docker compose logs --tail 200 "${seguir[@]}" ${servico:+"$servico"}
}

cmd_atualizar_dados() {
  local extra=()
  case "${1:-}" in
    "") ;;
    --forcar) extra=(--forcar) ;;
    *) uso "Opção desconhecida para atualizar-dados: $1" ;;
  esac
  [[ $# -le 1 ]] || uso "atualizar-dados aceita só --forcar."
  docker image inspect "$IMAGEM" > /dev/null 2>&1 \
    || falha "A imagem do painel ainda não existe. Rode primeiro: scripts/painel.sh iniciar"
  if ! docker compose run --rm -T atualizar "${extra[@]}"; then
    # no cron a saída normal vai para /dev/null: o fim do registro vai para a saída de erro (e-mail do cron)
    docker compose run --rm --no-deps -T --entrypoint tail atualizar -n 30 /dados/atualizacao.log >&2 || true
    falha "A atualização dos dados falhou. As últimas linhas do registro estão acima."
  fi
}

cmd_implantar() {
  local ramo
  ramo=$(ler_env SINAN_RAMO)
  ramo=${ramo:-main}
  [[ "$ramo" == main || "$ramo" == develop ]] || falha "SINAN_RAMO inválido no .env: '$ramo'. Use main ou develop."
  [[ -z "$(git status --porcelain)" ]] || falha "Há arquivos alterados nesta pasta. Guarde ou desfaça as mudanças antes de implantar."

  git fetch origin "$ramo"
  git switch "$ramo"
  git pull --ff-only origin "$ramo" || falha "Não foi possível baixar a versão nova do código."

  if docker image inspect "$IMAGEM" > /dev/null 2>&1; then
    docker tag "$IMAGEM" "$ANTERIOR"
  fi
  docker compose build
  if docker compose up -d "${ESPERA[@]}"; then
    avisar_endereco
    docker image prune -f > /dev/null  # só imagens sem nome; a anterior fica para a próxima volta
    return
  fi
  # shortcut: a volta troca só a imagem; compose.yaml e Caddyfile ficam na versão nova do git. Se a mudança for neles, volte o commit à mão.
  docker tag "$ANTERIOR" "$IMAGEM"
  docker compose up -d "${ESPERA[@]}" painel || true
  falha "A versão nova não ficou saudável. O painel voltou para a versão anterior. Veja: scripts/painel.sh logs painel"
}

comando=${1:-ajuda}
[[ $# -gt 0 ]] && shift
case "$comando" in
  ajuda | -h | --help) ajuda; exit 0 ;;
  status | iniciar | parar | reiniciar | logs | atualizar-dados | implantar) exigir_env ;;
  *) uso "Comando desconhecido: $comando" ;;
esac

case "$comando" in
  status) cmd_status ;;
  iniciar) subir; avisar_endereco ;;
  parar) docker compose down ;;  # nunca com -v: apagaria os dados e os certificados
  reiniciar) subir --force-recreate; avisar_endereco ;;
  logs) cmd_logs "$@" ;;
  atualizar-dados) cmd_atualizar_dados "$@" ;;
  implantar) cmd_implantar ;;
esac
