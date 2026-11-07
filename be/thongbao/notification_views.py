from datetime import datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from nguoidung.permissions import LaAdmin
from nguoidung.models import NguoiDung

from .models import ThongBaoPhatHanh
from .serializers import (
    ThongBaoPhatHanhSerializer,
    TaoThongBaoPhatHanhSerializer,
)
from .services import chuc_vu_phat_hanh_options, dem_nguoi_nhan_du_kien, phan_phoi_thong_bao


class ThongBaoPhatHanhViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Admin: xem lịch sử phát hành thông báo.
    POST tạo mới qua action gui hoặc create override.
    """
    serializer_class = ThongBaoPhatHanhSerializer
    permission_classes = [IsAuthenticated, LaAdmin]
    queryset = ThongBaoPhatHanh.objects.select_related(
        'nguoi_gui', 'nguoi_nhan'
    ).order_by('-thoi_gian_gui', '-created_at')

    def get_serializer_class(self):
        if self.action in ('create', 'gui'):
            return TaoThongBaoPhatHanhSerializer
        return ThongBaoPhatHanhSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        tu_ngay = (params.get('tu_ngay') or '').strip()
        den_ngay = (params.get('den_ngay') or '').strip()
        if tu_ngay:
            try:
                d = datetime.strptime(tu_ngay, '%Y-%m-%d').date()
                qs = qs.filter(thoi_gian_gui__date__gte=d)
            except ValueError:
                pass
        if den_ngay:
            try:
                d = datetime.strptime(den_ngay, '%Y-%m-%d').date()
                qs = qs.filter(thoi_gian_gui__date__lte=d)
            except ValueError:
                pass
        tim_kiem = (params.get('tim_kiem') or params.get('q') or '').strip()
        if tim_kiem:
            qs = qs.filter(
                Q(tieu_de__icontains=tim_kiem) | Q(noi_dung__icontains=tim_kiem)
            )
        loai = (params.get('loai_thong_bao') or '').strip()
        if loai:
            qs = qs.filter(loai_thong_bao=loai)
        pham_vi = (params.get('pham_vi') or '').strip()
        if pham_vi:
            qs = qs.filter(pham_vi=pham_vi)
        return qs

    def create(self, request, *args, **kwargs):
        ser = TaoThongBaoPhatHanhSerializer(
            data=request.data, context={'request': request}
        )
        ser.is_valid(raise_exception=True)
        phat_hanh = ser.save()
        so = phan_phoi_thong_bao(phat_hanh)
        out = ThongBaoPhatHanhSerializer(phat_hanh, context={'request': request})
        return Response(
            {**out.data, 'so_nguoi_nhan_thuc_te': so},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='gui')
    def gui(self, request):
        """Alias POST /phat-hanh/gui/ — tạo và gửi thông báo."""
        return self.create(request)

    @action(detail=False, methods=['get'], url_path='tuy-chon')
    def tuy_chon(self, request):
        """Metadata cho form admin."""
        return Response({
            'loai_thong_bao': [
                {'value': c[0], 'label': c[1]}
                for c in ThongBaoPhatHanh.LoaiThongBao.choices
            ],
            'pham_vi': [
                {'value': c[0], 'label': c[1]}
                for c in ThongBaoPhatHanh.PhamVi.choices
            ],
            'vai_tro': [
                {'value': c[0], 'label': c[1]}
                for c in NguoiDung.VAI_TRO_CHOICES
            ],
            'chuc_vu': chuc_vu_phat_hanh_options(),
        })

    @action(detail=False, methods=['get'], url_path='dem-nguoi-nhan')
    def dem_nguoi_nhan(self, request):
        """Preview số người nhận."""
        pham_vi = request.query_params.get('pham_vi', '')
        vai_tro = request.query_params.get('vai_tro', '')
        chuc_vu = request.query_params.get('chuc_vu', '')
        nguoi_nhan_id = request.query_params.get('nguoi_nhan_id') or None
        so = dem_nguoi_nhan_du_kien(pham_vi, vai_tro, chuc_vu, nguoi_nhan_id)
        return Response({'so_nguoi_nhan': so})
