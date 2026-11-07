from decimal import Decimal
from datetime import date

from django.db import transaction
from rest_framework import serializers

from .models import *

_THUOC_NCC_UNSET = object()

# ==================== SERIALIZERS CHO CÁC MODEL CƠ BẢN ====================

class LoaiThuocSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiThuoc
        fields = '__all__'

class DonViTinhSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonViTinh
        fields = '__all__'

class NhaCungCapSerializer(serializers.ModelSerializer):
    class Meta:
        model = NhaCungCap
        fields = '__all__'

# ==================== SERIALIZERS CHO THUỐC ====================

def _tinh_tong_tien_nhap_lot(so_luong, don_gia):
    try:
        sl = int(so_luong or 0)
        dg = Decimal(str(don_gia if don_gia is not None else '0'))
        return float(dg * sl)
    except (TypeError, ValueError, ArithmeticError):
        return 0.0


class KhoThuocSerializer(serializers.ModelSerializer):
    ma_thuoc = serializers.CharField(source='thuoc.ma_thuoc', read_only=True)
    ten_thuoc = serializers.CharField(source='thuoc.ten_thuoc', read_only=True)
    don_gia_nhap = serializers.DecimalField(
        source='thuoc.don_gia_nhap', read_only=True, max_digits=10, decimal_places=2
    )
    tong_tien = serializers.SerializerMethodField()
    con_han = serializers.BooleanField(read_only=True)

    def get_tong_tien(self, obj):
        dg = getattr(getattr(obj, 'thuoc', None), 'don_gia_nhap', None)
        return _tinh_tong_tien_nhap_lot(obj.so_luong, dg)
    
    class Meta:
        model = KhoThuoc
        fields = '__all__'

class LichSuGiaThuocSerializer(serializers.ModelSerializer):
    class Meta:
        model = LichSuGiaThuoc
        fields = '__all__'

class ThuocSerializer(serializers.ModelSerializer):
    loai_thuoc_ten = serializers.CharField(source='loai_thuoc.ten_loai', read_only=True)
    don_vi_ten = serializers.CharField(source='don_vi.ten_don_vi', read_only=True)
    ton_kho = serializers.SerializerMethodField()
    han_sd_gan_nhat = serializers.SerializerMethodField()
    nha_cung_cap = NhaCungCapSerializer(many=True, read_only=True)
    nha_cung_cap_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    hinh_anh_url = serializers.SerializerMethodField()
    ma_thuoc = serializers.CharField(required=False, allow_blank=True)

    def get_ton_kho(self, obj):
        return obj.ton_kho()

    def get_han_sd_gan_nhat(self, obj):
        h = obj.han_sd_lo_gan_nhat()
        return h.isoformat() if h else None

    def get_hinh_anh_url(self, obj):
        if not obj.hinh_anh:
            return None
        request = self.context.get('request')
        url = obj.hinh_anh.url
        if request:
            return request.build_absolute_uri(url)
        return url

    @transaction.atomic
    def create(self, validated_data):
        ncc_id = validated_data.pop('nha_cung_cap_id', None)
        validated_data.setdefault('nha_san_xuat', '')
        validated_data.setdefault('nuoc_san_xuat', '')
        ma = (validated_data.get('ma_thuoc') or '').strip()
        if not ma or Thuoc.objects.filter(ma_thuoc=ma).exists():
            validated_data['ma_thuoc'] = Thuoc.generate_next_ma_thuoc()
        else:
            validated_data['ma_thuoc'] = ma
        # Mặc định đang kinh doanh — multipart/parse đôi khi bỏ trống → lưu 0.
        validated_data.setdefault('trang_thai', True)
        instance = super().create(validated_data)
        if ncc_id:
            ThuocNhaCungCap.objects.filter(thuoc=instance).delete()
            ThuocNhaCungCap.objects.create(
                thuoc=instance, nha_cung_cap_id=ncc_id, la_ncc_chinh=True
            )
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        ncc_id = validated_data.pop('nha_cung_cap_id', _THUOC_NCC_UNSET)
        instance = super().update(instance, validated_data)
        if ncc_id is not _THUOC_NCC_UNSET:
            ThuocNhaCungCap.objects.filter(thuoc=instance).delete()
            if ncc_id:
                ThuocNhaCungCap.objects.create(
                    thuoc=instance, nha_cung_cap_id=ncc_id, la_ncc_chinh=True
                )
        return instance
    
    class Meta:
        model = Thuoc
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class ThuocChiTietSerializer(ThuocSerializer):
    kho_thuoc = KhoThuocSerializer(many=True, read_only=True)
    lich_su_gia = LichSuGiaThuocSerializer(many=True, read_only=True)
    
    class Meta(ThuocSerializer.Meta):
        # Chuyển string thành list trước khi cộng
        base_fields = ThuocSerializer.Meta.fields
        if isinstance(base_fields, str):
            base_fields = [base_fields]
        fields = base_fields + ['kho_thuoc', 'lich_su_gia']

