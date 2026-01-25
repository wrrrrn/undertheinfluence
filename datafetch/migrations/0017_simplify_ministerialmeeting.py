# Generated manually for MinisterialMeeting model simplification

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Simplify MinisterialMeeting model:
    - Remove external_actor FK (now tracked via MeetingAttendee)
    - Remove canonical_external_actor FK (entity resolution via MeetingAttendee)
    - Rename external_actor_name_raw to organisation_met_raw

    The MeetingAttendee table is now canonical for tracking organization access.
    """

    dependencies = [
        ('datafetch', '0016_alter_companieshousematch_status'),
    ]

    operations = [
        # 1. Remove indexes on FK fields (must do before removing fields)
        migrations.RemoveIndex(
            model_name='ministerialmeeting',
            name='meeting_external_idx',
        ),
        migrations.RemoveIndex(
            model_name='ministerialmeeting',
            name='meeting_canon_idx',
        ),

        # 2. Remove the old constraint (uses external_actor_name_raw)
        migrations.RemoveConstraint(
            model_name='ministerialmeeting',
            name='unique_ministerial_meeting',
        ),

        # 3. Remove FK fields (data preserved in MeetingAttendee)
        migrations.RemoveField(
            model_name='ministerialmeeting',
            name='external_actor',
        ),
        migrations.RemoveField(
            model_name='ministerialmeeting',
            name='canonical_external_actor',
        ),

        # 4. Rename the raw text field from external_actor_name_raw to organisation_met_raw
        migrations.RenameField(
            model_name='ministerialmeeting',
            old_name='external_actor_name_raw',
            new_name='organisation_met_raw',
        ),

        # 5. Add new constraint with updated field name
        migrations.AddConstraint(
            model_name='ministerialmeeting',
            constraint=models.UniqueConstraint(
                fields=['minister', 'organisation_met_raw', 'meeting_date', 'department'],
                name='unique_ministerial_meeting_v2'
            ),
        ),
    ]
