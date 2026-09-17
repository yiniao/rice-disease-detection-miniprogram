from django.urls import path

from .views import AccountLoginView, AccountMeView, AccountRegisterView


urlpatterns = [
    path("login/", AccountLoginView.as_view(), name="account-login"),
    path("register/", AccountRegisterView.as_view(), name="account-register"),
    path("me/", AccountMeView.as_view(), name="account-me"),
]
