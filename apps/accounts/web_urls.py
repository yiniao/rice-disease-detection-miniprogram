from django.urls import path

from .views import WebLoginView, WebLogoutView, WebRegisterView


urlpatterns = [
    path("login/", WebLoginView.as_view(), name="web-login"),
    path("register/", WebRegisterView.as_view(), name="web-register"),
    path("logout/", WebLogoutView.as_view(), name="web-logout"),
]
