# Khớp collation với bảng bac_si / nguoi_dung (tránh lỗi 1267 khi JOIN trên MySQL)

from django.db import migrations


def fix_collation_mysql_only(apps, schema_editor):
    if schema_editor.connection.vendor == 'mysql':
        schema_editor.execute(
            'ALTER TABLE doctor_schedule '
            'CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('nguoidung', '0002_doctor_schedule'),
    ]

    operations = [
        migrations.RunPython(
            code=fix_collation_mysql_only,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
