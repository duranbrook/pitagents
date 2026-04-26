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
        raise NotImplementedError

    @staticmethod
    def generate_report(report: dict, media_urls: list[str], shop: dict) -> bytes:
        """Return PDF bytes for the Inspection Report document."""
        raise NotImplementedError
