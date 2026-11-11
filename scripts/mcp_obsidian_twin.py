#!/usr/bin/env python3
"""
🧠 3-Ebenen Obsidian Digital Twin MCP-Server & CLI
==================================================
Verbindet den 3-stufigen Obsidian-Vault (`vault/01..03`) mit lokaler KI (OpenCode, Goose, Open WebUI via mcpo):
  - Ebene 1 (`01_fleeting_notes`):   Roh-Markdown aus PDF/ODT/DOCX (Gewichtung 1.0x)
  - Ebene 2 (`02_literature_notes`): Strukturierte Zusammenfassungen & Exzerpte (Gewichtung 2.0x)
  - Ebene 3 (`03_permanent_brain`):  Verifiziertes Kernwissen / Digitaler Zwilling (Gewichtung 3.5x)

Nutzt SQLite FTS5 für ultraschnelle Volltextsuche (0 MB VRAM Overhead) und erkennt `[[WikiLinks]]`.
"""

import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))
import ingest_to_markdown as ingester  # noqa: E402

CONFIG_DIR = BASE_DIR / "configs"
VAULT_DIR = BASE_DIR / "vault"
DB_PATH = CONFIG_DIR / "twin_memory.db"

LAYER_DIRS = {
    1: VAULT_DIR / "01_fleeting_notes",
    2: VAULT_DIR / "02_literature_notes",
    3: VAULT_DIR / "03_permanent_brain",
}

LAYER_NAMES = {
    1: "fleeting",
    2: "literature",
    3: "permanent",
}

LAYER_WEIGHTS = {
    1: 1.0,
    2: 2.0,
    3: 3.5,
}


def get_db() -> sqlite3.Connection:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for d in LAYER_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    (VAULT_DIR / "00_inbox_raw").mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            rel_path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            brain_layer INTEGER NOT NULL,
            layer_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            tags TEXT NOT NULL DEFAULT '',
            wikilinks TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            rel_path,
            title,
            tags,
            content
        )
        """
    )
    conn.commit()
    return conn


def extract_wikilinks(text: str) -> List[str]:
    return sorted(set(re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", text)))


def parse_frontmatter(md_text: str, default_layer: int) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "title": "",
        "brain_layer": default_layer,
        "status": "active",
        "tags": [],
    }
    if md_text.startswith("---\n"):
        end_idx = md_text.find("\n---\n", 4)
        if end_idx != -1:
            fm_block = md_text[4:end_idx]
            for line in fm_block.splitlines():
                if ":" in line and not line.strip().startswith("-"):
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "title":
                        meta["title"] = v
                    elif k == "brain_layer":
                        try:
                            meta["brain_layer"] = int(v)
                        except ValueError:
                            pass
                    elif k == "status":
                        meta["status"] = v
                elif line.strip().startswith("- "):
                    tag_val = line.strip()[2:].strip().strip('"').strip("'")
                    meta["tags"].append(tag_val)
    return meta


def sync_vault_to_db() -> Dict[str, Any]:
    """Synchronisiert alle Markdown-Dateien der 3 Obsidian-Ebenen mit dem SQLite-FTS5-Index."""
    conn = get_db()
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM notes_fts")

    counts = {1: 0, 2: 0, 3: 0}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    for layer_num, folder in LAYER_DIRS.items():
        if not folder.exists():
            continue
        md_files: List[Path] = []
        for root, _, files in os.walk(folder, followlinks=True):
            for fname in sorted(files):
                if fname.endswith(".md") and not fname.startswith("."):
                    md_files.append(Path(root) / fname)

        for md_file in sorted(md_files):
            rel_path = str(md_file.relative_to(VAULT_DIR))
            text = md_file.read_text(encoding="utf-8", errors="replace")
            meta = parse_frontmatter(text, layer_num)
            title = meta["title"] or md_file.stem
            tags_str = ", ".join(meta["tags"])
            links_str = ", ".join(extract_wikilinks(text))

            conn.execute(
                """
                INSERT OR REPLACE INTO notes
                (rel_path, title, brain_layer, layer_name, status, tags, wikilinks, content, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel_path,
                    title,
                    layer_num,
                    LAYER_NAMES[layer_num],
                    meta["status"],
                    tags_str,
                    links_str,
                    text,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO notes_fts (rel_path, title, tags, content) VALUES (?, ?, ?, ?)",
                (rel_path, title, tags_str, text),
            )
            counts[layer_num] += 1

    conn.commit()
    conn.close()
    return {"synced_layers": counts, "total_notes": sum(counts.values())}


