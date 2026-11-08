
import argparse
import re
import sys
from collections import Counter, defaultdict

from sqlalchemy import text

from backend.app.database import SessionLocal, engine
from backend.app.models import (
    Agent,
    Assignment,
    Category,
    Complaint,
    ComplaintEvent,
    ComplaintMessage,
    ComplaintProduct,
    Customer,
    Order,
    OrderItem,
    PriorityDecision,
    PriorityDecisionRule,
    Product,
    Resolution,
    SLAClock,
    Survey,
    Team,
)
from backend.generator.rules import classify_complaint
from backend.generator.lifecycle_config import get_status_distribution


SEED = 20261022

EXPECTED_COUNTS = {
    "starter": {
        "customers": 100,
        "products": 30,
        "categories": 10,
        "orders": 160,
        "complaints": 40,
        "complaint_messages": 120,
        "priority_decisions": 40,
        "priority_decision_rules": 75,
    },
    "full": {
        "customers": 5000,
        "products": 500,
        "categories": 10,
        "orders": 8000,
        "complaints": 2000,
        "complaint_messages": 6000,
        "priority_decisions": 2000,
    },
}

ALLOWED_CHANNELS = {"EMAIL", "PHONE", "CHAT", "WEB"}
ALLOWED_SENTIMENTS = {
    "STRONGLY NEGATIVE",
    "NEGATIVE",
    "NEUTRAL",
    "POSITIVE",
}
ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
ALLOWED_PRIORITIES = {"P1", "P2", "P3", "P4"}

EXPECTED_CATEGORIES = {
    "DELIVERY",
    "REFUND",
    "PAYMENT",
    "DAMAGED PRODUCT",
    "PRODUCT SAFETY",
    "MISSING ITEM",
    "CANCELLATION",
    "WARRANTY",
    "ACCOUNT",
    "OTHER",
}


class Validator:
    def __init__(self):
        self.errors = []
        self.passes = 0
        self.warnings = 0

    def check(self, condition, description):
        if condition:
            self.passes += 1
            print(f"[PASS] {description}")
        else:
            self.errors.append(description)
            print(f"[FAIL] {description}")

    def warning(self, description):
        self.warnings += 1
        print(f"[WARN] {description}")

    def finish(self):
        print("\n" + "=" * 55)
        print("VALIDATION SUMMARY")
        print("=" * 55)
        print(f"Passed checks: {self.passes}")
        print(f"Warnings:      {self.warnings}")
        print(f"Failed checks: {len(self.errors)}")

        if self.errors:
            print("\nIssues requiring attention:")
            for number, error in enumerate(self.errors, start=1):
                print(f"{number}. {error}")

            print("\nVALIDATION RESULT: FAILED")
            return False

        print("\nVALIDATION RESULT: PASSED")
        return True


def timestamps_are_ordered(*values):
    """Compare timestamps safely when SQLite returns naive datetimes."""
    present = [value for value in values if value is not None]

    for earlier, later in zip(present, present[1:]):
        earlier = earlier.replace(tzinfo=None)
        later = later.replace(tzinfo=None)

        if later < earlier:
            return False

    return True


def validate_database(validator):
    with engine.connect() as connection:
        violations = connection.exec_driver_sql(
            "PRAGMA foreign_key_check"
        ).fetchall()

    validator.check(
        len(violations) == 0,
        f"Database foreign-key integrity ({len(violations)} violations)",
    )

    if violations:
        for violation in violations[:10]:
            validator.errors.append(
                f"Foreign-key violation: table={violation[0]}, "
                f"rowid={violation[1]}, parent={violation[2]}"
            )


def validate_counts(db, validator, mode):
    if mode == "operational":
        print(
            "Operational mode: exact generated record counts "
            "and synthetic distribution targets are not enforced."
        )
        return

    expected = EXPECTED_COUNTS[mode]

    models = {
        "customers": Customer,
        "products": Product,
        "categories": Category,
        "orders": Order,
        "complaints": Complaint,
        "complaint_messages": ComplaintMessage,
        "priority_decisions": PriorityDecision,
    }

    if mode == "starter":
        models["priority_decision_rules"] = PriorityDecisionRule

    for name, model in models.items():
        actual = db.query(model).count()
        target = expected[name]

        validator.check(
            actual == target,
            f"{name}: expected {target}, found {actual}",
        )

    if mode == "starter":
        actual = db.query(ComplaintProduct).count()
        validator.check(
            actual == 58,
            f"complaint-product links: expected 58, found {actual}",
        )

        actual = db.query(OrderItem).count()
        validator.check(
            actual == 330,
            f"order items: expected 330, found {actual}",
        )


