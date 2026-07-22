#!/usr/bin/env python3
"""
CLDR Language Groups Integration
Uses CLDR supplemental/languageGroups to wire parent–child relationships
for ~5,600 individual languages that had no family link.

Outputs:
  iso639_languages.jsonl   — updated flat JSONL with parent links
  iso639_tree.json         — family-only tree (rebuilt, now richer)
  viewer.html              — rebuilt self-contained viewer
"""

import json
from pathlib import Path

CLDR_FILE = Path("/Users/maximmagder/Downloads/languageGroups.json")
OUT_DIR   = Path("/Users/maximmagder/ISO_DATA")

# ── load CLDR ─────────────────────────────────────────────────────────────────
print("Loading CLDR languageGroups…")
with open(CLDR_FILE, encoding="utf-8") as f:
    cldr_data = json.load(f)
cldr_groups = cldr_data["supplemental"]["languageGroups"]
print(f"  {len(cldr_groups)} groups")

# ── load existing JSONL ───────────────────────────────────────────────────────
print("Loading existing JSONL…")
records = []
by_id   = {}
with open(OUT_DIR / "iso639_languages.jsonl", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line.strip())
        records.append(r)
        by_id[r["id"]] = r
print(f"  {len(records):,} records loaded")

# ── ISO 639-1 → our primary-id aliases (CLDR uses ISO 639-1 as group codes) ──
# Discovered: cr (Cree) → cre, sw (Swahili) → swa
iso1_to_primary = {}
for r in records:
    i1 = r.get("iso639_1")
    if i1 and i1 not in by_id:
        iso1_to_primary[i1] = r["id"]

print(f"  ISO639-1 aliases mapped: {iso1_to_primary}")

def resolve(code):
    """Map a CLDR code to the canonical id in our data."""
    if code in by_id:
        return code
    return iso1_to_primary.get(code, code)


# ── add missing family stub records ──────────────────────────────────────────
# After aliasing, check what's still missing as a parent
still_missing = set()
for parent_code in cldr_groups:
    r = resolve(parent_code)
    if r not in by_id:
        still_missing.add(parent_code)

print(f"  CLDR parent codes still missing after alias resolution: {still_missing}")

# Hardcoded names for any CLDR-only group codes (currently none expected)
CLDR_NAMES = {}

for code in still_missing:
    stub = {
        "id": code,
        "iso639_1": None, "iso639_2": None,
        "iso639_2_bibliographic": None, "iso639_2_terminology": None,
        "iso639_3": None, "iso639_5": None,
        "names": {
            "english": CLDR_NAMES.get(code, f"{code} (CLDR group)"),
            "english_iso639_2": None, "english_variants": None, "english_iso639_5": None,
            "french": None, "french_iso639_5": None, "french_variants": None,
            "german": None, "german_variants": None,
        },
        "scope": "Collective",
        "language_type": "Genetic",
        "category": None, "iso639_5_category": None,
        "hierarchy_path": code,
        "parent": "LANG",
        "grandparent": None, "great_grandparent": None,
        "gg_grandparent": None, "ggg_grandparent": "LANG",
        "notes": "Added from CLDR UNICODE supplemental languageGroups",
        "date_numerical": None, "location_country": None,
    }
    records.append(stub)
    by_id[code] = stub

# ── apply CLDR parent links ───────────────────────────────────────────────────
print("Applying CLDR parent links…")

# CLDR's 'mul' (Multiple languages) lists all top-level families.
# We already have them as children of LANG — skip 'mul' as a parent.
SKIP_AS_PARENT = {"mul"}

updated = 0
for cldr_parent, children_str in cldr_groups.items():
    if cldr_parent in SKIP_AS_PARENT:
        continue

    canonical_parent = resolve(cldr_parent)
    if canonical_parent not in by_id:
        print(f"  WARNING: parent {cldr_parent!r} → {canonical_parent!r} not in data, skipping")
        continue

    for cldr_child in children_str.split():
        canonical_child = resolve(cldr_child)
        if canonical_child not in by_id:
            continue  # language not in our dataset
        child_rec = by_id[canonical_child]

        # Only update if the child currently has no real parent
        # (parent is None or LANG) — don't overwrite existing hierarchy from
        # the ISO 639-5 source, which is more authoritative for family nodes
        if child_rec.get("parent") in (None, "LANG"):
            child_rec["parent"] = canonical_parent
            updated += 1

print(f"  {updated:,} parent links updated")

# ── ensure family nodes' ggg_grandparent stays 'LANG' ────────────────────────
FAMILY_SCOPES = {"Collective", "Special", "Universal"}
for r in records:
    if r["scope"] in FAMILY_SCOPES and r["id"] != "LANG":
        r["ggg_grandparent"] = "LANG"

# ── write updated JSONL ───────────────────────────────────────────────────────
jsonl_path = OUT_DIR / "iso639_languages.jsonl"
print(f"Writing {jsonl_path}…")
with open(jsonl_path, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  {len(records):,} lines")

# ── rebuild family tree ───────────────────────────────────────────────────────
print("Rebuilding family tree…")

# All nodes that are family/collective type
family_ids = {r["id"] for r in records if r["scope"] in FAMILY_SCOPES}

# Build children map for family nodes only
children_of = {fid: [] for fid in family_ids}
for r in records:
    if r["id"] in family_ids:
        p = r.get("parent")
        if p and p in children_of:
            children_of[p].append(r["id"])

def tree_node(code, depth=0):
    r = by_id[code]
    child_codes = sorted(
        children_of.get(code, []),
        key=lambda c: (by_id[c]["names"]["english"] or c).lower()
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

def count_nodes(node):
    return 1 + sum(count_nodes(c) for c in node["children"])

total_nodes = count_nodes(tree)
print(f"  {size_kb:.0f} KB, {total_nodes} family nodes")
print(f"  LANG root children: {len(tree['children'])}")

# ── validation ────────────────────────────────────────────────────────────────
print("\nTop-level families under LANG:")
for ch in sorted(tree["children"], key=lambda x: x["name"]):
    print(f"  {ch['id']:6s}  {ch['name'][:48]:<48s}  subtree={count_nodes(ch)-1}")

print("\nDone — now run build_viewer.py to regenerate viewer.html")
