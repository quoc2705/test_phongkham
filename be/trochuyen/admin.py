from django.contrib import admin
from .models import PhongChat, TinNhan, ThanhVienPhong, TinNhanDaXem


@admin.register(PhongChat)
class PhongChatAdmin(admin.ModelAdmin):
    list_display = [
        'ma_phong',
        'ten_phong',
        'loai_phong',
        'trang_thai',
        'benh_nhan',
        'ten_nguoi_tu_van',
        'ngay_tao',
    ]
    list_filter = ['loai_phong', 'trang_thai', 'ngay_tao']
    search_fields = ['ma_phong', 'ten_phong', 'benh_nhan__nguoi_dung__ho_ten']
    readonly_fields = ['ma_phong', 'ngay_tao', 'ngay_cap_nhat']

    def ten_nguoi_tu_van(self, obj):
        return obj.ten_nguoi_tu_van

    ten_nguoi_tu_van.short_description = 'Nguoi tu van'


@admin.register(TinNhan)
class TinNhanAdmin(admin.ModelAdmin):
    list_display = ['id', 'phong_chat', 'nguoi_gui', 'loai', 'noi_dung_short', 'ngay_gui']
    list_filter = ['loai', 'ngay_gui']
    search_fields = ['noi_dung', 'phong_chat__ma_phong']
    readonly_fields = ['id', 'ngay_gui', 'ngay_xem']
    list_per_page = 20

    def noi_dung_short(self, obj):
        t = obj.noi_dung or ''
        return (t[:60] + '...') if len(t) > 60 else t

    noi_dung_short.short_description = 'Noi dung'


@admin.register(TinNhanDaXem)
class TinNhanDaXemAdmin(admin.ModelAdmin):
    list_display = ['tin_nhan', 'nguoi_dung', 'da_xem_luc']
    list_filter = ['da_xem_luc']


@admin.register(ThanhVienPhong)
class ThanhVienPhongAdmin(admin.ModelAdmin):
    list_display = ['phong_chat', 'nguoi_dung', 'vai_tro', 'ngay_tham_gia', 'is_active']
    list_filter = ['is_active', 'vai_tro', 'ngay_tham_gia']
    search_fields = ['phong_chat__ma_phong', 'nguoi_dung__ho_ten']
