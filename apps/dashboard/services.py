from datetime import datetime, time, timedelta
from collections import defaultdict

from django.db.models import Avg, Case, CharField, Count, Max, Min, Q, Value, When
from django.db.models import Prefetch
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

from apps.accounts.models import User
from apps.common.category_labels import build_category_record_code, to_chinese_category_label
from apps.common.file_names import sanitize_filename
from apps.diagnosis.models import DetectionRecord, DetectionResult


def get_statistics_filter_options(*, viewer=None):
    scoped_records = build_filtered_detection_records(viewer=viewer)
    scoped_results = DetectionResult.objects.filter(record__in=scoped_records)
    categories = list(
        scoped_results.order_by().values_list("label", flat=True).distinct().order_by("label")
    )
    models = sorted(
        {
            f'{item["model_name"] or "未记录"} / {item["model_version"] or "-"}'
            for item in scoped_records.order_by().values("model_name", "model_version").distinct()
        }
    )
    if viewer and not getattr(viewer, "is_role_admin", False):
        users = [{"id": viewer.id, "username": viewer.username}]
    else:
        users = list(
            User.objects.filter(detection_records__isnull=False)
            .order_by("username")
            .values("id", "username")
            .distinct()
        )
    return {
        "categories": categories,
        "statuses": [
            {"value": DetectionRecord.Status.SUCCESS, "label": "成功"},
            {"value": DetectionRecord.Status.FAILED, "label": "失败"},
            {"value": DetectionRecord.Status.PENDING, "label": "处理中"},
        ],
        "models": models,
        "users": users,
        "granularities": [
            {"value": "auto", "label": "自动"},
            {"value": "day", "label": "按天"},
            {"value": "week", "label": "按周"},
            {"value": "month", "label": "按月"},
        ],
        "can_select_user": bool(viewer and getattr(viewer, "is_role_admin", False)),
    }


def build_detection_statistics(
    *,
    viewer=None,
    start_date=None,
    end_date=None,
    category="",
    status="",
    model_key="",
    user_id=None,
    granularity="auto",
    include_recent=True,
    fast=False,
):
    if fast:
        return _build_fast_detection_statistics(
            viewer=viewer,
            start_date=start_date,
            end_date=end_date,
            category=category,
            status=status,
            model_key=model_key,
            user_id=user_id,
            granularity=granularity,
            include_recent=include_recent,
        )

    records = build_filtered_detection_records(
        viewer=viewer,
        start_date=start_date,
        end_date=end_date,
        category=category,
        status=status,
        model_key=model_key,
        user_id=user_id,
    )
    results = DetectionResult.objects.filter(record__in=records)
    if category:
        results = results.filter(label=category)

    record_summary = records.aggregate(
        total_records=Count("id", distinct=True),
        success_records=Count(
            "id",
            filter=Q(status=DetectionRecord.Status.SUCCESS),
            distinct=True,
        ),
        failed_records=Count(
            "id",
            filter=Q(status=DetectionRecord.Status.FAILED),
            distinct=True,
        ),
        pending_records=Count(
            "id",
            filter=Q(status=DetectionRecord.Status.PENDING),
            distinct=True,
        ),
        avg_duration=Avg("duration_ms"),
        unique_users=Count("user_id", distinct=True),
    )
    result_summary = results.aggregate(
        total_results=Count("id"),
        avg_confidence=Avg("confidence"),
        unique_categories=Count("label", distinct=True),
    )

    total_records = record_summary["total_records"] or 0
    success_records = record_summary["success_records"] or 0
    failed_records = record_summary["failed_records"] or 0
    pending_records = record_summary["pending_records"] or 0
    total_results = result_summary["total_results"] or 0
    avg_duration = record_summary["avg_duration"] or 0
    avg_confidence = result_summary["avg_confidence"] or 0

    selected_granularity = _resolve_granularity(granularity, start_date, end_date, records)
    summary = {
        "total_records": total_records,
        "success_records": success_records,
        "failed_records": failed_records,
        "pending_records": pending_records,
        "success_rate": round((success_records / total_records) * 100, 1) if total_records else 0.0,
        "total_results": total_results,
        "avg_results_per_image": round(total_results / total_records, 2) if total_records else 0.0,
        "avg_duration_ms": round(avg_duration, 1),
        "avg_confidence": round(avg_confidence * 100, 1) if total_results else 0.0,
        "unique_users": record_summary["unique_users"] or 0,
        "unique_categories": result_summary["unique_categories"] or 0,
    }

    return {
        "filters": {
            "selected": {
                "start_date": start_date.isoformat() if start_date else "",
                "end_date": end_date.isoformat() if end_date else "",
                "category": category,
                "status": status,
                "model": model_key,
                "user_id": _normalize_selected_user_id(viewer, user_id),
                "granularity": selected_granularity,
            },
            "options": get_statistics_filter_options(viewer=viewer),
        },
        "summary": summary,
        "charts": {
            "timeline": _build_timeline(records, selected_granularity),
            "categories": _build_category_distribution(results),
            "status_distribution": _build_status_distribution(records, total_records),
            "model_distribution": _build_model_distribution(records),
            "user_distribution": _build_user_distribution(records),
            "confidence_distribution": _build_confidence_distribution(results),
        },
        "recent_records": _build_recent_records(records) if include_recent else [],
}


