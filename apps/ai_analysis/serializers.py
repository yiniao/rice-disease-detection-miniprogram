from rest_framework import serializers

from .models import AdviceRecord


class AdviceRecordSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = AdviceRecord
        fields = ("status", "source", "source_display", "response_text", "raw_response", "updated_at")
