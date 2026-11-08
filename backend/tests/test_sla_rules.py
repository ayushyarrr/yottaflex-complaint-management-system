
from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.app.services.sla_service import calculate_sla_breaches


def make_sla_clock(**overrides):
    now = datetime(2026, 11, 8, 12, 0, 0)

    values = {
        "response_deadline": now + timedelta(minutes=15),
        "resolution_deadline": now + timedelta(hours=4),
        "first_response_at": None,
        "resolved_at": None,
        "paused_at": None,
        "response_breached": False,
        "resolution_breached": False,
    }

    values.update(overrides)
    return SimpleNamespace(**values)


def test_response_and_resolution_within_deadline():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        first_response_at=now - timedelta(minutes=5),
        resolved_at=now - timedelta(hours=1),
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["response_breached"] is False
    assert result["resolution_breached"] is False
    assert result["paused"] is False


def test_response_breach_when_first_response_is_late():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        response_deadline=now - timedelta(minutes=10),
        first_response_at=now - timedelta(minutes=5),
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["response_breached"] is True


def test_unresolved_complaint_breaches_resolution_deadline():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        resolution_deadline=now - timedelta(minutes=10),
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["resolution_breached"] is True


def test_paused_clock_does_not_accumulate_live_resolution_breach():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        resolution_deadline=now - timedelta(minutes=10),
        paused_at=now - timedelta(minutes=30),
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["resolution_breached"] is False
    assert result["paused"] is True


def test_previous_resolution_breach_is_preserved_while_paused():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        resolution_deadline=now - timedelta(hours=1),
        paused_at=now - timedelta(minutes=30),
        resolution_breached=True,
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["resolution_breached"] is True
    assert result["paused"] is True


def test_resolved_complaint_uses_resolution_timestamp():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        response_deadline=now - timedelta(minutes=30),
        resolution_deadline=now + timedelta(hours=2),
        resolved_at=now - timedelta(minutes=40),
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["response_breached"] is False
    assert result["resolution_breached"] is False


def test_resolved_complaint_can_have_resolution_breach():
    now = datetime(2026, 11, 8, 12, 0, 0)

    clock = make_sla_clock(
        resolution_deadline=now - timedelta(hours=1),
        resolved_at=now - timedelta(minutes=30),
    )

    result = calculate_sla_breaches(clock, now=now)

    assert result["resolution_breached"] is True
