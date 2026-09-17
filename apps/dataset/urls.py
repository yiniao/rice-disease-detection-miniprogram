from django.urls import path

from .views import DatasetCollectionToggleView, DatasetImageDestroyView, DatasetImageFileView, DatasetImageListCreateView


urlpatterns = [
    path("dataset-images/", DatasetImageListCreateView.as_view(), name="dataset-images"),
    path("dataset-images/<int:pk>/", DatasetImageDestroyView.as_view(), name="dataset-image-detail"),
    path("dataset-images/<int:pk>/image/", DatasetImageFileView.as_view(), name="dataset-image-file"),
    path("dataset-toggle/<int:detection_id>/", DatasetCollectionToggleView.as_view(), name="dataset-toggle"),
]
