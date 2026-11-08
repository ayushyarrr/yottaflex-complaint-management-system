
from datetime import timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models import (
    Agent,
    Assignment,
    Category,
    Complaint,
    ComplaintMessage,
    SLAClock,
    Team,
)
from backend.generator.lifecycle_config import get_status_distribution


CATEGORY_TEAM_MAP = {
    "DELIVERY": "Delivery Support",
    "MISSING ITEM": "Delivery Support",
    "CANCELLATION": "Delivery Support",
    "REFUND": "Finance Support",
    "PAYMENT": "Finance Support",
    "DAMAGED PRODUCT": "Product Support",
    "WARRANTY": "Product Support",
    "PRODUCT SAFETY": "Safety Response",
    "ACCOUNT": "General Support",
    "OTHER": "General Support",
}

SLA_TARGETS = {
    "P1": {"response_minutes": 15, "resolution_hours": 4},
    "P2": {"response_minutes": 60, "resolution_hours": 12},
    "P3": {"response_minutes": 240, "resolution_hours": 48},
    "P4": {"response_minutes": 480, "resolution_hours": 72},
}


def normalize_datetime(value):
    """Normalize datetimes for consistent UTC comparisons."""

    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def get_first_agent_response(db, complaint_id):
    """Find the earliest customer-visible agent message."""

    return (
        db.query(ComplaintMessage)
        .filter(
            ComplaintMessage.complaint_id == complaint_id,
            ComplaintMessage.sender_type == "AGENT",
            ComplaintMessage.is_internal.is_(False),
        )
        .order_by(
            ComplaintMessage.created_at.asc(),
            ComplaintMessage.message_id.asc(),
        )
        .first()
    )


def make_new_complaint_agent_messages_internal(db, complaint_id):
    """
    NEW complaints must not have customer-visible agent responses.

    Retain the generated agent message as an internal note instead.
    """

    messages = (
        db.query(ComplaintMessage)
        .filter(
            ComplaintMessage.complaint_id == complaint_id,
            ComplaintMessage.sender_type == "AGENT",
            ComplaintMessage.is_internal.is_(False),
        )
        .all()
    )

    for message in messages:
        message.is_internal = True


