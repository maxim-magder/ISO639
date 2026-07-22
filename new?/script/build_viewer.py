#!/usr/bin/env python3
"""
Generates a self-contained viewer.html from the JSONL and tree JSON.
All data is embedded as JavaScript so the file works without a web server.
"""
import json, re
from pathlib import Path

OUT_DIR = Path("/Users/maximmagder/ISO_DATA")

# ── load data ─────────────────────────────────────────────────────────────────
print("Loading data…")
with open(OUT_DIR / "iso639_tree.json", encoding="utf-8") as f:
    tree = json.load(f)

records = []
with open(OUT_DIR / "iso639_languages.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

# Build a compact search index (id, names, codes, scope, type, parent)
print("Building search index…")
search_index = []
for r in records:
    names = r.get("names", {})
    search_index.append({
        "id":   r["id"],
        "en":   names.get("english") or "",
        "en2":  names.get("english_iso639_2") or "",
        "fr":   names.get("french") or "",
        "de":   names.get("german") or "",
        "i1":   r.get("iso639_1") or "",
        "i2":   r.get("iso639_2") or "",
        "i3":   r.get("iso639_3") or "",
        "i5":   r.get("iso639_5") or "",
        "sc":   r.get("scope") or "",
        "lt":   r.get("language_type") or "",
        "par":  r.get("parent") or "",
        "cat":  r.get("category") or "",
        "hp":   r.get("hierarchy_path") or "",
        "notes": r.get("notes") or "",
    })

# Full record lookup (id → record) for the details panel
full_lookup = {r["id"]: r for r in records}

tree_js    = json.dumps(tree,         ensure_ascii=False, separators=(",",":"))
index_js   = json.dumps(search_index, ensure_ascii=False, separators=(",",":"))
lookup_js  = json.dumps(full_lookup,  ensure_ascii=False, separators=(",",":"))

print(f"  Tree: {len(tree_js)//1024} KB | Index: {len(index_js)//1024} KB | Lookup: {len(lookup_js)//1024} KB")

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ISO 639 Language Family Tree</title>
<style>
  :root {
    --bg:        #0f1117;
    --surface:   #1a1d27;
    --surface2:  #242736;
    --border:    #2e3248;
    --accent:    #5b8cff;
    --accent2:   #7c5bff;
    --text:      #e2e8f0;
    --muted:     #7c8096;
    --green:     #4ade80;
    --orange:    #fb923c;
    --yellow:    #facc15;
    --red:       #f87171;
    --pink:      #f472b6;
    --radius:    8px;
    --tree-w:    340px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── top bar ── */
  header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 10;
  }
  header h1 {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -.3px;
    white-space: nowrap;
  }
  header h1 span { color: var(--accent); }
  .badge {
    font-size: .7rem;
    padding: 2px 8px;
    border-radius: 20px;
    background: var(--surface2);
    color: var(--muted);
    border: 1px solid var(--border);
    white-space: nowrap;
  }
  .search-wrap {
    flex: 1;
    max-width: 440px;
    position: relative;
    margin-left: auto;
  }
  .search-wrap input {
    width: 100%;
    padding: 7px 12px 7px 36px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: .875rem;
    outline: none;
    transition: border-color .2s;
  }
  .search-wrap input:focus { border-color: var(--accent); }
  .search-wrap .icon {
    position: absolute;
    left: 10px; top: 50%;
    transform: translateY(-50%);
    color: var(--muted);
    pointer-events: none;
    font-size: .9rem;
  }
  .search-count {
    font-size: .72rem;
    color: var(--muted);
    white-space: nowrap;
    align-self: center;
  }

  /* ── main area ── */
  main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* ── left sidebar (tree) ── */
  #sidebar {
    width: var(--tree-w);
    min-width: 220px;
    max-width: 500px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex-shrink: 0;
    resize: horizontal;
  }
  #sidebar-header {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    font-size: .75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .05em;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  #tree-container {
    overflow-y: auto;
    flex: 1;
    padding: 6px 0;
  }
  #search-results {
    overflow-y: auto;
    flex: 1;
    padding: 6px 0;
  }

  /* ── tree nodes ── */
  .tree-node {
    user-select: none;
  }
  .tree-row {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px 4px 0;
    cursor: pointer;
    border-radius: 5px;
    margin: 1px 6px;
    transition: background .12s;
    font-size: .84rem;
    line-height: 1.4;
  }
  .tree-row:hover  { background: var(--surface2); }
  .tree-row.active { background: color-mix(in srgb, var(--accent) 18%, transparent); }
  .tree-indent { flex-shrink: 0; display: inline-block; }
  .tree-toggle {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    font-size: .7rem;
    transition: transform .15s;
  }
  .tree-toggle.open { transform: rotate(90deg); }
  .tree-toggle.leaf { opacity: 0; pointer-events: none; }
  .tree-icon {
    font-size: .9rem;
    flex-shrink: 0;
  }
  .tree-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tree-code {
    font-size: .7rem;
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    padding: 1px 5px;
    border-radius: 4px;
    flex-shrink: 0;
  }
  .tree-children {
    overflow: hidden;
    transition: height .2s ease;
  }

  /* ── search result rows ── */
  .result-row {
    padding: 7px 12px;
    cursor: pointer;
    font-size: .84rem;
    display: flex;
    flex-direction: column;
    gap: 2px;
    border-bottom: 1px solid var(--border);
    transition: background .1s;
  }
  .result-row:hover  { background: var(--surface2); }
  .result-row.active { background: color-mix(in srgb, var(--accent) 15%, transparent); }
  .result-name { font-weight: 500; }
  .result-meta {
    font-size: .72rem;
    color: var(--muted);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  mark {
    background: color-mix(in srgb, var(--yellow) 35%, transparent);
    color: inherit;
    border-radius: 2px;
  }

  /* ── right panel ── */
  #detail-panel {
    flex: 1;
    overflow-y: auto;
    padding: 28px 32px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .detail-empty {
    margin: auto;
    text-align: center;
    color: var(--muted);
    font-size: .95rem;
  }
  .detail-empty .big { font-size: 3rem; margin-bottom: 12px; }

  .detail-header { display: flex; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
  .detail-title { font-size: 1.6rem; font-weight: 700; line-height: 1.2; flex: 1; min-width: 200px; }
  .detail-title .subtitle { font-size: .85rem; color: var(--muted); font-weight: 400; margin-top: 3px; }

  .pill-group { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .pill {
    font-size: .72rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
    border: 1px solid transparent;
  }
  .pill.scope-Collective    { background:#1e3a5f; color:#7dd3fc; border-color:#1e4c7a; }
  .pill.scope-Individual    { background:#1a3a28; color:#86efac; border-color:#1e4c34; }
  .pill.scope-Macrolanguage { background:#2d1e4a; color:#c4b5fd; border-color:#5b3fa0; }
  .tree-code.macro-code { color: #c4b5fd; background: color-mix(in srgb, #c4b5fd 12%, transparent); }
  .pill.scope-Special       { background:#3b2e12; color:#fde68a; border-color:#5a4420; }
  .pill.scope-Local         { background:#3b1a1a; color:#fca5a5; border-color:#5a2828; }
  .pill.scope-Universal     { background:#1a2e3b; color:#7dd3fc; border-color:#1e3d5a; }
  .pill.type {
    background: var(--surface2);
    color: var(--muted);
    border-color: var(--border);
  }

  .detail-section { }
  .section-title {
    font-size: .7rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--muted);
    margin-bottom: 10px;
    font-weight: 600;
  }
  .code-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 10px;
  }
  .code-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
  }
  .code-card .label { font-size: .65rem; color: var(--muted); margin-bottom: 4px; }
  .code-card .value {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: .95rem;
    color: var(--accent);
    font-weight: 600;
  }
  .code-card .value.empty { color: var(--border); font-size: .8rem; }

  .names-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  .names-table td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
  .names-table td:first-child { color: var(--muted); width: 90px; font-size: .78rem; }
  .names-table tr:last-child td { border-bottom: none; }

  .path-box {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 14px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: .82rem;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .path-crumb {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .path-code {
    background: color-mix(in srgb, var(--accent) 18%, transparent);
    color: var(--accent);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
    padding: 2px 8px;
    border-radius: 5px;
    cursor: pointer;
    transition: background .15s;
    font-size: .8rem;
  }
  .path-code:hover { background: color-mix(in srgb, var(--accent) 30%, transparent); }
  .path-sep { color: var(--muted); }

  .children-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
  }
  .child-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    cursor: pointer;
    transition: border-color .15s, background .15s;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .child-card:hover {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 8%, var(--surface2));
  }
  .child-card .child-name { font-size: .85rem; font-weight: 500; }
  .child-card .child-meta { font-size: .7rem; color: var(--muted); display: flex; gap: 6px; }

  .note-box {
    background: color-mix(in srgb, var(--yellow) 8%, var(--surface2));
    border: 1px solid color-mix(in srgb, var(--yellow) 30%, var(--border));
    border-radius: var(--radius);
    padding: 10px 14px;
    font-size: .84rem;
    color: var(--yellow);
  }

  /* ── language leaf nodes (individual languages in tree) ── */
  .tree-code.lang-code { color: var(--green); background: color-mix(in srgb, var(--green) 12%, transparent); border-radius: 4px; padding: 1px 5px; }
  .tree-count {
    font-size: .65rem;
    color: var(--muted);
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0px 5px;
    flex-shrink: 0;
    min-width: 20px;
    text-align: center;
  }

  /* ── scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }

  /* ── responsive ── */
  @media (max-width: 640px) {
    #sidebar { width: 100%; max-width: 100%; border-right: none; border-bottom: 1px solid var(--border); height: 40vh; }
    main { flex-direction: column; }
    #detail-panel { padding: 16px; }
  }
</style>
</head>
<body>

<header>
  <h1>ISO 639 <span>Language</span> Database</h1>
  <span class="badge" id="total-badge">— languages</span>
  <span class="badge">ISO 639-1 · 2 · 3 · 5</span>
  <div class="search-wrap">
    <span class="icon">&#128269;</span>
    <input type="text" id="search" placeholder="Search by name, code, or family…" autocomplete="off" spellcheck="false">
  </div>
  <span class="search-count" id="search-count"></span>
</header>

<main>
  <div id="sidebar">
    <div id="sidebar-header">
      <span>&#127968;</span> Family Tree
      <span id="family-count" style="margin-left:auto"></span>
    </div>
    <div id="tree-container"></div>
    <div id="search-results" style="display:none"></div>
  </div>

  <div id="detail-panel">
    <div class="detail-empty">
      <div class="big">&#127758;</div>
      <div style="font-weight:600;font-size:1.1rem;margin-bottom:6px">ISO 639 Language Database</div>
      <div style="max-width:320px;margin:0 auto;line-height:1.6">
        Browse the language family tree on the left, or search for any of the
        <strong id="detail-count">—</strong> languages above.
      </div>
    </div>
  </div>
</main>

<script>
// ── embedded data ─────────────────────────────────────────────────────────────
const TREE  = __TREE__;
const INDEX = __INDEX__;
const FULL  = __FULL__;

// ── globals ───────────────────────────────────────────────────────────────────
let activeId = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const treeContainer   = document.getElementById('tree-container');
const searchResults   = document.getElementById('search-results');
const detailPanel     = document.getElementById('detail-panel');
const searchInput     = document.getElementById('search');
const searchCount     = document.getElementById('search-count');
const totalBadge      = document.getElementById('total-badge');
const familyCountEl   = document.getElementById('family-count');
const detailCountEl   = document.getElementById('detail-count');

// ── init ──────────────────────────────────────────────────────────────────────
totalBadge.textContent = INDEX.length.toLocaleString() + ' languages';
detailCountEl.textContent = INDEX.length.toLocaleString();

// Count family nodes
function countTreeNodes(node) {
  let n = 1;
  for (const c of node.children) n += countTreeNodes(c);
  return n;
}
const familyCount = countTreeNodes(TREE);
familyCountEl.textContent = familyCount + ' nodes';

// ── precompute lookup structures ──────────────────────────────────────────────

// Set of all family/collective node IDs (from the tree JSON)
const FAMILY_IDS = new Set();
(function collectFamilyIds(node) {
  FAMILY_IDS.add(node.id);
  for (const c of node.children) collectFamilyIds(c);
})(TREE);

// parent-id → sorted array of INDEX entries (all languages, including families)
const CHILDREN_MAP = {};
for (const r of INDEX) {
  if (!r.par) continue;
  if (!CHILDREN_MAP[r.par]) CHILDREN_MAP[r.par] = [];
  CHILDREN_MAP[r.par].push(r);
}
for (const key of Object.keys(CHILDREN_MAP)) {
  CHILDREN_MAP[key].sort((a, b) => (a.en || a.id).localeCompare(b.en || b.id));
}

// ── tree rendering ────────────────────────────────────────────────────────────
function familyNodeIcon(node) {
  if (node.id === 'LANG') return '&#127760;';
  const s = node.scope || '';
  const t = node.language_type || '';
  if (s === 'Macrolanguage') return '&#128279;'; // link / macrolanguage
  if (s === 'Special')       return '&#10022;';
  if (t === 'Geographic')    return '&#128205;';
  if (t === 'Genetic-like')  return '&#9881;';
  if (t === 'Genetic')       return '&#129516;';
  return '&#128193;';
}

function langLeafIcon(r) {
  const sc = r.sc || '';
  const lt = r.lt || '';
  if (sc === 'Macrolanguage') return '&#127760;';
  if (lt === 'Extinct')       return '&#9760;';
  if (lt === 'Historical')    return '&#128218;';
  if (lt === 'Constructed')   return '&#9881;';
  return '&#128441;';
}

// Build a family node (from TREE) with lazy-loaded children
function buildTreeNode(node, depth) {
  const wrapper = document.createElement('div');
  wrapper.className = 'tree-node';

  const row = document.createElement('div');
  row.className = 'tree-row';
  row.dataset.id = node.id;

  // Individual language children of this family node (non-family records)
  const indivChildren = (CHILDREN_MAP[node.id] || []).filter(r => !FAMILY_IDS.has(r.id));
  const familyChildren = node.children || [];
  const hasChildren = familyChildren.length > 0 || indivChildren.length > 0;
  const childCount   = familyChildren.length + indivChildren.length;

  // indent
  const indent = document.createElement('span');
  indent.className = 'tree-indent';
  indent.style.width = (depth * 16) + 'px';
  row.appendChild(indent);

  // toggle arrow
  const toggle = document.createElement('span');
  toggle.className = 'tree-toggle' + (hasChildren ? '' : ' leaf');
  toggle.innerHTML = '&#9654;';
  row.appendChild(toggle);

  // icon
  const icon = document.createElement('span');
  icon.className = 'tree-icon';
  icon.innerHTML = familyNodeIcon(node);
  row.appendChild(icon);

  // label
  const label = document.createElement('span');
  label.className = 'tree-label';
  label.textContent = node.name;
  row.appendChild(label);

  // child count badge
  if (childCount > 0 && node.id !== 'LANG') {
    const cnt = document.createElement('span');
    cnt.className = 'tree-count';
    cnt.textContent = childCount;
    row.appendChild(cnt);
  }

  // code badge
  if (node.id !== 'LANG') {
    const code = document.createElement('span');
    code.className = 'tree-code' + (node.scope === 'Macrolanguage' ? ' macro-code' : '');
    code.textContent = node.id;
    row.appendChild(code);
  }

  wrapper.appendChild(row);

  // ── lazy children container ──────────────────────────────────────────────
  let childrenEl  = null;
  let childrenLoaded = false;
  let open = (depth === 0); // only root starts expanded

  if (hasChildren) {
    childrenEl = document.createElement('div');
    childrenEl.className = 'tree-children';
    wrapper.appendChild(childrenEl);

    function loadChildren() {
      if (childrenLoaded) return;
      childrenLoaded = true;
      // Subfamily nodes first (from tree JSON)
      for (const child of familyChildren) {
        childrenEl.appendChild(buildTreeNode(child, depth + 1));
      }
      // Individual language leaves (from INDEX, lazily added)
      for (const r of indivChildren) {
        childrenEl.appendChild(buildLangLeaf(r, depth + 1));
      }
    }

    if (open) {
      loadChildren();
      toggle.classList.add('open');
    } else {
      childrenEl.style.display = 'none';
    }

    toggle.addEventListener('click', e => {
      e.stopPropagation();
      loadChildren(); // renders children on first expand only
      open = !open;
      childrenEl.style.display = open ? '' : 'none';
      toggle.classList.toggle('open', open);
    });
  }

  row.addEventListener('click', () => selectNode(node.id));
  return wrapper;
}

// Build a leaf (or expandable sub-node) for an individual language.
// If the language itself parents other languages (e.g. hbo → heb, smp),
// we show a toggle and lazily render those children recursively.
function buildLangLeaf(r, depth) {
  // Only include non-family children (family nodes are in the TREE already)
  const children = (CHILDREN_MAP[r.id] || []).filter(c => !FAMILY_IDS.has(c.id));
  const hasChildren = children.length > 0;

  const wrapper = document.createElement('div');
  wrapper.className = 'tree-node';

  const row = document.createElement('div');
  row.className = 'tree-row';
  row.dataset.id = r.id;

  const indent = document.createElement('span');
  indent.className = 'tree-indent';
  indent.style.width = (depth * 16) + 'px';
  row.appendChild(indent);

  const toggle = document.createElement('span');
  toggle.className = 'tree-toggle' + (hasChildren ? '' : ' leaf');
  toggle.innerHTML = '&#9654;';
  row.appendChild(toggle);

  const icon = document.createElement('span');
  icon.className = 'tree-icon';
  icon.innerHTML = langLeafIcon(r);
  row.appendChild(icon);

  const label = document.createElement('span');
  label.className = 'tree-label';
  label.textContent = r.en || r.id;
  row.appendChild(label);

  if (hasChildren) {
    const cnt = document.createElement('span');
    cnt.className = 'tree-count';
    cnt.textContent = children.length;
    row.appendChild(cnt);
  }

  const code = document.createElement('span');
  code.className = 'tree-code lang-code';
  code.textContent = r.id;
  row.appendChild(code);

  row.addEventListener('click', () => selectNode(r.id));
  wrapper.appendChild(row);

  if (hasChildren) {
    const childrenEl = document.createElement('div');
    childrenEl.className = 'tree-children';
    childrenEl.style.display = 'none';
    wrapper.appendChild(childrenEl);

    let loaded = false;
    let open   = false;

    toggle.addEventListener('click', e => {
      e.stopPropagation();
      if (!loaded) {
        loaded = true;
        for (const child of children) {
          childrenEl.appendChild(buildLangLeaf(child, depth + 1));
        }
      }
      open = !open;
      childrenEl.style.display = open ? '' : 'none';
      toggle.classList.toggle('open', open);
    });
  }

  return wrapper;
}

treeContainer.appendChild(buildTreeNode(TREE, 0));

// ── select + detail ───────────────────────────────────────────────────────────
function selectNode(id) {
  activeId = id;

  // highlight in tree
  document.querySelectorAll('.tree-row.active, .result-row.active').forEach(el => el.classList.remove('active'));
  document.querySelectorAll(`.tree-row[data-id="${id}"]`).forEach(el => el.classList.add('active'));
  document.querySelectorAll(`.result-row[data-id="${id}"]`).forEach(el => el.classList.add('active'));

  const rec = FULL[id];
  if (!rec) return;
  renderDetail(rec);
}

function renderDetail(rec) {
  const n = rec.names || {};

  // build breadcrumb hierarchy
  const crumbs = [];
  let cur = rec;
  while (cur && cur.id !== 'LANG') {
    crumbs.unshift(cur.id);
    const pid = cur.parent;
    cur = pid ? FULL[pid] : null;
  }
  crumbs.unshift('LANG');

  // find children in tree or via parent index
  const children = findChildren(rec.id);

  let html = '';

  // header
  const scopeClass = 'pill scope-' + (rec.scope || 'Individual');
  html += `<div class="detail-header">
    <div class="detail-title">
      ${esc(n.english || rec.id)}
      ${n.french ? `<div class="subtitle">${esc(n.french)}${n.german ? ` &nbsp;·&nbsp; ${esc(n.german)}` : ''}</div>` : ''}
    </div>
    <div class="pill-group">
      <span class="${scopeClass}">${esc(rec.scope || '—')}</span>
      ${rec.language_type ? `<span class="pill type">${esc(rec.language_type)}</span>` : ''}
      ${rec.category ? `<span class="pill type">${esc(rec.category)}</span>` : ''}
    </div>
  </div>`;

  // note
  if (rec.notes) {
    html += `<div class="detail-section">
      <div class="note-box">&#9432; ${esc(rec.notes)}</div>
    </div>`;
  }

  // codes
  html += `<div class="detail-section">
    <div class="section-title">ISO Standard Codes</div>
    <div class="code-grid">`;
  const codeFields = [
    ['ISO 639-1', rec.iso639_1],
    ['ISO 639-2', rec.iso639_2],
    ['ISO 639-2B', rec.iso639_2_bibliographic],
    ['ISO 639-2T', rec.iso639_2_terminology],
    ['ISO 639-3', rec.iso639_3],
    ['ISO 639-5', rec.iso639_5],
  ];
  for (const [label, val] of codeFields) {
    html += `<div class="code-card">
      <div class="label">${label}</div>
      <div class="value${val ? '' : ' empty'}">${val ? esc(val) : '—'}</div>
    </div>`;
  }
  html += `</div></div>`;

  // names
  const nameRows = [
    ['English',   n.english],
    ['ISO 639-2 English', n.english_iso639_2],
    ['Variants',  n.english_variants],
    ['ISO 639-5 English', n.english_iso639_5],
    ['French',    n.french],
    ['ISO 639-5 French',  n.french_iso639_5],
    ['French variants',   n.french_variants],
    ['German',    n.german],
    ['German variants',   n.german_variants],
  ].filter(([,v]) => v);

  if (nameRows.length) {
    html += `<div class="detail-section">
      <div class="section-title">Names</div>
      <table class="names-table">`;
    for (const [label, val] of nameRows) {
      html += `<tr><td>${esc(label)}</td><td>${esc(val)}</td></tr>`;
    }
    html += `</table></div>`;
  }

  // ISO 639-5 category
  if (rec.iso639_5_category) {
    const cat5 = rec.iso639_5_category;
    html += `<div class="detail-section">
      <div class="section-title">ISO 639-5 Category</div>
      <table class="names-table">
        ${cat5.english ? `<tr><td>English</td><td>${esc(cat5.english)}</td></tr>` : ''}
        ${cat5.french  ? `<tr><td>French</td><td>${esc(cat5.french)}</td></tr>`  : ''}
      </table></div>`;
  }

  // hierarchy breadcrumb
  if (crumbs.length > 1) {
    html += `<div class="detail-section">
      <div class="section-title">Family Hierarchy</div>
      <div class="path-box">`;
    for (let i = 0; i < crumbs.length; i++) {
      const cid = crumbs[i];
      const cr  = FULL[cid];
      const label = cr ? (cr.names.english || cid) : cid;
      html += `<div class="path-crumb">
        <span class="path-code" data-id="${cid}" title="${esc(label)}">${cid}</span>
        ${i < crumbs.length-1 ? '<span class="path-sep">›</span>' : ''}
      </div>`;
    }
    html += `</div></div>`;
  }

  // hierarchy path string
  if (rec.hierarchy_path) {
    html += `<div class="detail-section">
      <div class="section-title">Hierarchy Path (ISO 639-5)</div>
      <div class="path-box" style="font-size:.8rem;color:var(--muted)">${esc(rec.hierarchy_path)}</div>
    </div>`;
  }

  // children
  if (children.length) {
    html += `<div class="detail-section">
      <div class="section-title">Subfamily / Children (${children.length})</div>
      <div class="children-grid">`;
    for (const child of children) {
      const cn = child.names || {};
      html += `<div class="child-card" data-id="${child.id}">
        <div class="child-name">${esc(cn.english || child.id)}</div>
        <div class="child-meta">
          <span>${esc(child.id)}</span>
          ${child.scope ? `<span>${esc(child.scope)}</span>` : ''}
          ${child.language_type ? `<span>${esc(child.language_type)}</span>` : ''}
        </div>
      </div>`;
    }
    html += `</div></div>`;
  }

  detailPanel.innerHTML = html;

  // wire up path-code clicks
  detailPanel.querySelectorAll('.path-code[data-id]').forEach(el => {
    el.addEventListener('click', () => selectNode(el.dataset.id));
  });
  // wire up child cards
  detailPanel.querySelectorAll('.child-card[data-id]').forEach(el => {
    el.addEventListener('click', () => {
      selectNode(el.dataset.id);
      scrollTreeToNode(el.dataset.id);
    });
  });
}

function findChildren(id) {
  return INDEX
    .filter(r => r.par === id)
    .map(r => FULL[r.id])
    .filter(Boolean)
    .sort((a,b) => (a.names.english||a.id).localeCompare(b.names.english||b.id));
}

function scrollTreeToNode(id) {
  // Expand ancestors up to this id so the node exists in the DOM
  const ancestors = [];
  let cur = FULL[id];
  while (cur && cur.id !== 'LANG') {
    const pid = cur.parent;
    if (!pid) break;
    ancestors.unshift(pid);
    cur = FULL[pid];
  }
  for (const anc of ancestors) {
    const row = treeContainer.querySelector(`.tree-row[data-id="${anc}"]`);
    if (row) {
      const toggle = row.querySelector('.tree-toggle:not(.leaf)');
      if (toggle && !toggle.classList.contains('open')) toggle.click();
    }
  }
  // Now scroll
  setTimeout(() => {
    const el = treeContainer.querySelector(`.tree-row[data-id="${id}"]`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 60);
}

// ── search ────────────────────────────────────────────────────────────────────
let searchTimer = null;

searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(doSearch, 180);
});

function doSearch() {
  const q = searchInput.value.trim().toLowerCase();

  if (!q) {
    searchResults.style.display = 'none';
    treeContainer.style.display  = '';
    searchCount.textContent = '';
    document.getElementById('sidebar-header').querySelector('span:first-child').innerHTML = '&#127968;';
    document.getElementById('sidebar-header').childNodes[1].textContent = ' Family Tree';
    return;
  }

  const terms = q.split(/\s+/);
  const hits = [];
  for (const r of INDEX) {
    const haystack = [r.en, r.en2, r.fr, r.de, r.id, r.i1, r.i2, r.i3, r.i5, r.sc, r.lt, r.notes]
      .join(' ').toLowerCase();
    if (terms.every(t => haystack.includes(t))) hits.push(r);
    if (hits.length >= 500) break;
  }

  searchCount.textContent = hits.length < 500
    ? `${hits.length} result${hits.length===1?'':'s'}`
    : '500+ results';

  // render
  searchResults.innerHTML = '';
  for (const r of hits) {
    const div = document.createElement('div');
    div.className = 'result-row';
    div.dataset.id = r.id;
    if (r.id === activeId) div.classList.add('active');
    const name = r.en || r.en2 || r.fr || r.id;
    const codes = [r.i1,r.i2,r.i3,r.i5].filter(Boolean).join(' · ');
    div.innerHTML = `
      <div class="result-name">${highlight(esc(name), q)}</div>
      <div class="result-meta">
        <span>${highlight(esc(r.id), q)}</span>
        ${codes ? `<span>${highlight(esc(codes), q)}</span>` : ''}
        ${r.sc  ? `<span>${esc(r.sc)}</span>`  : ''}
        ${r.lt  ? `<span>${esc(r.lt)}</span>`  : ''}
        ${r.fr && r.fr !== name ? `<span style="font-style:italic">${highlight(esc(r.fr), q)}</span>` : ''}
      </div>`;
    div.addEventListener('click', () => selectNode(r.id));
    searchResults.appendChild(div);
  }

  treeContainer.style.display  = 'none';
  searchResults.style.display  = '';
}

function highlight(str, q) {
  const terms = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  let out = str;
  for (const t of terms) {
    if (!t) continue;
    out = out.replace(new RegExp(escapeRE(t), 'gi'), m => `<mark>${m}</mark>`);
  }
  return out;
}
function escapeRE(s) { return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }
function esc(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>
"""

# ── inject data ───────────────────────────────────────────────────────────────
html = HTML.replace("__TREE__",  tree_js)
html = html.replace("__INDEX__", index_js)
html = html.replace("__FULL__",  lookup_js)

out_path = OUT_DIR / "viewer.html"
print(f"Writing {out_path}…")
out_path.write_text(html, encoding="utf-8")
size_mb = out_path.stat().st_size / 1024 / 1024
print(f"  {size_mb:.1f} MB — open in any browser, no server needed.")
print("Done.")
