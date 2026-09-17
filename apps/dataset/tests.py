import base64
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.diagnosis.models import DetectionRecord, DetectionResult

from .models import DatasetImage


User = get_user_model()


def build_dataset_image(name="dataset.jpg", color="yellow"):
    buffer = BytesIO()
    image = Image.new("RGB", (300, 200), color=color)
    image.save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def build_dataset_image_base64(color="yellow"):
    buffer = BytesIO()
    image = Image.new("RGB", (300, 200), color=color)
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@override_settings(MEDIA_ROOT="test_media")
class DatasetApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="collector")
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_user_can_collect_detection_image(self):
        detection = DetectionRecord.objects.create(user=self.user, original_image=build_dataset_image_base64())
        response = self.client.post("/api/dataset-images/", {"detection_id": detection.id, "category_label": "稻瘟病"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(DatasetImage.objects.count(), 1)
        self.assertEqual(response.data["source_detection_id"], detection.id)
        self.assertEqual(response.data["note"], "")
        self.assertEqual(response.data["category_label"], "稻瘟病")

    def test_collect_keeps_original_image_instead_of_visualized_result(self):
        detection = DetectionRecord.objects.create(
            user=self.user,
            original_image=build_dataset_image_base64(color="green"),
            visualized_image=build_dataset_image_base64(color="red"),
        )
        response = self.client.post("/api/dataset-images/", {"detection_id": detection.id}, format="json")
        self.assertEqual(response.status_code, 201)

        dataset_image = DatasetImage.objects.get(pk=response.data["id"])
        self.assertEqual(base64.b64decode(dataset_image.image), base64.b64decode(detection.original_image))

    def test_user_can_delete_own_dataset_image(self):
        detection = DetectionRecord.objects.create(user=self.user, original_image=build_dataset_image_base64())
        item = DatasetImage.objects.create(user=self.user, source_detection=detection, image=build_dataset_image_base64())

        response = self.client.delete(f"/api/dataset-images/{item.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(DatasetImage.objects.filter(pk=item.id).exists())

    def test_toggle_dataset_collection_creates_and_removes_archive(self):
        detection = DetectionRecord.objects.create(user=self.user, original_image=build_dataset_image_base64())

        create_response = self.client.post(
            f"/api/dataset-toggle/{detection.id}/",
            {"category_label": "纹枯病"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(create_response.data["collected"])
        self.assertEqual(DatasetImage.objects.count(), 1)
        self.assertEqual(DatasetImage.objects.first().category_label, "纹枯病")

        remove_response = self.client.post(f"/api/dataset-toggle/{detection.id}/", {}, format="json")
        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(remove_response.data["collected"])
        self.assertEqual(DatasetImage.objects.count(), 0)

    def test_collect_without_category_uses_detected_label(self):
        detection = DetectionRecord.objects.create(user=self.user, original_image=build_dataset_image_base64())
        DetectionResult.objects.create(
            record=detection,
            label="leaf_blast",
            confidence=0.93,
            xmin=1,
            ymin=1,
            xmax=10,
            ymax=10,
        )

        response = self.client.post("/api/dataset-images/", {"detection_id": detection.id}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["category_label"], "稻瘟病")
        self.assertTrue(response.data["record_code"].startswith("稻瘟病-"))
