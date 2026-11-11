#!/usr/bin/env bash
# ==============================================================================
# link_existing_llm_docs.sh
# Bindet alle bestehenden, verifizierten Markdown-Dokumentationen aus dem
# /home/clemi/Projekte/LLM Workspace ohne Duplikate (per Symlink + MOC)
# direkt in Ebene 3 (03_permanent_brain) des Obsidian-Vaults ein.
# ==============================================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
LLM_ROOT="/home/clemi/Projekte/LLM"
LAYER3_DIR="${PROJECT_DIR}/vault/03_permanent_brain"
ECO_DIR="${LAYER3_DIR}/llm_ecosystem"

mkdir -p "${ECO_DIR}"

echo "🔗 Verknüpfe bestehende LLM-Dokumentationen per Symlink nach Ebene 3 (${ECO_DIR})..."

ln -sfn "${LLM_ROOT}/agent-cli/docs"         "${ECO_DIR}/agent-cli"
ln -sfn "${LLM_ROOT}/llm-optimierungen/docs" "${ECO_DIR}/llm-optimierungen"
ln -sfn "${LLM_ROOT}/image-video-setup/docs" "${ECO_DIR}/image-video-setup"
ln -sfn "${LLM_ROOT}/ollama-zugriff/docs"    "${ECO_DIR}/ollama-zugriff"

# Zentrale Map of Content (MOC) für Obsidian Graph View erzeugen
NOW="$(date '+%Y-%m-%d %H:%M')"
cat << EOF > "${LAYER3_DIR}/MOC_LLM_Gesamtsystem.md"
---
id: "moc-llm-gesamtsystem"
title: "MOC: Lokales KI- & LLM-Ökosystem (W7800)"
brain_layer: 3
layer_name: "permanent"
status: "evergreen"
tags:
  - "brain/layer3"
  - "moc"
  - "arbeit/ki-workstation"
created_at: "${NOW}"
updated_at: "${NOW}"
---

# 🗺️ Map of Content (MOC): Lokales KI- & LLM-Ökosystem

> **Rolle in Ebene 3 (Permanent Brain):** Zentraler Knotenpunkt (Index) für alle bestehenden, verifizierten System-Handbücher aus \`/home/clemi/Projekte/LLM/\`.  
> Durch die Symlink-Architektur unter \`03_permanent_brain/llm_ecosystem/\` sind alle Original-Dokumente **ohne Kopieren live synchronisiert** und erhalten bei KI-Abfragen automatisch die **höchste Priorität (Gewicht 3.5x)**.

---

## 🤖 1. Multi-Agenten-System & CLI (\`agent-cli\`)
* [[03_permanent_brain/llm_ecosystem/agent-cli/01_ARCHITEKTUR_UND_TOOL_INTERAKTION|01. Architektur & Tool-Interaktion]]
* [[03_permanent_brain/llm_ecosystem/agent-cli/02_HARDWARE_UND_VRAM_STRATEGIE_W7800|02. Hardware & VRAM-Strategie W7800 (48 GB)]]
* [[03_permanent_brain/llm_ecosystem/agent-cli/06_PRAXIS_LEITFADEN_GROSSE_PROJEKTE_UND_BEDIENUNG|06. Praxis-Leitfaden für große Projekte]]
* [[03_permanent_brain/llm_ecosystem/agent-cli/08_KOMPLETTHANDBUCH_WORKFLOWS_MODELLE_UND_ERWEITERUNGEN|08. Kompletthandbuch Workflows & Modelle]]
* [[03_permanent_brain/llm_ecosystem/agent-cli/10_LOKALES_GEDAECHTNIS_UND_DEFAULT_CONFIG|10. Bisheriges Agenten-Gedächtnis & Default-Config]]
* [[03_permanent_brain/llm_ecosystem/agent-cli/11_SYSTEM_LANDKARTE_UND_TOOL_MATRIX|11. System-Landkarte & Tool-Matrix]]

## ⚙️ 2. LLM-Tuning, Speedup & Gateways (\`llm-optimierungen\`)
* [[03_permanent_brain/llm_ecosystem/llm-optimierungen/MODELL_UEBERSICHT_UND_BEWERTUNG|Modell-Übersicht & Master-Benchmark]]
* [[03_permanent_brain/llm_ecosystem/llm-optimierungen/SYSTEM_TUNING_SWAP_UND_STABILITAET|System-Tuning, Swap & ROCm-Stabilität]]
* [[03_permanent_brain/llm_ecosystem/llm-optimierungen/vram-und-modell-leitfaden|VRAM- & Modell-Leitfaden (41-GiB-Grenze)]]
* [[03_permanent_brain/llm_ecosystem/llm-optimierungen/mcpo-gateway-handbuch|mcpo Gateway & OpenAPI-Tools Handbuch]]
* [[03_permanent_brain/llm_ecosystem/llm-optimierungen/git-hooks-anleitung|Git-Hooks & Code-Qualität]]

## 🎨 3. Bild- & Video-Studio (\`image-video-setup\`)
* [[03_permanent_brain/llm_ecosystem/image-video-setup/handbuch-bild-und-video-ki|Gesamthandbuch Bild- & Video-KI (ComfyUI)]]
* [[03_permanent_brain/llm_ecosystem/image-video-setup/speicher-und-workflow-guide|Speicher- & Workflow-Guide (Wan 2.2 / MiniMax)]]
* [[03_permanent_brain/llm_ecosystem/image-video-setup/sicherheitsguide-ollama-comfyui|Sicherheitsguide Ollama + ComfyUI Koexistenz]]

## 🌐 4. Web-Stack & Remote-Zugriff (\`ollama-zugriff\`)
* [[03_permanent_brain/llm_ecosystem/ollama-zugriff/OPEN_WEBUI_BILDGENERIERUNG_UND_MODELL_KOMBINATIONEN|Open WebUI Setup & Modell-Kombinationen]]
* [[03_permanent_brain/llm_ecosystem/ollama-zugriff/cloudflare-tunnel-und-sicherheit|Cloudflare Zero Trust Tunnel & Sicherheit]]
EOF

echo "✅ MOC_LLM_Gesamtsystem.md erstellt. Aktualisiere SQLite-FTS5 Index..."
"${PROJECT_DIR}/scripts/brain_cli.sh" status
