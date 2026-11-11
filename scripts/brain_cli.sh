#!/usr/bin/env bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
VENV_PY="${PROJECT_DIR}/.venv/bin/python3"

if [[ -x "${VENV_PY}" ]]; then
    PY_BIN="${VENV_PY}"
else
    PY_BIN="python3"
fi

CMD="${1:-status}"
shift || true

case "${CMD}" in
    ingest-all)
        exec "${PY_BIN}" "${SCRIPT_DIR}/mcp_obsidian_twin.py" --cli ingest "${PROJECT_DIR}/vault/00_inbox_raw"
        ;;
    ingest|search|write|read|promote|status)
        exec "${PY_BIN}" "${SCRIPT_DIR}/mcp_obsidian_twin.py" --cli "${CMD}" "$@"
        ;;
    *)
        echo "Verwendung: $0 {status|ingest <datei>|ingest-all|search <begriff> [--layer 1|2|3]|read <pfad>|write <titel> <inhalt> [--layer 1|2|3]|promote <quellpfad> --to-layer 2|3 [--model <name>]}"
        exit 1
        ;;
esac
