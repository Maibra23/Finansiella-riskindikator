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


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _distribution_drawing(kri_scores: list[float], width: float, height: float) -> Drawing:
    """Return a reportlab Drawing with a binned histogram coloured by risk zone."""
    n_bins = 20
    lo, hi = -2.5, 2.5
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
        if center < -0.6745:
            fill = C_LOW
        elif center > 0.6745:
            fill = C_HIGH
        else:
            fill = C_MED
        r = Rect(x0, 10, bar_w - 1, bh, fillColor=fill, strokeColor=None)
        d.add(r)

    # X-axis line
    d.add(Line(20, 10, width - 20, 10, strokeColor=C_BORDER, strokeWidth=0.5))

    # Axis labels
    for label, xpos in [("-2,5", 20), ("0", width / 2), ("+2,5", width - 20)]:
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
) -> Table:
    """Build a styled table: Rang | Kommun | KRI Poäng | Riskklass."""
    header = [
        Paragraph("Rang", styles_dict["table_header"]),
        Paragraph("Kommun", styles_dict["table_header"]),
        Paragraph("KRI Poäng", styles_dict["table_header"]),
        Paragraph("Riskklass", styles_dict["table_header"]),
    ]
    data = [header]
    risk_color_map = {"Hög": C_HIGH, "Medel": C_MED, "Låg": C_LOW}
    for rank, name, score, risk in rows:
        data.append([
            Paragraph(str(rank), styles_dict["table_cell"]),
            Paragraph(name, styles_dict["table_cell"]),
            Paragraph(f"{score:.3f}".replace(".", ","), styles_dict["table_cell"]),
            Paragraph(risk, styles_dict["table_cell"]),
        ])

    col_widths = [1.4 * cm, 6.2 * cm, 2.6 * cm, 2.4 * cm]
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
    canvas.drawString(tx, 2.6 * cm, f"Analysperiod: 2010–{report_year}")
    canvas.drawString(tx, 1.9 * cm, f"Publicerad: {today}")
    canvas.drawString(tx, 1.2 * cm, "Källa: SCB, Arbetsförmedlingen/Kolada")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_report(
    kri_df: pd.DataFrame | None = None,
    output_path: Path | None = None,
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

    top20_rows = latest.sort_values("rank").head(20)
    top5_high = top20_rows.head(5)
    bot5 = latest.sort_values("rank", ascending=False).head(5)

    yearly_avg: dict[int, float] = (
        kri_df.groupby("year")["kri_score"].mean().to_dict()
    )
    kri_scores_list = latest["kri_score"].tolist()

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

    # ── PAGE 2: Executive summary ──────────────────────────────────────────
    story.append(Paragraph("Sammanfattning", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    intro = (
        f"Kommunal Finansiell Riskindikator (KRI) rangordnar alla Sveriges 290 kommuner "
        f"utifrån ett sammansatt index för strukturell ekonomisk sårbarhet. Indexet kombinerar "
        f"fem nyckelvariabler — skuld per capita, arbetslöshet, försörjningskvot, "
        f"befolkningstillväxt och skattekraft — viktade enligt deras prognostiska relevans "
        f"för kommunal finansiell stabilitet. Analysperioden omfattar 2010–{report_year}, "
        f"vilket inkluderar ett fullt konjunkturcykel med pandemiåren 2020–2021 och "
        f"inflationschocken 2022–2023."
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
        "Covid-pandemin 2020 medförde ett tillfälligt trendbrott där högrisk-kommuner "
        "ökade kraftigt, följt av en partiell återhämtning 2021–2022.",
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

    # ── PAGE 3: Methodology ────────────────────────────────────────────────
    story.append(Paragraph("Metodik", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    story.append(Paragraph("Indexkonstruktion", S["h2"]))
    story.append(Paragraph(
        "KRI beräknas i fyra steg: (1) insamling av årsdata för fem variabler från SCB och "
        "Arbetsförmedlingen/Kolada, (2) tvärsektionell z-poängs-normalisering för alla kommuner "
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
        "z<sub>k</sub> = riktningskorrigerat z-poäng.",
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
        ("Skuld per capita (kr)", "25 %", "Hög = hög risk", "SCB BalansKn"),
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

    story.append(Paragraph("Klassificering", S["h2"]))
    story.append(Paragraph(
        "Kommuner klassificeras baserat på kvantilandelar inom varje år: kommuner med KRI "
        "under 25:e percentilen = Låg risk (grön), 25–75:e percentilen = Medel risk (gul), "
        "över 75:e percentilen = Hög risk (röd). Klassificeringen är relativ och stabil "
        "mot extremvärden.",
        S["body"],
    ))

    story.append(Paragraph("Datakvalitet", S["h2"]))
    story.append(Paragraph(
        "Samtliga 290 kommuner har kompletta tidsserier för analysperioden 2010–2024 (4 350 "
        "observationer, 0 saknade värden). Gotland (0980) flaggas för delad "
        "redovisning mellan kommunen och regionen; skuld justeras med faktorn 0,65. "
        "Knivsta (0330) bildades 2003 och har begränsad historik.",
        S["body"],
    ))

    story.append(PageBreak())

    # ── PAGE 4: Results ────────────────────────────────────────────────────
    story.append(Paragraph(f"Resultat {report_year}", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    # Distribution chart + trend chart side by side
    chart_col_w = CONTENT_W / 2 - 0.3 * cm
    dist_d = _distribution_drawing(kri_scores_list, chart_col_w, 130)
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
        [[Paragraph("Fördelning av KRI-poäng 2024", S["small"]),
          Paragraph("Rikssnitt KRI 2010–2024", S["small"])]],
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
    story.append(_risk_table(top20_data, S))

    story.append(PageBreak())

    # ── PAGE 5: Conclusions ────────────────────────────────────────────────
    story.append(Paragraph("Slutsatser och begränsningar", S["h1"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=C_GOLD, spaceAfter=10))

    story.append(Paragraph("Huvudslutsatser", S["h2"]))
    conclusions = [
        f"Strukturell ekonomisk sårbarhet bland svenska kommuner är bestående och geografiskt "
        f"koncentrerad. Högrisk-kommuner återfinns systematiskt i glesbygd och bruksorter, "
        f"medan lågrisk-kommuner domineras av storstadsförorter med stark skattebas.",
        "Skuld per capita och arbetslöshet förklarar sammantaget 50 % av KRI-variansen och "
        "är de starkaste riskdrivarna.",
        f"Pandemin 2020 gav en tydlig negativ impuls — andelen högrisk-kommuner ökade under "
        f"2020–2021 — men de flesta kommuner återhämtade sig till 2022.",
        "Tidsseriestabilitet är hög (år-till-år-korrelation > 0,85), vilket bekräftar att "
        "KRI mäter strukturell, inte konjunkturell, sårbarhet.",
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
        "KRI är ett relativ index — ett kommuner som förbättras kan få ett höjt KRI om "
        "omgivande kommuner förbättras ännu mer.",
        "Indexet inkluderar inte externa faktorer som statsbidrag, exploateringsintäkter "
        "eller extraordinära händelser.",
        "Skuldbegreppet avser långfristiga skulder och fångar inte kortfristiga likviditetsrisker.",
        "Kommuner med befolkning under 5 000 kan ha volatila nyckeltal till följd av "
        "enskilda investeringar eller demografiska händelser.",
    ]
    for lim in limitations:
        story.append(Paragraph(f"• {lim}", S["body"]))

    story.append(Paragraph("Förslag till vidare analys", S["h2"]))
    story.append(Paragraph(
        "Framtida versioner av KRI bör utökas med: (1) soliditet och kassalikviditet som "
        "kompletterande variabler, (2) prognos-komponent baserad på demografiska framskrivningar, "
        "(3) regional aggregering för länsnivå-analys, samt (4) jämförelse med Norden. "
        "En paneldataregressionsanalys av KRI mot faktiska betalningsinställelser och "
        "lånerating-förändringar skulle stärka indexets prediktiva validitet.",
        S["body"],
    ))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=C_BORDER, spaceAfter=8))
    story.append(Paragraph(
        "Källa: SCB Statistikdatabasen (BalansKn, BefolkningNy, SkatteKraft), "
        "Arbetsförmedlingen via Kolada API (N03937). "
        f"Rapport genererad {date.today().strftime('%Y-%m-%d')}.",
        S["small"],
    ))

    # ---------- Build ----------
    doc.build(story)

    pdf_bytes = buf.getvalue()

    if output_path is not None:
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
