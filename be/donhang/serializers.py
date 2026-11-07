from rest_framework import serializers
from .models import GioHang, SanPhamGioHang, DonHang, ChiTietDonHang, ThanhToan
from thuoc.serializers import ThuocSerializer
from nguoidung.serializers import BenhNhanSerializer

class SanPhamGioHangSerializer(serializers.ModelSerializer):
    thuoc = ThuocSerializer(read_only=True)
    thuoc_id = serializers.UUIDField(write_only=True)
    thanh_tien = serializers.SerializerMethodField()
    
    class Meta:
        model = SanPhamGioHang
        fields = ['id', 'thuoc', 'thuoc_id', 'so_luong', 'thanh_tien', 'ngay_them']
        read_only_fields = ['id', 'ngay_them']
    
    def get_thanh_tien(self, obj):
        return obj.thanh_tien()
    
    def validate(self, data):
        from thuoc.models import Thuoc
        
        thuoc = Thuoc.objects.get(id=data['thuoc_id'])
        
        # Kiểm tra thuốc cần đơn
        if thuoc.can_don_thuoc:
            raise serializers.ValidationError("Thuốc này cần có đơn từ bác sĩ, không thể mua online")
        
        # Kiểm tra tồn kho
        if thuoc.ton_kho() < data['so_luong']:
            raise serializers.ValidationError(f"Thuốc chỉ còn {thuoc.ton_kho()} {thuoc.don_vi}")
        
        return data

class GioHangSerializer(serializers.ModelSerializer):
    san_pham_gio_hang = SanPhamGioHangSerializer(many=True, read_only=True)
    tong_tien = serializers.SerializerMethodField()
    so_luong_san_pham = serializers.SerializerMethodField()
    
    class Meta:
        model = GioHang
        fields = ['id', 'san_pham_gio_hang', 'tong_tien', 'so_luong_san_pham', 'ngay_cap_nhat']
        read_only_fields = ['id', 'ngay_cap_nhat']
    
    def get_tong_tien(self, obj):
        return obj.tong_tien()
    
    def get_so_luong_san_pham(self, obj):
        return obj.so_luong_san_pham()

class ChiTietDonHangSerializer(serializers.ModelSerializer):
    thuoc = ThuocSerializer(read_only=True)
    thanh_tien = serializers.SerializerMethodField()
    
    class Meta:
        model = ChiTietDonHang
        fields = ['id', 'thuoc', 'so_luong', 'don_gia', 'thanh_tien']
    
    def get_thanh_tien(self, obj):
        return obj.thanh_tien()

class ThanhToanSerializer(serializers.ModelSerializer):
    phuong_thuc_display = serializers.CharField(source='get_phuong_thuc_display', read_only=True)
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    
    class Meta:
        model = ThanhToan
        fields = ['id', 'so_tien', 'phuong_thuc', 'phuong_thuc_display', 
                 'trang_thai', 'trang_thai_display', 'ma_giao_dich', 'ngay_thanh_toan']
        read_only_fields = ['id', 'ma_giao_dich', 'ngay_thanh_toan']

class DonHangSerializer(serializers.ModelSerializer):
    benh_nhan = BenhNhanSerializer(read_only=True)
    chi_tiet_don_hang = ChiTietDonHangSerializer(many=True, read_only=True)
    thanh_toan = ThanhToanSerializer(read_only=True)
    loai_don_display = serializers.CharField(source='get_loai_don_display', read_only=True)
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    trang_thai_quan_ly = serializers.SerializerMethodField()

    def get_trang_thai_quan_ly(self, obj):
        return obj.trang_thai_hien_thi_quan_ly()

    class Meta:
        model = DonHang
        fields = ['id', 'ma_don_hang', 'benh_nhan', 'loai_don', 'loai_don_display',
                 'ngay_tao', 'dia_chi_giao_hang', 'tong_tien', 'trang_thai',
                 'trang_thai_display', 'trang_thai_quan_ly', 'ghi_chu', 'chi_tiet_don_hang', 'thanh_toan']
        read_only_fields = ['id', 'ma_don_hang', 'ngay_tao', 'tong_tien']

class TaoDonHangSerializer(serializers.Serializer):
    """Serializer để tạo đơn hàng từ giỏ hàng"""
    dia_chi_giao_hang = serializers.CharField()
    phuong_thuc_thanh_toan = serializers.ChoiceField(choices=ThanhToan.PhuongThuc.choices)
    ghi_chu = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        # Kiểm tra giỏ hàng có sản phẩm không
        request = self.context.get('request')
        benh_nhan = request.user.benh_nhan
        
        if not benh_nhan.gio_hang.san_pham_gio_hang.exists():
            raise serializers.ValidationError("Giỏ hàng trống")
        
        # Kiểm tra thuốc cần tư vấn
        can_tu_van = benh_nhan.gio_hang.san_pham_gio_hang.filter(
            thuoc__can_tu_van=True
        ).exists()
        
        if can_tu_van:
            # Kiểm tra đã được bác sĩ tư vấn chưa
            # Logic kiểm tra tư vấn ở đây
            pass
        
        return data
    
    def create(self, validated_data):
        import random
        from django.db import transaction
        
        request = self.context.get('request')
        benh_nhan = request.user.benh_nhan
        gio_hang = benh_nhan.gio_hang
        
        with transaction.atomic():
            # Tạo mã đơn hàng
            ma_don_hang = f"DH{random.randint(100000, 999999)}"
            
            # Tính tổng tiền
            tong_tien = gio_hang.tong_tien()
            
            # Tạo đơn hàng
            don_hang = DonHang.objects.create(
                ma_don_hang=ma_don_hang,
                benh_nhan=benh_nhan,
                loai_don='ONLINE',
                dia_chi_giao_hang=validated_data['dia_chi_giao_hang'],
                tong_tien=tong_tien,
                ghi_chu=validated_data.get('ghi_chu', '')
            )
            
            # Tạo chi tiết đơn hàng từ giỏ hàng
            for item in gio_hang.san_pham_gio_hang.all():
                ChiTietDonHang.objects.create(
                    don_hang=don_hang,
                    thuoc=item.thuoc,
                    so_luong=item.so_luong,
                    don_gia=item.thuoc.gia_ban
                )
            
            # Tạo thanh toán
            ThanhToan.objects.create(
                don_hang=don_hang,
                so_tien=tong_tien,
                phuong_thuc=validated_data['phuong_thuc_thanh_toan']
            )
            
            # Xóa giỏ hàng
            gio_hang.san_pham_gio_hang.all().delete()
            
            # Gửi thông báo
            from thongbao.models import ThongBao
            ThongBao.tao_thong_bao(
                nguoi_nhan=benh_nhan.nguoi_dung,
                loai='DON_HANG',
                tieu_de='Đơn hàng đã được tạo',
                noi_dung=f'Đơn hàng {ma_don_hang} đã được tạo thành công. Tổng tiền: {tong_tien:,.0f}đ'
            )
            
        return don_hang