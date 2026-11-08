
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    SLAClock,
    Team,
)
from backend.app.schemas.complaint import ComplaintCreate

from backend.generator.generate_complaints import (
    get_applicable_rules,
    seed_priority_rules,
)
from backend.generator.generate_workflow import (
    CATEGORY_TEAM_MAP,
    SLA_TARGETS,
)
from backend.generator.rules import (
    calculate_priority,
    classify_complaint,
    determine_severity,
)


def generate_complaint_id(db: Session) -> str:
    """Generate the next complaint ID for the current year."""

    year = 2026
    prefix = f"CMP-{year}-"

    existing_ids = (
        db.query(Complaint.complaint_id)
        .filter(Complaint.complaint_id.like(f"{prefix}%"))
        .all()
    )

    highest_number = 0

    for (complaint_id,) in existing_ids:
        try:
            number = int(complaint_id.rsplit("-", 1)[1])
            highest_number = max(highest_number, number)
        except (ValueError, IndexError):
            continue

    next_number = highest_number + 1

    while True:
        candidate = f"{prefix}{next_number:06d}"

        exists = (
            db.query(Complaint)
            .filter(Complaint.complaint_id == candidate)
            .first()
        )

        if not exists:
            return candidate

        next_number += 1


def get_recurrence_count(
    db: Session,
    customer_id: str,
    category_id: int,
) -> int:
    """Count previous complaints by the same customer in this category."""

    previous_count = (
        db.query(func.count(Complaint.complaint_id))
        .filter(
            Complaint.customer_id == customer_id,
            Complaint.category_id == category_id,
        )
        .scalar()
    )

    return (previous_count or 0) + 1


def get_products_for_complaint(
    db: Session,
    payload: ComplaintCreate,
    order: Order | None,
) -> list[Product]:
    """
    Resolve products associated with a complaint.

    Explicit product IDs take precedence.
    Otherwise, products are inherited from the linked order.
    """

    if payload.product_ids is not None:
        products = (
            db.query(Product)
            .filter(Product.product_id.in_(payload.product_ids))
            .all()
        )

        found_ids = {product.product_id for product in products}
        missing_ids = set(payload.product_ids) - found_ids

        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Products not found: {sorted(missing_ids)}",
            )

        if order:
            order_product_ids = {
                item.product_id
                for item in db.query(OrderItem)
                .filter(OrderItem.order_id == order.order_id)
                .all()
            }

            unrelated_ids = found_ids - order_product_ids

            if unrelated_ids:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "The selected products do not belong to the "
                        f"provided order: {sorted(unrelated_ids)}"
                    ),
                )

        return products

    if order:
        order_items = (
            db.query(OrderItem)
            .filter(OrderItem.order_id == order.order_id)
            .all()
        )

        product_ids = list({
            item.product_id for item in order_items
        })

        if not product_ids:
            return []

        return (
            db.query(Product)
            .filter(Product.product_id.in_(product_ids))
            .all()
        )

    return []


def select_agent(
    db: Session,
    team: Team,
) -> Agent:
    """Select the least-loaded active agent within the assigned team."""

    agents = (
        db.query(Agent)
        .filter(
            Agent.team_id == team.team_id,
            Agent.is_active.is_(True),
        )
        .order_by(Agent.agent_id)
        .all()
    )

    available_agents = []

    for agent in agents:
        current_workload = (
            db.query(func.count(Assignment.assignment_id))
            .filter(
                Assignment.agent_id == agent.agent_id,
                Assignment.is_current.is_(True),
            )
            .scalar()
        ) or 0

        if current_workload < agent.workload_capacity:
            available_agents.append(
                (current_workload, agent.agent_id, agent)
            )

    if not available_agents:
        raise HTTPException(
            status_code=503,
            detail=f"No available agents in team {team.team_name}.",
        )

    available_agents.sort(key=lambda item: (item[0], item[1]))

    return available_agents[0][2]


