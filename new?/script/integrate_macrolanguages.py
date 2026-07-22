#!/usr/bin/env python3
"""
ISO 639-3 Macrolanguage Integration
====================================
Inserts macrolanguages as an intermediate hierarchy level between
language families (from CLDR) and their individual member languages.

Source: ISO 639-3 official macrolanguage table (SIL International, Dec 2023)
        63 macrolanguage codes covering 444 individual language codes.

Run AFTER integrate_cldr.py:
    python3 convert.py && python3 integrate_cldr.py && python3 integrate_macrolanguages.py

Outputs:
  iso639_languages.jsonl   — updated (macrolanguage member parents overridden)
  iso639_tree.json         — rebuilt (macrolanguages now appear as tree nodes)
"""

import json
from collections import Counter
from pathlib import Path

OUT_DIR = Path("/Users/maximmagder/ISO_DATA")

# ── Complete ISO 639-3 macrolanguage → individual language members ─────────────
# Source: SIL International, current as of December 2023
MACROLANGUAGE_MEMBERS = {
    "aka": ["fat", "twi"],
    "ara": ["aao", "abh", "abv", "acm", "acq", "acw", "acx", "acy", "adf",
            "aeb", "aec", "afb", "apc", "apd", "arb", "arq", "ars", "ary",
            "arz", "auz", "avl", "ayh", "ayl", "ayn", "ayp", "pga", "shu", "ssh"],
    "aym": ["ayc", "ayr"],
    "aze": ["azb", "azj"],
    "bal": ["bcc", "bgn", "bgp"],
    "bik": ["bcl", "bln", "bto", "cts", "fbl", "lbl", "rbl", "ubl"],
    "bnc": ["ebk", "lbk", "obk", "rbk", "vbk"],
    "bua": ["bxm", "bxr", "bxu"],
    "chm": ["mhr", "mrj"],
    "cnk": ["cek"],
    "cre": ["crj", "crk", "crl", "crm", "csw", "cwd"],
    "del": ["umu", "unm"],
    "den": ["scs", "xsl"],
    "din": ["dib", "dik", "dip", "diw", "dks"],
    "doi": ["dgo", "xnr"],
    "est": ["ekk", "vro"],
    "fas": ["pes", "prs"],
    "ful": ["ffm", "fub", "fuc", "fue", "fuf", "fuh", "fui", "fuq", "fuv"],
    "gba": ["bdt", "gbp", "gbq", "gmm", "gso", "gya"],
    "gon": ["esg", "gno", "wsg"],
    "grb": ["gbo", "gec", "grj", "grv", "gry"],
    "grn": ["gnw", "gug", "gui", "gun", "nhd"],
    "hai": ["hax", "hdn"],
    "hbs": ["bos", "cnr", "hrv", "srp"],      # Serbo-Croatian
    "hmn": ["cqd", "hea", "hma", "hmc", "hmd", "hme", "hmg", "hmh", "hmi",
            "hmj", "hml", "hmm", "hmp", "hmq", "hms", "hmw", "hmy", "hmz",
            "hnj", "hrm", "huj", "mmr", "muq", "mww", "sfm"],
    "iku": ["ike", "ikt"],
    "ipk": ["esi", "esk"],
    "jrb": ["aju", "jye", "yhd", "yud"],
    "kau": ["kby", "knc", "krt"],
    "kln": ["enb", "eyo", "niq", "oki", "pko", "sgc", "spy", "tec", "tuy"],
    "kok": ["gom", "knn"],
    "kom": ["koi", "kpv"],
    "kon": ["kng", "kwy", "ldi"],
    "kpe": ["gkp", "xpe"],
    "kur": ["ckb", "kmr", "sdh"],
    "lah": ["hnd", "hno", "jat", "phr", "pnb", "skr", "xhe"],
    "lav": ["ltg", "lvs"],
    "luy": ["bxk", "ida", "lkb", "lko", "lks", "lri", "lrm", "lsm",
            "lto", "lts", "lwg", "nle", "nyd", "rag"],
    "man": ["emk", "mku", "mlq", "mnk", "msc", "mwk"],
    "mlg": ["bhr", "bmm", "bzc", "msh", "plt", "skg", "tdx", "tkg", "txy", "xmv", "xmw"],
    "mon": ["khk", "mvf"],
    "msa": ["bjn", "btj", "bve", "bvu", "coa", "dup", "hji", "ind", "jak",
            "jax", "kvb", "kvr", "kxd", "lce", "lcf", "liw", "max", "meo",
            "mfa", "mfb", "min", "mqg", "msi", "mui", "orn", "ors", "pel",
            "pse", "tmw", "urk", "vkk", "vkt", "xmm", "zlm", "zmi", "zsm"],
    "mwr": ["dhd", "mtr", "mve", "rwr", "swv", "wry"],
    "nep": ["dty", "npi"],
    "nor": ["nno", "nob"],
    "oji": ["ciw", "ojb", "ojc", "ojg", "ojs", "ojw", "otw"],
    "ori": ["ory", "spv"],
    "orm": ["gax", "gaz", "hae", "orc"],
    "pus": ["pbt", "pbu", "pst"],
    "que": ["qub", "qud", "quf", "qug", "quh", "quk", "qul", "qup", "qur",
            "qus", "quw", "qux", "quy", "quz", "qva", "qvc", "qve", "qvh",
            "qvi", "qvj", "qvl", "qvm", "qvn", "qvo", "qvp", "qvs", "qvw",
            "qvz", "qwa", "qwc", "qwh", "qws", "qxa", "qxc", "qxh", "qxl",
            "qxn", "qxo", "qxp", "qxr", "qxt", "qxu", "qxw"],
    "raj": ["bgq", "gda", "gju", "hoj", "mup", "wbr"],
    "rom": ["rmc", "rmf", "rml", "rmn", "rmo", "rmw", "rmy"],
    "san": ["cls", "vsn"],
    "sqi": ["aae", "aat", "aln", "als"],
    "srd": ["sdc", "sdn", "src", "sro"],
    "swa": ["swc", "swh"],
    "syr": ["aii", "cld"],
    "tmh": ["taq", "thv", "thz", "ttq"],
    "uzb": ["uzn", "uzs"],
    "yid": ["ydd", "yih"],
    "zap": ["zaa", "zab", "zac", "zad", "zae", "zaf", "zai", "zam", "zao",
            "zaq", "zar", "zas", "zat", "zav", "zaw", "zax", "zca", "zcd",
            "zoo", "zpa", "zpb", "zpc", "zpd", "zpe", "zpf", "zpg", "zph",
            "zpi", "zpj", "zpk", "zpl", "zpm", "zpn", "zpo", "zpp", "zpq",
            "zpr", "zps", "zpt", "zpu", "zpv", "zpw", "zpx", "zpy", "zpz",
            "zsr", "zte", "ztg", "ztl", "ztm", "ztn", "ztp", "ztq", "zts",
            "ztt", "ztu", "ztx", "zty"],
    "zha": ["zch", "zeh", "zgb", "zgm", "zgn", "zhd", "zhn", "zlj", "zln",
            "zlq", "zqe", "zyb", "zyg", "zyj", "zyn", "zzj"],
    "zho": ["cdo", "cjy", "cmn", "cnp", "cpx", "csp", "czh", "czo", "gan",
            "hak", "hnm", "hsn", "luh", "lzh", "mnp", "nan", "sjc", "wuu", "yue"],
    "zza": ["diq", "kiu"],
}

