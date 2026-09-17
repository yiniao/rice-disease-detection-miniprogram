from rest_framework import serializers

from apps.common.file_names import sanitize_filename
from apps.common.category_labels import build_category_record_code, to_chinese_category_label
from apps.common.image_utils import decode_image_to_jpeg_bytes, encode_bytes_to_data_url, image_bytes_to_data_url
from apps.diagnosis.models import DetectionRecord

from .models import DatasetImage
from .services import create_dataset_from_detection


class DatasetImageSerializer(serializers.ModelSerializer):
    record_code = serializers.SerializerMethodField()
    source_detection_code = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    image_name = serializers.SerializerMethodField()
    image_path = serializers.SerializerMethodField()
    source_detection_id = serializers.SerializerMethodField()
    source_detection_preview_url = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DatasetImage
        fields = (
            "id",
            "record_code",
            "source_detection_code",
            "image_url",
            "image_name",
            "image_path",
            "source_detection_id",
            "source_detection_preview_url",
            "category_label",
            "shot_at",
            "location_text",
            "growth_stage",
            "note",
            "status",
            "status_display",
            "is_in_training_set",
            "created_at",
        )
        read_only_fields = ("status", "is_in_training_set", "created_at")

    def get_record_code(self, obj):
        source_code = self.get_source_detection_code(obj)
        if source_code:
            return source_code
        return build_category_record_code(obj.category_label, obj.pk)

    def get_source_detection_code(self, obj):
        if not obj.source_detection_id or not obj.source_detection:
            return ""
        results = list(obj.source_detection.results.all())
        category_label = max(results, key=lambda item: (item.confidence, -item.id)).label if results else ""
        return build_category_record_code(category_label, obj.source_detection_id)

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        return self._render_image(obj.image, thumb=(self.context.get("image_variant") == "thumb"))

    def get_image_name(self, obj):
        if not obj.image:
            return ""
        fallback = obj.source_detection.original_filename if obj.source_detection else f"detection-{obj.pk}-original.jpg"
        return sanitize_filename(obj.image_filename or fallback, default=fallback)

    def get_image_path(self, obj):
        return f"dataset/{obj.pk}.jpg" if obj.image else ""

    def get_source_detection_id(self, obj):
        return obj.source_detection_id

    def get_source_detection_preview_url(self, obj):
        if not obj.source_detection:
            return ""
        return self._render_image(
            obj.source_detection.original_image,
            thumb=(self.context.get("image_variant") == "thumb")
        )

    def _render_image(self, value, *, thumb=False):
        content = decode_image_to_jpeg_bytes(value)
        if thumb:
            return image_bytes_to_data_url(content, max_size=(240, 240), quality=70)
        return encode_bytes_to_data_url(content)


class DatasetImageListSerializer(serializers.ModelSerializer):
    record_code = serializers.SerializerMethodField()
    source_detection_code = serializers.SerializerMethodField()
    source_detection_id = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DatasetImage
        fields = (
            "id",
            "record_code",
            "source_detection_code",
            "source_detection_id",
            "category_label",
            "status",
            "status_display",
            "created_at",
        )

    def get_record_code(self, obj):
        source_code = self.get_source_detection_code(obj)
        return source_code or build_category_record_code(obj.category_label, obj.pk)

    def get_source_detection_code(self, obj):
        if not obj.source_detection_id or not obj.source_detection:
            return ""
        category_label = (
            obj.source_detection.results.order_by("-confidence", "id").values_list("label", flat=True).first()
        )
        return build_category_record_code(category_label, obj.source_detection_id)


class DatasetCollectionSerializer(serializers.Serializer):
    detection_id = serializers.IntegerField()
    category_label = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate_detection_id(self, value):
        request = self.context["request"]
        if not DetectionRecord.objects.filter(pk=value, user=request.user).exists():
            raise serializers.ValidationError("未找到可收集的检测图片。")
        return value

    def validate_category_label(self, value):
        return to_chinese_category_label(value, default="")

    def create(self, validated_data):
        request = self.context["request"]
        detection = DetectionRecord.objects.get(pk=validated_data["detection_id"])
        return create_dataset_from_detection(
            request.user,
            detection,
            category_label=validated_data.get("category_label", ""),
        )


class DatasetImageAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetImage
        fields = ("status", "is_in_training_set")
