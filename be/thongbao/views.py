from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
from nguoidung.permissions import LaNhanVien
from donhang.models import DonHang
from lichhen.models import LichHen
from benhan.models import DonThuoc
from thuoc.models import KhoThuoc, KhoVaccine

class BaoCaoDoanhThuView(APIView):
    """Báo cáo doanh thu"""
    permission_classes = [IsAuthenticated, LaNhanVien]
    
    def get(self, request):
        # Lấy tham số
        tu_ngay = request.query_params.get('tu_ngay')
        den_ngay = request.query_params.get('den_ngay')
        
        # Mặc định: 30 ngày gần nhất
        if not tu_ngay or not den_ngay:
            den_ngay = timezone.now().date()
            tu_ngay = den_ngay - timedelta(days=30)
        else:
            tu_ngay = datetime.strptime(tu_ngay, '%Y-%m-%d').date()
            den_ngay = datetime.strptime(den_ngay, '%Y-%m-%d').date()
        
        # Doanh thu từ đơn hàng — chỉ đơn đã hoàn thành
        don_hang = DonHang.objects.filter(
            ngay_tao__date__range=[tu_ngay, den_ngay],
            trang_thai=DonHang.TrangThai.HOAN_THANH,
        )
        
        doanh_thu_online = don_hang.aggregate(
            tong=Sum('tong_tien')
        )['tong'] or 0
        
        # Doanh thu từ đơn thuốc tại quầy
        don_thuoc = DonThuoc.objects.filter(
            ngay_tao__date__range=[tu_ngay, den_ngay],
            da_thanh_toan=True
        )
        
        doanh_thu_quay = sum(don.tong_tien() for don in don_thuoc)
        
        # Tổng doanh thu
        tong_doanh_thu = doanh_thu_online + doanh_thu_quay
        
        # Số lượng đơn
        so_don_online = don_hang.count()
        so_don_quay = don_thuoc.count()
        
        # Doanh thu theo ngày
        doanh_thu_theo_ngay = []
        current_date = tu_ngay
        while current_date <= den_ngay:
            dh_ngay = don_hang.filter(ngay_tao__date=current_date).aggregate(
                tong=Sum('tong_tien')
            )['tong'] or 0
            
            dt_ngay = sum(
                don.tong_tien() for don in don_thuoc.filter(ngay_tao__date=current_date)
            )
            
            doanh_thu_theo_ngay.append({
                'ngay': current_date.isoformat(),
                'doanh_thu': dh_ngay + dt_ngay
            })
            
            current_date += timedelta(days=1)
        
        return Response({
            'tu_ngay': tu_ngay.isoformat(),
            'den_ngay': den_ngay.isoformat(),
            'tong_doanh_thu': tong_doanh_thu,
            'doanh_thu_online': doanh_thu_online,
            'doanh_thu_quay': doanh_thu_quay,
            'so_don_online': so_don_online,
            'so_don_quay': so_don_quay,
            'doanh_thu_theo_ngay': doanh_thu_theo_ngay
        })

class BaoCaoLichHenView(APIView):
    """Báo cáo lịch hẹn"""
    permission_classes = [IsAuthenticated, LaNhanVien]
    
    def get(self, request):
        tu_ngay = request.query_params.get('tu_ngay')
        den_ngay = request.query_params.get('den_ngay')
        
        if not tu_ngay or not den_ngay:
            den_ngay = timezone.now().date()
            tu_ngay = den_ngay - timedelta(days=30)
        else:
            tu_ngay = datetime.strptime(tu_ngay, '%Y-%m-%d').date()
            den_ngay = datetime.strptime(den_ngay, '%Y-%m-%d').date()
        
        lich_hen = LichHen.objects.filter(
            ngay_gio_hen__date__range=[tu_ngay, den_ngay]
        )
        
        # Thống kê theo trạng thái
        theo_trang_thai = lich_hen.values('trang_thai').annotate(
            so_luong=Count('id')
        )
        
        # Thống kê theo loại lịch
        theo_loai = lich_hen.values('loai_lich').annotate(
            so_luong=Count('id')
        )
        
        # Tỷ lệ hoàn thành
        tong_lich = lich_hen.count()
        hoan_thanh = lich_hen.filter(trang_thai='HOAN_THANH').count()
        ty_le_hoan_thanh = (hoan_thanh / tong_lich * 100) if tong_lich > 0 else 0
        
        # Vắng mặt
        vang_mat = lich_hen.filter(trang_thai='VANG_MAT').count()
        ty_le_vang_mat = (vang_mat / tong_lich * 100) if tong_lich > 0 else 0
        
        return Response({
            'tu_ngay': tu_ngay.isoformat(),
            'den_ngay': den_ngay.isoformat(),
            'tong_lich_hen': tong_lich,
            'hoan_thanh': hoan_thanh,
            'ty_le_hoan_thanh': round(ty_le_hoan_thanh, 2),
            'vang_mat': vang_mat,
            'ty_le_vang_mat': round(ty_le_vang_mat, 2),
            'theo_trang_thai': list(theo_trang_thai),
            'theo_loai': list(theo_loai)
        })

