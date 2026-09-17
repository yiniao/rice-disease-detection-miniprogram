from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers

from apps.common.file_names import derive_visualized_filename, sanitize_filename
from apps.common.category_labels import build_category_record_code, to_chinese_category_label
from apps.common.image_utils import (
    decode_image_to_jpeg_bytes,
    encode_bytes_to_data_url,
    image_bytes_to_data_url,
    fetch_remote_image_bytes,
    image_byte_size,
)
from apps.ai_analysis.serializers import AdviceRecordSerializer

from .models import DetectionRecord, DetectionResult, ModelConfig


class DetectionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionResult
        fields = ("id", "label", "confidence", "xmin", "ymin", "xmax", "ymax")


class FlexibleImageField(serializers.Field):
    def to_internal_value(self, data):
        if hasattr(data, "read"):
            return data

        if isinstance(data, (bytes, bytearray)):
            raw_bytes = bytes(data)
        elif isinstance(data, str):
            value = data.strip()
            try:
                if value.startswith(("http://", "https://")):
                    raw_bytes = fetch_remote_image_bytes(value)
                else:
                    raw_bytes = decode_image_to_jpeg_bytes(value)
            except ValueError as exc:
                raise serializers.ValidationError("无法解析图片内容。") from exc
        else:
            raise serializers.ValidationError("无法解析图片内容。")

        if not raw_bytes:
            raise serializers.ValidationError("无法解析图片内容。")

        return SimpleUploadedFile("upload.jpg", raw_bytes, content_type="image/jpeg")


class DetectionRecordSerializer(serializers.ModelSerializer):
    record_code = serializers.SerializerMethodField()
    primary_category = serializers.SerializerMethodField()
    category_options = serializers.SerializerMethodField()
    results = DetectionResultSerializer(many=True, read_only=True)
    advice = AdviceRecordSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    original_image_url = serializers.SerializerMethodField()
    original_image_name = serializers.SerializerMethodField()
    visualized_image_name = serializers.SerializerMethodField()
    preview_image_name = serializers.SerializerMethodField()
    original_image_path = serializers.SerializerMethodField()
    original_image_size = serializers.SerializerMethodField()
    visualized_image_url = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()

    class Meta:
        model = DetectionRecord
        fields = (
            "id",
            "record_code",
            "status",
            "status_display",
            "model_name",
            "model_version",
            "duration_ms",
            "image_width",
            "image_height",
            "error_message",
            "created_at",
            "original_image_url",
            "original_image_name",
            "visualized_image_name",
            "preview_image_name",
            "original_image_path",
            "original_image_size",
            "visualized_image_url",
            "preview_image_url",
            "primary_category",
            "category_options",
            "results",
            "advice",
        )

    def get_record_code(self, obj):
        return build_category_record_code(self.get_primary_category(obj), obj.pk)

    def get_primary_category(self, obj):
        options = self.get_category_options(obj)
        return options[0] if options else "未标注"

    def get_category_options(self, obj):
        results = list(getattr(obj, "results").all()) if hasattr(obj, "results") else []
        labels = []
        seen = set()
        for item in sorted(results, key=lambda value: (-value.confidence, value.id)):
            label = to_chinese_category_label(item.label)
            if label and label not in seen:
                seen.add(label)
                labels.append(label)
        return labels

    def get_original_image_url(self, obj):
        if not obj.original_image:
            return ""
        if self.context.get("image_variant") == "detail":
            return self.get_original_image_path(obj)
        return self._render_image(obj.original_image, thumb=(self.context.get("image_variant") == "thumb"))

    def get_original_image_name(self, obj):
        return sanitize_filename(obj.original_filename, default=f"detection-{obj.pk}-original.jpg") if obj.original_image else ""

    def get_visualized_image_name(self, obj):
        if not obj.visualized_image:
            return ""
        return derive_visualized_filename(self.get_original_image_name(obj))

    def get_preview_image_name(self, obj):
        return self.get_visualized_image_name(obj) or self.get_original_image_name(obj)

    def get_original_image_path(self, obj):
        return f"/api/detections/{obj.pk}/original-image/" if obj.original_image else ""

    def get_original_image_size(self, obj):
        return image_byte_size(obj.original_image) if obj.original_image else 0

    def get_visualized_image_url(self, obj):
        if not obj.visualized_image:
            return ""
        if self.context.get("image_variant") == "detail":
            return f"/api/detections/{obj.pk}/visualized-image/"
        return self._render_image(obj.visualized_image, thumb=(self.context.get("image_variant") == "thumb"))

    def get_preview_image_url(self, obj):
        return self.get_visualized_image_url(obj) or self.get_original_image_url(obj)

    def _render_image(self, value, *, thumb=False):
        content = decode_image_to_jpeg_bytes(value)
        if thumb:
            return image_bytes_to_data_url(content, max_size=(240, 240), quality=70)
        return encode_bytes_to_data_url(content)


