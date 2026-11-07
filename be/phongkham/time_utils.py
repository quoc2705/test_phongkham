"""
Khoảng thời gian theo múi giờ Django (TIME_ZONE) — tránh lỗi MySQL + USE_TZ:
filter field__date / __year / __month trên DateTimeField có thể trả về 0 dòng.
Dùng __gte/__lte với datetime có tz (đầu ngày → cuối ngày).
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time
from typing import Optional, Tuple, Union

import zoneinfo
from django.conf import settings


def _local_tz():
    return zoneinfo.ZoneInfo(str(settings.TIME_ZONE))


def _as_date(d: Union[date, str]) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    s = str(d).strip()[:10]
    y, m, day = map(int, s.split('-'))
    return date(y, m, day)


def bounds_for_local_days(tu_ngay: Union[date, str], den_ngay: Union[date, str]) -> Tuple[datetime, datetime]:
    """Đầu ngày tu → cuối ngày den (Asia/Ho_Chi_Minh)."""
    tz = _local_tz()
    a = _as_date(tu_ngay)
    b = _as_date(den_ngay)
    start = datetime.combine(a, time.min, tzinfo=tz)
    end = datetime.combine(b, time.max, tzinfo=tz)
    return start, end


def bounds_for_local_single_day(day: Union[date, str]) -> Tuple[datetime, datetime]:
    d = _as_date(day)
    return bounds_for_local_days(d, d)


def bounds_for_local_month(year: int, month: int) -> Tuple[datetime, datetime]:
    last = calendar.monthrange(year, month)[1]
    return bounds_for_local_days(date(year, month, 1), date(year, month, last))
