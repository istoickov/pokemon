# Generated manually to add stat_url field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("battle", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pokemonstat",
            name="stat_url",
            field=models.URLField(max_length=256, blank=True, default=""),
        ),
    ]

