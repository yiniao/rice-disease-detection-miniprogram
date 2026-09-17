from django import forms


class WebDetectionUploadForm(forms.Form):
    image = forms.FileField(
        label="检测图片",
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )
