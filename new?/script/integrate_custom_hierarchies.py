#!/usr/bin/env python3
"""
Integrate custom language-group hierarchy data from four user-supplied JSON files.

Each file is a flat list of {"id", "name", "parent_id"} entries that define
sub-group trees within Afroasiatic (Chadic, Berber, Semitic/Aramaic) and
Niger-Kordofanian branches.

Codes that start with 'q' (ISO 639 private-use range qaa-qtz) currently exist
in our data as generic "Reserved for local use" stubs. This script repurposes
them as proper named language-group Collective nodes.

For real ISO codes (e.g. heb, kon, kdo) the script only updates the parent
pointer (overriding any earlier value when the custom file is more specific).

Priority: custom files > macrolanguage integration > CLDR > Excel baseline.

Outputs: iso639_languages.jsonl, iso639_tree.json  (in-place update)
"""

import json
from pathlib import Path

OUT_DIR   = Path("/Users/maximmagder/ISO_DATA")
JSONL_IN  = OUT_DIR / "iso639_languages.jsonl"
JSONL_OUT = OUT_DIR / "iso639_languages.jsonl"
TREE_OUT  = OUT_DIR / "iso639_tree.json"

CUSTOM_FILES = [
    Path("/Users/maximmagder/Downloads/gemini-code-1781746627231.json"),
    Path("/Users/maximmagder/Downloads/gemini-code-1781746647171.json"),
    Path("/Users/maximmagder/Downloads/gemini-code-1781746651070.json"),
    Path("/Users/maximmagder/Downloads/gemini-code-1781747348196.json"),
]

FAMILY_SCOPES = {"Collective", "Special", "Universal", "Macrolanguage"}

# Hand-curated parent corrections that override everything else.
# Format: child_id → correct_parent_id
MANUAL_PARENT_OVERRIDES = {
    "sqr": "ara",   # Siculo Arabic → Arabic (macrolanguage)
    "xaa": "ara",   # Andalusian Arabic → Arabic (macrolanguage)
    "jrb": "ara",   # Judeo-Arabic → Arabic (macrolanguage), not a Semitic sibling
    "xpu": "phn",   # Punic → Phoenician (descended from Phoenician script/language)
}


# ── load existing JSONL ────────────────────────────────────────────────────────

print("Loading JSONL …")
records = []
with JSONL_IN.open() as fh:
    for line in fh:
        line = line.strip()
        if line:
            records.append(json.loads(line))

by_id: dict[str, dict] = {r["id"]: r for r in records}
print(f"  {len(records):,} records loaded")


# ── load & merge custom files ─────────────────────────────────────────────────
# Later files win on duplicate ids; root entries (parent_id=null) are skipped
# for parent updates but still register names.

print("Loading custom hierarchy files …")
custom_entries: dict[str, dict] = {}   # id → latest entry
for path in CUSTOM_FILES:
    with path.open() as fh:
        entries = json.load(fh)
    for e in entries:
        custom_entries[e["id"]] = e

print(f"  {len(custom_entries):,} unique custom entries")


# ── step 1: repurpose q** 'Reserved' stubs → named Collective group nodes ─────

updated_q = 0
for eid, entry in custom_entries.items():
    if not eid.startswith("q"):
        continue
    rec = by_id.get(eid)
    if rec is None:
        # Should not happen given the analysis, but handle gracefully
        new_rec = {
            "id": eid,
            "iso639_1": None, "iso639_2": None,
            "iso639_2_bibliographic": None, "iso639_2_terminology": None,
            "iso639_3": None, "iso639_5": None,
            "names": {
                "english": entry["name"],
                "english_iso639_2": None, "english_variants": None,
                "english_iso639_5": None, "french": None,
                "french_iso639_5": None, "french_variants": None,
                "german": None, "german_variants": None,
            },
            "scope": "Collective",
            "language_type": "Genetic",
            "category": None, "iso639_5_category": None,
            "hierarchy_path": None,
            "parent": entry.get("parent_id"),
            "grandparent": None, "great_grandparent": None,
            "gg_grandparent": None, "ggg_grandparent": None,
            "notes": "Custom language-group node (ISO 639 private-use range).",
            "date_numerical": None, "location_country": None,
        }
        records.append(new_rec)
        by_id[eid] = new_rec
        updated_q += 1
    else:
        # Repurpose the existing Reserved stub
        old_name = rec["names"]["english"]
        rec["names"]["english"] = entry["name"]
        rec["scope"] = "Collective"
        rec["language_type"] = "Genetic"
        rec["notes"] = (
            f"Custom language-group node (ISO 639 private-use range). "
            f"Original ISO label: \"{old_name}\"."
        )
        updated_q += 1

