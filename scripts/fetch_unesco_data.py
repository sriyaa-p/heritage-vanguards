"""
scripts/fetch_unesco_data.py
----------------------------
Downloads the official UNESCO World Heritage Sites XML feed, parses it, and
writes a clean JSON dataset to data/processed/unesco_sites_clean.json.

This script is intentionally dependency-light — it uses only the Python
standard library (urllib, xml.etree.ElementTree, re, json, html).

Usage (from repo root, with .env present):
    python scripts/fetch_unesco_data.py              # fetch and write
    python scripts/fetch_unesco_data.py --dry-run    # count only, no write

The output file is NOT committed to the repository; it is generated at
container build/startup time via entrypoint.sh.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "data" / "processed" / "unesco_sites_clean.json"

# Official UNESCO World Heritage Sites XML feed
UNESCO_XML_URL = "https://whc.unesco.org/en/list/xml/"

# Fields we care about inside each <row> element
_FIELD_MAP = {
    "site":                  "name",
    "states_name_en":        "country",
    "region_en":             "region",
    "date_inscribed":        "inscription_year",
    "criteria_txt":          "criteria",
    "short_description_en":  "description",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CRITERIA_RE = re.compile(r"\(([ivx]+)\)", re.IGNORECASE)


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    if not text:
        return ""
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return " ".join(text.split())  # normalise whitespace


def _parse_criteria(raw: str) -> str:
    """
    Convert UNESCO criteria notation to a comma-separated string.
    Examples:
        "(i)(ii)(vi)"  →  "i,ii,vi"
        "i, ii, vi"    →  "i,ii,vi"
        ""             →  ""
    """
    if not raw:
        return ""
    found = _CRITERIA_RE.findall(raw)
    if found:
        return ",".join(c.lower() for c in found)
    # Fallback: already clean-ish text
    return ",".join(p.strip().lower() for p in raw.split(",") if p.strip())


def _parse_country(raw: str) -> str:
    """
    Normalise transboundary country strings.
    "India,<br/>Nepal" → "India, Nepal"
    "France; Spain"     → "France, Spain"
    """
    text = _strip_html(raw)
    # Replace semicolons with commas
    text = re.sub(r"\s*;\s*", ", ", text)
    return text.strip()


# ── Core ───────────────────────────────────────────────────────────────────────

def fetch_and_parse(url: str = UNESCO_XML_URL) -> list[dict]:
    """Download the UNESCO XML feed and return a list of cleaned site dicts."""
    print(f"[fetch] Downloading UNESCO XML from {url} …", flush=True)

    # urllib.request works without third-party deps; add a browser-like UA so
    # the UNESCO server does not reject the request.
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (heritage-sentinel-ai/2.0; research)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw_xml = resp.read()

    print(f"[fetch] Downloaded {len(raw_xml):,} bytes. Parsing …", flush=True)

    root = ET.fromstring(raw_xml)

    # The feed wraps records in <row> elements (possibly inside a <dataset> root).
    rows = root.findall(".//row")
    if not rows:
        raise ValueError("No <row> elements found in the XML. Feed format may have changed.")

    sites: list[dict] = []
    skipped = 0

    for row in rows:
        record: dict = {}
        for xml_key, json_key in _FIELD_MAP.items():
            elem = row.find(xml_key)
            record[json_key] = (elem.text or "").strip() if elem is not None else ""

        # Require at minimum a name
        if not record.get("name"):
            skipped += 1
            continue

        # Clean individual fields
        record["name"]             = _strip_html(record["name"])
        record["country"]          = _parse_country(record["country"])
        record["region"]           = _strip_html(record["region"])
        record["description"]      = _strip_html(record["description"])
        record["criteria"]         = _parse_criteria(record["criteria"])

        # inscription_year: convert to int if possible
        try:
            record["inscription_year"] = int(record["inscription_year"])
        except (ValueError, TypeError):
            record["inscription_year"] = None

        # Drop empty-string country (keep None-like entries for transboundary)
        if not record["country"]:
            record["country"] = "Unknown"

        sites.append(record)

    print(
        f"[fetch] Parsed {len(sites)} sites "
        f"({skipped} skipped due to missing name).",
        flush=True,
    )
    return sites


def write_output(sites: list[dict], output_path: Path = OUTPUT_FILE) -> None:
    """Write the cleaned site list to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(sites, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[fetch] Written → {output_path}", flush=True)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv

    sites = fetch_and_parse()

    if dry_run:
        print(f"[fetch] --dry-run mode: {len(sites)} sites found, nothing written.")
    else:
        write_output(sites)
        print(f"[fetch] Done — {len(sites)} sites ready for seeding.")
