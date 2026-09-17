from apps.common.file_names import sanitize_filename
from apps.common.category_labels import to_chinese_category_label
from .models import DatasetImage


class DatasetCollectionError(Exception):
    pass


def infer_detection_category(detection):
    result = (
        detection.results.order_by("-confidence", "id").values_list("label", flat=True).first()
        if hasattr(detection, "results")
        else None
    )
    return to_chinese_category_label(result)


def normalize_category_label(category_label, detection):
    value = to_chinese_category_label(category_label, default="")
    return value or infer_detection_category(detection)


def create_dataset_from_detection(user, detection, *, category_label="", shot_at=None, location_text="", growth_stage="", note=""):
    if detection.user_id != user.id:
        raise DatasetCollectionError("只能收集自己的检测图片。")

    existing = DatasetImage.objects.filter(user=user, source_detection=detection).order_by("-created_at").first()
    if existing:
        return existing

    dataset = DatasetImage(
        user=user,
        source_detection=detection,
        image_filename=sanitize_filename(detection.original_filename, default=f"detection-{detection.pk}-original.jpg"),
        category_label=normalize_category_label(category_label, detection),
        shot_at=shot_at,
        location_text=location_text,
        growth_stage=growth_stage,
        note=note,
        image=detection.original_image,
    )
    dataset.save()
    return dataset


def delete_dataset_image(instance):
    instance.delete()


def delete_dataset_images_for_detection(detection):
    DatasetImage.objects.filter(source_detection=detection).delete()


def toggle_dataset_from_detection(user, detection, *, category_label=""):
    if detection.user_id != user.id:
        raise DatasetCollectionError("只能操作自己的检测图片。")

    existing_items = list(
        DatasetImage.objects.filter(user=user, source_detection=detection).order_by("-created_at")
    )
    if existing_items:
        removed_ids = [item.id for item in existing_items]
        for item in existing_items:
            delete_dataset_image(item)
        return {
            "collected": False,
            "action": "removed",
            "removed_ids": removed_ids,
            "dataset_image": None,
        }

    dataset = create_dataset_from_detection(user, detection, category_label=category_label)
    return {
        "collected": True,
        "action": "created",
        "removed_ids": [],
        "dataset_image": dataset,
    }