def create_complaint(
    db: Session,
    payload: ComplaintCreate,
) -> Complaint:
    """
    Create a complaint and all its initial workflow records.

    The operation is transactional. If any step fails,
    all changes are rolled back.
    """

    try:
        # -------------------------------------------------
        # 1. Validate the customer
        # -------------------------------------------------

        customer = (
            db.query(Customer)
            .filter(Customer.customer_id == payload.customer_id)
            .first()
        )

        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        # -------------------------------------------------
        # 2. Validate the optional order
        # -------------------------------------------------

        order = None

        if payload.order_id:
            order = (
                db.query(Order)
                .filter(Order.order_id == payload.order_id)
                .first()
            )

            if not order:
                raise HTTPException(
                    status_code=404,
                    detail="Order not found.",
                )

            if order.customer_id != customer.customer_id:
                raise HTTPException(
                    status_code=400,
                    detail="The order does not belong to this customer.",
                )

        # -------------------------------------------------
        # 3. Resolve associated products
        # -------------------------------------------------

        products = get_products_for_complaint(
            db=db,
            payload=payload,
            order=order,
        )

        # -------------------------------------------------
        # 4. Classify the complaint
        # -------------------------------------------------

        category_name = classify_complaint(payload.description)

        category = (
            db.query(Category)
            .filter(
                Category.category_name == category_name,
                Category.is_active.is_(True),
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=500,
                detail=f"Category configuration missing: {category_name}.",
            )

        severity = determine_severity(payload.description)
        # A safety-sensitive product elevates the complaint's severity.
        has_safety_sensitive_product = any(
            product.is_safety_sensitive for product in products
            )
        if has_safety_sensitive_product and severity in ("LOW", "MEDIUM"):
            severity = "HIGH"
        is_safety_risk = (
            category_name == "PRODUCT SAFETY"
            or has_safety_sensitive_product
        )

        # -------------------------------------------------
        # 5. Calculate recurrence and priority
        # -------------------------------------------------

        recurrence_count = get_recurrence_count(
            db=db,
            customer_id=customer.customer_id,
            category_id=category.category_id,
        )

        order_value = (
            float(order.total_amount)
            if order is not None
            else 0.0
        )


        score, priority, safety_override = calculate_priority(
            sentiment=payload.sentiment,
            order_value=order_value,
            recurrence_count=recurrence_count,
            is_vulnerable=customer.is_vulnerable,
            is_safety_risk=is_safety_risk,
        )

        # -------------------------------------------------
        # 6. Generate the complaint record
        # -------------------------------------------------

        complaint_id = generate_complaint_id(db)

        complaint = Complaint(
            complaint_id=complaint_id,
            customer_id=customer.customer_id,
            order_id=order.order_id if order else None,
            category_id=category.category_id,
            description=payload.description,
            channel=payload.channel,
            sentiment=payload.sentiment,
            severity=severity,
            priority=priority,
            status="NEW",
            recurrence_count=recurrence_count,
        )

        db.add(complaint)
        db.flush()

        # -------------------------------------------------
        # 7. Create product associations
        # -------------------------------------------------

        for product in products:
            db.add(
                ComplaintProduct(
                    complaint_id=complaint_id,
                    product_id=product.product_id,
                    issue_description=payload.description,
                )
            )

        # -------------------------------------------------
        # 8. Record the priority decision and rule history
        # -------------------------------------------------

        rule_map = seed_priority_rules(db)

        applicable_rule_names = get_applicable_rules(
            sentiment=payload.sentiment,
            order_value=order_value,
            recurrence_count=recurrence_count,
            is_vulnerable=customer.is_vulnerable,
            is_safety_risk=is_safety_risk,
        )

        decision = PriorityDecision(
            complaint_id=complaint_id,
            calculated_score=score,
            assigned_priority=priority,
            safety_override_applied=(
                "TRUE" if safety_override else "FALSE"
            ),
            explanation=(
                f"Priority {priority} assigned with score {score}. "
                f"Safety override applied: {safety_override}."
            ),
        )

        db.add(decision)
        db.flush()

        for rule_name in applicable_rule_names:
            rule = rule_map.get(rule_name)

            if rule:
                db.add(
                    PriorityDecisionRule(
                        decision_id=decision.decision_id,
                        rule_id=rule.rule_id,
                    )
                )

        # -------------------------------------------------
        # 9. Determine the responsible team
        # -------------------------------------------------

        if is_safety_risk:
            team_name = "Safety Response"
        else:
            team_name = CATEGORY_TEAM_MAP.get(
                category_name,
                "General Support",
            )

        team = (
            db.query(Team)
            .filter(
                Team.team_name == team_name,
                Team.is_active.is_(True),
            )
            .first()
        )

        if not team:
            raise HTTPException(
                status_code=500,
                detail=f"Required team is unavailable: {team_name}.",
            )

        agent = select_agent(db, team)

        # -------------------------------------------------
        # 10. Create the assignment
        # -------------------------------------------------

        assignment = Assignment(
            complaint_id=complaint_id,
            team_id=team.team_id,
            agent_id=agent.agent_id,
            assigned_by="SYSTEM",
            reason=(
                f"Automatically routed based on category "
                f"{category_name} and priority {priority}."
            ),
            is_current=True,
        )

        db.add(assignment)

        complaint.status = "ASSIGNED"

        # -------------------------------------------------
        # 11. Create the SLA clock
        # -------------------------------------------------

        db.flush()

        sla_target = SLA_TARGETS[priority]

        response_deadline = (
            complaint.created_at
            + timedelta(minutes=sla_target["response_minutes"])
        )

        resolution_deadline = (
            complaint.created_at
            + timedelta(hours=sla_target["resolution_hours"])
        )

        sla_clock = SLAClock(
            sla_id=f"SLA-{complaint_id}",
            complaint_id=complaint_id,
            priority=priority,
            response_deadline=response_deadline,
            resolution_deadline=resolution_deadline,
            first_response_at=None,
            resolved_at=None,
            paused_at=None,
            total_paused_seconds=0,
            response_breached=False,
            resolution_breached=False,
        )

        db.add(sla_clock)

        # -------------------------------------------------
        # 12. Record the initial customer message
        # -------------------------------------------------

        customer_message = ComplaintMessage(
            message_id=f"MSG-{complaint_id}-001",
            complaint_id=complaint_id,
            sender_type="CUSTOMER",
            message_text=payload.description,
            channel=payload.channel,
            is_internal=False,
        )

        system_message = ComplaintMessage(
            message_id=f"MSG-{complaint_id}-002",
            complaint_id=complaint_id,
            sender_type="SYSTEM",
            message_text=(
                f"Complaint classified as {category_name}, "
                f"severity {severity}, priority {priority}. "
                f"Assigned to {team_name}."
            ),
            channel=payload.channel,
            is_internal=True,
        )

        db.add_all([customer_message, system_message])

        # -------------------------------------------------
        # 13. Preserve workflow history through events
        # -------------------------------------------------

        events = [
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="COMPLAINT_CREATED",
                old_value=None,
                new_value="NEW",
                description="Complaint submitted by customer.",
                performed_by="CUSTOMER",
            ),
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="CLASSIFIED",
                old_value=None,
                new_value=category_name,
                description=(
                    f"Automatically classified with severity {severity}."
                ),
                performed_by="SYSTEM",
            ),
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="PRIORITY_DECIDED",
                old_value=None,
                new_value=priority,
                description=(
                    f"Priority score: {score}. "
                    f"Safety override: {safety_override}."
                ),
                performed_by="SYSTEM",
            ),
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="ASSIGNED",
                old_value=None,
                new_value=team_name,
                description=f"Assigned to {agent.agent_name}.",
                performed_by="SYSTEM",
            ),
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="STATUS_CHANGED",
                old_value="NEW",
                new_value="ASSIGNED",
                description="Complaint automatically assigned.",
                performed_by="SYSTEM",
            ),
        ]

        db.add_all(events)

        # -------------------------------------------------
        # 14. Commit the complete workflow
        # -------------------------------------------------

        db.commit()
        db.refresh(complaint)

        return complaint

    except Exception:
        db.rollback()
        raise
