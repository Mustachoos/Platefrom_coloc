from django import forms


class PseudoForm(forms.Form):
    pseudo = forms.CharField(max_length=50, label="Your name")


class ShareDriveForm(forms.Form):
    email = forms.EmailField(required=False, label="Your email")