def brain_search(query: str, layer: int = 0, limit: int = 8) -> List[Dict[str, Any]]:
    """Durchsucht alle 3 Gehirn-Ebenen mit Prioritäts-Boost für höhere Ebenen (Ebene 3 > Ebene 2 > Ebene 1)."""
    sync_vault_to_db()
    conn = get_db()
    q_like = f"%{query.strip()}%"

    sql = """
        SELECT rel_path, title, brain_layer, layer_name, status, tags, wikilinks, content, updated_at
        FROM notes
        WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?)
    """
    params: List[Any] = [q_like, q_like, q_like]
    if layer in (1, 2, 3):
        sql += " AND brain_layer = ?"
        params.append(layer)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    results = []
    q_lower = query.strip().lower()
    for r in rows:
        content_lower = r["content"].lower()
        occurrences = max(1, content_lower.count(q_lower))
        title_bonus = 3.0 if q_lower in r["title"].lower() else 1.0
        layer_weight = LAYER_WEIGHTS.get(r["brain_layer"], 1.0)
        score = round(occurrences * title_bonus * layer_weight, 2)

        # Kurzen Textausschnitt rund um den Treffer extrahieren
        idx = content_lower.find(q_lower)
        if idx != -1:
            start = max(0, idx - 120)
            end = min(len(r["content"]), idx + 280)
            snippet = r["content"][start:end].replace("\n", " ").strip()
        else:
            snippet = r["content"][:300].replace("\n", " ").strip()

        results.append(
            {
                "rel_path": r["rel_path"],
                "title": r["title"],
                "brain_layer": r["brain_layer"],
                "layer_name": r["layer_name"],
                "relevance_score": score,
                "wikilinks": r["wikilinks"],
                "snippet": snippet,
            }
        )

    results.sort(key=lambda x: (x["relevance_score"], x["brain_layer"]), reverse=True)
    return results[:limit]


def brain_read_note(rel_path: str) -> Dict[str, Any]:
    target = (VAULT_DIR / rel_path).resolve()
    if not str(target).startswith(str(VAULT_DIR.resolve())) or not target.exists():
        return {"error": f"Notiz nicht gefunden: {rel_path}"}
    text = target.read_text(encoding="utf-8", errors="replace")
    return {
        "rel_path": rel_path,
        "Outgoing_WikiLinks": extract_wikilinks(text),
        "content": text,
    }


def brain_write_note(title: str, content: str, layer: int = 2, parent_note: str = "", tags: str = "") -> Dict[str, Any]:
    if layer not in (1, 2, 3):
        layer = 2
    slug = ingester.slugify(title)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    date_prefix = datetime.datetime.now().strftime("%Y%m%d")
    folder = LAYER_DIRS[layer]
    folder.mkdir(parents=True, exist_ok=True)
    target_path = folder / f"{slug}.md"

    status_map = {1: "unprocessed", 2: "summarized", 3: "evergreen"}
    tag_list = [f"brain/layer{layer}"] + [t.strip() for t in tags.split(",") if t.strip()]
    tags_yaml = "\n".join(f'  - "{t}"' for t in tag_list)
    parent_yaml = f'["[[{parent_note}]]"]' if parent_note else "[]"
    parent_link_md = f"\n> **Abgeleitet aus Quelle:** [[{parent_note}]]\n" if parent_note else ""

    md_doc = f"""---
id: "{date_prefix}-{slug}"
title: "{title}"
brain_layer: {layer}
layer_name: "{LAYER_NAMES[layer]}"
status: "{status_map[layer]}"
parent_notes: {parent_yaml}
tags:
{tags_yaml}
created_at: "{now}"
updated_at: "{now}"
---

# {title}
{parent_link_md}
{content.strip()}
"""
    target_path.write_text(md_doc, encoding="utf-8")
    sync_vault_to_db()
    return {
        "status": "saved",
        "brain_layer": layer,
        "layer_name": LAYER_NAMES[layer],
        "rel_path": str(target_path.relative_to(VAULT_DIR)),
    }


