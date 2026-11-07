from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg, F, Value
from django.utils.dateparse import parse_date
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import date, timedelta, datetime
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *
from nguoidung.roles import la_nhan_vien_ban_thuoc, la_nhan_vien_quay_ban_thuoc
import logging
import json

logger = logging.getLogger(__name__)

def _loc_theo_quyen_benh_nhan(queryset, user, benh_nhan_field='benh_nhan'):
    """Giới hạn dữ liệu theo quyền truy cập của user hiện tại."""
    if user.is_superuser or user.vai_tro in ['ADMIN', 'NHAN_VIEN']:
        return queryset
    # Bác sĩ: xem/tìm hồ sơ trong phòng khám (không chỉ lần khám do chính mình tạo),
    # để tra cứu theo tên, mã BN, mở hồ sơ phục vụ khám.
    if user.vai_tro == 'BAC_SI' and hasattr(user, 'bac_si'):
        return queryset
    if user.vai_tro == 'BENH_NHAN' and hasattr(user, 'benh_nhan'):
        return queryset.filter(**{benh_nhan_field: user.benh_nhan})
    return queryset.none()


def _quyen_chinh_sua_ho_so(user, ho_so):
    if user.is_superuser or getattr(user, 'vai_tro', None) in ['ADMIN', 'NHAN_VIEN']:
        return True
    # Bác sĩ đăng nhập: NguoiDung không có bac_si_id; BacSi.pk == nguoi_dung_id
    if getattr(user, 'vai_tro', None) == 'BAC_SI' and hasattr(user, 'bac_si'):
        return True
    return False


def _loc_ho_so_theo_ngay_kham(queryset, tu_ngay=None, den_ngay=None):
    """Lọc ngay_kham theo TIME_ZONE — không dùng __date trên DateTimeField (MySQL + USE_TZ hay trả 0 dòng)."""
    from phongkham.time_utils import bounds_for_local_days

    tu = (str(tu_ngay).strip()[:10] if tu_ngay else '')
    den = (str(den_ngay).strip()[:10] if den_ngay else '')
    if not tu and not den:
        return queryset
    try:
        if tu and den:
            lo, hi = bounds_for_local_days(tu, den)
            return queryset.filter(ngay_kham__gte=lo, ngay_kham__lte=hi)
        if tu:
            lo, _ = bounds_for_local_days(tu, tu)
            return queryset.filter(ngay_kham__gte=lo)
        _, hi = bounds_for_local_days(den, den)
        return queryset.filter(ngay_kham__lte=hi)
    except (ValueError, TypeError):
        return queryset.none()