def _build_fast_detection_statistics(
    *,
    viewer=None,
    start_date=None,
    end_date=None,
    category="",
    status="",
    model_key="",
    user_id=None,
    granularity="auto",
    include_recent=True,
):
    records = build_filtered_detection_records(
        viewer=viewer,
        start_date=start_date,
        end_date=end_date,
        category=category,
        status=status,
        model_key=model_key,
        user_id=user_id,
    )
    record_rows = list(
        records.order_by().values(
            "id",
            "user_id",
            "user__username",
            "status",
            "model_name",
            "model_version",
            "duration_ms",
            "created_at",
        )
    )
    record_ids = [row["id"] for row in record_rows]
    result_rows = list(
        DetectionResult.objects.filter(record_id__in=record_ids)
        .order_by()
        .values("id", "record_id", "label", "confidence")
    ) if record_ids else []
    if category:
        result_rows = [row for row in result_rows if row["label"] == category]

    option_record_rows = record_rows
    option_result_labels = [row["label"] for row in result_rows]
    has_record_filters = bool(start_date or end_date or category or status or model_key or user_id)
    if has_record_filters:
        scoped_records = build_filtered_detection_records(viewer=viewer)
        option_record_rows = list(
            scoped_records.order_by().values(
                "id",
                "model_name",
                "model_version",
            )
        )
        option_record_ids = [row["id"] for row in option_record_rows]
        option_result_labels = list(
            DetectionResult.objects.filter(record_id__in=option_record_ids)
            .order_by()
            .values_list("label", flat=True)
        ) if option_record_ids else []

    selected_granularity = _resolve_fast_granularity(
        granularity,
        start_date,
        end_date,
        record_rows,
    )
    total_records = len(record_rows)
    success_records = sum(row["status"] == DetectionRecord.Status.SUCCESS for row in record_rows)
    failed_records = sum(row["status"] == DetectionRecord.Status.FAILED for row in record_rows)
    pending_records = sum(row["status"] == DetectionRecord.Status.PENDING for row in record_rows)
    total_results = len(result_rows)
    avg_duration = (
        sum(row["duration_ms"] or 0 for row in record_rows) / total_records
        if total_records
        else 0
    )
    avg_confidence = (
        sum(row["confidence"] or 0 for row in result_rows) / total_results
        if total_results
        else 0
    )
    summary = {
        "total_records": total_records,
        "success_records": success_records,
        "failed_records": failed_records,
        "pending_records": pending_records,
        "success_rate": round((success_records / total_records) * 100, 1) if total_records else 0.0,
        "total_results": total_results,
        "avg_results_per_image": round(total_results / total_records, 2) if total_records else 0.0,
        "avg_duration_ms": round(avg_duration, 1),
        "avg_confidence": round(avg_confidence * 100, 1) if total_results else 0.0,
        "unique_users": len({row["user_id"] for row in record_rows}),
        "unique_categories": len({row["label"] for row in result_rows}),
    }

    if viewer and not getattr(viewer, "is_role_admin", False):
        users = [{"id": viewer.id, "username": viewer.username}]
    else:
        users = list(
            User.objects.filter(detection_records__isnull=False)
            .order_by("username")
            .values("id", "username")
            .distinct()
        )
    options = {
        "categories": sorted({label for label in option_result_labels if label}),
        "statuses": [
            {"value": DetectionRecord.Status.SUCCESS, "label": "成功"},
            {"value": DetectionRecord.Status.FAILED, "label": "失败"},
            {"value": DetectionRecord.Status.PENDING, "label": "处理中"},
        ],
        "models": sorted(
            {
                f'{row["model_name"] or "未记录"} / {row["model_version"] or "-"}'
                for row in option_record_rows
            }
        ),
        "users": users,
        "granularities": [
            {"value": "auto", "label": "自动"},
            {"value": "day", "label": "按天"},
            {"value": "week", "label": "按周"},
            {"value": "month", "label": "按月"},
        ],
        "can_select_user": bool(viewer and getattr(viewer, "is_role_admin", False)),
    }
    return {
        "filters": {
            "selected": {
                "start_date": start_date.isoformat() if start_date else "",
                "end_date": end_date.isoformat() if end_date else "",
                "category": category,
                "status": status,
                "model": model_key,
                "user_id": _normalize_selected_user_id(viewer, user_id),
                "granularity": selected_granularity,
            },
            "options": options,
        },
        "summary": summary,
        "charts": {
            "timeline": _build_fast_timeline(record_rows, selected_granularity),
            "categories": _build_fast_category_distribution(result_rows),
            "status_distribution": _build_fast_status_distribution(record_rows, total_records),
            "model_distribution": _build_fast_model_distribution(record_rows),
            "user_distribution": _build_fast_user_distribution(record_rows),
            "confidence_distribution": _build_fast_confidence_distribution(result_rows),
        },
        "recent_records": _build_recent_records(records) if include_recent else [],
    }


