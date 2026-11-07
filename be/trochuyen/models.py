from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from nguoidung.models import NguoiDung, BenhNhan, BacSi, NhanVien
import uuid
from django.conf import settings


# ---------------------------------------------------------------------------
# PhongChat
# ---------------------------------------------------------------------------


class PhongChat(models.Model):
    class LoaiPhong(models.TextChoices):
        TU_VAN = 'TU_VAN', 'Tư vấn'
        HOI_CHAN = 'HOI_CHAN', 'Hội chẩn'       # bác sĩ với bác sĩ — không cần bệnh nhân
        HEN_LICH = 'HEN_LICH', 'Hẹn lịch'
        HOI_DAP = 'HOI_DAP', 'Hỏi đáp'

    class TrangThai(models.TextChoices):
        MO = 'MO', 'Mở'
        DONG = 'DONG', 'Đóng'
        KET_THUC = 'KET_THUC', 'Kết thúc'

    # Các loại phòng BẮT BUỘC có bệnh nhân
    LOAI_PHONG_CAN_BENH_NHAN = {LoaiPhong.TU_VAN, LoaiPhong.HEN_LICH, LoaiPhong.HOI_DAP}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ma_phong = models.CharField(max_length=50, unique=True, blank=True)
    ten_phong = models.CharField(max_length=255)
    loai_phong = models.CharField(
        max_length=20, choices=LoaiPhong.choices, default=LoaiPhong.TU_VAN
    )
    trang_thai = models.CharField(
        max_length=20, choices=TrangThai.choices, default=TrangThai.MO
    )

    # FIX: benh_nhan là nullable vì HOI_CHAN không cần bệnh nhân
    benh_nhan = models.ForeignKey(
        BenhNhan,
        on_delete=models.CASCADE,
        related_name='phong_chat',
        null=True,
        blank=True,
    )
    bac_si = models.ForeignKey(
        BacSi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='phong_chat_bac_si',
    )
    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='phong_chat_nhan_vien',
    )

    benh_an = models.ForeignKey(
        'benhan.HoSoBenhAn', on_delete=models.SET_NULL, null=True, blank=True
    )
    lich_hen = models.ForeignKey(
        'lichhen.LichHen', on_delete=models.SET_NULL, null=True, blank=True
    )

    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(auto_now=True)
    ngay_ket_thuc = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'phong_chat'
        verbose_name = 'Phòng chat'
        verbose_name_plural = 'Phòng chat'
        ordering = ['-ngay_cap_nhat']
        indexes = [
            models.Index(fields=['ma_phong']),
            models.Index(fields=['benh_nhan', 'trang_thai']),
            models.Index(fields=['ngay_cap_nhat']),
        ]

    def __str__(self):
        return f"{self.ma_phong} — {self.ten_phong}"

    def clean(self):
        # FIX: Validate nghiệp vụ — loại phòng cần bệnh nhân thì phải có
        if (
            self.loai_phong in self.LOAI_PHONG_CAN_BENH_NHAN
            and self.benh_nhan is None
        ):
            raise ValidationError(
                {
                    'benh_nhan': (
                        f"Phòng loại '{self.get_loai_phong_display()}' "
                        f"bắt buộc phải có bệnh nhân."
                    )
                }
            )
        # Phòng hội chẩn cần ít nhất một bác sĩ
        if self.loai_phong == self.LoaiPhong.HOI_CHAN and self.bac_si is None:
            raise ValidationError(
                {'bac_si': "Phòng hội chẩn bắt buộc phải có bác sĩ."}
            )

    def save(self, *args, **kwargs):
        # FIX: Dùng UUID rút gọn thay random để đảm bảo không trùng
        if not self.ma_phong:
            ngay = timezone.now().strftime('%Y%m%d')
            uid = str(uuid.uuid4()).replace('-', '')[:8].upper()
            self.ma_phong = f"CHAT{ngay}{uid}"
        super().save(*args, **kwargs)

    @property
    def ten_nguoi_tu_van(self):
        if self.bac_si:
            return self.bac_si.nguoi_dung.ho_ten
        if self.nhan_vien:
            return self.nhan_vien.nguoi_dung.ho_ten
        return None

    def danh_sach_thanh_vien(self):
        """Lấy danh sách thành viên đang active trong phòng."""
        return list(
            self.thanh_vien.filter(is_active=True)
            .select_related('nguoi_dung')
            .values(
                id=models.F('nguoi_dung__id'),
                ho_ten=models.F('nguoi_dung__ho_ten'),
                vai_tro=models.F('vai_tro'),
            )
        )

    def kiem_tra_quyen(self, user) -> bool:
        """Kiểm tra user có quyền truy cập phòng không."""
        return self.thanh_vien.filter(
            nguoi_dung=user, is_active=True
        ).exists()


# ---------------------------------------------------------------------------
# TinNhan (theo phong — khop views/serializers)
# ---------------------------------------------------------------------------


