from django.db import models

from apps.diagnosis.models import DetectionRecord


class AdviceRecord(models.Model):
    class Source(models.TextChoices):
        DEEPSEEK = "deepseek", "DeepSeek"
        LOCAL_FALLBACK = "local-fallback", "本地兜底"

    class Status(models.TextChoices):
        SUCCESS = "success", "成功"
        FALLBACK = "fallback", "降级"
        FAILED = "failed", "失败"

    record = models.OneToOneField(DetectionRecord, on_delete=models.CASCADE, related_name="advice")
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.LOCAL_FALLBACK)
    prompt_excerpt = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.FALLBACK)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_analysis_advicerecord"
