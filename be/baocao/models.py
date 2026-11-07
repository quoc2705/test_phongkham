
from django.db import models
from django.core.exceptions import ValidationError
import uuid
 
 
# ---------------------------------------------------------------------------
# BaseModel (tái sử dụng từ donhang hoặc một core app chung)
# ---------------------------------------------------------------------------
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
 
    class Meta:
        abstract = True
 
 
# ---------------------------------------------------------------------------
# BaoCao
# ---------------------------------------------------------------------------
class BaoCao(BaseModel):
    class LoaiBaoCao(models.TextChoices):
        DOANH_THU = 'DOANH_THU', 'Doanh thu'
        BENH_NHAN = 'BENH_NHAN', 'Bệnh nhân'
        THUOC = 'THUOC', 'Thuốc'
        VACCINE = 'VACCINE', 'Vaccine'
        LICH_HEN = 'LICH_HEN', 'Lịch hẹn'
        KHAC = 'KHAC', 'Khác'
 
    ten_bao_cao = models.CharField(max_length=255)
    loai = models.CharField(max_length=20, choices=LoaiBaoCao.choices)
    thoi_gian_bat_dau = models.DateField()
    thoi_gian_ket_thuc = models.DateField()
 
    # FIX: du_lieu vẫn là JSONField nhưng được populate bởi service,
    # không phải classmethod trên model. Model chỉ lưu trữ.
    du_lieu = models.JSONField(default=dict)
    nguoi_tao = models.ForeignKey(
        'nguoidung.NguoiDung',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bao_cao_da_tao',
    )
 
    class Meta:
        db_table = 'bao_cao'
        verbose_name = 'Báo cáo'
        verbose_name_plural = 'Báo cáo'
        ordering = ['-ngay_tao']
        indexes = [
            models.Index(fields=['loai', 'ngay_tao']),
            models.Index(fields=['thoi_gian_bat_dau', 'thoi_gian_ket_thuc']),
        ]
 
    def __str__(self):
        return (
            f"{self.ten_bao_cao} "
            f"({self.thoi_gian_bat_dau} - {self.thoi_gian_ket_thuc})"
        )
 
    def clean(self):
        # FIX: Validate khoảng thời gian hợp lệ
        if (
            self.thoi_gian_bat_dau
            and self.thoi_gian_ket_thuc
            and self.thoi_gian_bat_dau > self.thoi_gian_ket_thuc
        ):
            raise ValidationError(
                {
                    'thoi_gian_bat_dau': (
                        'Thời gian bắt đầu không thể sau thời gian kết thúc.'
                    )
                }
            )
 
    # ------------------------------------------------------------------
    # FIX: Các classmethod tạo báo cáo được CHUYỂN SANG BaoCaoService.
    # Model chỉ chứa dữ liệu và validation, không chứa business logic
    # tổng hợp dữ liệu từ các app khác.
    #
    # Xem: baocao/services.py — BaoCaoService.tao_bao_cao_doanh_thu(...)
    # ------------------------------------------------------------------
 
 
# ---------------------------------------------------------------------------
# MauBaoCao
# ---------------------------------------------------------------------------
class MauBaoCao(BaseModel):
    """Mẫu báo cáo định sẵn để tái sử dụng."""
 
    ten_mau = models.CharField(max_length=255)
    loai_bao_cao = models.CharField(max_length=20, choices=BaoCao.LoaiBaoCao.choices)
    tham_so = models.JSONField(default=dict, help_text='Các tham số mặc định cho báo cáo')
    mo_ta = models.TextField(blank=True)
 
    # FIX: Bổ sung nguoi_tao — template báo cáo cần biết ai tạo
    nguoi_tao = models.ForeignKey(
        'nguoidung.NguoiDung',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mau_bao_cao_da_tao',
    )
    la_cong_khai = models.BooleanField(
        default=False,
        help_text='True = mọi người có thể dùng mẫu này',
    )
 
    class Meta:
        db_table = 'mau_bao_cao'
        verbose_name = 'Mẫu báo cáo'
        verbose_name_plural = 'Mẫu báo cáo'
        indexes = [
            models.Index(fields=['loai_bao_cao']),
            models.Index(fields=['la_cong_khai']),
        ]
 
    def __str__(self):
        return self.ten_mau
 