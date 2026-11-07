from datetime import timedelta
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from nguoidung.models import BacSi, BenhNhan, NguoiDung, NhanVien


class LichHen(models.Model):
    LOAI_LICH_CHOICES = [
        ('KHAM_BENH', 'Khám bệnh'),
        ('TIEM_CHUNG', 'Tiêm chủng'),
        ('TAI_KHAM', 'Tái khám'),
        ('TU_VAN', 'Tư vấn'),
    ]
    
    TRANG_THAI_CHOICES = [
        ('CHO_XAC_NHAN', 'Chờ xác nhận'),
        ('DA_DAT', 'Đã đặt'),
        ('DA_XAC_NHAN', 'Đã xác nhận'),
        ('CHECKED_IN', 'Đã check-in / chờ vào phòng'),
        ('DANG_KHAM', 'Đang khám'),
        ('HOAN_THANH', 'Hoàn thành'),
        ('DA_HUY', 'Đã hủy'),
        ('VANG_MAT', 'Vắng mặt'),
        ('QUA_HAN', 'Quá hạn'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_lich_hen = models.CharField(max_length=20, unique=True, blank=True)
    
    benh_nhan = models.ForeignKey(BenhNhan, on_delete=models.CASCADE, related_name='lich_hen_appointments')
    bac_si = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, blank=True, related_name='lich_hen_schedule')
    nhan_vien_tao = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True, related_name='lich_hen_created')
    
    loai_lich = models.CharField(max_length=20, choices=LOAI_LICH_CHOICES)
    ngay_gio_hen = models.DateTimeField()
    ngay_gio_ket_thuc = models.DateTimeField(null=True, blank=True)
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHO_XAC_NHAN')
    
    so_dien_thoai_lien_he = models.CharField(max_length=15, blank=True)
    email_lien_he = models.EmailField(blank=True)
    
    can_nhac_nho = models.BooleanField(default=True)
    da_nhac_nho = models.BooleanField(default=False)
    ngay_nhac_nho = models.DateTimeField(null=True, blank=True)
    
    ly_do_huy = models.TextField(blank=True)
    nguoi_huy = models.ForeignKey(NguoiDung, on_delete=models.SET_NULL, null=True, blank=True, related_name='lich_hen_cancelled')
    ngay_huy = models.DateTimeField(null=True, blank=True)
    
    thoi_gian_den = models.DateTimeField(null=True, blank=True)
    thoi_gian_bat_dau = models.DateTimeField(null=True, blank=True)
    thoi_gian_ket_thuc = models.DateTimeField(null=True, blank=True)
    
    gia_dich_vu = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    da_thanh_toan = models.BooleanField(default=False)
    phuong_thuc_thanh_toan = models.CharField(max_length=20, blank=True)
    
    ghi_chu = models.TextField(blank=True)

    ma_phong = models.CharField(
        max_length=30, blank=True, default='',
        help_text='Mã phòng khám (VD: P01)',
    )
    ten_phong = models.CharField(
        max_length=100, blank=True, default='',
        help_text='Tên phòng hiển thị',
    )
    stt_trong_ngay = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Số thứ tự tiếp nhận trong ngày (walk-in / hàng chờ)',
    )
    
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lich_hen'
        verbose_name = 'Lịch hẹn'
        verbose_name_plural = 'Lịch hẹn'
        ordering = ['-ngay_gio_hen']
        indexes = [
            models.Index(fields=['benh_nhan', 'ngay_gio_hen']),
            models.Index(fields=['bac_si', 'ngay_gio_hen']),
            models.Index(fields=['trang_thai']),
            models.Index(fields=['ngay_gio_hen']),
            models.Index(fields=['loai_lich']),
        ]
    
    def __str__(self):
        return f"{self.ma_lich_hen or self.id} - {self.benh_nhan.ma_benh_nhan} - {self.get_loai_lich_display()}"
    
    def save(self, *args, **kwargs):
        if not self.ma_lich_hen:
            from django.db.models import Max
            import datetime
            
            today = datetime.datetime.now()
            prefix = f"LH{today.strftime('%y%m')}"
            
            last_lich = LichHen.objects.filter(ma_lich_hen__startswith=prefix).aggregate(
                Max('ma_lich_hen')
            )['ma_lich_hen__max']
            
            if last_lich:
                last_number = int(last_lich[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ma_lich_hen = f"{prefix}{new_number:04d}"
        
        if not self.ngay_gio_ket_thuc and self.ngay_gio_hen:
            self.ngay_gio_ket_thuc = self.ngay_gio_hen + timedelta(minutes=30)
        
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.ngay_gio_hen < timezone.now():
            raise ValidationError('Ngày giờ hẹn không thể trong quá khứ')
        
        if self.ngay_gio_ket_thuc and self.ngay_gio_ket_thuc <= self.ngay_gio_hen:
            raise ValidationError('Giờ kết thúc phải sau giờ bắt đầu')
        
        if self.bac_si and self.pk is None:
            lich_trung = LichHen.objects.filter(
                bac_si=self.bac_si,
                ngay_gio_hen__lt=self.ngay_gio_ket_thuc or (self.ngay_gio_hen + timedelta(minutes=30)),
                ngay_gio_ket_thuc__gt=self.ngay_gio_hen,
                trang_thai__in=['DA_DAT', 'DA_XAC_NHAN', 'DANG_KHAM']
            ).exclude(pk=self.pk)
            
            if lich_trung.exists():
                raise ValidationError('Bác sĩ đã có lịch hẹn trong khung giờ này')
    
    def xac_nhan(self, nguoi_xac_nhan=None):
        self.trang_thai = 'DA_XAC_NHAN'
        self.save()
        self._ghi_nhat_ky('XAC_NHAN', nguoi_xac_nhan)
    
    def bat_dau(self, nguoi_thuc_hien=None):
        self.trang_thai = 'DANG_KHAM'
        self.thoi_gian_bat_dau = timezone.now()
        self.save()
        self._ghi_nhat_ky('BAT_DAU', nguoi_thuc_hien)
    
    def hoan_thanh(self, nguoi_thuc_hien=None):
        self.trang_thai = 'HOAN_THANH'
        self.thoi_gian_ket_thuc = timezone.now()
        self.save()
        self._ghi_nhat_ky('HOAN_THANH', nguoi_thuc_hien)
    
    def huy(self, ly_do, nguoi_huy=None):
        self.trang_thai = 'DA_HUY'
        self.ly_do_huy = ly_do
        self.nguoi_huy = nguoi_huy
        self.ngay_huy = timezone.now()
        self.save()
        self._ghi_nhat_ky('HUY', nguoi_huy, {'ly_do': ly_do})
    
    def khach_den(self):
        self.thoi_gian_den = timezone.now()
        
        if self.thoi_gian_den > self.ngay_gio_hen + timedelta(minutes=15):
            pass
        
        self.save()
    
    def _ghi_nhat_ky(self, hanh_dong, nguoi_thuc_hien, extra_data=None):
        from nguoidung.models import NhatKyHoatDong
        
        data = {
            'lich_hen_id': str(self.id),
            'ma_lich_hen': self.ma_lich_hen,
            'trang_thai_cu': self.trang_thai if hasattr(self, 'trang_thai_cu') else None,
        }
        if extra_data:
            data.update(extra_data)
        
        NhatKyHoatDong.objects.create(
            nguoi_dung=nguoi_thuc_hien if nguoi_thuc_hien else self.benh_nhan.nguoi_dung,
            hanh_dong=hanh_dong,
            doi_tuong='LichHen',
            doi_tuong_id=str(self.id),
            du_lieu_moi=data
        )
    
    @property
    def thoi_gian_cho(self):
        if self.thoi_gian_den and self.thoi_gian_bat_dau:
            return int((self.thoi_gian_bat_dau - self.thoi_gian_den).total_seconds() / 60)
        return None
    
    @property
    def thoi_gian_kham(self):
        if self.thoi_gian_bat_dau and self.thoi_gian_ket_thuc:
            return int((self.thoi_gian_ket_thuc - self.thoi_gian_bat_dau).total_seconds() / 60)
        return None


class LichKham(models.Model):
    lich_hen = models.OneToOneField(LichHen, on_delete=models.CASCADE, primary_key=True, related_name='lich_kham')
    bac_si = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, blank=True, related_name='lich_kham_consultations')
    
    ly_do_kham = models.TextField()
    trieu_chung = models.TextField()
    chuan_doan_so_bo = models.TextField(blank=True)
    
    ket_luan = models.TextField(blank=True)
    loi_khuyen = models.TextField(blank=True)
    
    ho_so_benh_an = models.ForeignKey('benhan.HoSoBenhAn', on_delete=models.SET_NULL, null=True, blank=True, related_name='lich_kham')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lich_kham'
        verbose_name = 'Lịch khám'
        verbose_name_plural = 'Lịch khám'
    
    def __str__(self):
        return f"Lịch khám - {self.lich_hen.ma_lich_hen}"

class LichTiem(models.Model):
    TRANG_THAI_TIEM_CHOICES = [
        ('CHUA_TIEM', 'Chưa tiêm'),
        ('DA_TIEM', 'Đã tiêm'),
        ('TAM_HOAN', 'Tạm hoãn'),
        ('CHONG_CHI_DINH', 'Chống chỉ định'),
    ]
    
    lich_hen = models.OneToOneField(LichHen, on_delete=models.CASCADE, primary_key=True, related_name='lich_tiem')
    vaccine = models.ForeignKey('thuoc.Vaccine', on_delete=models.PROTECT, related_name='lich_tiem_vaccine_schedule')  # Changed to unique name
    
    so_mui = models.IntegerField(default=1)
    lo_vaccine = models.CharField(max_length=100, blank=True)
    nha_san_xuat = models.CharField(max_length=255, blank=True)
    han_su_dung = models.DateField(null=True, blank=True)
    
    nguoi_tiem = models.ForeignKey('nguoidung.BacSi', on_delete=models.SET_NULL, null=True, blank=True, related_name='lich_tiem_performed')
    ngay_tiem_thuc_te = models.DateTimeField(null=True, blank=True)
    
    phan_ung_sau_tiem = models.TextField(blank=True)
    xu_tri_phan_ung = models.TextField(blank=True)
    
    trang_thai_tiem = models.CharField(max_length=20, choices=TRANG_THAI_TIEM_CHOICES, default='CHUA_TIEM')
    ghi_chu = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lich_tiem'
        verbose_name = 'Lịch tiêm'
        verbose_name_plural = 'Lịch tiêm'
    
    def __str__(self):
        return f"Lịch tiêm {self.vaccine.ten_vaccine} - Mũi {self.so_mui}"
    
    def save(self, *args, **kwargs):
        if not self.nha_san_xuat and self.vaccine:
            self.nha_san_xuat = self.vaccine.nha_san_xuat
        super().save(*args, **kwargs)
    
    def thuc_hien_tiem(self, nguoi_tiem, lo_vaccine=None, han_su_dung=None):
        from django.utils import timezone
        self.trang_thai_tiem = 'DA_TIEM'
        self.nguoi_tiem = nguoi_tiem
        self.ngay_tiem_thuc_te = timezone.now()
        if lo_vaccine:
            self.lo_vaccine = lo_vaccine
        if han_su_dung:
            self.han_su_dung = han_su_dung
        self.save()
        
        self.lich_hen.hoan_thanh(nguoi_tiem.nguoi_dung)

class LichSuLichHen(models.Model):
    """Lịch sử thay đổi trạng thái lịch hẹn"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lich_hen = models.ForeignKey(LichHen, on_delete=models.CASCADE, related_name='lich_su')
    
    trang_thai_cu = models.CharField(max_length=20, choices=LichHen.TRANG_THAI_CHOICES)
    trang_thai_moi = models.CharField(max_length=20, choices=LichHen.TRANG_THAI_CHOICES)
    
    ghi_chu = models.TextField(blank=True)
    nguoi_thay_doi = models.ForeignKey(NguoiDung, on_delete=models.SET_NULL, null=True, related_name='lich_su_thay_doi')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lich_su_lich_hen'
        verbose_name = 'Lịch sử lịch hẹn'
        verbose_name_plural = 'Lịch sử lịch hẹn'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.lich_hen.ma_lich_hen}: {self.trang_thai_cu} -> {self.trang_thai_moi}"


class NhacNhoLichHen(models.Model):
    """Nhắc nhở lịch hẹn"""
    LOAI_NHAC_CHOICES = [
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('PUSH', 'Push notification'),
        ('ZALO', 'Zalo'),
    ]
    
    TRANG_THAI_CHOICES = [
        ('CHO_GUI', 'Chờ gửi'),
        ('DA_GUI', 'Đã gửi'),
        ('THAT_BAI', 'Thất bại'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lich_hen = models.ForeignKey(LichHen, on_delete=models.CASCADE, related_name='nhac_nho')
    
    loai_nhac = models.CharField(max_length=10, choices=LOAI_NHAC_CHOICES)
    thoi_gian_nhac = models.DateTimeField()
    noi_dung = models.TextField()
    
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHO_GUI')
    chi_tiet_phan_hoi = models.JSONField(default=dict, blank=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nhac_nho_lich_hen'
        verbose_name = 'Nhắc nhở lịch hẹn'
        verbose_name_plural = 'Nhắc nhở lịch hẹn'
        indexes = [
            models.Index(fields=['thoi_gian_nhac', 'trang_thai']),
        ]
    
    def __str__(self):
        return f"Nhắc nhở {self.lich_hen.ma_lich_hen} - {self.get_loai_nhac_display()}"


class DanhGiaDichVu(models.Model):
    """Đánh giá dịch vụ sau lịch hẹn"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lich_hen = models.OneToOneField(LichHen, on_delete=models.CASCADE, related_name='danh_gia')
    
    diem = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    nhan_xet = models.TextField(blank=True)
    
    thai_do_nhan_vien = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    thoi_gian_cho = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    chat_luong_dich_vu = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    co_so_vat_chat = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'danh_gia_dich_vu'
        verbose_name = 'Đánh giá dịch vụ'
        verbose_name_plural = 'Đánh giá dịch vụ'
    
    def __str__(self):
        return f"Đánh giá {self.lich_hen.ma_lich_hen}: {self.diem}/5"