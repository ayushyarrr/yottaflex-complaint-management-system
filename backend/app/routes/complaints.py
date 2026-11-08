
from datetime import timezone
from backend.app.schemas.survey import SurveyCreate
from backend.app.services.survey_service import submit_survey
from backend.app.schemas.message import ComplaintMessageCreate
from backend.app.services.message_service import add_complaint_message
from backend.app.schemas.reopen import ComplaintReopen
from backend.app.services.reopen_service import reopen_complaint
from backend.app.schemas.resolution import ResolutionCreate
from backend.app.services.resolution_service import resolve_complaint
from backend.app.schemas.status import StatusUpdate
from backend.app.services.status_service import transition_complaint_status
from backend.app.schemas.complaint import ComplaintCreate
from backend.app.services.complaint_service import create_complaint
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.sla_service import calculate_sla_breaches
from backend.app.models import (
    Agent,
    Assignment,
    Category,
    Complaint,
    ComplaintEvent,
    ComplaintMessage,
    Customer,
    Order,
    PriorityDecision,
    Resolution,
    SLAClock,
    Survey,
    Team,
)

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


def serialize_datetime(value):
    if value is None:
        return None

    # Database timestamps are stored as UTC without timezone information.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.isoformat().replace("+00:00", "Z")


@router.get("")
def list_complaints(
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Complaint, Customer, Category)
        .join(Customer, Complaint.customer_id == Customer.customer_id)
        .join(Category, Complaint.category_id == Category.category_id)
    )

    if status:
        query = query.filter(Complaint.status == status.upper())

    if priority:
        query = query.filter(Complaint.priority == priority.upper())

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (Complaint.complaint_id.ilike(search_term))
            | (Complaint.description.ilike(search_term))
            | (Customer.full_name.ilike(search_term))
            | (Customer.email.ilike(search_term))
        )

    total = query.count()

    results = (
        query.order_by(Complaint.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    complaints = []

    for complaint, customer, category in results:
        sla = (
            db.query(SLAClock)
            .filter(SLAClock.complaint_id == complaint.complaint_id)
            .order_by(SLAClock.created_at.desc())
            .first()
        )
        sla_status = calculate_sla_breaches(sla) if sla else None

        assignment = (
            db.query(Assignment)
            .filter(
                Assignment.complaint_id == complaint.complaint_id,
                Assignment.is_current.is_(True),
            )
            .first()
        )

        team = None
        agent = None

        if assignment:
            team = db.query(Team).filter(
                Team.team_id == assignment.team_id
            ).first()

            agent = db.query(Agent).filter(
                Agent.agent_id == assignment.agent_id
            ).first()

        complaints.append({
            "complaint_id": complaint.complaint_id,
            "customer": {
                "customer_id": customer.customer_id,
                "name": customer.full_name,
                "email": customer.email,
            },
            "category": category.category_name,
            "description": complaint.description,
            "channel": complaint.channel,
            "sentiment": complaint.sentiment,
            "severity": complaint.severity,
            "priority": complaint.priority,
            "status": complaint.status,
            "recurrence_count": complaint.recurrence_count,
            "created_at": serialize_datetime(complaint.created_at),
            "assignment": {
                "team": team.team_name if team else None,
                "agent": agent.agent_name if agent else None,
            } if assignment else None,
            "sla": {
                "response_deadline": serialize_datetime(
                    sla.response_deadline
                ),
                "resolution_deadline": serialize_datetime(
                    sla.resolution_deadline
                ),
                "response_breached": sla_status["response_breached"],
                "resolution_breached": sla_status["resolution_breached"],
                "paused": sla_status["paused"],
            } if sla else None,
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "complaints": complaints,
    }


@router.post("", status_code=201)
def create_new_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
):
    complaint = create_complaint(
        db=db,
        payload=payload,
    )

    return {
        "message": "Complaint created successfully.",
        "complaint_id": complaint.complaint_id,
        "customer_id": complaint.customer_id,
        "order_id": complaint.order_id,
        "category_id": complaint.category_id,
        "priority": complaint.priority,
        "severity": complaint.severity,
        "status": complaint.status,
        "recurrence_count": complaint.recurrence_count,
        "created_at": serialize_datetime(complaint.created_at),
    }

@router.patch("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: str,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
):
    old_status = (
        db.query(Complaint.status)
        .filter(Complaint.complaint_id == complaint_id)
        .scalar()
    )

    complaint = transition_complaint_status(
        db=db,
        complaint_id=complaint_id,
        new_status=payload.new_status,
        performed_by=payload.performed_by,
    )

    return {
        "message": "Complaint status updated successfully.",
        "complaint_id": complaint.complaint_id,
        "old_status": old_status,
        "new_status": complaint.status,
        "updated_at": serialize_datetime(complaint.updated_at),
    }

@router.post("/{complaint_id}/resolve", status_code=201)
def resolve_complaint_endpoint(
    complaint_id: str,
    payload: ResolutionCreate,
    db: Session = Depends(get_db),
):
    resolution = resolve_complaint(
        db=db,
        complaint_id=complaint_id,
        payload=payload,
    )

    return {
        "message": "Complaint resolved successfully.",
        "complaint_id": resolution.complaint_id,
        "resolution_id": resolution.resolution_id,
        "resolution_type": resolution.resolution_type,
        "resolution_description": resolution.resolution_description,
        "resolved_by": resolution.resolved_by,
        "resolved_at": serialize_datetime(resolution.resolved_at),
        "is_final": resolution.is_final,
        "status": "RESOLVED",
    }

@router.post("/{complaint_id}/reopen")
def reopen_complaint_endpoint(
    complaint_id: str,
    payload: ComplaintReopen,
    db: Session = Depends(get_db),
):
    complaint = reopen_complaint(
        db=db,
        complaint_id=complaint_id,
        payload=payload,
    )

    return {
        "message": "Complaint reopened successfully.",
        "complaint_id": complaint.complaint_id,
        "status": complaint.status,
        "updated_at": serialize_datetime(complaint.updated_at),
    }

@router.post("/{complaint_id}/messages", status_code=201)
def add_complaint_message_endpoint(
    complaint_id: str,
    payload: ComplaintMessageCreate,
    db: Session = Depends(get_db),
):
    message = add_complaint_message(
        db=db,
        complaint_id=complaint_id,
        payload=payload,
    )

    return {
        "message": "Complaint message added successfully.",
        "message_id": message.message_id,
        "complaint_id": message.complaint_id,
        "sender_type": message.sender_type,
        "message_text": message.message_text,
        "channel": message.channel,
        "is_internal": message.is_internal,
        "created_at": serialize_datetime(message.created_at),
    }



@router.post("/{complaint_id}/survey", status_code=201)
def submit_complaint_survey_endpoint(
    complaint_id: str,
    payload: SurveyCreate,
    db: Session = Depends(get_db),
):
    survey = submit_survey(
        db=db,
        complaint_id=complaint_id,
        payload=payload,
    )

    return {
        "message": "Customer survey submitted successfully.",
        "survey_id": survey.survey_id,
        "complaint_id": survey.complaint_id,
        "resolution_id": survey.resolution_id,
        "rating": survey.rating,
        "feedback": survey.feedback,
        "submitted_at": serialize_datetime(survey.submitted_at),
    }


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: str,
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.complaint_id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    customer = db.query(Customer).filter(
        Customer.customer_id == complaint.customer_id
    ).first()

    category = db.query(Category).filter(
        Category.category_id == complaint.category_id
    ).first()

    order = None
    if complaint.order_id:
        order = db.query(Order).filter(
            Order.order_id == complaint.order_id
        ).first()

    messages = (
        db.query(ComplaintMessage)
        .filter(ComplaintMessage.complaint_id == complaint_id)
        .order_by(ComplaintMessage.created_at.asc())
        .all()
    )

    events = (
        db.query(ComplaintEvent)
        .filter(ComplaintEvent.complaint_id == complaint_id)
        .order_by(ComplaintEvent.created_at.asc())
        .all()
    )

    assignments = (
        db.query(Assignment)
        .filter(Assignment.complaint_id == complaint_id)
        .order_by(Assignment.assigned_at.asc())
        .all()
    )

    assignment_history = []

    for assignment in assignments:
        team = db.query(Team).filter(
            Team.team_id == assignment.team_id
        ).first()

        agent = db.query(Agent).filter(
            Agent.agent_id == assignment.agent_id
        ).first()

        assignment_history.append({
            "assignment_id": assignment.assignment_id,
            "agent_id": agent.agent_id if agent else None,
            "team": team.team_name if team else None,
            "agent": agent.agent_name if agent else None,
            "assigned_by": assignment.assigned_by,
            "reason": assignment.reason,
            "is_current": assignment.is_current,
            "assigned_at": serialize_datetime(assignment.assigned_at),
        })

    sla_clocks = (
        db.query(SLAClock)
        .filter(SLAClock.complaint_id == complaint_id)
        .order_by(SLAClock.created_at.asc())
        .all()
    )
    sla_status_by_id = {
        sla.sla_id: calculate_sla_breaches(sla)
        for sla in sla_clocks
    }

    resolutions = (
        db.query(Resolution)
        .filter(Resolution.complaint_id == complaint_id)
        .order_by(Resolution.resolved_at.asc())
        .all()
    )

    resolution_history = []

    for resolution in resolutions:
        survey = db.query(Survey).filter(
            Survey.resolution_id == resolution.resolution_id
        ).first()

        resolution_history.append({
            "resolution_id": resolution.resolution_id,
            "resolution_type": resolution.resolution_type,
            "description": resolution.resolution_description,
            "resolved_by": resolution.resolved_by,
            "resolved_at": serialize_datetime(resolution.resolved_at),
            "is_final": resolution.is_final,
            "survey": {
                "rating": survey.rating,
                "feedback": survey.feedback,
                "submitted_at": serialize_datetime(survey.submitted_at),
            } if survey else None,
        })

    priority_decisions = (
        db.query(PriorityDecision)
        .filter(PriorityDecision.complaint_id == complaint_id)
        .order_by(PriorityDecision.decided_at.asc())
        .all()
    )

    return {
        "complaint_id": complaint.complaint_id,
        "customer": {
            "customer_id": customer.customer_id,
            "name": customer.full_name,
            "email": customer.email,
            "phone": customer.phone,
            "region": customer.region,
            "is_vulnerable": customer.is_vulnerable,
        } if customer else None,
        "order": {
            "order_id": order.order_id,
            "total_amount": float(order.total_amount),
            "payment_status": order.payment_status,
            "order_status": order.order_status,
        } if order else None,
        "category": category.category_name if category else None,
        "description": complaint.description,
        "channel": complaint.channel,
        "sentiment": complaint.sentiment,
        "severity": complaint.severity,
        "priority": complaint.priority,
        "status": complaint.status,
        "recurrence_count": complaint.recurrence_count,
        "created_at": serialize_datetime(complaint.created_at),
        "updated_at": serialize_datetime(complaint.updated_at),
        "messages": [
            {
                "message_id": message.message_id,
                "sender_type": message.sender_type,
                "message_text": message.message_text,
                "channel": message.channel,
                "is_internal": message.is_internal,
                "created_at": serialize_datetime(message.created_at),
            }
            for message in messages
        ],
        "assignment_history": assignment_history,
        "sla_clocks": [
            {
                "sla_id": sla.sla_id,
                "priority": sla.priority,
                "response_deadline": serialize_datetime(
                    sla.response_deadline
                ),
                "resolution_deadline": serialize_datetime(
                    sla.resolution_deadline
                ),
                "first_response_at": serialize_datetime(
                    sla.first_response_at
                ),
                "resolved_at": serialize_datetime(sla.resolved_at),
                "paused_at": serialize_datetime(sla.paused_at),
                "total_paused_seconds": sla.total_paused_seconds,
                "response_breached": (
                    sla_status_by_id[sla.sla_id]["response_breached"]
                ),
                "resolution_breached": (
                    sla_status_by_id[sla.sla_id]["resolution_breached"]
                ),
            }
            for sla in sla_clocks
        ],
        "resolutions": resolution_history,
        "priority_decisions": [
            {
                "decision_id": decision.decision_id,
                "calculated_score": decision.calculated_score,
                "assigned_priority": decision.assigned_priority,
                "safety_override_applied": (
                    decision.safety_override_applied
                ),
                "explanation": decision.explanation,
                "decided_at": serialize_datetime(decision.decided_at),
            }
            for decision in priority_decisions
        ],
        "events": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "description": event.description,
                "performed_by": event.performed_by,
                "created_at": serialize_datetime(event.created_at),
            }
            for event in events
        ],
    }