def build_filtered_detection_records(*, viewer=None, start_date=None, end_date=None, category="", status="", model_key="", user_id=None):
    records = DetectionRecord.objects.select_related("user")
    if viewer and not getattr(viewer, "is_role_admin", False):
        records = records.filter(user=viewer)
        user_id = viewer.id
    current_timezone = timezone.get_current_timezone()
    if start_date:
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, time.min),
            current_timezone,
        )
        records = records.filter(created_at__gte=start_datetime)
    if end_date:
        end_datetime = timezone.make_aware(
            datetime.combine(end_date + timedelta(days=1), time.min),
            current_timezone,
        )
        records = records.filter(created_at__lt=end_datetime)
    if status:
        records = records.filter(status=status)
    if model_key:
        model_name, model_version = _split_model_key(model_key)
        records = records.filter(model_name=model_name, model_version=model_version)
    if user_id:
        records = records.filter(user_id=user_id)
    if category:
        records = records.filter(results__label=category)
    if category:
        records = records.distinct()
    return records


def _resolve_fast_granularity(granularity, start_date, end_date, record_rows):
    if granularity in {"day", "week", "month"}:
        return granularity
    if start_date and end_date:
        delta_days = max((end_date - start_date).days, 0)
    else:
        dates = [
            timezone.localtime(row["created_at"]).date()
            for row in record_rows
            if row["created_at"]
        ]
        delta_days = (max(dates) - min(dates)).days if dates else 0
    if delta_days > 180:
        return "month"
    if delta_days > 60:
        return "week"
    return "day"


def _fast_bucket(created_at, granularity):
    local_date = timezone.localtime(created_at).date()
    if granularity == "week":
        return local_date - timedelta(days=local_date.weekday())
    if granularity == "month":
        return local_date.replace(day=1)
    return local_date


def _build_fast_timeline(record_rows, granularity):
    buckets = defaultdict(lambda: {"total": 0, "success": 0, "failed": 0})
    for row in record_rows:
        if not row["created_at"]:
            continue
        bucket = buckets[_fast_bucket(row["created_at"], granularity)]
        bucket["total"] += 1
        if row["status"] == DetectionRecord.Status.SUCCESS:
            bucket["success"] += 1
        elif row["status"] == DetectionRecord.Status.FAILED:
            bucket["failed"] += 1
    return [
        {"label": key.isoformat(), **buckets[key]}
        for key in sorted(buckets)
    ]


def _build_fast_category_distribution(result_rows):
    grouped = defaultdict(lambda: {"total": 0, "confidence": 0})
    for row in result_rows:
        item = grouped[row["label"]]
        item["total"] += 1
        item["confidence"] += row["confidence"] or 0
    rows = sorted(
        grouped.items(),
        key=lambda item: (-item[1]["total"], item[0] or ""),
    )[:12]
    return [
        {
            "label": label,
            "total": values["total"],
            "avg_confidence": round((values["confidence"] / values["total"]) * 100, 1),
        }
        for label, values in rows
    ]


