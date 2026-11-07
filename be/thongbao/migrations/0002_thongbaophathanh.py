# ThongBaoPhatHanh — db_constraint=False (MariaDB 10.4 collation / FK errno 150)

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('thongbao', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS thong_bao_phat_hanh;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name='ThongBaoPhatHanh',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tieu_de', models.CharField(max_length=255)),
                ('noi_dung', models.TextField()),
                ('loai_thong_bao', models.CharField(
                    choices=[
                        ('HE_THONG', 'Hệ thống'),
                        ('LICH_HEN', 'Lịch hẹn'),
                        ('DON_THUOC', 'Đơn thuốc'),
                        ('TIEM_CHUNG', 'Tiêm chủng'),
                        ('THANH_TOAN', 'Thanh toán'),
                        ('TAI_KHOAN', 'Tài khoản'),
                    ],
                    default='HE_THONG',
                    max_length=20,
                )),
                ('pham_vi', models.CharField(
                    choices=[
                        ('TAT_CA', 'Toàn bộ người dùng'),
                        ('VAI_TRO', 'Theo vai trò'),
                        ('CHUC_VU', 'Theo chức vụ nhân viên'),
                        ('NGUOI_DUNG', 'Một người dùng cụ thể'),
                    ],
                    max_length=20,
                )),
                ('vai_tro', models.CharField(blank=True, max_length=20)),
                ('chuc_vu', models.CharField(blank=True, max_length=30)),
                ('thoi_gian_gui', models.DateTimeField(help_text='Thời điểm gửi thông báo')),
                ('so_nguoi_nhan', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'nguoi_gui',
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='thong_bao_da_gui',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'nguoi_nhan',
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='thong_bao_phat_hanh_chi_dinh',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Phát hành thông báo',
                'verbose_name_plural': 'Phát hành thông báo',
                'db_table': 'thong_bao_phat_hanh',
                'ordering': ['-thoi_gian_gui', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='thongbaophathanh',
            index=models.Index(fields=['-thoi_gian_gui'], name='tb_ph_gio_idx'),
        ),
        migrations.AddIndex(
            model_name='thongbaophathanh',
            index=models.Index(fields=['pham_vi'], name='tb_ph_pv_idx'),
        ),
        migrations.AddIndex(
            model_name='thongbaophathanh',
            index=models.Index(fields=['loai_thong_bao'], name='tb_ph_loai_idx'),
        ),
    ]
