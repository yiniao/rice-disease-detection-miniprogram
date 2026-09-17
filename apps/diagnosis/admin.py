from django.contrib import admin

from apps.ai_analysis.models import AdviceRecord

from .models import DetectionRecord, DetectionResult, ModelConfig


class DetectionResultInline(admin.TabularInline):
    model = DetectionResult
    extra = 0


class AdviceRecordInline(admin.StackedInline):
    model = AdviceRecord
    extra = 0


@admin.register(DetectionRecord)
class DetectionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "model_name", "model_version", "created_at")
    list_filter = ("status", "model_name", "model_version")
    search_fields = ("user__username", "error_message")
    inlines = [DetectionResultInline, AdviceRecordInline]


@admin.register(ModelConfig)
class ModelConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "backend", "version", "is_active", "updated_at")
    list_filter = ("backend", "is_active")
    search_fields = ("name", "version")