# ==================== SERIALIZERS CHO VACCINE ====================

class LoaiVaccineSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiVaccine
        fields = '__all__'

class KhoVaccineSerializer(serializers.ModelSerializer):
    ma_vaccine = serializers.CharField(source='vaccine.ma_vaccine', read_only=True)
    ten_vaccine = serializers.CharField(source='vaccine.ten_vaccine', read_only=True)
    gia_nhap = serializers.DecimalField(
        source='vaccine.gia_nhap', read_only=True, max_digits=10, decimal_places=2
    )
    tong_tien = serializers.SerializerMethodField()
    con_han = serializers.BooleanField(read_only=True)

    def get_tong_tien(self, obj):
        gn = getattr(getattr(obj, 'vaccine', None), 'gia_nhap', None)
        return _tinh_tong_tien_nhap_lot(obj.so_luong, gn)
    
    class Meta:
        model = KhoVaccine
        fields = '__all__'

class LichSuGiaVaccineSerializer(serializers.ModelSerializer):
    class Meta:
        model = LichSuGiaVaccine
        fields = '__all__'

class VaccineSerializer(serializers.ModelSerializer):
    loai_vaccine_ten = serializers.CharField(source='loai_vaccine.ten_loai', read_only=True)
    ten_nha_cung_cap = serializers.CharField(source='nha_cung_cap.ten_ncc', read_only=True, allow_null=True)
    ton_kho = serializers.SerializerMethodField()
    han_sd_gan_nhat = serializers.SerializerMethodField()
    hinh_anh_url = serializers.SerializerMethodField()
    ma_vaccine = serializers.CharField(required=False, allow_blank=True)

    def get_ton_kho(self, obj):
        return obj.ton_kho()

    def get_han_sd_gan_nhat(self, obj):
        h = obj.han_sd_lo_gan_nhat()
        return h.isoformat() if h else None

    def get_hinh_anh_url(self, obj):
        if not obj.hinh_anh:
            return None
        request = self.context.get('request')
        url = obj.hinh_anh.url
        if request:
            return request.build_absolute_uri(url)
        return url

    @transaction.atomic
    def create(self, validated_data):
        validated_data.setdefault('nha_san_xuat', '')
        validated_data.setdefault('nuoc_san_xuat', '')
        ma = (validated_data.get('ma_vaccine') or '').strip()
        if not ma or Vaccine.objects.filter(ma_vaccine=ma).exists():
            validated_data['ma_vaccine'] = Vaccine.generate_next_ma_vaccine()
        else:
            validated_data['ma_vaccine'] = ma
        validated_data.setdefault('trang_thai', True)
        return super().create(validated_data)
    
    class Meta:
        model = Vaccine
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

# ==================== SERIALIZERS CHO NHẬP KHO ====================

class ChiTietPhieuNhapThuocSerializer(serializers.ModelSerializer):
    ten_thuoc = serializers.CharField(source='thuoc.ten_thuoc', read_only=True)
    
    class Meta:
        model = ChiTietPhieuNhapThuoc
        fields = '__all__'

