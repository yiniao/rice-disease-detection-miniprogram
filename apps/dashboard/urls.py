from django.urls import path

from .views import (
    DashboardHomeView,
    DashboardIndexView,
    DashboardLoginView,
    DashboardLogoutView,
    DashboardStatisticsView,
)


urlpatterns = [
    path("home/", DashboardHomeView.as_view(), name="dashboard-home"),
    path("login/", DashboardLoginView.as_view(), name="dashboard-login"),
    path("logout/", DashboardLogoutView.as_view(), name="dashboard-logout"),
    path("statistics/", DashboardStatisticsView.as_view(), name="dashboard-statistics"),
    path("", DashboardIndexView.as_view(), name="dashboard-index"),
]
