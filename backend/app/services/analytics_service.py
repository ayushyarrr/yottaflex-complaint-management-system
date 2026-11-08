
from statistics import mean

from sqlalchemy.orm import Session

from backend.app.models import (
    Complaint,
    Category,
    SLAClock,
    Resolution,
    Survey,
    ComplaintEvent,
)

from backend.app.services.sla_service import (
    calculate_sla_breaches,
    get_current_utc_time,
)


def get_analytics(db: Session) -> dict:
    now = get_current_utc_time()

    # 1. Total complaints
    total_complaints = db.query(Complaint).count()

    # 2. Complaint status distribution
    status_rows = db.query(Complaint.status, Complaint.complaint_id).all()

    status_distribution = {
        "NEW": 0,
        "CLASSIFIED": 0,
        "ASSIGNED": 0,
        "IN_PROGRESS": 0,
        "PENDING_CUSTOMER": 0,
        "RESOLVED": 0,
        "CLOSED": 0,
    }

    for status, _ in status_rows:
        status_distribution[status] = (
            status_distribution.get(status, 0) + 1
        )

    # 3. Priority distribution
    priority_distribution = {
        "P1": 0,
        "P2": 0,
        "P3": 0,
        "P4": 0,
    }

    priority_rows = db.query(Complaint.priority).all()

    for (priority,) in priority_rows:
        priority_distribution[priority] = (
            priority_distribution.get(priority, 0) + 1
        )

    # 4. Category distribution
    category_rows = (
        db.query(Category.category_name, Complaint.complaint_id)
        .join(Complaint, Complaint.category_id == Category.category_id)
        .all()
    )

    category_distribution = {}

    for category_name, _ in category_rows:
        category_distribution[category_name] = (
            category_distribution.get(category_name, 0) + 1
        )

    # 5. SLA breach metrics
    sla_clocks = db.query(SLAClock).all()
    total_sla_cycles = len(sla_clocks)

    response_breaches = 0
    resolution_breaches = 0

    for clock in sla_clocks:
        breach_status = calculate_sla_breaches(
            clock,
            now=now,
        )

        if breach_status["response_breached"]:
            response_breaches += 1

        if breach_status["resolution_breached"]:
            resolution_breaches += 1

    response_breach_rate = (
        round(response_breaches / total_sla_cycles * 100, 2)
        if total_sla_cycles else 0.0
    )

    resolution_breach_rate = (
        round(resolution_breaches / total_sla_cycles * 100, 2)
        if total_sla_cycles else 0.0
    )

    # 6. Average resolution time.
    # Only the final resolution of each complaint is counted.
    final_resolutions = (
        db.query(Resolution, Complaint.created_at)
        .join(
            Complaint,
            Complaint.complaint_id == Resolution.complaint_id,
        )
        .filter(
            Resolution.is_final.is_(True),
            Resolution.resolved_at.isnot(None),
        )
        .all()
    )

    resolution_times = []

    for resolution, complaint_created_at in final_resolutions:
        duration = resolution.resolved_at - complaint_created_at
        resolution_times.append(duration.total_seconds() / 3600)

    average_resolution_hours = (
        round(mean(resolution_times), 2)
        if resolution_times else 0.0
    )

    # 7. Reopened complaints
    reopened_complaints = (
        db.query(ComplaintEvent.complaint_id)
        .filter(
            ComplaintEvent.event_type == "COMPLAINT_REOPENED"
        )
        .distinct()
        .count()
    )

    # 8. Customer satisfaction
    surveys = db.query(Survey).all()

    survey_count = len(surveys)

    average_satisfaction = (
        round(mean([survey.rating for survey in surveys]), 2)
        if surveys else 0.0
    )

    satisfaction_distribution = {
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
    }

    for survey in surveys:
        rating = str(survey.rating)
        satisfaction_distribution[rating] += 1

    # 9. Open complaints
    open_statuses = {
        "NEW",
        "CLASSIFIED",
        "ASSIGNED",
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
    }

    open_complaints = sum(
        count
        for status, count in status_distribution.items()
        if status in open_statuses
    )

    return {
        "overview": {
            "total_complaints": total_complaints,
            "open_complaints": open_complaints,
            "reopened_complaints": reopened_complaints,
            "average_resolution_hours": average_resolution_hours,
        },
        "status_distribution": status_distribution,
        "priority_distribution": priority_distribution,
        "category_distribution": category_distribution,
        "sla": {
            "total_sla_cycles": total_sla_cycles,
            "response_breaches": response_breaches,
            "response_breach_rate_percent": response_breach_rate,
            "resolution_breaches": resolution_breaches,
            "resolution_breach_rate_percent": resolution_breach_rate,
            "rate_denominator": "All recorded SLA cycles",
        },
        "customer_satisfaction": {
            "survey_count": survey_count,
            "average_rating": average_satisfaction,
            "rating_distribution": satisfaction_distribution,
        },
    }
