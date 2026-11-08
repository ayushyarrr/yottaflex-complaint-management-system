
# Complaint classification and priority rules.

CATEGORY_KEYWORDS = {
    "PRODUCT SAFETY": [
        "unsafe", "injury", "injured", "overheating",
        "fire", "smoke", "electric shock", "dangerous"
    ],
    "DAMAGED PRODUCT": [
        "broken", "damaged", "defective", "cracked",
        "not working", "malfunction"
    ],
    "DELIVERY": [
        "delivery", "shipment", "courier", "late delivery",
        "delayed", "tracking"
    ],
    "REFUND": [
        "refund", "money back", "reimbursement"
    ],
    "PAYMENT": [
        "payment", "charged", "transaction", "billing"
    ],
    "MISSING ITEM": [
        "missing", "not received", "item absent"
    ],
    "CANCELLATION": [
        "cancel", "cancellation"
    ],
    "WARRANTY": [
        "warranty", "repair", "replacement"
    ],
    "ACCOUNT": [
        "login", "password", "account", "sign in"
    ]
}


def classify_complaint(description):
    """
    Classify complaint text using deterministic keyword matching.
    Safety-related keywords receive the highest precedence.
    """

    text = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category

    return "OTHER"


def determine_severity(description):
    """
    Determine complaint severity using transparent keyword rules.
    """

    text = description.lower()

    critical_terms = [
        "injury", "injured", "electric shock",
        "fire", "smoke", "explosion"
    ]

    high_terms = [
        "unsafe", "dangerous", "overheating",
        "completely broken", "serious"
    ]

    if any(term in text for term in critical_terms):
        return "CRITICAL"

    if any(term in text for term in high_terms):
        return "HIGH"

    if any(term in text for term in ["damaged", "defective", "broken"]):
        return "MEDIUM"

    return "LOW"


def calculate_priority(
    sentiment,
    order_value,
    recurrence_count,
    is_vulnerable,
    is_safety_risk=False
):
    """
    Calculate complaint priority using documented scoring rules.

    Returns:
        score, priority, safety_override_applied
    """

    score = 0

    sentiment_scores = {
        "STRONGLY NEGATIVE": 3,
        "NEGATIVE": 2,
        "NEUTRAL": 1,
        "POSITIVE": 0
    }

    score += sentiment_scores.get(sentiment.upper(), 0)

    if order_value > 10000:
        score += 2
    elif order_value > 5000:
        score += 1

    if recurrence_count >= 3:
        score += 3
    elif recurrence_count == 2:
        score += 2

    if is_vulnerable:
        score += 1

    if is_safety_risk:
        return score, "P1", True

    if score >= 7:
        priority = "P1"
    elif score >= 5:
        priority = "P2"
    elif score >= 3:
        priority = "P3"
    else:
        priority = "P4"

    return score, priority, False
