from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'loai-thuoc', views.LoaiThuocViewSet)
router.register(r'don-vi-tinh', views.DonViTinhViewSet)
router.register(r'nha-cung-cap', views.NhaCungCapViewSet)
router.register(r'thuoc', views.ThuocViewSet)
router.register(r'kho-thuoc', views.KhoThuocViewSet)
router.register(r'loai-vaccine', views.LoaiVaccineViewSet)
router.register(r'vaccine', views.VaccineViewSet)
router.register(r'kho-vaccine', views.KhoVaccineViewSet)
router.register(r'phieu-nhap', views.PhieuNhapKhoViewSet)
router.register(r'toa-thuoc-mau', views.ToaThuocMauViewSet)
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('dashboard/ke-toan/tai-chinh-xuat/', views.tai_chinh_xuat_download, name='tai-chinh-xuat'),
    path('', include(router.urls)),
]