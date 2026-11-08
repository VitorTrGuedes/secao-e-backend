from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_streamingavailabilitycache_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='delete_token_hash',
            field=models.CharField(blank=True, editable=False, max_length=64),
        ),
        migrations.AddField(
            model_name='comment',
            name='delete_token_expires_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
