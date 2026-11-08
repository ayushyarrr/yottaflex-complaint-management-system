
"""
Shared deterministic lifecycle distributions.

Used by the workflow and lifecycle generators so that
assignment creation and final complaint statuses remain consistent.
"""

STARTER_STATUS_DISTRIBUTION = (
    ["ASSIGNED"] * 10
    + ["IN_PROGRESS"] * 10
    + ["PENDING_CUSTOMER"] * 6
    + ["RESOLVED"] * 8
    + ["CLOSED"] * 6
)

FULL_STATUS_COUNTS = {
    "NEW": 100,
    "ASSIGNED": 400,
    "IN_PROGRESS": 500,
    "PENDING_CUSTOMER": 300,
    "RESOLVED": 400,
    "CLOSED": 300,
}


def get_status_distribution(complaint_count):
    """
    Return a deterministic final-status list for a supported dataset.

    The list position corresponds to the complaint's sorted position.
    """

    if complaint_count == 40:
        return list(STARTER_STATUS_DISTRIBUTION)

    if complaint_count == 2000:
        distribution = []

        for status, count in FULL_STATUS_COUNTS.items():
            distribution.extend([status] * count)

        return distribution

    raise ValueError(
        f"Unsupported complaint count: {complaint_count}. "
        "Supported counts are 40 (starter) and 2000 (full)."
    )


def get_status_counts(complaint_count):
    """Return the expected status totals for a supported dataset."""

    distribution = get_status_distribution(complaint_count)

    return {
        status: distribution.count(status)
        for status in (
            "NEW",
            "ASSIGNED",
            "IN_PROGRESS",
            "PENDING_CUSTOMER",
            "RESOLVED",
            "CLOSED",
        )
    }
