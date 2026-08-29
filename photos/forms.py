from django import forms
from django.contrib.auth.forms import AuthenticationForm


class StaffLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "input", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))


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
    client_secret_file = forms.FileField(label="Google OAuth credentials (JSON)")
