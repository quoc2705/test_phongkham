"""Đồng bộ bản ghi nhắc lịch (1 ngày trước giờ khám) — dùng cho Celery gửi thông báo tài khoản + SMS."""
from datetime import timedelta

from django.utils import timezone

from .models import LichHen, NhacNhoLichHen


def dong_bo_nhac_cho_lich_hen(lich_hen: LichHen) -> None:
    """
    Xóa các nhắc đang chờ gửi và tạo lại một nhắc mới trùng mốc (ngay_gio_hen - 1 ngày).
    Không tạo nếu tắt nhắc, lịch đã kết thúc/hủy, hoặc mốc nhắc đã qua.
    """
    NhacNhoLichHen.objects.filter(lich_hen=lich_hen, trang_thai='CHO_GUI').delete()
    if not getattr(lich_hen, 'can_nhac_nho', True):
        return
    if lich_hen.trang_thai in ('HOAN_THANH', 'DA_HUY'):
        return
    thoi_gian_nhac = lich_hen.ngay_gio_hen - timedelta(days=1)
    if thoi_gian_nhac <= timezone.now():
        return
    noi_dung = (
        f"Nhắc: bạn có lịch {lich_hen.get_loai_lich_display()} "
        f"vào {lich_hen.ngay_gio_hen.strftime('%H:%M ngày %d/%m/%Y')}"
        f"{f' (mã {lich_hen.ma_lich_hen})' if lich_hen.ma_lich_hen else ''}."
    )
    NhacNhoLichHen.objects.create(
        lich_hen=lich_hen,
        loai_nhac='PUSH',
        thoi_gian_nhac=thoi_gian_nhac,
        noi_dung=noi_dung,
    )
