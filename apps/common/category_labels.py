ENGLISH_TO_CHINESE_CATEGORY = {
    "healthy": "健康叶片",
    "brown_spot": "褐斑病",
    "leaf_scald": "叶枯病",
    "leaf_blast": "稻瘟病",
    "bacterial_leaf_blight": "白叶枯病",
    "leaf_smut": "叶黑粉病",
    "narrow_brown_spot": "窄褐斑病",
    "not_leaf": "非叶片",
}


def _normalize_key(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def to_chinese_category_label(value, default="未标注"):
    label = str(value or "").strip()
    if not label:
        return default

    normalized = _normalize_key(label)
    if normalized in ENGLISH_TO_CHINESE_CATEGORY:
        return ENGLISH_TO_CHINESE_CATEGORY[normalized]

    # Already looks like Chinese or a custom label.
    return label


def build_category_record_code(category_label, record_id, default="未标注"):
    prefix = to_chinese_category_label(category_label, default=default)
    return f"{prefix}-{int(record_id):06d}"