class HoSoBenhAnPagination(PageNumberPagination):
    """Cho phép ?page_size= khi lọc theo bệnh nhân (bác sĩ xem nhiều lần khám)."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ==================== VIEWSETS CHO HỒ SƠ BỆNH ÁN ====================

class HoSoBenhAnViewSet(viewsets.ModelViewSet):
    """API cho hồ sơ bệnh án"""
    pagination_class = HoSoBenhAnPagination
    queryset = HoSoBenhAn.objects.select_related(
        'benh_nhan', 'benh_nhan__nguoi_dung', 'bac_si', 'bac_si__nguoi_dung'
    ).prefetch_related(
        'chan_doan', 'don_thuoc', 'lich_hen', 'theo_doi'
    ).all()
    serializer_class = HoSoBenhAnSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['trang_thai', 'loai_kham', 'bac_si', 'benh_nhan']
    search_fields = ['ma_hs', 'benh_nhan__nguoi_dung__ho_ten', 'benh_nhan__ma_benh_nhan', 'trieu_chung']
    ordering_fields = ['ngay_kham', 'ngay_tao', 'benh_nhan__nguoi_dung__ho_ten']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HoSoBenhAnChiTietSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return HoSoBenhAnCreateUpdateSerializer
        return HoSoBenhAnSerializer

    def get_queryset(self):
        """Custom queryset với filter đặc biệt"""
        queryset = _loc_theo_quyen_benh_nhan(super().get_queryset(), self.request.user)
        
        # Filter theo ngày khám (datetime theo múi giờ phòng khám)
        tu_ngay = self.request.query_params.get('tu_ngay')
        den_ngay = self.request.query_params.get('den_ngay')
        queryset = _loc_ho_so_theo_ngay_kham(queryset, tu_ngay, den_ngay)
        
        # Filter theo bệnh nhân (UUID khóa benh_nhan)
        benh_nhan_id = self.request.query_params.get('benh_nhan')
        if benh_nhan_id:
            queryset = queryset.filter(benh_nhan_id=benh_nhan_id)

        # Filter theo mã bệnh nhân (vd. BN2024001)
        ma_bn = self.request.query_params.get('ma_benh_nhan')
        if ma_bn:
            queryset = queryset.filter(
                benh_nhan__ma_benh_nhan__iexact=ma_bn.strip()
            )

        # Tìm theo mã BN / họ tên / SĐT — không dùng UUID (bỏ qua nếu chuỗi giống UUID)
        tim = (self.request.query_params.get('tim_kiem') or '').strip()
        if tim:
            uuid_like = len(tim) == 36 and tim.count('-') == 4
            if not uuid_like:
                queryset = queryset.filter(
                    Q(benh_nhan__ma_benh_nhan__icontains=tim)
                    | Q(benh_nhan__nguoi_dung__ho_ten__icontains=tim)
                    | Q(benh_nhan__nguoi_dung__so_dien_thoai__icontains=tim)
                )

        return queryset

    @action(detail=False, methods=['get'])
    def thong_ke(self, request):
        """Thống kê tổng quan hồ sơ bệnh án"""
        today = date.today()
        first_day_of_month = today.replace(day=1)
        
        # Thống kê theo trạng thái
        thong_ke_trang_thai = HoSoBenhAn.objects.values('trang_thai').annotate(
            so_luong=Count('id')
        )
        
        # Thống kê theo loại khám
        thong_ke_loai_kham = HoSoBenhAn.objects.values('loai_kham').annotate(
            so_luong=Count('id')
        )
        
        # Thống kê theo tháng
        thong_ke_thang = HoSoBenhAn.objects.filter(
            ngay_kham__date__gte=first_day_of_month
        ).values('ngay_kham__date').annotate(
            so_luong=Count('id')
        ).order_by('ngay_kham__date')
        
        # Top bệnh nhân khám nhiều
        top_benh_nhan = HoSoBenhAn.objects.values(
            'benh_nhan__ma_benh_nhan', 'benh_nhan__nguoi_dung__ho_ten'
        ).annotate(
            so_lan=Count('id')
        ).order_by('-so_lan')[:10]
        
        return Response({
            'tong_ho_so': self.get_queryset().count(),
            'thong_ke_trang_thai': thong_ke_trang_thai,
            'thong_ke_loai_kham': thong_ke_loai_kham,
            'thong_ke_thang': thong_ke_thang,
            'top_benh_nhan': top_benh_nhan
        })

    @action(detail=True, methods=['get'])
    def lich_su_dieu_tri(self, request, pk=None):
        """Xem lịch sử điều trị chi tiết"""
        ho_so = self.get_object()
        
        data = {
            'ho_so': HoSoBenhAnSerializer(ho_so).data,
            'chan_doan': ChanDoanSerializer(ho_so.chan_doan).data if hasattr(ho_so, 'chan_doan') else None,
            'don_thuoc': DonThuocSerializer(ho_so.don_thuoc.all(), many=True).data,
            'lich_hen': LichHenTaiKhamSerializer(ho_so.lich_hen.all(), many=True).data,
            'theo_doi': TheoDoiDieuTriSerializer(ho_so.theo_doi.all(), many=True).data
        }
        
        return Response(data)

    @action(detail=True, methods=['post'])
    def cap_nhat_trang_thai(self, request, pk=None):
        """Cập nhật trạng thái hồ sơ"""
        ho_so = self.get_object()
        trang_thai_moi = request.data.get('trang_thai')
        ghi_chu = request.data.get('ghi_chu', '')
        
        if trang_thai_moi not in dict(HoSoBenhAn.TRANG_THAI_CHOICES):
            return Response(
                {'error': 'Trạng thái không hợp lệ'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ho_so.trang_thai = trang_thai_moi
        if ghi_chu:
            ho_so.ghi_chu = f"{ho_so.ghi_chu}\n[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Cập nhật trạng thái: {ghi_chu}"
        ho_so.save()
        
        return Response({
            'message': 'Cập nhật trạng thái thành công',
            'trang_thai': ho_so.trang_thai
        })


    @action(detail=True, methods=['post'])
    def nhap_chan_doan(self, request, pk=None):
        ho_so = self.get_object()
        if not _quyen_chinh_sua_ho_so(request.user, ho_so):
            return Response({'error': 'Khong co quyen'}, status=status.HTTP_403_FORBIDDEN)
        payload = (
            request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        )
        # Cập nhật triệu chứng / khám lâm sàng trên hồ sơ lần khám hiện tại
        trieu_chung = payload.pop('trieu_chung', None)
        ket_qua_kham_lam_sang = payload.pop('ket_qua_kham_lam_sang', None)
        upd_hs = []
        if trieu_chung is not None:
            ho_so.trieu_chung = trieu_chung
            upd_hs.append('trieu_chung')
        if ket_qua_kham_lam_sang is not None:
            ho_so.ket_qua_kham_lam_sang = ket_qua_kham_lam_sang
            upd_hs.append('ket_qua_kham_lam_sang')
        if upd_hs:
            upd_hs.append('ngay_cap_nhat')
            ho_so.save(update_fields=upd_hs)

        payload['ho_so'] = str(ho_so.id)
        if hasattr(request.user, 'bac_si'):
            # BacSi PK = nguoi_dung_id — không có attribute .id
            payload['bac_si_chan_doan'] = str(request.user.bac_si.pk)
        if getattr(ho_so, 'chan_doan', None):
            ser = ChanDoanCreateUpdateSerializer(ho_so.chan_doan, data=payload, partial=True)
        else:
            ser = ChanDoanCreateUpdateSerializer(data=payload)
        if ser.is_valid():
            cd = ser.save()
            out = ChanDoanSerializer(cd).data
            out['ho_so'] = HoSoBenhAnSerializer(ho_so).data
            return Response(out, status=status.HTTP_200_OK)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def tao_don_thuoc(self, request, pk=None):
        ho_so = self.get_object()
        if not _quyen_chinh_sua_ho_so(request.user, ho_so):
            return Response({'error': 'Khong co quyen'}, status=status.HTTP_403_FORBIDDEN)
        if not hasattr(request.user, 'bac_si'):
            return Response({'error': 'Chi bac si ke don'}, status=status.HTTP_403_FORBIDDEN)
        body = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        body['ho_so'] = str(ho_so.id)
        body['benh_nhan'] = str(ho_so.benh_nhan_id)
        body['bac_si'] = str(request.user.bac_si.pk)
        ser = DonThuocCreateSerializer(data=body)
        if ser.is_valid():
            don = ser.save()
            don.tinh_tong_tien()
            return Response(DonThuocSerializer(don).data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def chi_dinh_tiem(self, request, pk=None):
        ho_so = self.get_object()
        if not _quyen_chinh_sua_ho_so(request.user, ho_so):
            return Response({'error': 'Khong co quyen'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        # FE cũ có thể gửi mã vaccine (VD: VC20260001) thay vì UUID.
        vaccine_raw = (data.get('vaccine') or '').strip() if isinstance(data.get('vaccine'), str) else data.get('vaccine')
        if isinstance(vaccine_raw, str) and vaccine_raw:
            uuid_like = len(vaccine_raw) == 36 and vaccine_raw.count('-') == 4
            if not uuid_like:
                from thuoc.models import Vaccine
                vc = Vaccine.objects.filter(ma_vaccine__iexact=vaccine_raw).first()
                if vc is None:
                    return Response(
                        {'vaccine': [f'Không tìm thấy vaccine với mã "{vaccine_raw}"']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                data['vaccine'] = str(vc.pk)
        data['benh_nhan'] = str(ho_so.benh_nhan_id)
        if hasattr(request.user, 'bac_si'):
            data['nguoi_tiem'] = str(request.user.bac_si.pk)
        data.setdefault('trang_thai', 'HEN_TIEM')
        ser = LichSuTiemChungCreateSerializer(data=data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        trang_thai = ser.validated_data.get('trang_thai') or 'HEN_TIEM'
        if trang_thai == 'DA_TIEM':
            from thuoc.stock import VaccineHetTonError, tru_ton_vaccine_mot_lieu

            lo_raw = (request.data.get('lo_vaccine') or data.get('lo_vaccine') or '').strip()
            han_raw = request.data.get('han_su_dung') or data.get('han_su_dung')
            han_parsed = parse_date(han_raw) if han_raw else None
            try:
                with transaction.atomic():
                    lot = tru_ton_vaccine_mot_lieu(
                        ser.validated_data['vaccine'],
                        lo_sx=lo_raw or None,
                        han_su_dung=han_parsed,
                    )
                    obj = ser.save(lo_vaccine=lot['lo_sx'])
            except VaccineHetTonError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            obj = ser.save()
        return Response(LichSuTiemChungSerializer(obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def chi_dinh_xet_nghiem(self, request, pk=None):
        ho_so = self.get_object()
        if not _quyen_chinh_sua_ho_so(request.user, ho_so):
            return Response({'error': 'Khong co quyen'}, status=status.HTTP_403_FORBIDDEN)
        noi_dung = (request.data.get('noi_dung') or '').strip()
        if not noi_dung:
            return Response({'error': 'Thieu noi_dung'}, status=status.HTTP_400_BAD_REQUEST)
        ngay_du_kien = request.data.get('ngay_du_kien')
        parsed = parse_date(ngay_du_kien) if ngay_du_kien else None
        chi_so = {
            'loai': 'CHI_DINH_XET_NGHIEM',
            'mo_ta': noi_dung,
            'ngay_du_kien': parsed.isoformat() if parsed else None,
        }
        bac_si = request.user.bac_si if hasattr(request.user, 'bac_si') else None
        td = TheoDoiDieuTri.objects.create(
            ho_so=ho_so,
            bac_si=bac_si,
            dien_bien='Chi dinh xet nghiem',
            yeu_cau=noi_dung,
            chi_so_sinh_ton=chi_so,
        )
        return Response(TheoDoiDieuTriSerializer(td).data, status=status.HTTP_201_CREATED)

# ==================== VIEWSETS CHO CHẨN ĐOÁN ====================

class ChanDoanViewSet(viewsets.ModelViewSet):
    """API cho chẩn đoán"""
    queryset = ChanDoan.objects.select_related('ho_so', 'bac_si_chan_doan').all()
    serializer_class = ChanDoanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['loai_benh', 'muc_do', 'bac_si_chan_doan']
    search_fields = ['ma_icd10', 'ten_benh', 'mo_ta']
    ordering_fields = ['ngay_chan_doan']

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_superuser or getattr(u, 'vai_tro', None) in ['ADMIN', 'NHAN_VIEN']:
            return qs
        if getattr(u, 'vai_tro', None) == 'BAC_SI' and hasattr(u, 'bac_si'):
            return qs.filter(ho_so__bac_si=u.bac_si)
        if getattr(u, 'vai_tro', None) == 'BENH_NHAN' and hasattr(u, 'benh_nhan'):
            return qs.filter(ho_so__benh_nhan=u.benh_nhan)
        return qs.none()

    @action(detail=False, methods=['get'])
    def thong_ke_icd10(self, request):
        """Thống kê theo mã ICD-10"""
        thong_ke = ChanDoan.objects.values(
            'ma_icd10', 'ten_benh'
        ).annotate(
            so_luong=Count('id')
        ).order_by('-so_luong')[:20]
        
        return Response(thong_ke)

    @action(detail=False, methods=['get'])
    def thong_ke_muc_do(self, request):
        """Thống kê theo mức độ bệnh"""
        thong_ke = ChanDoan.objects.values('muc_do').annotate(
            so_luong=Count('id')
        )
        
        return Response(thong_ke)

# ==================== VIEWSETS CHO ĐƠN THUỐC ====================

class DonThuocViewSet(viewsets.ModelViewSet):
    """API cho đơn thuốc"""
    queryset = DonThuoc.objects.select_related(
        'ho_so', 'bac_si', 'benh_nhan'
    ).prefetch_related(
        'chi_tiet_don_thuoc__thuoc'
    ).all()
    serializer_class = DonThuocSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['trang_thai', 'da_thanh_toan', 'bac_si', 'benh_nhan', 'phuong_thuc_thanh_toan']
    search_fields = ['ma_don', 'benh_nhan__nguoi_dung__ho_ten', 'benh_nhan__ma_benh_nhan']
    ordering_fields = ['ngay_tao', 'tong_tien']

    def get_queryset(self):
        qs = super().get_queryset()
        if la_nhan_vien_quay_ban_thuoc(self.request.user):
            queryset = qs.filter(trang_thai='HOAN_THANH')
        else:
            queryset = _loc_theo_quyen_benh_nhan(qs, self.request.user)
        
        # Filter theo khoảng thời gian (datetime theo TIME_ZONE)
        tu_ngay = self.request.query_params.get('tu_ngay') or self.request.query_params.get('tu')
        den_ngay = self.request.query_params.get('den_ngay') or self.request.query_params.get('den')
        if tu_ngay or den_ngay:
            from datetime import datetime as _dt
            from phongkham.time_utils import bounds_for_local_days

            def _pd(s):
                return _dt.strptime(str(s)[:10], '%Y-%m-%d').date()

            try:
                if tu_ngay and den_ngay:
                    lo, hi = bounds_for_local_days(_pd(tu_ngay), _pd(den_ngay))
                    queryset = queryset.filter(ngay_tao__gte=lo, ngay_tao__lte=hi)
                elif tu_ngay:
                    lo, _ = bounds_for_local_days(_pd(tu_ngay), _pd(tu_ngay))
                    queryset = queryset.filter(ngay_tao__gte=lo)
                else:
                    _, hi = bounds_for_local_days(_pd(den_ngay), _pd(den_ngay))
                    queryset = queryset.filter(ngay_tao__lte=hi)
            except ValueError:
                queryset = queryset.none()
        
        # Filter theo tổng tiền
        tu_tien = self.request.query_params.get('tu_tien')
        den_tien = self.request.query_params.get('den_tien')
        if tu_tien:
            queryset = queryset.filter(tong_tien__gte=tu_tien)
        if den_tien:
            queryset = queryset.filter(tong_tien__lte=den_tien)
        
        return queryset

    def perform_create(self, serializer):
        """Tạo đơn thuốc mới"""
        don_thuoc = serializer.save()
        don_thuoc.tinh_tong_tien()

    @action(detail=False, methods=['get'], url_path='theo-ma')
    def theo_ma(self, request):
        """Nhân viên quầy: tra cứu toa theo mã — kèm tồn kho từng dòng thuốc trong hệ thống."""
        ma_don = (request.query_params.get('ma_don') or '').strip()
        if not ma_don:
            return Response({'error': 'Thiếu tham số ma_don'}, status=status.HTTP_400_BAD_REQUEST)
        if not la_nhan_vien_ban_thuoc(request.user):
            return Response({'error': 'Chỉ nhân viên bán thuốc (chức vụ Bán thuốc) mới tra cứu được toa'}, status=status.HTTP_403_FORBIDDEN)
        try:
            don = DonThuoc.objects.select_related('benh_nhan__nguoi_dung', 'bac_si__nguoi_dung').prefetch_related(
                'chi_tiet_don_thuoc__thuoc__don_vi'
            ).get(ma_don__iexact=ma_don)
        except DonThuoc.DoesNotExist:
            return Response({'error': 'Không tìm thấy toa'}, status=status.HTTP_404_NOT_FOUND)
        base = DonThuocSerializer(don).data
        chi_enriched = []
        for ct in don.chi_tiet_don_thuoc.all():
            row = ChiTietDonThuocSerializer(ct).data
            if ct.la_thuoc_mua_ngoai or not ct.thuoc_id:
                row['ton_kho'] = 0
                row['duoc_ban_tai_quay'] = False
                row['ghi_chu_loai'] = 'Mua ngoài — không bán tại quầy'
            else:
                row['ton_kho'] = int(ct.thuoc.ton_kho())
                row['duoc_ban_tai_quay'] = True
                row['ghi_chu_loai'] = 'Trong kho'
            chi_enriched.append(row)
        base['chi_tiet'] = chi_enriched
        return Response(base)

    @action(detail=False, methods=['get'], url_path='toa-da-hoan-thanh')
    def toa_da_hoan_thanh(self, request):
        """Nhân viên quầy: danh sách toa đã bán xong tại quầy (kèm mã đơn hàng để in lại)."""
        if not la_nhan_vien_quay_ban_thuoc(self.request.user):
            return Response(
                {'error': 'Chỉ nhân viên bán thuốc xem được danh sách này'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = (
            DonThuoc.objects.filter(trang_thai='HOAN_THANH')
            .select_related('benh_nhan__nguoi_dung')
            .order_by('-ngay_cap_nhat')[:300]
        )
        out = []
        for dt in qs:
            dh = (
                dt.don_hang_ban.filter(loai_don='TAI_QUAY', trang_thai='DA_THANH_TOAN')
                .select_related('thanh_toan')
                .order_by('-ngay_tao')
                .first()
            )
            pt = ''
            if dh and hasattr(dh, 'thanh_toan'):
                pt = dh.thanh_toan.get_phuong_thuc_display()
            out.append(
                {
                    'loai': 'THEO_TOA',
                    'id': str(dt.id),
                    'ma_don': dt.ma_don,
                    'ma_benh_nhan': dt.benh_nhan.ma_benh_nhan,
                    'ten_benh_nhan': dt.benh_nhan.nguoi_dung.ho_ten,
                    'ngay_cap_nhat': dt.ngay_cap_nhat.isoformat(),
                    'don_hang_id': str(dh.id) if dh else None,
                    'ma_don_hang': dh.ma_don_hang if dh else None,
                    'phuong_thuc_thanh_toan': pt,
                }
            )
        return Response(out)

    @action(detail=True, methods=['post'])
    def them_thuoc(self, request, pk=None):
        """Thêm thuốc vào đơn"""
        don_thuoc = self.get_object()
        serializer = ChiTietDonThuocSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(don_thuoc=don_thuoc)
            don_thuoc.tinh_tong_tien()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def thanh_toan(self, request, pk=None):
        """Thanh toán đơn thuốc"""
        don_thuoc = self.get_object()
        
        if don_thuoc.da_thanh_toan:
            return Response(
                {'error': 'Đơn thuốc đã được thanh toán'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phuong_thuc = request.data.get('phuong_thuc_thanh_toan')
        ma_giao_dich = request.data.get('ma_giao_dich', '')
        ma_bao_hiem = request.data.get('ma_bao_hiem', '')
        ty_le_bao_hiem = request.data.get('ty_le_bao_hiem', 0)
        
        don_thuoc.da_thanh_toan = True
        don_thuoc.trang_thai = 'DA_THANH_TOAN'
        don_thuoc.ngay_thanh_toan = timezone.now()
        don_thuoc.phuong_thuc_thanh_toan = phuong_thuc
        don_thuoc.ma_giao_dich = ma_giao_dich
        don_thuoc.ma_bao_hiem = ma_bao_hiem
        don_thuoc.ty_le_bao_hiem = ty_le_bao_hiem
        don_thuoc.save()
        
        return Response({
            'message': 'Thanh toán thành công',
            'don_thuoc': DonThuocSerializer(don_thuoc).data
        })

    @action(detail=True, methods=['post'])
    def xac_nhan_xuat_thuoc(self, request, pk=None):
        """Xác nhận xuất thuốc"""
        don_thuoc = self.get_object()
        
        if don_thuoc.trang_thai == 'DA_XUAT_THUOC':
            return Response(
                {'error': 'Đơn thuốc đã được xuất'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Tạo phiếu xuất
        phieu_xuat = PhieuXuatThuoc.objects.create(
            don_thuoc=don_thuoc,
            nguoi_xuat=request.user.bac_si,
            ghi_chu=request.data.get('ghi_chu', '')
        )
        
        # Cập nhật trạng thái đơn thuốc
        don_thuoc.trang_thai = 'DA_XUAT_THUOC'
        don_thuoc.save()
        
        return Response({
            'message': 'Xuất thuốc thành công',
            'phieu_xuat': PhieuXuatThuocSerializer(phieu_xuat).data
        })

    @action(detail=False, methods=['get'])
    def thong_ke_doanh_thu(self, request):
        """Thống kê doanh thu từ đơn thuốc"""
        tu_ngay = request.query_params.get('tu_ngay')
        den_ngay = request.query_params.get('den_ngay')
        
        if not tu_ngay or not den_ngay:
            return Response(
                {'error': 'Vui lòng cung cấp tu_ngay và den_ngay'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        don_thuoc_da_tt = DonThuoc.objects.filter(
            da_thanh_toan=True,
            ngay_thanh_toan__date__gte=tu_ngay,
            ngay_thanh_toan__date__lte=den_ngay
        )
        
        tong_doanh_thu = don_thuoc_da_tt.aggregate(
            tong=Sum('tong_tien')
        )['tong'] or 0
        
        thong_ke_theo_phuong_thuc = don_thuoc_da_tt.values(
            'phuong_thuc_thanh_toan'
        ).annotate(
            tong=Sum('tong_tien'),
            so_luong=Count('id')
        )
        
        thong_ke_theo_ngay = don_thuoc_da_tt.values(
            'ngay_thanh_toan__date'
        ).annotate(
            tong=Sum('tong_tien'),
            so_luong=Count('id')
        ).order_by('ngay_thanh_toan__date')
        
        return Response({
            'tu_ngay': tu_ngay,
            'den_ngay': den_ngay,
            'tong_doanh_thu': tong_doanh_thu,
            'tong_don_thuoc': don_thuoc_da_tt.count(),
            'thong_ke_theo_phuong_thuc': thong_ke_theo_phuong_thuc,
            'thong_ke_theo_ngay': thong_ke_theo_ngay
        })

class ChiTietDonThuocViewSet(viewsets.ModelViewSet):
    """API cho chi tiết đơn thuốc"""
    queryset = ChiTietDonThuoc.objects.select_related('don_thuoc', 'thuoc').all()
    serializer_class = ChiTietDonThuocSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['don_thuoc', 'thuoc', 'da_xuat_thuoc']

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_superuser or getattr(u, 'vai_tro', None) in ['ADMIN', 'NHAN_VIEN']:
            return qs
        if getattr(u, 'vai_tro', None) == 'BAC_SI' and hasattr(u, 'bac_si'):
            return qs.filter(don_thuoc__bac_si=u.bac_si)
        if getattr(u, 'vai_tro', None) == 'BENH_NHAN' and hasattr(u, 'benh_nhan'):
            return qs.filter(don_thuoc__benh_nhan=u.benh_nhan)
        return qs.none()

    @action(detail=False, methods=['get'])
    def thong_ke_thuoc(self, request):
        """Thống kê thuốc được kê nhiều nhất"""
        tu_ngay = request.query_params.get('tu_ngay')
        den_ngay = request.query_params.get('den_ngay')
        
        queryset = self.get_queryset().filter(la_thuoc_mua_ngoai=False).exclude(thuoc__isnull=True)
        if tu_ngay:
            queryset = queryset.filter(don_thuoc__ngay_tao__date__gte=tu_ngay)
        if den_ngay:
            queryset = queryset.filter(don_thuoc__ngay_tao__date__lte=den_ngay)
        
        thong_ke = queryset.values(
            'thuoc__ma_thuoc', 'thuoc__ten_thuoc'
        ).annotate(
            tong_so_luong=Sum('so_luong'),
            tong_tien=Sum(F('so_luong') * F('don_gia_tai_thoi_diem')),
            so_lan_ke=Count('id')
        ).order_by('-tong_so_luong')[:20]
        
        return Response(thong_ke)

# ==================== VIEWSETS CHO PHIẾU XUẤT THUỐC ====================

class PhieuXuatThuocViewSet(viewsets.ModelViewSet):
    """API cho phiếu xuất thuốc"""
    queryset = PhieuXuatThuoc.objects.select_related(
        'don_thuoc', 'nguoi_xuat'
    ).prefetch_related(
        'chi_tiet__kho_thuoc__thuoc'
    ).all()
    serializer_class = PhieuXuatThuocSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['nguoi_xuat']
    search_fields = ['ma_phieu', 'don_thuoc__ma_don']
    ordering_fields = ['ngay_xuat']

    @action(detail=True, methods=['get'])
    def chi_tiet_xuat(self, request, pk=None):
        """Xem chi tiết xuất thuốc"""
        phieu_xuat = self.get_object()
        chi_tiet = ChiTietXuatThuoc.objects.filter(phieu_xuat=phieu_xuat)
        serializer = ChiTietXuatThuocSerializer(chi_tiet, many=True)
        
        return Response({
            'phieu_xuat': PhieuXuatThuocSerializer(phieu_xuat).data,
            'chi_tiet': serializer.data,
            'tong_tien': sum(ct.thanh_tien() for ct in chi_tiet)
        })

# ==================== VIEWSETS CHO LỊCH SỬ TIÊM CHỦNG ====================

class LichSuTiemChungViewSet(viewsets.ModelViewSet):
    """API cho lịch sử tiêm chủng"""
    queryset = LichSuTiemChung.objects.select_related(
        'benh_nhan', 'vaccine', 'nguoi_tiem'
    ).all()
    serializer_class = LichSuTiemChungSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['benh_nhan', 'vaccine', 'trang_thai', 'so_mui']
    search_fields = ['ma_lich', 'benh_nhan__nguoi_dung__ho_ten', 'vaccine__ten_vaccine']
    ordering_fields = ['ngay_tiem', 'ngay_tiem_tiep_theo']

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_superuser or getattr(u, 'vai_tro', None) in ['ADMIN', 'NHAN_VIEN']:
            return qs
        if getattr(u, 'vai_tro', None) == 'BAC_SI' and hasattr(u, 'bac_si'):
            return qs.filter(
                Q(nguoi_tiem=u.bac_si) | Q(benh_nhan__ho_so__bac_si=u.bac_si)
            ).distinct()
        if getattr(u, 'vai_tro', None) == 'BENH_NHAN' and hasattr(u, 'benh_nhan'):
            return qs.filter(benh_nhan=u.benh_nhan)
        return qs.none()

    @action(detail=False, methods=['get'])
    def lich_tiem_sap_toi(self, request):
        """Lấy danh sách lịch tiêm sắp tới"""
        today = date.today()
        seven_days_later = today + timedelta(days=7)
        
        lich_sap_toi = self.get_queryset().filter(
            ngay_tiem_tiep_theo__gte=today,
            ngay_tiem_tiep_theo__lte=seven_days_later,
            trang_thai='HEN_TIEM'
        ).order_by('ngay_tiem_tiep_theo')
        
        serializer = self.get_serializer(lich_sap_toi, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def thong_ke(self, request):
        """Thống kê tiêm chủng"""
        tu_ngay = request.query_params.get('tu_ngay')
        den_ngay = request.query_params.get('den_ngay')
        
        queryset = self.get_queryset()
        if tu_ngay:
            queryset = queryset.filter(ngay_tiem__gte=tu_ngay)
        if den_ngay:
            queryset = queryset.filter(ngay_tiem__lte=den_ngay)
        
        # Thống kê theo vaccine
        thong_ke_vaccine = queryset.values(
            'vaccine__ma_vaccine', 'vaccine__ten_vaccine'
        ).annotate(
            so_luong=Count('id')
        ).order_by('-so_luong')
        
        # Thống kê theo phản ứng
        thong_ke_phan_ung = queryset.values('phan_ung_sau_tiem').annotate(
            so_luong=Count('id')
        )
        
        return Response({
            'tong_luot_tiem': queryset.count(),
            'thong_ke_vaccine': thong_ke_vaccine,
            'thong_ke_phan_ung': thong_ke_phan_ung
        })

# ==================== VIEWSETS CHO TOA THUỐC MẪU ====================

class ToaThuocMauViewSet(viewsets.ModelViewSet):
    """API cho toa thuốc mẫu"""
    queryset = ToaThuocMau.objects.prefetch_related(
        'chi_tiet__thuoc'
    ).all()
    serializer_class = ToaThuocMauSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['ma_toa', 'ten_toa', 'chuan_doan']

    @action(detail=True, methods=['post'])
    def ap_dung(self, request, pk=None):
        """Áp dụng toa thuốc mẫu vào đơn thuốc"""
        toa_mau = self.get_object()
        don_thuoc_id = request.data.get('don_thuoc_id')
        
        try:
            don_thuoc = DonThuoc.objects.get(id=don_thuoc_id)
        except DonThuoc.DoesNotExist:
            return Response(
                {'error': 'Không tìm thấy đơn thuốc'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Thêm các thuốc từ toa mẫu vào đơn
        for ct in toa_mau.chi_tiet.all():
            ChiTietDonThuoc.objects.create(
                don_thuoc=don_thuoc,
                thuoc=ct.thuoc,
                so_luong=ct.so_luong,
                lieu_dung=ct.lieu_dung,
                cach_dung=ct.cach_dung,
                thoi_diem=ct.thoi_diem,
                so_ngay_dung=ct.so_ngay_dung,
                tan_suat=ct.tan_suat
            )
        
        # Cập nhật số lần dùng
        toa_mau.so_luot_dung += 1
        toa_mau.save()
        
        # Tính lại tổng tiền
        don_thuoc.tinh_tong_tien()
        
        return Response({
            'message': 'Áp dụng toa thuốc mẫu thành công',
            'don_thuoc': DonThuocSerializer(don_thuoc).data
        })

    @action(detail=True, methods=['get'])
    def tinh_tien(self, request, pk=None):
        """Tính tổng tiền của toa thuốc mẫu"""
        toa_mau = self.get_object()
        tong_tien = sum(ct.thanh_tien_mau() for ct in toa_mau.chi_tiet.all())
        
        chi_tiet = []
        for ct in toa_mau.chi_tiet.all():
            chi_tiet.append({
                'thuoc': ct.thuoc.ten_thuoc,
                'so_luong': ct.so_luong,
                'don_gia': float(ct.thuoc.gia_ban),
                'thanh_tien': float(ct.thanh_tien_mau()),
                'cach_dung': ct.get_cach_dung_display(),
                'lieu_dung': ct.lieu_dung
            })
        
        return Response({
            'toa_thuoc': toa_mau.ten_toa,
            'ma_toa': toa_mau.ma_toa,
            'tong_tien': float(tong_tien),
            'chi_tiet': chi_tiet
        })

# ==================== VIEWSETS CHO LỊCH HẸN TÁI KHÁM ====================

class LichHenTaiKhamViewSet(viewsets.ModelViewSet):
    """API cho lịch hẹn tái khám"""
    queryset = LichHenTaiKham.objects.select_related(
        'benh_nhan', 'bac_si', 'ho_so'
    ).all()
    serializer_class = LichHenTaiKhamSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['trang_thai', 'bac_si', 'benh_nhan']
    search_fields = ['ma_hen', 'benh_nhan__nguoi_dung__ho_ten', 'ly_do']
    ordering_fields = ['ngay_hen', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        u = self.request.user
        if not (u.is_superuser or getattr(u, 'vai_tro', None) in ['ADMIN', 'NHAN_VIEN']):
            if getattr(u, 'vai_tro', None) == 'BAC_SI' and hasattr(u, 'bac_si'):
                queryset = queryset.filter(bac_si=u.bac_si)
            elif getattr(u, 'vai_tro', None) == 'BENH_NHAN' and hasattr(u, 'benh_nhan'):
                queryset = queryset.filter(benh_nhan=u.benh_nhan)
            else:
                queryset = queryset.none()

        tu_ngay = self.request.query_params.get('tu_ngay')
        den_ngay = self.request.query_params.get('den_ngay')
        hom_nay = self.request.query_params.get('hom_nay')
        if tu_ngay or den_ngay or hom_nay == 'true':
            from phongkham.time_utils import bounds_for_local_single_day
            if tu_ngay:
                start, _ = bounds_for_local_single_day(tu_ngay)
                queryset = queryset.filter(ngay_hen__gte=start)
            if den_ngay:
                _, end = bounds_for_local_single_day(den_ngay)
                queryset = queryset.filter(ngay_hen__lte=end)
            if hom_nay == 'true':
                d0, d1 = bounds_for_local_single_day(date.today())
                queryset = queryset.filter(ngay_hen__gte=d0, ngay_hen__lte=d1)

        return queryset

    def perform_create(self, serializer):
        """Bác sĩ chỉ được tạo lịch với chính mình — không tin bac_si từ client."""
        u = self.request.user
        if getattr(u, 'vai_tro', None) == 'BAC_SI' and hasattr(u, 'bac_si'):
            serializer.save(bac_si=u.bac_si)
        else:
            serializer.save()

    @action(detail=True, methods=['post'])
    def cap_nhat_trang_thai(self, request, pk=None):
        """Cập nhật trạng thái lịch hẹn"""
        lich_hen = self.get_object()
        trang_thai_moi = request.data.get('trang_thai')
        
        if trang_thai_moi not in dict(LichHenTaiKham.TRANG_THAI_CHOICES):
            return Response(
                {'error': 'Trạng thái không hợp lệ'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lich_hen.trang_thai = trang_thai_moi
        lich_hen.save()
        
        return Response({
            'message': 'Cập nhật trạng thái thành công',
            'trang_thai': lich_hen.trang_thai
        })

    @action(detail=False, methods=['get'])
    def thong_ke(self, request):
        """Thống kê lịch hẹn"""
        thong_ke_trang_thai = LichHenTaiKham.objects.values('trang_thai').annotate(
            so_luong=Count('id')
        )
        
        # Lịch hẹn theo ngày trong tuần
        lich_hen_trong_tuan = LichHenTaiKham.objects.filter(
            ngay_hen__date__gte=date.today(),
            ngay_hen__date__lte=date.today() + timedelta(days=7)
        ).values('ngay_hen__date').annotate(
            so_luong=Count('id')
        ).order_by('ngay_hen__date')
        
        return Response({
            'thong_ke_trang_thai': thong_ke_trang_thai,
            'lich_hen_trong_tuan': lich_hen_trong_tuan
        })

# ==================== VIEWSETS CHO THEO DÕI ĐIỀU TRỊ ====================

class TheoDoiDieuTriViewSet(viewsets.ModelViewSet):
    """API cho theo dõi điều trị"""
    queryset = TheoDoiDieuTri.objects.select_related('ho_so', 'bac_si').all()
    serializer_class = TheoDoiDieuTriSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['ho_so', 'bac_si']
    ordering_fields = ['ngay_theo_doi']

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_superuser or getattr(u, 'vai_tro', None) in ['ADMIN', 'NHAN_VIEN']:
            return qs
        if getattr(u, 'vai_tro', None) == 'BAC_SI' and hasattr(u, 'bac_si'):
            return qs.filter(ho_so__bac_si=u.bac_si)
        if getattr(u, 'vai_tro', None) == 'BENH_NHAN' and hasattr(u, 'benh_nhan'):
            return qs.filter(ho_so__benh_nhan=u.benh_nhan)
        return qs.none()

    @action(detail=False, methods=['get'])
    def theo_ho_so(self, request):
        """Lấy tất cả theo dõi của một hồ sơ"""
        ho_so_id = request.query_params.get('ho_so_id')
        if not ho_so_id:
            return Response(
                {'error': 'Vui lòng cung cấp ho_so_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        theo_doi = self.get_queryset().filter(ho_so_id=ho_so_id)
        serializer = self.get_serializer(theo_doi, many=True)
        
        # Tạo biểu đồ diễn biến
        chart_data = []
        for td in theo_doi:
            chart_data.append({
                'ngay': td.ngay_theo_doi.strftime('%d/%m/%Y %H:%M'),
                'chi_so': td.chi_so_sinh_ton
            })
        
        return Response({
            'theo_doi': serializer.data,
            'chart_data': chart_data
        })

# ==================== DASHBOARD API ====================

class DashboardViewSet(viewsets.ViewSet):
    """API cho dashboard tổng quan"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def tong_quan(self, request):
        """Thống kê tổng quan"""
        today = date.today()
        
        # Hồ sơ bệnh án
        tong_ho_so = HoSoBenhAn.objects.count()
        ho_so_hom_nay = HoSoBenhAn.objects.filter(ngay_kham__date=today).count()
        
        # Đơn thuốc
        tong_don_thuoc = DonThuoc.objects.count()
        don_thuoc_hom_nay = DonThuoc.objects.filter(ngay_tao__date=today).count()
        doanh_thu_hom_nay = DonThuoc.objects.filter(
            da_thanh_toan=True,
            ngay_thanh_toan__date=today
        ).aggregate(tong=Sum('tong_tien'))['tong'] or 0
        
        # Lịch tiêm
        lich_tiem_hom_nay = LichSuTiemChung.objects.filter(ngay_tiem=today).count()
        
        # Lịch hẹn
        lich_hen_hom_nay = LichHenTaiKham.objects.filter(
            ngay_hen__date=today,
            trang_thai='CHUA_KHAM'
        ).count()
        
        return Response({
            'ho_so_benh_an': {
                'tong': tong_ho_so,
                'hom_nay': ho_so_hom_nay
            },
            'don_thuoc': {
                'tong': tong_don_thuoc,
                'hom_nay': don_thuoc_hom_nay,
                'doanh_thu_hom_nay': doanh_thu_hom_nay
            },
            'lich_tiem': {
                'hom_nay': lich_tiem_hom_nay
            },
            'lich_hen': {
                'hom_nay': lich_hen_hom_nay
            }
        })

    @action(detail=False, methods=['get'])
    def bao_cao_ton_kho(self, request):
        """Báo cáo tồn kho thuốc từ đơn thuốc"""
        # Lấy danh sách thuốc được kê nhiều trong tháng
        first_day = date.today().replace(day=1)
        
        thuoc_ke_nhieu = ChiTietDonThuoc.objects.filter(
            don_thuoc__ngay_tao__date__gte=first_day
        ).values(
            'thuoc__ma_thuoc', 'thuoc__ten_thuoc'
        ).annotate(
            tong_luong=Sum('so_luong')
        ).order_by('-tong_luong')[:10]
        
        return Response({
            'thuoc_ke_nhieu_trong_thang': thuoc_ke_nhieu
        })
        