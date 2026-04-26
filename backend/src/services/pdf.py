"""PDF generation service using reportlab."""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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
        raise NotImplementedError
