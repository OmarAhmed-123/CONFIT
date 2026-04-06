#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PentAGI Startup Script for CONFIT Security
# ═══════════════════════════════════════════════════════════════════════════════
# This script starts PentAGI services with proper configuration

set -e

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "Starting PentAGI AI Penetration Testing Platform"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")/../../backend"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[ERROR] .env file not found in backend directory"
    echo "Please copy .env.example to .env and configure the required variables:"
    echo "  - DEEPSEEK_API_KEY"
    echo "  - PENTAGI_API_TOKEN"
    echo "  - SHODAN_API_KEY (optional)"
    echo "  - VIRUSTOTAL_API_KEY (optional)"
    exit 1
fi

echo "[INFO] Starting PentAGI services..."
echo ""

# Start only PentAGI-related services
docker compose up -d pentagi-pgvector pentagi pentagi-worker

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to start PentAGI services"
    echo "Check Docker logs: docker compose logs pentagi"
    exit 1
fi

echo ""
echo "[SUCCESS] PentAGI services started"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "PentAGI is now running at: https://localhost:8443"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "To view logs:     docker compose logs -f pentagi"
echo "To stop services: docker compose down pentagi pentagi-worker pentagi-pgvector"
echo ""
