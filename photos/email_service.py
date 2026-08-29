"""Sends admin password-reset (and test) emails via Gmail SMTP, using
credentials configured through the admin UI (SiteSettings) rather than a
fixed env var — this app also ships as a standalone .exe where end users
can't set environment variables, so admin-UI configuration is the only
option that works in every deployment mode."""

from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend

from .models import SiteSettings


def _credentials():
    settings = SiteSettings.get_solo()
    return settings.support_email, settings.support_email_app_password


def build_backend():
    email, app_password = _credentials()
    return EmailBackend(host="smtp.gmail.com", port=587, username=email, password=app_password, use_tls=True)


def send_test_email(to_address):
    email, _ = _credentials()
    EmailMessage(
        subject="PartyBooth test email",
        body="If you're reading this, the support email is configured correctly.",
        from_email=email,
        to=[to_address],
        connection=build_backend(),
    ).send()


def send_verification_email(to_address, verify_url):
    email, _ = _credentials()
    EmailMessage(
        subject="Verify your PartyBooth recovery email",
        body=(
            "Someone just set this address as the recovery email for password resets on your "
            "PartyBooth admin account. Click the link below to confirm it works:\n\n"
            f"{verify_url}\n\n"
            "If you didn't request this, you can ignore this email."
        ),
        from_email=email,
        to=[to_address],
        connection=build_backend(),
    ).send()
