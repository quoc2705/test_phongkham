# Khớp collation utf8mb4_unicode_ci (MariaDB 10.4 / MySQL)

from django.db import migrations


def fix_collation_mysql_only(apps, schema_editor):
    if schema_editor.connection.vendor == 'mysql':
        schema_editor.execute(
            'ALTER TABLE thong_bao_phat_hanh '
            'CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('thongbao', '0002_thongbaophathanh'),
    ]

    operations = [
        migrations.RunPython(
            code=fix_collation_mysql_only,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
