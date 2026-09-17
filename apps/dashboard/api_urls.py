from django.urls import path

from .api_views import (
    AdminDatasetListView,
    AdminDatasetUpdateView,
    AdminDetectionListView,
    AdminModelActivateView,
    AdminModelConfigListView,
    AdminStatisticsExportView,
    AdminStatisticsView,
    AdminUserListView,
)


urlpatterns = [
    path("detections/", AdminDetectionListView.as_view(), name="admin-detections"),
    path("dataset-images/", AdminDatasetListView.as_view(), name="admin-dataset-images"),
    path("dataset-images/<int:pk>/", AdminDatasetUpdateView.as_view(), name="admin-dataset-update"),
    path("model-configs/", AdminModelConfigListView.as_view(), name="admin-model-configs"),
    path("model-configs/<int:pk>/activate/", AdminModelActivateView.as_view(), name="admin-model-activate"),
    path("statistics/", AdminStatisticsView.as_view(), name="admin-statistics"),
    path("statistics/export/", AdminStatisticsExportView.as_view(), name="admin-statistics-export"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
]
