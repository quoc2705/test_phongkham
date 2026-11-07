from rest_framework import serializers
from django.utils import timezone
from .models import *
from nguoidung.serializers import BenhNhanSerializer, BacSiSerializer
from thuoc.serializers import ThuocSerializer, VaccineSerializer

# ==================== SERIALIZERS CHO HỒ SƠ BỆNH ÁN ====================

class HoSoBenhAnSerializer(serializers.ModelSerializer):
    """Serializer cho hồ sơ bệnh án"""
    ten_benh_nhan = serializers.CharField(source='benh_nhan.nguoi_dung.ho_ten', read_only=True)
    ma_benh_nhan = serializers.CharField(source='benh_nhan.ma_benh_nhan', read_only=True)
    ten_bac_si = serializers.CharField(source='bac_si.nguoi_dung.ho_ten', read_only=True)
    tuoi = serializers.SerializerMethodField()
    loai_kham_display = serializers.CharField(source='get_loai_kham_display', read_only=True)
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    
    class Meta:
        model = HoSoBenhAn
        fields = '__all__'
        read_only_fields = ['ma_hs', 'ngay_tao', 'ngay_cap_nhat']
    
    def get_tuoi(self, obj):
        return obj.tuoi_benh_nhan()

class HoSoBenhAnChiTietSerializer(HoSoBenhAnSerializer):
    """Serializer chi tiết hồ sơ bệnh án kèm các thông tin liên quan"""
    benh_nhan = BenhNhanSerializer(read_only=True)
    bac_si = BacSiSerializer(read_only=True)
    chan_doan = serializers.SerializerMethodField()
    don_thuoc = serializers.SerializerMethodField()
    lich_hen = serializers.SerializerMethodField()
    theo_doi = serializers.SerializerMethodField()
    
    class Meta(HoSoBenhAnSerializer.Meta):
        fields = '__all__'
    
    def get_chan_doan(self, obj):
        if hasattr(obj, 'chan_doan'):
            return ChanDoanSerializer(obj.chan_doan).data
        return None
    
    def get_don_thuoc(self, obj):
        return DonThuocSerializer(obj.don_thuoc.all(), many=True).data
    
    def get_lich_hen(self, obj):
        return LichHenTaiKhamSerializer(obj.lich_hen.all(), many=True).data
    
    def get_theo_doi(self, obj):
        return TheoDoiDieuTriSerializer(obj.theo_doi.all(), many=True).data

class HoSoBenhAnCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo/cập nhật hồ sơ bệnh án"""
    class Meta:
        model = HoSoBenhAn
        fields = '__all__'
        read_only_fields = ['ma_hs', 'ngay_tao', 'ngay_cap_nhat']
    
    def validate(self, data):
        """Validate dữ liệu đầu vào"""
        if data.get('chieu_cao') and data.get('can_nang'):
            # Tính BMI nếu có cả chiều cao và cân nặng
            height_in_m = data['chieu_cao'] / 100
            bmi = data['can_nang'] / (height_in_m * height_in_m)
            if bmi < 15 or bmi > 40:
                raise serializers.ValidationError(
                    "Chỉ số BMI không hợp lệ. Vui lòng kiểm tra lại chiều cao/cân nặng"
                )
        return data

# ==================== SERIALIZERS CHO CHẨN ĐOÁN ====================

class ChanDoanSerializer(serializers.ModelSerializer):
    """Serializer cho chẩn đoán"""
    ma_hs = serializers.CharField(source='ho_so.ma_hs', read_only=True)
    ten_benh_nhan = serializers.CharField(source='ho_so.benh_nhan.nguoi_dung.ho_ten', read_only=True)
    ten_bac_si = serializers.CharField(source='bac_si_chan_doan.nguoi_dung.ho_ten', read_only=True)
    loai_benh_display = serializers.CharField(source='get_loai_benh_display', read_only=True)
    muc_do_display = serializers.CharField(source='get_muc_do_display', read_only=True)
    
    class Meta:
        model = ChanDoan
        fields = '__all__'
        read_only_fields = ['ngay_chan_doan', 'ngay_cap_nhat']

class ChanDoanCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo/cập nhật chẩn đoán"""
    class Meta:
        model = ChanDoan
        fields = '__all__'
        read_only_fields = ['ngay_chan_doan', 'ngay_cap_nhat']
    
    def validate_ma_icd10(self, value):
        """Validate mã ICD-10 (tùy chọn)"""
        v = (value or '').strip()
        if len(v) > 10:
            raise serializers.ValidationError("Mã ICD-10 không được quá 10 ký tự")
        return v.upper() if v else ''

