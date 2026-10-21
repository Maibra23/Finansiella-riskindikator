"""
PDF report generator for Kommunal Finansiell Riskindikator.

Generates a 5-page professional PDF report in Swedish using reportlab.
All report content is in Swedish. Code identifiers and comments are in English.
"""

from __future__ import annotations

import io
import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    FrameBreak,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.frames import Frame

from src.config import SENSITIVITY
from src.risk_scale import RiskScale

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Brand colours (matching dashboard theme)
# ---------------------------------------------------------------------------

C_NAVY = colors.HexColor("#0B1F3F")
C_NAVY_LIGHT = colors.HexColor("#1B2A4A")
C_GOLD = colors.HexColor("#C4A35A")
C_LOW = colors.HexColor("#2E7D5B")
C_MED = colors.HexColor("#D4A03C")
C_HIGH = colors.HexColor("#B94A48")
C_BG = colors.HexColor("#F7F8FA")
C_BORDER = colors.HexColor("#EEF0F3")
C_TEXT = colors.HexColor("#1A1A2E")
C_MUTED = colors.HexColor("#6B7280")
C_WHITE = colors.white
C_BLACK = colors.black

PAGE_W, PAGE_H = A4
MARGIN = 2.5 * cm
CONTENT_W = PAGE_W - 2 * MARGIN


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=C_WHITE,
            alignment=TA_LEFT,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#C8D0DC"),
            alignment=TA_LEFT,
            spaceBefore=8,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#9CA3AF"),
            alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=24,
            textColor=C_NAVY,
            spaceBefore=20,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            textColor=C_NAVY,
            spaceBefore=14,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=C_TEXT,
            spaceAfter=6,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=15,
            textColor=C_TEXT,
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=C_MUTED,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=C_MUTED,
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=C_WHITE,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=C_TEXT,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=C_NAVY,
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=C_MUTED,
            alignment=TA_CENTER,
        ),
    }


# ---------------------------------------------------------------------------
# Page event callbacks (header / footer)
# ---------------------------------------------------------------------------

class _KRIDocTemplate(BaseDocTemplate):
    """Custom doc template that draws a footer on every page except the cover."""

    def __init__(self, filename_or_buf: Any, **kwargs: Any) -> None:
        super().__init__(filename_or_buf, **kwargs)
        self._page_number = 0

    def handle_pageBegin(self) -> None:
        super().handle_pageBegin()
        self._page_number += 1

    def handle_pageEnd(self) -> None:
        super().handle_pageEnd()
        canvas = self.canv
        page = self._page_number

        # Cover page: no footer
        if page == 1:
            return

        # Footer bar
        canvas.saveState()
        canvas.setFillColor(C_BORDER)
        canvas.rect(0, 0.7 * cm, PAGE_W, 0.04 * cm, fill=1, stroke=0)

        # Left: source attribution
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(C_MUTED)
        canvas.drawString(MARGIN, 0.45 * cm, "Källa: SCB, Arbetsförmedlingen/Kolada")

        # Centre: KRI label
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(C_NAVY)
        label = "Kommunal Finansiell Riskindikator"
        canvas.drawCentredString(PAGE_W / 2, 0.45 * cm, label)

        # Right: page number
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(C_MUTED)
        canvas.drawRightString(PAGE_W - MARGIN, 0.45 * cm, f"Sida {page - 1}")
        canvas.restoreState()


SENSITIVITY_PATH = PROJECT_ROOT / "data" / "processed" / "kri_sensitivity.parquet"


def _load_sensitivity() -> pd.DataFrame | None:
    """Weight-sensitivity band, or None when the optional layer is not built."""
    if not SENSITIVITY_PATH.exists():
        return None
    try:
        df = pd.read_parquet(SENSITIVITY_PATH)
        df["year"] = df["year"].astype(int)
        return df
    except Exception as exc:
        logger.warning("Could not read sensitivity layer: %s", exc)
        return None


