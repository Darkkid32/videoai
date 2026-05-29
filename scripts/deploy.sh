#!/usr/bin/env bash
# deploy.sh — Deploy VideoAI to Anti-Gravity GPU instance
# Usage: ./scripts/deploy.sh root@<your-ip>
set -euo pipefail

HOST="${1:-}"
[[ -z "$HOST" ]] && { echo "Usage: $0 user@host"; exit 1; }

echo "=== VideoAI → Anti-Gravity Deploy ==="
echo "Host: $HOST"

echo ""
echo "→ Syncing codebase..."
rsync -avz --progress \
  --exclude node_modules \
  --exclude .git \
  --exclude model_cache \
  --exclude outputs \
  --exclude __pycache__ \
  --exclude "*.pyc" \
  ./ "$HOST:/workspace/videoai/"

echo ""
echo "→ Remote setup..."
ssh "$HOST" << 'REMOTE'
set -euo pipefail
cd /workspace/videoai

# Install Docker if needed
if ! command -v docker &>/dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

# NVIDIA container toolkit
if ! dpkg -l | grep -q nvidia-container-toolkit 2>/dev/null; then
  echo "Installing NVIDIA container toolkit..."
  distribution=$(. /etc/os-release; echo "$ID$VERSION_ID")
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L "https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list" | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update && apt-get install -y nvidia-container-toolkit
  systemctl restart docker
fi

# Create .env if not present
[[ -f .env ]] || cp .env.example .env

echo "→ Building images..."
docker compose build --parallel

echo "→ Starting stack..."
docker compose up -d

echo "→ Waiting for API..."
sleep 8
curl -s http://localhost:8000/health && echo ""

echo ""
echo "=== Deployed successfully ==="
docker compose ps
REMOTE

echo ""
echo "✅ VideoAI running on $HOST"
echo ""
echo "   Dashboard: http://$HOST:3000"
echo "   API:       http://$HOST:8000"
echo "   API Docs:  http://$HOST:8000/docs"
echo ""
echo "First time? Edit .env on server:"
echo "  ssh $HOST 'nano /workspace/videoai/.env'"
