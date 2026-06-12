"""Secretary-of-State / business-entity verification for the landlord named
during intake.

`lookup_entity` is best-effort: a real automated lookup is only implemented
for Texas (via the Texas Comptroller's public franchise-tax data-search API,
which mirrors the SOS registration status, registered agent, and registered
office address — the same data the Texas SOS "Account Status" search
surfaces). Every other state, and any TX lookup that fails or doesn't find an
exact match, returns `verified: False` with a `manual_verification` block so
the user can check the landlord's entity status themselves without blocking
the intake flow.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

_TX_SEARCH_URL = "https://comptroller.texas.gov/data-search/franchise-tax"
_TX_DETAIL_URL = "https://comptroller.texas.gov/data-search/franchise-tax/{taxpayer_id}"
_TX_PORTAL_URL = "https://comptroller.texas.gov/taxes/franchise/account-status/search/"

# Official state business-entity search portals, used to build manual-lookup
# instructions when an automated lookup isn't available or doesn't find a match.
SOS_PORTALS: dict[str, dict[str, str]] = {
    "TX": {
        "portal_name": "Texas Comptroller — Franchise Tax Account Status Search",
        "url": _TX_PORTAL_URL,
        "instructions": (
            "1. Open the search page and enter the landlord's name in the 'Entity Name' field.\n"
            "2. Click the matching result to open its account status page.\n"
            "3. Note the 'SOS Registration Status', 'Registered Agent Name', and "
            "'Registered Office Address' fields — enter these as the landlord's "
            "legal name, registered agent, and service address."
        ),
    },
    "CA": {
        "portal_name": "California Secretary of State — Business Search (bizfileonline)",
        "url": "https://bizfileonline.sos.ca.gov/search/business",
        "instructions": (
            "1. Enter the landlord's name in the business search box.\n"
            "2. Open the matching entity record.\n"
            "3. Note the registered 'Entity Name', 'Agent for Service of Process', "
            "and registered agent address — enter these as the landlord's legal "
            "name, registered agent, and service address."
        ),
    },
    "FL": {
        "portal_name": "Florida Division of Corporations — Sunbiz",
        "url": "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName",
        "instructions": (
            "1. Enter the landlord's name and search by entity name.\n"
            "2. Open the matching entity's detail page.\n"
            "3. Note the 'Registered Agent Name & Address' and entity status — "
            "enter these as the landlord's registered agent, service address, "
            "and verification status."
        ),
    },
}

_GENERIC_PORTAL = {
    "portal_name": "{state} Secretary of State — business entity search",
    "url": None,
    "instructions": (
        "Search '{state} Secretary of State business entity search' to find the "
        "official portal, then look up the landlord's name. Note the registered "
        "legal name, registered agent, and registered agent address — enter these "
        "as the landlord's legal name, registered agent, and service address."
    ),
}


def _manual_verification(state: str, why: str, candidates: list[str] | None = None) -> dict:
    portal = SOS_PORTALS.get(state.upper())
    if portal is None:
        portal = {
            "portal_name": _GENERIC_PORTAL["portal_name"].format(state=state.upper()),
            "url": _GENERIC_PORTAL["url"],
            "instructions": _GENERIC_PORTAL["instructions"].format(state=state.upper()),
        }
    manual = {**portal, "why": why}
    if candidates:
        manual["candidates"] = candidates
    return manual


def _unverified(state: str, reason: str, why: str, candidates: list[str] | None = None) -> dict:
    return {
        "verified": False,
        "status": reason,
        "manual_verification": _manual_verification(state, why, candidates),
    }


async def _lookup_tx(entity_name: str) -> dict | None:
    """Look up `entity_name` in the TX Comptroller franchise-tax data-search.

    Returns a verified result dict, an unverified result dict (no/ambiguous
    match), or `None` if the lookup itself failed (network/timeout/unexpected
    response) so the caller can fall back to a generic "lookup failed" message.
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
            search = await client.get(_TX_SEARCH_URL, params={"name": entity_name}, headers={"Accept": "application/json"})
            search.raise_for_status()
            payload = search.json()

            if not payload.get("success"):
                return _unverified("TX", "lookup_query_too_broad", payload.get("error", "Search query was rejected."))

            results = payload.get("data") or []
            if not results:
                return _unverified("TX", "no_match_found", f"No entity named '{entity_name}' was found in the TX Comptroller search.")

            exact = [r for r in results if r.get("name", "").strip().lower() == entity_name.strip().lower()]
            match = exact[0] if exact else (results[0] if len(results) == 1 else None)
            if match is None:
                return _unverified(
                    "TX",
                    "multiple_matches_found",
                    f"Multiple entities match '{entity_name}' and none match exactly — pick the right one manually.",
                    candidates=[r.get("name", "") for r in results[:10]],
                )

            detail = await client.get(
                _TX_DETAIL_URL.format(taxpayer_id=match["taxpayerId"]), headers={"Accept": "application/json"}
            )
            detail.raise_for_status()
            data = detail.json().get("data") or {}

            address_parts = [
                data.get("registeredOfficeAddressStreet") or data.get("mailingAddressStreet"),
                data.get("registeredOfficeAddressCity") or data.get("mailingAddressCity"),
                data.get("registeredOfficeAddressState") or data.get("mailingAddressState"),
                data.get("registeredOfficeAddressZip") or data.get("mailingAddressZip"),
            ]

            return {
                "verified": True,
                "status": data.get("sosRegistrationStatus") or data.get("rightToTransactTX") or "unknown",
                "legal_name": data.get("name", match["name"]),
                "registered_agent": data.get("registeredAgentName"),
                "address": ", ".join(p for p in address_parts if p),
                "source": "tx_comptroller_franchise_tax",
                "source_url": _TX_DETAIL_URL.format(taxpayer_id=match["taxpayerId"]),
            }
    except (httpx.HTTPError, ValueError, KeyError):
        logger.exception("TX Comptroller SOS lookup failed for %r", entity_name)
        return None


async def lookup_entity(state: str, entity_name: str) -> dict:
    """Verify `entity_name` (the landlord) against `state`'s business registry.

    Always returns a dict with at least `verified: bool` and `status: str`;
    never raises. When `verified` is `False`, includes `manual_verification`
    with instructions for the user to check the landlord's status themselves.
    """
    state = state.upper()
    if state == "TX":
        result = await _lookup_tx(entity_name)
        if result is not None:
            return result
        return _unverified("TX", "lookup_failed", "The TX Comptroller search is temporarily unavailable.")

    return _unverified(
        state,
        "no_automated_lookup_for_state",
        f"DepositShield does not yet have an automated business-registry lookup for {state}.",
    )
