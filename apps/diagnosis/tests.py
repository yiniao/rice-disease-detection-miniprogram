import base64
import json
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.dataset.models import DatasetImage

from .models import DetectionRecord


User = get_user_model()


def build_test_image(name="leaf.jpg", color="green"):
    buffer = BytesIO()
    image = Image.new("RGB", (320, 240), color=color)
    image.save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def build_test_image_base64(color="green"):
    buffer = BytesIO()
    image = Image.new("RGB", (320, 240), color=color)
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_test_image_bytes(color="green"):
    return base64.b64decode(build_test_image_base64(color=color))


@override_settings(MEDIA_ROOT="test_media", MODEL_BACKEND="mock", DEEPSEEK_API_KEY="")
class DetectionApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="farmer")
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_detection_upload_creates_record_and_advice(self):
        response = self.client.post("/api/detections/", {"image": build_test_image()}, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "success")
        self.assertGreaterEqual(len(response.data["results"]), 1)
        self.assertIn("仅供参考", response.data["advice"]["response_text"])
        self.assertEqual(response.data["advice"]["source"], "local-fallback")

    def test_detection_upload_accepts_base64_image(self):
        response = self.client.post("/api/detections/", {"image": build_test_image_base64()}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["original_image_url"].startswith("data:image/jpeg;base64,"))
        self.assertTrue(response.data["preview_image_url"].startswith("data:image/jpeg;base64,"))

    @patch("apps.common.image_utils.urlopen")
    def test_detection_upload_accepts_remote_image_url(self, mock_urlopen):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return build_test_image_bytes(color="blue")

        mock_urlopen.return_value = FakeResponse()
        response = self.client.post("/api/detections/", {"image": "https://example.com/sample.jpg"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "success")
        self.assertTrue(response.data["original_image_url"].startswith("data:image/jpeg;base64,"))

    def test_user_only_sees_own_records(self):
        other = User.objects.create_user(username="other")
        DetectionRecord.objects.create(user=other, original_image=build_test_image_base64())
        DetectionRecord.objects.create(user=self.user, original_image=build_test_image_base64())
        response = self.client.get("/api/detections/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_user_can_open_detail_for_unlabeled_record(self):
        record = DetectionRecord.objects.create(
            user=self.user,
            original_image=build_test_image_base64(),
            original_filename="unlabeled.jpg",
        )

        response = self.client.get(f"/api/detections/{record.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["primary_category"], "未标注")
        self.assertEqual(response.data["results"], [])
        self.assertEqual(
            response.data["original_image_url"],
            f"/api/detections/{record.id}/original-image/",
        )
        self.assertIsNone(response.data["advice"])

    def test_user_can_download_detail_image_data_through_api(self):
        record = DetectionRecord.objects.create(
            user=self.user,
            original_image=build_test_image_base64(),
        )

        response = self.client.get(
            f"/api/detections/{record.id}/original-image/?image_response=data"
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload["data_url"].startswith("data:image/jpeg;base64,"))

    def test_user_can_delete_own_record(self):
        record = DetectionRecord.objects.create(user=self.user, original_image=build_test_image_base64())
        response = self.client.delete(f"/api/detections/{record.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DetectionRecord.objects.filter(pk=record.id).exists())

    def test_deleting_record_also_deletes_collected_dataset_images(self):
        record = DetectionRecord.objects.create(user=self.user, original_image=build_test_image_base64())
        dataset = DatasetImage.objects.create(user=self.user, source_detection=record, image=build_test_image_base64())
        response = self.client.delete(f"/api/detections/{record.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DatasetImage.objects.filter(pk=dataset.id).exists())
