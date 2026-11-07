from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'lich-hen', views.LichHenViewSet)
router.register(r'lich-kham', views.LichKhamViewSet)
router.register(r'lich-tiem', views.LichTiemViewSet)
router.register(r'nhac-nho', views.NhacNhoLichHenViewSet)
router.register(r'danh-gia', views.DanhGiaDichVuViewSet)
router.register(r'lich-su', views.LichSuLichHenViewSet)
router.register(r'dashboard', views.LichHenDashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]