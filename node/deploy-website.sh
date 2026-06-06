#!/bin/bash
# node/deploy-website.sh
#
# Deploy (or update) the sample website stack on a Swarm manager node.
# Baked into the image at /usr/local/bin/deploy-website.
# Safe to run more than once — docker stack deploy is idempotent.

set -euo pipefail

STACK_FILE="/opt/meshnode-stacks/website-example.yml"
STACK_NAME="website"

# ── Pre-flight checks ─────────────────────────────────────────────────────────

if [ "$(id -u)" -ne 0 ]; then
    echo "!! This script must be run as root." >&2
    exit 1
fi

SWARM_STATE=$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo "error")
if [ "${SWARM_STATE}" != "active" ]; then
    echo "!! Docker Swarm is not active (state: ${SWARM_STATE})." >&2
    echo "!! Complete the meshnode setup wizard first." >&2
    exit 1
fi

NODE_ROLE=$(docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null || echo "false")
if [ "${NODE_ROLE}" != "true" ]; then
    echo "!! This node is not a Swarm manager." >&2
    echo "!! Run this script on the manager node." >&2
    exit 1
fi

if [ ! -f "${STACK_FILE}" ]; then
    echo "!! Stack file not found: ${STACK_FILE}" >&2
    exit 1
fi

# ── Deploy ────────────────────────────────────────────────────────────────────

echo ">> Deploying '${STACK_NAME}' stack from ${STACK_FILE}..."
docker stack deploy --compose-file "${STACK_FILE}" "${STACK_NAME}"

echo ""
echo ">> Waiting 6 s for replicas to schedule..."
sleep 6

echo ">> Service status:"
docker stack services "${STACK_NAME}"

# ── Print access info ─────────────────────────────────────────────────────────

echo ""
MESH_IP=$(grep -oP '(?<=mesh_ip: ).*' /etc/meshnode/config.yaml 2>/dev/null \
          || hostname -I | awk '{print $1}')
echo ">> Website is reachable at: http://${MESH_IP}/"
echo ">> Each response shows which container (node) served the request."
echo ">> Run the failover test: see docs/failover-test.md"
