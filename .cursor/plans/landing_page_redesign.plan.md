---
name: Landing Page Redesign (updated)
overview: Redesign the KRI home view with banking-grade visuals, explanatory Swedish copy so users grasp the index concept and know what each area offers, aligned with the existing design system and ui-ux-pro-max.
todos:
  - id: design-system-note
    content: Optional — run ui-ux-pro-max search for fintech dashboard landing if refining copy/structure (project uses Streamlit + existing COLORS, not Tailwind)
  - id: css
    content: Add landing CSS (.lp-hero, .lp-stat-strip, .lp-nav-card, .lp-explain, .lp-visual, .lp-step, hover/focus, prefers-reduced-motion) in theme.py
  - id: helpers
    content: Add render helpers for hero, stat strip, explain blocks, optional SVG fragments, nav cards in theme.py
  - id: landing
    content: Replace landing section in app/main.py with hero, live stats, concept + expectations copy, lightweight visuals, feature cards, credibility strip
  - id: swedish-ui
    content: Run scripts/verify_swedish_ui.py after app/ edits per project skill
  - id: verify
    content: Manual Streamlit check — contrast, no horizontal scroll, keyboard focus on links, hover states
---

# KRI Landing Page — Redesign (Updated)

## Goals (beyond the first draft)

- **Visual engagement:** Add purposeful graphics (inline SVG only — no emoji-as-icons per ui-ux-pro-max). Examples: subtle Sweden/navy motif, a compact “index composition” diagram (five weighted inputs → KRI), or a 3-step “Så använder du verktyget” strip with icons.
- **Concept clarity:** Short Swedish blocks so first-time users understand *what* KRI measures, *how* it is built at a high level (five variables, weights, z-poäng / riskklass — consistent with [docs/Prd.md](docs/Prd.md) and README).
- **Expectations:** A “Vad hittar du här?” section that maps each sidebar destination to outcome (“nationell översikt”, “drivare per kommun”, “djupdykning”) so users know where to click next.

## Alignment with current design

- Reuse [src/config.py](src/config.py) `COLORS` (navy `#0B1F3F`, gold `#C4A35A`, risk greens/ambers/reds) and existing fonts in [app/styles/theme.py](app/styles/theme.py) (Source Sans Pro + IBM Plex Mono).
- Inner dashboard pages stay light; landing may use a scoped dark hero — same tokens as sidebar.
- **ui-ux-pro-max:** Apply checklist items relevant to Streamlit/HTML injection — cursor-pointer and hover feedback on clickable cards; 150–300ms transitions; SVG icons with consistent viewBox; sufficient contrast on hero (white/off-white text on navy); optional `prefers-reduced-motion` to reduce transition intensity; avoid layout shift on hover (shadow/border only, no scale that moves layout).

## Page structure (recommended order)

1. **Hero** — Eyebrow (e.g. “Kommunal finansiell analys”), H1, one-line value proposition, optional subline on audience (controllers, analytiker, beslutsfattare).
2. **Live stat strip** — Four metrics from `kri_df` + session year: t.ex. genomsnittlig KRI, antal hög risk, period 2010–2024, N=290.
3. **“Vad är KRI?”** — 2–3 sentences: sammansatt index, strukturell sårbarhet, 290 kommuner. Tone: institutional, not marketing fluff.
4. **Visual A — Indexat a glance** — Compact HTML block: either (a) horizontal bar or stacked row showing the five variable names with weights (25/25/20/15/15 %) from PRD, or (b) simple SVG “flow” diagram: five labeled boxes → “KRI” → “Riskklass”. Pure CSS + inline SVG; no new chart library on landing.
5. **“Så fungerar det i korthet”** — 3 numbered steps: data från SCB/Kolada → normalisering (z-poäng) → klassificering (Låg/Medel/Hög). One sentence each.
6. **“Vad hittar du här?”** — Three feature cards (existing plan): Riksöversikt, Riskdekomposition, Kommunanalys — each with title, one-line outcome, and page number tag; link styling consistent with sidebar (use `st.page_link` below or wrap cards in anchor pattern that Streamlit supports — implementation detail: prefer visible `st.page_link` calls under each card for accessibility, or a single row of links).
7. **Credibility strip** — Källor (SCB, Arbetsförmedlingen/Kolada), metodreferens (t.ex. “KRI v1.0”), link or caption to future “Metod & källor” page if present.

## Files to change

| File | Role |
|------|------|
| [app/styles/theme.py](app/styles/theme.py) | New `.lp-*` CSS classes; `render_landing_*` helpers including optional `render_landing_weights_bar()` or SVG snippet strings |
| [app/main.py](app/main.py) | Compose landing from helpers + computed stats; keep sidebar/session state unchanged |

Optional: [app/components/landing_visuals.py](app/components/landing_visuals.py) — only if SVG/HTML strings become large; keeps `main.py` readable.

## What stays out of scope

- New Python dependencies.
- Full ECharts on the landing page (heavy; inner pages already own charts).
- English user-facing strings.

## Verification

- `streamlit run app/main.py` — layout at wide and ~375px width, no horizontal scroll.
- [scripts/verify_swedish_ui.py](scripts/verify_swedish_ui.py) passes.
- Manual: tab to page links/cards, visible focus; hover states; read hero + explain blocks aloud for clarity.

## Optional ui-ux-pro-max CLI

If you want extra landing-structure keywords from the skill database (not required for implementation):

```bash
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "fintech municipal dashboard Sweden institutional landing" --design-system -p "KRI"
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "landing hero trust credibility" --domain landing
```

Paths assume the skill lives at `~/.claude/skills/ui-ux-pro-max/`; adjust if your machine differs.
