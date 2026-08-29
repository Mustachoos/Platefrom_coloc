"""Sends admin/subadmin password-reset (and test) emails via the Gmail
account connected through OAuth2 (see gmail_service.py) — not a fixed env
var, since this app also ships as a standalone .exe where end users can't
set environment variables, so admin-UI configuration is the only option
that works in every deployment mode."""

from django.core.mail import EmailMessage

from . import gmail_service


def build_backend():
    return gmail_service.GmailApiBackend()


def send_test_email(to_address):
    EmailMessage(
        subject="PartyBooth test email",
        body="If you're reading this, the recovery email is configured correctly.",
        to=[to_address],
        connection=build_backend(),
    ).send()
