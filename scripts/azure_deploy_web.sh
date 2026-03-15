#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RG="${RG:-school-admin-demo-rg}"
LOCATION="${LOCATION:-japaneast}"
LOG_WORKSPACE="${LOG_WORKSPACE:-school-admin-demo-logs}"
CONTAINER_ENV="${CONTAINER_ENV:-school-admin-demo-env}"
CONTAINER_ENV_RG="${CONTAINER_ENV_RG:-$RG}"
FALLBACK_CONTAINER_ENV_RG="${FALLBACK_CONTAINER_ENV_RG:-sit-copilot}"
FALLBACK_CONTAINER_ENV="${FALLBACK_CONTAINER_ENV:-sit-copilot-env}"
ACR_NAME="${ACR_NAME:-schooladmindemoacr23088}"
CONTAINER_APP="${CONTAINER_APP:-school-admin-demo-api}"
IMAGE_NAME="${IMAGE_NAME:-school-admin-api}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
VISION_RG="${VISION_RG:-school-admin-precheck-rg}"
VISION_ACCOUNT="${VISION_ACCOUNT:-schooladminocr23088}"
AOAI_RG="${AOAI_RG:-sit-copilot}"
AOAI_ACCOUNT="${AOAI_ACCOUNT:-sitcopilotaoai23088}"
AOAI_DEPLOYMENT="${AOAI_DEPLOYMENT:-sit-copilot-demo-chat}"
API_VERSION="${API_VERSION:-2024-10-21}"

command -v az >/dev/null 2>&1 || { echo "az CLI が見つかりません。" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker が見つかりません。" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 が見つかりません。" >&2; exit 1; }

az account show >/dev/null

echo "[1/7] resource group"
az group create -n "$RG" -l "$LOCATION" >/dev/null

echo "[2/7] log analytics"
az monitor log-analytics workspace create -g "$RG" -n "$LOG_WORKSPACE" -l "$LOCATION" >/dev/null
LOG_WORKSPACE_ID="$(az monitor log-analytics workspace show -g "$RG" -n "$LOG_WORKSPACE" --query customerId -o tsv)"
LOG_WORKSPACE_KEY="$(az monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LOG_WORKSPACE" --query primarySharedKey -o tsv)"

echo "[3/7] container apps environment"
if ! az containerapp env show -g "$CONTAINER_ENV_RG" -n "$CONTAINER_ENV" >/dev/null 2>&1; then
  if ! az containerapp env create \
    -g "$CONTAINER_ENV_RG" \
    -n "$CONTAINER_ENV" \
    -l "$LOCATION" \
    --logs-workspace-id "$LOG_WORKSPACE_ID" \
    --logs-workspace-key "$LOG_WORKSPACE_KEY" >/dev/null; then
    CONTAINER_ENV_RG="$FALLBACK_CONTAINER_ENV_RG"
    CONTAINER_ENV="$FALLBACK_CONTAINER_ENV"
  fi
fi
az containerapp env show -g "$CONTAINER_ENV_RG" -n "$CONTAINER_ENV" >/dev/null

echo "[4/7] registry"
az acr create -g "$RG" -n "$ACR_NAME" -l "$LOCATION" --sku Basic --admin-enabled true >/dev/null 2>&1 || true
ACR_SERVER="$(az acr show -g "$RG" -n "$ACR_NAME" --query loginServer -o tsv)"
ACR_USER="$(az acr credential show -g "$RG" -n "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show -g "$RG" -n "$ACR_NAME" --query 'passwords[0].value' -o tsv)"

echo "[5/7] app image build"
az acr login -n "$ACR_NAME" >/dev/null
(cd "$ROOT_DIR/frontend" && VITE_API_BASE= npm run build >/dev/null)
docker build --network host -f "$ROOT_DIR/backend/Dockerfile" -t "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" "$ROOT_DIR" >/dev/null
docker push "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" >/dev/null

