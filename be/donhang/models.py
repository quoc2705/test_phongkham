from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from nguoidung.models import BenhNhan, NhanVien, NguoiDung, BacSi
import uuid


# ---------------------------------------------------------------------------
# BaseModel — tránh lặp ngay_tao / ngay_cap_nhat ở mọi model
# ---------------------------------------------------------------------------
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# GioHang
# ---------------------------------------------------------------------------
class GioHang(BaseModel):
    benh_nhan = models.OneToOneField(
        BenhNhan, on_delete=models.CASCADE, related_name='gio_hang'
    )

    class Meta:
        db_table = 'gio_hang'
        verbose_name = 'Giỏ hàng'
        verbose_name_plural = 'Giỏ hàng'
        indexes = [
            models.Index(fields=['benh_nhan']),
            models.Index(fields=['ngay_cap_nhat']),
        ]

    def __str__(self):
        return f"Giỏ hàng - {self.benh_nhan.ma_benh_nhan}"

    def tong_tien(self):
        return sum(item.thanh_tien() for item in self.san_pham_gio_hang.all())

    def so_luong_san_pham(self):
        return self.san_pham_gio_hang.count()


# ---------------------------------------------------------------------------
# SanPhamGioHang
# ---------------------------------------------------------------------------
class SanPhamGioHang(BaseModel):
    gio_hang = models.ForeignKey(
        GioHang, on_delete=models.CASCADE, related_name='san_pham_gio_hang'
    )
    thuoc = models.ForeignKey('thuoc.Thuoc', on_delete=models.CASCADE)
    so_luong = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    # Lưu giá tại thời điểm thêm vào giỏ để tránh thay đổi giá ảnh hưởng giỏ
    don_gia_tai_thoi_diem = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = 'san_pham_gio_hang'
        verbose_name = 'Sản phẩm giỏ hàng'
        verbose_name_plural = 'Sản phẩm giỏ hàng'
        unique_together = ['gio_hang', 'thuoc']
        indexes = [
            models.Index(fields=['gio_hang']),
            models.Index(fields=['thuoc']),
        ]

    def save(self, *args, **kwargs):
        # Chỉ chốt giá khi lần đầu thêm vào giỏ
        if not self.don_gia_tai_thoi_diem:
            self.don_gia_tai_thoi_diem = self.thuoc.gia_ban
        super().save(*args, **kwargs)

    def thanh_tien(self):
        gia = self.don_gia_tai_thoi_diem or self.thuoc.gia_ban
        return gia * self.so_luong

    def clean(self):
        if self.so_luong < 1:
            raise ValidationError({'so_luong': 'Số lượng phải lớn hơn 0'})

    def __str__(self):
        return f"{self.thuoc.ten_thuoc} x {self.so_luong}"