def _build_fast_status_distribution(record_rows, total_records):
    grouped = defaultdict(int)
    for row in record_rows:
        grouped[row["status"]] += 1
    label_map = {
        DetectionRecord.Status.SUCCESS: "成功",
        DetectionRecord.Status.FAILED: "失败",
        DetectionRecord.Status.PENDING: "处理中",
    }
    color_map = {
        DetectionRecord.Status.SUCCESS: "#2d8a47",
        DetectionRecord.Status.FAILED: "#c24a3a",
        DetectionRecord.Status.PENDING: "#d8a233",
    }
    return [
        {
            "status": status,
            "label": label_map.get(status, status),
            "total": total,
            "percent": round((total / total_records) * 100, 1) if total_records else 0.0,
            "color": color_map.get(status, "#7a8f80"),
        }
        for status, total in sorted(grouped.items())
    ]


def _build_fast_model_distribution(record_rows):
    grouped = defaultdict(int)
    for row in record_rows:
        key = (row["model_name"] or "", row["model_version"] or "")
        grouped[key] += 1
    rows = sorted(
        grouped.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )[:8]
    return [
        {
            "label": f"{model_name or '未记录'} / {model_version or '-'}",
            "total": total,
        }
        for (model_name, model_version), total in rows
    ]


def _build_fast_user_distribution(record_rows):
    grouped = defaultdict(lambda: {"total": 0, "success": 0})
    for row in record_rows:
        username = row["user__username"] or "未知用户"
        item = grouped[username]
        item["total"] += 1
        if row["status"] == DetectionRecord.Status.SUCCESS:
            item["success"] += 1
    rows = sorted(
        grouped.items(),
        key=lambda item: (-item[1]["total"], item[0]),
    )[:10]
    return [
        {"label": username, "total": values["total"], "success": values["success"]}
        for username, values in rows
    ]


def _build_fast_confidence_distribution(result_rows):
    bucket_order = ["0.00-0.49", "0.50-0.69", "0.70-0.84", "0.85-1.00"]
    totals = dict.fromkeys(bucket_order, 0)
    for row in result_rows:
        confidence = row["confidence"] or 0
        if confidence < 0.5:
            bucket = "0.00-0.49"
        elif confidence < 0.7:
            bucket = "0.50-0.69"
        elif confidence < 0.85:
            bucket = "0.70-0.84"
        else:
            bucket = "0.85-1.00"
        totals[bucket] += 1
    return [{"label": bucket, "total": totals[bucket]} for bucket in bucket_order]


def _normalize_selected_user_id(viewer, user_id):
    if viewer and not getattr(viewer, "is_role_admin", False):
        return viewer.id
    return user_id or ""


def _split_model_key(model_key):
    parts = model_key.split(" / ", 1)
    if len(parts) != 2:
        return model_key, ""
    return parts[0], parts[1]


def _resolve_granularity(granularity, start_date, end_date, records):
    if granularity in {"day", "week", "month"}:
        return granularity
    if start_date and end_date:
        delta_days = max((end_date - start_date).days, 0)
    else:
        bounds = records.aggregate(first=Min("created_at"), last=Max("created_at"))
        first = bounds["first"]
        last = bounds["last"]
        delta_days = (last.date() - first.date()).days if first and last else 0
    if delta_days > 180:
        return "month"
    if delta_days > 60:
        return "week"
    return "day"


def _build_timeline(records, granularity):
    truncator = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}[granularity]
    rows = (
        records.order_by().annotate(bucket=truncator("created_at"))
        .values("bucket")
        .annotate(
            total=Count("id", distinct=True),
            success=Count("id", filter=Q(status=DetectionRecord.Status.SUCCESS), distinct=True),
            failed=Count("id", filter=Q(status=DetectionRecord.Status.FAILED), distinct=True),
        )
        .order_by("bucket")
    )
    items = []
    for row in rows:
        bucket = row["bucket"]
        if hasattr(bucket, "date"):
            bucket = bucket.date()
        items.append(
            {
                "label": bucket.isoformat() if bucket else "-",
                "total": row["total"],
                "success": row["success"],
                "failed": row["failed"],
            }
        )
    return items


