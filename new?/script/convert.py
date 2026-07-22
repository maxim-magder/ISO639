#!/usr/bin/env python3
"""
ISO 639 Data Converter
Converts finished_with_heirarchy_no_filters.xlsx into:

  iso639_languages.jsonl   — flat JSONL, one JSON object per language
  iso639_tree.json         — nested family/collective hierarchy with virtual
                             "Language" (LANG) root per the user's request

Individual languages (scope=Individual / Macrolanguage / Local) are stored
in the flat file; the tree only contains family/collective nodes since the
source data does not supply parent-pointers for individual languages.
"""

import json
import openpyxl
from pathlib import Path

SOURCE  = Path("/Users/maximmagder/Desktop/COMPLETE ISO639 data/finished_with_heirarchy_no_filters.xlsx")
OUT_DIR = Path("/Users/maximmagder/ISO_DATA")

# ── helpers ──────────────────────────────────────────────────────────────────

def clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def primary_code(row):
    for col in (4, 5, 1, 3, 2):   # 639-3, 639-5, 639-2, 639-2T, 639-2B
        if row[col] is not None:
            return clean(str(row[col]))
    return None


# ── load workbook ─────────────────────────────────────────────────────────────

print("Loading workbook…")
wb = openpyxl.load_workbook(SOURCE)
ws = wb.active

# ── build flat records ────────────────────────────────────────────────────────

print("Building records…")
records     = []
seen_codes  = set()

for raw in ws.iter_rows(min_row=2, values_only=True):
    code = primary_code(raw)
    if code is None or code in seen_codes:
        continue
    seen_codes.add(code)

    parent      = clean(raw[24])
    grandparent = clean(raw[25])
    ggp         = clean(raw[26])
    gggp        = clean(raw[27])

    record = {
        "id": code,

        # ISO standard codes
        "iso639_1":              clean(raw[0]),
        "iso639_2":              clean(raw[1]),
        "iso639_2_bibliographic": clean(raw[2]),
        "iso639_2_terminology":  clean(raw[3]),
        "iso639_3":              clean(raw[4]),
        "iso639_5":              clean(raw[5]),

        # Names in three languages
        # Best available English name: prefer ISO 639-3, fall back to 639-2, then 639-5
        "names": {
            "english":          clean(raw[7]) or clean(raw[6]) or clean(raw[8]),
            "english_iso639_2": clean(raw[6]),
            "english_variants": clean(raw[19]),
            "english_iso639_5": clean(raw[8]),
            "french":           clean(raw[20]),
            "french_iso639_5":  clean(raw[14]),
            "french_variants":  clean(raw[21]),
            "german":           clean(raw[22]),
            "german_variants":  clean(raw[23]),
        },

        # Classification  (ISO 639-3 controlled vocabularies)
        "scope":         clean(raw[9]),   # Individual | Collective | Macrolanguage | Special | Local
        "language_type": clean(raw[10]),  # Living | Extinct | Historical | Constructed | Genetic | Geographic | Genetic-like | Special
        "category":      clean(raw[11]),

        # ISO 639-5 metadata
        "iso639_5_category": {
            "english": clean(raw[15]),
            "french":  clean(raw[16]),
        } if (clean(raw[15]) or clean(raw[16])) else None,

        # Hierarchy (populated for family/collective nodes only)
        "hierarchy_path":    clean(raw[17]),
        "parent":            parent,
        "grandparent":       grandparent,
        "great_grandparent": ggp,
        "gg_grandparent":    gggp,
        "ggg_grandparent":   None,    # virtual "LANG" root; set below

        # Misc
        "notes":            clean(raw[18]),
        "date_numerical":   clean(raw[12]),
        "location_country": clean(raw[13]),
    }

    # ISO 639-5-only entries (no ISO 639-3 code) have no scope/type in the
    # source Excel, but by definition they ARE language group codes → Collective.
    if record["iso639_5"] and not record["iso639_3"] and record["scope"] is None:
        record["scope"] = "Collective"
        record["language_type"] = "Genetic"

    records.append(record)

print(f"  Loaded {len(records):,} records")

# ── wire every top-level family to the virtual LANG root ─────────────────────