# ---------------------------------------------------------------------------
# DonHang
# ---------------------------------------------------------------------------
class DonHang(BaseModel):
    class LoaiDon(models.TextChoices):
        ONLINE = 'ONLINE', 'Mua online'
        TAI_QUAY = 'TAI_QUAY', 'Mua tại quầy'

    class TrangThai(models.TextChoices):
        MOI_TAO = 'MOI_TAO', 'Mới tạo'
        CHO_THANH_TOAN = 'CHO_THANH_TOAN', 'Chờ thanh toán'
        DA_THANH_TOAN = 'DA_THANH_TOAN', 'Đã thanh toán'
        DANG_CHUAN_BI = 'DANG_CHUAN_BI', 'Đang chuẩn bị'
        DANG_GIAO = 'DANG_GIAO', 'Đang giao hàng'
        HOAN_THANH = 'HOAN_THANH', 'Hoàn thành'
        DA_HUY = 'DA_HUY', 'Đã hủy'

    class TrangThaiDuyetThuocDacThu(models.TextChoices):
        KHONG_CAN = 'KHONG_CAN', 'Khong can duyet bac si'
        CHO_DUYET = 'CHO_DUYET', 'Cho bac si duyet thuoc dac thu'
        DONG_Y = 'DONG_Y', 'Dong y'
        TU_CHOI = 'TU_CHOI', 'Tu choi'

    # Trang thai don da tru kho — can cong lai khi huy
    TRANG_THAI_DA_TRU_KHO = {
        TrangThai.DA_THANH_TOAN,
        TrangThai.DANG_CHUAN_BI,
        TrangThai.DANG_GIAO,
    }

    ma_don_hang = models.CharField(max_length=50, unique=True)
    benh_nhan = models.ForeignKey(
        BenhNhan, on_delete=models.CASCADE, related_name='don_hang'
    )

    # Thông tin người nhận
    ten_nguoi_nhan = models.CharField(max_length=100)
    so_dien_thoai_nhan = models.CharField(max_length=15)
    email_nhan = models.EmailField(blank=True)
    dia_chi_giao_hang = models.TextField()

    # Thông tin xử lý
    loai_don = models.CharField(
        max_length=20, choices=LoaiDon.choices, default=LoaiDon.ONLINE
    )
    nhan_vien_xu_ly = models.ForeignKey(
        NhanVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='don_hang_xu_ly',
    )
    ngay_xu_ly = models.DateTimeField(null=True, blank=True)

    # Tài chính
    tong_tien_hang = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    phi_ship = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    giam_gia = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    tong_tien = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )

    trang_thai = models.CharField(
        max_length=20, choices=TrangThai.choices, default=TrangThai.MOI_TAO
    )
    ly_do_huy = models.TextField(blank=True, null=True)
    ghi_chu = models.TextField(blank=True)

    trang_thai_duyet_bs = models.CharField(
        max_length=20,
        choices=TrangThaiDuyetThuocDacThu.choices,
        default=TrangThaiDuyetThuocDacThu.KHONG_CAN,
        help_text='Duyệt mua thuốc cần đơn / tư vấn (can_don_thuoc, can_tu_van)',
    )
    ghi_chu_duyet_bs = models.TextField(blank=True)
    bac_si_duyet = models.ForeignKey(
        BacSi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='don_hang_duyet_thuoc_dac_thu',
    )
    ngay_duyet_bs = models.DateTimeField(null=True, blank=True)

    don_thuoc = models.ForeignKey(
        'benhan.DonThuoc',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='don_hang_ban',
        help_text='Toa bác sĩ (nếu bán theo đơn)',
    )

    class Meta:
        db_table = 'don_hang'
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'
        ordering = ['-ngay_tao']
        indexes = [
            models.Index(fields=['ma_don_hang']),
            models.Index(fields=['benh_nhan', 'ngay_tao']),
            models.Index(fields=['trang_thai']),
            models.Index(fields=['ngay_tao']),
            models.Index(fields=['loai_don']),
        ]

    def __str__(self):
        return f"{self.ma_don_hang} - {self.benh_nhan.ma_benh_nhan}"

    def save(self, *args, **kwargs):
        # FIX: Chỉ tính tong_tien lần đầu tạo mới (adding),
        # không ghi đè khi update để tránh mất dữ liệu đã chỉnh sửa.
        if self._state.adding and not self.tong_tien:
            self.tong_tien = self.tong_tien_hang + self.phi_ship - self.giam_gia
        super().save(*args, **kwargs)

    def tinh_tong_tien(self):
        return sum(item.thanh_tien() for item in self.chi_tiet_don_hang.all())

    def kiem_tra_ton_kho(self):
        """Kiểm tra tồn kho trước khi xác nhận đơn."""
        for item in self.chi_tiet_don_hang.select_related('thuoc'):
            if item.so_luong > item.thuoc.so_luong_ton:
                return False, item.thuoc.ten_thuoc
        return True, None

    def huy_don_hang(self, ly_do='', nguoi_huy=None):
        """
        Huỷ đơn hàng và hoàn trả tồn kho nếu cần.

        FIX: Lưu trang_thai_cu TRƯỚC khi gán trạng thái mới.
        """
        if self.trang_thai == self.TrangThai.DA_HUY:
            raise ValidationError('Đơn hàng đã được huỷ trước đó.')

        trang_thai_cu = self.trang_thai  # FIX: snapshot trước khi thay đổi

        # Hoàn trả kho nếu đơn đã được xử lý
        if trang_thai_cu in self.TRANG_THAI_DA_TRU_KHO:
            for item in self.chi_tiet_don_hang.select_related('thuoc'):
                item.thuoc.so_luong_ton += item.so_luong
                item.thuoc.save(update_fields=['so_luong_ton'])

        self.trang_thai = self.TrangThai.DA_HUY
        self.ly_do_huy = ly_do
        self.save(update_fields=['trang_thai', 'ly_do_huy', 'ngay_cap_nhat'])

        LichSuDonHang.objects.create(
            don_hang=self,
            trang_thai_cu=trang_thai_cu,   # FIX: dùng snapshot
            trang_thai_moi=self.TrangThai.DA_HUY,
            nguoi_thay_doi=nguoi_huy,
            ghi_chu=f"Huỷ đơn hàng: {ly_do}",
        )

    def clean(self):
        if self.tong_tien is not None and self.tong_tien < 0:
            raise ValidationError({'tong_tien': 'Tổng tiền không thể âm'})
        if (
            self.giam_gia is not None
            and self.tong_tien_hang is not None
            and self.giam_gia > self.tong_tien_hang
        ):
            raise ValidationError({'giam_gia': 'Giảm giá không thể lớn hơn tổng tiền hàng'})

    def trang_thai_hien_thi_quan_ly(self):
        """
        Nhãn trạng thái cho màn quản trị — bám `DonHang.TrangThai` (app donhang),
        chỉ chỉnh nhẹ theo loại đơn / PTTT:

        - Mua tại quầy: sau khi xử lý (không còn chờ TT / hủy) hiển thị «Hoàn thành».
        - Mua online + COD (TIEN_MAT): Mới tạo / Chờ thanh toán → «Chờ thanh toán»;
          các bước sau đúng nhãn model (Đã thanh toán, Đang chuẩn bị, …).
        - Mua online + VNPay: luôn dùng `get_trang_thai_display()` (vd. Đã thanh toán, Đang chuẩn bị, …).
        """
        tt = self.trang_thai

        if self.loai_don == self.LoaiDon.TAI_QUAY:
            if tt in (
                self.TrangThai.MOI_TAO,
                self.TrangThai.CHO_THANH_TOAN,
                self.TrangThai.DA_HUY,
            ):
                return self.get_trang_thai_display()
            return self.TrangThai.HOAN_THANH.label

        phuong_thuc = None
        try:
            phuong_thuc = self.thanh_toan.phuong_thuc
        except ObjectDoesNotExist:
            pass

        if phuong_thuc == 'VNPAY':
            return self.get_trang_thai_display()

        if phuong_thuc == 'TIEN_MAT':
            if tt in (self.TrangThai.MOI_TAO, self.TrangThai.CHO_THANH_TOAN):
                return self.TrangThai.CHO_THANH_TOAN.label
            return self.get_trang_thai_display()

        return self.get_trang_thai_display()