def _build_category_distribution(results):
    rows = (
        results.order_by().values("label")
        .annotate(total=Count("id"), avg_confidence=Avg("confidence"))
        .order_by("-total", "label")[:12]
    )
    return [
        {
            "label": row["label"],
            "total": row["total"],
            "avg_confidence": round((row["avg_confidence"] or 0) * 100, 1),
        }
        for row in rows
    ]


def _build_status_distribution(records, total_records):
    rows = records.order_by().values("status").annotate(total=Count("id")).order_by("status")
    label_map = {
        DetectionRecord.Status.SUCCESS: "成功",
        DetectionRecord.Status.FAILED: "失败",
        DetectionRecord.Status.PENDING: "处理中",
    }
    color_map = {
        DetectionRecord.Status.SUCCESS: "#2d8a47",
        DetectionRecord.Status.FAILED: "#c24a3a",
        DetectionRecord.Status.PENDING: "#d8a233",
    }
    return [
        {
            "status": row["status"],
            "label": label_map.get(row["status"], row["status"]),
            "total": row["total"],
            "percent": round((row["total"] / total_records) * 100, 1) if total_records else 0.0,
            "color": color_map.get(row["status"], "#7a8f80"),
        }
        for row in rows
    ]


def _build_model_distribution(records):
    rows = (
        records.order_by().values("model_name", "model_version")
        .annotate(total=Count("id"))
        .order_by("-total", "model_name", "model_version")[:8]
    )
    return [
        {
            "label": f'{row["model_name"] or "未记录"} / {row["model_version"] or "-"}',
            "total": row["total"],
        }
        for row in rows
    ]


def _build_user_distribution(records):
    rows = (
        records.order_by().values("user__username")
        .annotate(
            total=Count("id"),
            success=Count("id", filter=Q(status=DetectionRecord.Status.SUCCESS)),
        )
        .order_by("-total", "user__username")[:10]
    )
    return [
        {
            "label": row["user__username"] or "未知用户",
            "total": row["total"],
            "success": row["success"],
        }
        for row in rows
    ]


def _build_confidence_distribution(results):
    bucket_order = ["0.00-0.49", "0.50-0.69", "0.70-0.84", "0.85-1.00"]
    rows = (
        results.order_by().annotate(
            bucket=Case(
                When(confidence__lt=0.5, then=Value("0.00-0.49")),
                When(confidence__lt=0.7, then=Value("0.50-0.69")),
                When(confidence__lt=0.85, then=Value("0.70-0.84")),
                default=Value("0.85-1.00"),
                output_field=CharField(),
            )
        )
        .values("bucket")
        .annotate(total=Count("id"))
    )
    data_map = {row["bucket"]: row["total"] for row in rows}
    return [{"label": bucket, "total": data_map.get(bucket, 0)} for bucket in bucket_order]


def _build_recent_records(records):
    label_map = {
        DetectionRecord.Status.SUCCESS: "成功",
        DetectionRecord.Status.FAILED: "失败",
        DetectionRecord.Status.PENDING: "处理中",
    }
    recent = (
        records.select_related("user")
        .only(
            "id",
            "user__username",
            "status",
            "model_name",
            "model_version",
            "created_at",
            "duration_ms",
            "original_filename",
        )
        .prefetch_related(
            Prefetch(
                "results",
                queryset=DetectionResult.objects.only(
                    "id",
                    "record_id",
                    "label",
                    "confidence",
                ),
            )
        )
        .order_by("-created_at")[:8]
    )
    return [
        {
            "id": record.id,
            "record_code": build_category_record_code(_get_record_primary_category(record), record.id),
            "original_image_name": _get_record_original_image_name(record),
            "status": label_map.get(record.status, record.status),
            "model": f'{record.model_name or "未记录"} / {record.model_version or "-"}',
            "user": record.user.username if record.user else "未知用户",
            "created_at": record.created_at.strftime("%Y-%m-%d %H:%M"),
            "duration_ms": record.duration_ms,
        }
        for record in recent
    ]


def _get_record_primary_category(record):
    results = list(getattr(record, "results").all()) if hasattr(record, "results") else []
    if not results:
        return "未标注"
    first = sorted(results, key=lambda item: (-item.confidence, item.id))[0]
    return to_chinese_category_label(first.label, default="未标注")


def _get_record_original_image_name(record):
    if not record.original_filename:
        return ""
    return sanitize_filename(record.original_filename, default=f"detection-{record.pk}-original.jpg")
