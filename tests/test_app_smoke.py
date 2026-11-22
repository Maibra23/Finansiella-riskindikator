"""Smoke tests: every page renders through the router without exceptions.

Runs the real app headless with streamlit.testing.v1.AppTest, so the pages,
shared shell, data module and components are all exercised together.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "app" / "main.py"
RESULTS = ROOT / "data" / "processed" / "kri_results.parquet"

# (page path as registered in app/main.py, heading expected on the page)
PAGES = [
    ("views/startsida.py", "Kommunal finansiell riskindikator"),
    ("views/riksoversikt.py", "Riksöversikt"),
    ("views/kommunanalys.py", "Kommunanalys"),
    ("views/riskdekomposition.py", "Riskdekomposition"),
    ("views/kallor.py", "Datakällor och metod"),
]

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not RESULTS.exists(), reason="kri_results.parquet not built"),
]


def _app():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(MAIN), default_timeout=180)
    at.run()
    return at


def _all_markdown(at) -> str:
    return "\n".join(m.value for m in at.markdown)


@pytest.mark.parametrize("path,heading", PAGES)
def test_page_renders(path: str, heading: str) -> None:
    at = _app()
    at.switch_page(path).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert heading in _all_markdown(at)


def test_every_page_runs_through_the_router() -> None:
    """Each page gets the shared sidebar (brand, navigation, year).

    Regression: while the views lived in app/pages/, Streamlit's legacy
    multipage mode could run a deep-linked page without the router, which
    left it without sidebar and crashed on the missing year.
    """
    at = _app()
    for path, _ in PAGES:
        at.switch_page(path).run()
        assert not at.exception, path
        assert at.sidebar.get("button_group"), f"{path}: sidebar year selector missing"
        assert any("Kommunal Risk" in m.value for m in at.sidebar.markdown), path


def test_year_persists_across_pages() -> None:
    """Regression for U2: visiting Startsida used to reset the selected year."""
    at = _app()
    at.switch_page("views/riksoversikt.py").run()
    year_pills = at.sidebar.get("button_group")[0]
    assert year_pills.key == "ar"
    year_pills.set_value(2015).run()
    assert at.session_state["selected_year"] == 2015
    for path, _ in PAGES:
        at.switch_page(path).run()
        assert not at.exception, path
        assert at.session_state["selected_year"] == 2015, path


def test_year_can_be_shared_in_the_url() -> None:
    """The year widget is bound to ?ar=, so a shared link opens that year."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(MAIN), default_timeout=180)
    at.query_params["ar"] = "2015"
    at.run()
    assert at.session_state["selected_year"] == 2015


def test_kommun_selection_is_shared() -> None:
    at = _app()
    at.switch_page("views/kommunanalys.py").run()
    at.selectbox(key="ka_muni_select").select("Eskilstuna").run()
    at.switch_page("views/riskdekomposition.py").run()
    assert at.selectbox(key="rd_muni_select").value == "Eskilstuna"


def test_kpi_counts_and_delta_signs() -> None:
    """4 KPIs on Riksöversikt, 6 on Kommunanalys; deltas start with the sign of the change."""
    at = _app()
    at.switch_page("views/riksoversikt.py").run()
    assert len([m for m in at.metric if m.label != ""]) >= 4

    df = pd.read_parquet(RESULTS)
    a = df[df["municipality_name"] == "Ale"].set_index("year")
    kri_up = a.loc[2024, "kri_score"] > a.loc[2023, "kri_score"]

    at.switch_page("views/kommunanalys.py").run()
    at.selectbox(key="ka_muni_select").select("Ale").run()
    kpis = [m for m in at.metric if m.label.startswith("KRI")]
    assert kpis, "KRI metric missing"
    assert kpis[0].delta.startswith("+" if kri_up else "-")
    assert len(at.metric) >= 6


def test_risk_filter_empty_means_all() -> None:
    at = _app()
    at.switch_page("views/riksoversikt.py").run()
    assert any("Visar alla" in c.value for c in at.caption)


def test_pages_render_without_sensitivity_layer(monkeypatch, tmp_path) -> None:
    """The optional kri_sensitivity.parquet may be absent: no column, no sentence, no error."""
    import streamlit as st

    import app.data as data

    monkeypatch.setattr(data, "SENSITIVITY_PATH", tmp_path / "missing.parquet")
    st.cache_data.clear()
    try:
        at = _app()
        for path, heading in PAGES:
            at.switch_page(path).run()
            assert not at.exception, (path, [e.value for e in at.exception])
            assert not at.error, path
            assert heading in _all_markdown(at)
            if path != "views/kallor.py":  # Källor describes the method in static text
                assert "Osäkerhet" not in _all_markdown(at), path
    finally:
        st.cache_data.clear()
