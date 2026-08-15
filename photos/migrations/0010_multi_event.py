import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import photos.models


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0009_eventsettings_drive_sharing_enabled_and_more'),
    ]

    operations = [
        migrations.RenameModel(old_name='EventSettings', new_name='Event'),
        migrations.AlterModelOptions(
            name='event',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='event',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='event',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='event',
            name='name',
            field=models.CharField(default=photos.models.default_drive_folder_name, max_length=200, unique=True),
        ),
        # Preserve the existing singleton's folder name as the migrated
        # event's name, instead of leaving it at the callable default above.
        migrations.RunSQL(
            sql="UPDATE photos_event SET name = drive_folder_name",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveField(
            model_name='event',
            name='drive_enabled',
        ),
        migrations.RemoveField(
            model_name='event',
            name='drive_folder_name',
        ),
        migrations.AddField(
            model_name='photo',
            name='event',
            field=models.ForeignKey(
                default=1, on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='photos.event'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='useridentity',
            name='event',
            field=models.ForeignKey(
                default=1, on_delete=django.db.models.deletion.CASCADE, related_name='identities', to='photos.event'
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='useridentity',
            name='pseudo',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='useridentity',
            name='session_key',
            field=models.CharField(max_length=40),
        ),
        migrations.AlterUniqueTogether(
            name='useridentity',
            unique_together={('event', 'pseudo'), ('event', 'session_key')},
        ),
    ]
