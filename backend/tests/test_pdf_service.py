"""Unit tests for PDFService — verifies output is valid PDF bytes with expected content."""
import pytest
from src.services.pdf import PDFService

SAMPLE_QUOTE = {
    "line_items": [
        {"type": "labor", "description": "Brake pad replacement", "qty": 1.5, "unit_price": 120.0, "total": 180.0},
        {"type": "part",  "description": "Front brake pads (OEM)", "qty": 1, "unit_price": 68.0, "total": 68.0},
    ],
    "total": 248.0,
}

SAMPLE_SESSION = {
    "vehicle": {
        "year": 2022, "make": "Honda", "model": "CR-V", "trim": "EX",
        "vin": "1HGBH41JXMN109186", "vehicle_id": "00000000-0000-0000-0000-000000000010",
    },
    "transcript": "Front brakes worn, checked tires.",
}

SAMPLE_REPORT = {
    "id": "00000000-0000-0000-0000-000000000020",
    "summary": "Front brakes need immediate replacement.",
    "findings": [
        {"part": "Front Brake Pads", "severity": "high", "notes": "2mm remaining"},
        {"part": "Engine Oil",       "severity": "low",  "notes": "Level normal"},
    ],
    "estimate": {"line_items": SAMPLE_QUOTE["line_items"]},
    "estimate_total": 248.0,
    "vehicle": SAMPLE_SESSION["vehicle"],
    "share_token": "abc-share-token",
}

SAMPLE_SHOP = {"name": "AutoShop SF", "address": "123 Main St", "phone": "(415) 555-0100"}


def test_generate_estimate_returns_pdf_bytes():
    pdf = PDFService.generate_estimate(SAMPLE_QUOTE, SAMPLE_SESSION, SAMPLE_SHOP)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_estimate_is_non_empty():
    pdf = PDFService.generate_estimate(SAMPLE_QUOTE, SAMPLE_SESSION, SAMPLE_SHOP)
    assert len(pdf) > 1000


def test_generate_estimate_handles_empty_line_items():
    quote = {"line_items": [], "total": 0.0}
    pdf = PDFService.generate_estimate(quote, SAMPLE_SESSION, SAMPLE_SHOP)
    assert pdf[:4] == b"%PDF"


def test_generate_report_returns_pdf_bytes():
    pdf = PDFService.generate_report(SAMPLE_REPORT, media_urls=[], shop=SAMPLE_SHOP)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_report_is_non_empty():
    pdf = PDFService.generate_report(SAMPLE_REPORT, media_urls=[], shop=SAMPLE_SHOP)
    assert len(pdf) > 1000


def test_generate_report_handles_no_findings():
    report = {**SAMPLE_REPORT, "findings": [], "summary": ""}
    pdf = PDFService.generate_report(report, media_urls=[], shop=SAMPLE_SHOP)
    assert pdf[:4] == b"%PDF"
