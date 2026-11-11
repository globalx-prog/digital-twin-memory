# ⚠️ 05. Die 7 häufigsten Probleme beim Wandeln nach Markdown (`.md`) & ihre Lösungen

> **Ziel:** Welche typischen Stolpersteine treten beim Umwandeln von PDFs, Scans und Office-Dokumenten nach Markdown (`.md`) auf – und wie löst unsere Pipeline sie?  
> *(Für die vollständige Schritt-für-Schritt-Installationsanleitung von Null siehe 👉 **[`07_KOMPLETT_SETUP_VON_NULL_OPENWEBUI_UND_ZWEITES_GEHIRN.md`](07_KOMPLETT_SETUP_VON_NULL_OPENWEBUI_UND_ZWEITES_GEHIRN.md)**).*

---

## 🔍 Problem- & Lösungs-Matrix bei der Format-Konvertierung

Markdown ist ein **lineares, reines Textformat**, während PDFs, Word-Dateien und Excel-Tabellen **visuelle 2D-Layouts** sind. Beim Konvertieren für Obsidian und lokale LLMs treten in der Praxis vor allem diese 7 Probleme auf:

| # | Problem beim Konvertieren | Auswirkung auf Obsidian & KI | Praktische Lösung im Projekt |
| :-: | :--- | :--- | :--- |
| **1** | **Mehrspaltiges PDF-Layout** *(Zeitungen, wissenschaftliche Papers, 2-Spalten-Berichte)* | Einfache Parser (`pdftotext`) lesen zeilenweise von links nach rechts über beide Spalten hinweg ➔ Sätze werden sinnlos ineinandergewürfelt. | **`PyMuPDF4LLM` oder `Docling` nutzen:** Diese erkennen Textblöcke (Bounding Boxes) geometrisch und lesen erst Spalte 1 komplett, dann Spalte 2. |
| **2** | **Gescannte PDFs ohne Textschicht** *(Briefe vom Amt, alte Rechnungen, Buch-Scans)* | Die erzeugte `.md`-Datei ist komplett **leer** (0 Wörter), weil das PDF intern nur aus einem JPEG-Bild besteht. | **Automatischer OCR-Fallback:** Wenn `< 20 Zeichen/Seite` erkannt werden, greift automatisch `ocrmypdf` (Tesseract `deu+eng`) oder ein lokales Vision-LLM (`qwen2.5vl:7b`). |
| **3** | **Komplexe Tabellen (Merged Cells)** *(Verbundene Zellen in Excel `.xlsx`, `.docx` oder PDF)* | Standard-Markdown-Tabellen (`\| A \| B \|`) unterstützen **keine verbundenen Zeilen/Spalten (`rowspan`/`colspan`)**. Zahlen verrutschen in die falsche Spalte! | **2-Stufen-Regel:** Einfache Tabellen als Markdown-Grid rendern; komplexe Tabellen als sauberes **HTML-`<table>` im Markdown** belassen (Obsidian und LLMs verstehen eingebettetes HTML nativ!). |
| **4** | **Wiederholte Kopf- & Fußzeilen / Seitenzahlen** *(„Seite 4 von 90 – Vertraulich“ mitten im Satz)* | Wenn ein Satz über das Seitenende geht, zerreißt die Fußzeile den Satzzusammenhang und verschmutzt die KI-Suche. | **Header/Footer-Clipping:** In `PyMuPDF4LLM` die obersten und untersten 5 % der Seitenränder ignorieren oder per Regex wiederkehrende Kopfzeilen vor dem Speichern filtern. |
| **5** | **Eingebettete Bilder, Diagramme & Charts** *(Architektur-Grafiken, Balkendiagramme in PDF/PPTX)* | Markdown speichert keinen Binär-Inhalt. Ohne Bild-Extraktion gehen sämtliche Informationen aus Diagrammen für die KI verloren. | **Asset-Extraktion + Bildbeschreibung:** Bilder nach `vault/99_assets/` extrahieren (`![[bild_s1.png]]`) und optional einmalig durch ein lokales Vision-Modell in Text beschreiben lassen. |
| **6** | **Silbentrennung & harte Zeilenumbrüche** *(„Speicher-\nverwaltung“ am Zeilenende im PDF)* | Die Volltextsuche (FTS5) findet das Wort `Speicherverwaltung` nicht mehr, weil ein Bindestrich + Zeilenumbruch dazwischenliegt. | **Dehyphenation-Filter im Ingest-Skript:** Regex `r"(\w+)-\n(\w+)" -> r"\1\2"` setzt getrennte deutsche Wörter beim Import automatisch wieder zusammen. |
| **7** | **Obsidian-Sonderzeichen & kaputte Links** *(Eckige Klammern `[1]`, Pipes `\|` oder `#Tags` im Rohtext)* | Ein zufälliges `#123` im Rechnungstext erzeugt in Obsidian ungewollte Tags; ein `\|` im Fließtext sprengt Markdown-Tabellen. | **Markdown-Sanitizer:** Pipes innerhalb von Tabellenzellen immer als `\|` maskieren und YAML-Frontmatter sauber in Anführungszeichen (`"..."`) kapseln. |

---

## 📊 Warum läuft die Konvertierung zu 100 % auf der CPU (0 MB VRAM)?

Alle 4 Konverter-Stufen in [`scripts/ingest_to_markdown.py`](file:///home/clemi/Projekte/LLM/digital-twin-memory/scripts/ingest_to_markdown.py) (`PyMuPDF4LLM`, `MarkItDown`, XML-ODT-Parser und `pdftotext`) sowie der **SQLite FTS5 Volltext-Index** (`configs/twin_memory.db`) arbeiten rein auf der CPU.  
Dadurch bleibt dein Grafikspeicher (egal ob 16 GB VRAM oder 48 GB VRAM auf der W7800) **zu 100 % für das Sprachmodell und dessen Kontextfenster (KV-Cache) reserviert**.
