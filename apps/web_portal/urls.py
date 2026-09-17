from django.urls import path

from .views import (
    WebDashboardView,
    WebDatasetDeleteView,
    WebDatasetListView,
    WebDetectionDetailView,
    WebDetectionListView,
    WebHomeView,
    WebStatisticsView,
)


urlpatterns = [
    path("", WebHomeView.as_view(), name="web-home"),
    path("web/", WebDashboardView.as_view(), name="web-dashboard"),
    path("web/detections/", WebDetectionListView.as_view(), name="web-detections"),
    path("web/detections/<int:pk>/", WebDetectionDetailView.as_view(), name="web-detection-detail"),
    path("web/dataset/", WebDatasetListView.as_view(), name="web-dataset"),
    path("web/dataset/<int:pk>/delete/", WebDatasetDeleteView.as_view(), name="web-dataset-delete"),
    path("web/statistics/", WebStatisticsView.as_view(), name="web-statistics"),
]
