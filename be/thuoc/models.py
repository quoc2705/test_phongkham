from django.db import models
from django.db.models import Min
from django.core.exceptions import ValidationError
import uuid
from datetime import date

# ==================== CÁC MODEL CƠ BẢN ====================

class LoaiThuoc(models.Model):
    """Loại thuốc (kháng sinh, giảm đau, hạ sốt, ...)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ten_loai = models.CharField(max_length=100, unique=True)
    mo_ta = models.TextField(blank=True)
    
    class Meta:
        db_table = 'loai_thuoc'
        verbose_name = 'Loại thuốc'
        verbose_name_plural = 'Loại thuốc'
        ordering = ['ten_loai']
    
    def __str__(self):
        return self.ten_loai

class DonViTinh(models.Model):
    """Đơn vị tính (viên, ống, chai, hộp, ...)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ten_don_vi = models.CharField(max_length=50, unique=True)
    ky_hieu = models.CharField(max_length=20, blank=True)  # viên, ống, vỉ...
    
    class Meta:
        db_table = 'don_vi_tinh'
        verbose_name = 'Đơn vị tính'
        verbose_name_plural = 'Đơn vị tính'
        ordering = ['ten_don_vi']
    
    def __str__(self):
        return self.ky_hieu or self.ten_don_vi

