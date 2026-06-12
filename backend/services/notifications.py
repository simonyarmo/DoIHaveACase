import logging

from config import settings

logger = logging.getLogger(__name__)


def send_admin_sms(message: str) -> bool:
    """Send an SMS to the admin phone number via Twilio.

    Stub for Phase 6, which builds out the full notification service. If
    Twilio credentials or an admin phone number aren't configured, logs the
    message instead of sending. Used by the ingestion pipeline's human
    review flag (Phase 2).

    Returns True if an SMS was sent, False if it was only logged.
    """
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_phone_number
        and settings.admin_phone_number
    ):
        logger.info("Admin SMS (not sent — Twilio not configured): %s", message)
        return False

    from twilio.base.exceptions import TwilioRestException
    from twilio.rest import Client

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(body=message, from_=settings.twilio_phone_number, to=settings.admin_phone_number)
    except TwilioRestException:
        logger.exception("Failed to send admin SMS: %s", message)
        return False
    return True
