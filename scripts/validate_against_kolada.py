"""
Cross-check the pipeline against Kolada's published municipal KPIs.

The unit tests anchor national totals; this script checks every
municipality-year against an independent publisher. It needs network access,
so it is run on demand rather than in pytest:

    python scripts/validate_against_kolada.py

Checks
  1. Unemployment equals Kolada N03937 (the source series itself).
  2. Debt (total borrowing) equals Kolada N03145 "Summa lån kommun exkl.
     vidareutlåning" plus onlending (SCB 088 + 135) plus bonds (SCB 136).
     Kolada publishes N03145 from 2019 and excludes bonds, which SCB moved to
     a separate post that year; onlending is kept in our measure because SCB's
     088 is reported inconsistently (docs/methodology.md, Section 7.4).
  3. SCB long-term liabilities (post 089) equal Kolada N03046.

Exit code 0 when every check passes.
"""

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import BALANCE_SHEET_POSTS, YEARS

KOLADA = "https://api.kolada.se/v3/data/kpi/{kpi}/year/{years}"
CACHE = PROJECT_ROOT / "data" / "cache"
BASE = PROJECT_ROOT / "data" / "processed" / "kri_base_data.parquet"
REL_TOL = 0.001  # 0.1 %


def kolada(kpi: str) -> pd.Series:
    url = KOLADA.format(kpi=kpi, years=",".join(str(y) for y in YEARS))
    rows = []
    while url:
        page = json.load(urllib.request.urlopen(url, timeout=60))
        for item in page["values"]:
            for v in item["values"]:
                if v.get("gender") == "T" and v.get("value") is not None:
                    rows.append((item["municipality"], int(item["period"]), float(v["value"])))
        url = page.get("next_url")
    s = pd.DataFrame(rows, columns=["municipality_code", "year", "value"])
    return s.set_index(["municipality_code", "year"])["value"]


def compare(label: str, ours: pd.Series, theirs: pd.Series) -> bool:
    j = pd.concat([ours.rename("ours"), theirs.rename("kolada")], axis=1, join="inner").dropna()
    diff = (j["ours"] - j["kolada"]).abs()
    ok = diff <= REL_TOL * j["kolada"].abs().clip(lower=1.0)
    status = "PASS" if ok.all() else "FAIL"
    print(f"[{status}] {label}: {int(ok.sum())}/{len(j)} municipality-years within 0.1 %"
          f" (max abs diff {diff.max():.3g})")
    if not ok.all():
        print(j[~ok].head(10).to_string())
    return bool(ok.all())


def main() -> int:
    base = pd.read_parquet(BASE).set_index(["municipality_code", "year"])
    bs = pd.read_parquet(CACHE / "balance_sheet.parquet")
    bs = bs[bs["municipality_code"].str.len() == 4]
    posts = bs.pivot_table(index=["municipality_code", "year"], columns="balanspost", values="value")
    pop = pd.read_parquet(CACHE / "population.parquet")
    pop = pop[pop["municipality_code"].str.len() == 4].groupby(["municipality_code", "year"])["value"].sum()
    per_capita = lambda tkr: tkr * 1000 / pop.reindex(tkr.index)

    onlending = (posts[BALANCE_SHEET_POSTS["onlending_to_group"]].fillna(0)
                 + posts[BALANCE_SHEET_POSTS["onlending_short_term"]].fillna(0))
    bonds = posts["136"].fillna(0)

    results = [
        compare("Unemployment vs N03937", base["unemployment"], kolada("N03937")),
        compare("Debt vs N03145 + onlending + bonds", base["debt_per_capita"],
                kolada("N03145") + per_capita(onlending + bonds)),
        compare("Post 089 vs N03046", per_capita(posts[BALANCE_SHEET_POSTS["long_term_liabilities"]]),
                kolada("N03046")),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
