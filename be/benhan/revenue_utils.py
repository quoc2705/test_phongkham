"""Logic thống kê doanh thu đơn thuốc — dùng chung admin / đơn hàng."""
from django.db.models import Q

from phongkham.time_utils import (
    bounds_for_local_days,
    bounds_for_local_month,
    bounds_for_local_single_day,
)

# Đơn đã thu tiền: cờ hoặc trạng thái cuối (tránh mất dữ liệu khi chỉ cập nhật trang_thai)
DON_THUOC_TRANG_CO_DOANH = (
    'DA_THANH_TOAN',
    'DANG_XU_LY',
    'DA_XUAT_THUOC',
    'HOAN_THANH',
)


def don_thuoc_co_doanh_q():
    return Q(da_thanh_toan=True) | Q(trang_thai__in=DON_THUOC_TRANG_CO_DOANH)


def loc_don_thuoc_theo_ky(qs, tu_ngay=None, den_ngay=None):
    """
    Lọc đơn thuốc theo kỳ: ưu tiên ngày thanh toán, không có thì dùng ngày tạo.
    tu_ngay / den_ngay: chuỗi 'YYYY-MM-DD' hoặc date (có thể chỉ một trong hai).
    Dùng khoảng datetime theo TIME_ZONE (MySQL + USE_TZ: không dùng __date/__year).
    """
    if tu_ngay:
        start_lo, _ = bounds_for_local_days(tu_ngay, tu_ngay)
        qs = qs.filter(
            Q(ngay_thanh_toan__isnull=False, ngay_thanh_toan__gte=start_lo)
            | Q(ngay_thanh_toan__isnull=True, ngay_tao__gte=start_lo)
        )
    if den_ngay:
        _, end_hi = bounds_for_local_days(den_ngay, den_ngay)
        qs = qs.filter(
            Q(ngay_thanh_toan__isnull=False, ngay_thanh_toan__lte=end_hi)
            | Q(ngay_thanh_toan__isnull=True, ngay_tao__lte=end_hi)
        )
    return qs


def loc_don_thuoc_ngay(qs, day):
    """Một ngày (date): doanh thu ghi nhận theo ngày TT hoặc ngày tạo."""
    start, end = bounds_for_local_single_day(day)
    return qs.filter(
        Q(ngay_thanh_toan__isnull=False, ngay_thanh_toan__gte=start, ngay_thanh_toan__lte=end)
        | Q(ngay_thanh_toan__isnull=True, ngay_tao__gte=start, ngay_tao__lte=end)
    )


def loc_don_thuoc_thang(qs, year: int, month: int):
    """Một tháng dương lịch (theo múi giờ hệ thống)."""
    start, end = bounds_for_local_month(year, month)
    return qs.filter(
        Q(ngay_thanh_toan__isnull=False, ngay_thanh_toan__gte=start, ngay_thanh_toan__lte=end)
        | Q(ngay_thanh_toan__isnull=True, ngay_tao__gte=start, ngay_tao__lte=end)
    )
