from django.contrib import admin
from .models import ThongBao, ThongBaoPhatHanh


@admin.register(ThongBao)
class ThongBaoAppAdmin(admin.ModelAdmin):
    list_display = ('tieu_de', 'nguoi_nhan', 'loai_thong_bao', 'ngay_tao', 'da_doc_luc')
    list_filter = ('loai_thong_bao',)
    search_fields = ('tieu_de', 'noi_dung')


@admin.register(ThongBaoPhatHanh)
class ThongBaoPhatHanhAdmin(admin.ModelAdmin):
    list_display = (
        'tieu_de', 'pham_vi', 'loai_thong_bao', 'nguoi_gui',
        'thoi_gian_gui', 'so_nguoi_nhan',
    )
    list_filter = ('pham_vi', 'loai_thong_bao')
    search_fields = ('tieu_de', 'noi_dung')
    readonly_fields = ('so_nguoi_nhan', 'created_at')