def _uncertainty_by_rank(
    kri_df: pd.DataFrame, sensitivity_df: pd.DataFrame | None, year: int
) -> dict[int, str] | None:
    """Map published rank -> pre-formatted uncertainty cell for *year*."""
    if sensitivity_df is None:
        return None
    merged = kri_df.merge(sensitivity_df, on=["municipality_code", "year"])
    sub = merged[merged["year"] == year]
    if sub.empty:
        return None
    return {
        int(r["rank"]): (
            f"{int(r['rank_p05'])}-{int(r['rank_p95'])}"
            if bool(r["is_robust"])
            else "gränsfall"
        )
        for _, r in sub.iterrows()
    }


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _distribution_drawing(
    kri_scores: list[float],
    width: float,
    height: float,
    scale: RiskScale | None = None,
) -> Drawing:
    """Return a reportlab Drawing with a binned histogram coloured by risk zone.

    Uses the same empirical percentiles as the dashboard and the risk_class
    column, so the PDF cannot disagree with the app it was exported from.
    """
    scale = scale or RiskScale.from_scores(kri_scores)
    n_bins = 20
    lo, hi = -scale.extent, scale.extent
    step = (hi - lo) / n_bins
    edges = [lo + i * step for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for x in kri_scores:
        idx = min(int((max(x, lo) - lo) / step), n_bins - 1)
        counts[idx] += 1

    d = Drawing(width, height)
    bar_w = (width - 40) / n_bins
    max_count = max(counts) if counts else 1
    chart_h = height - 30

    for i, cnt in enumerate(counts):
        x0 = 20 + i * bar_w
        bh = (cnt / max_count) * chart_h
        center = edges[i] + step / 2
        fill = {"Låg": C_LOW, "Hög": C_HIGH, "Medel": C_MED}[scale.classify(center)]
        r = Rect(x0, 10, bar_w - 1, bh, fillColor=fill, strokeColor=None)
        d.add(r)

    # X-axis line
    d.add(Line(20, 10, width - 20, 10, strokeColor=C_BORDER, strokeWidth=0.5))

    # Axis labels
    _lo_lbl = f"{-scale.extent:.1f}".replace(".", ",")
    _hi_lbl = f"+{scale.extent:.1f}".replace(".", ",")
    for label, xpos in [(_lo_lbl, 20), ("0", width / 2), (_hi_lbl, width - 20)]:
        d.add(String(xpos, 1, label, fontName="Helvetica", fontSize=7, fillColor=C_MUTED,
                     textAnchor="middle"))

    # X-axis caption
    d.add(String(width / 2, height - 14, "KRI Poäng",
                 fontName="Helvetica", fontSize=8, fillColor=C_MUTED, textAnchor="middle"))
    return d


def _trend_drawing(yearly_avg: dict[int, float], width: float, height: float) -> Drawing:
    """Return a small line chart of national-average KRI over time."""
    d = Drawing(width, height)
    years = sorted(yearly_avg)
    vals = [yearly_avg[y] for y in years]
    if not years:
        return d

    pad_l, pad_r, pad_b, pad_t = 28, 10, 18, 10
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_b - pad_t

    v_min, v_max = min(vals) - 0.05, max(vals) + 0.05
    v_range = v_max - v_min or 1.0

    def xp(i: int) -> float:
        return pad_l + (i / max(len(years) - 1, 1)) * chart_w

    def yp(v: float) -> float:
        return pad_b + ((v - v_min) / v_range) * chart_h

    # Zero line
    y0 = yp(0)
    if pad_b <= y0 <= pad_b + chart_h:
        d.add(Line(pad_l, y0, pad_l + chart_w, y0,
                   strokeColor=C_BORDER, strokeWidth=0.6, strokeDashArray=[3, 3]))

    # Line segments
    for i in range(len(years) - 1):
        d.add(Line(xp(i), yp(vals[i]), xp(i + 1), yp(vals[i + 1]),
                   strokeColor=C_NAVY, strokeWidth=1.5))

    # Year labels (every 2)
    for i, yr in enumerate(years):
        if i % 2 == 0:
            d.add(String(xp(i), 2, str(yr),
                         fontName="Helvetica", fontSize=6.5, fillColor=C_MUTED, textAnchor="middle"))

    # Y-axis labels
    for v_tick in [v_min, 0, v_max]:
        y_t = yp(v_tick)
        if pad_b <= y_t <= pad_b + chart_h:
            d.add(String(pad_l - 2, y_t - 3, f"{v_tick:.2f}".replace(".", ","),
                         fontName="Helvetica", fontSize=6, fillColor=C_MUTED, textAnchor="end"))

    return d


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

def _risk_table(
    rows: list[tuple[int, str, float, str]],
    styles_dict: dict[str, ParagraphStyle],
    uncertainty: dict[int, str] | None = None,
) -> Table:
    """Build a styled table: Rang | Kommun | KRI Poäng | Riskklass [| Osäkerhet].

    *uncertainty* maps rank to a pre-formatted cell ("4-13" or "gränsfall").
    Omitted when the weight-sensitivity layer is not built, so the exported
    report carries exactly the same caveats the screen does: no more, no less.
    """
    show_unc = bool(uncertainty)
    header = [
        Paragraph("Rang", styles_dict["table_header"]),
        Paragraph("Kommun", styles_dict["table_header"]),
        Paragraph("KRI Poäng", styles_dict["table_header"]),
        Paragraph("Riskklass", styles_dict["table_header"]),
    ]
    if show_unc:
        header.append(Paragraph("Osäkerhet", styles_dict["table_header"]))
    data = [header]
    risk_color_map = {"Hög": C_HIGH, "Medel": C_MED, "Låg": C_LOW}
    for rank, name, score, risk in rows:
        row = [
            Paragraph(str(rank), styles_dict["table_cell"]),
            Paragraph(name, styles_dict["table_cell"]),
            Paragraph(f"{score:.3f}".replace(".", ","), styles_dict["table_cell"]),
            Paragraph(risk, styles_dict["table_cell"]),
        ]
        if show_unc:
            row.append(Paragraph((uncertainty or {}).get(rank, "-"), styles_dict["table_cell"]))
        data.append(row)

    col_widths = (
        [1.4 * cm, 4.8 * cm, 2.4 * cm, 2.2 * cm, 2.4 * cm]
        if show_unc
        else [1.4 * cm, 6.2 * cm, 2.6 * cm, 2.4 * cm]
    )
    t = Table(data, colWidths=col_widths, repeatRows=1)

    ts = TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        # Zebra stripes
        *[("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F9FAFB"))
          for i in range(2, len(data), 2)],
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, C_GOLD),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
    ])
    # Colour risk class cells
    for row_idx, (_, _, _, risk) in enumerate(rows, start=1):
        c = risk_color_map.get(risk, C_MUTED)
        ts.add("TEXTCOLOR", (3, row_idx), (3, row_idx), c)
        ts.add("FONTNAME", (3, row_idx), (3, row_idx), "Helvetica-Bold")
    t.setStyle(ts)
    return t


