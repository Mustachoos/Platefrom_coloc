from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.core.mail import EmailMultiAlternatives
from django.template import loader

from . import email_service


class StaffLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "input", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))


class StyledPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "input", "autofocus": True}))

    def send_mail(
        self, subject_template_name, email_template_name, context, from_email, to_email,
        html_email_template_name=None,
    ):
        # PasswordResetForm.save() has no hook to choose an email backend —
        # it always sends through settings.EMAIL_BACKEND. This mirrors
        # Django's own send_mail() exactly, only adding `connection` so the
        # Gmail account connected via OAuth2 (see gmail_service.py) is what
        # actually sends it, not the global (unconfigured) backend.
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        email_message = EmailMultiAlternatives(
            subject, body, from_email, [to_email], connection=email_service.build_backend(),
        )
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")
        email_message.send()


class StyledSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input", "autofocus": True}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))


class StyledPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input", "autofocus": True}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))


class PseudoForm(forms.Form):
    pseudo = forms.CharField(
        max_length=50, label="Your name", widget=forms.TextInput(attrs={"class": "input"})
    )


class ShareDriveForm(forms.Form):
    email = forms.EmailField(required=False, label="Your email")


class AdminAccountForm(forms.Form):
    username = forms.CharField(
        max_length=150, label="Admin username", widget=forms.TextInput(attrs={"class": "input"})
    )
    email = forms.EmailField(
        label="Email", widget=forms.EmailInput(attrs={"class": "input"}),
        help_text="Used for password reset if you forget it.",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "input"}), label="Password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "input"}), label="Confirm password"
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Passwords don't match.")
        return cleaned


class DriveClientSecretForm(forms.Form):
    client_secret_file = forms.FileField(
        label="Google OAuth credentials (JSON)",
        widget=forms.ClearableFileInput(attrs={"style": "display:none"}),
    )
