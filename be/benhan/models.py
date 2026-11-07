from django.db import models
from django.core.exceptions import ValidationError
from nguoidung.models import BenhNhan, BacSi
import uuid
from datetime import date

# ==================== MODEL HỒ SƠ BỆNH ÁN ====================

class HoSoBenhAn(models.Model):
    """Hồ sơ bệnh án của bệnh nhân"""
    TRANG_THAI_CHOICES = [
        ('DANG_DIEU_TRI', 'Đang điều trị'),
        ('DA_XUAT_VIEN', 'Đã xuất viện'),
        ('TAI_KHAM', 'Tái khám'),
        ('KET_THUC', 'Kết thúc điều trị'),
        ('CHUYEN_VIEN', 'Chuyển viện'),
    ]
    
    LOAI_KHAM_CHOICES = [
        ('KHAM_BENH', 'Khám bệnh'),
        ('TAI_KHAM', 'Tái khám'),
        ('CAP_CUU', 'Cấp cứu'),
        ('NOI_TRU', 'Nội trú'),
        ('NGOAI_TRU', 'Ngoại trú'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_hs = models.CharField(max_length=50, unique=True, blank=True, help_text='Mã hồ sơ tự sinh')
    
    # Liên kết
    benh_nhan = models.ForeignKey(BenhNhan, on_delete=models.CASCADE, related_name='ho_so')
    bac_si = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, related_name='ho_so_kham')
    
    # Thông tin thời gian
    ngay_kham = models.DateTimeField(auto_now_add=True)
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
    
    # Thông tin khám lâm sàng
    ly_do_kham = models.TextField(help_text='Lý do đến khám')
    trieu_chung = models.TextField()
    ket_qua_kham_lam_sang = models.TextField(blank=True, default='', help_text='Kết quả khám lâm sàng (bác sĩ)')
    tien_su_benh = models.TextField(blank=True, help_text='Tiền sử bệnh lý')
    tien_su_di_ung = models.TextField(blank=True, help_text='Dị ứng với thuốc/thực phẩm')
    
    # Chỉ số sinh tồn
    can_nang = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='kg')
    chieu_cao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    huyet_ap = models.CharField(max_length=20, blank=True, help_text='VD: 120/80 mmHg')
    nhiet_do = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='°C')
    mach = models.IntegerField(null=True, blank=True, help_text='nhịp/phút')
    nhip_tho = models.IntegerField(null=True, blank=True, help_text='lần/phút')
    spO2 = models.IntegerField(null=True, blank=True, help_text='%')
    
    # Phân loại
    loai_kham = models.CharField(max_length=20, choices=LOAI_KHAM_CHOICES, default='KHAM_BENH')
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='DANG_DIEU_TRI')
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'ho_so_benh_an'
        verbose_name = 'Hồ sơ bệnh án'
        verbose_name_plural = 'Hồ sơ bệnh án'
        ordering = ['-ngay_kham']
        indexes = [
            models.Index(fields=['benh_nhan', 'ngay_kham']),
            models.Index(fields=['bac_si', 'ngay_kham']),
            models.Index(fields=['trang_thai']),
            models.Index(fields=['ma_hs']),
        ]
    
    def __str__(self):
        return f"HS: {self.ma_hs or self.id} - {self.benh_nhan.nguoi_dung.ho_ten} - {self.ngay_kham.strftime('%d/%m/%Y')}"
    
    def save(self, *args, **kwargs):
        if not self.ma_hs:
            from django.db.models import Max
            import datetime
            
            year = datetime.datetime.now().year
            month = datetime.datetime.now().month
            prefix = f"HS{year}{month:02d}"
            
            last_hs = HoSoBenhAn.objects.filter(ma_hs__startswith=prefix).aggregate(
                Max('ma_hs')
            )['ma_hs__max']
            
            if last_hs:
                last_number = int(last_hs[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ma_hs = f"{prefix}{new_number:04d}"
        
        super().save(*args, **kwargs)
    
    def tuoi_benh_nhan(self):
        """Tính tuổi bệnh nhân tại thời điểm khám"""
        if self.benh_nhan.ngay_sinh:
            age = self.ngay_kham.year - self.benh_nhan.ngay_sinh.year
            if (self.ngay_kham.month, self.ngay_kham.day) < (self.benh_nhan.ngay_sinh.month, self.benh_nhan.ngay_sinh.day):
                age -= 1
            return age
        return None


# ==================== MODEL CHẨN ĐOÁN ====================

class ChanDoan(models.Model):
    """Chẩn đoán bệnh cho hồ sơ"""
    LOAI_BENH_CHOICES = [
        ('NOI_TRU', 'Nội trú'),
        ('NGOAI_TRU', 'Ngoại trú'),
        ('CAP_CUU', 'Cấp cứu'),
        ('CHUYEN_KHOA', 'Chuyên khoa'),
    ]
    
    MUC_DO_CHOICES = [
        ('NHẸ', 'Nhẹ'),
        ('TRUNG_BINH', 'Trung bình'),
        ('NANG', 'Nặng'),
        ('NGUY_KICH', 'Nguy kịch'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ho_so = models.OneToOneField(HoSoBenhAn, on_delete=models.CASCADE, related_name='chan_doan')
    
    # Mã bệnh ICD-10
    ma_icd10 = models.CharField(
        max_length=10, db_index=True, blank=True, default='',
        help_text='Mã bệnh theo ICD-10 (tùy chọn)',
    )
    ten_benh = models.CharField(max_length=255)
    ten_benh_tieng_anh = models.CharField(max_length=255, blank=True)
    
    # Phân loại
    loai_benh = models.CharField(max_length=20, choices=LOAI_BENH_CHOICES, default='NGOAI_TRU')
    muc_do = models.CharField(max_length=20, choices=MUC_DO_CHOICES, default='NHẸ')
    
    # Thông tin chẩn đoán
    mo_ta = models.TextField(help_text='Mô tả chi tiết')
    ket_luan = models.TextField()
    phuong_phap_dieu_tri = models.TextField(blank=True)
    
    # Bác sĩ chẩn đoán
    bac_si_chan_doan = models.ForeignKey(
        BacSi, on_delete=models.SET_NULL, null=True, 
        related_name='chan_doan'
    )
    
    # Thời gian
    ngay_chan_doan = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'chan_doan'
        verbose_name = 'Chẩn đoán'
        verbose_name_plural = 'Chẩn đoán'
        indexes = [
            models.Index(fields=['ma_icd10']),
            models.Index(fields=['ten_benh']),
        ]
    
    def __str__(self):
        return f"{self.ma_icd10} - {self.ten_benh} - {self.ho_so}"


# ==================== MODEL ĐƠN THUỐC ====================

class DonThuoc(models.Model):
    """Đơn thuốc cho bệnh nhân"""
    TRANG_THAI_CHOICES = [
        ('CHO_XAC_NHAN', 'Chờ xác nhận'),
        ('CHO_THANH_TOAN', 'Chờ thanh toán'),
        ('DA_THANH_TOAN', 'Đã thanh toán'),
        ('DANG_XU_LY', 'Đang xử lý'),
        ('DA_XUAT_THUOC', 'Đã xuất thuốc'),
        ('HOAN_THANH', 'Hoàn thành'),
        ('DA_HUY', 'Đã hủy'),
    ]
    
    PHUONG_THUC_THANH_TOAN_CHOICES = [
        ('TIEN_MAT', 'Tiền mặt'),
        ('CHUYEN_KHOAN', 'Chuyển khoản'),
        ('THE', 'Thẻ'),
        ('BAO_HIEM', 'Bảo hiểm y tế'),
        ('KET_HOP', 'Kết hợp'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_don = models.CharField(max_length=50, unique=True, blank=True)
    
    # Liên kết
    ho_so = models.ForeignKey(HoSoBenhAn, on_delete=models.CASCADE, related_name='don_thuoc')
    bac_si = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, related_name='don_thuoc')
    benh_nhan = models.ForeignKey(BenhNhan, on_delete=models.CASCADE, related_name='don_thuoc')
    
    # Thông tin đơn thuốc
    chuan_doan = models.TextField(blank=True)
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
    han_su_dung = models.DateField(null=True, blank=True, help_text='Hạn sử dụng của đơn thuốc')
    
    # Trạng thái
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHO_XAC_NHAN')
    da_thanh_toan = models.BooleanField(default=False)
    can_tu_van = models.BooleanField(default=False)
    
    # Thông tin thanh toán
    tong_tien = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ngay_thanh_toan = models.DateTimeField(null=True, blank=True)
    phuong_thuc_thanh_toan = models.CharField(
        max_length=20, choices=PHUONG_THUC_THANH_TOAN_CHOICES, blank=True
    )
    ma_giao_dich = models.CharField(max_length=100, blank=True)
    
    # Thông tin bảo hiểm
    ma_bao_hiem = models.CharField(max_length=50, blank=True)
    ty_le_bao_hiem = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='% BHYT chi trả')
    so_tien_bao_hiem = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    so_tien_benh_nhan_tra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    ghi_chu_thanh_toan = models.TextField(blank=True)
    
    class Meta:
        db_table = 'don_thuoc'
        verbose_name = 'Đơn thuốc'
        verbose_name_plural = 'Đơn thuốc'
        ordering = ['-ngay_tao']
        indexes = [
            models.Index(fields=['trang_thai']),
            models.Index(fields=['benh_nhan', 'ngay_tao']),
            models.Index(fields=['ma_don']),
        ]
    
    def __str__(self):
        return f"ĐT: {self.ma_don} - {self.benh_nhan.ma_benh_nhan} - {self.get_trang_thai_display()}"
    
    def save(self, *args, **kwargs):
        if not self.ma_don:
            from django.db.models import Max
            import datetime
            
            year = datetime.datetime.now().year
            month = datetime.datetime.now().month
            prefix = f"DT{year}{month:02d}"
            
            last_don = DonThuoc.objects.filter(ma_don__startswith=prefix).aggregate(
                Max('ma_don')
            )['ma_don__max']
            
            if last_don:
                last_number = int(last_don[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ma_don = f"{prefix}{new_number:04d}"
        
        if self.ma_bao_hiem and self.ty_le_bao_hiem > 0:
            self.so_tien_bao_hiem = self.tong_tien * self.ty_le_bao_hiem / 100
            self.so_tien_benh_nhan_tra = self.tong_tien - self.so_tien_bao_hiem
        else:
            self.so_tien_benh_nhan_tra = self.tong_tien
        
        super().save(*args, **kwargs)
    
    def tinh_tong_tien(self):
        tong = sum(item.thanh_tien() for item in self.chi_tiet_don_thuoc.all())
        self.tong_tien = tong
        self.save()
        return tong
    
    def clean(self):
        if self.da_thanh_toan and not self.ngay_thanh_toan:
            raise ValidationError('Đơn thuốc đã thanh toán phải có ngày thanh toán')


class ChiTietDonThuoc(models.Model):
    """Chi tiết thuốc trong đơn"""
    CACH_DUNG_CHOICES = [
        ('UONG', 'Uống'),
        ('TIEM', 'Tiêm'),
        ('TRUYEN', 'Truyền'),
        ('BOI', 'Bôi ngoài da'),
        ('NHO_MAT', 'Nhỏ mắt'),
        ('NHO_TAI', 'Nhỏ tai'),
        ('XIT', 'Xịt'),
        ('XONG_HIT', 'Xông hít'),
        ('DAT', 'Đặt'),
        ('NGAM', 'Ngậm'),
        ('SUC', 'Súc miệng'),
    ]
    
    THOI_DIEM_CHOICES = [
        ('SANG', 'Sáng'),
        ('TRUA', 'Trưa'),
        ('CHIEU', 'Chiều'),
        ('TOI', 'Tối'),
        ('SANG_TOI', 'Sáng và tối'),
        ('SANG_CHIEU', 'Sáng và chiều'),
        ('SANG_TRUA_CHIEU', 'Sáng, trưa, chiều'),
        ('SANG_TRUA_CHIEU_TOI', 'Sáng, trưa, chiều, tối'),
        ('TRUOC_AN', 'Trước ăn 30 phút'),
        ('SAU_AN', 'Sau ăn 30 phút'),
        ('TRUOC_NGU', 'Trước khi ngủ'),
        ('KHI_DAN', 'Khi đau'),
        ('KHI_SOT', 'Khi sốt'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    don_thuoc = models.ForeignKey('DonThuoc', on_delete=models.CASCADE, related_name='chi_tiet_don_thuoc', null=True, blank=True)
    thuoc = models.ForeignKey(
        'thuoc.Thuoc',
        on_delete=models.PROTECT,
        related_name='benhan_chitiet_donthuoc',
        null=True,
        blank=True,
    )
    la_thuoc_mua_ngoai = models.BooleanField(
        default=False,
        help_text='Thuốc không có trong danh mục — bệnh nhân mua ngoài, không tính tiền tại quầy',
    )
    ten_thuoc_tu_do = models.CharField(max_length=255, blank=True, help_text='Tên thuốc khi mua ngoài / không chọn từ kho')
    
    # Thông tin liều dùng
    so_luong = models.IntegerField(help_text='Số lượng thuốc')
    lieu_dung = models.CharField(max_length=255, help_text='Liều dùng cho mỗi lần (VD: 1 viên)')
    cach_dung = models.CharField(max_length=20, choices=CACH_DUNG_CHOICES, default='UONG')
    thoi_diem = models.CharField(max_length=30, choices=THOI_DIEM_CHOICES, default='SANG')
    so_ngay_dung = models.IntegerField(default=1)
    tan_suat = models.CharField(max_length=100, blank=True, help_text='Tần suất dùng thuốc')
    
    # Thông tin giá
    don_gia_tai_thoi_diem = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Trạng thái
    da_xuat_thuoc = models.BooleanField(default=False)
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'chi_tiet_don_thuoc'
        verbose_name = 'Chi tiết đơn thuốc'
        verbose_name_plural = 'Chi tiết đơn thuốc'
        indexes = [
            models.Index(fields=['don_thuoc', 'thuoc']),
        ]

    def clean(self):
        if self.la_thuoc_mua_ngoai:
            if not (self.ten_thuoc_tu_do or '').strip():
                raise ValidationError(
                    {'ten_thuoc_tu_do': 'Cần nhập tên thuốc khi đánh dấu mua ngoài.'}
                )
        elif not self.thuoc_id:
            raise ValidationError({'thuoc': 'Cần chọn thuốc trong hệ thống hoặc đánh dấu mua ngoài.'})

    def __str__(self):
        ten = (
            self.ten_thuoc_tu_do
            if self.la_thuoc_mua_ngoai
            else (self.thuoc.ten_thuoc if self.thuoc else '')
        )
        return f"{ten} - SL: {self.so_luong} - {self.lieu_dung}"
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        if self.la_thuoc_mua_ngoai or self.thuoc_id is None:
            self.don_gia_tai_thoi_diem = Decimal('0')
        elif not self.don_gia_tai_thoi_diem and self.thuoc_id:
            self.don_gia_tai_thoi_diem = self.thuoc.gia_ban
        super().save(*args, **kwargs)
    
    def thanh_tien(self):
        from decimal import Decimal
        if self.la_thuoc_mua_ngoai:
            return Decimal('0')
        gia = self.don_gia_tai_thoi_diem or Decimal('0')
        return gia * self.so_luong
    
    def tong_so_lieu(self):
        so_lan_moi_ngay = {
            'SANG': 1,
            'TRUA': 1,
            'CHIEU': 1,
            'TOI': 1,
            'SANG_TOI': 2,
            'SANG_CHIEU': 2,
            'SANG_TRUA_CHIEU': 3,
            'SANG_TRUA_CHIEU_TOI': 4,
        }.get(self.thoi_diem, 1)
        
        tong_lieu = so_lan_moi_ngay * self.so_ngay_dung
        return tong_lieu


# ==================== MODEL XUẤT KHO THUỐC ====================

class PhieuXuatThuoc(models.Model):
    """Phiếu xuất thuốc từ kho"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_phieu = models.CharField(max_length=50, unique=True, blank=True)
    don_thuoc = models.OneToOneField(DonThuoc, on_delete=models.CASCADE, related_name='phieu_xuat')
    nguoi_xuat = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, related_name='phieu_xuat')
    ngay_xuat = models.DateTimeField(auto_now_add=True)
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'phieu_xuat_thuoc'
        verbose_name = 'Phiếu xuất thuốc'
        verbose_name_plural = 'Phiếu xuất thuốc'
        ordering = ['-ngay_xuat']
    
    def __str__(self):
        return f"PX: {self.ma_phieu} - {self.don_thuoc.ma_don}"
    
    def save(self, *args, **kwargs):
        if not self.ma_phieu:
            from django.db.models import Max
            import datetime
            
            year = datetime.datetime.now().year
            month = datetime.datetime.now().month
            prefix = f"PX{year}{month:02d}"
            
            last_px = PhieuXuatThuoc.objects.filter(ma_phieu__startswith=prefix).aggregate(
                Max('ma_phieu')
            )['ma_phieu__max']
            
            if last_px:
                last_number = int(last_px[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ma_phieu = f"{prefix}{new_number:04d}"
        
        super().save(*args, **kwargs)


class ChiTietXuatThuoc(models.Model):
    """Chi tiết xuất thuốc (lô thuốc cụ thể)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phieu_xuat = models.ForeignKey(PhieuXuatThuoc, on_delete=models.CASCADE, related_name='chi_tiet')
    kho_thuoc = models.ForeignKey('thuoc.KhoThuoc', on_delete=models.PROTECT)
    so_luong_xuat = models.IntegerField()
    don_gia_xuat = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'chi_tiet_xuat_thuoc'
    
    def __str__(self):
        return f"{self.kho_thuoc.thuoc.ten_thuoc} - SL: {self.so_luong_xuat}"
    
    def thanh_tien(self):
        return self.so_luong_xuat * self.don_gia_xuat


# ==================== MODEL LỊCH SỬ TIÊM CHỦNG ====================

class LichSuTiemChung(models.Model):
    """Lịch sử tiêm chủng của bệnh nhân"""
    TRANG_THAI_CHOICES = [
        ('DA_TIEM', 'Đã tiêm'),
        ('HEN_TIEM', 'Hẹn tiêm'),
        ('BO_QUA', 'Bỏ qua'),
        ('CHONG_CHI_DINH', 'Chống chỉ định'),
        ('HOAN', 'Hoãn tiêm'),
    ]
    
    PHAN_UNG_CHOICES = [
        ('BINH_THUONG', 'Bình thường'),
        ('SOT_NHE', 'Sốt nhẹ'),
        ('SOT_CAO', 'Sốt cao'),
        ('DI_UNG', 'Dị ứng'),
        ('SUNG_DAU', 'Sưng đau tại chỗ tiêm'),
        ('KHAC', 'Khác'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_lich = models.CharField(max_length=50, unique=True, blank=True)
    
    # Liên kết
    benh_nhan = models.ForeignKey(BenhNhan, on_delete=models.CASCADE, related_name='lich_su_tiem')
    vaccine = models.ForeignKey('thuoc.Vaccine', on_delete=models.PROTECT, related_name='lich_su_tiem')
    nguoi_tiem = models.ForeignKey(
        BacSi, on_delete=models.SET_NULL, null=True, 
        related_name='lich_su_tiem'
    )
    
    # Thông tin mũi tiêm
    so_mui = models.IntegerField(default=1, help_text='Mũi thứ mấy')
    lo_vaccine = models.CharField(max_length=100, blank=True)
    ngay_tiem = models.DateField()
    ngay_tiem_tiep_theo = models.DateField(null=True, blank=True)
    
    # Địa điểm
    dia_diem_tiem = models.CharField(max_length=255, blank=True)
    
    # Phản ứng sau tiêm
    phan_ung_sau_tiem = models.CharField(
        max_length=20, choices=PHAN_UNG_CHOICES, default='BINH_THUONG'
    )
    mo_ta_phan_ung = models.TextField(blank=True)
    
    # Trạng thái
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='DA_TIEM')
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    # Thời gian
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lich_su_tiem_chung'
        verbose_name = 'Lịch sử tiêm chủng'
        verbose_name_plural = 'Lịch sử tiêm chủng'
        ordering = ['-ngay_tiem']
        indexes = [
            models.Index(fields=['benh_nhan', 'ngay_tiem']),
            models.Index(fields=['ngay_tiem_tiep_theo']),
            models.Index(fields=['vaccine']),
        ]
    
    def __str__(self):
        return f"{self.benh_nhan.ma_benh_nhan} - {self.vaccine.ten_vaccine} - Mũi {self.so_mui}"
    
    def save(self, *args, **kwargs):
        if not self.ma_lich:
            from django.db.models import Max
            import datetime
            
            year = datetime.datetime.now().year
            prefix = f"TC{year}"
            
            last_lich = LichSuTiemChung.objects.filter(ma_lich__startswith=prefix).aggregate(
                Max('ma_lich')
            )['ma_lich__max']
            
            if last_lich:
                last_number = int(last_lich[-6:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ma_lich = f"{prefix}{new_number:06d}"
        
        super().save(*args, **kwargs)


# ==================== MODEL TOA THUỐC MẪU ====================

class ToaThuocMau(models.Model):
    """Toa thuốc mẫu cho các bệnh thường gặp"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_toa = models.CharField(max_length=50, unique=True)
    ten_toa = models.CharField(max_length=255)
    
    # Thông tin chẩn đoán
    chuan_doan = models.TextField(help_text='Chẩn đoán áp dụng')
    ma_icd10 = models.CharField(max_length=10, blank=True)
    trieu_chung = models.TextField(blank=True)
    
    # Thông tin tạo
    bac_si_tao = models.ForeignKey(
        BacSi, on_delete=models.SET_NULL, null=True, 
        related_name='benhan_toa_thuoc_mau'
    )
    so_luot_dung = models.IntegerField(default=0, help_text='Số lần được sử dụng')
    
    # Thời gian
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Trạng thái
    trang_thai = models.BooleanField(default=True, help_text='True: đang sử dụng')
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'toa_thuoc_mau_benhan'
        verbose_name = 'Toa thuốc mẫu'
        verbose_name_plural = 'Toa thuốc mẫu'
        ordering = ['ten_toa']
    
    def __str__(self):
        return f"{self.ma_toa} - {self.ten_toa}"


class ChiTietToaMau(models.Model):
    """Chi tiết thuốc trong toa mẫu"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toa_thuoc = models.ForeignKey(ToaThuocMau, on_delete=models.CASCADE, related_name='chi_tiet')
    thuoc = models.ForeignKey('thuoc.Thuoc', on_delete=models.PROTECT, related_name='benhan_chitiet_toamau')
    
    # Thông tin liều dùng (giống ChiTietDonThuoc)
    so_luong = models.IntegerField()
    lieu_dung = models.CharField(max_length=255)
    cach_dung = models.CharField(max_length=20, choices=ChiTietDonThuoc.CACH_DUNG_CHOICES, default='UONG')
    thoi_diem = models.CharField(max_length=30, choices=ChiTietDonThuoc.THOI_DIEM_CHOICES, default='SANG')
    so_ngay_dung = models.IntegerField(default=1)
    tan_suat = models.CharField(max_length=100, blank=True)
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'benhan_chi_tiet_toa_mau'
        verbose_name = 'Chi tiết toa mẫu'
        verbose_name_plural = 'Chi tiết toa mẫu'
        unique_together = ['toa_thuoc', 'thuoc']
    
    def __str__(self):
        return f"{self.thuoc.ten_thuoc} - {self.lieu_dung}"
    
    def thanh_tien_mau(self):
        return self.so_luong * self.thuoc.gia_ban


# ==================== MODEL LỊCH HẸN TÁI KHÁM ====================

class LichHenTaiKham(models.Model):
    """Lịch hẹn tái khám cho bệnh nhân"""
    TRANG_THAI_CHOICES = [
        ('CHUA_KHAM', 'Chưa khám'),
        ('DA_KHAM', 'Đã khám'),
        ('QUA_HAN', 'Quá hạn'),
        ('HUY', 'Đã hủy'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_hen = models.CharField(max_length=50, unique=True, blank=True)
    
    # Liên kết
    benh_nhan = models.ForeignKey(BenhNhan, on_delete=models.CASCADE, related_name='lich_hen_taikham')
    bac_si = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, related_name='lich_hen_taikham')
    ho_so = models.ForeignKey(HoSoBenhAn, on_delete=models.CASCADE, related_name='lich_hen')
    
    # Thông tin lịch hẹn
    ngay_hen = models.DateTimeField()
    ly_do = models.TextField()
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHUA_KHAM')
    
    # Thông tin nhắc nhở
    da_nhac = models.BooleanField(default=False)
    ngay_nhac = models.DateTimeField(null=True, blank=True)
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    # Thời gian
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lich_hen_tai_kham'
        verbose_name = 'Lịch hẹn tái khám'
        verbose_name_plural = 'Lịch hẹn tái khám'
        ordering = ['ngay_hen']
        indexes = [
            models.Index(fields=['ngay_hen', 'trang_thai']),
            models.Index(fields=['benh_nhan', 'ngay_hen']),
        ]
    
    def __str__(self):
        return f"Hẹn {self.benh_nhan.ma_benh_nhan} - {self.ngay_hen.strftime('%d/%m/%Y %H:%M')}"
    
    def save(self, *args, **kwargs):
        if not self.ma_hen:
            from django.db.models import Max
            import datetime
            
            year = datetime.datetime.now().year
            prefix = f"LH{year}"
            
            last_hen = LichHenTaiKham.objects.filter(ma_hen__startswith=prefix).aggregate(
                Max('ma_hen')
            )['ma_hen__max']
            
            if last_hen:
                last_number = int(last_hen[-6:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ma_hen = f"{prefix}{new_number:06d}"
        
        super().save(*args, **kwargs)


# ==================== MODEL THEO DÕI ĐIỀU TRỊ ====================

class TheoDoiDieuTri(models.Model):
    """Theo dõi quá trình điều trị của bệnh nhân"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ho_so = models.ForeignKey(HoSoBenhAn, on_delete=models.CASCADE, related_name='theo_doi')
    bac_si = models.ForeignKey(BacSi, on_delete=models.SET_NULL, null=True, related_name='theo_doi_dieu_tri')
    
    # Thông tin theo dõi
    ngay_theo_doi = models.DateTimeField(auto_now_add=True)
    dien_bien = models.TextField(help_text='Diễn biến bệnh')
    chi_so_sinh_ton = models.JSONField(default=dict, blank=True, help_text='Lưu các chỉ số dưới dạng JSON')
    
    # Đánh giá
    danh_gia = models.TextField(blank=True)
    yeu_cau = models.TextField(blank=True, help_text='Yêu cầu từ bác sĩ')
    
    # Ghi chú
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'theo_doi_dieu_tri'
        verbose_name = 'Theo dõi điều trị'
        verbose_name_plural = 'Theo dõi điều trị'
        ordering = ['-ngay_theo_doi']
    
    def __str__(self):
        return f"Theo dõi {self.ho_so.ma_hs} - {self.ngay_theo_doi.strftime('%d/%m/%Y %H:%M')}"