class NhaCungCap(models.Model):
    """Nhà cung cấp thuốc và vaccine"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_ncc = models.CharField(max_length=50, unique=True)
    ten_ncc = models.CharField(max_length=255)
    dia_chi = models.TextField()
    so_dien_thoai = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    ma_so_thue = models.CharField(max_length=20, blank=True)
    nguoi_lien_he = models.CharField(max_length=100, blank=True)
    ghi_chu = models.TextField(blank=True)
    trang_thai = models.BooleanField(default=True)  # True: đang hợp tác
    
    class Meta:
        db_table = 'nha_cung_cap'
        verbose_name = 'Nhà cung cấp'
        verbose_name_plural = 'Nhà cung cấp'
        ordering = ['ten_ncc']
    
    def __str__(self):
        return f"{self.ma_ncc} - {self.ten_ncc}"

# ==================== MODEL THUỐC ====================

class Thuoc(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_thuoc = models.CharField(max_length=50, unique=True)
    ten_thuoc = models.CharField(max_length=255)
    
    # Sửa lại thành ForeignKey thay vì CharField
    loai_thuoc = models.ForeignKey(LoaiThuoc, on_delete=models.PROTECT, related_name='thuoc')
    
    # Thông tin giá cả
    don_gia_nhap = models.DecimalField(max_digits=10, decimal_places=2, help_text='Giá nhập vào')
    ty_le_ke_khai = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Tỷ lệ kê khai (%)')
    gia_ban = models.DecimalField(max_digits=10, decimal_places=2, help_text='Giá bán lẻ')
    
    # Đơn vị tính
    don_vi = models.ForeignKey(DonViTinh, on_delete=models.PROTECT, related_name='thuoc')
    
    # Thông tin nhà sản xuất (tùy chọn — ưu tiên liên kết NCC)
    nha_san_xuat = models.CharField(max_length=255, blank=True, default='')
    nuoc_san_xuat = models.CharField(max_length=100, blank=True, default='')
    
    # Thông tin quản lý
    thanh_phan = models.TextField(blank=True, help_text='Thành phần chính')
    ham_luong = models.CharField(max_length=100, blank=True, help_text='Hàm lượng (VD: 500mg)')
    cach_dung = models.TextField(blank=True)
    chi_dinh = models.TextField(blank=True)
    chong_chi_dinh = models.TextField(blank=True)
    tac_dung_phu = models.TextField(blank=True)
    
    # Các cờ đặc biệt
    can_don_thuoc = models.BooleanField(default=False)
    can_tu_van = models.BooleanField(default=False)
    la_thuoc_ban_chay = models.BooleanField(default=False)
    
    # Thông tin khác
    mo_ta = models.TextField(blank=True)
    hinh_anh = models.ImageField(upload_to='thuoc/', null=True, blank=True)
    
    # Trạng thái
    trang_thai = models.BooleanField(default=True, help_text='True: đang kinh doanh, False: ngừng')
    
    # Liên kết với nhà cung cấp
    nha_cung_cap = models.ManyToManyField(NhaCungCap, through='ThuocNhaCungCap', blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'thuoc'
        verbose_name = 'Thuốc'
        verbose_name_plural = 'Thuốc'
        ordering = ['ten_thuoc']
        indexes = [
            models.Index(fields=['ma_thuoc']),
            models.Index(fields=['ten_thuoc']),
            models.Index(fields=['loai_thuoc']),
            models.Index(fields=['trang_thai']),
        ]
    
    def __str__(self):
        return f"{self.ma_thuoc} - {self.ten_thuoc}"

    @classmethod
    def generate_next_ma_thuoc(cls):
        """Mã TH{YYYY}{seq 4 số} — cùng quy tắc với BN/NV/BS."""
        year = date.today().year
        prefix = f'TH{year}'
        codes = cls.objects.filter(ma_thuoc__startswith=prefix).values_list(
            'ma_thuoc', flat=True
        )
        max_seq = 0
        for code in codes:
            try:
                suf = str(code)[-4:]
                max_seq = max(max_seq, int(suf))
            except (ValueError, TypeError):
                continue
        return f'{prefix}{str(max_seq + 1).zfill(4)}'
    
    def ton_kho(self):
        """Tính tổng tồn kho còn hạn sử dụng"""
        kho_con_hang = self.kho_thuoc.filter(han_su_dung__gt=date.today())
        return sum(item.so_luong for item in kho_con_hang)

    def han_sd_lo_gan_nhat(self):
        """Hạn sử dụng gần nhất trong các lô còn hàng (còn hạn)."""
        today = date.today()
        return self.kho_thuoc.filter(han_su_dung__gt=today, so_luong__gt=0).aggregate(
            m=Min('han_su_dung')
        )['m']
    
    def sap_het_han(self):
        """Kiểm tra thuốc sắp hết hạn (trong vòng 3 tháng)"""
        from datetime import timedelta
        ba_thang_toi = date.today() + timedelta(days=90)
        return self.kho_thuoc.filter(
            han_su_dung__lte=ba_thang_toi,
            han_su_dung__gt=date.today()
        ).exists()

class ThuocNhaCungCap(models.Model):
    """Bảng trung gian giữa Thuốc và Nhà cung cấp"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thuoc = models.ForeignKey(Thuoc, on_delete=models.CASCADE)
    nha_cung_cap = models.ForeignKey(NhaCungCap, on_delete=models.CASCADE)
    gia_cung_cap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    la_ncc_chinh = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'thuoc_nha_cung_cap'
        unique_together = ['thuoc', 'nha_cung_cap']

