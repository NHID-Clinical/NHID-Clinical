"""
Minimal Twilio SMS sender for the website demo features (used by the inbound
demo line's end-of-demo "text me the starter pack link" option).

This is infrastructure for the demo website feature, NOT the NHID-Clinical
governance framework itself. httpx is provided by the Lambda runtime.

Sending is gated on three env vars being present (sms_enabled()); when they
are not configured the demo line simply doesn't offer the SMS option, so the
code is safe to ship before A2P 10DLC registration / credentials are in place.
"""

from __future__ import annotations

import os

ACCOUNT_SID_ENV = "TWILIO_ACCOUNT_SID"
AUTH_TOKEN_ENV = "TWILIO_AUTH_TOKEN"
SMS_FROM_ENV = "TWILIO_SMS_FROM"


def sms_enabled() -> bool:
    """True only when account SID, auth token, and a sending number are all set."""
    return all(os.environ.get(k) for k in (ACCOUNT_SID_ENV, AUTH_TOKEN_ENV, SMS_FROM_ENV))


def send_sms(
    to_number: str,
    body: str,
    *,
    account_sid: str | None = None,
    auth_token: str | None = None,
    from_number: str | None = None,
) -> bool:
    """Send one SMS via the Twilio REST API. Returns True on a 2xx response.

    Credentials default to the env vars above; pass them explicitly in tests.
    Returns False (never raises for config gaps) when any required value is
    missing, so callers can treat it as a best-effort, fire-and-forget send.
    """
    account_sid = account_sid or os.environ.get(ACCOUNT_SID_ENV, "")
    auth_token = auth_token or os.environ.get(AUTH_TOKEN_ENV, "")
    from_number = from_number or os.environ.get(SMS_FROM_ENV, "")
    if not (account_sid and auth_token and from_number and to_number):
        return False

    import httpx  # local import: only required for an actual send in the Lambda runtime

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    resp = httpx.post(
        url,
        data={"To": to_number, "From": from_number, "Body": body},
        auth=(account_sid, auth_token),
        timeout=10.0,
    )
    return 200 <= resp.status_code < 300
