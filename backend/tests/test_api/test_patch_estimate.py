"""Tests for PATCH /reports/{id}/estimate — pure derivation logic first, DB tests in Task 2."""


def _derive(labor_hours: float, labor_rate: float, parts_cost: float):
    """Mirror the derivation logic from the endpoint."""
    labor_cost = round(labor_hours * labor_rate, 2)
    total = round(labor_cost + parts_cost, 2)
    return labor_cost, total


def test_derive_fields():
    labor_cost, total = _derive(2.0, 125.0, 85.0)
    assert labor_cost == 250.0
    assert total == 335.0


def test_derive_zero_hours():
    labor_cost, total = _derive(0.0, 125.0, 40.0)
    assert labor_cost == 0.0
    assert total == 40.0


def test_derive_fractional_hours():
    labor_cost, total = _derive(1.5, 90.0, 22.50)
    assert labor_cost == 135.0
    assert total == 157.5


def test_derive_zero_parts():
    labor_cost, total = _derive(2.0, 100.0, 0.0)
    assert labor_cost == 200.0
    assert total == 200.0
