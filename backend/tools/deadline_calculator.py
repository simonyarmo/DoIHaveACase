"""Security-deposit return deadline calculator — pure date logic, no external calls.

Statutory deposit-return windows (days after the landlord's obligation to
return the deposit begins):
  - TX Prop. Code § 92.103/92.107: 30 days, conditioned on the tenant
    surrendering the premises *and* providing a forwarding address.
  - CA Civ. Code § 1950.5: 21 days after the tenant vacates.
  - FL Stat. § 83.49: 15 days (no claim) / 30 days (itemized claim) after
    the tenant vacates — 15 is used here as the floor.
"""

from datetime import date, timedelta

STATE_RETURN_DEADLINE_DAYS = {
    "TX": 30,
    "CA": 21,
    "FL": 15,
}


def calculate_deadline(
    state: str,
    move_out_date: date | None,
    keys_returned_date: date | None = None,
    forwarding_address_provided_date: date | None = None,
) -> dict:
    """Return `{deadline_date, days_overdue, violation_confirmed}` for `state`.

    The clock starts on the latest of move-out, keys-returned, and
    forwarding-address-provided dates — the landlord's obligation to return
    the deposit doesn't begin until possession is fully surrendered and (for
    states like TX) a forwarding address has been provided.

    Returns all-`None` values if `state` isn't a recognized state or
    `move_out_date` is missing — there isn't enough information yet.
    """
    deadline_days = STATE_RETURN_DEADLINE_DAYS.get(state.upper()) if state else None
    if deadline_days is None or move_out_date is None:
        return {"deadline_date": None, "days_overdue": None, "violation_confirmed": None}

    baseline = max(d for d in (move_out_date, keys_returned_date, forwarding_address_provided_date) if d is not None)
    deadline_date = baseline + timedelta(days=deadline_days)

    days_overdue = (date.today() - deadline_date).days
    return {
        "deadline_date": deadline_date,
        "days_overdue": max(days_overdue, 0),
        "violation_confirmed": days_overdue > 0,
    }
