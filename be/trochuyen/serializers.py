from rest_framework import serializers
from .models import PhongChat, TinNhan, ThanhVienPhong
from nguoidung.serializers import BenhNhanSerializer, BacSiSerializer, NhanVienSerializer
from benhan.serializers import HoSoBenhAnSerializer
from lichhen.serializers import LichHenSerializer
from thuoc.serializers import ThuocSerializer

class ThanhVienPhongSerializer(serializers.ModelSerializer):
    nguoi_dung = serializers.StringRelatedField()
    
    class Meta:
        model = ThanhVienPhong
        fields = ['id', 'nguoi_dung', 'ngay_tham_gia', 'ngay_roi_di', 'is_active']

class PhongChatSerializer(serializers.ModelSerializer):
    benh_nhan = BenhNhanSerializer(read_only=True)
    bac_si = BacSiSerializer(read_only=True)
    nhan_vien = NhanVienSerializer(read_only=True)
    benh_an = HoSoBenhAnSerializer(read_only=True)
    lich_hen = LichHenSerializer(read_only=True)
    thanh_vien = serializers.SerializerMethodField()
    so_tin_nhan_chua_doc = serializers.SerializerMethodField()
    tin_nhan_cuoi = serializers.SerializerMethodField()
    
    class Meta:
        model = PhongChat
        fields = ['id', 'ma_phong', 'ten_phong', 'loai_phong', 'trang_thai',
                 'benh_nhan', 'bac_si', 'nhan_vien', 'benh_an', 'lich_hen',
                 'ngay_tao', 'ngay_cap_nhat', 'ngay_ket_thuc',
                 'thanh_vien', 'so_tin_nhan_chua_doc', 'tin_nhan_cuoi']
        read_only_fields = ['id', 'ma_phong', 'ngay_tao', 'ngay_cap_nhat']
    
    def get_thanh_vien(self, obj):
        return obj.danh_sach_thanh_vien()
    
    def get_so_tin_nhan_chua_doc(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.tin_nhan.exclude(
                nguoi_gui=request.user
            ).exclude(
                trang_thai_xem__nguoi_dung=request.user
            ).count()
        return 0
    
    def get_tin_nhan_cuoi(self, obj):
        tin_nhan_cuoi = obj.tin_nhan.last()
        if tin_nhan_cuoi:
            req = self.context.get('request')
            da = False
            if req and req.user.is_authenticated:
                da = tin_nhan_cuoi.da_xem_boi(req.user)
            ho_ten = getattr(tin_nhan_cuoi.nguoi_gui, 'ho_ten', str(tin_nhan_cuoi.nguoi_gui))
            return {
                'id': str(tin_nhan_cuoi.id),
                'noi_dung': tin_nhan_cuoi.noi_dung[:100] if tin_nhan_cuoi.noi_dung else f"[{tin_nhan_cuoi.get_loai_display()}]",
                'ngay_gui': tin_nhan_cuoi.ngay_gui,
                'nguoi_gui': ho_ten,
                'loai': tin_nhan_cuoi.loai,
                'da_xem': da,
            }
        return None

class TaoPhongChatSerializer(serializers.Serializer):
    ten_phong = serializers.CharField(max_length=255)
    loai_phong = serializers.ChoiceField(
        choices=PhongChat.LoaiPhong.choices, default=PhongChat.LoaiPhong.TU_VAN
    )
    benh_nhan_id = serializers.UUIDField()
    bac_si_id = serializers.UUIDField(required=False, allow_null=True)
    nhan_vien_id = serializers.UUIDField(required=False, allow_null=True)
    benh_an_id = serializers.UUIDField(required=False, allow_null=True)
    lich_hen_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate(self, data):
        # Kiểm tra ít nhất có bác sĩ hoặc nhân viên
        if not data.get('bac_si_id') and not data.get('nhan_vien_id'):
            raise serializers.ValidationError("Cần có bác sĩ hoặc nhân viên tư vấn")
        return data

class TinNhanSerializer(serializers.ModelSerializer):
    nguoi_gui = serializers.StringRelatedField()
    thuoc = ThuocSerializer(read_only=True)
    lich_hen = LichHenSerializer(read_only=True)
    benh_an = HoSoBenhAnSerializer(read_only=True)
    da_xem = serializers.SerializerMethodField()

    class Meta:
        model = TinNhan
        fields = ['id', 'phong_chat', 'nguoi_gui', 'loai', 'noi_dung',
                 'thuoc', 'lich_hen', 'benh_an', 'file', 'hinh_anh',
                 'da_xem', 'ngay_gui', 'ngay_xem']
        read_only_fields = ['id', 'ngay_gui', 'ngay_xem']

    def get_da_xem(self, obj):
        req = self.context.get('request')
        if not req or not req.user.is_authenticated:
            return False
        return obj.da_xem_boi(req.user)

class GuiTinNhanSerializer(serializers.Serializer):
    phong_chat_id = serializers.UUIDField(required=False, allow_null=True)
    noi_dung = serializers.CharField(required=False, allow_blank=True)
    loai = serializers.ChoiceField(
        choices=TinNhan.LOAI_TIN_NHAN_CHOICES, default=TinNhan.LoaiTinNhan.TEXT
    )
    
    # Các trường cho tin nhắn đặc biệt
    thuoc_id = serializers.UUIDField(required=False, allow_null=True)
    lich_hen_id = serializers.UUIDField(required=False, allow_null=True)
    benh_an_id = serializers.UUIDField(required=False, allow_null=True)
    
    # File
    file = serializers.FileField(required=False, allow_null=True)
    hinh_anh = serializers.ImageField(required=False, allow_null=True)
    
    def validate(self, data):
        loai = data.get('loai')
        
        if loai == 'TEXT' and not data.get('noi_dung'):
            raise serializers.ValidationError("Tin nhắn văn bản cần có nội dung")
        
        if loai == 'THUOC' and not data.get('thuoc_id'):
            raise serializers.ValidationError("Tin nhắn thuốc cần có thuoc_id")
        
        if loai == 'LICH_HEN' and not data.get('lich_hen_id'):
            raise serializers.ValidationError("Tin nhắn lịch hẹn cần có lich_hen_id")
        
        if loai == 'BENH_AN' and not data.get('benh_an_id'):
            raise serializers.ValidationError("Tin nhắn bệnh án cần có benh_an_id")
        
        if loai == 'HINH_ANH' and not data.get('hinh_anh'):
            raise serializers.ValidationError("Tin nhắn hình ảnh cần có file hình ảnh")
        
        if loai == 'FILE' and not data.get('file'):
            raise serializers.ValidationError("Tin nhắn file cần có file đính kèm")
        
        return data

class DanhSachPhongChatSerializer(serializers.Serializer):
    """Serializer cho danh sách phòng chat"""
    id = serializers.UUIDField()
    ma_phong = serializers.CharField()
    ten_phong = serializers.CharField()
    loai_phong = serializers.CharField()
    trang_thai = serializers.CharField()
    ten_benh_nhan = serializers.CharField()
    ten_nguoi_tu_van = serializers.CharField()
    so_tin_nhan_chua_doc = serializers.IntegerField()
    tin_nhan_cuoi = serializers.DictField()
    ngay_cap_nhat = serializers.DateTimeField()