from django.urls import path

from .api_views import StatisticsExportView, StatisticsView


urlpatterns = [
    path("statistics/", StatisticsView.as_view(), name="statistics"),
    path("statistics/export/", StatisticsExportView.as_view(), name="statistics-export"),
]