def validate_categories(db, validator):
    categories = db.query(Category).all()
    names = {category.category_name for category in categories}

    validator.check(
        names == EXPECTED_CATEGORIES,
        "All 10 expected complaint categories exist",
    )

    category_lookup = {
        category.category_id: category.category_name
        for category in categories
    }

    return category_lookup


def validate_ids(db, validator):
    customers = db.query(Customer).all()
    products = db.query(Product).all()
    orders = db.query(Order).all()
    complaints = db.query(Complaint).all()
    messages = db.query(ComplaintMessage).all()

    validator.check(
        all(re.fullmatch(r"CUS-\d{6}", item.customer_id) for item in customers),
        "Customer IDs follow CUS-000001 format",
    )

    validator.check(
        all(re.fullmatch(r"PROD-\d{6}", item.product_id) for item in products),
        "Product IDs follow PROD-000001 format",
    )

    validator.check(
        all(re.fullmatch(r"ORD-2026-\d{6}", item.order_id) for item in orders),
        "Order IDs follow ORD-2026-000001 format",
    )

    validator.check(
        all(
            re.fullmatch(r"CMP-2026-\d{6}", item.complaint_id)
            for item in complaints
        ),
        "Complaint IDs follow CMP-2026-000001 format",
    )

    validator.check(
        all(
            re.fullmatch(
                r"MSG-CMP-2026-\d{6}-\d{3}",
                item.message_id,
            )
            for item in messages
        ),
        "Message IDs follow MSG-CMP-2026-000001-001 format",
    )


def validate_complaints(db, validator, category_lookup, mode):
    complaints = db.query(Complaint).all()

    messages_by_complaint = Counter()
    for message in db.query(ComplaintMessage).all():
        messages_by_complaint[message.complaint_id] += 1

    safety_count = 0
    no_order_count = 0
    repeat_count = 0

    for complaint in complaints:
        category_name = category_lookup.get(complaint.category_id)

        validator.check(
            category_name is not None,
            f"{complaint.complaint_id}: valid category reference",
        )

        validator.check(
            complaint.channel in ALLOWED_CHANNELS,
            f"{complaint.complaint_id}: valid channel",
        )

        validator.check(
            complaint.sentiment in ALLOWED_SENTIMENTS,
            f"{complaint.complaint_id}: valid sentiment",
        )

        validator.check(
            complaint.severity in ALLOWED_SEVERITIES,
            f"{complaint.complaint_id}: valid severity",
        )

        validator.check(
            complaint.priority in ALLOWED_PRIORITIES,
            f"{complaint.complaint_id}: valid priority",
        )

        validator.check(
            complaint.recurrence_count >= 1,
            f"{complaint.complaint_id}: recurrence count is at least 1",
        )

        validator.check(
            timestamps_are_ordered(
                complaint.created_at,
                complaint.updated_at,
            ),
            f"{complaint.complaint_id}: valid creation/update chronology",
        )

        if category_name is not None:
            actual_category = classify_complaint(complaint.description)

            validator.check(
                actual_category == category_name,
                f"{complaint.complaint_id}: description classification "
                f"matches {category_name}",
            )

            if category_name == "PRODUCT SAFETY":
                safety_count += 1

                validator.check(
                    complaint.priority == "P1",
                    f"{complaint.complaint_id}: safety complaint has P1 priority",
                )

        if complaint.order_id is None:
            no_order_count += 1

        if complaint.recurrence_count > 1:
            repeat_count += 1

        if mode == "operational":
            validator.check(
                messages_by_complaint[complaint.complaint_id] >= 1,
                f"{complaint.complaint_id}: at least 1 message",
            )
        else:
            validator.check(
                messages_by_complaint[complaint.complaint_id] == 3,
                f"{complaint.complaint_id}: exactly 3 generated messages",
            )

    print("\nComplaint observations:")
    print(f"  Safety complaints: {safety_count}")
    print(f"  Complaints without orders: {no_order_count}")
    print(f"  Complaints marked as repeats: {repeat_count}")

    if mode == "starter":
        validator.check(
            safety_count == 4,
            f"Expected 4 product safety complaints, found {safety_count}",
        )

        validator.check(
            no_order_count == 13,
            f"Expected 13 complaints without orders, found {no_order_count}",
        )

    elif mode == "full":
        validator.check(
            safety_count == 200,
            f"Expected 200 product safety complaints, found {safety_count}",
        )

        validator.check(
            no_order_count > 0,
            f"At least one complaint without an order exists "
            f"(found {no_order_count})",
        )


