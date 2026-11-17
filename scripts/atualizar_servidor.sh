#!/usr/bin/env bash
# Atualização dos dados do painel publicado. Roda dentro do container (serviço "atualizar" do
# compose.yaml), chamado pelo scripts/painel.sh atualizar-dados, à mão ou pelo cron.
#
# Precisa de SINAN_DADOS (pasta dos dados). Argumentos extras vão para o baixar_dados.py
# (ex.: --forcar para baixar tudo de novo; --agravos/--anos trocam os padrões).
set -euo pipefail

: "${SINAN_DADOS:?defina SINAN_DADOS com a pasta dos dados}"

cd "$(dirname "$0")/.."
mkdir -p "$SINAN_DADOS"
ANO=$(date +%Y)  # calculado a cada vez: o ano novo entra sozinho em janeiro
LOG="$SINAN_DADOS/atualizacao.log"

# flock: se outra atualização ainda estiver rodando, esta desiste
exec 9>"$SINAN_DADOS/.atualizando"
if ! flock -n 9; then
  echo "$(date '+%F %T') Já existe uma atualização em andamento." | tee -a "$LOG" >&2
  exit 1
fi

echo "== $(date '+%F %T') início" | tee -a "$LOG"
# set +e: com uma falha no download, o fim ainda precisa ir para o log
set +e
python baixar_dados.py --agravos DENG CHIK ZIKA --ufs RR --anos "$((ANO - 5))-$ANO" "$@" 2>&1 | tee -a "$LOG"
codigo=${PIPESTATUS[0]}
set -e
echo "== $(date '+%F %T') fim (código $codigo)" | tee -a "$LOG"
exit "$codigo"
