from django import forms


class PseudoForm(forms.Form):
    pseudo = forms.CharField(max_length=50, label="Your name")


class ShareDriveForm(forms.Form):
    email = forms.EmailField(required=False, label="Your email")


class AdminAccountForm(forms.Form):
    username = forms.CharField(max_length=150, label="Admin username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Passwords don't match.")
        return cleaned


class DriveClientSecretForm(forms.Form):
    client_secret_file = forms.FileField(label="Google OAuth credentials (JSON)")


class NetworkForm(forms.Form):
    server_host = forms.CharField(max_length=255, label="Server address")


class FirstEventForm(forms.Form):
    name = forms.CharField(max_length=200, label="Event name")
