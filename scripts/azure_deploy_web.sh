#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RG="${RG:-school-admin-demo-rg}"
ACR_NAME="${ACR_NAME:-schooladmindemoacr23088}"
CONTAINER_APP="${CONTAINER_APP:-school-admin-demo-api}"
IMAGE_NAME="${IMAGE_NAME:-school-admin-api}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
CONTAINER_ENV_RG="${CONTAINER_ENV_RG:-sit-copilot}"
CONTAINER_ENV="${CONTAINER_ENV:-sit-copilot-env}"

command -v az >/dev/null 2>&1 || { echo "az CLI が見つかりません。" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker が見つかりません。" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm が見つかりません。" >&2; exit 1; }

az account show >/dev/null

echo "[1/4] verify target resources"
az group show -n "$RG" >/dev/null
az containerapp env show -g "$CONTAINER_ENV_RG" -n "$CONTAINER_ENV" >/dev/null

echo "[2/4] build frontend and container image"
az acr login -n "$ACR_NAME" >/dev/null
(cd "$ROOT_DIR/frontend" && npm run build >/dev/null)

ACR_SERVER="$(az acr show -g "$RG" -n "$ACR_NAME" --query loginServer -o tsv)"
ACR_USER="$(az acr credential show -g "$RG" -n "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show -g "$RG" -n "$ACR_NAME" --query 'passwords[0].value' -o tsv)"
docker build --network host -f "$ROOT_DIR/backend/Dockerfile" -t "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" "$ROOT_DIR" >/dev/null
docker push "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" >/dev/null

echo "[3/4] update container app"
ENV_ID="$(az containerapp env show -g "$CONTAINER_ENV_RG" -n "$CONTAINER_ENV" --query id -o tsv)"
TMP_YAML="$(mktemp)"
cat >"$TMP_YAML" <<EOF
{
  "location": "Japan East",
  "name": "${CONTAINER_APP}",
  "type": "Microsoft.App/containerApps",
  "properties": {
    "managedEnvironmentId": "${ENV_ID}",
    "configuration": {
      "activeRevisionsMode": "Single",
      "ingress": {
        "external": true,
        "targetPort": 8000,
        "transport": "auto",
        "allowInsecure": false
      },
      "registries": [
        {
          "server": "${ACR_SERVER}",
          "username": "${ACR_USER}",
          "passwordSecretRef": "acr-password"
        }
      ],
      "secrets": [
        {
          "name": "acr-password",
          "value": "${ACR_PASS}"
        }
      ]
    },
    "template": {
      "containers": [
        {
          "name": "${CONTAINER_APP}",
          "image": "${ACR_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}",
          "env": [
            { "name": "APP_DATA_DIR", "value": "/app/data" },
            { "name": "FRONTEND_DIST_DIR", "value": "/app/frontend_dist" },
            { "name": "DEMO_SUSPENDED", "value": "true" }
          ],
          "resources": {
            "cpu": 0.25,
            "memory": "0.5Gi"
          }
        }
      ],
      "scale": {
        "minReplicas": 0,
        "maxReplicas": 1
      }
    }
  }
}
EOF

az containerapp update -g "$RG" -n "$CONTAINER_APP" --yaml "$TMP_YAML" >/dev/null
rm -f "$TMP_YAML"

API_URL="https://$(az containerapp show -g "$RG" -n "$CONTAINER_APP" --query 'properties.configuration.ingress.fqdn' -o tsv)"
WEB_URL="$API_URL"

echo "[4/4] smoke URL ready"
az containerapp show -g "$RG" -n "$CONTAINER_APP" --query 'properties.runningStatus' -o tsv >/dev/null

echo
echo "API_URL=$API_URL"
echo "WEB_URL=$WEB_URL"