def generate_workflow():
    db = SessionLocal()

    try:
        complaints = (
            db.query(Complaint)
            .order_by(Complaint.complaint_id)
            .all()
        )

        if not complaints:
            raise ValueError(
                "No complaints found. Generate complaints first."
            )

        # Obtain the same deterministic lifecycle plan used by
        # the lifecycle generator.
        planned_statuses = get_status_distribution(len(complaints))

        if len(planned_statuses) != len(complaints):
            raise ValueError(
                "Lifecycle distribution does not match complaint count."
            )

        existing_assignments = db.query(Assignment).count()
        existing_sla_clocks = db.query(SLAClock).count()

        if existing_assignments > 0 or existing_sla_clocks > 0:
            print("Workflow records already exist.")
            print("No records were added to avoid duplicates.")
            print(f"Existing assignments: {existing_assignments}")
            print(f"Existing SLA clocks: {existing_sla_clocks}")
            return

        categories = {
            category.category_id: category.category_name.upper()
            for category in db.query(Category).all()
        }

        teams = {
            team.team_name: team
            for team in db.query(Team)
            .filter(Team.is_active.is_(True))
            .all()
        }

        agents = (
            db.query(Agent)
            .filter(Agent.is_active.is_(True))
            .order_by(Agent.agent_id)
            .all()
        )

        if len(teams) != 5:
            raise ValueError(
                f"Expected 5 active teams, found {len(teams)}."
            )

        if not agents:
            raise ValueError("No active agents found.")

        agents_by_team = {}

        for agent in agents:
            agents_by_team.setdefault(agent.team_id, []).append(agent)

        workload = {agent.agent_id: 0 for agent in agents}

        assignments_created = 0
        sla_clocks_created = 0
        new_complaints_unassigned = 0
        first_responses_found = 0
        response_breaches_found = 0

        for index, complaint in enumerate(complaints):
            planned_status = planned_statuses[index]

            if complaint.created_at is None:
                raise ValueError(
                    f"Missing creation timestamp: "
                    f"{complaint.complaint_id}"
                )

            priority = complaint.priority.upper()

            if priority not in SLA_TARGETS:
                raise ValueError(
                    f"Invalid priority for {complaint.complaint_id}: "
                    f"{complaint.priority}"
                )

            start_time = normalize_datetime(complaint.created_at)
            targets = SLA_TARGETS[priority]

            response_deadline = (
                start_time
                + timedelta(minutes=targets["response_minutes"])
            )

            resolution_deadline = (
                start_time
                + timedelta(hours=targets["resolution_hours"])
            )

            # NEW complaints receive an SLA clock but no assignment.
            if planned_status == "NEW":
                make_new_complaint_agent_messages_internal(
                    db,
                    complaint.complaint_id,
                )

                first_response_at = None
                response_breached = False
                new_complaints_unassigned += 1

            else:
                category_name = categories.get(
                    complaint.category_id
                )

                if category_name not in CATEGORY_TEAM_MAP:
                    raise ValueError(
                        f"Unknown category for {complaint.complaint_id}: "
                        f"{category_name}"
                    )

                team_name = CATEGORY_TEAM_MAP[category_name]
                team = teams.get(team_name)

                if team is None:
                    raise ValueError(
                        f"Required team not found: {team_name}"
                    )

                eligible_agents = agents_by_team.get(
                    team.team_id,
                    [],
                )

                if not eligible_agents:
                    raise ValueError(
                        f"No active agents available in {team_name}."
                    )

                selected_agent = min(
                    eligible_agents,
                    key=lambda agent: (
                        workload[agent.agent_id],
                        agent.agent_id,
                    ),
                )

                if (
                    workload[selected_agent.agent_id]
                    >= selected_agent.workload_capacity
                ):
                    raise ValueError(
                        f"Agent capacity exceeded: "
                        f"{selected_agent.agent_name}"
                    )

                workload[selected_agent.agent_id] += 1

                assignment = Assignment(
                    complaint_id=complaint.complaint_id,
                    team_id=team.team_id,
                    agent_id=selected_agent.agent_id,
                    assigned_at=start_time,
                    assigned_by="SYSTEM",
                    reason=(
                        "Automatically routed based on category: "
                        f"{category_name}"
                    ),
                    is_current=True,
                )

                db.add(assignment)
                assignments_created += 1

                # Find the first actual customer-visible agent response.
                first_message = get_first_agent_response(
                    db,
                    complaint.complaint_id,
                )

                first_response_at = None
                response_breached = False

                if first_message is not None:
                    first_response_at = normalize_datetime(
                        first_message.created_at
                    )

                    if first_response_at < start_time:
                        raise ValueError(
                            "Agent response precedes complaint creation: "
                            f"{complaint.complaint_id}"
                        )

                    response_breached = (
                        first_response_at > response_deadline
                    )

                    first_responses_found += 1

                    if response_breached:
                        response_breaches_found += 1

            # Every complaint gets an SLA clock, regardless of assignment.
            sla_clock = SLAClock(
                sla_id=f"SLA-{complaint.complaint_id}",
                complaint_id=complaint.complaint_id,
                priority=priority,
                response_deadline=response_deadline,
                resolution_deadline=resolution_deadline,
                first_response_at=first_response_at,
                resolved_at=None,
                paused_at=None,
                total_paused_seconds=0,
                response_breached=response_breached,
                resolution_breached=False,
            )

            db.add(sla_clock)
            sla_clocks_created += 1

        db.commit()

        print("\nWorkflow generation completed successfully.")
        print(f"Complaints processed: {len(complaints)}")
        print(f"Planned NEW complaints: {new_complaints_unassigned}")
        print(f"Assignments created: {assignments_created}")
        print(f"SLA clocks created: {sla_clocks_created}")
        print(f"First responses found: {first_responses_found}")
        print(f"Response breaches found: {response_breaches_found}")

        print("\nAgent workloads:")

        for agent in agents:
            print(
                f"{agent.agent_name} "
                f"({agent.agent_id}): "
                f"{workload[agent.agent_id]} complaints"
            )

        print("\nTeam assignment totals:")

        for team_name in sorted(teams):
            team = teams[team_name]

            team_total = sum(
                workload[agent.agent_id]
                for agent in agents_by_team.get(team.team_id, [])
            )

            print(f"{team_name}: {team_total}")

    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_workflow()
