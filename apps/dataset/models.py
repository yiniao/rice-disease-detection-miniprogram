from django.conf import settings
from django.db import models

from apps.diagnosis.models import DetectionRecord


class DatasetImage(models.Model):
    class Status(models.TextChoices):
        ARCHIVED = "archived", "已归档"
        SELECTED = "selected", "已选中"
        REJECTED = "rejected", "已剔除"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dataset_images")
    source_detection = models.ForeignKey(
        DetectionRecord,
        on_delete=models.SET_NULL,
        related_name="collected_dataset_images",
        null=True,
        blank=True,
    )
    image = models.TextField(blank=True, default="")
    image_filename = models.CharField(max_length=255, blank=True)
    category_label = models.CharField(max_length=100, blank=True)
    shot_at = models.DateTimeField(blank=True, null=True)
    location_text = models.CharField(max_length=255, blank=True)
    growth_stage = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ARCHIVED)
    is_in_training_set = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
