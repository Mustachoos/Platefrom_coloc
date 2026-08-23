from django import forms


class PseudoForm(forms.Form):
    pseudo = forms.CharField(
        max_length=50, label="Your name", widget=forms.TextInput(attrs={"class": "input"})
    )


class ShareDriveForm(forms.Form):
    email = forms.EmailField(
        required=False, label="Your email", widget=forms.EmailInput(attrs={"class": "input"})
    )
