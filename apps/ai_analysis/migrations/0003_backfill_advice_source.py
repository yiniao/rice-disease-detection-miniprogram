from django.db import migrations


def backfill_source(apps, schema_editor):
    AdviceRecord = apps.get_model("ai_analysis", "AdviceRecord")
    for record in AdviceRecord.objects.all():
        raw_response = record.raw_response or {}
        if isinstance(raw_response, dict) and "choices" in raw_response:
            record.source = "deepseek"
        else:
            record.source = "local-fallback"
        record.save(update_fields=["source"])


class Migration(migrations.Migration):

    dependencies = [
        ("ai_analysis", "0002_add_source_field"),
    ]

    operations = [
        migrations.RunPython(backfill_source, reverse_code=migrations.RunPython.noop),
    ]
