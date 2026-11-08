
import pytest

from backend.generator.rules import (
    classify_complaint,
    determine_severity,
    calculate_priority,
)


@pytest.mark.parametrize(
    "description, expected",
    [
        ("My package delivery is late", "DELIVERY"),
        ("I want a refund for my order", "REFUND"),
        ("I was charged twice for payment", "PAYMENT"),
        ("The product arrived broken", "DAMAGED PRODUCT"),
        ("My item is missing", "MISSING ITEM"),
        ("I want to cancel my order", "CANCELLATION"),
        ("I need a warranty repair", "WARRANTY"),
        ("I cannot login to my account", "ACCOUNT"),
        ("The product is overheating and producing smoke", "PRODUCT SAFETY"),
        ("I have a general question", "OTHER"),
    ],
)
def test_complaint_classification(description, expected):
    assert classify_complaint(description) == expected


@pytest.mark.parametrize(
    "description, expected",
    [
        ("The product caused an injury", "CRITICAL"),
        ("The device is producing smoke", "CRITICAL"),
        ("The product is overheating", "HIGH"),
        ("The item is damaged", "MEDIUM"),
        ("I have a question about my order", "LOW"),
    ],
)
def test_complaint_severity(description, expected):
    assert determine_severity(description) == expected


def test_product_safety_always_receives_p1():
    score, priority, safety_override = calculate_priority(
        sentiment="NEUTRAL",
        order_value=100,
        recurrence_count=1,
        is_vulnerable=False,
        is_safety_risk=True,
    )

    assert priority == "P1"
    assert safety_override is True


def test_high_priority_score():
    score, priority, safety_override = calculate_priority(
        sentiment="STRONGLY NEGATIVE",
        order_value=15000,
        recurrence_count=3,
        is_vulnerable=True,
        is_safety_risk=False,
    )

    assert score == 9
    assert priority == "P1"
    assert safety_override is False


def test_low_priority_score():
    score, priority, safety_override = calculate_priority(
        sentiment="POSITIVE",
        order_value=1000,
        recurrence_count=1,
        is_vulnerable=False,
        is_safety_risk=False,
    )

    assert score == 0
    assert priority == "P4"
    assert safety_override is False


def test_medium_priority_score():
    score, priority, safety_override = calculate_priority(
        sentiment="NEGATIVE",
        order_value=6000,
        recurrence_count=1,
        is_vulnerable=False,
        is_safety_risk=False,
    )

    assert score == 3
    assert priority == "P3"
    assert safety_override is False
