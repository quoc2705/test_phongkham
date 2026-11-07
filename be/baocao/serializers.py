from rest_framework import serializers
from .models import BaoCao, MauBaoCao

class BaoCaoSerializer(serializers.ModelSerializer):
    nguoi_tao = serializers.StringRelatedField()
    
    class Meta:
        model = BaoCao
        fields = ['id', 'ten_bao_cao', 'loai', 'thoi_gian_bat_dau',
                 'thoi_gian_ket_thuc', 'du_lieu', 'ngay_tao', 'nguoi_tao']
        read_only_fields = ['id', 'ngay_tao', 'nguoi_tao']

class TaoBaoCaoSerializer(serializers.Serializer):
    loai_bao_cao = serializers.ChoiceField(choices=BaoCao.LoaiBaoCao.choices)
    thoi_gian_bat_dau = serializers.DateField()
    thoi_gian_ket_thuc = serializers.DateField()
    ten_bao_cao = serializers.CharField(max_length=255, required=False)
    
    def validate(self, data):
        if data['thoi_gian_bat_dau'] > data['thoi_gian_ket_thuc']:
            raise serializers.ValidationError("Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc")
        return data

class MauBaoCaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MauBaoCao
        fields = ['id', 'ten_mau', 'loai_bao_cao', 'tham_so', 'mo_ta']

class ThongKeTongQuanSerializer(serializers.Serializer):
    """Serializer cho thống kê tổng quan"""
    tong_benh_nhan = serializers.IntegerField()
    benh_nhan_moi_thang = serializers.IntegerField()
    tong_doanh_thu_thang = serializers.DecimalField(max_digits=12, decimal_places=2)
    doanh_thu_ngay = serializers.DecimalField(max_digits=12, decimal_places=2)
    so_lich_hen_hom_nay = serializers.IntegerField()
    thuoc_sap_het_han = serializers.IntegerField()