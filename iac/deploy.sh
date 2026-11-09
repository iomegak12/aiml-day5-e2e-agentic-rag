#!/usr/bin/env bash
# Runs on the EC2 instance (as root, from the Terraform provisioner): deploy.sh <hub_user> <app_version>
# Installs the uploaded files into /opt/netcore, restores Chroma on the first deploy, pulls and starts the stack.
set -euo pipefail

HUB_USER="${1:?hub user}"
APP_VERSION="${2:?app version}"
SRC=/tmp/netcore
APP=/opt/netcore
cd "$SRC"
trap 'rm -rf "$SRC"' EXIT # the upload contains secrets: never leave it in /tmp

install -d -o ubuntu -g ubuntu -m 0750 "$APP"
install -o ubuntu -g ubuntu -m 0600 app.env "$APP/.env"
install -o ubuntu -g ubuntu -m 0644 compose.prod.yaml "$APP/compose.yaml"
printf 'HUB_USER=%s\nAPP_VERSION=%s\n' "$HUB_USER" "$APP_VERSION" > "$APP/release.env"
chown ubuntu:ubuntu "$APP/release.env"

cd "$APP"
compose() { docker compose --env-file .env --env-file release.env "$@"; }

echo "==> pulling ${HUB_USER}/netcore-rag-*:${APP_VERSION} and the infrastructure images"
compose pull --quiet

# Create volumes and containers without starting them, so the Chroma volume exists for the restore.
compose up --no-start
VOLUME="netcore-rag_chroma-data"
if [ -z "$(docker run --rm -v "$VOLUME":/data alpine:3 ls -A /data)" ]; then
  if [ -s "$SRC/chroma-data.tgz" ]; then
    echo "==> restoring the knowledge base into $VOLUME"
    docker run --rm -v "$VOLUME":/data -v "$SRC":/backup:ro alpine:3 tar xzf /backup/chroma-data.tgz -C /data
  else
    echo "==> WARNING: no Chroma snapshot uploaded; the knowledge base is empty"
  fi
else
  echo "==> $VOLUME already has data: kept (delete the volume to restore the snapshot again)"
fi

echo "==> starting the stack"
compose up -d --wait --wait-timeout 420
compose ps --format 'table {{.Service}}\t{{.Status}}'
docker image prune -f > /dev/null
echo "==> deployed ${APP_VERSION}"