VISION_KEY="$(az cognitiveservices account keys list -g "$VISION_RG" -n "$VISION_ACCOUNT" --query key1 -o tsv)"
AOAI_KEY="$(az cognitiveservices account keys list -g "$AOAI_RG" -n "$AOAI_ACCOUNT" --query key1 -o tsv)"

echo "[6/7] container app"
ENV_ID="$(az containerapp env show -g "$CONTAINER_ENV_RG" -n "$CONTAINER_ENV" --query id -o tsv)"
TMP_YAML="$(mktemp)"
export ENV_ID ACR_SERVER ACR_USER ACR_PASS VISION_KEY AOAI_KEY CONTAINER_APP IMAGE_NAME IMAGE_TAG AOAI_DEPLOYMENT API_VERSION
python3 - <<'PY' >"$TMP_YAML"
import json
import os

payload = {
    "location": "Japan East",
    "name": os.environ["CONTAINER_APP"],
    "type": "Microsoft.App/containerApps",
    "properties": {
        "managedEnvironmentId": os.environ["ENV_ID"],
        "configuration": {
            "activeRevisionsMode": "Single",
            "ingress": {
                "external": True,
                "targetPort": 8000,
                "transport": "auto",
                "allowInsecure": False,
            },
            "registries": [{
                "server": os.environ["ACR_SERVER"],
                "username": os.environ["ACR_USER"],
                "passwordSecretRef": "acr-password",
            }],
            "secrets": [
                {"name": "acr-password", "value": os.environ["ACR_PASS"]},
                {"name": "azure-vision-key", "value": os.environ["VISION_KEY"]},
                {"name": "azure-openai-key", "value": os.environ["AOAI_KEY"]},
            ],
        },
        "template": {
            "containers": [{
                "name": os.environ["CONTAINER_APP"],
                "image": f"{os.environ['ACR_SERVER']}/{os.environ['IMAGE_NAME']}:{os.environ['IMAGE_TAG']}",
                "env": [
                    {"name": "APP_DATA_DIR", "value": "/app/data"},
                    {"name": "FRONTEND_DIST_DIR", "value": "/app/frontend_dist"},
                    {"name": "AZURE_VISION_ENDPOINT", "value": "https://japaneast.api.cognitive.microsoft.com/"},
                    {"name": "AZURE_VISION_KEY", "secretRef": "azure-vision-key"},
                    {"name": "AZURE_OPENAI_ENDPOINT", "value": "https://japaneast.api.cognitive.microsoft.com/"},
                    {"name": "AZURE_OPENAI_KEY", "secretRef": "azure-openai-key"},
                    {"name": "AZURE_OPENAI_DEPLOYMENT", "value": os.environ["AOAI_DEPLOYMENT"]},
                    {"name": "AZURE_OPENAI_API_VERSION", "value": os.environ["API_VERSION"]},
                    {"name": "AZURE_ANALYSIS_LIVE_ENABLED", "value": "true"},
                ],
                "resources": {"cpu": 0.5, "memory": "1Gi"},
            }],
            "scale": {"minReplicas": 0, "maxReplicas": 1},
        },
    },
}

print(json.dumps(payload))
PY

if az containerapp show -g "$RG" -n "$CONTAINER_APP" >/dev/null 2>&1; then
  az containerapp update -g "$RG" -n "$CONTAINER_APP" --yaml "$TMP_YAML" >/dev/null
else
  az containerapp create -g "$RG" -n "$CONTAINER_APP" --yaml "$TMP_YAML" >/dev/null
fi
rm -f "$TMP_YAML"

API_URL="https://$(az containerapp show -g "$RG" -n "$CONTAINER_APP" --query 'properties.configuration.ingress.fqdn' -o tsv)"
WEB_URL="$API_URL"

echo "[7/7] smoke URL ready"
az containerapp show -g "$RG" -n "$CONTAINER_APP" --query 'properties.runningStatus' -o tsv >/dev/null

echo
echo "API_URL=$API_URL"
echo "WEB_URL=$WEB_URL"