def brain_promote_with_ai(
    source_rel_path: str,
    to_layer: int,
    custom_title: str = "",
    custom_summary: str = "",
    model: str = "qwen3-coder:latest",
    tags: str = "",
) -> Dict[str, Any]:
    """Befördert eine Notiz in Ebene 2 (Literature) oder Ebene 3 (Permanent Brain) – optional mit automatischer KI-Verdichtung via Ollama."""
    note = brain_read_note(source_rel_path)
    if "error" in note:
        return note

    raw_text = note["content"]
    src_stem = Path(source_rel_path).stem
    parent_link = source_rel_path[:-3] if source_rel_path.endswith(".md") else source_rel_path

    if not custom_title:
        suffix = "Exzerpt" if to_layer == 2 else "Kernwissen"
        custom_title = f"{src_stem}_{suffix}"

    if custom_summary.strip():
        synthesized_md = custom_summary.strip()
    else:
        if to_layer == 2:
            prompt = (
                "Du bist ein präziser Wissens-Kurator für Obsidian (Ebene 2: Literature Note). "
                "Extrahiere aus dem folgenden Rohtext (Ebene 1) eine strukturierte Markdown-Zusammenfassung mit:\n"
                "1) ## 🎯 Kernaussagen (Bullet Points)\n"
                "2) ## 📊 Wichtige Fakten, Zahlen & Parameter\n"
                "3) ## 🔗 Vorgeschlagene Obsidian-[[WikiLinks]] für Konzepte\n\n"
                f"Rohtext:\n{raw_text[:18000]}"
            )
        else:
            prompt = (
                "Du bist mein Digitaler Zwilling für Obsidian (Ebene 3: Permanent Brain / Evergreen Note). "
                "Destilliere aus dieser Notiz zeitloses, verifiziertes Kernwissen:\n"
                "1) ## 🧠 Prinzip / Entscheidung (Atomare Aussage)\n"
                "2) ## ⚙️ Konkrete Regeln & Anwendung\n"
                "3) ## 🔗 Vernetzung (relevante [[WikiLinks]])\n\n"
                f"Quellnotiz:\n{raw_text[:18000]}"
            )
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                synthesized_md = resp_data.get("response", "").strip()
        except Exception as err:
            return {"error": f"Ollama-Aufruf fehlgeschlagen ({err}). Übergib alternativ --summary '...' direkt."}

    # Status in der Quellnotiz aktualisieren (von unprocessed -> summarized / evergreen)
    src_full_path = (VAULT_DIR / source_rel_path).resolve()
    if src_full_path.exists():
        new_src_status = "summarized" if to_layer == 2 else "distilled_to_layer3"
        updated_src = re.sub(r'status:\s*"[^"]*"', f'status: "{new_src_status}"', raw_text, count=1)
        src_full_path.write_text(updated_src, encoding="utf-8")

    return brain_write_note(
        title=custom_title,
        content=synthesized_md,
        layer=to_layer,
        parent_note=parent_link,
        tags=tags or ("literatur,exzerpt" if to_layer == 2 else "evergreen,zwilling"),
    )


def brain_status() -> Dict[str, Any]:
    sync_info = sync_vault_to_db()
    inbox_files = [
        p.name
        for p in sorted((VAULT_DIR / "00_inbox_raw").iterdir())
        if p.is_file() and not p.name.startswith(".")
    ]
    return {
        "vault_path": str(VAULT_DIR),
        "db_path": str(DB_PATH),
        "inbox_raw_files": inbox_files,
        "layer_1_fleeting_count": sync_info["synced_layers"][1],
        "layer_2_literature_count": sync_info["synced_layers"][2],
        "layer_3_permanent_count": sync_info["synced_layers"][3],
        "total_indexed_notes": sync_info["total_notes"],
    }