LANG_ROOT = {
    "id": "LANG",
    "iso639_1": None, "iso639_2": None,
    "iso639_2_bibliographic": None, "iso639_2_terminology": None,
    "iso639_3": None, "iso639_5": None,
    "names": {
        "english": "Language", "english_iso639_2": None,
        "english_variants": None, "english_iso639_5": None,
        "french": "Langue", "french_iso639_5": None, "french_variants": None,
        "german": "Sprache", "german_variants": None,
    },
    "scope": "Universal", "language_type": "Root", "category": None,
    "iso639_5_category": None,
    "hierarchy_path": "LANG",
    "parent": None, "grandparent": None, "great_grandparent": None,
    "gg_grandparent": None, "ggg_grandparent": None,
    "notes": "Virtual root node connecting all language families (GGG_Grandparent per user specification)",
    "date_numerical": None, "location_country": None,
}

# Build lookup
by_id = {r["id"]: r for r in records}
by_id["LANG"] = LANG_ROOT

# Identify family/collective nodes (scopes that carry hierarchy)
FAMILY_SCOPES  = {"Collective", "Special", "Universal"}

# Wire every family node that has no parent → LANG
for r in records:
    if r["scope"] in FAMILY_SCOPES and r["parent"] is None:
        r["parent"]        = "LANG"
        r["ggg_grandparent"] = None   # LANG is the direct parent

# Also set ggg_grandparent string for deeply nested nodes so the field
# consistently means "the topmost named family above this entry"
def find_root(code, depth=0, visited=None):
    if visited is None:
        visited = set()
    if code in visited or depth > 10:
        return None
    visited.add(code)
    rec = by_id.get(code)
    if rec is None:
        return None
    p = rec.get("parent")
    if p is None or p == "LANG":
        return code
    return find_root(p, depth+1, visited)

for r in records:
    if r["scope"] in FAMILY_SCOPES and r["id"] != "LANG":
        r["ggg_grandparent"] = "LANG"

# ── write JSONL ───────────────────────────────────────────────────────────────

all_records = [LANG_ROOT] + records
jsonl_path  = OUT_DIR / "iso639_languages.jsonl"
print(f"Writing {jsonl_path}…")
with open(jsonl_path, "w", encoding="utf-8") as f:
    for r in all_records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  {len(all_records):,} lines written")

# ── build family-only tree ────────────────────────────────────────────────────
# (Individual/Macrolanguage/Local languages are NOT in the tree —
#  the source data does not carry their family membership.)

print("Building family tree…")
family_nodes = {r["id"]: r for r in all_records if r["scope"] in FAMILY_SCOPES}
family_nodes["LANG"] = LANG_ROOT

# Child map restricted to family nodes
children_of = {fid: [] for fid in family_nodes}
for r in family_nodes.values():
    p = r.get("parent")
    if p and p in children_of:
        children_of[p].append(r["id"])

def tree_node(code, depth=0):
    r = family_nodes[code]
    child_codes = sorted(
        children_of.get(code, []),
        key=lambda c: (family_nodes[c]["names"]["english"] or c).lower()
    )
    return {
        "id":            r["id"],
        "name":          r["names"]["english"] or r["id"],
        "scope":         r["scope"],
        "language_type": r["language_type"],
        "iso639_1":      r["iso639_1"],
        "iso639_2":      r["iso639_2"],
        "iso639_3":      r["iso639_3"],
        "iso639_5":      r["iso639_5"],
        "names":         r["names"],
        "category":      r["category"],
        "iso639_5_category": r["iso639_5_category"],
        "hierarchy_path":    r["hierarchy_path"],
        "notes":         r["notes"],
        "children": [tree_node(c, depth+1) for c in child_codes],
    }

tree      = tree_node("LANG")
tree_path = OUT_DIR / "iso639_tree.json"
print(f"Writing {tree_path}…")
with open(tree_path, "w", encoding="utf-8") as f:
    json.dump(tree, f, ensure_ascii=False, indent=2)

size_kb = tree_path.stat().st_size / 1024
print(f"  {size_kb:.0f} KB, family nodes: {len(family_nodes)}")

# ── quick validation ──────────────────────────────────────────────────────────
print("\nValidation:")
print(f"  LANG root children: {len(tree['children'])}")
for ch in sorted(tree["children"], key=lambda x: x["name"]):
    print(f"    {ch['id']:6s}  {ch['name'][:50]:<50s}  subtree_children={len(ch['children'])}")

print("\nDone.")