# ── load JSONL ────────────────────────────────────────────────────────────────
print("Loading JSONL…")
records = []
by_id   = {}
with open(OUT_DIR / "iso639_languages.jsonl", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line.strip())
        records.append(r)
        by_id[r["id"]] = r
print(f"  {len(records):,} records")

# ── step 1: determine correct parent for each macrolanguage ───────────────────
# For macrolanguages whose parent is still LANG (not placed by CLDR), infer
# their family parent from the current (pre-override) parents of their members.

# ── step 0: create stubs for macrolanguages missing from the data ─────────────
# hbs (Serbo-Croatian) has no ISO 639-1/2 code → not in Excel → create stub
MACROLANGUAGE_STUBS = {
    "hbs": {
        "names_english": "Serbo-Croatian",
        "names_french":  "serbo-croate",
        "notes": "Macrolanguage (ISO 639-3). Deprecated ISO 639-1 code: sh. "
                 "Encompasses Bosnian, Croatian, Montenegrin, and Serbian.",
    },
}
for code, meta in MACROLANGUAGE_STUBS.items():
    if code not in by_id:
        stub = {
            "id": code,
            "iso639_1": None, "iso639_2": None,
            "iso639_2_bibliographic": None, "iso639_2_terminology": None,
            "iso639_3": code, "iso639_5": None,
            "names": {
                "english": meta["names_english"],
                "english_iso639_2": None, "english_variants": None, "english_iso639_5": None,
                "french": meta.get("names_french"),
                "french_iso639_5": None, "french_variants": None,
                "german": None, "german_variants": None,
            },
            "scope": "Macrolanguage",
            "language_type": "Genetic",
            "category": None, "iso639_5_category": None,
            "hierarchy_path": None,
            "parent": "LANG",
            "grandparent": None, "great_grandparent": None,
            "gg_grandparent": None, "ggg_grandparent": "LANG",
            "notes": meta.get("notes"),
            "date_numerical": None, "location_country": None,
        }
        records.append(stub)
        by_id[code] = stub
        print(f"  Created stub for missing macrolanguage: {code} ({meta['names_english']})")