# ---------------------------------------------------------------------------
# Page content builders
# ---------------------------------------------------------------------------

def _page1_cover(canvas: Any, doc: Any, report_year: int) -> None:
    """Draw full-bleed navy cover directly onto canvas."""
    canvas.saveState()

    # Navy background
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Gold accent strip (left edge)
    canvas.setFillColor(C_GOLD)
    canvas.rect(0, 0, 0.55 * cm, PAGE_H, fill=1, stroke=0)

    # Bottom data-band
    canvas.setFillColor(C_NAVY_LIGHT)
    canvas.rect(0, 0, PAGE_W, 3.5 * cm, fill=1, stroke=0)

    # Title block
    tx = MARGIN + 0.8 * cm
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(tx, PAGE_H - 5.5 * cm, "Kommunal Finansiell")
    canvas.drawString(tx, PAGE_H - 7.0 * cm, "Riskindikator")

    canvas.setFillColor(C_GOLD)
    canvas.setFont("Helvetica-Bold", 44)
    canvas.drawString(tx, PAGE_H - 9.5 * cm, str(report_year))

    canvas.setFillColor(colors.HexColor("#C8D0DC"))
    canvas.setFont("Helvetica", 13)
    canvas.drawString(tx, PAGE_H - 11.2 * cm,
                      "Analys av strukturell ekonomisk sårbarhet")
    canvas.drawString(tx, PAGE_H - 12.3 * cm,
                      "i Sveriges 290 kommuner")

    # Decorative rule
    canvas.setStrokeColor(C_GOLD)
    canvas.setLineWidth(1.5)
    canvas.line(tx, PAGE_H - 13.0 * cm, tx + 5 * cm, PAGE_H - 13.0 * cm)

    # Meta block
    canvas.setFont("Helvetica", 9.5)
    canvas.setFillColor(colors.HexColor("#9CA3AF"))
    today = date.today().strftime("%d %B %Y").lstrip("0")
    canvas.drawString(tx, 2.6 * cm, f"Analysperiod: 2010 till {report_year}")
    canvas.drawString(tx, 1.9 * cm, f"Publicerad: {today}")
    canvas.drawString(tx, 1.2 * cm, "Källa: SCB, Arbetsförmedlingen/Kolada")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_report(
    kri_df: pd.DataFrame | None = None,
    output_path: Path | str | None = None,
    report_year: int = 2024,
) -> bytes:
    """Generate the KRI PDF report and return PDF bytes.

    Parameters
    ----------
    kri_df:
        Full KRI results DataFrame.  Loaded from parquet if None.
    output_path:
        If given, also write the PDF to this file path.
    report_year:
        Year used for the analysis snapshot (default 2024).

    Returns
    -------
    PDF bytes.
    """
    if kri_df is None:
        p = PROJECT_ROOT / "data" / "processed" / "kri_results.parquet"
        kri_df = pd.read_parquet(p)
        kri_df["year"] = kri_df["year"].astype(int)

    latest = kri_df[kri_df["year"] == report_year].copy()
    if latest.empty:
        report_year = int(kri_df["year"].max())
        latest = kri_df[kri_df["year"] == report_year].copy()

    S = _styles()

    # ---------- KPI values ----------
    n_high = int((latest["risk_class"] == "Hög").sum())
    n_med = int((latest["risk_class"] == "Medel").sum())
    n_low = int((latest["risk_class"] == "Låg").sum())
    avg_kri = float(latest["kri_score"].mean())
    median_debt = float(latest["debt_per_capita"].median())

    # Figures quoted in the findings and conclusions, computed so the text cannot
    # drift from the data.
    _ranks = kri_df.pivot(index="municipality_code", columns="year", values="rank")
    _years = sorted(_ranks.columns)
    rank_corr_consecutive = float(np.mean([
        _ranks[a].corr(_ranks[b], method="spearman") for a, b in zip(_years, _years[1:])
    ]))
    rank_corr_span = float(_ranks[_years[0]].corr(_ranks[_years[-1]], method="spearman"))
    n_always_high = int(
        (kri_df.pivot(index="municipality_code", columns="year", values="risk_class") == "Hög")
        .all(axis=1).sum()
    )
    _sd = kri_df.groupby("year")["kri_score"].std()
    _contrib = latest[[f"contribution_{k}" for k in
                       ("debt", "unemployment", "dependency", "population", "tax_base")]]
    _cov = _contrib.cov()
    var_share = {c.removeprefix("contribution_"): float(_cov[c].sum() / latest["kri_score"].var())
                 for c in _contrib.columns}

    def _sv(x: float, d: int = 2) -> str:
        return f"{x:.{d}f}".replace(".", ",")

    def _pct(x: float) -> str:
        return f"{x * 100:.0f} %"

    top20_rows = latest.sort_values("rank").head(20)
    top5_high = top20_rows.head(5)
    bot5 = latest.sort_values("rank", ascending=False).head(5)

    yearly_avg: dict[int, float] = (
        kri_df.groupby("year")["kri_score"].mean().to_dict()
    )
    kri_scores_list = latest["kri_score"].tolist()

    yr_min = int(kri_df["year"].min())
    yr_max = int(kri_df["year"].max())
    n_obs = len(kri_df)

    # ---------- Build PDF in-memory ----------
    buf = io.BytesIO()

    doc = _KRIDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 1.0 * cm,
    )

    # Two templates: cover (no frame needed; drawn in onPage) and content pages
    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0, id="cover")
    content_frame = Frame(
        MARGIN, MARGIN + 1.0 * cm,
        CONTENT_W, PAGE_H - 2 * MARGIN - 1.0 * cm,
        id="content",
    )

    def _draw_cover(canvas: Any, doc: Any) -> None:
        _page1_cover(canvas, doc, report_year)

    def _draw_content(canvas: Any, doc: Any) -> None:
        # Subtle top rule in gold
        canvas.saveState()
        canvas.setStrokeColor(C_GOLD)
        canvas.setLineWidth(2.5)
        canvas.line(MARGIN, PAGE_H - MARGIN + 0.3 * cm,
                    PAGE_W - MARGIN, PAGE_H - MARGIN + 0.3 * cm)
        canvas.restoreState()

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_draw_cover),
        PageTemplate(id="content", frames=[content_frame], onPage=_draw_content),
    ])

    story: list[Any] = []

    # ── PAGE 1: Cover (no flowable content; entire page drawn via onPage) ──
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ── PAGE 2: Executive summary ------------------------------------------
    story.append(Paragraph("Sammanfattning", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    intro = (
        f"Kommunal Finansiell Riskindikator (KRI) rangordnar alla Sveriges 290 kommuner "
        f"utifrån ett sammansatt index för strukturell ekonomisk sårbarhet. Indexet kombinerar "
        f"fem nyckelvariabler: skuld per capita, arbetslöshet, försörjningskvot, "
        f"befolkningstillväxt och skattekraft, viktade enligt deras prognostiska relevans "
        f"för kommunal finansiell stabilitet. Analysperioden omfattar åren 2010 till {report_year}, "
        f"vilket inkluderar en full konjunkturcykel med pandemiåren 2020 och 2021 samt "
        f"inflationschocken under 2022 och 2023."
    )
    story.append(Paragraph(intro, S["body"]))
    story.append(Spacer(1, 10))

    # KPI strip
    kpi_data = [
        [
            Paragraph(f"{n_high}", S["kpi_value"]),
            Paragraph(f"{n_med}", S["kpi_value"]),
            Paragraph(f"{n_low}", S["kpi_value"]),
            Paragraph(f"{avg_kri:.3f}".replace(".", ","), S["kpi_value"]),
        ],
        [
            Paragraph("Högrisk kommuner", S["kpi_label"]),
            Paragraph("Medelrisk kommuner", S["kpi_label"]),
            Paragraph("Lågrisk kommuner", S["kpi_label"]),
            Paragraph("Rikssnitt KRI", S["kpi_label"]),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[CONTENT_W / 4] * 4)
    kpi_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FFF5F5")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F0FBF4")),
        ("BOX", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (0, 0), 2, C_HIGH),
        ("LINEBELOW", (1, 0), (1, 0), 2, C_MED),
        ("LINEBELOW", (2, 0), (2, 0), 2, C_LOW),
        ("LINEBELOW", (3, 0), (3, 0), 2, C_GOLD),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Viktigaste fynd", S["h2"]))
    findings = [
        f"Av landets 290 kommuner klassificeras {n_high} (25 %) som högrisk, "
        f"{n_med} (50 %) som medelrisk och {n_low} (25 %) som lågrisk för {report_year}.",
        f"Medianskuld per capita för alla kommuner uppgår till "
        f"{median_debt:,.0f} kr ({report_year}).".replace(",", "\u202f"),
        "Strukturellt svaga kommuner karaktäriseras av kombinationen hög skuld, "
        "hög arbetslöshet och en åldrande befolkning med låg skattekraft.",
        "Storstadskommuner och förorter med stark skattebas (t.ex. Danderyd, Täby, Solna) "
        "uppvisar genomgående låg risk under hela analysperioden.",
        f"Rangordningen är stabil över tid: rangkorrelationen mellan på varandra följande "
        f"år är i genomsnitt {_sv(rank_corr_consecutive)} och {n_always_high} kommuner har "
        f"klassats som högrisk varje år sedan {yr_min}. "
        f"Spridningen mellan kommuner har samtidigt minskat - standardavvikelsen i KRI "
        f"har gått från {_sv(_sd[yr_min])} ({yr_min}) till {_sv(_sd[yr_max])} ({yr_max}).",
    ]
    for f in findings:
        story.append(Paragraph(f"• {f}", S["body"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Fem mest sårbara kommuner", S["h2"]))
    top5_rows_data = [
        (int(r["rank"]), str(r["municipality_name"]), float(r["kri_score"]), str(r["risk_class"]))
        for _, r in top5_high.iterrows()
    ]
    story.append(_risk_table(top5_rows_data, S))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Fem mest robusta kommuner", S["h2"]))
    bot5_rows_data = [
        (int(r["rank"]), str(r["municipality_name"]), float(r["kri_score"]), str(r["risk_class"]))
        for _, r in bot5.sort_values("rank", ascending=False).iterrows()
    ]
    story.append(_risk_table(bot5_rows_data, S))

    story.append(PageBreak())

    # ── PAGE 3: Methodology ------------------------------------------------
    story.append(Paragraph("Metodik", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    story.append(Paragraph("Indexkonstruktion", S["h2"]))
    story.append(Paragraph(
        "KRI beräknas i fyra steg: (1) insamling av årsdata för fem variabler från SCB och "
        "Arbetsförmedlingen/Kolada, (2) tvärsektionell normalisering med z poäng för alla kommuner "
        "inom respektive år, (3) riktningskorrigering så att högt värde alltid innebär hög risk, "
        "samt (4) viktad summering till ett sammansatt index. Formeln är:",
        S["body"],
    ))
    story.append(Paragraph(
        "<b>KRI(i,t) = Σ w<sub>k</sub> · z<sub>k</sub>(i,t)</b>",
        ParagraphStyle("formula", parent=S["body"], fontName="Helvetica-Bold",
                       alignment=TA_CENTER, spaceBefore=6, spaceAfter=6),
    ))
    story.append(Paragraph(
        "där i = kommun, t = år, w<sub>k</sub> = variabelns vikt och "
        "z<sub>k</sub> = riktningskorrigerat z poäng.",
        S["body"],
    ))

    story.append(Paragraph("Variabler och vikter", S["h2"]))
    var_header = [
        Paragraph("Variabel", S["table_header"]),
        Paragraph("Vikt", S["table_header"]),
        Paragraph("Riktning", S["table_header"]),
        Paragraph("Källa", S["table_header"]),
    ]
    var_rows = [
        ("Långfristig skuld per capita (kr)", "25 %", "Hög = hög risk", "SCB BalansKn, post 089"),
        ("Arbetslöshet (%)", "25 %", "Hög = hög risk", "Arbetsförmedlingen/Kolada"),
        ("Försörjningskvot", "20 %", "Hög = hög risk", "SCB BefolkningNy"),
        ("Befolkningstillväxt 5 år (%)", "15 %", "Negativ = hög risk", "SCB BefolkningNy"),
        ("Skattekraft (% av rikssnitt)", "15 %", "Låg = hög risk", "SCB SkatteKraft"),
    ]
    var_data = [var_header] + [
        [Paragraph(c, S["table_cell"]) for c in row]
        for row in var_rows
    ]
    var_table = Table(var_data, colWidths=[5.0 * cm, 1.8 * cm, 3.5 * cm, 4.3 * cm])
    var_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        *[("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F9FAFB"))
          for i in range(2, len(var_data), 2)],
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, C_GOLD),
    ]))
    story.append(var_table)

    story.append(Paragraph("Viktkänslighet", S["h2"]))
    _sens_meth = _load_sensitivity()
    if _sens_meth is None:
        story.append(Paragraph(
            "Vikterna är motiverade utifrån offentlig finansieringsteori och är alltså "
            "valda, inte skattade ur data.",
            S["body"],
        ))
    else:
        _merged_meth = kri_df.merge(_sens_meth, on=["municipality_code", "year"])
        _my = _merged_meth[_merged_meth["year"] == report_year]
        _robust_n = int(_my["is_robust"].sum())
        _modal_ok = int((_my["modal_class"] == _my["risk_class"]).sum())
        _delta_meth = f"{SENSITIVITY['delta']:.2f}".replace(".", ",")
        story.append(Paragraph(
            f"Vikterna är motiverade utifrån offentlig finansieringsteori och är alltså "
            f"valda, inte skattade ur data. För att visa hur mycket rangordningen beror "
            f"på det valet tillåts varje vikt variera likformigt med ±{_delta_meth} kring "
            f"sitt nominella värde, varefter vektorn normeras så att summan förblir 1. "
            f"Indexet räknas om {int(SENSITIVITY['n_draws'])} gånger och kvartilgränserna "
            f"beräknas om inom varje omräkning. En kommun kallas robust när den behåller "
            f"sin riskklass i minst {SENSITIVITY['robust_threshold']:.0%} av omräkningarna.",
            S["body"],
        ))
        story.append(Paragraph(
            f"För {report_year} är {_robust_n} av {len(_my)} kommuner robusta. Framför allt "
            f"gäller att den publicerade riskklassen också är den vanligaste klassen över "
            f"samtliga omräkningar för {_modal_ok} av {len(_my)} kommuner, "
            f"känslighetsanalysen bekräftar indexet snarare än ifrågasätter det. "
            f"Analysen avser osäkerhet i viktningen, inte i underliggande data eller i "
            f"valet av indikatorer.",
            S["body"],
        ))
        story.append(Paragraph(
            "Ett alternativ vore att låta principalkomponentanalys bestämma vikterna. Den "
            "metoden prövades och förkastades: första principalkomponenten laddar negativt "
            "på skuld varje år från 2012 och skulle därmed rangordna de mest skuldsatta "
            "kommunerna bland de minst riskutsatta. Den förklarar dessutom endast 40-44 % "
            "av variansen, och vikterna skattas per år vilket omöjliggör jämförelser "
            "över tid.",
            S["body"],
        ))

    story.append(Paragraph("Klassificering", S["h2"]))
    story.append(Paragraph(
        "Kommuner klassificeras baserat på kvantilandelar inom varje år: kommuner med KRI "
        "under 25:e percentilen = Låg risk (grön), mellan 25:e och 75:e percentilen = Medel risk (gul), "
        "över 75:e percentilen = Hög risk (röd). Klassificeringen är relativ och stabil "
        "mot extremvärden.",
        S["body"],
    ))

    story.append(Paragraph("Datakvalitet", S["h2"]))
    story.append(Paragraph(
        f"Samtliga 290 kommuner har kompletta tidsserier för analysperioden {yr_min} till {yr_max} "
        f"({n_obs} observationer, 0 saknade värden). Gotland (0980) flaggas för delad "
        "redovisning mellan kommunen och regionen; skuld justeras med faktorn 0,65. "
        "Knivsta (0330) bildades 2003 och har begränsad historik.",
        S["body"],
    ))

    story.append(PageBreak())

    # ── PAGE 4: Results ----------------------------------------------------
    story.append(Paragraph(f"Resultat {report_year}", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    # Distribution chart + trend chart side by side
    chart_col_w = CONTENT_W / 2 - 0.3 * cm
    dist_d = _distribution_drawing(kri_scores_list, chart_col_w, 130, RiskScale.from_scores(kri_scores_list))
    trend_d = _trend_drawing(yearly_avg, chart_col_w, 130)

    charts_table = Table(
        [[dist_d, trend_d]],
        colWidths=[chart_col_w + 0.3 * cm, chart_col_w],
    )
    charts_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(charts_table)

    chart_labels = Table(
        [[Paragraph(f"Fördelning av KRI poäng {report_year}", S["small"]),
          Paragraph(f"Rikssnitt KRI {yr_min} till {yr_max}", S["small"])]],
        colWidths=[chart_col_w + 0.3 * cm, chart_col_w],
    )
    chart_labels.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(chart_labels)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Topp 20 högst risk", S["h2"]))
    top20_data = [
        (int(r["rank"]), str(r["municipality_name"]), float(r["kri_score"]), str(r["risk_class"]))
        for _, r in top20_rows.iterrows()
    ]
    _sens_df = _load_sensitivity()
    _unc = _uncertainty_by_rank(kri_df, _sens_df, report_year)
    story.append(_risk_table(top20_data, S, uncertainty=_unc))
    if _unc is not None:
        _delta_sv = f"{SENSITIVITY['delta']:.2f}".replace(".", ",")
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Kolumnen Osäkerhet visar hur rangen rör sig när varje vikt tillåts variera "
            f"med ±{_delta_sv} kring sitt nominella värde och indexet räknas om "
            f"{int(SENSITIVITY['n_draws'])} gånger: intervallet mellan 5:e och 95:e "
            f"percentilen av rangen. Kommuner som byter riskklass i mer än "
            f"{1 - SENSITIVITY['robust_threshold']:.0%} av omräkningarna markeras "
            f"gränsfall och ligger nära gränsen mellan två riskklasser. "
            f"Se avsnittet Viktkänslighet nedan.",
            S["small"],
        ))

    story.append(PageBreak())

    # ── PAGE 5: Conclusions ------------------------------------------------
    story.append(Paragraph("Slutsatser och begränsningar", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    story.append(Paragraph("Huvudslutsatser", S["h2"]))
    conclusions = [
        f"Strukturell ekonomisk sårbarhet bland svenska kommuner är bestående och geografiskt "
        f"koncentrerad. Kommuner med högrisk återfinns systematiskt i glesbygd och bruksorter, "
        f"medan kommuner med lågrisk domineras av storstadsförorter med stark skattebas.",
        f"De fem faktorerna bidrar nästan lika mycket till spridningen i KRI {report_year}: "
        f"arbetslöshet {_pct(var_share['unemployment'])}, skattekraft "
        f"{_pct(var_share['tax_base'])}, försörjningskvot {_pct(var_share['dependency'])}, "
        f"befolkningstillväxt {_pct(var_share['population'])} och skuld "
        f"{_pct(var_share['debt'])}. Skuld per capita väger tyngst i formeln (0,25) men "
        f"bidrar minst, eftersom hög skuld förekommer både i växande och i krympande "
        f"kommuner och därför delvis tar ut de demografiska faktorerna.",
        "Riskklasserna är relativa och definieras av kvartiler inom varje år. Andelen "
        "kommuner i varje klass är därför konstant (25 % Hög, 50 % Medel, 25 % Låg) och "
        "kan inte användas för att avläsa om riket som helhet förbättrats eller försämrats. "
        "Måttet visar hur kommuner förhåller sig till varandra, inte till en absolut nivå.",
        f"Tidsseriestabilitet är hög: rangkorrelationen mellan på varandra följande år är "
        f"i genomsnitt {_sv(rank_corr_consecutive)}, och mellan {yr_min} och {yr_max} "
        f"fortfarande {_sv(rank_corr_span)}. Det bekräftar att KRI mäter strukturell, inte "
        f"konjunkturell, sårbarhet. {n_always_high} kommuner har klassats som Hög risk "
        f"varje år under hela perioden.",
    ]
    for c in conclusions:
        story.append(Paragraph(f"• {c}", S["body"]))

    story.append(Paragraph("Policyimplikationer", S["h2"]))
    story.append(Paragraph(
        "Kommuner med högt KRI bör prioriteras i statliga utjämningssystem och i "
        "regionalpolitiska insatser. Indexet kan tjäna som ett tidigt varningssystem för "
        "kommuner som riskerar att inte klara balanskravet på sikt. SKR och länsstyrelser "
        "rekommenderas att använda KRI som ett komplement till befintliga nyckeltal.",
        S["body"],
    ))

    story.append(Paragraph("Begränsningar", S["h2"]))
    limitations = [
        "KRI är ett relativt index: en kommun som förbättras kan få ett höjt KRI om "
        "omgivande kommuner förbättras ännu mer.",
        "Indexet inkluderar inte externa faktorer som statsbidrag, exploateringsintäkter "
        "eller extraordinära händelser.",
        "Skuldbegreppet avser långfristiga skulder (SCB BalansKn, post 089) och fångar inte "
        "kortfristiga likviditetsrisker. Det omfattar även lån som kommunen vidareutlånat till "
        "egna bolag (post 088), vilket gör skulden högre än kommunens egen nettoupplåning.",
        "Kommuner med befolkning under 5 000 kan ha volatila nyckeltal till följd av "
        "enskilda investeringar eller demografiska händelser.",
    ]
    for lim in limitations:
        story.append(Paragraph(f"• {lim}", S["body"]))

    story.append(Paragraph("Förslag till vidare analys", S["h2"]))
    story.append(Paragraph(
        "Framtida versioner av KRI bör utökas med: (1) soliditet och kassalikviditet som "
        "kompletterande variabler, (2) prognoskomponent baserad på demografiska framskrivningar, "
        "(3) regional aggregering för länsnivåanalys, samt (4) jämförelse med Norden. "
        "En paneldataregressionsanalys av KRI mot faktiska betalningsinställelser och "
        "förändringar av lånerating skulle stärka indexets prediktiva validitet.",
        S["body"],
    ))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=C_BORDER, spaceAfter=8))
    story.append(Paragraph(
        "Källa: SCB Statistikdatabasen (BalansKn, BefolkningNy, SkatteKraft), "
        "Arbetsförmedlingen via Kolada API (N03937). "
        f"Rapport genererad {date.today().strftime('%d.%m.%Y')}.",
        S["small"],
    ))

    # ---------- Build ----------
    doc.build(story)

    pdf_bytes = buf.getvalue()

    if output_path is not None:
        output_path = Path(output_path)  # accept str paths from callers/CLI
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)
        logger.info("PDF saved to %s (%d bytes)", output_path, len(pdf_bytes))

    return pdf_bytes


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = PROJECT_ROOT / "report" / "kri_rapport_2024.pdf"
    generate_report(output_path=out)
    print(f"PDF genererad: {out}  ({out.stat().st_size // 1024} KB)")
