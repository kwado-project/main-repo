"""Give every existing account (e.g. ones made with createsuperuser) a profile, streak and wallet."""
from django.db import migrations


def backfill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for model in (apps.get_model("accounts", "StudentProfile"), apps.get_model("gamification", "Streak"),
                  apps.get_model("wallet", "Wallet")):
        missing = User.objects.exclude(pk__in=model.objects.values("user_id")).values_list("pk", flat=True)
        model.objects.bulk_create([model(user_id=pk) for pk in missing], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
        ("gamification", "0001_initial"),
        ("wallet", "0001_initial"),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
