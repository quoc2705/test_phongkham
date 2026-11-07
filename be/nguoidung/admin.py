from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *

# ==================== INLINES ====================

class BenhNhanInline(admin.StackedInline):
    model = BenhNhan
    can_delete = False
    verbose_name = 'Thông tin bệnh nhân'
    verbose_name_plural = 'Thông tin bệnh nhân'
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('ma_benh_nhan', 'ngay_sinh', 'gioi_tinh', 'dia_chi')
        }),
        ('Bảo hiểm y tế', {
            'fields': ('so_bao_hiem', 'ngay_dang_ky_bhyt', 'ngay_het_han_bhyt', 'noi_dang_ky_kham_chua'),
            'classes': ('collapse',)
        }),
        ('Thông tin y tế', {
            'fields': ('nhom_mau', 'chieu_cao', 'can_nang', 'tien_su_benh', 'tien_su_di_ung', 'benh_man_tinh'),
            'classes': ('collapse',)
        }),
        ('Thông tin nhân khẩu', {
            'fields': ('nghe_nghiep', 'noi_lam_viec', 'tinh_trang_hon_nhan'),
            'classes': ('collapse',)
        }),
        ('Người thân', {
            'fields': ('ho_ten_nguoi_than', 'quan_he_nguoi_than', 'sdt_nguoi_than'),
            'classes': ('collapse',)
        }),
    )

class BacSiInline(admin.StackedInline):
    model = BacSi
    can_delete = False
    verbose_name = 'Thông tin bác sĩ'
    verbose_name_plural = 'Thông tin bác sĩ'
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('ma_bac_si', 'chuyen_khoa', 'so_giay_phep')
        }),
        ('Chuyên môn', {
            'fields': ('trinh_do', 'chuc_vu', 'chuyen_mon'),
            'classes': ('collapse',)
        }),
        ('Công tác', {
            'fields': ('khoa_phong', 'ngay_bat_dau_cong_tac', 'ngay_ket_thuc_cong_tac', 'is_working'),
            'classes': ('collapse',)
        }),
        ('Chứng chỉ & Ngoại ngữ', {
            'fields': ('chung_chi', 'ngoai_ngu'),
            'classes': ('collapse',)
        }),
        ('Giới thiệu', {
            'fields': ('gioi_thieu', 'thanh_tich'),
            'classes': ('collapse',)
        }),
        ('Lịch làm việc', {
            'fields': ('lich_lam_viec',),
            'classes': ('collapse',)
        }),
    )

class NhanVienInline(admin.StackedInline):
    model = NhanVien
    can_delete = False
    verbose_name = 'Thông tin nhân viên'
    verbose_name_plural = 'Thông tin nhân viên'
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('ma_nhan_vien', 'phong_ban', 'chuc_vu')
        }),
        ('Công việc', {
            'fields': ('ngay_bat_dau_lam', 'mo_ta_cong_viec', 'is_working'),
            'classes': ('collapse',)
        }),
        ('Quyền hạn', {
            'fields': ('quyen_han',),
            'classes': ('collapse',)
        }),
    )

# ==================== ADMIN NGƯỜI DÙNG ====================

@admin.register(NguoiDung)
class NguoiDungAdmin(UserAdmin):
    list_display = ('username', 'ho_ten', 'email', 'so_dien_thoai', 'vai_tro', 'is_active', 'is_verified', 'last_login')
    list_filter = ('vai_tro', 'is_active', 'is_verified', 'is_locked', 'gioi_tinh')
    search_fields = ('ten_dang_nhap', 'ho_ten', 'email', 'so_dien_thoai', 'cccd')
    ordering = ('-ngay_tao',)
    
    fieldsets = (
        ('Thông tin đăng nhập', {
            'fields': ('ten_dang_nhap', 'password')
        }),
        ('Thông tin cá nhân', {
            'fields': ('ho_ten', 'email', 'so_dien_thoai', 'vai_tro', 'avatar')
        }),
        ('Thông tin chi tiết', {
            'fields': ('ngay_sinh', 'gioi_tinh', 'dia_chi', 'cccd'),
            'classes': ('collapse',)
        }),
        ('Liên hệ khẩn cấp', {
            'fields': ('nguoi_lien_he_khan', 'sdt_lien_he_khan'),
            'classes': ('collapse',)
        }),
        ('Bảo mật', {
            'fields': ('last_login_ip', 'last_login_device', 'password_changed_at'),
            'classes': ('collapse',)
        }),
        ('Trạng thái tài khoản', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 
                      'is_locked', 'locked_until', 'login_attempts', 'last_active', 'deleted_at')
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('last_login', 'ngay_tao', 'ngay_cap_nhat'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('ten_dang_nhap', 'password1', 'password2', 'ho_ten', 'email', 
                      'so_dien_thoai', 'vai_tro', 'is_active', 'is_staff'),
        }),
    )
    
    def username(self, obj):
        return obj.ten_dang_nhap
    username.short_description = 'Tên đăng nhập'
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.vai_tro == 'BENH_NHAN':
                return [BenhNhanInline]
            elif obj.vai_tro == 'BAC_SI':
                return [BacSiInline]
            elif obj.vai_tro == 'NHAN_VIEN':
                return [NhanVienInline]
        return []