# ---------------------------------------------------------------------------
# ChiTietDonHang
# ---------------------------------------------------------------------------
class ChiTietDonHang(BaseModel):
    don_hang = models.ForeignKey(
        DonHang, on_delete=models.CASCADE, related_name='chi_tiet_don_hang'
    )
    thuoc = models.ForeignKey('thuoc.Thuoc', on_delete=models.PROTECT)
    chi_tiet_don_thuoc = models.ForeignKey(
        'benhan.ChiTietDonThuoc',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chi_tiet_don_hang',
        help_text='Dòng toa tương ứng (nếu bán theo đơn)',
    )
    so_luong = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    don_gia = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    thue_suat = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    chiet_khau = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        db_table = 'chi_tiet_don_hang'
        verbose_name = 'Chi tiết đơn hàng'
        verbose_name_plural = 'Chi tiết đơn hàng'
        indexes = [
            models.Index(fields=['don_hang']),
            models.Index(fields=['thuoc']),
        ]

    def thanh_tien(self):
        return (self.don_gia * self.so_luong) - self.chiet_khau

    def thanh_tien_sau_thue(self):
        return self.thanh_tien() * (1 + self.thue_suat / 100)

    def clean(self):
        if self.chiet_khau is not None and self.don_gia is not None:
            if self.chiet_khau > self.don_gia * self.so_luong:
                raise ValidationError(
                    {'chiet_khau': 'Chiết khấu không thể lớn hơn thành tiền'}
                )

    def __str__(self):
        return f"{self.thuoc.ten_thuoc} x {self.so_luong}"


