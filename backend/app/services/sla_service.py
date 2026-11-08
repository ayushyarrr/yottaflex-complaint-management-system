
from datetime import datetime, timezone


def normalize_datetime(value):
    """Convert a datetime to timezone-naive UTC for comparisons."""

    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def get_current_utc_time():
    """Return the current UTC time in SQLite-compatible format."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


def calculate_sla_breaches(sla_clock, now=None):
    """
    Calculate effective response and resolution SLA breaches.

    Response clock:
    - Uses first_response_at when a response exists.
    - Otherwise uses resolved_at if the complaint is resolved.
    - Otherwise checks against the current time.
    - Is never paused.

    Resolution clock:
    - Uses resolved_at when resolved.
    - Checks current time when unresolved and not paused.
    - Does not accumulate a live breach while paused.

    Previously recorded breaches are preserved.
    """

    if now is None:
        now = get_current_utc_time()
    else:
        now = normalize_datetime(now)

    response_deadline = normalize_datetime(
        sla_clock.response_deadline
    )

    resolution_deadline = normalize_datetime(
        sla_clock.resolution_deadline
    )

    first_response_at = normalize_datetime(
        sla_clock.first_response_at
    )

    resolved_at = normalize_datetime(
        sla_clock.resolved_at
    )

    paused_at = normalize_datetime(
        sla_clock.paused_at
    )

    # RESPONSE SLA
    response_breached = bool(sla_clock.response_breached)

    if first_response_at is not None:
        response_observation_time = first_response_at
    elif resolved_at is not None:
        response_observation_time = resolved_at
    else:
        response_observation_time = now

    if (
        response_deadline is not None
        and response_observation_time > response_deadline
    ):
        response_breached = True

    # RESOLUTION SLA
    resolution_breached = bool(sla_clock.resolution_breached)

    if resolved_at is not None:
        if (
            resolution_deadline is not None
            and resolved_at > resolution_deadline
        ):
            resolution_breached = True

    elif paused_at is None:
        if (
            resolution_deadline is not None
            and now > resolution_deadline
        ):
            resolution_breached = True

    return {
        "response_breached": response_breached,
        "resolution_breached": resolution_breached,
        "paused": paused_at is not None,
    }