# ==================== ADMIN BỆNH NHÂN ====================

@admin.register(BenhNhan)
class BenhNhanAdmin(admin.ModelAdmin):
    list_display = ('ma_benh_nhan', 'ho_ten', 'ngay_sinh', 'tuoi', 'gioi_tinh', 'so_dien_thoai', 'bhyt_status')
    list_filter = ('gioi_tinh', 'nhom_mau', 'nghe_nghiep', 'tinh_trang_hon_nhan')
    search_fields = ('ma_benh_nhan', 'nguoi_dung__ho_ten', 'nguoi_dung__so_dien_thoai', 'so_bao_hiem')
    readonly_fields = ('created_at', 'updated_at', 'get_bmi_info')
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('nguoi_dung', 'ma_benh_nhan', 'ngay_sinh', 'gioi_tinh', 'dia_chi')
        }),
        ('Bảo hiểm y tế', {
            'fields': ('so_bao_hiem', 'ngay_dang_ky_bhyt', 'ngay_het_han_bhyt', 'noi_dang_ky_kham_chua'),
            'classes': ('collapse',)
        }),
        ('Thông tin y tế', {
            'fields': ('nhom_mau', 'chieu_cao', 'can_nang', 'get_bmi_info',
                      'tien_su_benh', 'tien_su_di_ung', 'benh_man_tinh'),
            'classes': ('collapse',)
        }),
        ('Thông tin nhân khẩu', {
            'fields': ('nghe_nghiep', 'noi_lam_viec', 'tinh_trang_hon_nhan'),
            'classes': ('collapse',)
        }),
        ('Người thân', {
            'fields': ('ho_ten_nguoi_than', 'quan_he_nguoi_than', 'sdt_nguoi_than'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def ho_ten(self, obj):
        return obj.nguoi_dung.ho_ten
    ho_ten.short_description = 'Họ tên'
    
    def so_dien_thoai(self, obj):
        return obj.nguoi_dung.so_dien_thoai
    so_dien_thoai.short_description = 'SĐT'
    
    def tuoi(self, obj):
        return obj.tuoi()
    tuoi.short_description = 'Tuổi'
    
    def bhyt_status(self, obj):
        if obj.kiem_tra_bhyt_con_han():
            return format_html('<span style="color: green;">Còn hạn</span>')
        elif obj.so_bao_hiem:
            return format_html('<span style="color: red;">Hết hạn</span>')
        return format_html('<span style="color: gray;">Không có</span>')
    bhyt_status.short_description = 'BHYT'
    
    def get_bmi_info(self, obj):
        bmi = obj.get_bmi()
        phan_loai = obj.get_bmi_phan_loai()
        if bmi:
            return f"{bmi} - {phan_loai}"
        return "Chưa có dữ liệu"
    get_bmi_info.short_description = 'BMI'

# ==================== ADMIN BÁC SĨ ====================

@admin.register(BacSi)
class BacSiAdmin(admin.ModelAdmin):
    list_display = ('ma_bac_si', 'ho_ten', 'chuyen_khoa', 'trinh_do', 'chuc_vu', 'so_dien_thoai', 'danh_gia', 'is_working')
    list_filter = ('chuyen_khoa', 'trinh_do', 'chuc_vu', 'is_working')
    search_fields = ('ma_bac_si', 'nguoi_dung__ho_ten', 'so_giay_phep', 'chuyen_khoa')
    readonly_fields = ('created_at', 'updated_at', 'danh_gia')
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('nguoi_dung', 'ma_bac_si', 'chuyen_khoa', 'so_giay_phep')
        }),
        ('Chuyên môn', {
            'fields': ('trinh_do', 'chuc_vu', 'chuyen_mon'),
        }),
        ('Công tác', {
            'fields': ('khoa_phong', 'ngay_bat_dau_cong_tac', 'ngay_ket_thuc_cong_tac', 'is_working'),
        }),
        ('Chứng chỉ & Ngoại ngữ', {
            'fields': ('chung_chi', 'ngoai_ngu'),
            'classes': ('collapse',)
        }),
        ('Giới thiệu', {
            'fields': ('gioi_thieu', 'thanh_tich'),
            'classes': ('collapse',)
        }),
        ('Lịch làm việc', {
            'fields': ('lich_lam_viec',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def ho_ten(self, obj):
        return obj.nguoi_dung.ho_ten
    ho_ten.short_description = 'Họ tên'
    
    def so_dien_thoai(self, obj):
        return obj.nguoi_dung.so_dien_thoai
    so_dien_thoai.short_description = 'SĐT'
    
    def danh_gia(self, obj):
        avg = obj.danh_gia_trung_binh()
        stars = '★' * int(avg) + '☆' * (5 - int(avg))
        return format_html(f'{stars} ({avg})')
    danh_gia.short_description = 'Đánh giá'

# ==================== ADMIN NHÂN VIÊN ====================

@admin.register(NhanVien)
class NhanVienAdmin(admin.ModelAdmin):
    list_display = ('ma_nhan_vien', 'ho_ten', 'phong_ban', 'chuc_vu', 'so_dien_thoai', 'is_working')
    list_filter = ('phong_ban', 'chuc_vu', 'is_working')
    search_fields = ('ma_nhan_vien', 'nguoi_dung__ho_ten', 'phong_ban')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('nguoi_dung', 'ma_nhan_vien', 'phong_ban', 'chuc_vu')
        }),
        ('Công việc', {
            'fields': ('ngay_bat_dau_lam', 'mo_ta_cong_viec', 'is_working'),
        }),
        ('Quyền hạn', {
            'fields': ('quyen_han',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def ho_ten(self, obj):
        return obj.nguoi_dung.ho_ten
    ho_ten.short_description = 'Họ tên'
    
    def so_dien_thoai(self, obj):
        return obj.nguoi_dung.so_dien_thoai
    so_dien_thoai.short_description = 'SĐT'

# ==================== ADMIN CÁC MODEL KHÁC ====================

@admin.register(LichSuKhamBenh)
class LichSuKhamBenhAdmin(admin.ModelAdmin):
    list_display = ('benh_nhan', 'bac_si', 'ngay_kham', 'chuan_doan')
    list_filter = ('bac_si', 'ngay_kham')
    search_fields = ('benh_nhan__ma_benh_nhan', 'benh_nhan__nguoi_dung__ho_ten', 'chuan_doan')
    date_hierarchy = 'ngay_kham'

@admin.register(DanhGiaBacSi)
class DanhGiaBacSiAdmin(admin.ModelAdmin):
    list_display = ('benh_nhan', 'bac_si', 'diem', 'nhan_xet_ngan', 'created_at')
    list_filter = ('diem', 'bac_si')
    search_fields = ('benh_nhan__nguoi_dung__ho_ten', 'bac_si__nguoi_dung__ho_ten', 'nhan_xet')
    date_hierarchy = 'created_at'
    
    def nhan_xet_ngan(self, obj):
        if obj.nhan_xet:
            return obj.nhan_xet[:50] + '...' if len(obj.nhan_xet) > 50 else obj.nhan_xet
        return '-'
    nhan_xet_ngan.short_description = 'Nhận xét'

@admin.register(ThongBao)
class ThongBaoAdmin(admin.ModelAdmin):
    list_display = ('tieu_de', 'nguoi_nhan', 'loai', 'da_xem', 'created_at')
    list_filter = ('loai', 'da_xem')
    search_fields = ('tieu_de', 'noi_dung', 'nguoi_nhan__ho_ten')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(da_xem=True, ngay_xem=timezone.now())
    mark_as_read.short_description = "Đánh dấu đã xem"

@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ('bac_si', 'ngay_lam', 'ca_lam', 'ghi_chu', 'created_at')
    list_filter = ('ca_lam', 'ngay_lam')
    search_fields = ('bac_si__ma_bac_si', 'bac_si__nguoi_dung__ho_ten')
    date_hierarchy = 'ngay_lam'


@admin.register(LichLamViec)
class LichLamViecAdmin(admin.ModelAdmin):
    list_display = ('nguoi_dung', 'ngay', 'gio_bat_dau', 'gio_ket_thuc', 'trang_thai', 'benh_nhan')
    list_filter = ('trang_thai', 'ngay')
    search_fields = ('nguoi_dung__ho_ten', 'benh_nhan__nguoi_dung__ho_ten')
    date_hierarchy = 'ngay'

@admin.register(NhatKyHoatDong)
class NhatKyHoatDongAdmin(admin.ModelAdmin):
    list_display = ('nguoi_dung', 'hanh_dong', 'doi_tuong', 'ip_address', 'created_at')
    list_filter = ('hanh_dong', 'created_at')
    search_fields = ('nguoi_dung__ho_ten', 'doi_tuong', 'ip_address')
    readonly_fields = ('created_at', 'du_lieu_cu', 'du_lieu_moi')
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False