class ChiTietPhieuNhapVaccineSerializer(serializers.ModelSerializer):
    ten_vaccine = serializers.CharField(source='vaccine.ten_vaccine', read_only=True)
    
    class Meta:
        model = ChiTietPhieuNhapVaccine
        fields = '__all__'

def _sinh_ma_phieu_nhap():
    """Mã phiếu duy nhất (tránh trùng khi client gửi lại cùng mã)."""
    import random
    import uuid as uuid_mod

    for _ in range(80):
        cand = f"PNK-{date.today().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
        if not PhieuNhapKho.objects.filter(ma_phieu=cand).exists():
            return cand
    return f"PNK-{uuid_mod.uuid4().hex[:16].upper()}"


class PhieuNhapKhoSerializer(serializers.ModelSerializer):
    ten_nha_cung_cap = serializers.CharField(source='nha_cung_cap.ten_ncc', read_only=True)
    chi_tiet_thuoc = ChiTietPhieuNhapThuocSerializer(many=True, read_only=True)
    chi_tiet_vaccine = ChiTietPhieuNhapVaccineSerializer(many=True, read_only=True)

    class Meta:
        model = PhieuNhapKho
        fields = '__all__'
        read_only_fields = [
            'ngay_nhap', 'tong_tien',
            'nguoi_nhap',  # Gán server-side trong PhieuNhapKhoViewSet.perform_create
            'da_duyet_chi', 'nguoi_duyet_chi', 'ngay_duyet_chi',
            'da_cap_nhat_kho',
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        loai = attrs.get('loai_nhap')
        ct_t = request.data.get('chi_tiet_thuoc')
        ct_v = request.data.get('chi_tiet_vaccine')
        if not isinstance(ct_t, list):
            ct_t = []
        if not isinstance(ct_v, list):
            ct_v = []

        if loai == 'THUOC':
            if not ct_t:
                raise serializers.ValidationError(
                    {'chi_tiet_thuoc': 'Thêm ít nhất một dòng thuốc.'}
                )
            if ct_v:
                raise serializers.ValidationError(
                    {'chi_tiet_vaccine': 'Phiếu nhập thuốc không được kèm dòng vaccine.'}
                )
            for i, row in enumerate(ct_t):
                if not isinstance(row, dict):
                    raise serializers.ValidationError(
                        {'chi_tiet_thuoc': f'Dòng {i + 1}: dữ liệu không hợp lệ.'}
                    )
                tid = row.get('thuoc')
                if not tid:
                    raise serializers.ValidationError(
                        {'chi_tiet_thuoc': f'Dòng {i + 1}: thiếu thuốc.'}
                    )
                if not Thuoc.objects.filter(pk=tid).exists():
                    raise serializers.ValidationError(
                        {'chi_tiet_thuoc': f'Dòng {i + 1}: thuốc không tồn tại hoặc không khớp loại phiếu.'}
                    )
                sl = row.get('so_luong')
                try:
                    sl = int(sl)
                except (TypeError, ValueError):
                    sl = 0
                if sl < 1:
                    raise serializers.ValidationError(
                        {'chi_tiet_thuoc': f'Dòng {i + 1}: số lượng phải ≥ 1.'}
                    )
        elif loai == 'VACCINE':
            if not ct_v:
                raise serializers.ValidationError(
                    {'chi_tiet_vaccine': 'Thêm ít nhất một dòng vaccine.'}
                )
            if ct_t:
                raise serializers.ValidationError(
                    {'chi_tiet_thuoc': 'Phiếu nhập vaccine không được kèm dòng thuốc.'}
                )
            for i, row in enumerate(ct_v):
                if not isinstance(row, dict):
                    raise serializers.ValidationError(
                        {'chi_tiet_vaccine': f'Dòng {i + 1}: dữ liệu không hợp lệ.'}
                    )
                vid = row.get('vaccine')
                if not vid:
                    raise serializers.ValidationError(
                        {'chi_tiet_vaccine': f'Dòng {i + 1}: thiếu vaccine.'}
                    )
                if not Vaccine.objects.filter(pk=vid).exists():
                    raise serializers.ValidationError(
                        {'chi_tiet_vaccine': f'Dòng {i + 1}: vaccine không tồn tại hoặc không khớp loại phiếu.'}
                    )
                sl = row.get('so_luong')
                try:
                    sl = int(sl)
                except (TypeError, ValueError):
                    sl = 0
                if sl < 1:
                    raise serializers.ValidationError(
                        {'chi_tiet_vaccine': f'Dòng {i + 1}: số lượng phải ≥ 1.'}
                    )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        chi_tiet_thuoc_data = request.data.get('chi_tiet_thuoc') or []
        chi_tiet_vaccine_data = request.data.get('chi_tiet_vaccine') or []
        if not isinstance(chi_tiet_thuoc_data, list):
            chi_tiet_thuoc_data = []
        if not isinstance(chi_tiet_vaccine_data, list):
            chi_tiet_vaccine_data = []

        loai = validated_data.get('loai_nhap')
        if loai == 'THUOC':
            chi_tiet_vaccine_data = []
        else:
            chi_tiet_thuoc_data = []

        vd = dict(validated_data)
        if not vd.get('nguoi_nhap'):
            u = request.user
            if u.is_authenticated:
                vd['nguoi_nhap'] = u.get_username()
        ma = (vd.get('ma_phieu') or '').strip()
        if not ma or PhieuNhapKho.objects.filter(ma_phieu=ma).exists():
            vd['ma_phieu'] = _sinh_ma_phieu_nhap()
        else:
            vd['ma_phieu'] = ma

        tong_tien = Decimal('0')
        with transaction.atomic():
            phieu_nhap = PhieuNhapKho.objects.create(**vd)

            if loai == 'THUOC':
                for row in chi_tiet_thuoc_data:
                    dg = row.get('don_gia', 0)
                    try:
                        don_gia = Decimal(str(dg if dg is not None else '0'))
                    except Exception:
                        don_gia = Decimal('0')
                    if don_gia < 0:
                        don_gia = Decimal('0')
                    han = row.get('han_su_dung')
                    if isinstance(han, str):
                        han = han.strip()[:10]
                    ct = ChiTietPhieuNhapThuoc.objects.create(
                        phieu_nhap=phieu_nhap,
                        thuoc_id=row['thuoc'],
                        so_luong=int(row['so_luong']),
                        don_gia=don_gia,
                        han_su_dung=han,
                        lo_sx=(row.get('lo_sx') or '')[:100],
                    )
                    tong_tien += ct.thanh_tien()
            else:
                for row in chi_tiet_vaccine_data:
                    dg = row.get('don_gia', 0)
                    try:
                        don_gia = Decimal(str(dg if dg is not None else '0'))
                    except Exception:
                        don_gia = Decimal('0')
                    if don_gia < 0:
                        don_gia = Decimal('0')
                    han = row.get('han_su_dung')
                    if isinstance(han, str):
                        han = han.strip()[:10]
                    ct = ChiTietPhieuNhapVaccine.objects.create(
                        phieu_nhap=phieu_nhap,
                        vaccine_id=row['vaccine'],
                        so_luong=int(row['so_luong']),
                        don_gia=don_gia,
                        han_su_dung=han,
                        lo_sx=(row.get('lo_sx') or '')[:100],
                    )
                    tong_tien += ct.thanh_tien()

            phieu_nhap.tong_tien = tong_tien
            phieu_nhap.save(update_fields=['tong_tien'])

        return phieu_nhap

# ==================== SERIALIZERS CHO TOA THUỐC MẪU ====================

class ChiTietToaMauSerializer(serializers.ModelSerializer):
    ten_thuoc = serializers.CharField(source='thuoc.ten_thuoc', read_only=True)
    don_gia = serializers.DecimalField(source='thuoc.gia_ban', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ChiTietToaMau
        fields = '__all__'

class ToaThuocMauSerializer(serializers.ModelSerializer):
    chi_tiet = ChiTietToaMauSerializer(many=True, read_only=True)
    
    class Meta:
        model = ToaThuocMau
        fields = '__all__'