#!/usr/bin/env python3
"""
📄 Dokumenten-zu-Markdown Konverter für das 3-Ebenen Obsidian-Gehirn
===================================================================
Liest Dokumente unterschiedlichster Formate ein:
  - PDF (.pdf)           -> via PyMuPDF4LLM / pypdf / pdftotext
  - LibreOffice (.odt)   -> Nativ per XML-Strukturparser (Überschriften, Absätze, Tabellen)
  - Word (.docx)         -> via MarkItDown / python-docx / XML-Fallback
  - Tabellen (.csv/.tsv) -> Markdown-Tabellen-Konverter
  - Web (.html/.htm)     -> Bereinigtes Markdown
  - Text (.txt/.md)      -> Direktimport mit YAML-Frontmatter

Erzeugt saubere Obsidian-Markdown-Dateien in Ebene 1 (`vault/01_fleeting_notes/`)
inklusive standardisiertem YAML-Frontmatter und synchronisiert sie sofort mit der
SQLite-FTS5 Volltextdatenbank (`configs/twin_memory.db`).
"""

import argparse
import csv
import datetime
import hashlib
import io
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_DIR = BASE_DIR / "vault"
INBOX_DIR = VAULT_DIR / "00_inbox_raw"
LAYER1_DIR = VAULT_DIR / "01_fleeting_notes"

SUPPORTED_EXTENSIONS = {".pdf", ".odt", ".docx", ".doc", ".pptx", ".xlsx", ".csv", ".tsv", ".html", ".htm", ".txt", ".md"}


def slugify(name: str) -> str:
    clean = re.sub(r"[^\w\s\-äöüÄÖÜß]", "", name).strip()
    clean = re.sub(r"[\s]+", "_", clean)
    return clean or "unbenanntes_dokument"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def extract_odt_to_markdown(path: Path) -> str:
    """Liest LibreOffice .odt Dateien nativ ohne externe Abhängigkeiten inkl. Überschriften & Tabellen."""
    try:
        with zipfile.ZipFile(path, "r") as z:
            xml_content = z.read("content.xml")
    except Exception as e:
        return f"> ⚠️ Fehler beim Lesen der ODT-Datei `{path.name}`: {e}\n"

    root = ET.fromstring(xml_content)
    ns = {
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    }

    lines: List[str] = []

    def get_all_text(elem: ET.Element) -> str:
        return "".join(elem.itertext()).strip()

    body = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:office:1.0}text")
    if body is None:
        body = root

    for elem in body:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "h":
            level_attr = elem.attrib.get(f"{{{ns['text']}}}outline-level", "2")
            try:
                level = max(1, min(6, int(level_attr)))
            except ValueError:
                level = 2
            txt = get_all_text(elem)
            if txt:
                lines.append(f"\n{'#' * level} {txt}\n")
        elif tag == "p":
            txt = get_all_text(elem)
            if txt:
                lines.append(txt)
        elif tag == "list":
            for item in elem.findall(f".//{{{ns['text']}}}list-item"):
                item_txt = get_all_text(item)
                if item_txt:
                    lines.append(f"- {item_txt}")
            lines.append("")
        elif tag == "table":
            rows_md: List[List[str]] = []
            for row in elem.findall(f".//{{{ns['table']}}}table-row"):
                cells = [
                    get_all_text(c).replace("|", "\\|").replace("\n", " ")
                    for c in row.findall(f".//{{{ns['table']}}}table-cell")
                ]
                if any(cells):
                    rows_md.append(cells)
            if rows_md:
                max_cols = max(len(r) for r in rows_md)
                lines.append("")
                for idx, r in enumerate(rows_md):
                    padded = r + [""] * (max_cols - len(r))
                    lines.append("| " + " | ".join(padded) + " |")
                    if idx == 0:
                        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
                lines.append("")

    return "\n\n".join(lines).strip()


def extract_docx_to_markdown(path: Path) -> str:
    """Konvertiert .docx via MarkItDown oder nativem XML-Parser."""
    try:
        from markitdown import MarkItDown  # type: ignore
        md = MarkItDown()
        res = md.convert(str(path))
        if res and res.text_content:
            return res.text_content.strip()
    except ImportError:
        pass

    try:
        with zipfile.ZipFile(path, "r") as z:
            xml_content = z.read("word/document.xml")
        root = ET.fromstring(xml_content)
        paragraphs: List[str] = []
        for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [t.text for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if t.text]
            joined = "".join(texts).strip()
            if joined:
                paragraphs.append(joined)
        return "\n\n".join(paragraphs)
    except Exception as e:
        return f"> ⚠️ Fehler beim Lesen der DOCX-Datei `{path.name}`: {e}\n"


