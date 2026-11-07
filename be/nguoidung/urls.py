from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.contrib.auth import views as auth_views
# views.py - Thêm vào cuối file
from .views import (
    AdminDashboardView, admin_stats_api, admin_search_api,
    admin_bac_si_api, admin_benh_nhan_api, admin_nhan_vien_api
)
router = DefaultRouter()
router.register(r'users', views.NguoiDungViewSet)
router.register(r'benh-nhan', views.BenhNhanViewSet)
router.register(r'bac-si', views.BacSiViewSet)
router.register(r'nhan-vien', views.NhanVienViewSet)
router.register(r'danh-gia', views.DanhGiaBacSiViewSet)
router.register(r'thong-bao', views.ThongBaoViewSet, basename='thongbao')
router.register(r'doctor-schedule', views.DoctorScheduleViewSet)
router.register(r'lich-lam-viec', views.LichLamViecViewSet)
router.register(r'nhat-ky', views.NhatKyHoatDongViewSet, basename='nhatky')
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    # path('api/', include(router.urls)),
    path('', include(router.urls)),
    
    # Login/Logout URLs (cho web frontend)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Admin Dashboard
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/stats/', views.admin_stats_api, name='admin_stats'),
    path('admin/search/', views.admin_search_api, name='admin_search'),
    
    # Admin APIs
    path('admin/bac-si/', views.admin_bac_si_api, name='admin_bac_si'),
    path('admin/bac-si/<str:pk>/', views.admin_bac_si_api, name='admin_bac_si_detail'),
    path('admin/benh-nhan/', views.admin_benh_nhan_api, name='admin_benh_nhan'),
    path('admin/benh-nhan/<str:pk>/', views.admin_benh_nhan_api, name='admin_benh_nhan_detail'),
    path('admin/nhan-vien/', views.admin_nhan_vien_api, name='admin_nhan_vien'),
    path('admin/nhan-vien/<str:pk>/', views.admin_nhan_vien_api, name='admin_nhan_vien_detail'),
]




