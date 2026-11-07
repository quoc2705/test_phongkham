"""Báo cáo thống kê tài chính — dùng chung kế toán, admin và export."""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import Count, DateField, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Cast, Coalesce
from zoneinfo import ZoneInfo

from phongkham.time_utils import bounds_for_local_days


def _agg_period(rows: List[dict], key_len: int, label_key: str) -> List[dict]:
    bucket: Dict[str, dict] = {}
    for r in rows:
        ngay = str(r.get('ngay') or '')
        if len(ngay) < key_len:
            continue
        key = ngay[:key_len]
        if key not in bucket:
            bucket[key] = {
                label_key: key,
                'doanh_thu_don_hang': 0.0,
                'doanh_thu_don_thuoc': 0.0,
                'doanh_thu_tiem': 0.0,
                'tong_doanh_thu': 0.0,
            }
        for fld in ('doanh_thu_don_hang', 'doanh_thu_don_thuoc', 'doanh_thu_tiem', 'tong_doanh_thu'):
            bucket[key][fld] += float(r.get(fld) or 0)
    return [bucket[k] for k in sorted(bucket)]


def _row_tong(a: float, b: float, c: float) -> dict:
    tong = a + b + c
    return {
        'doanh_thu_don_hang': a,
        'doanh_thu_don_thuoc': b,
        'doanh_thu_tiem': c,
        'tong_doanh_thu': tong,
    }


def _day_val(maps: tuple, d: date) -> tuple:
    dh_ngay, dt_ngay, tc_ngay = maps
    return (
        dh_ngay.get(d, 0.0),
        dt_ngay.get(d, 0.0),
        tc_ngay.get(d, 0.0),
    )


def _build_theo_ngay_thang(maps: tuple, year: int, month: int) -> List[dict]:
    """Các ngày trong tháng (01 → hết tháng)."""
    last = calendar.monthrange(year, month)[1]
    rows: List[dict] = []
    for day in range(1, last + 1):
        d = date(year, month, day)
        a, b, c = _day_val(maps, d)
        row = _row_tong(a, b, c)
        row['ngay'] = d.isoformat()
        rows.append(row)
    return rows


def _build_theo_thang_nam(maps: tuple, year: int) -> List[dict]:
    """12 tháng trong năm."""
    dh_ngay, dt_ngay, tc_ngay = maps
    month_totals: Dict[int, dict] = {m: _row_tong(0, 0, 0) for m in range(1, 13)}

    for src, fld in ((dh_ngay, 'doanh_thu_don_hang'), (dt_ngay, 'doanh_thu_don_thuoc'), (tc_ngay, 'doanh_thu_tiem')):
        for d, v in src.items():
            if not d or d.year != year:
                continue
            month_totals[d.month][fld] += float(v or 0)
            month_totals[d.month]['tong_doanh_thu'] = (
                month_totals[d.month]['doanh_thu_don_hang']
                + month_totals[d.month]['doanh_thu_don_thuoc']
                + month_totals[d.month]['doanh_thu_tiem']
            )

    rows: List[dict] = []
    for m in range(1, 13):
        row = dict(month_totals[m])
        row['thang'] = f'{year}-{m:02d}'
        rows.append(row)
    return rows


def _build_theo_nam(maps: tuple, year_start: int, year_end: int) -> List[dict]:
    """So sánh doanh thu theo từng năm."""
    dh_ngay, dt_ngay, tc_ngay = maps
    year_totals: Dict[int, dict] = {
        y: _row_tong(0, 0, 0) for y in range(year_start, year_end + 1)
    }

    for src, fld in ((dh_ngay, 'doanh_thu_don_hang'), (dt_ngay, 'doanh_thu_don_thuoc'), (tc_ngay, 'doanh_thu_tiem')):
        for d, v in src.items():
            if not d:
                continue
            y = d.year if hasattr(d, 'year') else int(str(d)[:4])
            if y < year_start or y > year_end:
                continue
            if y not in year_totals:
                year_totals[y] = _row_tong(0, 0, 0)
            year_totals[y][fld] += float(v or 0)
            t = year_totals[y]
            t['tong_doanh_thu'] = (
                t['doanh_thu_don_hang'] + t['doanh_thu_don_thuoc'] + t['doanh_thu_tiem']
            )

    rows: List[dict] = []
    for y in range(year_start, year_end + 1):
        t = year_totals.get(y) or _row_tong(0, 0, 0)
        row = _row_tong(t['doanh_thu_don_hang'], t['doanh_thu_don_thuoc'], t['doanh_thu_tiem'])
        row['nam'] = str(y)
        rows.append(row)
    return rows