def run_mcp_stdio() -> None:
    """MCP JSON-RPC 2.0 STDIO Server für OpenCode, Goose & mcpo."""
    sync_vault_to_db()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method", "")
            if "id" not in req or req.get("id") is None:
                continue
            req_id = req["id"]

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "obsidian-3layer-twin", "version": "1.0.0"},
                    },
                }
            elif method == "ping":
                res = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "brain_ingest_file",
                                "description": "Liest ein Dokument (PDF, ODT, DOCX, CSV, HTML, TXT) ein, konvertiert es in Obsidian-Markdown und speichert es in Gehirn-Ebene 1 (01_fleeting_notes).",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {"type": "string", "description": "Absoluter Pfad zur Quelldatei"}
                                    },
                                    "required": ["file_path"],
                                },
                            },
                            {
                                "name": "brain_search",
                                "description": "Durchsucht das 3-stufige Obsidian-Gehirn. Ebene 3 (Permanent Brain) wird automatisch am höchsten gewichtet (3.5x), Ebene 2 (Literature) mit 2.0x, Ebene 1 (Rohdaten) mit 1.0x.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Suchbegriff oder Thema"},
                                        "layer": {"type": "integer", "description": "Optionaler Filter: 0=Alle Ebenen, 1=Fleeting, 2=Literature, 3=Permanent", "default": 0},
                                    },
                                    "required": ["query"],
                                },
                            },
                            {
                                "name": "brain_read_note",
                                "description": "Liest den vollständigen Markdown-Inhalt und alle [[WikiLinks]] einer Notiz aus dem Obsidian-Vault.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "rel_path": {"type": "string", "description": "Relativer Pfad im Vault, z.B. '01_fleeting_notes/doku1.md'"}
                                    },
                                    "required": ["rel_path"],
                                },
                            },
                            {
                                "name": "brain_promote_or_write_note",
                                "description": "Erstellt oder aktualisiert eine Notiz in Ebene 1, 2 (Literatur-Exzerpt) oder 3 (Permanentes Wissen / Digitaler Zwilling) und verknüpft sie per [[WikiLink]] mit der Quelle.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string", "description": "Titel der Notiz"},
                                        "content": {"type": "string", "description": "Markdown-Inhalt inkl. [[WikiLinks]]"},
                                        "layer": {"type": "integer", "description": "Ziel-Gehirnebene: 1 (Fleeting), 2 (Literature) oder 3 (Permanent)", "default": 2},
                                        "parent_note": {"type": "string", "description": "Optionaler Pfad der Ursprungsnotiz für automatischen WikiLink"},
                                        "tags": {"type": "string", "description": "Kommagetrennte Tags"},
                                    },
                                    "required": ["title", "content", "layer"],
                                },
                            },
                            {
                                "name": "brain_status",
                                "description": "Zeigt Statistiken über alle 3 Gehirn-Ebenen und den Status des Obsidian-Vaults.",
                                "inputSchema": {"type": "object", "properties": {}},
                            },
                        ]
                    },
                }
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name", "")
                args = params.get("arguments", {})
                if name == "brain_ingest_file":
                    out_md, fhash = ingester.convert_file_to_markdown(Path(str(args.get("file_path", ""))))
                    sync_vault_to_db()
                    out: Any = {"status": "ingested_to_layer_1", "markdown_path": str(out_md.relative_to(VAULT_DIR)), "sha256": fhash}
                elif name == "brain_search":
                    out = brain_search(str(args.get("query", "")), int(args.get("layer", 0)))
                elif name == "brain_read_note":
                    out = brain_read_note(str(args.get("rel_path", "")))
                elif name == "brain_promote_or_write_note":
                    out = brain_write_note(
                        str(args.get("title", "")),
                        str(args.get("content", "")),
                        int(args.get("layer", 2)),
                        str(args.get("parent_note", "")),
                        str(args.get("tags", "")),
                    )
                elif name == "brain_status":
                    out = brain_status()
                else:
                    out = {"error": f"Unbekanntes Tool: {name}"}

                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(out, indent=2, ensure_ascii=False)}],
                        "isError": False,
                    },
                }
            else:
                res = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as err:
            err_res = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(err)}}
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        parser = argparse.ArgumentParser(description="Obsidian 3-Ebenen Digital Twin CLI")
        parser.add_argument("--cli", action="store_true")
        sub = parser.add_subparsers(dest="cmd")

        p_ing = sub.add_parser("ingest", help="Datei oder Ordner in Ebene 1 konvertieren")
        p_ing.add_argument("path", nargs="?", default=str(VAULT_DIR / "00_inbox_raw"))

        p_search = sub.add_parser("search", help="3-Ebenen-Gehirn durchsuchen")
        p_search.add_argument("query")
        p_search.add_argument("--layer", type=int, default=0)

        p_write = sub.add_parser("write", help="Notiz in Ebene 1, 2 oder 3 schreiben")
        p_write.add_argument("title")
        p_write.add_argument("content")
        p_write.add_argument("--layer", type=int, default=2)
        p_write.add_argument("--parent", default="")
        p_write.add_argument("--tags", default="")

        p_read = sub.add_parser("read", help="Notiz und ihre WikiLinks lesen")
        p_read.add_argument("rel_path")

        p_prom = sub.add_parser("promote", help="Notiz mit lokaler KI oder direkt in höhere Gehirn-Ebene (2 oder 3) befördern")
        p_prom.add_argument("source_rel_path", help="Pfad im Vault, z.B. 01_fleeting_notes/doku1.md")
        p_prom.add_argument("--to-layer", type=int, choices=[2, 3], required=True, help="Ziel-Ebene: 2 (Literature) oder 3 (Permanent Brain)")
        p_prom.add_argument("--title", default="", help="Optionaler neuer Titel")
        p_prom.add_argument("--summary", default="", help="Optionaler Text (wenn leer, fasst Ollama automatisch zusammen)")
        p_prom.add_argument("--model", default="qwen3-coder:latest", help="Lokales Ollama-Modell für die KI-Verdichtung")
        p_prom.add_argument("--tags", default="", help="Kommagetrennte Tags")

        sub.add_parser("status", help="Status des 3-Ebenen-Gehirns anzeigen")

        args = parser.parse_args()
        if args.cmd == "ingest":
            target = Path(args.path).resolve()
            if target.is_file():
                out_md, fhash = ingester.convert_file_to_markdown(target)
                print(f"✅ Konvertiert (Ebene 1): {out_md.relative_to(VAULT_DIR)} [{fhash}]")
            elif target.is_dir():
                for f in sorted(target.iterdir()):
                    if f.is_file() and f.suffix.lower() in ingester.SUPPORTED_EXTENSIONS and not f.name.startswith("."):
                        out_md, fhash = ingester.convert_file_to_markdown(f)
                        print(f"✅ Konvertiert (Ebene 1): {out_md.relative_to(VAULT_DIR)} [{fhash}]")
            sync_vault_to_db()
        elif args.cmd == "search":
            res = brain_search(args.query, args.layer)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.cmd == "write":
            res = brain_write_note(args.title, args.content, args.layer, args.parent, args.tags)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.cmd == "read":
            res = brain_read_note(args.rel_path)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.cmd == "promote":
            res = brain_promote_with_ai(
                args.source_rel_path,
                args.to_layer,
                args.title,
                args.summary,
                args.model,
                args.tags,
            )
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            st = brain_status()
            print("======================================================================")
            print("🧠 OBSIDIAN 3-EBENEN DIGITAL TWIN — STATUS")
            print("======================================================================")
            print(f"  📂 Vault-Pfad:                 {st['vault_path']}")
            print(f"  🗄️ SQLite FTS5 Index:          {st['db_path']}")
            print(f"  📥 00_inbox_raw (Rohdateien):  {len(st['inbox_raw_files'])} Datei(en)")
            print(f"  🟢 Ebene 1 (Fleeting / Roh):   {st['layer_1_fleeting_count']} Markdown-Notiz(en) [Gewicht 1.0x]")
            print(f"  🟡 Ebene 2 (Literature):       {st['layer_2_literature_count']} Exzerpt-Notiz(en)  [Gewicht 2.0x]")
            print(f"  🔵 Ebene 3 (Permanent Brain):  {st['layer_3_permanent_count']} Kern-Notiz(en)     [Gewicht 3.5x]")
            print("======================================================================")
    else:
        run_mcp_stdio()


if __name__ == "__main__":
    main()