def validate_priority_decisions(db, validator):
    complaints = {
        item.complaint_id: item
        for item in db.query(Complaint).all()
    }

    decisions = db.query(PriorityDecision).all()
    decisions_by_complaint = Counter()

    for decision in decisions:
        decisions_by_complaint[decision.complaint_id] += 1

        complaint = complaints.get(decision.complaint_id)

        validator.check(
            complaint is not None,
            f"Priority decision {decision.decision_id}: complaint exists",
        )

        if complaint is None:
            continue

        validator.check(
            decision.assigned_priority == complaint.priority,
            f"{complaint.complaint_id}: decision priority matches complaint",
        )

        validator.check(
            decision.assigned_priority in ALLOWED_PRIORITIES,
            f"{complaint.complaint_id}: valid decision priority",
        )

        override = decision.safety_override_applied

        validator.check(
            override in {"TRUE", "FALSE", None},
            f"{complaint.complaint_id}: valid safety override value",
        )

        category_name = None
        category = db.get(Category, complaint.category_id)

        if category:
            category_name = category.category_name

        if category_name == "PRODUCT SAFETY":
            validator.check(
                override == "TRUE",
                f"{complaint.complaint_id}: safety override recorded",
            )

    validator.check(
        all(count == 1 for count in decisions_by_complaint.values()),
        "No complaint has multiple priority decisions",
    )

    validator.check(
        set(decisions_by_complaint) == set(complaints),
        "Every complaint has a priority decision",
    )


def validate_assignments(db, validator, mode):
    agents = {
        agent.agent_id: agent
        for agent in db.query(Agent).all()
    }

    complaints = db.query(Complaint).all()
    assignments = db.query(Assignment).all()
    current_counts = Counter()

    for assignment in assignments:
        agent = agents.get(assignment.agent_id)

        validator.check(
            agent is not None,
            f"Assignment {assignment.assignment_id}: agent exists",
        )

        if agent is not None:
            validator.check(
                agent.team_id == assignment.team_id,
                f"Assignment {assignment.assignment_id}: "
                f"agent belongs to assigned team",
            )

        if assignment.is_current:
            current_counts[assignment.complaint_id] += 1

    validator.check(
        all(count <= 1 for count in current_counts.values()),
        "Each complaint has at most one current assignment",
    )

    if mode in ("starter", "full"):
        planned_statuses = get_status_distribution(len(complaints))

        validator.check(
            len(planned_statuses) == len(complaints),
            "Lifecycle distribution matches complaint count",
        )

        if len(planned_statuses) == len(complaints):
            expected_assignments = 0

            for index, complaint in enumerate(
                sorted(complaints, key=lambda item: item.complaint_id)
            ):
                planned_status = planned_statuses[index]
                actual_assignments = current_counts[
                    complaint.complaint_id
                ]

                should_be_assigned = planned_status != "NEW"

                if should_be_assigned:
                    expected_assignments += 1

                validator.check(
                    actual_assignments == (
                        1 if should_be_assigned else 0
                    ),
                    f"{complaint.complaint_id}: assignment "
                    f"matches planned status {planned_status}",
                )

                validator.check(
                    complaint.status == planned_status,
                    f"{complaint.complaint_id}: actual status "
                    f"matches planned status {planned_status}",
                )

            actual_current_assignments = sum(
                current_counts.values()
            )

            validator.check(
                actual_current_assignments == expected_assignments,
                f"Current assignments: expected "
                f"{expected_assignments}, found "
                f"{actual_current_assignments}",
            )


def validate_messages(db, validator):
    complaints = {
        item.complaint_id: item
        for item in db.query(Complaint).all()
    }

    for message in db.query(ComplaintMessage).all():
        complaint = complaints.get(message.complaint_id)

        if complaint is None:
            continue

        validator.check(
            timestamps_are_ordered(
                complaint.created_at,
                message.created_at,
            ),
            f"{message.message_id}: message is not before complaint creation",
        )

        validator.check(
            message.channel in ALLOWED_CHANNELS,
            f"{message.message_id}: valid message channel",
        )

        validator.check(
            message.sender_type in {"CUSTOMER", "AGENT", "SYSTEM"},
            f"{message.message_id}: valid sender type",
        )



