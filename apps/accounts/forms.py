from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class WebUserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "nickname", "avatar_url")


class WebLoginForm(forms.Form):
    username = forms.CharField(label="用户名")
    password = forms.CharField(label="密码", widget=forms.PasswordInput)

