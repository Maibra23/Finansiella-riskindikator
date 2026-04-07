---
name: KRI Pre-Publication Review
overview: Comprehensive pre-publication audit of the KRI Streamlit dashboard, covering bugs, inefficiencies, UX inconsistencies, deployment readiness, and README accuracy.
todos:
  - id: fix-pipeline
    content: Add KRIBuilder().build() call to run_pipeline.py or update README with separate index build step
    status: pending
  - id: remove-unused-deps
    content: Remove plotly and httpx from requirements.txt
    status: pending
  - id: fix-hardcoded-date
    content: Update or dynamically generate 'Senast uppdaterad' date in sidebar footers
    status: pending
  - id: consolidate-data-loader
    content: Extract duplicate _load() functions to shared module
    status: pending
  - id: fix-pdf-download-ux
    content: Refactor PDF download to single-click experience
    status: pending
  - id: delete-unused-map
    content: Remove unused sweden_map.py component
    status: pending
  - id: add-geojson-error-handling
    content: Add graceful error handling if GeoJSON file is missing
    status: pending
  - id: update-readme
    content: "Fix README inaccuracies: filenames, pipeline steps, tooltip description"
    status: pending
  - id: verify-license
    content: Confirm LICENSE file contains MIT license text
    status: pending
  - id: accessibility-audit
    content: Add ARIA labels to custom HTML cards and verify color contrast
    status: pending
isProject: false
---

# KRI Dashboard Pre-Publication Review

## Executive Summary

After reviewing the entire codebase, this dashboard is well-structured with a clean separation of concerns, comprehensive data pipeline, and professional UI. However, there are several issues that should be addressed before Streamlit Cloud deployment.

---

## Critical Issues (Must Fix Before Publishing)

### 1. Pipeline/Build Step Missing from README

**Problem:** The README step 4 says `python scripts/run_pipeline.py` builds the index, but this script only produces `kri_base_data.parquet`. The actual KRI index (`kri_results.parquet` required by the dashboard) is built by `KRIBuilder().build()` which is NOT called by `run_pipeline.py`.

**Location:** [scripts/run_pipeline.py](scripts/run_pipeline.py) lines 1-254

**Fix:** Either:
- Add `KRIBuilder().build()` call to the end of `run_pipeline.py`, OR
- Update README to include a second step: `python -c "from src.index_builder import KRIBuilder; KRIBuilder().build()"`

### 2. Unused Dependency: Plotly

**Problem:** `plotly>=5.18.0` is in [requirements.txt](requirements.txt) but never imported anywhere in the codebase. This bloats the deployment.

**Fix:** Remove `plotly>=5.18.0` from requirements.txt

### 3. Unused Dependency: httpx

**Problem:** `httpx>=0.25.0` is listed but the code uses `requests` exclusively.

**Fix:** Remove `httpx>=0.25.0` from requirements.txt

### 4. Hardcoded Year in Sidebar Footer

**Problem:** The sidebar shows "Senast uppdaterad 2024-12-31" hardcoded in multiple files.

**Locations:**
- [app/main.py](app/main.py) line 149
- [app/pages/riksoversikt.py](app/pages/riksoversikt.py) line 131

**Fix:** Either make this dynamic (`datetime.now().strftime(...)`) or update to current date and add a note in docs to update on each release.

---

## High Priority Issues (Should Fix)

### 5. Duplicate Data Loading in Session State

**Problem:** Each page defines its own `@st.cache_data` function `_load()` that reads the same parquet file. While session_state lookup works after main.py loads, the cache functions create redundant entries if a page is visited directly via URL.

**Locations:**
- [app/main.py](app/main.py) `load_kri_data()` 
- [app/pages/riksoversikt.py](app/pages/riksoversikt.py) `_load()` (identical logic)
- [app/pages/riskdekomposition.py](app/pages/riskdekomposition.py) `_load()` (identical logic)
- [app/pages/kommunanalys.py](app/pages/kommunanalys.py) `_load()` (identical logic)

**Fix:** Extract to a shared module `app/utils/data_loader.py` with single cached loader.

### 6. PDF Download Button Nesting Issue

**Problem:** In [app/pages/kommunanalys.py](app/pages/kommunanalys.py) lines 448-467, clicking the PDF button generates the PDF and then creates a nested download button. This is poor UX - clicking once should trigger download.

**Fix:** Use `st.session_state` to track PDF generation state, or generate on load with caching.

### 7. sweden_map.py Component Unused

**Problem:** [app/components/sweden_map.py](app/components/sweden_map.py) exists but is never imported or used by any page. The riksoversikt page uses Folium choropleth instead.