class TinNhan(models.Model):
    class LoaiTinNhan(models.TextChoices):
        TEXT = 'TEXT', 'Van ban'
        HINH_ANH = 'HINH_ANH', 'Hinh anh'
        FILE = 'FILE', 'File'
        THUOC = 'THUOC', 'Thuoc'
        LICH_HEN = 'LICH_HEN', 'Lich hen'
        BENH_AN = 'BENH_AN', 'Benh an'
        THONG_BAO = 'THONG_BAO', 'Thong bao'

    LOAI_TIN_NHAN_CHOICES = LoaiTinNhan.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phong_chat = models.ForeignKey(
        PhongChat, on_delete=models.CASCADE, related_name='tin_nhan'
    )
    nguoi_gui = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tin_nhan_phong_gui',
    )

    loai = models.CharField(
        max_length=20, choices=LoaiTinNhan.choices, default=LoaiTinNhan.TEXT
    )
    noi_dung = models.TextField(blank=True)

    thuoc = models.ForeignKey(
        'thuoc.Thuoc', on_delete=models.SET_NULL, null=True, blank=True
    )
    lich_hen = models.ForeignKey(
        'lichhen.LichHen', on_delete=models.SET_NULL, null=True, blank=True
    )
    benh_an = models.ForeignKey(
        'benhan.HoSoBenhAn', on_delete=models.SET_NULL, null=True, blank=True
    )

    file = models.FileField(
        upload_to='chat/files/%Y/%m/%d/', null=True, blank=True
    )
    hinh_anh = models.ImageField(
        upload_to='chat/images/%Y/%m/%d/', null=True, blank=True
    )

    ngay_gui = models.DateTimeField(auto_now_add=True)
    ngay_xem = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tin_nhan'
        ordering = ['ngay_gui']
        indexes = [
            models.Index(fields=['phong_chat', 'ngay_gui']),
        ]

    def __str__(self):
        if self.loai == self.LoaiTinNhan.TEXT:
            return f"{self.nguoi_gui}: {self.noi_dung[:50]}"
        return f"{self.nguoi_gui}: [{self.get_loai_display()}]"

    def save(self, *args, **kwargs):
        if not self.noi_dung:
            if self.loai == self.LoaiTinNhan.THUOC and self.thuoc:
                self.noi_dung = f"Gui thuoc: {self.thuoc.ten_thuoc}"
            elif self.loai == self.LoaiTinNhan.LICH_HEN and self.lich_hen:
                self.noi_dung = f"Gui lich hen: {self.lich_hen}"
            elif self.loai == self.LoaiTinNhan.BENH_AN and self.benh_an:
                self.noi_dung = f"Gui benh an: {self.benh_an.ma_hs}"
        super().save(*args, **kwargs)

    def da_xem_boi(self, nguoi_dung) -> bool:
        return self.trang_thai_xem.filter(nguoi_dung=nguoi_dung).exists()


# ---------------------------------------------------------------------------
# TinNhanDaXem — thay thế da_xem BooleanField
#
# FIX: Model riêng để track từng thành viên đọc tin nhắn.
# Phù hợp group chat (nhiều người đọc), hỗ trợ analytics "đọc lúc mấy giờ".
# ---------------------------------------------------------------------------
class TinNhanDaXem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tin_nhan = models.ForeignKey(
        TinNhan, on_delete=models.CASCADE, related_name='trang_thai_xem'
    )
    nguoi_dung = models.ForeignKey(
        NguoiDung, on_delete=models.CASCADE, related_name='tin_nhan_da_xem'
    )
    da_xem_luc = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tin_nhan_da_xem'
        verbose_name = 'Trạng thái đọc tin nhắn'
        verbose_name_plural = 'Trạng thái đọc tin nhắn'
        unique_together = ['tin_nhan', 'nguoi_dung']
        indexes = [
            models.Index(fields=['tin_nhan']),
            models.Index(fields=['nguoi_dung', 'da_xem_luc']),
        ]

    def __str__(self):
        return f"{self.nguoi_dung.ho_ten} đọc lúc {self.da_xem_luc}"


# ---------------------------------------------------------------------------
# ThanhVienPhong
# ---------------------------------------------------------------------------
class ThanhVienPhong(models.Model):
    class VaiTro(models.TextChoices):
        BENH_NHAN = 'BENH_NHAN', 'Bệnh nhân'
        BAC_SI = 'BAC_SI', 'Bác sĩ'
        NHAN_VIEN = 'NHAN_VIEN', 'Nhân viên'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phong_chat = models.ForeignKey(
        PhongChat, on_delete=models.CASCADE, related_name='thanh_vien'
    )
    nguoi_dung = models.ForeignKey(NguoiDung, on_delete=models.CASCADE)

    # FIX: Thêm vai_tro — cần biết thành viên đóng vai trò gì trong phòng
    vai_tro = models.CharField(max_length=20, choices=VaiTro.choices)

    ngay_tham_gia = models.DateTimeField(auto_now_add=True)
    ngay_roi_di = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'thanh_vien_phong'
        verbose_name = 'Thành viên phòng'
        verbose_name_plural = 'Thành viên phòng'
        unique_together = ['phong_chat', 'nguoi_dung']
        indexes = [
            models.Index(fields=['phong_chat', 'is_active']),
        ]

    def roi_phong(self):
        """Đánh dấu thành viên rời phòng."""
        self.is_active = False
        self.ngay_roi_di = timezone.now()
        self.save(update_fields=['is_active', 'ngay_roi_di'])

    def __str__(self):
        return (
            f"{self.phong_chat.ma_phong} — "
            f"{self.nguoi_dung.ho_ten} ({self.get_vai_tro_display()})"
        )