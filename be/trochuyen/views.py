from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
import uuid

from .models import PhongChat, TinNhan, TinNhanDaXem, ThanhVienPhong
from .serializers import (
    PhongChatSerializer, TinNhanSerializer, TaoPhongChatSerializer,
    GuiTinNhanSerializer, DanhSachPhongChatSerializer
)
from nguoidung.models import BenhNhan, BacSi, NhanVien, NguoiDung

class PhongChatViewSet(viewsets.ModelViewSet):
    """ViewSet cho quản lý phòng chat"""
    serializer_class = PhongChatSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = PhongChat.objects.all()
        
        # Filter theo vai trò
        if hasattr(user, 'benh_nhan'):
            # Bệnh nhân chỉ xem được phòng của mình
            queryset = queryset.filter(benh_nhan=user.benh_nhan)
        elif hasattr(user, 'bac_si'):
            # Bác sĩ xem phòng mình tư vấn
            queryset = queryset.filter(bac_si=user.bac_si)
        elif hasattr(user, 'nhan_vien'):
            # Nhân viên xem phòng mình tư vấn
            queryset = queryset.filter(nhan_vien=user.nhan_vien)
        
        # Filter theo query params
        trang_thai = self.request.query_params.get('trang_thai')
        loai_phong = self.request.query_params.get('loai_phong')
        
        if trang_thai:
            queryset = queryset.filter(trang_thai=trang_thai)
        if loai_phong:
            queryset = queryset.filter(loai_phong=loai_phong)
        
        return queryset.select_related('benh_nhan', 'bac_si', 'nhan_vien')
    
    @action(detail=True, methods=['get'])
    def tin_nhan(self, request, pk=None):
        """Lấy danh sách tin nhắn của phòng"""
        phong_chat = self.get_object()
        
        # Kiểm tra quyền
        if not phong_chat.kiem_tra_quyen(request.user):
            return Response(
                {'error': 'Bạn không có quyền xem phòng chat này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Lấy query params
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 50))
        truoc_id = request.GET.get('truoc_id')
        
        # Query tin nhắn
        tin_nhan_query = phong_chat.tin_nhan.select_related('nguoi_gui')
        
        if truoc_id:
            # Lấy tin nhắn trước một tin nhắn cụ thể (load more)
            tin_nhan = get_object_or_404(TinNhan, id=truoc_id)
            tin_nhan_query = tin_nhan_query.filter(ngay_gui__lt=tin_nhan.ngay_gui)
        
        # Phân trang
        paginator = Paginator(tin_nhan_query.order_by('-ngay_gui'), limit)
        tin_nhan_page = paginator.get_page(page)
        
        serializer = TinNhanSerializer(
            tin_nhan_page, many=True, context={'request': request}
        )
        
        return Response({
            'data': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': tin_nhan_page.has_next(),
                'has_previous': tin_nhan_page.has_previous()
            }
        })
    
    @action(detail=True, methods=['post'])
    def danh_dau_da_doc(self, request, pk=None):
        """Đánh dấu tất cả tin nhắn trong phòng đã đọc"""
        phong_chat = self.get_object()
        
        # Kiểm tra quyền
        if not phong_chat.kiem_tra_quyen(request.user):
            return Response(
                {'error': 'Bạn không có quyền truy cập phòng chat này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Đánh dấu đã đọc qua bảng TinNhanDaXem (không có da_xem field trong TinNhan)
        chua_xem = TinNhan.objects.filter(
            phong_chat=phong_chat,
        ).exclude(
            nguoi_gui=request.user,
        ).exclude(
            trang_thai_xem__nguoi_dung=request.user,
        )
        updated = 0
        for tin_nhan in chua_xem:
            _, created = TinNhanDaXem.objects.get_or_create(
                tin_nhan=tin_nhan,
                nguoi_dung=request.user,
            )
            if created:
                updated += 1

        return Response({
            'message': f'Đã đánh dấu {updated} tin nhắn đã đọc',
            'so_luong': updated
        })
    
    @action(detail=True, methods=['post'])
    def ket_thuc(self, request, pk=None):
        """Kết thúc phòng chat"""
        phong_chat = self.get_object()
        
        # Kiểm tra quyền (chỉ bác sĩ/nhân viên mới được kết thúc)
        if not (hasattr(request.user, 'bac_si') or hasattr(request.user, 'nhan_vien')):
            return Response(
                {'error': 'Chỉ bác sĩ hoặc nhân viên mới có thể kết thúc phòng chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        phong_chat.trang_thai = 'KET_THUC'
        phong_chat.ngay_ket_thuc = timezone.now()
        phong_chat.save()
        
        # Gửi tin nhắn thông báo
        TinNhan.objects.create(
            phong_chat=phong_chat,
            nguoi_gui=request.user,
            loai='THONG_BAO',
            noi_dung=f'Đã kết thúc cuộc trò chuyện bởi {request.user.ho_ten}'
        )
        
        return Response(PhongChatSerializer(phong_chat).data)


def _dam_bao_thanh_vien(phong_chat, benh_nhan, bac_si):
    """Đảm bảo BN + BS là thành viên active (phòng get-or-create theo cặp)."""
    pairs = [
        (benh_nhan.nguoi_dung, ThanhVienPhong.VaiTro.BENH_NHAN),
        (bac_si.nguoi_dung, ThanhVienPhong.VaiTro.BAC_SI),
    ]
    for nguoi_dung, vai_tro in pairs:
        tv, _ = ThanhVienPhong.objects.get_or_create(
            phong_chat=phong_chat,
            nguoi_dung=nguoi_dung,
            defaults={'vai_tro': vai_tro},
        )
        updates = []
        if tv.vai_tro != vai_tro:
            tv.vai_tro = vai_tro
            updates.append('vai_tro')
        if not tv.is_active:
            tv.is_active = True
            updates.append('is_active')
        if updates:
            tv.save(update_fields=updates)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lay_hoac_tao_phong_bs_bn(request):
    """
    Chat 1-1 theo cap (benh nhan, bac si): tim phong TU_VAN da co hoac tao moi.
    - BENH_NHAN: gửi bac_si_id (UUID bảng bac_si).
    - BAC_SI: gửi benh_nhan_id (UUID bảng benh_nhan).
    """
    benh_nhan_id = request.data.get('benh_nhan_id')
    bac_si_id = request.data.get('bac_si_id')
    vt = getattr(request.user, 'vai_tro', None)

    benh_nhan = None
    bac_si = None

    if vt == 'BENH_NHAN' and hasattr(request.user, 'benh_nhan'):
        benh_nhan = request.user.benh_nhan
        if not bac_si_id:
            return Response(
                {'error': 'Bệnh nhân cần gửi bac_si_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bac_si = get_object_or_404(BacSi, id=bac_si_id)
    elif vt == 'BAC_SI' and hasattr(request.user, 'bac_si'):
        bac_si = request.user.bac_si
        if not benh_nhan_id:
            return Response(
                {'error': 'Bac si can gui benh_nhan_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        benh_nhan = get_object_or_404(BenhNhan, id=benh_nhan_id)
    else:
        return Response(
            {'error': 'Chi benh nhan hoac bac si duoc dung API nay'},
            status=status.HTTP_403_FORBIDDEN,
        )

    loai = PhongChat.LoaiPhong.TU_VAN
    phong = (
        PhongChat.objects.filter(
            benh_nhan=benh_nhan,
            bac_si=bac_si,
            loai_phong=loai,
            nhan_vien__isnull=True,
        )
        .order_by('-ngay_cap_nhat')
        .first()
    )

    if not phong:
        ten_phong = (
            f'{benh_nhan.nguoi_dung.ho_ten} — {bac_si.nguoi_dung.ho_ten}'
        )
        with transaction.atomic():
            phong = PhongChat.objects.create(
                ten_phong=ten_phong,
                loai_phong=loai,
                benh_nhan=benh_nhan,
                bac_si=bac_si,
            )
            _dam_bao_thanh_vien(phong, benh_nhan, bac_si)
            TinNhan.objects.create(
                phong_chat=phong,
                nguoi_gui=request.user,
                loai=TinNhan.LoaiTinNhan.THONG_BAO,
                noi_dung='Da mo kenh tro chuyen.',
            )
    else:
        _dam_bao_thanh_vien(phong, benh_nhan, bac_si)

    return Response(
        PhongChatSerializer(phong, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tao_phong_chat(request):
    """Tạo phòng chat mới"""
    serializer = TaoPhongChatSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # BENH_NHAN chỉ được tạo phòng cho chính mình
    if request.user.vai_tro == 'BENH_NHAN' and hasattr(request.user, 'benh_nhan'):
        benh_nhan = request.user.benh_nhan
    else:
        benh_nhan = get_object_or_404(BenhNhan, id=data['benh_nhan_id'])
    
    # Kiểm tra bác sĩ (nếu có)
    bac_si = None
    if data.get('bac_si_id'):
        bac_si = get_object_or_404(BacSi, id=data['bac_si_id'])
    
    # Kiểm tra nhân viên (nếu có)
    nhan_vien = None
    if data.get('nhan_vien_id'):
        nhan_vien = get_object_or_404(NhanVien, id=data['nhan_vien_id'])
    
    # Tạo phòng chat
    phong_chat = PhongChat.objects.create(
        ten_phong=data['ten_phong'],
        loai_phong=data['loai_phong'],
        benh_nhan=benh_nhan,
        bac_si=bac_si,
        nhan_vien=nhan_vien,
        benh_an_id=data.get('benh_an_id'),
        lich_hen_id=data.get('lich_hen_id')
    )
    
    # Thêm thành viên vào lịch sử
    ThanhVienPhong.objects.create(
        phong_chat=phong_chat,
        nguoi_dung=benh_nhan.nguoi_dung,
        vai_tro=ThanhVienPhong.VaiTro.BENH_NHAN,
    )
    if bac_si:
        ThanhVienPhong.objects.create(
            phong_chat=phong_chat,
            nguoi_dung=bac_si.nguoi_dung,
            vai_tro=ThanhVienPhong.VaiTro.BAC_SI,
        )
    if nhan_vien:
        ThanhVienPhong.objects.create(
            phong_chat=phong_chat,
            nguoi_dung=nhan_vien.nguoi_dung,
            vai_tro=ThanhVienPhong.VaiTro.NHAN_VIEN,
        )
    
    # Gửi tin nhắn chào mừng
    TinNhan.objects.create(
        phong_chat=phong_chat,
        nguoi_gui=request.user,
        loai='THONG_BAO',
        noi_dung=f'Đã tạo phòng chat: {phong_chat.ten_phong}'
    )
    
    return Response(
        PhongChatSerializer(phong_chat, context={'request': request}).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gui_tin_nhan(request, phong_id=None):
    """Gửi tin nhắn mới (REST fallback khi WebSocket không hoạt động)"""
    serializer = GuiTinNhanSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    phong_chat_id = phong_id or data.get('phong_chat_id')
    phong_chat = get_object_or_404(PhongChat, id=phong_chat_id)
    
    # Kiểm tra quyền
    if not phong_chat.kiem_tra_quyen(request.user):
        return Response(
            {'error': 'Bạn không có quyền gửi tin nhắn trong phòng này'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Tạo tin nhắn
    tin_nhan_data = {
        'phong_chat': phong_chat,
        'nguoi_gui': request.user,
        'loai': data['loai'],
        'noi_dung': data.get('noi_dung', '')
    }
    
    # Thêm các trường đặc biệt
    if data.get('thuoc_id'):
        from thuoc.models import Thuoc
        tin_nhan_data['thuoc'] = get_object_or_404(Thuoc, id=data['thuoc_id'])
    
    if data.get('lich_hen_id'):
        from lichhen.models import LichHen
        tin_nhan_data['lich_hen'] = get_object_or_404(LichHen, id=data['lich_hen_id'])
    
    if data.get('benh_an_id'):
        from benhan.models import HoSoBenhAn
        tin_nhan_data['benh_an'] = get_object_or_404(HoSoBenhAn, id=data['benh_an_id'])
    
    if data.get('file'):
        tin_nhan_data['file'] = data['file']
    
    if data.get('hinh_anh'):
        tin_nhan_data['hinh_anh'] = data['hinh_anh']
    
    tin_nhan = TinNhan.objects.create(**tin_nhan_data)
    
    return Response(
        TinNhanSerializer(tin_nhan, context={'request': request}).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def danh_sach_tin_nhan(request, phong_id):
    """Lấy danh sách tin nhắn của phòng (phương thức GET)"""
    phong_chat = get_object_or_404(PhongChat, id=phong_id)
    
    # Kiểm tra quyền
    if not phong_chat.kiem_tra_quyen(request.user):
        return Response(
            {'error': 'Bạn không có quyền xem tin nhắn trong phòng này'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Lấy query params
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    
    # Query tin nhắn
    tin_nhan_query = phong_chat.tin_nhan.select_related('nguoi_gui').order_by('-ngay_gui')
    
    # Phân trang
    paginator = Paginator(tin_nhan_query, limit)
    tin_nhan_page = paginator.get_page(page)
    
    serializer = TinNhanSerializer(
        tin_nhan_page, many=True, context={'request': request}
    )
    
    return Response({
        'data': serializer.data,
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': tin_nhan_page.has_next(),
            'has_previous': tin_nhan_page.has_previous()
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def danh_dau_da_doc(request, phong_id):
    """Đánh dấu tin nhắn đã đọc"""
    phong_chat = get_object_or_404(PhongChat, id=phong_id)
    
    # Kiểm tra quyền
    if not phong_chat.kiem_tra_quyen(request.user):
        return Response(
            {'error': 'Bạn không có quyền truy cập phòng này'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    tin_nhan_ids = request.data.get('tin_nhan_ids', [])

    # Lọc tin nhắn cần đánh dấu (dùng TinNhanDaXem thay da_xem field)
    queryset = TinNhan.objects.filter(
        phong_chat=phong_chat,
    ).exclude(
        nguoi_gui=request.user,
    ).exclude(
        trang_thai_xem__nguoi_dung=request.user,
    )
    if tin_nhan_ids:
        queryset = queryset.filter(id__in=tin_nhan_ids)

    updated = 0
    for tin_nhan in queryset:
        _, created = TinNhanDaXem.objects.get_or_create(
            tin_nhan=tin_nhan,
            nguoi_dung=request.user,
        )
        if created:
            updated += 1

    return Response({
        'message': f'Đã đánh dấu {updated} tin nhắn đã đọc',
        'so_luong': updated
    })