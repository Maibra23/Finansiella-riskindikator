---
name: swedish-ui-check
description: Verify that all user-facing text in the KRI Streamlit dashboard is in Swedish. Detects English words, missing Swedish vowels, and non-Swedish labels. Auto-fixes by adjusting the responsible source files. Use when any file under app/ is created or modified.
triggers:
  - app/**/*.py
  - src/config.py
---

# Swedish UI Text Verification

This skill enforces the project rule: **zero English in the user-facing UI**. Every string a user can see — browser tab, sidebar, charts, tables, tooltips, error messages, buttons, KPI cards — must be Swedish.

## When to invoke

- After creating or editing any file under `app/`
- After modifying `SWEDISH_LABELS` in `src/config.py`
- Before any commit that touches Streamlit page files
- During UX polish reviews (Task 5.2 in docs/tasks.md)

## Canonical source of truth

`src/config.py` contains `SWEDISH_LABELS`, the single authoritative mapping of English variable names to Swedish display text. All user-facing text must either:

1. Come directly from `SWEDISH_LABELS[key]`, or
2. Be a hardcoded Swedish string that does not appear in `SWEDISH_LABELS`

## Scan procedure

Walk every `.py` file under `app/` and extract user-facing strings from these locations:

### Streamlit calls
- `st.markdown()` — the text/HTML argument
- `st.info()`, `st.error()`, `st.warning()`, `st.success()` — message argument
- `st.set_page_config()` — `page_title`, `menu_items` values
- `st.sidebar.slider()`, `st.sidebar.selectbox()`, `st.sidebar.multiselect()` — the label (first positional argument)
- `st.selectbox()`, `st.multiselect()`, `st.text_input()` — the label argument
- `st.download_button()` — `label` argument
- `st.expander()` — the label argument
- `st.tabs()` — the list of tab names
- `st.cache_data(show_spinner=...)` — the spinner text

### Plotly calls
- `labels={}` dict values
- `title=`, `xaxis_title=`, `yaxis_title=` string values
- `hovertemplate=` string content (excluding format specifiers like `%{x:.2f}`)
- `text=` and `name=` in trace constructors
- `fig.add_annotation(text=...)` — the annotation text
- Legend `title=` strings

### Custom component calls
- `render_kpi_card(title=, help_text=, suffix=, prefix=)`
- `render_sidebar_header(subtitle=)`
- Column rename dicts passed to `df.rename(columns=...)`
- Any HTML string passed to `unsafe_allow_html=True`

## English detection checklist

The following English words should NEVER appear in user-facing strings. If found, they indicate a violation:

### High-confidence violations (always wrong in UI context)
```
Dashboard, Overview, Score, Average, Download, Filter, Select,
Year, Municipality, Source, Loading, Error, Warning, Risk Class,
Contribution, National, Population, Debt, Unemployment, Growth,
Tax, Rank, Compare, Table, Chart, Map, Distribution, Trend,
Summary, Report, Page, Help, Settings, About, Total, Count,
Change, Previous, Current, High, Medium, Low
```

### Context-dependent (check surrounding text)
```
vs (use "mot" or "jämfört med"),
per (acceptable in "per capita" which is Latin, not English),
KRI (project acronym, always acceptable),
PDF (format name, acceptable),
CSV (format name, acceptable)
```

### Always acceptable (same word in Swedish and English)
```
Period, Median, KRI, PDF, CSV, Parquet, API, SCB
```

## Auto-fix mapping

When a violation is found, apply this mapping. Primary source is `SWEDISH_LABELS` from `src/config.py`. Supplementary mappings for terms not in that dict:

```python
SUPPLEMENTARY_SWEDISH = {
    "Dashboard":      "Kontrollpanel",
    "Overview":       "Översikt",
    "Loading":        "Laddar",
    "Loading data":   "Laddar data",
    "Loading map":    "Laddar kartdata",
    "Error":          "Fel",
    "Warning":        "Varning",
    "Help":           "Hjälp",
    "About":          "Om",
    "Settings":       "Inställningar",
    "vs":             "mot",
    "Download":       "Ladda ner",
    "Download data":  "Ladda ner data",
    "Download report":"Ladda ner rapport",
    "Select":         "Välj",
    "Filter":         "Filtrera",
    "Compare":        "Jämför",
    "Score":          "Poäng",
    "Average":        "Genomsnitt",
    "National average":"Rikssnitt",
    "Rank":           "Rang",
    "Risk class":     "Riskklass",
    "High risk":      "Hög risk",
    "Medium risk":    "Medel risk",
    "Low risk":       "Låg risk",
    "Municipality":   "Kommun",
    "Year":           "År",
    "Population":     "Befolkning",
    "Debt":           "Skuld",
    "Unemployment":   "Arbetslöshet",
    "Tax base":       "Skattekraft",
    "Growth":         "Tillväxt",
    "Source":         "Källa",
    "Data source":    "Datakälla",
    "Contribution":   "Bidrag",
    "Distribution":   "Fördelning",
    "Trend":          "Trend",
    "Total":          "Totalt",
    "Count":          "Antal",
    "Change":         "Förändring",
    "Previous year":  "Föregående år",
    "Current year":   "Innevarande år",
    "Table":          "Tabell",
    "Chart":          "Diagram",
    "Map":            "Karta",
    "Summary":        "Sammanfattning",
    "Report":         "Rapport",
    "Number of":      "Antal",
}
```

## Fix procedure

1. Run `scripts/verify_swedish_ui.py` to get a violation report
2. For each violation:
   a. Check if the English term has a match in `SWEDISH_LABELS` — use that value
   b. Otherwise check `SUPPLEMENTARY_SWEDISH` above — use that value
   c. If neither matches, translate manually and add to `SWEDISH_LABELS` in `src/config.py`
3. Edit the source file at the reported line
4. Re-run the script to confirm the fix

## Verification script

Run the standalone script to check compliance:

```bash
python3 scripts/verify_swedish_ui.py
```

Exit code 0 = all clean. Exit code 1 = violations found (printed to stdout).

## Swedish character encoding rules

- All files must be UTF-8
- Swedish vowels (å, ä, ö, Å, Ä, Ö) must render correctly — never as escape sequences or mojibake
- Use `\u202f` (narrow no-break space) as thousands separator in formatted numbers, not commas
- Use en-dash `–` (not hyphen `-`) for year ranges like "2010–2024"