# ==================== SERIALIZERS CHO ĐƠN THUỐC =================

class ChiTietDonThuocSerializer(serializers.ModelSerializer):
    """Serializer cho chi tiết đơn thuốc (đọc + ghi)"""
    ten_thuoc = serializers.SerializerMethodField()
    ma_thuoc = serializers.SerializerMethodField()
    don_vi = serializers.SerializerMethodField()
    thanh_tien = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    cach_dung_display = serializers.CharField(source='get_cach_dung_display', read_only=True)
    thoi_diem_display = serializers.CharField(source='get_thoi_diem_display', read_only=True)

    def get_ten_thuoc(self, obj):
        if getattr(obj, 'la_thuoc_mua_ngoai', False):
            return (obj.ten_thuoc_tu_do or '').strip()
        return obj.thuoc.ten_thuoc if obj.thuoc else ''

    def get_ma_thuoc(self, obj):
        if getattr(obj, 'la_thuoc_mua_ngoai', False):
            return ''
        return obj.thuoc.ma_thuoc if obj.thuoc else ''

    def get_don_vi(self, obj):
        if getattr(obj, 'la_thuoc_mua_ngoai', False):
            return ''
        if obj.thuoc and obj.thuoc.don_vi:
            return obj.thuoc.don_vi.ten_don_vi
        return ''

    class Meta:
        model = ChiTietDonThuoc
        fields = '__all__'
        read_only_fields = ['don_gia_tai_thoi_diem']
    
    def validate(self, data):
        if data.get('so_luong', 0) <= 0:
            raise serializers.ValidationError({'so_luong': 'Số lượng phải lớn hơn 0'})
        la_ngoai = data.get('la_thuoc_mua_ngoai', getattr(self.instance, 'la_thuoc_mua_ngoai', False))
        if data.get('la_thuoc_mua_ngoai', False) or la_ngoai:
            if not (data.get('ten_thuoc_tu_do') or '').strip():
                raise serializers.ValidationError(
                    {'ten_thuoc_tu_do': 'Nhập tên thuốc khi mua ngoài / không có trong danh mục.'}
                )
            data['la_thuoc_mua_ngoai'] = True
            data['thuoc'] = None
            return data
        if not data.get('thuoc'):
            raise serializers.ValidationError(
                {'thuoc': 'Chọn thuốc trong danh mục hoặc đánh dấu thuốc mua ngoài.'}
            )
        # Kê đơn không chặn tồn kho — nhân viên quầy kiểm tra khi bán
        return data

class DonThuocSerializer(serializers.ModelSerializer):
    """Serializer cho đơn thuốc"""
    ten_benh_nhan = serializers.CharField(source='benh_nhan.nguoi_dung.ho_ten', read_only=True)
    ma_benh_nhan = serializers.CharField(source='benh_nhan.ma_benh_nhan', read_only=True)
    ten_bac_si = serializers.CharField(source='bac_si.nguoi_dung.ho_ten', read_only=True)
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    phuong_thuc_thanh_toan_display = serializers.CharField(
        source='get_phuong_thuc_thanh_toan_display', read_only=True
    )
    chi_tiet = ChiTietDonThuocSerializer(source='chi_tiet_don_thuoc', many=True, read_only=True)
    
    class Meta:
        model = DonThuoc
        fields = '__all__'
        read_only_fields = ['ma_don', 'ngay_tao', 'ngay_cap_nhat', 'tong_tien', 
                           'so_tien_bao_hiem', 'so_tien_benh_nhan_tra']

class DonThuocCreateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo đơn thuốc mới"""
    chi_tiet = ChiTietDonThuocSerializer(many=True, required=False, allow_empty=True)
    
    class Meta:
        model = DonThuoc
        fields = '__all__'
        read_only_fields = ['ma_don', 'ngay_tao', 'ngay_cap_nhat', 'tong_tien']
    
    def create(self, validated_data):
        chi_tiet_data = validated_data.pop('chi_tiet', [])
        don_thuoc = DonThuoc.objects.create(**validated_data)
        
        # Tạo chi tiết đơn thuốc
        for ct_data in chi_tiet_data:
            ct_data = dict(ct_data)
            ct_data.pop('don_thuoc', None)
            ct_data.pop('id', None)
            ChiTietDonThuoc.objects.create(don_thuoc=don_thuoc, **ct_data)
        
        # Tính tổng tiền
        don_thuoc.tinh_tong_tien()
        
        return don_thuoc

class DonThuocUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho cập nhật đơn thuốc"""
    class Meta:
        model = DonThuoc
        fields = ['trang_thai', 'can_tu_van', 'ghi_chu']
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class DonThuocThanhToanSerializer(serializers.Serializer):
    """Serializer cho thanh toán đơn thuốc"""
    phuong_thuc_thanh_toan = serializers.ChoiceField(
        choices=DonThuoc.PHUONG_THUC_THANH_TOAN_CHOICES
    )
    ma_giao_dich = serializers.CharField(required=False, allow_blank=True)
    ma_bao_hiem = serializers.CharField(required=False, allow_blank=True)
    ty_le_bao_hiem = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=0
    )
    
    def validate_ty_le_bao_hiem(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Tỷ lệ bảo hiểm phải từ 0-100%")
        return value

# ==================== SERIALIZERS CHO PHIẾU XUẤT THUỐC ====================

class ChiTietXuatThuocSerializer(serializers.ModelSerializer):
    """Serializer cho chi tiết xuất thuốc"""
    ten_thuoc = serializers.CharField(source='kho_thuoc.thuoc.ten_thuoc', read_only=True)
    lo_sx = serializers.CharField(source='kho_thuoc.lo_sx', read_only=True)
    han_su_dung = serializers.DateField(source='kho_thuoc.han_su_dung', read_only=True)
    thanh_tien = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = ChiTietXuatThuoc
        fields = '__all__'
    
    def validate_so_luong_xuat(self, value):
        if value <= 0:
            raise serializers.ValidationError("Số lượng xuất phải lớn hơn 0")
        return value

class PhieuXuatThuocSerializer(serializers.ModelSerializer):
    """Serializer cho phiếu xuất thuốc"""
    ten_nguoi_xuat = serializers.CharField(source='nguoi_xuat.nguoi_dung.ho_ten', read_only=True)
    ma_don_thuoc = serializers.CharField(source='don_thuoc.ma_don', read_only=True)
    chi_tiet = ChiTietXuatThuocSerializer(many=True, read_only=True)
    
    class Meta:
        model = PhieuXuatThuoc
        fields = '__all__'
        read_only_fields = ['ma_phieu', 'ngay_xuat']

class PhieuXuatThuocCreateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo phiếu xuất thuốc"""
    chi_tiet = ChiTietXuatThuocSerializer(many=True)
    
    class Meta:
        model = PhieuXuatThuoc
        fields = ['don_thuoc', 'nguoi_xuat', 'ghi_chu', 'chi_tiet']
    
    def create(self, validated_data):
        chi_tiet_data = validated_data.pop('chi_tiet')
        phieu_xuat = PhieuXuatThuoc.objects.create(**validated_data)
        
        # Tạo chi tiết xuất và cập nhật kho
        for ct_data in chi_tiet_data:
            ChiTietXuatThuoc.objects.create(phieu_xuat=phieu_xuat, **ct_data)
            
            # Cập nhật số lượng trong kho
            kho = ct_data['kho_thuoc']
            kho.so_luong -= ct_data['so_luong_xuat']
            kho.save()
        
        return phieu_xuat

# ==================== SERIALIZERS CHO LỊCH SỬ TIÊM CHỦNG ====================

class LichSuTiemChungSerializer(serializers.ModelSerializer):
    """Serializer cho lịch sử tiêm chủng"""
    ten_benh_nhan = serializers.CharField(source='benh_nhan.nguoi_dung.ho_ten', read_only=True)
    ma_benh_nhan = serializers.CharField(source='benh_nhan.ma_benh_nhan', read_only=True)
    ten_vaccine = serializers.CharField(source='vaccine.ten_vaccine', read_only=True)
    ten_nguoi_tiem = serializers.CharField(source='nguoi_tiem.nguoi_dung.ho_ten', read_only=True)
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    phan_ung_display = serializers.CharField(source='get_phan_ung_sau_tiem_display', read_only=True)
    
    class Meta:
        model = LichSuTiemChung
        fields = '__all__'
        read_only_fields = ['ma_lich', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate dữ liệu tiêm chủng"""
        if data.get('ngay_tiem') and data.get('ngay_tiem_tiep_theo'):
            if data['ngay_tiem_tiep_theo'] <= data['ngay_tiem']:
                raise serializers.ValidationError(
                    {"ngay_tiem_tiep_theo": "Ngày tiêm tiếp theo phải sau ngày tiêm hiện tại"}
                )
        
        # Kiểm tra số mũi
        if data.get('so_mui', 1) < 1:
            raise serializers.ValidationError({"so_mui": "Số mũi phải lớn hơn 0"})
        
        return data

class LichSuTiemChungCreateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo lịch tiêm mới"""
    class Meta:
        model = LichSuTiemChung
        fields = '__all__'
        read_only_fields = ['ma_lich', 'created_at', 'updated_at']

# ==================== SERIALIZERS CHO TOA THUỐC MẪU ====================

class ChiTietToaMauSerializer(serializers.ModelSerializer):
    """Serializer cho chi tiết toa thuốc mẫu"""
    ten_thuoc = serializers.CharField(source='thuoc.ten_thuoc', read_only=True)
    ma_thuoc = serializers.CharField(source='thuoc.ma_thuoc', read_only=True)
    don_vi = serializers.CharField(source='thuoc.don_vi.ten_don_vi', read_only=True)
    don_gia_hien_tai = serializers.DecimalField(
        source='thuoc.gia_ban', max_digits=10, decimal_places=2, read_only=True
    )
    thanh_tien = serializers.SerializerMethodField()
    cach_dung_display = serializers.CharField(source='get_cach_dung_display', read_only=True)
    thoi_diem_display = serializers.CharField(source='get_thoi_diem_display', read_only=True)
    
    class Meta:
        model = ChiTietToaMau
        fields = '__all__'
    
    def get_thanh_tien(self, obj):
        return obj.thanh_tien_mau()

class ToaThuocMauSerializer(serializers.ModelSerializer):
    """Serializer cho toa thuốc mẫu"""
    ten_bac_si_tao = serializers.CharField(source='bac_si_tao.nguoi_dung.ho_ten', read_only=True)
    chi_tiet = ChiTietToaMauSerializer(many=True, read_only=True)
    tong_tien = serializers.SerializerMethodField()
    
    class Meta:
        model = ToaThuocMau
        fields = '__all__'
        read_only_fields = ['so_luot_dung', 'created_at', 'updated_at']
    
    def get_tong_tien(self, obj):
        return sum(ct.thanh_tien_mau() for ct in obj.chi_tiet.all())

class ToaThuocMauCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo/cập nhật toa thuốc mẫu"""
    chi_tiet = ChiTietToaMauSerializer(many=True, required=False)
    
    class Meta:
        model = ToaThuocMau
        fields = '__all__'
        read_only_fields = ['so_luot_dung', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        chi_tiet_data = validated_data.pop('chi_tiet', [])
        toa_mau = ToaThuocMau.objects.create(**validated_data)
        
        for ct_data in chi_tiet_data:
            ChiTietToaMau.objects.create(toa_thuoc=toa_mau, **ct_data)
        
        return toa_mau
    
    def update(self, instance, validated_data):
        chi_tiet_data = validated_data.pop('chi_tiet', None)
        
        # Cập nhật thông tin cơ bản
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Cập nhật chi tiết nếu có
        if chi_tiet_data is not None:
            instance.chi_tiet.all().delete()
            for ct_data in chi_tiet_data:
                ChiTietToaMau.objects.create(toa_thuoc=instance, **ct_data)
        
        return instance

# ==================== SERIALIZERS CHO LỊCH HẸN TÁI KHÁM ====================

class LichHenTaiKhamSerializer(serializers.ModelSerializer):
    """Serializer cho lịch hẹn tái khám"""
    ten_benh_nhan = serializers.CharField(source='benh_nhan.nguoi_dung.ho_ten', read_only=True)
    ma_benh_nhan = serializers.CharField(source='benh_nhan.ma_benh_nhan', read_only=True)
    ten_bac_si = serializers.CharField(source='bac_si.nguoi_dung.ho_ten', read_only=True)
    ma_hs = serializers.CharField(source='ho_so.ma_hs', read_only=True)
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    
    class Meta:
        model = LichHenTaiKham
        fields = '__all__'
        read_only_fields = ['ma_hen', 'created_at', 'updated_at', 'da_nhac']
    
    def validate_ngay_hen(self, value):
        """Validate ngày hẹn không được trong quá khứ"""
        if value < timezone.now():
            raise serializers.ValidationError("Ngày hẹn không thể trong quá khứ")
        return value

class LichHenTaiKhamCreateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo lịch hẹn mới"""
    class Meta:
        model = LichHenTaiKham
        fields = '__all__'
        read_only_fields = ['ma_hen', 'created_at', 'updated_at', 'da_nhac']

# ==================== SERIALIZERS CHO THEO DÕI ĐIỀU TRỊ ====================

class TheoDoiDieuTriSerializer(serializers.ModelSerializer):
    """Serializer cho theo dõi điều trị"""
    ten_benh_nhan = serializers.CharField(source='ho_so.benh_nhan.nguoi_dung.ho_ten', read_only=True)
    ma_hs = serializers.CharField(source='ho_so.ma_hs', read_only=True)
    ten_bac_si = serializers.CharField(source='bac_si.nguoi_dung.ho_ten', read_only=True)
    
    class Meta:
        model = TheoDoiDieuTri
        fields = '__all__'
        read_only_fields = ['ngay_theo_doi']
    
    def validate_chi_so_sinh_ton(self, value):
        """Validate chỉ số sinh tồn"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Chỉ số sinh tồn phải là dạng JSON object")
        
        # Kiểm tra các chỉ số cơ bản
        allowed_keys = ['huyet_ap', 'nhiet_do', 'mach', 'nhip_tho', 'spO2', 'can_nang']
        for key in value.keys():
            if key not in allowed_keys:
                raise serializers.ValidationError(f"Chỉ số '{key}' không được hỗ trợ")
        
        return value

# ==================== SERIALIZERS CHO DASHBOARD ====================

class ThongKeDonThuocSerializer(serializers.Serializer):
    """Serializer cho thống kê đơn thuốc"""
    tong_don = serializers.IntegerField()
    tong_tien = serializers.DecimalField(max_digits=15, decimal_places=2)
    don_trung_binh = serializers.DecimalField(max_digits=10, decimal_places=2)
    don_cao_nhat = serializers.DecimalField(max_digits=10, decimal_places=2)
    don_thap_nhat = serializers.DecimalField(max_digits=10, decimal_places=2)

class ThongKeBenhNhanSerializer(serializers.Serializer):
    """Serializer cho thống kê bệnh nhân"""
    tong_benh_nhan = serializers.IntegerField()
    benh_nhan_moi = serializers.IntegerField()
    benh_nhan_tai_kham = serializers.IntegerField()
    ty_le_tai_kham = serializers.FloatField()

class ThongKeTheoNgaySerializer(serializers.Serializer):
    """Serializer cho thống kê theo ngày"""
    ngay = serializers.DateField()
    so_luong = serializers.IntegerField()
    tong_tien = serializers.DecimalField(max_digits=15, decimal_places=2)

# ==================== SERIALIZERS CHO IMPORT/EXPORT ====================

class DonThuocExportSerializer(serializers.ModelSerializer):
    """Serializer cho export đơn thuốc ra Excel/CSV"""
    ten_benh_nhan = serializers.CharField(source='benh_nhan.nguoi_dung.ho_ten')
    ma_benh_nhan = serializers.CharField(source='benh_nhan.ma_benh_nhan')
    ten_bac_si = serializers.CharField(source='bac_si.nguoi_dung.ho_ten')
    ngay_tao_str = serializers.DateTimeField(source='ngay_tao', format='%d/%m/%Y %H:%M')
    trang_thai_str = serializers.CharField(source='get_trang_thai_display')
    
    class Meta:
        model = DonThuoc
        fields = [
            'ma_don', 'ten_benh_nhan', 'ma_benh_nhan', 'ten_bac_si',
            'ngay_tao_str', 'tong_tien', 'trang_thai_str', 'da_thanh_toan'
        ]

class LichSuTiemChungExportSerializer(serializers.ModelSerializer):
    """Serializer cho export lịch sử tiêm chủng"""
    ten_benh_nhan = serializers.CharField(source='benh_nhan.nguoi_dung.ho_ten')
    ma_benh_nhan = serializers.CharField(source='benh_nhan.ma_benh_nhan')
    ten_vaccine = serializers.CharField(source='vaccine.ten_vaccine')
    ngay_tiem_str = serializers.DateField(source='ngay_tiem', format='%d/%m/%Y')
    trang_thai_str = serializers.CharField(source='get_trang_thai_display')
    
    class Meta:
        model = LichSuTiemChung
        fields = [
            'ma_lich', 'ten_benh_nhan', 'ma_benh_nhan', 'ten_vaccine',
            'so_mui', 'ngay_tiem_str', 'trang_thai_str'
        ]

# ==================== SERIALIZERS CHO BÁO CÁO ====================

class BaoCaoDoanhThuSerializer(serializers.Serializer):
    """Serializer cho báo cáo doanh thu"""
    tu_ngay = serializers.DateField()
    den_ngay = serializers.DateField()
    tong_doanh_thu = serializers.DecimalField(max_digits=15, decimal_places=2)
    tong_don_thuoc = serializers.IntegerField()
    doanh_thu_trung_binh = serializers.DecimalField(max_digits=10, decimal_places=2)
    doanh_thu_theo_ngay = ThongKeTheoNgaySerializer(many=True)
    doanh_thu_theo_phuong_thuc = serializers.DictField()

class BaoCaoThuocSerializer(serializers.Serializer):
    """Serializer cho báo cáo thuốc"""
    tu_ngay = serializers.DateField()
    den_ngay = serializers.DateField()
    tong_loai_thuoc = serializers.IntegerField()
    tong_luot_ke = serializers.IntegerField()
    tong_so_luong = serializers.IntegerField()
    top_thuoc = serializers.ListField(child=serializers.DictField())

class BaoCaoTiemChungSerializer(serializers.Serializer):
    """Serializer cho báo cáo tiêm chủng"""
    tu_ngay = serializers.DateField()
    den_ngay = serializers.DateField()
    tong_luot_tiem = serializers.IntegerField()
    tong_benh_nhan = serializers.IntegerField()
    ty_le_phan_ung = serializers.DictField()
    thong_ke_vaccine = serializers.ListField(child=serializers.DictField())