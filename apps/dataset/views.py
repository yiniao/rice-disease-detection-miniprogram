from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from django.http import Http404, HttpResponse

from apps.common.image_utils import decode_image_to_jpeg_bytes
from apps.common.pagination import MiniAppPagination
from apps.diagnosis.models import DetectionRecord

from .models import DatasetImage
from .serializers import DatasetCollectionSerializer, DatasetImageListSerializer, DatasetImageSerializer
from .services import DatasetCollectionError, delete_dataset_image, toggle_dataset_from_detection


class DatasetImageListCreateView(generics.ListCreateAPIView):
    serializer_class = DatasetImageSerializer
    pagination_class = MiniAppPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["image_variant"] = "thumb" if self.request.method == "GET" else "full"
        return context

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DatasetCollectionSerializer
        return DatasetImageListSerializer

    def get_queryset(self):
        queryset = DatasetImage.objects.select_related("user", "source_detection").prefetch_related("source_detection__results")
        if self.request.user.is_role_admin:
            return queryset.filter(source_detection__isnull=False)
        return queryset.filter(user=self.request.user, source_detection__isnull=False)

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        try:
            instance = write_serializer.save()
        except DatasetCollectionError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        read_serializer = DatasetImageSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class DatasetImageDestroyView(generics.DestroyAPIView):
    serializer_class = DatasetImageSerializer

    def get_queryset(self):
        queryset = DatasetImage.objects.select_related("user", "source_detection").prefetch_related("source_detection__results")
        if self.request.user.is_role_admin:
            return queryset.filter(source_detection__isnull=False)
        return queryset.filter(user=self.request.user, source_detection__isnull=False)

    def perform_destroy(self, instance):
        delete_dataset_image(instance)


class DatasetImageFileView(generics.RetrieveAPIView):
    serializer_class = DatasetImageSerializer

    def get_queryset(self):
        queryset = DatasetImage.objects.select_related("user", "source_detection").prefetch_related("source_detection__results")
        if self.request.user.is_role_admin:
            return queryset.filter(source_detection__isnull=False)
        return queryset.filter(user=self.request.user, source_detection__isnull=False)

    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        if not item.image:
            raise Http404
        try:
            content = decode_image_to_jpeg_bytes(item.image)
        except ValueError as exc:
            raise Http404 from exc
        response = HttpResponse(content, content_type="image/jpeg")
        filename = f"dataset-{item.pk}.jpg"
        if request.GET.get("download"):
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        else:
            response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class DatasetCollectionToggleView(APIView):
    def post(self, request, detection_id):
        try:
            detection = DetectionRecord.objects.get(pk=detection_id, user=request.user)
        except DetectionRecord.DoesNotExist as exc:
            raise ValidationError({"detail": "未找到可收集的检测图片。"}) from exc

        try:
            result = toggle_dataset_from_detection(
                request.user,
                detection,
                category_label=request.data.get("category_label", ""),
            )
        except DatasetCollectionError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        response_data = {
            "collected": result["collected"],
            "action": result["action"],
            "removed_ids": result["removed_ids"],
            "detection_id": detection.id,
            "dataset_image": None,
        }
        if result["dataset_image"] is not None:
            response_data["dataset_image"] = DatasetImageSerializer(
                result["dataset_image"],
                context={"request": request},
            ).data
        return Response(response_data, status=status.HTTP_200_OK)
