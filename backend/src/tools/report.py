from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def build_report_pdf(data: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    vehicle = data.get("vehicle", {})
    findings = data.get("findings", {})
    estimate = data.get("estimate", {})

    # Header
    story.append(Paragraph("Vehicle Inspection Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Vehicle info
    story.append(Paragraph("Vehicle Information", styles["Heading2"]))
    v_data = [
        ["Year / Make / Model", f"{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')} {vehicle.get('trim','')}"],
        ["VIN", vehicle.get("vin", "N/A")],
        ["Mileage", f"{data.get('mileage', 'N/A'):,} mi" if data.get('mileage') else "N/A"],
        ["Tire Size", data.get("tire_size", "N/A") or "N/A"],
    ]
    story.append(Table(v_data, colWidths=[150, 350]))
    story.append(Spacer(1, 12))

    # Summary
    if findings.get("summary"):
        story.append(Paragraph("Summary", styles["Heading2"]))
        story.append(Paragraph(findings["summary"], styles["Normal"]))
        story.append(Spacer(1, 12))

    # Line items
    if estimate.get("line_items"):
        story.append(Paragraph("Estimate", styles["Heading2"]))
        headers = ["Part", "Severity", "Labor Hrs", "Labor Cost", "Parts Cost", "Total"]
        rows = [headers]
        for item in estimate["line_items"]:
            rows.append([
                item.get("part", ""),
                item.get("severity", "").capitalize(),
                str(item.get("labor_hrs", "")),
                f"${item.get('labor_cost', 0):.2f}",
                f"${item.get('parts_cost', 0):.2f}",
                f"${item.get('line_total', 0):.2f}",
            ])
        rows.append(["", "", "", "", "TOTAL", f"${estimate.get('total', 0):.2f}"])
        t = Table(rows, colWidths=[180, 70, 60, 70, 70, 60])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)

    doc.build(story)
    return buffer.getvalue()