# ---------------------------------------------------------------------------
# LichSuDonHang
# ---------------------------------------------------------------------------
class LichSuDonHang(models.Model):
    """
    Bảng audit log — KHÔNG kế thừa BaseModel vì không cần ngay_cap_nhat;
    lịch sử là bất biến sau khi tạo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    don_hang = models.ForeignKey(
        DonHang, on_delete=models.CASCADE, related_name='lich_su'
    )
    trang_thai_cu = models.CharField(max_length=20, choices=DonHang.TrangThai.choices)
    trang_thai_moi = models.CharField(max_length=20, choices=DonHang.TrangThai.choices)
    nguoi_thay_doi = models.ForeignKey(
        NguoiDung,
        on_delete=models.SET_NULL,
        null=True,
        related_name='don_hang_thay_doi',
    )
    ghi_chu = models.TextField(blank=True)
    thoi_gian = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lich_su_don_hang'
        verbose_name = 'Lịch sử đơn hàng'
        verbose_name_plural = 'Lịch sử đơn hàng'
        ordering = ['-thoi_gian']
        indexes = [
            models.Index(fields=['don_hang']),
            models.Index(fields=['thoi_gian']),
            models.Index(fields=['trang_thai_moi']),
        ]

    def __str__(self):
        return (
            f"{self.don_hang.ma_don_hang} — "
            f"{self.trang_thai_cu} → {self.trang_thai_moi}"
        )


# ---------------------------------------------------------------------------
# ThanhToan
# ---------------------------------------------------------------------------
class ThanhToan(BaseModel):
    class PhuongThuc(models.TextChoices):
        TIEN_MAT = 'TIEN_MAT', 'Tiền mặt'
        CHUYEN_KHOAN = 'CHUYEN_KHOAN', 'Chuyển khoản'
        THE = 'THE', 'Thẻ'
        VI_DIEN_TU = 'VI_DIEN_TU', 'Ví điện tử'
        VNPAY = 'VNPAY', 'VNPay (QR / chuyển khoản ảo)'

    class TrangThai(models.TextChoices):
        CHO_XU_LY = 'CHO_XU_LY', 'Chờ xử lý'
        THANH_CONG = 'THANH_CONG', 'Thành công'
        THAT_BAI = 'THAT_BAI', 'Thất bại'
        HOAN_TIEN = 'HOAN_TIEN', 'Hoàn tiền'

    don_hang = models.OneToOneField(
        DonHang, on_delete=models.CASCADE, related_name='thanh_toan'
    )
    so_tien = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    phuong_thuc = models.CharField(max_length=20, choices=PhuongThuc.choices)
    trang_thai = models.CharField(
        max_length=20, choices=TrangThai.choices, default=TrangThai.CHO_XU_LY
    )
    ma_giao_dich = models.CharField(max_length=100, blank=True)
    noi_dung = models.TextField(blank=True)
    ngay_thanh_toan = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'thanh_toan'
        verbose_name = 'Thanh toán'
        verbose_name_plural = 'Thanh toán'
        indexes = [
            models.Index(fields=['don_hang']),
            models.Index(fields=['trang_thai']),
            models.Index(fields=['ma_giao_dich']),
            models.Index(fields=['ngay_thanh_toan']),
        ]

    def __str__(self):
        return f"TT-{self.don_hang.ma_don_hang} - {self.so_tien}"

    def clean(self):
        if self.so_tien is not None and self.so_tien <= 0:
            raise ValidationError({'so_tien': 'Số tiền thanh toán phải lớn hơn 0'})