class KhoThuoc(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thuoc = models.ForeignKey(Thuoc, on_delete=models.CASCADE, related_name='kho_thuoc')
    so_luong = models.IntegerField(default=0)
    ngay_nhap = models.DateField()
    han_su_dung = models.DateField()
    lo_sx = models.CharField(max_length=100, blank=True, verbose_name='Lô sản xuất')
    vi_tri = models.CharField(max_length=100, blank=True, help_text='Vị trí lưu kho')
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'kho_thuoc'
        verbose_name = 'Kho thuốc'
        verbose_name_plural = 'Kho thuốc'
        ordering = ['-ngay_nhap']
        indexes = [
            models.Index(fields=['han_su_dung']),
        ]
    
    def __str__(self):
        return f"{self.thuoc.ten_thuoc} - SL: {self.so_luong}"
    
    def clean(self):
        if self.han_su_dung and self.ngay_nhap and self.han_su_dung <= self.ngay_nhap:
            raise ValidationError('Hạn sử dụng phải sau ngày nhập')
    
    def con_han(self):
        return self.han_su_dung > date.today()
    
    def sap_het_han(self):
        from datetime import timedelta
        return self.han_su_dung <= date.today() + timedelta(days=90)

class LichSuGiaThuoc(models.Model):
    """Lịch sử thay đổi giá thuốc"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thuoc = models.ForeignKey(Thuoc, on_delete=models.CASCADE, related_name='lich_su_gia')
    gia_cu = models.DecimalField(max_digits=10, decimal_places=2)
    gia_moi = models.DecimalField(max_digits=10, decimal_places=2)
    ngay_thay_doi = models.DateTimeField(auto_now_add=True)
    nguoi_thay_doi = models.CharField(max_length=100)
    ly_do = models.TextField(blank=True)
    
    class Meta:
        db_table = 'lich_su_gia_thuoc'
        verbose_name = 'Lịch sử giá thuốc'
        verbose_name_plural = 'Lịch sử giá thuốc'
        ordering = ['-ngay_thay_doi']

# ==================== MODEL VACCINE ====================

class LoaiVaccine(models.Model):
    """Phân loại vaccine (theo bệnh/đối tượng)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ten_loai = models.CharField(max_length=100, unique=True)
    mo_ta = models.TextField(blank=True)
    
    class Meta:
        db_table = 'loai_vaccine'
        verbose_name = 'Loại vaccine'
        verbose_name_plural = 'Loại vaccine'
    
    def __str__(self):
        return self.ten_loai

class Vaccine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_vaccine = models.CharField(max_length=50, unique=True)
    ten_vaccine = models.CharField(max_length=255)
    
    # Phân loại
    loai_vaccine = models.ForeignKey(LoaiVaccine, on_delete=models.PROTECT, related_name='vaccine')
    
    # Thông tin giá cả
    gia_nhap = models.DecimalField(max_digits=10, decimal_places=2)
    gia_tiem = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Thông tin tiêm chủng
    phong_benh = models.CharField(max_length=255, help_text='Phòng bệnh gì')
    do_tuoi_ap_dung = models.CharField(max_length=100)
    so_mui = models.IntegerField(default=1)
    lich_tiem = models.TextField(blank=True, help_text='Lịch tiêm chi tiết')
    khoang_cach_mui = models.IntegerField(null=True, blank=True, help_text='Khoảng cách giữa các mũi (ngày)')
    
    # Thông tin bảo quản
    bao_quan = models.CharField(max_length=255, blank=True, help_text='Nhiệt độ bảo quản')
    han_su_dung = models.DateField(null=True, blank=True)
    
    # Thông tin nhà sản xuất (tùy chọn — ưu tiên nhà cung cấp)
    nha_san_xuat = models.CharField(max_length=255, blank=True, default='')
    nuoc_san_xuat = models.CharField(max_length=100, blank=True, default='')
    nha_cung_cap = models.ForeignKey(
        NhaCungCap,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vaccine',
    )
    
    # Thông tin khác
    thanh_phan = models.TextField(blank=True)
    chong_chi_dinh = models.TextField(blank=True)
    phan_ung_sau_tiem = models.TextField(blank=True, help_text='Phản ứng sau tiêm')
    mo_ta = models.TextField(blank=True)
    hinh_anh = models.ImageField(upload_to='vaccine/', null=True, blank=True)
    
    # Trạng thái
    trang_thai = models.BooleanField(default=True)  # True: đang sử dụng
    la_vaccine_dich_vu = models.BooleanField(default=False, help_text='Vaccine dịch vụ')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vaccine'
        verbose_name = 'Vaccine'
        verbose_name_plural = 'Vaccine'
        ordering = ['ten_vaccine']
        indexes = [
            models.Index(fields=['ma_vaccine']),
            models.Index(fields=['ten_vaccine']),
            models.Index(fields=['loai_vaccine']),
        ]
    
    def __str__(self):
        return f"{self.ma_vaccine} - {self.ten_vaccine}"

    @classmethod
    def generate_next_ma_vaccine(cls):
        """Mã VC{YYYY}{seq 4 số} — cùng quy tắc với BN/NV/BS."""
        year = date.today().year
        prefix = f'VC{year}'
        codes = cls.objects.filter(ma_vaccine__startswith=prefix).values_list(
            'ma_vaccine', flat=True
        )
        max_seq = 0
        for code in codes:
            try:
                suf = str(code)[-4:]
                max_seq = max(max_seq, int(suf))
            except (ValueError, TypeError):
                continue
        return f'{prefix}{str(max_seq + 1).zfill(4)}'
    
    def ton_kho(self):
        """Tính tổng tồn kho còn hạn"""
        kho_con_hang = self.kho_vaccine.filter(han_su_dung__gt=date.today())
        return sum(item.so_luong for item in kho_con_hang)

    def han_sd_lo_gan_nhat(self):
        """Hạn sử dụng gần nhất trong các lô còn hàng (còn hạn)."""
        today = date.today()
        return self.kho_vaccine.filter(han_su_dung__gt=today, so_luong__gt=0).aggregate(
            m=Min('han_su_dung')
        )['m']
    
    def get_lich_tiem(self):
        """Trả về lịch tiêm dạng list"""
        if self.lich_tiem:
            return [mui.strip() for mui in self.lich_tiem.split(';')]
        return []

class KhoVaccine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE, related_name='kho_vaccine')
    so_luong = models.IntegerField(default=0)
    ngay_nhap = models.DateField()
    han_su_dung = models.DateField()
    lo_sx = models.CharField(max_length=100, blank=True, verbose_name='Lô sản xuất')
    vi_tri = models.CharField(max_length=100, blank=True)
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'kho_vaccine'
        verbose_name = 'Kho vaccine'
        verbose_name_plural = 'Kho vaccine'
        ordering = ['-ngay_nhap']
        indexes = [
            models.Index(fields=['han_su_dung']),
        ]
    
    def __str__(self):
        return f"{self.vaccine.ten_vaccine} - SL: {self.so_luong}"
    
    def clean(self):
        if self.han_su_dung and self.ngay_nhap and self.han_su_dung <= self.ngay_nhap:
            raise ValidationError('Hạn sử dụng phải sau ngày nhập')
    
    def con_han(self):
        return self.han_su_dung > date.today()

