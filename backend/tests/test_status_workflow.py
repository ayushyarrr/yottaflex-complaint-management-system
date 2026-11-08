
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.models import Complaint, ComplaintEvent, SLAClock
from backend.app.services import status_service


FIXED_NOW = datetime(2026, 11, 8, 12, 0, 0)


class FakeQuery:
    """A lightweight query mock for testing the status service."""

    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDatabase:
    """An isolated fake database; it never touches the real SQLite file."""

    def __init__(self, complaint=None, sla_clock=None):
        self.complaint = complaint
        self.sla_clock = sla_clock
        self.added_objects = []
        self.commit_count = 0
        self.rollback_count = 0
        self.refreshed_objects = []

    def query(self, model):
        if model is Complaint:
            return FakeQuery(self.complaint)

        if model is SLAClock:
            return FakeQuery(self.sla_clock)

        raise AssertionError(f"Unexpected model queried: {model}")

    def add(self, obj):
        self.added_objects.append(obj)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def refresh(self, obj):
        self.refreshed_objects.append(obj)


def make_complaint(status="ASSIGNED"):
    return SimpleNamespace(
        complaint_id="CMP-TEST-000001",
        status=status,
        updated_at=None,
    )


def make_sla_clock():
    return SimpleNamespace(
        complaint_id="CMP-TEST-000001",
        paused_at=None,
        total_paused_seconds=0,
        resolution_deadline=FIXED_NOW + timedelta(hours=4),
    )


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(
        status_service,
        "get_current_time",
        lambda: FIXED_NOW,
    )


def test_assigned_complaint_can_start_work():
    complaint = make_complaint("ASSIGNED")
    db = FakeDatabase(complaint=complaint)

    result = status_service.transition_complaint_status(
        db=db,
        complaint_id=complaint.complaint_id,
        new_status="IN_PROGRESS",
        performed_by="Test Agent",
    )

    assert result.status == "IN_PROGRESS"
    assert result.updated_at == FIXED_NOW
    assert db.commit_count == 1
    assert db.rollback_count == 0
    assert len(db.added_objects) == 1

    event = db.added_objects[0]
    assert isinstance(event, ComplaintEvent)
    assert event.event_type == "STATUS_CHANGED"
    assert event.old_value == "ASSIGNED"
    assert event.new_value == "IN_PROGRESS"
    assert event.performed_by == "Test Agent"


def test_awaiting_customer_pauses_resolution_sla():
    complaint = make_complaint("IN_PROGRESS")
    sla_clock = make_sla_clock()
    db = FakeDatabase(complaint, sla_clock)

    result = status_service.transition_complaint_status(
        db=db,
        complaint_id=complaint.complaint_id,
        new_status="PENDING_CUSTOMER",
        performed_by="Test Agent",
    )

    assert result.status == "PENDING_CUSTOMER"
    assert sla_clock.paused_at == FIXED_NOW
    assert sla_clock.total_paused_seconds == 0
    assert db.commit_count == 1

    event = db.added_objects[0]
    assert event.old_value == "IN_PROGRESS"
    assert event.new_value == "PENDING_CUSTOMER"


def test_customer_response_resumes_sla_and_extends_deadline():
    complaint = make_complaint("PENDING_CUSTOMER")
    sla_clock = make_sla_clock()

    paused_duration = 120
    sla_clock.paused_at = FIXED_NOW - timedelta(
        seconds=paused_duration
    )

    original_deadline = sla_clock.resolution_deadline
    db = FakeDatabase(complaint, sla_clock)

    result = status_service.transition_complaint_status(
        db=db,
        complaint_id=complaint.complaint_id,
        new_status="IN_PROGRESS",
        performed_by="Test Agent",
    )

    assert result.status == "IN_PROGRESS"
    assert sla_clock.paused_at is None
    assert sla_clock.total_paused_seconds == paused_duration
    assert sla_clock.resolution_deadline == (
        original_deadline + timedelta(seconds=paused_duration)
    )
    assert db.commit_count == 1

    event = db.added_objects[0]
    assert event.old_value == "PENDING_CUSTOMER"
    assert event.new_value == "IN_PROGRESS"


def test_invalid_status_transition_is_rejected():
    complaint = make_complaint("ASSIGNED")
    db = FakeDatabase(complaint=complaint)

    with pytest.raises(HTTPException) as error:
        status_service.transition_complaint_status(
            db=db,
            complaint_id=complaint.complaint_id,
            new_status="CLOSED",
            performed_by="Test Agent",
        )

    assert error.value.status_code == 409
    assert complaint.status == "ASSIGNED"
    assert db.commit_count == 0
    assert db.rollback_count == 1
    assert db.added_objects == []


def test_missing_complaint_returns_404():
    db = FakeDatabase()

    with pytest.raises(HTTPException) as error:
        status_service.transition_complaint_status(
            db=db,
            complaint_id="CMP-DOES-NOT-EXIST",
            new_status="IN_PROGRESS",
            performed_by="Test Agent",
        )

    assert error.value.status_code == 404
    assert db.commit_count == 0
    assert db.rollback_count == 1


def test_blank_performer_is_rejected():
    complaint = make_complaint()
    db = FakeDatabase(complaint=complaint)

    with pytest.raises(HTTPException) as error:
        status_service.transition_complaint_status(
            db=db,
            complaint_id=complaint.complaint_id,
            new_status="IN_PROGRESS",
            performed_by="   ",
        )

    assert error.value.status_code == 422
    assert db.commit_count == 0
    assert db.rollback_count == 0


def test_unsupported_status_is_rejected():
    complaint = make_complaint()
    db = FakeDatabase(complaint=complaint)

    with pytest.raises(HTTPException) as error:
        status_service.transition_complaint_status(
            db=db,
            complaint_id=complaint.complaint_id,
            new_status="CANCELLED",
            performed_by="Test Agent",
        )

    assert error.value.status_code == 422
    assert db.commit_count == 0
    assert db.rollback_count == 0


def test_pausing_without_sla_clock_is_rejected():
    complaint = make_complaint("IN_PROGRESS")
    db = FakeDatabase(complaint=complaint)

    with pytest.raises(HTTPException) as error:
        status_service.transition_complaint_status(
            db=db,
            complaint_id=complaint.complaint_id,
            new_status="PENDING_CUSTOMER",
            performed_by="Test Agent",
        )

    assert error.value.status_code == 409
    assert complaint.status == "IN_PROGRESS"
    assert db.commit_count == 0
    assert db.rollback_count == 1


def test_resuming_without_paused_clock_is_rejected():
    complaint = make_complaint("PENDING_CUSTOMER")
    sla_clock = make_sla_clock()
    db = FakeDatabase(complaint, sla_clock)

    with pytest.raises(HTTPException) as error:
        status_service.transition_complaint_status(
            db=db,
            complaint_id=complaint.complaint_id,
            new_status="IN_PROGRESS",
            performed_by="Test Agent",
        )

    assert error.value.status_code == 409
    assert sla_clock.paused_at is None
    assert db.commit_count == 0
    assert db.rollback_count == 1
