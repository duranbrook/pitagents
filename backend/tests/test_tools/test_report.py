from src.tools.report import build_report_pdf

REPORT_DATA = {
    "vehicle": {"year": "2019", "make": "Honda", "model": "Civic", "trim": "LX", "vin": "1HGBH41JXMN109186"},
    "mileage": 67420,
    "tire_size": "215/55R16",
    "findings": {"summary": "Brakes worn.", "findings": [{"part": "Brake pads", "severity": "urgent", "notes": "worn"}]},
    "estimate": {"line_items": [{"part": "Brake pads", "labor_hrs": 2.0, "labor_cost": 240.0, "parts_cost": 89.0, "line_total": 329.0}], "total": 329.0},
    "media_urls": [],
}

def test_build_report_returns_bytes():
    pdf_bytes = build_report_pdf(REPORT_DATA)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000  # valid PDF has content
    assert pdf_bytes[:4] == b"%PDF"  # PDF magic bytes
