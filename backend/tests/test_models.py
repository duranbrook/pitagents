"""
Tests for SQLAlchemy model definitions.
We test column existence and types without a real DB — just inspect the mapper.
"""
import pytest
from sqlalchemy import inspect as sa_inspect
from src.models.shop import Shop
from src.models.user import User
from src.models.session import InspectionSession
from src.models.report import Report
from src.models.media import MediaFile


def _col_names(model) -> set[str]:
    return {c.key for c in sa_inspect(model).mapper.column_attrs}


def test_shop_columns():
    cols = _col_names(Shop)
    assert {"id", "name", "address", "labor_rate", "pricing_flag", "alldata_api_key"}.issubset(cols)


def test_user_columns():
    cols = _col_names(User)
    assert {"id", "shop_id", "email", "hashed_password", "role", "name"}.issubset(cols)


def test_inspection_session_columns():
    cols = _col_names(InspectionSession)
    assert {"id", "shop_id", "technician_id", "status", "vehicle", "transcript",
            "created_at", "completed_at"}.issubset(cols)


def test_report_columns():
    cols = _col_names(Report)
    assert {"id", "session_id", "summary", "findings", "estimate_total",
            "share_token", "share_expires_at", "sent_to", "pdf_url", "created_at"}.issubset(cols)


def test_media_file_columns():
    cols = _col_names(MediaFile)
    assert {"id", "session_id", "media_type", "tag", "s3_url", "filename"}.issubset(cols)


def test_shop_tablename():
    assert Shop.__tablename__ == "shops"


def test_user_tablename():
    assert User.__tablename__ == "users"


def test_session_tablename():
    assert InspectionSession.__tablename__ == "inspection_sessions"


def test_report_tablename():
    assert Report.__tablename__ == "reports"


def test_media_tablename():
    assert MediaFile.__tablename__ == "media_files"
