#!/usr/bin/env bash
# ==============================================================================
# 01-install-standalone-deps.sh
# Richtet eine isolierte Python-Umgebung (.venv) für die Dokumenten-Konvertierung
# (PDF -> Markdown via PyMuPDF4LLM & MarkItDown) ein — 0 MB VRAM Verbrauch!
# ==============================================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
VENV_DIR="${PROJECT_DIR}/.venv"

echo "🧠 Richtet Standalone Digital-Twin Umgebung in ${VENV_DIR} ein..."

if command -v uv >/dev/null 2>&1; then
    uv venv "${VENV_DIR}"
    uv pip install --python "${VENV_DIR}/bin/python" pymupdf4llm pypdf markitdown pyyaml watchdog
else
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade pip
    "${VENV_DIR}/bin/pip" install pymupdf4llm pypdf markitdown pyyaml watchdog
fi

echo "✅ Installation abgeschlossen! Teste Status:"
"${PROJECT_DIR}/scripts/brain_cli.sh" status
