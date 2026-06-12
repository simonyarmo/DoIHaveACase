"""USPS address verification for the landlord's service address.

Calls the USPS Web Tools XML `Verify` API. Any failure (missing/invalid
API key, network error, unexpected response, or an address we can't parse
into street/city/state/zip) returns a `deliverable: None` result with an
`error` message rather than raising — this is informational for the agent,
not a blocker.
"""

import logging
import re
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import httpx

from config import settings

logger = logging.getLogger(__name__)

_VERIFY_URL = "https://secure.shippingapis.com/ShippingAPI.dll"
_PO_BOX_RE = re.compile(r"\bP\.?\s*O\.?\s*BOX\b", re.IGNORECASE)


def _parse_address(address: str) -> dict | None:
    """Split a single-line `"street, city, state zip"` address into parts.

    Returns `None` if the address doesn't have enough comma-separated parts
    or the last part isn't `"STATE ZIP"`.
    """
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) < 3:
        return None
    state_zip = parts[-1].split()
    if len(state_zip) < 2:
        return None
    return {"street": parts[0], "city": parts[1], "state": state_zip[0], "zip5": state_zip[1][:5]}


def _build_request_xml(parsed: dict) -> str:
    return (
        f'<AddressValidateRequest USERID="{escape(settings.usps_api_key)}">'
        '<Address ID="0">'
        "<Address1></Address1>"
        f"<Address2>{escape(parsed['street'])}</Address2>"
        f"<City>{escape(parsed['city'])}</City>"
        f"<State>{escape(parsed['state'])}</State>"
        f"<Zip5>{escape(parsed['zip5'])}</Zip5>"
        "<Zip4></Zip4>"
        "</Address>"
        "</AddressValidateRequest>"
    )


async def validate_address(address: str) -> dict:
    """Verify `address` against the USPS database.

    Returns `{"deliverable": bool | None, "standardized": str | None,
    "is_po_box": bool, "error": str | None}`.
    """
    is_po_box = bool(_PO_BOX_RE.search(address))
    parsed = _parse_address(address)
    if parsed is None:
        return {"deliverable": None, "standardized": None, "is_po_box": is_po_box, "error": "Could not parse address into street/city/state/zip."}
    if not settings.usps_api_key:
        return {"deliverable": None, "standardized": None, "is_po_box": is_po_box, "error": "USPS API key is not configured."}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.get(_VERIFY_URL, params={"API": "Verify", "XML": _build_request_xml(parsed)})
            response.raise_for_status()
            root = ElementTree.fromstring(response.text)
    except (httpx.HTTPError, ElementTree.ParseError):
        logger.exception("USPS address validation failed for %r", address)
        return {"deliverable": None, "standardized": None, "is_po_box": is_po_box, "error": "USPS address validation is currently unavailable."}

    if root.tag == "Error":
        # API-level error (bad/unconfigured credentials, service outage) — not a
        # statement about the address itself.
        description = root.findtext("Description") or "USPS address validation is currently unavailable."
        return {"deliverable": None, "standardized": None, "is_po_box": is_po_box, "error": description}

    address_el = root.find("Address")
    address_error = address_el.find("Error") if address_el is not None else None
    if address_error is not None:
        # Address-level error (e.g. "Invalid City/State/ZIP") — the address itself
        # didn't validate.
        description = address_error.findtext("Description") or "Address could not be verified."
        return {"deliverable": False, "standardized": None, "is_po_box": is_po_box, "error": description}

    if address_el is None:
        return {"deliverable": None, "standardized": None, "is_po_box": is_po_box, "error": "Unexpected USPS response."}

    zip5, zip4 = address_el.findtext("Zip5"), address_el.findtext("Zip4")
    zip_combined = f"{zip5}-{zip4}" if zip5 and zip4 else zip5
    standardized = ", ".join(
        part
        for part in [
            address_el.findtext("Address2"),
            address_el.findtext("City"),
            address_el.findtext("State"),
            zip_combined,
        ]
        if part
    )
    return {"deliverable": True, "standardized": standardized, "is_po_box": is_po_box, "error": None}
