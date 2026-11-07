from rest_framework import serializers
from django.utils import timezone

from nguoidung.models import NguoiDung, NhanVien

from .models import ThongBao, ThongBaoPhatHanh
from .services import CHUC_VU_PHAT_HANH, dem_nguoi_nhan_du_kien


class ThongBaoSerializer(serializers.ModelSerializer):
    loai_thong_bao_display = serializers.CharField(
        source='get_loai_thong_bao_display', read_only=True
    )

    class Meta:
        model = ThongBao
        fields = [
            'id', 'loai_thong_bao', 'loai_thong_bao_display', 'tieu_de',
            'noi_dung', 'da_doc', 'ngay_tao', 'lien_ket',
        ]
        read_only_fields = ['id', 'ngay_tao']


class ThongBaoPhatHanhSerializer(serializers.ModelSerializer):
    loai_thong_bao_display = serializers.CharField(
        source='get_loai_thong_bao_display', read_only=True
    )
    pham_vi_display = serializers.CharField(source='get_pham_vi_display', read_only=True)
    ten_nguoi_gui = serializers.CharField(source='nguoi_gui.ho_ten', read_only=True)
    ten_nguoi_nhan = serializers.SerializerMethodField()
    vai_tro_display = serializers.SerializerMethodField()
    chuc_vu_display = serializers.SerializerMethodField()

    class Meta:
        model = ThongBaoPhatHanh
        fields = [
            'id', 'tieu_de', 'noi_dung', 'loai_thong_bao', 'loai_thong_bao_display',
            'pham_vi', 'pham_vi_display', 'vai_tro', 'vai_tro_display',
            'chuc_vu', 'chuc_vu_display', 'nguoi_nhan', 'ten_nguoi_nhan',
            'nguoi_gui', 'ten_nguoi_gui', 'thoi_gian_gui', 'so_nguoi_nhan',
            'created_at',
        ]
        read_only_fields = [
            'id', 'tieu_de', 'noi_dung', 'loai_thong_bao', 'loai_thong_bao_display',
            'pham_vi', 'pham_vi_display', 'vai_tro', 'vai_tro_display',
            'chuc_vu', 'chuc_vu_display', 'nguoi_nhan', 'ten_nguoi_nhan',
            'nguoi_gui', 'ten_nguoi_gui', 'thoi_gian_gui', 'so_nguoi_nhan',
            'created_at',
        ]

    def get_ten_nguoi_nhan(self, obj):
        if obj.nguoi_nhan_id:
            return obj.nguoi_nhan.ho_ten
        return None

    def get_vai_tro_display(self, obj):
        if not obj.vai_tro:
            return None
        return dict(NguoiDung.VAI_TRO_CHOICES).get(obj.vai_tro, obj.vai_tro)

    def get_chuc_vu_display(self, obj):
        if not obj.chuc_vu:
            return None
        return dict(NhanVien.CHUC_VU_CHOICES).get(obj.chuc_vu, obj.chuc_vu)


class TaoThongBaoPhatHanhSerializer(serializers.Serializer):
    tieu_de = serializers.CharField(max_length=255)
    noi_dung = serializers.CharField()
    loai_thong_bao = serializers.ChoiceField(
        choices=ThongBaoPhatHanh.LoaiThongBao.choices,
        default=ThongBaoPhatHanh.LoaiThongBao.HE_THONG,
    )
    pham_vi = serializers.ChoiceField(choices=ThongBaoPhatHanh.PhamVi.choices)
    vai_tro = serializers.CharField(required=False, allow_blank=True)
    chuc_vu = serializers.CharField(required=False, allow_blank=True)
    nguoi_nhan_id = serializers.UUIDField(required=False, allow_null=True)
    thoi_gian_gui = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        pham_vi = attrs.get('pham_vi')
        vai_tro = (attrs.get('vai_tro') or '').strip()
        chuc_vu = (attrs.get('chuc_vu') or '').strip()
        nguoi_nhan_id = attrs.get('nguoi_nhan_id')

        if pham_vi == ThongBaoPhatHanh.PhamVi.VAI_TRO:
            if not vai_tro:
                raise serializers.ValidationError({'vai_tro': 'Chọn vai trò người nhận.'})
            hop_le = {c[0] for c in NguoiDung.VAI_TRO_CHOICES}
            if vai_tro not in hop_le:
                raise serializers.ValidationError({'vai_tro': 'Vai trò không hợp lệ.'})
            attrs['vai_tro'] = vai_tro

        elif pham_vi == ThongBaoPhatHanh.PhamVi.CHUC_VU:
            if not chuc_vu:
                raise serializers.ValidationError({'chuc_vu': 'Chọn chức vụ nhân viên.'})
            if chuc_vu not in CHUC_VU_PHAT_HANH:
                raise serializers.ValidationError({'chuc_vu': 'Chức vụ không được phép gửi thông báo.'})
            attrs['chuc_vu'] = chuc_vu

        elif pham_vi == ThongBaoPhatHanh.PhamVi.NGUOI_DUNG:
            if not nguoi_nhan_id:
                raise serializers.ValidationError(
                    {'nguoi_nhan_id': 'Chọn người dùng nhận thông báo.'}
                )
            if not NguoiDung.objects.filter(pk=nguoi_nhan_id, is_active=True).exists():
                raise serializers.ValidationError(
                    {'nguoi_nhan_id': 'Người dùng không tồn tại hoặc đã bị khóa.'}
                )
        else:
            attrs['vai_tro'] = ''
            attrs['chuc_vu'] = ''

        so = dem_nguoi_nhan_du_kien(
            pham_vi,
            attrs.get('vai_tro', ''),
            attrs.get('chuc_vu', ''),
            str(nguoi_nhan_id) if nguoi_nhan_id else None,
        )
        if so < 1:
            raise serializers.ValidationError(
                'Không có người nhận phù hợp với phạm vi đã chọn.'
            )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        nguoi_nhan_id = validated_data.pop('nguoi_nhan_id', None)
        thoi_gian_gui = validated_data.pop('thoi_gian_gui', None) or timezone.now()

        nguoi_nhan = None
        if nguoi_nhan_id:
            nguoi_nhan = NguoiDung.objects.filter(pk=nguoi_nhan_id).first()

        return ThongBaoPhatHanh.objects.create(
            nguoi_gui=request.user,
            nguoi_nhan=nguoi_nhan,
            thoi_gian_gui=thoi_gian_gui,
            so_nguoi_nhan=0,
            **validated_data,
        )
