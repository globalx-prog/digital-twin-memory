# 📄 03. Dokumenten-Pipeline: Unterschiedliche Formate (PDF, DOCX, ODT, Scans) in Obsidian-Markdown umwandeln

> **Herausforderung:** Anwendungen wie **Obsidian** und lokale Sprachmodelle arbeiten am besten mit sauberem **Markdown (`.md`)**. Wenn du PDFs (Berichte, Rechnungen, Handbücher), Word-/LibreOffice-Dokumente (`.docx`, `.odt`), Präsentationen (`.pptx`) oder Tabellen (`.xlsx`, `.csv`) einliest, müssen Überschriften (`#`, `##`), Tabellen (`|...|`) und Listen erhalten bleiben – ohne dass die Formatierung zerbricht.

---

## 🛠️ 1. Die 4 besten lokalen Konverter im Vergleich (100 % Offline)

Für deine Linux-Workstation empfiehlt sich eine **mehrstufige Konverter-Kaskade** (in [`scripts/ingest_to_markdown.py`](file:///home/clemi/Projekte/LLM/digital-twin-memory/scripts/ingest_to_markdown.py) bereits genauso implementiert):

| Tool / Engine | Beste Formate | Geschwindigkeit | VRAM-Bedarf | Stärke |
| :--- | :--- | :---: | :---: | :--- |
| **1. `PyMuPDF4LLM`** *(Standard für PDF)* | Digitale PDFs (Berichte, Papers, Handbücher) | ⚡ Extrem schnell (~0,1 s / Seite) | **0 MB (CPU)** | Erkennt mehrspaltige PDF-Layouts, Überschriften und Markdown-Tabellen automatisch. |
| **2. `MarkItDown`** *(Microsoft Open-Source)* | `.docx`, `.pptx`, `.xlsx`, `.html`, `.epub`, `.zip` | ⚡ Sehr schnell | **0 MB (CPU)** | Speziell für LLMs entwickelt; wandelt Excel-Blätter und Word-Dokumente direkt in sauberes Markdown. |
| **3. `Pandoc` / XML-Parser** | `.odt` (LibreOffice), `.rtf`, `.tex`, `.rst` | ⚡ Sofort (<0,1 s) | **0 MB (CPU)** | Perfekt für deine lokalen `.odt`-Dokumente (wie `doku1.odt` im Hauptverzeichnis). |
| **4. `Docling` / `Marker` / Vision-LLM** *(Für Scans)* | Gescannte PDFs (Briefe, Bilder ohne Textschicht) | 🐢 Mittel (~1–2 s / Seite) | 0 MB (CPU-OCR) oder Ollama Vision | Nutzt OCR (Tesseract/EasyOCR) oder ein lokales Vision-Modell, um selbst abfotografierte Dokumente in Markdown zu verwandeln. |

---

## 🔄 2. Der automatische Ingest-Workflow (`00_inbox_raw` ➔ `01_fleeting_notes`)

So läuft die Umwandlung ab, sobald du eine Datei in `vault/00_inbox_raw/` legst oder `brain_cli.sh ingest <datei>` aufrufst:

```text
  [ Eingehende Datei: z. B. Finanzen_2026.pdf oder doku1.odt ]
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │  1. Dateityp- & Hash-Prüfung (SHA-256)  │ ──► Verhindert doppeltes Einlesen!
         └────────────────────┬────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   [ .pdf ]          [ .docx / .xlsx ]         [ .odt / .html ]
  PyMuPDF4LLM           MarkItDown           Pandoc / ODT-Extractor
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │  2. Markdown-Reinigung & Normalisierung │
         │  • Überflüssige Leerzeilen entfernen    │
         │  • Seitenumbrüche als Kommentar mark.   │
         └────────────────────┬────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │  3. Obsidian YAML-Frontmatter erzeugen  │
         │  • brain_layer: 1 (fleeting)            │
         │  • source_file, created_at, tags        │
         └────────────────────┬────────────────────┘
                              │
                              ▼
  [ Gespeichert in: vault/01_fleeting_notes/Finanzen_2026.md ]
  [ Automatisch indexiert in: configs/twin_memory.db (FTS5)  ]
```

---

## 💻 3. Weiterführende Guides (Befehle & Setup)

* **Tägliche Bedienung (Füttern, Abfragen, Befördern):** siehe 👉 [`06_PRAXIS_WORKFLOW_GEHIRN_FUETTERN_ABFRAGEN_UND_EBENE3.md`](06_PRAXIS_WORKFLOW_GEHIRN_FUETTERN_ABFRAGEN_UND_EBENE3.md)
* **Komplette Installation von Null:** siehe 👉 [`07_KOMPLETT_SETUP_VON_NULL_OPENWEBUI_UND_ZWEITES_GEHIRN.md`](07_KOMPLETT_SETUP_VON_NULL_OPENWEBUI_UND_ZWEITES_GEHIRN.md)