def validate_optional_records(db, validator, mode):
    complaints = {
        item.complaint_id: item
        for item in db.query(Complaint).all()
    }

    resolutions = {
        item.resolution_id: item
        for item in db.query(Resolution).all()
    }

    # Resolution chronology and agent references.
    for resolution in resolutions.values():
        complaint = complaints.get(resolution.complaint_id)

        if complaint:
            validator.check(
                timestamps_are_ordered(
                    complaint.created_at,
                    resolution.resolved_at,
                ),
                f"{resolution.resolution_id}: resolution chronology",
            )

    # Surveys must refer to the same complaint as their resolution.
    events_by_complaint = defaultdict(list)

    for event in db.query(ComplaintEvent).all():
        events_by_complaint[event.complaint_id].append(event)

    for survey in db.query(Survey).all():
        resolution = resolutions.get(survey.resolution_id)
        complaint = complaints.get(survey.complaint_id)

        validator.check(
            resolution is not None,
            f"Survey {survey.survey_id}: resolution exists",
        )

        validator.check(
            complaint is not None,
            f"Survey {survey.survey_id}: complaint exists",
        )

        validator.check(
            1 <= survey.rating <= 5,
            f"Survey {survey.survey_id}: rating is between 1 and 5",
        )

        if resolution and complaint:
            validator.check(
                resolution.complaint_id == survey.complaint_id,
                f"Survey {survey.survey_id}: complaint matches resolution",
            )

            validator.check(
                resolution.is_final,
                f"Survey {survey.survey_id}: resolution is final",
            )

            validator.check(
                timestamps_are_ordered(
                    complaint.created_at,
                    resolution.resolved_at,
                    survey.submitted_at,
                ),
                f"Survey {survey.survey_id}: valid chronology",
            )

            closure_events = [
                event
                for event in events_by_complaint[survey.complaint_id]
                if (
                    event.event_type == "STATUS_CHANGED"
                    and event.new_value == "CLOSED"
                )
            ]

            submitted_after_closure = any(
                timestamps_are_ordered(
                    event.created_at,
                    survey.submitted_at,
                )
                for event in closure_events
            )

            if mode == "operational" and not closure_events:
                validator.warning(
                    f"Survey {survey.survey_id}: no CLOSED event in "
                    "legacy operational history"
                )
            else:
                validator.check(
                    submitted_after_closure,
                    f"Survey {survey.survey_id}: submitted after closure",
                )

    # SLA records.
    for sla in db.query(SLAClock).all():
        complaint = complaints.get(sla.complaint_id)

        if complaint:
            validator.check(
                timestamps_are_ordered(
                    complaint.created_at,
                    sla.created_at,
                ),
                f"{sla.sla_id}: SLA creation chronology",
            )

        validator.check(
            sla.priority in ALLOWED_PRIORITIES,
            f"{sla.sla_id}: valid SLA priority",
        )

        validator.check(
            sla.total_paused_seconds >= 0,
            f"{sla.sla_id}: non-negative paused duration",
        )

        if sla.first_response_at and complaint:
            validator.check(
                timestamps_are_ordered(
                    complaint.created_at,
                    sla.first_response_at,
                ),
                f"{sla.sla_id}: first response chronology",
            )

        if sla.resolved_at and complaint:
            validator.check(
                timestamps_are_ordered(
                    complaint.created_at,
                    sla.resolved_at,
                ),
                f"{sla.sla_id}: resolution chronology",
            )

    # Complaint events.
    for event in db.query(ComplaintEvent).all():
        complaint = complaints.get(event.complaint_id)

        if complaint:
            validator.check(
                timestamps_are_ordered(
                    complaint.created_at,
                    event.created_at,
                ),
                f"Event {event.event_id}: event chronology",
            )

    optional_counts = {
        "assignments": db.query(Assignment).count(),
        "SLA clocks": db.query(SLAClock).count(),
        "resolutions": db.query(Resolution).count(),
        "surveys": db.query(Survey).count(),
        "complaint events": db.query(ComplaintEvent).count(),
    }

    print("\nAdditional workflow records:")
    for name, count in optional_counts.items():
        print(f"  {name}: {count}")

        if count == 0:
            validator.warning(
                f"No {name} exist yet; this workflow area has not been populated."
            )



def main():
    parser = argparse.ArgumentParser(
        description="Validate the YottaFlex complaint dataset."
    )
    parser.add_argument(
        "--mode",
        choices=["starter", "full", "operational"],
        default="starter",
        help="Dataset size to validate (default: starter).",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("YOTTAFLEX COMPLAINT DATA VALIDATOR")
    print("=" * 55)
    print(f"Mode: {args.mode}")
    print(f"Seed: {SEED}")
    print("Read-only validation: enabled\n")

    validator = Validator()
    db = SessionLocal()

    try:
        validate_database(validator)
        validate_counts(db, validator, args.mode)

        category_lookup = validate_categories(db, validator)

        validate_ids(db, validator)
        validate_complaints(db, validator, category_lookup, args.mode)
        validate_priority_decisions(db, validator)
        validate_assignments(db, validator, args.mode)
        validate_messages(db, validator)
        validate_optional_records(db, validator, args.mode)

    except Exception as error:
        print(f"\n[ERROR] Validation could not complete: {error}")
        raise

    finally:
        db.close()

    success = validator.finish()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
