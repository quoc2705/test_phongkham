# Bảng doctor_schedule — FK logic qua Django (db_constraint=False cho MariaDB 10.4 + BacSi PK OneToOne)

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('nguoidung', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS doctor_schedule;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name='DoctorSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ngay_lam', models.DateField(help_text='Ngày làm việc')),
                ('ca_lam', models.CharField(
                    choices=[('SANG', 'Ca sáng'), ('CHIEU', 'Ca chiều'), ('TOI', 'Ca tối')],
                    max_length=10,
                )),
                ('ghi_chu', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'bac_si',
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='doctor_schedules',
                        to='nguoidung.bacsi',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Lịch ca làm bác sĩ',
                'verbose_name_plural': 'Lịch ca làm bác sĩ',
                'db_table': 'doctor_schedule',
                'ordering': ['ngay_lam', 'ca_lam'],
            },
        ),
        migrations.AddIndex(
            model_name='doctorschedule',
            index=models.Index(fields=['ngay_lam', 'ca_lam'], name='doctor_sch_ngay_ca_idx'),
        ),
        migrations.AddIndex(
            model_name='doctorschedule',
            index=models.Index(fields=['bac_si', 'ngay_lam'], name='doctor_sch_bs_ngay_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='doctorschedule',
            unique_together={('bac_si', 'ngay_lam', 'ca_lam')},
        ),
    ]
