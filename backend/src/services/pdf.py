"""PDF generation service using reportlab."""
from __future__ import annotations

import logging
import urllib.request
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


def _fetch_image(url: str, max_width: float, max_height: float) -> Image | None:
    """Download a photo from S3 and return a scaled ReportLab Image, or None on failure."""
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310
            data = resp.read()
        img = Image(BytesIO(data))
        scale = min(max_width / img.imageWidth, max_height / img.imageHeight, 1.0)
        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        return img
    except Exception:
        logger.warning("pdf: could not fetch photo %s", url)
        return None

_W, _H = letter  # 8.5 × 11 inches
_DARK = colors.HexColor("#1a1a2e")
_AMBER = colors.HexColor("#ffc107")
_RED = colors.HexColor("#dc3545")
_ORANGE = colors.HexColor("#fd7e14")
_GREEN = colors.HexColor("#28a745")


class PDFService:

    @staticmethod
    def generate_estimate(quote: dict, session: dict, shop: dict) -> bytes:
        """Return PDF bytes for the customer-signed Estimate document."""
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=letter,
            leftMargin=0.6*inch, rightMargin=0.6*inch,
            topMargin=0.4*inch, bottomMargin=0.5*inch,
        )
        styles = getSampleStyleSheet()
        bold = ParagraphStyle("bold", parent=styles["Normal"], fontName="Helvetica-Bold")
        vehicle = session.get("vehicle", {})
        line_items = quote.get("line_items", [])

        story = []

        # ── Header band ──
        header_data = [[
            Paragraph(f"<b>{shop.get('name', 'AutoShop')}</b><br/>"
                      f"<font size=8>{shop.get('address','')}<br/>"
                      f"{shop.get('phone','')}</font>", styles["Normal"]),
            Paragraph("<b>ESTIMATE</b>", bold),
        ]]
        header_table = Table(header_data, colWidths=[4*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), _DARK),
            ("TEXTCOLOR",  (0,0), (-1,-1), colors.white),
            ("ALIGN",      (1,0), (1,0),   "RIGHT"),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.15*inch))

        # ── Vehicle / info row ──
        veh_str = (f"{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')} "
                   f"{vehicle.get('trim','')}").strip()
        vin_str = f"VIN: {vehicle.get('vin','N/A')}"
        info_data = [[
            Paragraph(f"<b>Vehicle</b><br/>{veh_str}<br/><font size=8>{vin_str}</font>", styles["Normal"]),
            Paragraph(f"<b>Labor Rate</b><br/>$120/hr", styles["Normal"]),
        ]]
        info_table = Table(info_data, colWidths=[4*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ("BOX",         (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("INNERGRID",   (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("TOPPADDING",  (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.15*inch))

        # ── Line items ──
        story.append(Paragraph("Recommended Services", bold))
        story.append(Spacer(1, 0.05*inch))
        col_hdr = [Paragraph(h, bold) for h in ["Description", "Type", "Qty", "Unit Price", "Total"]]
        rows = [col_hdr]
        labor_sub = parts_sub = 0.0
        for item in line_items:
            t = item.get("type", "labor")
            qty = float(item.get("qty", 1))
            unit = float(item.get("unit_price", 0))
            itotal = float(item.get("total", 0))
            if t == "labor": labor_sub += itotal
            else:            parts_sub += itotal
            qty_str = f"{qty:.0f} hr" if t == "labor" else f"{qty:.0f}"
            rows.append([
                Paragraph(item.get("description",""), styles["Normal"]),
                Paragraph(t.capitalize(), styles["Normal"]),
                qty_str,
                f"${unit:,.2f}",
                Paragraph(f"<b>${itotal:,.2f}</b>", bold),
            ])
        items_table = Table(rows, colWidths=[2.8*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  colors.HexColor("#f5f5f5")),
            ("LINEBELOW",   (0,0), (-1,0),  1.5, colors.grey),
            ("LINEBELOW",   (0,1), (-1,-1), 0.5, colors.HexColor("#f0f0f0")),
            ("ALIGN",       (2,0), (-1,-1), "RIGHT"),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0), (0,-1),  6),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.1*inch))

        # ── Totals ──
        tax_rate = 0.08625
        tax = (labor_sub + parts_sub) * tax_rate
        grand = labor_sub + parts_sub + tax
        totals_data = [
            ["", "Labor subtotal",  f"${labor_sub:,.2f}"],
            ["", "Parts subtotal",  f"${parts_sub:,.2f}"],
            ["", f"Tax ({tax_rate*100:.3f}%)", f"${tax:,.2f}"],
            ["", Paragraph("<b>TOTAL</b>", bold), Paragraph(f"<b>${grand:,.2f}</b>", bold)],
        ]
        totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch, 1.4*inch])
        totals_table.setStyle(TableStyle([
            ("LINEABOVE",    (1,3), (-1,3), 1.5, colors.black),
            ("ALIGN",        (2,0), (2,-1), "RIGHT"),
            ("TOPPADDING",   (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 0.2*inch))

        # ── Authorization ──
        auth_data = [[
            Paragraph(
                "<b>Customer Authorization</b><br/>"
                "<font size=8>I authorize the above repairs and agree to the stated pricing.</font>",
                styles["Normal"]
            ),
        ]]
        auth_table = Table(auth_data, colWidths=[7*inch])
        auth_table.setStyle(TableStyle([
            ("BOX",         (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#fffef5")),
            ("TOPPADDING",  (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 30),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(auth_table)

        doc.build(story)
        return buf.getvalue()

    @staticmethod
    def generate_report(report: dict, media_urls: list[str], shop: dict) -> bytes:
        """Return PDF bytes for the Inspection Report document."""
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=letter,
            leftMargin=0.6*inch, rightMargin=0.6*inch,
            topMargin=0.4*inch, bottomMargin=0.5*inch,
        )
        styles = getSampleStyleSheet()
        bold = ParagraphStyle("bold2", parent=styles["Normal"], fontName="Helvetica-Bold")
        small_grey = ParagraphStyle("smgrey", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
        vehicle = report.get("vehicle", {})
        findings = report.get("findings", [])
        estimate_data = report.get("estimate", {})
        line_items = estimate_data.get("line_items", [])
        summary = report.get("summary", "")
        share_token = report.get("share_token", "")

        _sev_color = {"high": _RED, "medium": _ORANGE, "moderate": _ORANGE, "low": _GREEN}
        _sev_label = {"high": "Service Now", "medium": "Monitor", "moderate": "Monitor", "low": "Good"}

        story = []

        # ── Header ──
        veh_str = (f"{vehicle.get('year','')} {vehicle.get('make','')} "
                   f"{vehicle.get('model','')} {vehicle.get('trim','')}").strip()
        header_data = [[
            Paragraph(f"<b>{shop.get('name','AutoShop')}</b><br/>"
                      f"<font size=8>{shop.get('address','')}</font>", styles["Normal"]),
            Paragraph("<b>INSPECTION REPORT</b>", bold),
        ]]
        ht = Table(header_data, colWidths=[4*inch, 3*inch])
        ht.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), _DARK),
            ("TEXTCOLOR",  (0,0), (-1,-1), colors.white),
            ("ALIGN",      (1,0), (1,0),   "RIGHT"),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING",(0,0), (-1,-1), 12),
        ]))
        story.append(ht)
        story.append(Spacer(1, 0.1*inch))

        # ── Vehicle banner ──
        vin = vehicle.get("vin", "")
        story.append(Paragraph(
            f"<b>{veh_str}</b> &nbsp;·&nbsp; VIN: {vin}",
            ParagraphStyle("banner", parent=styles["Normal"],
                           backColor=colors.HexColor("#f5f5f5"), borderPadding=6,
                           leftIndent=0, rightIndent=0, fontSize=10)
        ))
        story.append(Spacer(1, 0.1*inch))

        # ── Summary callout ──
        if summary:
            story.append(Table(
                [[Paragraph(f"<b>Summary:</b> {summary}", styles["Normal"])]],
                colWidths=[7*inch],
                style=[
                    ("LEFTPADDING",  (0,0), (-1,-1), 10),
                    ("RIGHTPADDING", (0,0), (-1,-1), 10),
                    ("TOPPADDING",   (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING",(0,0), (-1,-1), 6),
                    ("LINEBEFORE",   (0,0), (0,-1),  3, _AMBER),
                    ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#fff3cd")),
                ]
            ))
            story.append(Spacer(1, 0.15*inch))

        # ── Findings (one card per finding, with photo if available) ──
        if findings:
            story.append(Paragraph("Inspection Findings", bold))
            story.append(Spacer(1, 0.05*inch))
            for idx, f in enumerate(findings):
                sev = (f.get("severity") or "low").lower()
                badge_color = _sev_color.get(sev, _GREEN)
                label = _sev_label.get(sev, "Good")
                badge = Table(
                    [[Paragraph(f"<font color='white'><b>{label}</b></font>",
                                ParagraphStyle("badge", parent=styles["Normal"], fontSize=8))]],
                    style=[
                        ("BACKGROUND",     (0,0), (-1,-1), badge_color),
                        ("TOPPADDING",     (0,0), (-1,-1), 2),
                        ("BOTTOMPADDING",  (0,0), (-1,-1), 2),
                        ("LEFTPADDING",    (0,0), (-1,-1), 6),
                        ("RIGHTPADDING",   (0,0), (-1,-1), 6),
                    ],
                )
                header_row = Table(
                    [[Paragraph(f"<b>{f.get('part', '')}</b>", styles["Normal"]), badge]],
                    colWidths=[5.6*inch, 1.3*inch],
                    style=[
                        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                        ("TOPPADDING",    (0,0), (-1,-1), 4),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                    ],
                )
                story.append(header_row)
                story.append(Paragraph(f.get("notes", ""), styles["Normal"]))

                photo_url = f.get("photo_url")
                if photo_url and photo_url.startswith("http"):
                    img = _fetch_image(photo_url, max_width=6.8 * inch, max_height=3 * inch)
                    if img:
                        story.append(Spacer(1, 0.06 * inch))
                        story.append(img)

                if idx < len(findings) - 1:
                    story.append(Spacer(1, 0.06 * inch))
                    story.append(HRFlowable(width="100%", thickness=0.5,
                                            color=colors.HexColor("#e0e0e0")))
                    story.append(Spacer(1, 0.06 * inch))

            story.append(Spacer(1, 0.15*inch))

        # ── Estimate summary ──
        if line_items:
            story.append(Paragraph("Repair Estimate", bold))
            story.append(Spacer(1, 0.05*inch))
            est_rows = [[Paragraph("<b>Service</b>", bold), Paragraph("<b>Total</b>", bold)]]
            grand = 0.0
            for item in line_items:
                itotal = float(item.get("total", 0))
                grand += itotal
                est_rows.append([
                    Paragraph(item.get("description",""), styles["Normal"]),
                    f"${itotal:,.2f}",
                ])
            est_rows.append([Paragraph("<b>Grand Total</b>", bold), Paragraph(f"<b>${grand:,.2f}</b>", bold)])
            et = Table(est_rows, colWidths=[5.5*inch, 1.4*inch])
            et.setStyle(TableStyle([
                ("LINEBELOW",   (0,-2), (-1,-2), 1.5, colors.black),
                ("LINEBELOW",   (0,0),  (-1,-3), 0.5, colors.HexColor("#f0f0f0")),
                ("ALIGN",       (1,0),  (1,-1),  "RIGHT"),
                ("TOPPADDING",  (0,0),  (-1,-1), 4),
                ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ]))
            story.append(et)
            story.append(Spacer(1, 0.15*inch))

        # ── Footer ──
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 0.05*inch))
        if share_token:
            story.append(Paragraph(
                f"View online: {shop.get('name','AutoShop')}.app/r/{share_token}",
                small_grey
            ))

        doc.build(story)
        return buf.getvalue()