class LichSuGiaVaccine(models.Model):
    """Lịch sử thay đổi giá vaccine"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE, related_name='lich_su_gia')
    gia_cu = models.DecimalField(max_digits=10, decimal_places=2)
    gia_moi = models.DecimalField(max_digits=10, decimal_places=2)
    ngay_thay_doi = models.DateTimeField(auto_now_add=True)
    nguoi_thay_doi = models.CharField(max_length=100)
    ly_do = models.TextField(blank=True)
    
    class Meta:
        db_table = 'lich_su_gia_vaccine'
        verbose_name = 'Lịch sử giá vaccine'
        verbose_name_plural = 'Lịch sử giá vaccine'
        ordering = ['-ngay_thay_doi']

# ==================== MODEL PHIẾU NHẬP KHO ====================

class PhieuNhapKho(models.Model):
    """Phiếu nhập kho tổng quát cho cả thuốc và vaccine"""
    LOAI_NHAP_CHOICES = [
        ('THUOC', 'Thuốc'),
        ('VACCINE', 'Vaccine'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_phieu = models.CharField(max_length=50, unique=True)
    loai_nhap = models.CharField(max_length=10, choices=LOAI_NHAP_CHOICES)
    
    # Thông tin nhà cung cấp
    nha_cung_cap = models.ForeignKey(NhaCungCap, on_delete=models.PROTECT)
    
    # Thời gian
    ngay_nhap = models.DateTimeField(auto_now_add=True)
    ngay_chung_tu = models.DateField()
    
    # Thông tin chứng từ
    so_chung_tu = models.CharField(max_length=100, blank=True)
    tong_tien = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    da_thanh_toan = models.BooleanField(default=False)

    # Duyệt chi (kế toán) — ghi nhận chi phí nhập kho
    da_duyet_chi = models.BooleanField(default=False)
    nguoi_duyet_chi = models.CharField(max_length=150, blank=True)
    ngay_duyet_chi = models.DateTimeField(null=True, blank=True)

    # Đã ghi nhận tồn kho (sau khi kế toán duyệt; tránh cộng trùng)
    da_cap_nhat_kho = models.BooleanField(default=False)
    
    # Người thực hiện
    nguoi_nhap = models.CharField(max_length=100)
    ghi_chu = models.TextField(blank=True)
    
    class Meta:
        db_table = 'phieu_nhap_kho'
        verbose_name = 'Phiếu nhập kho'
        verbose_name_plural = 'Phiếu nhập kho'
        ordering = ['-ngay_nhap']
    
    def __str__(self):
        return f"{self.ma_phieu} - {self.get_loai_nhap_display()}"

class ChiTietPhieuNhapThuoc(models.Model):
    """Chi tiết phiếu nhập cho thuốc"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phieu_nhap = models.ForeignKey(PhieuNhapKho, on_delete=models.CASCADE, related_name='chi_tiet_thuoc')
    thuoc = models.ForeignKey(Thuoc, on_delete=models.PROTECT)
    so_luong = models.IntegerField()
    don_gia = models.DecimalField(max_digits=10, decimal_places=2)
    han_su_dung = models.DateField()
    lo_sx = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'chi_tiet_phieu_nhap_thuoc'
    
    def thanh_tien(self):
        return self.so_luong * self.don_gia