class DetectionRecordListSerializer(serializers.ModelSerializer):
    record_code = serializers.SerializerMethodField()
    primary_category = serializers.SerializerMethodField()
    category_options = serializers.SerializerMethodField()
    results_count = serializers.SerializerMethodField()
    advice_source_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    original_image_name = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    original_image_url = serializers.SerializerMethodField()
    original_image_path = serializers.SerializerMethodField()
    visualized_image_path = serializers.SerializerMethodField()
    preview_image_path = serializers.SerializerMethodField()
    is_collected = serializers.SerializerMethodField()
    dataset_image_id = serializers.SerializerMethodField()
    dataset_record_code = serializers.SerializerMethodField()
    archived_category_label = serializers.SerializerMethodField()

    class Meta:
        model = DetectionRecord
        fields = (
            "id",
            "record_code",
            "status",
            "status_display",
            "model_name",
            "model_version",
            "duration_ms",
            "image_width",
            "image_height",
            "created_at",
            "original_image_name",
            "original_image_url",
            "preview_image_url",
            "original_image_path",
            "visualized_image_path",
            "preview_image_path",
            "primary_category",
            "category_options",
            "results_count",
            "advice_source_display",
            "is_collected",
            "dataset_image_id",
            "dataset_record_code",
            "archived_category_label",
        )

    def get_record_code(self, obj):
        return DetectionRecordSerializer.get_record_code(self, obj)

    def get_primary_category(self, obj):
        return DetectionRecordSerializer.get_primary_category(self, obj)

    def get_category_options(self, obj):
        return DetectionRecordSerializer.get_category_options(self, obj)

    def get_advice_source_display(self, obj):
        advice = getattr(obj, "advice", None)
        return advice.get_source_display() if advice else ""

    def get_results_count(self, obj):
        results = getattr(obj, "results", None)
        if results is None:
            return 0
        if hasattr(results, "all"):
            return results.count()
        return len(results)

    def get_original_image_name(self, obj):
        return sanitize_filename(
            obj.original_filename,
            default=f"detection-{obj.pk}-original.jpg",
        ) if obj.original_image else ""

    def get_original_image_path(self, obj):
        return f"/api/detections/{obj.pk}/original-image/" if obj.original_image else ""

    def get_visualized_image_path(self, obj):
        return f"/api/detections/{obj.pk}/visualized-image/" if obj.visualized_image else ""

    def get_preview_image_path(self, obj):
        return self.get_visualized_image_path(obj) or self.get_original_image_path(obj)

    def get_preview_image_url(self, obj):
        if not obj.visualized_image and not obj.original_image:
            return ""
        source = obj.visualized_image or obj.original_image
        return image_bytes_to_data_url(
            decode_image_to_jpeg_bytes(source),
            max_size=(240, 240),
            quality=70,
        )

    def get_original_image_url(self, obj):
        if not obj.original_image:
            return ""
        return image_bytes_to_data_url(
            decode_image_to_jpeg_bytes(obj.original_image),
            max_size=(240, 240),
            quality=70,
        )

    def _dataset_item(self, obj):
        items = getattr(obj, "current_user_dataset_images", [])
        return items[0] if items else None

    def get_is_collected(self, obj):
        return self._dataset_item(obj) is not None

    def get_dataset_image_id(self, obj):
        item = self._dataset_item(obj)
        return item.id if item else None

    def get_dataset_record_code(self, obj):
        item = self._dataset_item(obj)
        return build_category_record_code(item.category_label, item.id) if item else ""

    def get_archived_category_label(self, obj):
        item = self._dataset_item(obj)
        return to_chinese_category_label(item.category_label) if item else ""


class DetectionCreateSerializer(serializers.Serializer):
    image = FlexibleImageField()
    image_name = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ModelConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelConfig
        fields = (
            "id",
            "name",
            "backend",
            "version",
            "weights_path",
            "class_names",
            "confidence_threshold",
            "input_size",
            "is_active",
            "updated_at",
        )
