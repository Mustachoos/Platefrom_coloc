from django import forms


class UploadForm(forms.Form):
    username = forms.CharField(max_length=50)
