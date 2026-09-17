from django.urls import path

from .views import (
    DetectionDetailView,
    DetectionListCreateView,
    DetectionOriginalImageView,
    DetectionVisualizedImageView,
)


urlpatterns = [
    path("detections/", DetectionListCreateView.as_view(), name="detections"),
    path("detections/<int:pk>/", DetectionDetailView.as_view(), name="detection-detail"),
    path("detections/<int:pk>/original-image/", DetectionOriginalImageView.as_view(), name="detection-original-image"),
    path("detections/<int:pk>/visualized-image/", DetectionVisualizedImageView.as_view(), name="detection-visualized-image"),
]
