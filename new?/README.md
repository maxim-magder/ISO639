# ISO 639 Language Data

A machine-readable, hierarchically enriched dataset of every ISO 639 language code, built from the ISO 639 standard and enriched with CLDR groupings, ISO 639-3 macrolanguage data, and custom sub-family trees.

## Files

| File | Description |
|------|-------------|
| `iso639_languages.jsonl` | Flat JSONL — one JSON object per language/family (8 566 records) |
| `iso639_tree.json` | Nested family tree with virtual `LANG` root (429 family nodes) |
| `viewer.html` | Self-contained interactive tree viewer — open in any browser, no server needed |
| `iso639-1.tsv` | ISO 639-1 codes + English names (183 entries) |
| `iso639-2.tsv` | ISO 639-2 codes + English names (1 006 entries) |
| `iso639-3.tsv` | ISO 639-3 codes + English names (7 835 entries) |
| `iso639-5.tsv` | ISO 639-5 codes + English names (115 entries) |

## Pipeline

```
convert.py                   # Excel → base JSONL + initial tree
integrate_cldr.py            # Apply Unicode CLDR parent links
integrate_macrolanguages.py  # Wire ISO 639-3 macrolanguage members
integrate_custom_hierarchies.py  # Apply user-supplied sub-family trees + manual overrides
build_viewer.py              # Generate viewer.html
```

## Data Sources

- ISO 639 standard spreadsheet (`finished_with_heirarchy_no_filters.xlsx`)
- Unicode CLDR `languageGroups.json`
- ISO 639-3 macrolanguage member lists
- Custom Afroasiatic / Niger-Kordofanian sub-family trees (private-use `q**` codes)

## Hierarchy

The root node is a virtual `LANG` entry. Below it the standard ISO 639-5 language families branch out; macrolanguages sit between families and individual languages; custom `q**` nodes (ISO 639 private-use range) provide finer-grained sub-group structure where the standard is silent.
