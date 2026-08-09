from django import forms


class PseudoForm(forms.Form):
    pseudo = forms.CharField(max_length=50, label="Your name")
