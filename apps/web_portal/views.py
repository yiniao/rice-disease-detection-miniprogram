from types import SimpleNamespace

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView

from apps.dataset.models import DatasetImage
from apps.dataset.services import delete_dataset_image
from apps.diagnosis.models import DetectionRecord
from apps.diagnosis.services import DetectionPipelineService

from .forms import WebDetectionUploadForm


def _image_proxy(url, name):
    return SimpleNamespace(url=url, name=name, path=name)


def _decorate_detection(request, detection):
    detection.original_image = _image_proxy(
        request.build_absolute_uri(reverse("detection-original-image", args=[detection.pk])),
        f"detection-{detection.pk}-original.jpg",
    )
    if detection.visualized_image:
        detection.visualized_image = _image_proxy(
            request.build_absolute_uri(reverse("detection-visualized-image", args=[detection.pk])),
            f"detection-{detection.pk}-visualized.jpg",
        )
    else:
        detection.visualized_image = None
    return detection


def _decorate_dataset_item(request, item):
    item.image = _image_proxy(
        request.build_absolute_uri(reverse("dataset-image-file", args=[item.pk])),
        f"dataset-{item.pk}.jpg",
    )
    return item


class WebHomeView(TemplateView):
    template_name = "web_portal/home.html"


class WebDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "web_portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detection_count"] = DetectionRecord.objects.filter(user=self.request.user).count()
        context["dataset_count"] = DatasetImage.objects.filter(
            user=self.request.user,
            source_detection__isnull=False,
        ).count()
        return context


class WebDetectionListView(LoginRequiredMixin, FormView):
    template_name = "web_portal/detections.html"
    form_class = WebDetectionUploadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        records = (
            DetectionRecord.objects.filter(user=self.request.user)
            .select_related("advice")
            .prefetch_related("results")
        )
        context["records"] = [_decorate_detection(self.request, record) for record in records]
        return context

    def form_valid(self, form):
        record = DetectionPipelineService.run(self.request.user, form.cleaned_data["image"])
        record = _decorate_detection(self.request, record)
        context = self.get_context_data(
            form=self.get_form(),
            latest_record=record,
        )
        return self.render_to_response(context)


class WebDetectionDetailView(LoginRequiredMixin, DetailView):
    template_name = "web_portal/detection_detail.html"
    model = DetectionRecord
    context_object_name = "record"

    def get_queryset(self):
        return (
            DetectionRecord.objects.filter(user=self.request.user)
            .select_related("advice")
            .prefetch_related("results")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["record"] = _decorate_detection(self.request, context["record"])
        return context


class WebDatasetListView(LoginRequiredMixin, TemplateView):
    template_name = "web_portal/dataset.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = list(
            DatasetImage.objects.filter(
                user=self.request.user,
                source_detection__isnull=False,
            ).select_related("source_detection")
        )
        items_by_detection_id = {
            item.source_detection_id: item
            for item in items
            if item.source_detection_id
        }
        detections = list(
            DetectionRecord.objects.filter(user=self.request.user)
            .select_related("advice")
            .prefetch_related("results")
        )
        for detection in detections:
            dataset_item = items_by_detection_id.get(detection.id)
            detection.is_collected = dataset_item is not None
            detection.dataset_image_id = dataset_item.id if dataset_item else None
            _decorate_detection(self.request, detection)
        context["items"] = [_decorate_dataset_item(self.request, item) for item in items]
        context["detections"] = detections
        return context


class WebDatasetDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(DatasetImage, pk=pk, user=request.user)
        delete_dataset_image(item)
        return redirect("web-dataset")


class WebStatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "web_portal/statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statistics_api_url"] = "/api/statistics/"
        context["statistics_export_url"] = "/api/statistics/export/"
        context["can_select_user"] = self.request.user.is_role_admin
        return context