**Fix:** Delete `sweden_map.py` to avoid confusion, or document it as an alternative implementation.

### 8. Missing Error Handling for GeoJSON

**Problem:** If `data/geo/kommuner.geojson` is missing, the choropleth will crash with an unhandled exception.

**Location:** [app/components/sweden_choropleth.py](app/components/sweden_choropleth.py) line 27

**Fix:** Add graceful error handling with user-friendly message.

---

## Medium Priority Issues (Nice to Fix)

### 9. Inconsistent Spacing Between Pages

**Problem:** Different spacer heights used across pages:
- riksoversikt: `<div style='height:16px'>` 
- riskdekomposition/kommunanalys: `<div style='height:24px'>`

**Fix:** Standardize on one spacing value or use CSS class.

### 10. README Inaccuracies

| Section | Issue |
|---------|-------|
| Project Structure | Lists `1_riksoversikt.py` but actual file is `riksoversikt.py` (no prefix) |
| Project Structure | Missing `sweden_choropleth.py` in components list |
| Quick start | References `scripts/setup.sh` which exists but path shows `kommun-risk-dashboard/` - actual repo folder differs |
| Visualization | States "navy tooltip with gold border" but code uses white background tooltip |
| API Documentation | SCB example shows empty `values: []` array - could clarify this fetches all |

### 11. Missing LICENSE File Content Check

**Problem:** LICENSE file exists but content wasn't verified. README says MIT License.

**Fix:** Verify LICENSE contains actual MIT text.

### 12. Tooltip Style Mismatch with PRD

**Problem:** PRD (`docs/Prd.md`) describes dark navy tooltips; actual implementation uses light white tooltips in `get_tooltip_style()`.

**Location:** [app/styles/theme.py](app/styles/theme.py) line 970-988

**Fix:** Either update PRD to match implementation, or adjust tooltip styling if dark was intentional.

---

## Performance Considerations

### 13. Choropleth Map Re-renders

**Problem:** The Folium map is rendered fresh on every filter change. For 290 polygons this is noticeable.

**Potential Optimization:** Cache the base map object and only update styles on filter change (complex to implement with Folium/Streamlit).

### 14. Large CSS Block in Theme

**Problem:** ~900 lines of CSS injected via `st.markdown()` on every page load.

**Mitigation:** This is acceptable for Streamlit but consider extracting to external CSS if performance is measured as poor.

---

## Accessibility Issues

### 15. Missing ARIA Labels on Interactive Elements

**Problem:** Custom HTML cards (`kpi-card`, `nav-card`) lack proper ARIA roles/labels for screen readers.

**Fix:** Add `role="region"`, `aria-label` attributes to card divs.

### 16. Color Contrast in Risk Pills

**Problem:** Medium risk pill uses `#8B6914` on `rgba(212,160,60,0.12)` - may not meet WCAG AA contrast.

**Fix:** Verify with contrast checker; may need darker text.

### 17. Scroll Wheel Disabled on Map

**Problem:** `scrollWheelZoom=False` in Folium map may confuse users who expect scroll-to-zoom.

**Location:** [app/components/sweden_choropleth.py](app/components/sweden_choropleth.py) line 93

**Fix:** Consider enabling or adding visible zoom controls with tooltip explaining interaction.

---

## Deployment Readiness Checklist

- [ ] **Fix pipeline step** - Critical for fresh deployment
- [ ] **Remove unused deps** - Faster deployment, smaller image
- [ ] **Verify data files exist** - Add graceful handling if missing
- [ ] **Test with `streamlit run app/main.py --server.address 0.0.0.0`**
- [ ] **Verify all Swedish text** - Run existing verify_swedish_ui.py
- [ ] **Check Streamlit Cloud requirements** - No path issues with OneDrive folder names

---

## README Update Requirements

1. Fix the pipeline command to include index building step
2. Update project structure to match actual filenames
3. Correct tooltip description in Visualization section
4. Remove or note `setup.sh` requires bash (not available on Windows)
5. Add Streamlit Cloud deployment instructions
6. Update "last updated" date references

---

## Files to Delete (Cleanup)

- `app/components/sweden_map.py` (unused ECharts map wrapper)

---

## Summary by Priority

| Priority | Count | Action |
|----------|-------|--------|
| Critical | 4 | Must fix before publish |
| High | 4 | Should fix for quality |
| Medium | 5 | Nice to have |
| Perf/A11y | 5 | Consider for polish |

**Estimated effort:** 2-4 hours for critical+high priority fixes