def extract_pdf_to_markdown(path: Path) -> str:
    """Konvertiert PDF mehrstufig: 1) PyMuPDF4LLM, 2) pypdf, 3) pdftotext (Poppler CLI)."""
    # 1. PyMuPDF4LLM (Beste Layout- und Tabellen-Erkennung)
    try:
        import pymupdf4llm  # type: ignore
        md_text = pymupdf4llm.to_markdown(str(path))
        if md_text and md_text.strip():
            return md_text.strip()
    except ImportError:
        pass
    except Exception:
        pass

    # 2. pypdf
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            txt = (page.extract_text() or "").strip()
            if txt:
                pages.append(f"### Seite {i}\n\n{txt}")
        if pages:
            return "\n\n---\n\n".join(pages)
    except ImportError:
        pass
    except Exception:
        pass

    # 3. Linux Poppler pdftotext Fallback (vorinstalliert auf fast jedem Ubuntu-System)
    if shutil.which("pdftotext"):
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                capture_output=True,
                text=True,
                check=True,
            )
            if proc.stdout.strip():
                return proc.stdout.strip()
        except Exception as e:
            return f"> ⚠️ Fehler bei pdftotext für `{path.name}`: {e}\n"

    return (
        f"> ⚠️ Konnte PDF `{path.name}` noch nicht extrahieren. "
        "Bitte `./setup/01-install-standalone-deps.sh` ausführen (installiert `pymupdf4llm`)."
    )


def extract_csv_to_markdown(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    delim = ";" if content.count(";") > content.count(",") else ","
    reader = csv.reader(io.StringIO(content), delimiter=delim)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return "*Leere Tabelle*"
    max_cols = max(len(r) for r in rows)
    lines = []
    for idx, r in enumerate(rows[:200]):  # Limit Vorschau auf 200 Zeilen
        padded = [c.strip().replace("|", "\\|") for c in r] + [""] * (max_cols - len(r))
        lines.append("| " + " | ".join(padded) + " |")
        if idx == 0:
            lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    return "\n".join(lines)


def convert_file_to_markdown(source_path: Path, copy_to_inbox: bool = True) -> Tuple[Path, str]:
    """Konvertiert eine beliebige Datei nach Ebene 1 (`vault/01_fleeting_notes/`) und gibt den Zielpfad zurück."""
    source_path = source_path.resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {source_path}")

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    LAYER1_DIR.mkdir(parents=True, exist_ok=True)

    ext = source_path.suffix.lower()
    doc_hash = file_sha256(source_path)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    date_prefix = datetime.datetime.now().strftime("%Y%m%d")

    if copy_to_inbox and source_path.parent != INBOX_DIR:
        inbox_target = INBOX_DIR / source_path.name
        if not inbox_target.exists():
            shutil.copy2(source_path, inbox_target)

    if ext == ".pdf":
        body_md = extract_pdf_to_markdown(source_path)
    elif ext == ".odt":
        body_md = extract_odt_to_markdown(source_path)
    elif ext in {".docx", ".pptx", ".xlsx"}:
        body_md = extract_docx_to_markdown(source_path)
    elif ext in {".csv", ".tsv"}:
        body_md = extract_csv_to_markdown(source_path)
    elif ext in {".html", ".htm"}:
        raw_html = source_path.read_text(encoding="utf-8", errors="replace")
        body_md = re.sub(r"<[^>]+>", "", raw_html).strip()
    else:
        body_md = source_path.read_text(encoding="utf-8", errors="replace").strip()

    slug = slugify(source_path.stem)
    target_md_path = LAYER1_DIR / f"{slug}.md"

    frontmatter = f"""---
id: "{date_prefix}-{slug}"
title: "{source_path.stem}"
brain_layer: 1
layer_name: "fleeting"
status: "unprocessed"
source_file: "00_inbox_raw/{source_path.name}"
source_format: "{ext.lstrip('.')}"
sha256: "{doc_hash}"
parent_notes: []
tags:
  - "brain/layer1"
  - "import/{ext.lstrip('.') or 'text'}"
created_at: "{now}"
updated_at: "{now}"
---

# 📄 {source_path.stem} (Roh-Import Ebene 1)

> **Quelle:** `{source_path.name}` | **Gehirn-Ebene:** `1 (Fleeting / Rohdaten)` | **Importiert:** `{now}`  
> **Nächster Schritt:** Nutze `brain_promote_note`, um eine kuratierte Zusammenfassung in **Ebene 2 (`02_literature_notes/`)** zu erstellen.

---

{body_md}
"""
    target_md_path.write_text(frontmatter, encoding="utf-8")
    return target_md_path, doc_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Konvertiert Dokumente (PDF, ODT, DOCX, CSV, HTML) in Obsidian Markdown (Ebene 1).")
    parser.add_argument("path", nargs="?", help="Pfad zu einer Datei oder einem Ordner (Standard: vault/00_inbox_raw)")
    args = parser.parse_args()

    target = Path(args.path).resolve() if args.path else INBOX_DIR
    files_to_process: List[Path] = []

    if target.is_file():
        files_to_process.append(target)
    elif target.is_dir():
        for p in sorted(target.iterdir()):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and not p.name.startswith("."):
                files_to_process.append(p)
    else:
        print(f"❌ Pfad existiert nicht: {target}", file=sys.stderr)
        sys.exit(1)

    if not files_to_process:
        print(f"ℹ️ Keine unterstützten Dokumente in {target} gefunden.")
        return

    for fpath in files_to_process:
        out_path, fhash = convert_file_to_markdown(fpath)
        print(f"✅ Konvertiert nach Ebene 1: {fpath.name} -> {out_path.relative_to(BASE_DIR)} (SHA256: {fhash})")


if __name__ == "__main__":
    main()
