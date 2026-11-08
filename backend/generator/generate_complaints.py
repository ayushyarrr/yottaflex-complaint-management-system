
import argparse
import random
from decimal import Decimal

from backend.app.database import SessionLocal
from backend.app.models import (
    Customer,
    Product,
    Order,
    OrderItem,
    Category,
    Complaint,
    ComplaintProduct,
    ComplaintMessage,
    PriorityRule,
    PriorityDecision,
    PriorityDecisionRule,
)

from backend.generator.rules import (
    classify_complaint,
    determine_severity,
    calculate_priority,
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022

CHANNELS = ["EMAIL", "PHONE", "CHAT", "WEB"]

SENTIMENTS = [
    "STRONGLY NEGATIVE",
    "NEGATIVE",
    "NEUTRAL",
    "POSITIVE",
]

CATEGORY_ORDER = [
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
]


# --------------------------------------------------
# COMPLAINT DESCRIPTION TEMPLATES
# --------------------------------------------------

COMPLAINT_TEMPLATES = {
    "DELIVERY": [
        "My delivery is delayed and the tracking information has not updated.",
        "The courier has not delivered my shipment despite repeated attempts.",
        "I am unhappy because my order delivery is late.",
        "The delivery status says pending but my package has not arrived.",
    ],

    "REFUND": [
        "I requested a refund but my money has not been returned.",
        "Please process my reimbursement for the cancelled order.",
        "My refund has not been processed and I want my money back.",
        "I have contacted support several times about my refund.",
    ],

    "PAYMENT": [
        "I was charged twice for the same transaction.",
        "My payment failed but the amount was deducted.",
        "There is an incorrect charge on my billing statement.",
        "I need help resolving a payment issue.",
    ],

    "DAMAGED PRODUCT": [
        "The product arrived broken and damaged.",
        "The item is defective and is not working properly.",
        "My product has a cracked screen and appears damaged.",
        "The product malfunctioned shortly after delivery.",
    ],

    "PRODUCT SAFETY": [
        "The product is overheating and producing smoke.",
        "I experienced an electric shock while using this product.",
        "This device is unsafe and caused an injury.",
        "The appliance caught fire during normal operation.",
    ],

    "MISSING ITEM": [
        "An item is missing from my package.",
        "I received the package but one product was not received.",
        "The order arrived with fewer items than I purchased; one item is missing.",
        "One item is missing from my package.",
    ],

    "CANCELLATION": [
        "I want to cancel my order immediately.",
        "Please process my cancellation request.",
        "I requested cancellation but the order is still processing.",
        "I no longer need this order and want it cancelled.",
    ],

    "WARRANTY": [
        "I need a warranty repair for my product.",
        "My product requires replacement under warranty.",
        "Please help me with a warranty claim.",
        "The repair request under warranty has not been addressed.",
    ],

    "ACCOUNT": [
        "I cannot login to my account.",
        "My password is rejected whenever I try to sign in.",
        "I am having trouble accessing my account.",
        "Please help me resolve this account access issue.",
    ],

    "OTHER": [
        "I have a general complaint about my recent shopping experience.",
        "I need assistance with an issue that has not been resolved.",
        "I am dissatisfied with the service I received.",
        "Please contact me regarding my unresolved concern.",
    ],
}


# --------------------------------------------------
# PRIORITY RULE DEFINITIONS
# --------------------------------------------------

PRIORITY_RULE_DEFINITIONS = [
    (
        "STRONGLY_NEGATIVE_SENTIMENT",
        "SENTIMENT",
        "STRONGLY NEGATIVE",
        3,
        None,
    ),
    (
        "NEGATIVE_SENTIMENT",
        "SENTIMENT",
        "NEGATIVE",
        2,
        None,
    ),
    (
        "NEUTRAL_SENTIMENT",
        "SENTIMENT",
        "NEUTRAL",
        1,
        None,
    ),
    (
        "HIGH_ORDER_VALUE",
        "ORDER_VALUE",
        "ABOVE_10000",
        2,
        None,
    ),
    (
        "MEDIUM_ORDER_VALUE",
        "ORDER_VALUE",
        "ABOVE_5000",
        1,
        None,
    ),
    (
        "THIRD_OR_LATER_COMPLAINT",
        "RECURRENCE",
        "AT_LEAST_3",
        3,
        None,
    ),
    (
        "REPEAT_COMPLAINT",
        "RECURRENCE",
        "EXACTLY_2",
        2,
        None,
    ),
    (
        "VULNERABLE_CUSTOMER",
        "CUSTOMER",
        "IS_VULNERABLE",
        1,
        None,
    ),
    (
        "PRODUCT_SAFETY_OVERRIDE",
        "SAFETY",
        "IS_SAFETY_RISK",
        0,
        "P1",
    ),
]


def seed_priority_rules(db):
    """Insert missing priority rules without duplicating existing ones."""

    existing_rules = {
        rule.rule_name: rule
        for rule in db.query(PriorityRule).all()
    }

    for name, condition_type, condition_value, score, override in (
        PRIORITY_RULE_DEFINITIONS
    ):
        if name not in existing_rules:
            rule = PriorityRule(
                rule_name=name,
                condition_type=condition_type,
                condition_value=condition_value,
                score=score,
                priority_override=override,
                is_active=True,
            )

            db.add(rule)

    db.flush()

    return {
        rule.rule_name: rule
        for rule in db.query(PriorityRule).all()
    }


# --------------------------------------------------
# DETERMINE WHICH RULES INFLUENCED A DECISION
# --------------------------------------------------

def get_applicable_rules(
    sentiment,
    order_value,
    recurrence_count,
    is_vulnerable,
    is_safety_risk,
):
    """Return the names of rules that contributed to a priority decision."""

    applicable = []

    if sentiment == "STRONGLY NEGATIVE":
        applicable.append("STRONGLY_NEGATIVE_SENTIMENT")

    elif sentiment == "NEGATIVE":
        applicable.append("NEGATIVE_SENTIMENT")

    elif sentiment == "NEUTRAL":
        applicable.append("NEUTRAL_SENTIMENT")

    if order_value > 10000:
        applicable.append("HIGH_ORDER_VALUE")

    elif order_value > 5000:
        applicable.append("MEDIUM_ORDER_VALUE")

    if recurrence_count >= 3:
        applicable.append("THIRD_OR_LATER_COMPLAINT")

    elif recurrence_count == 2:
        applicable.append("REPEAT_COMPLAINT")

    if is_vulnerable:
        applicable.append("VULNERABLE_CUSTOMER")

    if is_safety_risk:
        applicable.append("PRODUCT_SAFETY_OVERRIDE")

    return applicable


# --------------------------------------------------
# MESSAGE GENERATION
# --------------------------------------------------

def generate_messages(complaint_id, channel, description):
    """Generate three messages for every complaint."""

    messages = [
        (
            "CUSTOMER",
            description,
            False,
        ),
        (
            "AGENT",
            "Thank you for contacting support. Your complaint has been "
            "recorded and is being reviewed by our team.",
            False,
        ),
        (
            "SYSTEM",
            "Complaint classification and priority evaluation completed.",
            True,
        ),
    ]

    result = []

    for number, (sender, message_text, is_internal) in enumerate(
        messages,
        start=1,
    ):
        result.append(
            ComplaintMessage(
                message_id=f"MSG-{complaint_id}-{number:03d}",
                complaint_id=complaint_id,
                sender_type=sender,
                message_text=message_text,
                channel=channel,
                is_internal=is_internal,
            )
        )

    return result


# --------------------------------------------------
# COMPLAINT GENERATION
# --------------------------------------------------

def generate_complaints(db, count):
    """Generate complaints, messages, product links and priority history."""

    rng = random.Random(SEED + 1)

    customers = db.query(Customer).order_by(
        Customer.customer_id
    ).all()

    products = db.query(Product).order_by(
        Product.product_id
    ).all()

    orders = db.query(Order).order_by(
        Order.order_id
    ).all()

    order_items = db.query(OrderItem).all()

    categories = {
        category.category_name: category
        for category in db.query(Category).all()
    }

    if not customers or not products or not orders:
        raise ValueError(
            "Customers, products and orders must exist before "
            "generating complaints."
        )

    missing_categories = [
        name for name in CATEGORY_ORDER
        if name not in categories
    ]

    if missing_categories:
        raise ValueError(
            f"Missing complaint categories: {missing_categories}"
        )

    orders_by_customer = {}

    for order in orders:
        orders_by_customer.setdefault(
            order.customer_id, []
        ).append(order)

    products_by_order = {}

    for item in order_items:
        products_by_order.setdefault(
            item.order_id, []
        ).append(item.product_id)

    priority_rules = seed_priority_rules(db)

    complaint_records = []
    complaint_product_records = []
    complaint_message_records = []
    priority_decisions = []

    # Tracks recurrence by customer and category.
    recurrence_tracker = {}

    # Retains the first complaint for each customer/category pair.
    previous_complaints = {}

    safety_count = 0
    missing_order_count = 0
    repeat_count = 0

    for number in range(1, count + 1):

        # Cycle through all ten categories.
        category_name = CATEGORY_ORDER[
            (number - 1) % len(CATEGORY_ORDER)
        ]

        # Deliberately create repeat complaints for selected records.
        if number > 10 and number in (11, 16, 21, 26, 31, 36):
            previous_number = number - 10

            previous = complaint_records[previous_number - 1]

            customer = next(
                customer
                for customer in customers
                if customer.customer_id == previous.customer_id
            )

        else:
            customer = rng.choice(customers)

        recurrence_key = (customer.customer_id, category_name)

        recurrence_count = (
            recurrence_tracker.get(recurrence_key, 0) + 1
        )

        recurrence_tracker[recurrence_key] = recurrence_count

        if recurrence_count > 1:
            repeat_count += 1

        previous_complaints.setdefault(
            recurrence_key,
            number,
        )

        # Safety cases are explicitly represented.
        is_safety_risk = category_name == "PRODUCT SAFETY"

        if is_safety_risk:
            safety_count += 1

        # Some complaints deliberately arrive without an order reference.
        has_order = rng.random() >= 0.10

        customer_orders = orders_by_customer.get(
            customer.customer_id, []
        )

        selected_order = None

        if has_order and customer_orders:
            selected_order = rng.choice(customer_orders)

        else:
            missing_order_count += 1

        order_value = (
            Decimal(str(selected_order.total_amount))
            if selected_order is not None
            else Decimal("0.00")
        )

        # Generate text and verify its category using the actual classifier.
        possible_descriptions = COMPLAINT_TEMPLATES[category_name]

        description = rng.choice(possible_descriptions)

        detected_category = classify_complaint(description)

        if detected_category != category_name:
            raise ValueError(
                f"Classification mismatch for complaint {number}: "
                f"expected {category_name}, got {detected_category}"
            )

        severity = determine_severity(description)

        sentiment = rng.choice(SENTIMENTS)

        score, priority, safety_override = calculate_priority(
            sentiment=sentiment,
            order_value=float(order_value),
            recurrence_count=recurrence_count,
            is_vulnerable=customer.is_vulnerable,
            is_safety_risk=is_safety_risk,
        )

        complaint_id = f"CMP-2026-{number:06d}"

        channel = rng.choice(CHANNELS)

        complaint = Complaint(
            complaint_id=complaint_id,
            customer_id=customer.customer_id,
            order_id=(
                selected_order.order_id
                if selected_order is not None
                else None
            ),
            category_id=categories[category_name].category_id,
            description=description,
            channel=channel,
            sentiment=sentiment,
            severity=severity,
            priority=priority,
            status="NEW",
            recurrence_count=recurrence_count,
        )

        db.add(complaint)
        complaint_records.append(complaint)

        # Determine the products involved in the complaint.
        if selected_order is not None:
            selected_product_ids = products_by_order.get(
                selected_order.order_id, []
            )
        else:
            selected_product_ids = []

        if not selected_product_ids:
            selected_product_ids = [
                rng.choice(products).product_id
            ]

        # Link up to two distinct products.
        selected_product_ids = list(dict.fromkeys(
            selected_product_ids
        ))[:2]

        for product_id in selected_product_ids:
            complaint_product_records.append(
                ComplaintProduct(
                    complaint_id=complaint_id,
                    product_id=product_id,
                    issue_description=description,
                )
            )

        # Generate customer, agent and system messages.
        complaint_message_records.extend(
            generate_messages(
                complaint_id,
                channel,
                description,
            )
        )

        # Preserve priority decision history.
        explanation_parts = [
            f"Sentiment: {sentiment}",
            f"Order value: INR {order_value}",
            f"Recurrence count: {recurrence_count}",
            f"Vulnerable customer: {customer.is_vulnerable}",
        ]

        if safety_override:
            explanation_parts.append(
                "Product safety override forced priority P1"
            )

        else:
            explanation_parts.append(
                f"Priority calculated from score {score}"
            )

        decision = PriorityDecision(
            complaint_id=complaint_id,
            calculated_score=score,
            assigned_priority=priority,
            safety_override_applied=(
                "TRUE" if safety_override else "FALSE"
            ),
            explanation="; ".join(explanation_parts),
        )

        priority_decisions.append(
            (decision, get_applicable_rules(
                sentiment=sentiment,
                order_value=float(order_value),
                recurrence_count=recurrence_count,
                is_vulnerable=customer.is_vulnerable,
                is_safety_risk=is_safety_risk,
            ))
        )

    # Insert complaints first to satisfy foreign-key constraints.
    db.flush()

    db.add_all(complaint_product_records)
    db.add_all(complaint_message_records)

    db.flush()

    # Insert decisions and obtain their generated primary keys.
    for decision, applicable_rule_names in priority_decisions:
        db.add(decision)

    db.flush()

    # Connect decisions to the rules that influenced them.
    decision_rule_links = []

    for decision, applicable_rule_names in priority_decisions:

        for rule_name in applicable_rule_names:

            rule = priority_rules[rule_name]

            decision_rule_links.append(
                PriorityDecisionRule(
                    decision_id=decision.decision_id,
                    rule_id=rule.rule_id,
                )
            )

    db.add_all(decision_rule_links)
    db.flush()

    print(f"Generated {len(complaint_records)} complaints.")
    print(
        f"Generated {len(complaint_product_records)} complaint-product links."
    )
    print(
        f"Generated {len(complaint_message_records)} complaint messages."
    )
    print(f"Generated {len(priority_decisions)} priority decisions.")
    print(
        f"Generated {len(decision_rule_links)} decision-rule links."
    )
    print(f"Repeat complaints: {repeat_count}")
    print(f"Product safety complaints: {safety_count}")
    print(f"Complaints without an order: {missing_order_count}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Generate synthetic complaint records."
    )

    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter",
    )

    args = parser.parse_args()

    if args.mode == "starter":
        complaint_count = 40

    else:
        complaint_count = 2000

    db = SessionLocal()

    try:

        existing_count = db.query(Complaint).count()

        if existing_count > 0:
            raise RuntimeError(
                f"Found {existing_count} existing complaints. "
                "Generation stopped to prevent duplicate records."
            )

        print("Starting complaint generation...")
        print(f"Mode: {args.mode}")
        print(f"Target complaints: {complaint_count}")

        generate_complaints(db, complaint_count)

        db.commit()

        print("\nComplaint generation completed successfully.")
        print(f"Mode: {args.mode}")
        print(f"Seed: {SEED}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