class BaoCaoTonKhoView(APIView):
    """Báo cáo tồn kho"""
    permission_classes = [IsAuthenticated, LaNhanVien]
    
    def get(self, request):
        # Tổng thuốc trong kho
        tong_thuoc = KhoThuoc.objects.aggregate(
            tong_loai=Count('thuoc', distinct=True),
            tong_so_luong=Sum('so_luong')
        )
        
        # Thuốc sắp hết hạn (30 ngày)
        from datetime import date
        ngay_kiem_tra = date.today() + timedelta(days=30)
        
        thuoc_sap_het_han = KhoThuoc.objects.filter(
            han_su_dung__lte=ngay_kiem_tra,
            han_su_dung__gt=date.today(),
            so_luong__gt=0
        ).count()
        
        # Thuốc đã hết hạn
        thuoc_het_han = KhoThuoc.objects.filter(
            han_su_dung__lt=date.today(),
            so_luong__gt=0
        ).count()
        
        # Thuốc sắp hết (dưới 10 đơn vị)
        thuoc_sap_het = KhoThuoc.objects.filter(
            so_luong__lt=10,
            so_luong__gt=0
        ).count()
        
        # Top 10 thuốc tồn kho nhiều nhất
        top_thuoc = KhoThuoc.objects.select_related('thuoc').order_by('-so_luong')[:10]
        
        top_thuoc_data = [{
            'thuoc': item.thuoc.ten_thuoc,
            'so_luong': item.so_luong,
            'don_vi': item.thuoc.don_vi,
            'han_su_dung': item.han_su_dung.isoformat()
        } for item in top_thuoc]
        
        # Vaccine
        tong_vaccine = KhoVaccine.objects.aggregate(
            tong_loai=Count('vaccine', distinct=True),
            tong_so_luong=Sum('so_luong')
        )
        
        return Response({
            'thuoc': {
                'tong_loai': tong_thuoc['tong_loai'] or 0,
                'tong_so_luong': tong_thuoc['tong_so_luong'] or 0,
                'sap_het_han': thuoc_sap_het_han,
                'het_han': thuoc_het_han,
                'sap_het': thuoc_sap_het,
                'top_10': top_thuoc_data
            },
            'vaccine': {
                'tong_loai': tong_vaccine['tong_loai'] or 0,
                'tong_so_luong': tong_vaccine['tong_so_luong'] or 0
            }
        })

class BaoCaoTongQuanView(APIView):
    """Báo cáo tổng quan hệ thống"""
    permission_classes = [IsAuthenticated, LaNhanVien]
    
    def get(self, request):
        from nguoidung.models import BenhNhan
        
        hom_nay = timezone.now().date()
        
        # Thống kê bệnh nhân
        tong_benh_nhan = BenhNhan.objects.count()
        benh_nhan_moi_thang = BenhNhan.objects.filter(
            nguoi_dung__ngay_tao__month=hom_nay.month,
            nguoi_dung__ngay_tao__year=hom_nay.year
        ).count()
        
        # Thống kê lịch hẹn hôm nay
        lich_hen_hom_nay = LichHen.objects.filter(
            ngay_gio_hen__date=hom_nay
        )
        
        lich_hen_stats = {
            'tong': lich_hen_hom_nay.count(),
            'cho_kham': lich_hen_hom_nay.filter(trang_thai__in=['DA_DAT', 'DA_XAC_NHAN']).count(),
            'dang_kham': lich_hen_hom_nay.filter(trang_thai='DANG_KHAM').count(),
            'hoan_thanh': lich_hen_hom_nay.filter(trang_thai='HOAN_THANH').count()
        }
        
        # Thống kê đơn hàng hôm nay — doanh thu chỉ đơn hoàn thành
        don_hang_hom_nay = DonHang.objects.filter(ngay_tao__date=hom_nay)
        doanh_thu_hom_nay = don_hang_hom_nay.filter(
            trang_thai=DonHang.TrangThai.HOAN_THANH,
        ).aggregate(tong=Sum('tong_tien'))['tong'] or 0
        
        # Đơn thuốc chờ thanh toán
        don_thuoc_cho = DonThuoc.objects.filter(
            trang_thai='CHO_THANH_TOAN'
        ).count()
        
        return Response({
            'benh_nhan': {
                'tong': tong_benh_nhan,
                'moi_thang_nay': benh_nhan_moi_thang
            },
            'lich_hen_hom_nay': lich_hen_stats,
            'don_hang_hom_nay': {
                'so_luong': don_hang_hom_nay.count(),
                'doanh_thu': doanh_thu_hom_nay
            },
            'don_thuoc_cho_thanh_toan': don_thuoc_cho
        })