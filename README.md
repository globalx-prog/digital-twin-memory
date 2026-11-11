# 🧠 Digital Twin & 3-Ebenen-Gehirn (Obsidian + Lokales Gedächtnis)

> **Status:** 📦 Standalone-Blaupause & Referenz-Architektur (Alternative & Ergänzung zu `llm-optimierungen`)  
> **Hardware-Fokus:** AMD Radeon PRO W7800 (48 GB VRAM) | 0 MB VRAM Overhead für Dokumenten-Indexierung (CPU-FTS5 + CPU-Embeddings)  
> **Architektur-Standard:** 4-Säulen-NAS-Standard (`configs/`, `docs/`, `scripts/`, `setup/`) + integrierter Obsidian-Vault (`vault/`)

---

## 📍 1. Wo liegt dein aktuelles „Lokales Gedächtnis“?

In deinem bestehenden System (`agent-cli` + `llm-optimierungen`) existiert bereits ein **2-schichtiges Agenten-Gedächtnis** für Fakten und Systemregeln:

| Komponente | Physischer Pfad auf `clemi-pc` | Funktion & Zugriff |
| :--- | :--- | :--- |
| **1. SQLite-Datenbank** | [`/home/clemi/Projekte/LLM/agent-cli/configs/agent_memory.db`](file:///home/clemi/Projekte/LLM/agent-cli/configs/agent_memory.db) | Persistente Key-Value- & Volltext-Datenbank für Fakten, Ports, Architekturentscheidungen (`0 MB VRAM`). |
| **2. Markdown-Spiegel** | [`/home/clemi/Projekte/LLM/agent-cli/configs/MEMORY.md`](file:///home/clemi/Projekte/LLM/agent-cli/configs/MEMORY.md) | Menschenlesbare Tabelle, automatisch bei jedem Speichern synchronisiert und beim Start von `OpenCode` geladen. |
| **3. MCP-Server / Bridge** | [`/home/clemi/Projekte/LLM/agent-cli/scripts/mcp_memory_bridge.py`](file:///home/clemi/Projekte/LLM/agent-cli/scripts/mcp_memory_bridge.py) | Python-Backend (STDIO & CLI) mit den Tools `memory_save`, `memory_search`, `memory_list`, `memory_delete`. |
| **4. Terminal-CLI** | [`/home/clemi/Projekte/LLM/agent-cli/scripts/memory.sh`](file:///home/clemi/Projekte/LLM/agent-cli/scripts/memory.sh) | Direkter Terminal-Befehl (`memory.sh list`, `add`, `search`). |
| **5. OpenAPI-Gateway** | [`/home/clemi/Projekte/LLM/llm-optimierungen/docker-compose.mcpo.yml`](file:///home/clemi/Projekte/LLM/llm-optimierungen/docker-compose.mcpo.yml) | Stellt `agent-memory` auf Port `9000` (`http://mcpo:9000/agent-memory`) für **Open WebUI** bereit. |
| **6. Dokumentation** | [`/home/clemi/Projekte/LLM/docs/LOKALES_GEDAECHTNIS_UND_DEFAULT_CONFIG.md`](file:///home/clemi/Projekte/LLM/docs/LOKALES_GEDAECHTNIS_UND_DEFAULT_CONFIG.md) | Handbuch zur aktuellen Funktionsweise des Agenten-Gedächtnisses. |

### Warum reicht das bisherige Gedächtnis nicht für ein Dokumenten-System / Obsidian?
Das bisherige `agent_memory.db` ist als **kompaktes Regel- & Fakten-Gedächtnis** (10–40 kurze Einträge) konzipiert. Für einen echten **Digitalen Zwilling (Second Brain)** mit hunderten PDFs, DOCX-Dateien, E-Books und mehrstufigen Obsidian-Notizen braucht es eine **eigene Dokumenten-Pipeline + 3-Ebenen-Wissensarchitektur** – genau das setzt dieses Standalone-Projekt (`digital-twin-memory`) um.

---

## 🏛️ 2. Die 3-Stufige Gehirn-Architektur (Obsidian Zettelkasten + KI)

Alle eingelesenen Dokumente durchlaufen nach der Konvertierung in Markdown (`00_inbox_raw` ➔ `.md`) drei klar getrennte kognitive Ebenen im Ordner [`vault/`](file:///home/clemi/Projekte/LLM/digital-twin-memory/vault):

```text
  [ PDF / DOCX / ODT / PPTX / XLSX / HTML / Audio ]
                         │
                         ▼ (Ingest: Docling / MarkItDown / Pandoc)
         ┌───────────────────────────────┐
         │    vault/00_inbox_raw/        │  (Roh-Dateien & Archiv)
         └───────────────┬───────────────┘
                         │ Automatische Konvertierung + YAML-Frontmatter
                         ▼
  ╔══════════════════════════════════════════════════════════════════════╗
  ║ EBENE 1: vault/01_fleeting_notes/ (Sensorisches / Kurzzeit-Gehirn)   ║
  ║ • 1:1 konvertierte Markdown-Dokumente, schnelle Notizen, Diktate     ║
  ║ • Status: "unprocessed" | KI-Aufgabe: OCR-Reinigung & Auto-Tagging   ║
  ╚══════════════════════╤═══════════════════════════════════════════════╝
                         │ KI-Synthese & Exzerpt-Extraktion (`promote_note`)
                         ▼
  ╔══════════════════════════════════════════════════════════════════════╗
  ║ EBENE 2: vault/02_literature_notes/ (Arbeitsgedächtnis / Kontext)    ║
  ║ • Strukturierte Zusammenfassungen, Kernaussagen, Zitate, Fakten      ║
  ║ • Mit Quelle verknüpft (`source: [[01_fleeting_notes/...]]`)         ║
  ║ • Status: "summarized" | KI-Aufgabe: Querverbindungen vorschlagen    ║
  ╚══════════════════════╤═══════════════════════════════════════════════╝
                         │ Destillation & Vernetzung (`distill_knowledge`)
                         ▼
  ╔══════════════════════════════════════════════════════════════════════╗
  ║ EBENE 3: vault/03_permanent_brain/ (Langzeitgedächtnis / Zwilling)   ║
  ║ • Atomare Konzepte, eigenes Wissen, Entscheidungen, Projekte (MOCs)  ║
  ║ • Dichtes WikiLink-Netzwerk (`[[Konzept-A]]` <-> `[[Konzept-B]]`)    ║
  ║ • Status: "evergreen" | Höchste Priorität bei KI-Abfragen!           ║
  ╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📂 3. Projekt-Struktur (NAS-Standard)

```text
digital-twin-memory/
├── README.md                                 # Übersicht, Schnellstart & Architektur
├── docker-compose.standalone.yml             # Eigenständiger Stack (Converter + MCP + Vector/FTS)
├── configs/
│   ├── twin-config.yaml                      # Ebenen-Gewichtung, Parser-Regeln & Modelle
│   └── mcp-obsidian-twin.json                # MCP-Konfiguration für OpenCode, Goose & Open WebUI
├── docs/
│   ├── 01_BESTANDSANALYSE_WO_LIEGT_DAS_GEDAECHTNIS.md
│   ├── 02_ARCHITEKTUR_3_EBENEN_OBSIDIAN_GEHIRN.md
│   ├── 03_DOKUMENTEN_PIPELINE_PDF_ZU_MARKDOWN.md
│   └── 04_STANDALONE_VERGLEICH_VS_LLM_OPTIMIERUNGEN.md
├── scripts/
│   ├── ingest_to_markdown.py                 # Konvertiert PDF/DOCX/ODT -> Ebene 1 (.md + Frontmatter)
│   ├── mcp_obsidian_twin.py                  # MCP-Server für 3-Ebenen-Suche & KI-Bearbeitung
│   └── brain_cli.sh                          # Terminal-Steuerung (ingest, search, promote, status)
├── setup/
│   └── 01-install-standalone-deps.sh         # Installiert Python-Venv (markitdown, pymupdf4llm, sqlite-vec)
└── vault/                                    # Dein Obsidian-Vault (direkt in Obsidian öffnen!)
    ├── 00_inbox_raw/                         # Drop-Ordner für PDFs, Word, ODT, Scans
    ├── 01_fleeting_notes/                    # Ebene 1: Konvertierte Roh-Markdown-Dokumente
    ├── 02_literature_notes/                  # Ebene 2: KI-kuratierte Exzerpte & Literatur-Notizen
    ├── 03_permanent_brain/                   # Ebene 3: Atomares Kernwissen & Digitaler Zwilling
    └── 99_templates/                         # YAML-Frontmatter & Obsidian-Templates
```

---

## ⚡ 4. Schnellstart (In 3 Schritten einsatzbereit)

```bash
# 1. Abhängigkeiten in isolierter Virtualenv installieren (0 MB VRAM Overhead):
./setup/01-install-standalone-deps.sh

# 2. Beliebige Dokumente (z. B. PDF, ODT, DOCX) in Ebene 1 einlesen & umwandeln:
./scripts/brain_cli.sh ingest /home/clemi/Projekte/LLM/doku1.odt

# 3. Das 3-Ebenen-Gehirn per CLI oder MCP durchsuchen:
./scripts/brain_cli.sh search "ROCm"
./scripts/brain_cli.sh status
```

---

## 📚 5. Weiterführende Dokumentation in `docs/`

1. [**01_BESTANDSANALYSE_WO_LIEGT_DAS_GEDAECHTNIS.md**](docs/01_BESTANDSANALYSE_WO_LIEGT_DAS_GEDAECHTNIS.md) — Exakte Karte aller bisherigen Gedächtnis-Dateien und Aufwandsschätzung für den Ausbau.
2. [**02_ARCHITEKTUR_3_EBENEN_OBSIDIAN_GEHIRN.md**](docs/02_ARCHITEKTUR_3_EBENEN_OBSIDIAN_GEHIRN.md) — Detailliertes Konzept der 3 Gehirn-Ebenen, Frontmatter-Metadaten, WikiLinks und KI-Interaktion.
3. [**03_DOKUMENTEN_PIPELINE_PDF_ZU_MARKDOWN.md**](docs/03_DOKUMENTEN_PIPELINE_PDF_ZU_MARKDOWN.md) — Vergleich und Konfiguration der besten lokalen Konverter (PyMuPDF4LLM, Docling, MarkItDown, Pandoc, Whisper).
4. [**04_STANDALONE_VERGLEICH_VS_LLM_OPTIMIERUNGEN.md**](docs/04_STANDALONE_VERGLEICH_VS_LLM_OPTIMIERUNGEN.md) — Direktvergleich: `llm-optimierungen` (System- & Speed-Tuning) vs. `digital-twin-memory` (Standalone Wissens- & Dokumenten-System).
5. [**05_PROBLEME_DATEIWANDLUNG_UND_SETUP_VON_NULL_16GB.md**](docs/05_PROBLEME_DATEIWANDLUNG_UND_SETUP_VON_NULL_16GB.md) — Die 7 häufigsten Probleme bei der PDF/Office-zu-Markdown-Wandlung (+ Lösungen).
6. [**06_PRAXIS_WORKFLOW_GEHIRN_FUETTERN_ABFRAGEN_UND_EBENE3.md**](docs/06_PRAXIS_WORKFLOW_GEHIRN_FUETTERN_ABFRAGEN_UND_EBENE3.md) — Schritt-für-Schritt-Praxisanleitung: Füttern, Abfragen, mit KI bearbeiten und Dokumente für Ebene 3 („Permanent Brain“) freigeben.
7. [**07_KOMPLETT_SETUP_VON_NULL_OPENWEBUI_UND_ZWEITES_GEHIRN.md**](docs/07_KOMPLETT_SETUP_VON_NULL_OPENWEBUI_UND_ZWEITES_GEHIRN.md) — Einzige zentrale Installationsanleitung von Null: Teil 1 (Basis: Ollama + Obsidian) & Teil 2 (Erweiterung: Open WebUI + `mcpo` + SearXNG).
8. [**08_ANWENDUNGSFAELLE_STUDIUM_JOB_UND_DOKU_INTEGRATION.md**](docs/08_ANWENDUNGSFAELLE_STUDIUM_JOB_UND_DOKU_INTEGRATION.md) — Konkrete Anwendungsfälle für Studium & Beruf sowie die redundanzfreie Symlink-Integration deiner bestehenden LLM-Dokumentationen in Ebene 3.
