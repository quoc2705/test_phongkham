"""Lọc đơn hàng theo ngày ghi nhận doanh thu (thanh toán) thay vì chỉ ngày tạo đơn."""
from django.db.models import Q

from phongkham.time_utils import bounds_for_local_days, bounds_for_local_month, bounds_for_local_single_day


def loc_don_hang_theo_ky_doanh(qs, tu_ngay=None, den_ngay=None):
    """
    Đơn thuộc kỳ báo cáo: ưu tiên ngày thanh toán (bản ghi ThanhToan),
    không có thanh toán thì dùng ngày tạo đơn (đơn cũ / dữ liệu thiếu TT).
    MySQL + USE_TZ: dùng __gte/__lte với datetime có timezone, không dùng __date.
    """
    if tu_ngay:
        start_lo, _ = bounds_for_local_days(tu_ngay, tu_ngay)
        qs = qs.filter(
            Q(thanh_toan__ngay_thanh_toan__gte=start_lo)
            | Q(thanh_toan__isnull=True, ngay_tao__gte=start_lo)
        )
    if den_ngay:
        _, end_hi = bounds_for_local_days(den_ngay, den_ngay)
        qs = qs.filter(
            Q(thanh_toan__ngay_thanh_toan__lte=end_hi)
            | Q(thanh_toan__isnull=True, ngay_tao__lte=end_hi)
        )
    return qs.distinct()


def loc_don_hang_hom_nay(qs, today):
    """Doanh thu trong ngày (theo ngày thanh toán hoặc ngày tạo nếu chưa có TT)."""
    start, end = bounds_for_local_single_day(today)
    return qs.filter(
        Q(thanh_toan__ngay_thanh_toan__gte=start, thanh_toan__ngay_thanh_toan__lte=end)
        | Q(thanh_toan__isnull=True, ngay_tao__gte=start, ngay_tao__lte=end)
    ).distinct()


def loc_don_hang_thang(qs, year: int, month: int):
    """Một tháng dương lịch theo ngày thanh toán hoặc ngày tạo."""
    start, end = bounds_for_local_month(year, month)
    return qs.filter(
        Q(thanh_toan__ngay_thanh_toan__gte=start, thanh_toan__ngay_thanh_toan__lte=end)
        | Q(thanh_toan__isnull=True, ngay_tao__gte=start, ngay_tao__lte=end)
    ).distinct()
