#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_FILE="${1:-$ROOT_DIR/.env.local}"

VISION_RG="${VISION_RG:-school-admin-precheck-rg}"
VISION_ACCOUNT="${VISION_ACCOUNT:-schooladminocr23088}"
AOAI_RG="${AOAI_RG:-sit-copilot}"
AOAI_ACCOUNT="${AOAI_ACCOUNT:-sitcopilotaoai23088}"

command -v az >/dev/null 2>&1 || { echo "az CLI が見つかりません。" >&2; exit 1; }
az account show >/dev/null

VISION_KEY="$(az cognitiveservices account keys list -g "$VISION_RG" -n "$VISION_ACCOUNT" --query key1 -o tsv)"
AOAI_KEY="$(az cognitiveservices account keys list -g "$AOAI_RG" -n "$AOAI_ACCOUNT" --query key1 -o tsv)"

umask 077
cat >"$TARGET_FILE" <<EOF
AZURE_VISION_ENDPOINT=https://japaneast.api.cognitive.microsoft.com/
AZURE_VISION_KEY=$VISION_KEY
AZURE_OPENAI_ENDPOINT=https://japaneast.api.cognitive.microsoft.com/
AZURE_OPENAI_KEY=$AOAI_KEY
AZURE_OPENAI_DEPLOYMENT=sit-copilot-demo-chat
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_ANALYSIS_LIVE_ENABLED=true
APP_DATA_DIR=$ROOT_DIR/data
DEMO_MODE_DEFAULT=live
EOF

echo "Wrote local live env: $TARGET_FILE"
