from django.contrib import admin

from .models import AdviceRecord


@admin.register(AdviceRecord)
class AdviceRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "record", "status", "source", "updated_at")
    list_filter = ("status", "source")
    search_fields = ("record__id", "response_text")
