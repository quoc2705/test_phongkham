# ---------------------------------------------------------------------------
# baocao/services.py (đặt trong cùng app, import vào views)
#
# FIX: Business logic tổng hợp dữ liệu được tách hoàn toàn ra khỏi Model.
# Service sử dụng ORM annotation để tránh N+1 query.
# ---------------------------------------------------------------------------
# Nội dung file services.py — để tham khảo cùng:

from django.db.models import Sum, Count, Q
from datetime import date, timedelta
from .models import BaoCao
 
 
class BaoCaoService:
 
    @staticmethod
    def tao_bao_cao_doanh_thu(thoi_gian_bat_dau, thoi_gian_ket_thuc, nguoi_tao=None):
        from donhang.models import DonHang, ChiTietDonHang
 
        # FIX: Dùng ORM annotation thay vì vòng lặp Python
        qs = DonHang.objects.filter(
            ngay_tao__date__range=[thoi_gian_bat_dau, thoi_gian_ket_thuc],
            trang_thai=DonHang.TrangThai.HOAN_THANH,
        )
 
        tong = qs.aggregate(
            tong_doanh_thu=Sum('tong_tien'),
            so_don=Count('id'),
        )
        tong_doanh_thu = float(tong['tong_doanh_thu'] or 0)
        so_don = tong['so_don'] or 0
 
        # Doanh thu theo loại đơn
        theo_loai = (
            qs.values('loai_don')
            .annotate(doanh_thu=Sum('tong_tien'))
            .order_by('loai_don')
        )
        doanh_thu_theo_loai = {r['loai_don']: float(r['doanh_thu'] or 0) for r in theo_loai}
 
        # Doanh thu theo ngày
        from django.db.models.functions import TruncDate
        theo_ngay = (
            qs.annotate(ngay=TruncDate('ngay_tao'))
            .values('ngay')
            .annotate(doanh_thu=Sum('tong_tien'))
            .order_by('ngay')
        )
        doanh_thu_theo_ngay = {
            r['ngay'].isoformat(): float(r['doanh_thu'] or 0) for r in theo_ngay
        }
 
        du_lieu = {
            'tong_doanh_thu': tong_doanh_thu,
            'so_don_hang': so_don,
            'don_hang_trung_binh': tong_doanh_thu / so_don if so_don > 0 else 0,
            'doanh_thu_theo_ngay': doanh_thu_theo_ngay,
            'doanh_thu_theo_loai': doanh_thu_theo_loai,
        }
 
        return BaoCao.objects.create(
            ten_bao_cao=f'Báo cáo doanh thu {thoi_gian_bat_dau} - {thoi_gian_ket_thuc}',
            loai=BaoCao.LoaiBaoCao.DOANH_THU,
            thoi_gian_bat_dau=thoi_gian_bat_dau,
            thoi_gian_ket_thuc=thoi_gian_ket_thuc,
            du_lieu=du_lieu,
            nguoi_tao=nguoi_tao,
        )
 
    @staticmethod
    def tao_bao_cao_benh_nhan(thoi_gian_bat_dau, thoi_gian_ket_thuc, nguoi_tao=None):
        from nguoidung.models import BenhNhan
        from benhan.models import HoSoBenhAn
 
        benh_nhan_moi = BenhNhan.objects.filter(
            nguoi_dung__ngay_tao__date__range=[thoi_gian_bat_dau, thoi_gian_ket_thuc]
        ).count()
 
        tong_benh_nhan = BenhNhan.objects.count()
 
        # FIX: dùng annotation thay vì vòng lặp
        ho_so_theo_ck = (
            HoSoBenhAn.objects.filter(
                ngay_kham__date__range=[thoi_gian_bat_dau, thoi_gian_ket_thuc]
            )
            .values('bac_si__chuyen_khoa')
            .annotate(so_luong=Count('id'))
        )
        chuyen_khoa_map = {
            r['bac_si__chuyen_khoa']: r['so_luong'] for r in ho_so_theo_ck
        }
 
        du_lieu = {
            'benh_nhan_moi': benh_nhan_moi,
            'tong_benh_nhan': tong_benh_nhan,
            'ho_so_theo_chuyen_khoa': chuyen_khoa_map,
            'ti_le_tang_truong': (
                benh_nhan_moi / tong_benh_nhan * 100 if tong_benh_nhan > 0 else 0
            ),
        }
 
        return BaoCao.objects.create(
            ten_bao_cao=f'Báo cáo bệnh nhân {thoi_gian_bat_dau} - {thoi_gian_ket_thuc}',
            loai=BaoCao.LoaiBaoCao.BENH_NHAN,
            thoi_gian_bat_dau=thoi_gian_bat_dau,
            thoi_gian_ket_thuc=thoi_gian_ket_thuc,
            du_lieu=du_lieu,
            nguoi_tao=nguoi_tao,
        )
 
    @staticmethod
    def tao_bao_cao_thuoc(thoi_gian_bat_dau, thoi_gian_ket_thuc, nguoi_tao=None):
        from thuoc.models import Thuoc, KhoThuoc
        from benhan.models import ChiTietDonThuoc
        from datetime import date, timedelta
 
        ngay_kiem_tra = date.today() + timedelta(days=30)
 
        # FIX: annotation thay vì vòng lặp
        ton_kho = (
            KhoThuoc.objects.filter(so_luong__gt=0)
            .values('thuoc__loai_thuoc')
            .annotate(tong=Sum('so_luong'))
        )
        ton_kho_map = {r['thuoc__loai_thuoc']: r['tong'] for r in ton_kho}
 
        thuoc_sap_het = KhoThuoc.objects.filter(
            han_su_dung__lte=ngay_kiem_tra,
            han_su_dung__gt=date.today(),
            so_luong__gt=0,
        ).count()
 
        thuoc_het_han = KhoThuoc.objects.filter(
            han_su_dung__lt=date.today(),
            so_luong__gt=0,
        ).count()
 
        thuoc_ban_chay = list(
            ChiTietDonThuoc.objects.filter(
                ho_so__ngay_kham__date__range=[thoi_gian_bat_dau, thoi_gian_ket_thuc]
            )
            .values('thuoc__ten_thuoc')
            .annotate(tong_so_luong=Sum('so_luong'))
            .order_by('-tong_so_luong')[:10]
        )
 
        du_lieu = {
            'tong_loai_thuoc': Thuoc.objects.count(),
            'ton_kho_theo_loai': ton_kho_map,
            'thuoc_sap_het_han': thuoc_sap_het,
            'thuoc_da_het_han': thuoc_het_han,
            'thuoc_ban_chay': thuoc_ban_chay,
        }
 
        return BaoCao.objects.create(
            ten_bao_cao=f'Báo cáo thuốc {thoi_gian_bat_dau} - {thoi_gian_ket_thuc}',
            loai=BaoCao.LoaiBaoCao.THUOC,
            thoi_gian_bat_dau=thoi_gian_bat_dau,
            thoi_gian_ket_thuc=thoi_gian_ket_thuc,
            du_lieu=du_lieu,
            nguoi_tao=nguoi_tao,
        )
