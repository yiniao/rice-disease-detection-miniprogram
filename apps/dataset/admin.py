from django.contrib import admin

from .models import DatasetImage


@admin.register(DatasetImage)
class DatasetImageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source_detection", "growth_stage", "status", "is_in_training_set", "created_at")
    list_filter = ("status", "growth_stage", "is_in_training_set")
    search_fields = ("user__username", "location_text", "note")