class ChiTietPhieuNhapVaccine(models.Model):
    """Chi tiết phiếu nhập cho vaccine"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phieu_nhap = models.ForeignKey(PhieuNhapKho, on_delete=models.CASCADE, related_name='chi_tiet_vaccine')
    vaccine = models.ForeignKey(Vaccine, on_delete=models.PROTECT)
    so_luong = models.IntegerField()
    don_gia = models.DecimalField(max_digits=10, decimal_places=2)
    han_su_dung = models.DateField()
    lo_sx = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'chi_tiet_phieu_nhap_vaccine'
    
    def thanh_tien(self):
        return self.so_luong * self.don_gia

# ==================== MODEL TOA THUỐC MẪU ====================

class ToaThuocMau(models.Model):
    """Toa thuốc mẫu cho các bệnh thường gặp"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_toa = models.CharField(max_length=50, unique=True)
    ten_toa = models.CharField(max_length=255)
    chuan_doan = models.TextField(help_text='Chẩn đoán áp dụng')
    trieu_chung = models.TextField(blank=True)
    ghi_chu = models.TextField(blank=True)
    thuoc = models.ForeignKey(Thuoc, on_delete=models.PROTECT, related_name='thuoc_chi_tiet_toa_mau')
    
    class Meta:
        db_table = 'thuoc_toa_thuoc_mau'
        verbose_name = 'Toa thuốc mẫu'
        verbose_name_plural = 'Toa thuốc mẫu'
    
    def __str__(self):
        return f"{self.ma_toa} - {self.ten_toa}"

class ChiTietToaMau(models.Model):
    """Chi tiết thuốc trong toa mẫu"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toa_thuoc = models.ForeignKey(ToaThuocMau, on_delete=models.CASCADE, related_name='chi_tiet')
    thuoc = models.ForeignKey(Thuoc, on_delete=models.PROTECT)
    lieu_luong = models.CharField(max_length=100)
    so_luong = models.IntegerField(default=1)
    cach_dung = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'thuoc_chi_tiet_toa_mau'
        unique_together = ['toa_thuoc', 'thuoc']
    
    def __str__(self):
        return f"{self.thuoc.ten_thuoc} - {self.lieu_luong}"