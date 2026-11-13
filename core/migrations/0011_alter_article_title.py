from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_comment_delete_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='title',
            field=models.CharField(max_length=500),
        ),
    ]