print(f"  Repurposed {updated_q} q** reserved codes → Collective group nodes")


# ── step 2: update parent pointers for ALL custom entries ─────────────────────
# Skip entries whose parent_id is null (they are root nodes; keep existing parent).
# For real ISO codes, override the parent unconditionally (custom = highest priority).
# For q** codes, set the parent from the file as well.

parent_updates = 0
for eid, entry in custom_entries.items():
    new_parent = entry.get("parent_id")
    if new_parent is None:
        continue   # root; don't clobber the existing LANG parent
    rec = by_id.get(eid)
    if rec is None:
        continue
    if rec["parent"] != new_parent:
        rec["parent"] = new_parent
        parent_updates += 1

print(f"  Updated {parent_updates} parent pointers from custom files")


# ── step 2b: apply manual parent overrides ────────────────────────────────────

manual_applied = 0
for child_id, new_parent in MANUAL_PARENT_OVERRIDES.items():
    rec = by_id.get(child_id)
    if rec is None:
        print(f"  WARNING: manual override target '{child_id}' not found in data")
        continue
    rec["parent"] = new_parent
    manual_applied += 1

print(f"  Applied {manual_applied} manual parent overrides")


# ── step 3: rebuild JSONL ─────────────────────────────────────────────────────

print("Writing JSONL …")
with JSONL_OUT.open("w") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  Wrote {len(records):,} records → {JSONL_OUT}")


# ── step 4: rebuild tree ──────────────────────────────────────────────────────

print("Rebuilding tree …")

family_ids  = {r["id"] for r in records if r.get("scope") in FAMILY_SCOPES}
children_of = {fid: [] for fid in family_ids}

for r in records:
    if r["id"] in family_ids:
        p = r.get("parent")
        if p and p in children_of:
            children_of[p].append(r["id"])

# Nodes that ended up with no valid family parent → attach to LANG
lang_adopted = 0
for r in records:
    if r["id"] in family_ids and r["id"] != "LANG":
        p = r.get("parent")
        if not p or p not in by_id:
            r["parent"] = "LANG"
            if "LANG" in children_of and r["id"] not in children_of["LANG"]:
                children_of["LANG"].append(r["id"])
            lang_adopted += 1

if lang_adopted:
    print(f"  Adopted {lang_adopted} orphaned family nodes under LANG")


def tree_node(fid: str, depth: int = 0) -> dict:
    r = by_id[fid]
    names = r.get("names", {})
    node = {
        "id":       fid,
        "name":     names.get("english") or fid,
        "scope":    r.get("scope"),
        "children": [],
    }
    for child_id in sorted(children_of.get(fid, [])):
        node["children"].append(tree_node(child_id, depth + 1))
    return node


root = tree_node("LANG")

# Quick stats
def count_nodes(n):
    return 1 + sum(count_nodes(c) for c in n["children"])

total = count_nodes(root)
print(f"  Tree: {total} family/collective nodes total")

top_level = sorted(root["children"], key=lambda n: -len(n["children"]))
print("  Top-level families (by direct children):")
for n in top_level[:10]:
    sub = sum(count_nodes(c) for c in n["children"])
    print(f"    {n['id']:8s}  {n['name']:40s}  direct={len(n['children'])}  subtree={sub}")

with TREE_OUT.open("w") as fh:
    json.dump(root, fh, ensure_ascii=False, indent=2)
print(f"  Wrote → {TREE_OUT}")
