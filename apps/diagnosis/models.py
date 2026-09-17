from django.conf import settings
from django.db import models


class DetectionRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "处理中"
        SUCCESS = "success", "成功"
        FAILED = "failed", "失败"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="detection_records")
    original_image = models.TextField(blank=True, default="")
    visualized_image = models.TextField(blank=True, default="")
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    model_name = models.CharField(max_length=100, blank=True)
    model_version = models.CharField(max_length=50, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    image_width = models.PositiveIntegerField(default=0)
    image_height = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="diag_record_created_idx"),
            models.Index(fields=["user", "-created_at"], name="diag_record_user_created_idx"),
            models.Index(fields=["status", "-created_at"], name="diag_record_status_created_idx"),
        ]


class DetectionResult(models.Model):
    record = models.ForeignKey(DetectionRecord, on_delete=models.CASCADE, related_name="results")
    label = models.CharField(max_length=100)
    confidence = models.FloatField()
    xmin = models.FloatField()
    ymin = models.FloatField()
    xmax = models.FloatField()
    ymax = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=["label"], name="diag_result_label_idx"),
            models.Index(fields=["record", "label"], name="diag_result_record_label_idx"),
        ]


class ModelConfig(models.Model):
    class Backend(models.TextChoices):
        MOCK = "mock", "Mock"
        ONNX = "onnx", "ONNX"
        ULTRALYTICS = "ultralytics", "Ultralytics"

    name = models.CharField(max_length=100)
    backend = models.CharField(max_length=32, choices=Backend.choices, default=Backend.MOCK)
    version = models.CharField(max_length=50, default="v1")
    weights_path = models.CharField(max_length=255, blank=True)
    class_names = models.JSONField(default=list, blank=True)
    confidence_threshold = models.FloatField(default=0.25)
    input_size = models.PositiveIntegerField(default=640)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            self.__class__.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)
