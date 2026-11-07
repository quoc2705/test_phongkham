from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'ho-so-benh-an', views.HoSoBenhAnViewSet)
router.register(r'chan-doan', views.ChanDoanViewSet)
router.register(r'don-thuoc', views.DonThuocViewSet)
router.register(r'chi-tiet-don-thuoc', views.ChiTietDonThuocViewSet)
router.register(r'phieu-xuat-thuoc', views.PhieuXuatThuocViewSet)
router.register(r'lich-su-tiem-chung', views.LichSuTiemChungViewSet)
router.register(r'toa-thuoc-mau', views.ToaThuocMauViewSet)
router.register(r'lich-hen-tai-kham', views.LichHenTaiKhamViewSet)
router.register(r'theo-doi-dieu-tri', views.TheoDoiDieuTriViewSet)
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]