def _max_tong(rows: List[dict]) -> float:
    if not rows:
        return 0.0
    return max(float(r.get('tong_doanh_thu') or 0) for r in rows)


class BaoCaoTaiChinhService:
    @staticmethod
    def _parse_ymd(value: str) -> date:
        return datetime.strptime(str(value).strip()[:10], '%Y-%m-%d').date()

    @staticmethod
    def resolve_period(params) -> tuple[date, date, str]:
        """
        Xác định kỳ báo cáo từ query:
        - ky_loai=khoang + tu, den
        - ky_loai=ngay + ngay (hoặc tu=den)
        - ky_loai=thang + thang (YYYY-MM)
        - ky_loai=nam + nam (YYYY)
        """
        ky_loai = (params.get('ky_loai') or 'khoang').strip().lower()

        if ky_loai == 'ngay':
            ngay = params.get('ngay') or params.get('tu') or params.get('den')
            if not ngay:
                raise ValueError('Chọn ngày cụ thể (tham số ngay)')
            d = BaoCaoTaiChinhService._parse_ymd(ngay)
            return d, d, f'Ngày {d.strftime("%d/%m/%Y")}'

        if ky_loai == 'thang':
            thang = (params.get('thang') or '').strip()
            if not thang or len(thang) < 7:
                raise ValueError('Chọn tháng cụ thể (định dạng YYYY-MM)')
            y, m = int(thang[:4]), int(thang[5:7])
            last = calendar.monthrange(y, m)[1]
            tu_d = date(y, m, 1)
            den_d = date(y, m, last)
            return tu_d, den_d, f'Tháng {m:02d}/{y}'

        if ky_loai == 'nam':
            nam_raw = params.get('nam') or params.get('year')
            if not nam_raw:
                raise ValueError('Chọn năm cụ thể')
            y = int(str(nam_raw).strip()[:4])
            return date(y, 1, 1), date(y, 12, 31), f'Năm {y}'

        tu = params.get('tu') or params.get('tu_ngay')
        den = params.get('den') or params.get('den_ngay')
        if not tu or not den:
            raise ValueError('Chọn từ ngày và đến ngày')
        tu_d = BaoCaoTaiChinhService._parse_ymd(tu)
        den_d = BaoCaoTaiChinhService._parse_ymd(den)
        if tu_d > den_d:
            raise ValueError('Từ ngày không được lớn hơn đến ngày')
        return tu_d, den_d, f'{tu_d.strftime("%d/%m/%Y")} — {den_d.strftime("%d/%m/%Y")}'

    @staticmethod
    def parse_query_params(params) -> Dict[str, Any]:
        tu_d, den_d, ky_label = BaoCaoTaiChinhService.resolve_period(params)
        nhom = (params.get('nhom') or 'ngay').strip().lower()
        if nhom not in ('ngay', 'thang', 'nam', 'bac_si'):
            raise ValueError('nhom phải là ngay, thang, nam hoặc bac_si')
        return {
            'tu_d': tu_d,
            'den_d': den_d,
            'tu': tu_d.isoformat(),
            'den': den_d.isoformat(),
            'ky_bao_cao': ky_label,
            'nhom': nhom,
            'ma_bac_si': (params.get('ma_bac_si') or '').strip() or None,
        }

    @staticmethod
    def _fetch_day_maps(
        tu_d: date,
        den_d: date,
        ma_bac_si: Optional[str],
        _tz,
        _zero_dgn,
        _dec_out,
    ) -> tuple:
        """Gom doanh thu theo ngày (đơn / toa / tiêm) trong khoảng [tu_d, den_d]."""
        from benhan.revenue_utils import don_thuoc_co_doanh_q
        from donhang.models import DonHang
        from donhang.revenue_utils import loc_don_hang_theo_ky_doanh
        from benhan.models import DonThuoc, LichSuTiemChung

        tu_s = tu_d.isoformat()
        den_s = den_d.isoformat()
        start, end = bounds_for_local_days(tu_d, den_d)

        _tt_doanh_hang = (
            DonHang.TrangThai.HOAN_THANH,
            DonHang.TrangThai.DA_THANH_TOAN,
            DonHang.TrangThai.DANG_CHUAN_BI,
            DonHang.TrangThai.DANG_GIAO,
        )
        qs_don = loc_don_hang_theo_ky_doanh(
            DonHang.objects.filter(trang_thai__in=_tt_doanh_hang),
            tu_s,
            den_s,
        )
        don_thuoc_qs = DonThuoc.objects.filter(don_thuoc_co_doanh_q()).filter(
            Q(ngay_tao__gte=start, ngay_tao__lte=end)
            | Q(ngay_cap_nhat__gte=start, ngay_cap_nhat__lte=end)
        ).distinct()
        tiem_qs = LichSuTiemChung.objects.filter(
            trang_thai='DA_TIEM',
            ngay_tiem__gte=tu_d,
            ngay_tiem__lte=den_d,
        )
        if ma_bac_si:
            don_thuoc_qs = don_thuoc_qs.filter(bac_si__ma_bac_si=ma_bac_si)
            tiem_qs = tiem_qs.filter(nguoi_tiem__ma_bac_si=ma_bac_si)
            qs_don = qs_don.none()

        # MariaDB: TruncDate trả về NULL — dùng Cast; order_by() tránh DISTINCT + ORDER BY tách nhóm.
        _ngay_dh = Cast(
            Coalesce(F('thanh_toan__ngay_thanh_toan'), F('ngay_tao')),
            DateField(),
        )
        _ngay_dt = Cast(
            Coalesce(F('ngay_cap_nhat'), F('ngay_thanh_toan'), F('ngay_tao')),
            DateField(),
        )

        def _day_map(rows):
            out: Dict[date, float] = {}
            for row in rows:
                k = row.get('ngay_key')
                if not k:
                    continue
                out[k] = out.get(k, 0.0) + float(row.get('tien') or 0)
            return out

        dh_rows = (
            qs_don.order_by()
            .annotate(ngay_key=_ngay_dh)
            .values('ngay_key')
            .annotate(tien=Sum('tong_tien'))
        )
        dh_ngay = _day_map(dh_rows)

        dt_rows = (
            don_thuoc_qs.order_by()
            .annotate(ngay_key=_ngay_dt)
            .values('ngay_key')
            .annotate(tien=Sum('tong_tien'))
        )
        dt_ngay = _day_map(dt_rows)

        tc_rows = tiem_qs.values('ngay_tiem').annotate(
            tien=Sum(Coalesce(F('vaccine__gia_tiem'), _zero_dgn), output_field=_dec_out)
        )
        tc_ngay = {row['ngay_tiem']: float(row['tien'] or 0) for row in tc_rows if row['ngay_tiem']}

        return dh_ngay, dt_ngay, tc_ngay

    @staticmethod
    def thong_ke(
        tu_d,
        den_d,
        tu: Optional[str] = None,
        den: Optional[str] = None,
        nhom: str = 'ngay',
        ma_bac_si: Optional[str] = None,
        ky_bao_cao: Optional[str] = None,
    ) -> Dict[str, Any]:
        from benhan.models import ChiTietDonThuoc, DonThuoc, LichSuTiemChung
        from benhan.revenue_utils import don_thuoc_co_doanh_q
        from donhang.models import ChiTietDonHang, DonHang
        from donhang.revenue_utils import loc_don_hang_theo_ky_doanh
        from thuoc.models import PhieuNhapKho

        tu_s = tu or tu_d.isoformat()
        den_s = den or den_d.isoformat()
        start, end = bounds_for_local_days(tu_d, den_d)
        _tz = ZoneInfo(str(settings.TIME_ZONE))

        _dec_out = DecimalField(max_digits=22, decimal_places=2)
        _zero_dgn = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))

        _tt_doanh_hang = (
            DonHang.TrangThai.HOAN_THANH,
            DonHang.TrangThai.DA_THANH_TOAN,
            DonHang.TrangThai.DANG_CHUAN_BI,
            DonHang.TrangThai.DANG_GIAO,
        )
        qs_don_co_doanh = loc_don_hang_theo_ky_doanh(
            DonHang.objects.filter(trang_thai__in=_tt_doanh_hang),
            tu_s,
            den_s,
        )

        don_thuoc_qs = DonThuoc.objects.filter(don_thuoc_co_doanh_q()).filter(
            Q(ngay_tao__gte=start, ngay_tao__lte=end)
            | Q(ngay_cap_nhat__gte=start, ngay_cap_nhat__lte=end)
        ).distinct()

        tiem_qs = LichSuTiemChung.objects.filter(
            trang_thai='DA_TIEM',
            ngay_tiem__gte=tu_d,
            ngay_tiem__lte=den_d,
        )

        if ma_bac_si:
            don_thuoc_qs = don_thuoc_qs.filter(bac_si__ma_bac_si=ma_bac_si)
            tiem_qs = tiem_qs.filter(nguoi_tiem__ma_bac_si=ma_bac_si)
            qs_don_co_doanh = qs_don_co_doanh.none()

        _dh_tong_tien = float(qs_don_co_doanh.aggregate(s=Sum('tong_tien'))['s'] or 0)
        _dh_tu_chi_tiet = float(
            ChiTietDonHang.objects.filter(don_hang__in=qs_don_co_doanh).aggregate(
                s=Sum(
                    F('don_gia') * F('so_luong') - F('chiet_khau'),
                    output_field=_dec_out,
                )
            )['s']
            or 0
        )
        doanh_thu_don_hang = max(_dh_tong_tien, _dh_tu_chi_tiet)
        doanh_thu_don_thuoc = float(don_thuoc_qs.aggregate(s=Sum('tong_tien'))['s'] or 0)
        doanh_thu_tiem = float(
            tiem_qs.aggregate(
                s=Sum(Coalesce(F('vaccine__gia_tiem'), _zero_dgn), output_field=_dec_out)
            )['s']
            or 0
        )
        doanh_thu = doanh_thu_don_hang + doanh_thu_don_thuoc + doanh_thu_tiem

        gv_dh = ChiTietDonHang.objects.filter(don_hang__in=qs_don_co_doanh).aggregate(
            s=Sum(
                F('so_luong') * Coalesce(F('thuoc__don_gia_nhap'), _zero_dgn),
                output_field=_dec_out,
            )
        )['s'] or 0

        gv_dt = ChiTietDonThuoc.objects.filter(
            don_thuoc__in=don_thuoc_qs,
            la_thuoc_mua_ngoai=False,
            thuoc__isnull=False,
        ).aggregate(
            s=Sum(
                F('so_luong') * Coalesce(F('thuoc__don_gia_nhap'), _zero_dgn),
                output_field=_dec_out,
            )
        )['s'] or 0

        gv_tiem = tiem_qs.aggregate(
            s=Sum(Coalesce(F('vaccine__gia_nhap'), _zero_dgn), output_field=_dec_out)
        )['s'] or 0

        gia_von = float(gv_dh) + float(gv_dt) + float(gv_tiem)
        loi_nhuan = doanh_thu - gia_von

        phieu_cho_duyet = PhieuNhapKho.objects.filter(da_duyet_chi=False).count()

        # Chuỗi biểu đồ: ngày = từng ngày trong tháng; tháng = 12 tháng/năm; năm = so sánh nhiều năm
        chart_year = den_d.year
        chart_month = den_d.month
        chart_nam_end = chart_year
        chart_nam_start = chart_nam_end - 4 if chart_nam_end - tu_d.year < 1 else min(tu_d.year, den_d.year)
        chart_nam_start = max(2020, chart_nam_start)

        series_tu = date(chart_nam_start, 1, 1)
        series_den = date(chart_year, 12, 31)
        series_maps = BaoCaoTaiChinhService._fetch_day_maps(
            series_tu, series_den, ma_bac_si, _tz, _zero_dgn, _dec_out
        )

        theo_ngay = _build_theo_ngay_thang(series_maps, chart_year, chart_month)
        theo_thang = _build_theo_thang_nam(series_maps, chart_year)
        theo_nam = _build_theo_nam(series_maps, chart_nam_start, chart_nam_end)
        max_tong = max(_max_tong(theo_ngay), _max_tong(theo_thang), _max_tong(theo_nam), 0.0)

        theo_bac_si = BaoCaoTaiChinhService._theo_bac_si(
            qs_don_co_doanh, don_thuoc_qs, tiem_qs, _dec_out, _zero_dgn
        )

        _zero_dec = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        top_thuoc_don_hang = list(
            ChiTietDonHang.objects.filter(don_hang__in=qs_don_co_doanh)
            .values('thuoc__id', 'thuoc__ten_thuoc')
            .annotate(
                so_luong_ban=Sum('so_luong'),
                doanh_thu=Sum(F('don_gia') * F('so_luong') - F('chiet_khau'), output_field=_dec_out),
            )
            .order_by('-doanh_thu')[:10]
        )
        top_thuoc_toa = list(
            ChiTietDonThuoc.objects.filter(
                don_thuoc__in=don_thuoc_qs,
                la_thuoc_mua_ngoai=False,
                thuoc__isnull=False,
            )
            .values('thuoc__id', 'thuoc__ten_thuoc')
            .annotate(
                so_luong_ban=Sum('so_luong'),
                doanh_thu=Sum(
                    Coalesce(F('don_gia_tai_thoi_diem'), _zero_dec) * F('so_luong'),
                    output_field=_dec_out,
                ),
            )
            .order_by('-doanh_thu')[:10]
        )

        if not ky_bao_cao:
            ky_bao_cao = f'{tu_d.strftime("%d/%m/%Y")} — {den_d.strftime("%d/%m/%Y")}'

        bang_chi_tiet = {
            'ngay': theo_ngay,
            'thang': theo_thang,
            'nam': theo_nam,
            'bac_si': theo_bac_si,
        }.get(nhom, theo_ngay)

        return {
            'tu': tu_s,
            'den': den_s,
            'ky_bao_cao': ky_bao_cao,
            'nhom': nhom,
            'doanh_thu': doanh_thu,
            'doanh_thu_don_hang': doanh_thu_don_hang,
            'doanh_thu_don_thuoc': doanh_thu_don_thuoc,
            'doanh_thu_tiem': doanh_thu_tiem,
            'gia_von_uoc_tinh': gia_von,
            'gia_von_don_hang': float(gv_dh),
            'gia_von_don_thuoc': float(gv_dt),
            'gia_von_tiem': float(gv_tiem),
            'loi_nhuan_uoc_tinh': loi_nhuan,
            'so_don_hang': qs_don_co_doanh.count(),
            'so_don_thuoc': don_thuoc_qs.count(),
            'so_lan_tiem': tiem_qs.count(),
            'so_giao_dich': qs_don_co_doanh.count() + don_thuoc_qs.count() + tiem_qs.count(),
            'theo_ngay': theo_ngay,
            'theo_thang': theo_thang,
            'theo_nam': theo_nam,
            'theo_bac_si': theo_bac_si,
            'bang_chi_tiet': bang_chi_tiet,
            'bieu_do_max': max_tong,
            'chart_nam': chart_year,
            'chart_thang': f'{chart_month:02d}/{chart_year}',
            'chart_nam_tu': chart_nam_start,
            'chart_nam_den': chart_nam_end,
            'top_thuoc_don_hang': [
                {
                    'ten_thuoc': x.get('thuoc__ten_thuoc') or '',
                    'so_luong': x.get('so_luong_ban') or 0,
                    'doanh_thu': float(x.get('doanh_thu') or 0),
                }
                for x in top_thuoc_don_hang
            ],
            'top_thuoc_theo_toa': [
                {
                    'ten_thuoc': x.get('thuoc__ten_thuoc') or '',
                    'so_luong': x.get('so_luong_ban') or 0,
                    'doanh_thu': float(x.get('doanh_thu') or 0),
                }
                for x in top_thuoc_toa
            ],
            'phieu_nhap_cho_duyet_chi': phieu_cho_duyet,
            'tieu_chi_doanh_thu': 'HOAN_THANH_DA_THANH_TOAN + DON_THUOC_CO_DOANH + TIEM_CHUNG_DA_TIEM',
            'ghi_chu': (
                'Đơn hàng: Hoàn thành hoặc Đã thanh toán (đã thu). '
                'Đơn thuốc toa: đã thanh toán / hoàn thành. '
                'Tiêm chủng: các mũi đã tiêm (DA_TIEM). '
                'Giá vốn ước tính theo đơn giá nhập danh mục.'
            ),
        }

    @staticmethod
    def _theo_bac_si(qs_don, don_thuoc_qs, tiem_qs, _dec_out, _zero_dgn) -> List[dict]:
        bucket: Dict[str, dict] = defaultdict(
            lambda: {
                'ma_bac_si': '',
                'ten_bac_si': '',
                'doanh_thu_don_hang': 0.0,
                'doanh_thu_don_thuoc': 0.0,
                'doanh_thu_tiem': 0.0,
                'so_don_hang': 0,
                'so_don_thuoc': 0,
                'so_lan_tiem': 0,
                'tong_doanh_thu': 0.0,
            }
        )

        dh_tien = float(qs_don.aggregate(s=Sum('tong_tien'))['s'] or 0)
        dh_count = qs_don.count()
        if dh_tien or dh_count:
            key = '__quay_app__'
            bucket[key]['ma_bac_si'] = 'QUAY'
            bucket[key]['ten_bac_si'] = 'Quầy / App'
            bucket[key]['doanh_thu_don_hang'] = dh_tien
            bucket[key]['so_don_hang'] = dh_count

        dt_rows = (
            don_thuoc_qs.values('bac_si__ma_bac_si', 'bac_si__nguoi_dung__ho_ten')
            .annotate(
                tien=Sum('tong_tien'),
                so=Count('id'),
            )
        )
        for row in dt_rows:
            ma = row.get('bac_si__ma_bac_si') or 'KHONG_BS'
            ten = row.get('bac_si__nguoi_dung__ho_ten') or 'Không xác định'
            bucket[ma]['ma_bac_si'] = ma
            bucket[ma]['ten_bac_si'] = ten
            bucket[ma]['doanh_thu_don_thuoc'] = float(row.get('tien') or 0)
            bucket[ma]['so_don_thuoc'] = int(row.get('so') or 0)

        tc_rows = (
            tiem_qs.values('nguoi_tiem__ma_bac_si', 'nguoi_tiem__nguoi_dung__ho_ten')
            .annotate(
                tien=Sum(Coalesce(F('vaccine__gia_tiem'), _zero_dgn), output_field=_dec_out),
                so=Count('id'),
            )
        )
        for row in tc_rows:
            ma = row.get('nguoi_tiem__ma_bac_si') or 'KHONG_BS'
            ten = row.get('nguoi_tiem__nguoi_dung__ho_ten') or 'Không xác định'
            bucket[ma]['ma_bac_si'] = ma
            bucket[ma]['ten_bac_si'] = ten
            bucket[ma]['doanh_thu_tiem'] = float(row.get('tien') or 0)
            bucket[ma]['so_lan_tiem'] = int(row.get('so') or 0)

        out = []
        for item in bucket.values():
            item['tong_doanh_thu'] = (
                item['doanh_thu_don_hang']
                + item['doanh_thu_don_thuoc']
                + item['doanh_thu_tiem']
            )
            if item['tong_doanh_thu'] > 0 or item['so_don_hang'] or item['so_don_thuoc'] or item['so_lan_tiem']:
                out.append(item)
        out.sort(key=lambda x: -x['tong_doanh_thu'])
        return out
