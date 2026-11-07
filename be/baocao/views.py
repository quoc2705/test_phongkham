from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import BaoCao, MauBaoCao
from .serializers import (
    BaoCaoSerializer, TaoBaoCaoSerializer,
    MauBaoCaoSerializer, ThongKeTongQuanSerializer
)
from nguoidung.permissions import LaNhanVien

class BaoCaoViewSet(viewsets.ModelViewSet):
    """ViewSet quản lý báo cáo"""
    queryset = BaoCao.objects.all()
    serializer_class = BaoCaoSerializer
    permission_classes = [IsAuthenticated, LaNhanVien]
    filter_backends = []
    
    def get_queryset(self):
        # Lọc theo loại báo cáo
        loai = self.request.query_params.get('loai')
        if loai:
            return self.queryset.filter(loai=loai)
        return self.queryset
    
    @action(detail=False, methods=['post'])
    def tao_bao_cao(self, request):
        """Tạo báo cáo mới"""
        serializer = TaoBaoCaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        loai_bao_cao = serializer.validated_data['loai_bao_cao']
        thoi_gian_bat_dau = serializer.validated_data['thoi_gian_bat_dau']
        thoi_gian_ket_thuc = serializer.validated_data['thoi_gian_ket_thuc']
        ten_bao_cao = serializer.validated_data.get('ten_bao_cao')
        
        # Tạo báo cáo theo loại
        if loai_bao_cao == 'DOANH_THU':
            bao_cao = BaoCao.tao_bao_cao_doanh_thu(
                thoi_gian_bat_dau, thoi_gian_ket_thuc, request.user
            )
        elif loai_bao_cao == 'BENH_NHAN':
            bao_cao = BaoCao.tao_bao_cao_benh_nhan(
                thoi_gian_bat_dau, thoi_gian_ket_thuc, request.user
            )
        elif loai_bao_cao == 'THUOC':
            bao_cao = BaoCao.tao_bao_cao_thuoc(
                thoi_gian_bat_dau, thoi_gian_ket_thuc, request.user
            )
        else:
            return Response({'error': 'Loại báo cáo không hỗ trợ'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        if ten_bao_cao:
            bao_cao.ten_bao_cao = ten_bao_cao
            bao_cao.save()
        
        return Response(
            BaoCaoSerializer(bao_cao).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def xuat_pdf(self, request, pk=None):
        """Xuất báo cáo ra PDF"""
        bao_cao = self.get_object()
        
        # TODO: Triển khai xuất PDF
        return Response({
            'message': 'Chức năng xuất PDF đang phát triển',
            'bao_cao': BaoCaoSerializer(bao_cao).data
        })
    
    @action(detail=True, methods=['get'])
    def xuat_excel(self, request, pk=None):
        """Xuất báo cáo ra Excel"""
        bao_cao = self.get_object()
        
        # TODO: Triển khai xuất Excel
        return Response({
            'message': 'Chức năng xuất Excel đang phát triển',
            'bao_cao': BaoCaoSerializer(bao_cao).data
        })
    
    @action(detail=False, methods=['get'])
    def thong_ke_tong_quan(self, request):
        """Thống kê tổng quan dashboard"""
        from nguoidung.models import BenhNhan
        from donhang.models import DonHang
        from lichhen.models import LichHen
        from thuoc.models import KhoThuoc
        from datetime import date
        
        # Tổng số bệnh nhân
        tong_benh_nhan = BenhNhan.objects.count()
        
        # Bệnh nhân mới trong tháng
        thang_nay = timezone.now().month
        nam_nay = timezone.now().year
        benh_nhan_moi_thang = BenhNhan.objects.filter(
            nguoi_dung__ngay_tao__month=thang_nay,
            nguoi_dung__ngay_tao__year=nam_nay
        ).count()
        
        # Doanh thu tháng
        doanh_thu_thang = DonHang.objects.filter(
            ngay_tao__month=thang_nay,
            ngay_tao__year=nam_nay,
            trang_thai='HOAN_THANH',
        ).aggregate(tong=Sum('tong_tien'))['tong'] or 0
        
        # Doanh thu ngày
        hom_nay = date.today()
        doanh_thu_ngay = DonHang.objects.filter(
            ngay_tao__date=hom_nay,
            trang_thai='HOAN_THANH',
        ).aggregate(tong=Sum('tong_tien'))['tong'] or 0
        
        # Lịch hẹn hôm nay
        so_lich_hen_hom_nay = LichHen.objects.filter(
            ngay_gio_hen__date=hom_nay,
            trang_thai__in=['DA_DAT', 'DA_XAC_NHAN']
        ).count()
        
        # Thuốc sắp hết hạn (30 ngày)
        ngay_kiem_tra = hom_nay + timedelta(days=30)
        thuoc_sap_het_han = KhoThuoc.objects.filter(
            han_su_dung__lte=ngay_kiem_tra,
            han_su_dung__gt=hom_nay,
            so_luong__gt=0
        ).count()
        
        data = {
            'tong_benh_nhan': tong_benh_nhan,
            'benh_nhan_moi_thang': benh_nhan_moi_thang,
            'tong_doanh_thu_thang': doanh_thu_thang,
            'doanh_thu_ngay': doanh_thu_ngay,
            'so_lich_hen_hom_nay': so_lich_hen_hom_nay,
            'thuoc_sap_het_han': thuoc_sap_het_han
        }
        
        serializer = ThongKeTongQuanSerializer(data=data)
        serializer.is_valid()
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def doanh_thu_theo_thang(self, request):
        """Thống kê doanh thu theo tháng"""
        from django.db.models.functions import TruncMonth
        from donhang.models import DonHang
        
        # Lấy doanh thu 12 tháng gần nhất
        now = timezone.now()
        start_date = now - timedelta(days=365)
        
        doanh_thu = DonHang.objects.filter(
            ngay_tao__gte=start_date,
            trang_thai='HOAN_THANH',
        ).annotate(
            thang=TruncMonth('ngay_tao')
        ).values('thang').annotate(
            tong_doanh_thu=Sum('tong_tien')
        ).order_by('thang')
        
        # Định dạng dữ liệu cho chart
        labels = []
        data = []
        
        for item in doanh_thu:
            labels.append(item['thang'].strftime('%m/%Y'))
            data.append(float(item['tong_doanh_thu']))
        
        return Response({
            'labels': labels,
            'data': data
        })
    
    @action(detail=False, methods=['get'])
    def top_thuoc_ban_chay(self, request):
        """Top 10 thuốc bán chạy"""
        from benhan.models import ChiTietDonThuoc
        from django.db.models import Sum
        
        # Lấy tháng hiện tại
        thang_nay = timezone.now().month
        nam_nay = timezone.now().year
        
        thuoc_ban_chay = ChiTietDonThuoc.objects.filter(
            ho_so__ngay_kham__month=thang_nay,
            ho_so__ngay_kham__year=nam_nay
        ).values(
            'thuoc__ten_thuoc',
            'thuoc__loai_thuoc'
        ).annotate(
            tong_so_luong=Sum('so_luong'),
            tong_tien=Sum('so_luong') * Sum('thuoc__gia_ban')
        ).order_by('-tong_so_luong')[:10]
        
        return Response(list(thuoc_ban_chay))

class MauBaoCaoViewSet(viewsets.ModelViewSet):
    """ViewSet quản lý mẫu báo cáo"""
    queryset = MauBaoCao.objects.all()
    serializer_class = MauBaoCaoSerializer
    permission_classes = [IsAuthenticated, LaNhanVien]
    
    @action(detail=True, methods=['post'])
    def su_dung_mau(self, request, pk=None):
        """Sử dụng mẫu báo cáo để tạo báo cáo mới"""
        mau_bao_cao = self.get_object()
        
        # Lấy tham số từ request hoặc dùng mặc định
        thoi_gian_bat_dau = request.data.get(
            'thoi_gian_bat_dau',
            (timezone.now() - timedelta(days=30)).date().isoformat()
        )
        thoi_gian_ket_thuc = request.data.get(
            'thoi_gian_ket_thuc',
            timezone.now().date().isoformat()
        )
        
        # Tạo báo cáo từ mẫu
        bao_cao = BaoCao.tao_bao_cao_doanh_thu(
            thoi_gian_bat_dau=thoi_gian_bat_dau,
            thoi_gian_ket_thuc=thoi_gian_ket_thuc,
            nguoi_tao=request.user
        )
        
        return Response(
            BaoCaoSerializer(bao_cao).data,
            status=status.HTTP_201_CREATED
        )