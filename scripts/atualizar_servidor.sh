#!/usr/bin/env bash
# Atualização semanal do painel publicado (chamado pelo cron).
#
# Precisa de:
#   UV           caminho completo do uv (o cron não carrega o PATH), ex.: /home/sinan/.local/bin/uv
#   SINAN_DADOS  pasta dos dados, ex.: /srv/sinan-dados
# Argumentos extras vão para o baixar_dados.py (ex.: --forcar para baixar tudo de novo).
set -euo pipefail

: "${UV:?defina UV com o caminho completo do uv}"
: "${SINAN_DADOS:?defina SINAN_DADOS com a pasta dos dados}"
export SINAN_DADOS

cd "$(dirname "$0")/.."
mkdir -p "$SINAN_DADOS"
ANO=$(date +%Y)  # calculado a cada vez: o ano novo entra sozinho em janeiro
LOG="$SINAN_DADOS/atualizacao.log"

# flock: se a semana anterior ainda estiver rodando, esta execução desiste
exec 9>"$SINAN_DADOS/.atualizando"
if ! flock -n 9; then
  echo "$(date '+%F %T') já existe uma atualização em andamento" >> "$LOG"
  exit 0
fi

{
  echo "== $(date '+%F %T') início"
  "$UV" run --frozen python baixar_dados.py --agravos DENG CHIK ZIKA --ufs RR --anos "$((ANO - 5))-$ANO" "$@"
  echo "== $(date '+%F %T') fim"
} >> "$LOG" 2>&1
