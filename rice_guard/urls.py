from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


def healthcheck(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz/", healthcheck),
    path("django-admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.diagnosis.urls")),
    path("api/", include("apps.dataset.urls")),
    path("api/", include("apps.dashboard.user_api_urls")),
    path("api/admin/", include("apps.dashboard.api_urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]

if settings.ENABLE_WEB_FRONTEND:
    urlpatterns = [
        path("", include("apps.web_portal.urls")),
        path("accounts/", include("apps.accounts.web_urls")),
    ] + urlpatterns
else:
    urlpatterns = [
        path("", healthcheck),
    ] + urlpatterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
