# Generated by Django 5.0.7 on 2024-07-24 02:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_customuser_delete_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="email",
            field=models.TextField(unique=True),
        ),
    ]