print("Determining macrolanguage family parents…")
parent_fixes = {}

for macro_code, members in MACROLANGUAGE_MEMBERS.items():
    macro_rec = by_id.get(macro_code)
    if not macro_rec:
        print(f"  WARNING: macrolanguage {macro_code!r} not found in data")
        continue

    current_parent = macro_rec.get("parent")
    if current_parent not in (None, "LANG"):
        # Already has a real family parent — trust it
        continue

    # Collect members' current parents (before we override them)
    member_parents = []
    for m in members:
        mr = by_id.get(m)
        if mr and mr.get("parent") not in (None, "LANG"):
            member_parents.append(mr["parent"])

    if not member_parents:
        continue

    # Use the most common member parent as the macrolanguage's family home
    best = Counter(member_parents).most_common(1)[0][0]
    parent_fixes[macro_code] = best
    print(f"  {macro_code} ({macro_rec['names']['english'] or macro_code}): "
          f"parent LANG → {best}")

# Apply the inferred parents
for macro_code, new_parent in parent_fixes.items():
    by_id[macro_code]["parent"] = new_parent
    by_id[macro_code]["ggg_grandparent"] = "LANG"

# ── step 2: wire individual languages to their macrolanguage ──────────────────
print("Wiring individual languages to macrolanguages…")

wired   = 0
missing = 0
for macro_code, members in MACROLANGUAGE_MEMBERS.items():
    if macro_code not in by_id:
        missing += 1
        continue
    for member_code in members:
        mr = by_id.get(member_code)
        if not mr:
            continue
        mr["parent"] = macro_code   # OVERRIDE any prior CLDR parent
        wired += 1

print(f"  Wired {wired} individual languages → their macrolanguages")
print(f"  Missing macrolanguage records: {missing}")

# ── step 3: rebuild family tree (now includes Macrolanguage scope) ────────────
print("Rebuilding family tree…")

# Macrolanguages now appear as intermediate nodes in the tree
FAMILY_SCOPES = {"Collective", "Special", "Universal", "Macrolanguage"}
family_ids = {r["id"] for r in records if r["scope"] in FAMILY_SCOPES}

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

tree = tree_node("LANG")

def count_nodes(node):
    return 1 + sum(count_nodes(c) for c in node["children"])
total = count_nodes(tree)

tree_path = OUT_DIR / "iso639_tree.json"
print(f"Writing {tree_path}…")
with open(tree_path, "w", encoding="utf-8") as f:
    json.dump(tree, f, ensure_ascii=False, indent=2)
size_kb = tree_path.stat().st_size / 1024
print(f"  {size_kb:.0f} KB, {total} family/macrolanguage nodes")
print(f"  LANG top-level children: {len(tree['children'])}")

# ── step 4: write updated JSONL ───────────────────────────────────────────────
jsonl_path = OUT_DIR / "iso639_languages.jsonl"
print(f"Writing {jsonl_path}…")
with open(jsonl_path, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  {len(records):,} lines")

# ── step 5: validation ────────────────────────────────────────────────────────
print("\nValidation — sample ancestry chains:")
def ancestry(code, limit=10):
    path, cur = [], code
    for _ in range(limit):
        r = by_id.get(cur)
        if not r: break
        name = (r.get("names") or {}).get("english") or cur
        path.append(f"{cur}({name[:20]})")
        cur = r.get("parent")
        if not cur: break
    return " → ".join(path)

for code in ["arb", "cmn", "nob", "fra", "hbs", "swh", "twi", "srp"]:
    print(f"  {ancestry(code)}")

print()
print("Macrolanguage subtree counts (top-10 by size):")
# Count how many individual languages fall under each macrolanguage
macro_sizes = {}
for macro_code in MACROLANGUAGE_MEMBERS:
    if macro_code not in by_id:
        continue
    count = sum(1 for m in MACROLANGUAGE_MEMBERS[macro_code] if m in by_id)
    macro_sizes[macro_code] = count

for code, cnt in sorted(macro_sizes.items(), key=lambda x: -x[1])[:10]:
    name = by_id[code]["names"]["english"] or code
    print(f"  {code}  {name[:40]:<40s}  {cnt} members")

print("\nDone — run build_viewer.py to regenerate viewer.html")
