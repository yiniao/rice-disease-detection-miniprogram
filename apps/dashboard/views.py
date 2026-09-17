from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView


class AdminRoleRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_role_admin


class DashboardLoginView(LoginView):
    template_name = "dashboard/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard-index")


class DashboardLogoutView(LogoutView):
    pass


class DashboardHomeView(TemplateView):
    template_name = "dashboard/home.html"


class DashboardIndexView(LoginRequiredMixin, AdminRoleRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"
    login_url = "/dashboard/login/"


class DashboardStatisticsView(LoginRequiredMixin, AdminRoleRequiredMixin, TemplateView):
    template_name = "dashboard/statistics.html"
    login_url = "/dashboard/login/"
