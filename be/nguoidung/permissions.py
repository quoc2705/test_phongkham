from rest_framework import permissions

class LaAdmin(permissions.BasePermission):
    """Chỉ cho phép admin (vai_tro ADMIN) hoặc superuser truy cập."""
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and (
            getattr(u, 'is_superuser', False) or getattr(u, 'vai_tro', None) == 'ADMIN'
        )

class LaBenhNhan(permissions.BasePermission):
    """Chỉ cho phép bệnh nhân truy cập"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.vai_tro == 'BENH_NHAN'

class LaBacSi(permissions.BasePermission):
    """Chỉ cho phép bác sĩ truy cập"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.vai_tro == 'BAC_SI'

class LaNhanVien(permissions.BasePermission):
    """Chỉ cho phép nhân viên truy cập"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.vai_tro == 'NHAN_VIEN'

class LaBacSiHoacNhanVien(permissions.BasePermission):
    """Cho phép bác sĩ hoặc nhân viên truy cập"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.vai_tro in ['BAC_SI', 'NHAN_VIEN']


class LaAdminHoacNhanVien(permissions.BasePermission):
    """Admin hoặc nhân viên (quầy lễ tân tạo / xem hồ sơ bệnh nhân)."""
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and (
            getattr(u, 'is_superuser', False) or u.vai_tro in ('ADMIN', 'NHAN_VIEN')
        )