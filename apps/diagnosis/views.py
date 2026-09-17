from django.db.models import Prefetch
from django.http import HttpResponse, Http404, JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response

from apps.common.image_utils import decode_image_to_jpeg_bytes
from apps.common.image_utils import image_bytes_to_data_url
from apps.common.pagination import MiniAppPagination
from apps.dataset.models import DatasetImage
from apps.dataset.services import delete_dataset_images_for_detection

from .models import DetectionRecord
from .serializers import DetectionCreateSerializer, DetectionRecordListSerializer, DetectionRecordSerializer
from .services import DetectionPipelineService


def image_data_response(content, filename):
    return JsonResponse({
        "data_url": image_bytes_to_data_url(
            content,
            max_size=(1280, 1280),
            quality=80,
        ),
        "filename": filename,
    })


class DetectionListCreateView(generics.ListCreateAPIView):
    serializer_class = DetectionRecordSerializer
    pagination_class = MiniAppPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return DetectionRecordListSerializer
        return DetectionRecordSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["image_variant"] = "thumb" if self.request.method == "GET" else "full"
        return context

    def get_queryset(self):
        queryset = DetectionRecord.objects.select_related("advice", "user").prefetch_related("results")
        if self.request.method == "GET":
            queryset = queryset.prefetch_related(
                Prefetch(
                    "collected_dataset_images",
                    queryset=DatasetImage.objects.filter(user=self.request.user).order_by("-created_at"),
                    to_attr="current_user_dataset_images",
                )
            )
        if self.request.user.is_role_admin:
            return queryset
        return queryset.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        serializer = DetectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = DetectionPipelineService.run(
            request.user,
            serializer.validated_data["image"],
            original_filename=serializer.validated_data.get("image_name", ""),
        )
        payload = DetectionRecordSerializer(record, context=self.get_serializer_context()).data
        status_code = status.HTTP_201_CREATED if record.status == DetectionRecord.Status.SUCCESS else status.HTTP_502_BAD_GATEWAY
        return Response(payload, status=status_code)


class DetectionDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DetectionRecordSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Keep detail responses small; the miniapp downloads image bytes from
        # the authenticated image endpoints only when it needs to display or
        # save them.
        context["image_variant"] = "detail"
        return context

    def get_queryset(self):
        queryset = DetectionRecord.objects.select_related("advice", "user").prefetch_related("results")
        if self.request.user.is_role_admin:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_destroy(self, instance):
        delete_dataset_images_for_detection(instance)
        instance.delete()


class DetectionOriginalImageView(generics.RetrieveAPIView):
    serializer_class = DetectionRecordSerializer

    def get_queryset(self):
        queryset = DetectionRecord.objects.all()
        if self.request.user.is_role_admin:
            return queryset
        return queryset.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        record = self.get_object()
        if not record.original_image:
            raise Http404
        try:
            content = decode_image_to_jpeg_bytes(record.original_image)
        except ValueError as exc:
            raise Http404 from exc
        response = HttpResponse(content, content_type="image/jpeg")
        filename = f"detection-{record.pk}-original.jpg"
        if request.GET.get("image_response") == "data":
            return image_data_response(content, filename)
        if request.GET.get("download"):
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        else:
            response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class DetectionVisualizedImageView(DetectionOriginalImageView):
    def retrieve(self, request, *args, **kwargs):
        record = self.get_object()
        if not record.visualized_image:
            raise Http404
        try:
            content = decode_image_to_jpeg_bytes(record.visualized_image)
        except ValueError as exc:
            raise Http404 from exc
        response = HttpResponse(content, content_type="image/jpeg")
        filename = f"detection-{record.pk}-visualized.jpg"
        if request.GET.get("image_response") == "data":
            return image_data_response(content, filename)
        if request.GET.get("download"):
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        else:
            response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
