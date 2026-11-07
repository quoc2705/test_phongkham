# urls.py - Đơn giản hóa

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView
from django.views.static import serve
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
# views.py - Thêm vào cuối file

from donhang import views as donhang_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # VNPay — alias khớp URL thường khai trên cổng merchant (/api/payment/...)
    # (URL chuẩn trong code vẫn là /api/don-hang/vnpay-ipn/)
    path('api/payment/vnpay-ipn/', donhang_views.vnpay_ipn, name='vnpay_ipn_payment_alias'),
    path('api/payment/vnpay-return/', donhang_views.vnpay_return, name='vnpay_return_payment_alias'),

    # Auth endpoints
    path('api/auth/dang-nhap/', include('nguoidung.urls')),  # Giả sử có auth endpoints trong nguoidung.urls
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API endpoints — phat-hanh TRƯỚC api/ để không bị router thong-bao (nguoidung) nuốt path
    path('api/thong-bao/phat-hanh/', include('thongbao.urls')),
    path('api/', include('nguoidung.urls')),
    path('api/thuoc/', include('thuoc.urls')),
    path('api/lich-hen/', include('lichhen.urls')),
    path('api/don-hang/', include('donhang.urls')),
    path('api/benh-an/', include('benhan.urls')),
    path('api/tro-chuyen/', include('trochuyen.urls')),
    path('api/bao-cao/', include('baocao.urls')),
    
    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Thêm vào urlpatterns
    path('login/', TemplateView.as_view(template_name='index.html'), name='login'),
    path('admin-dashboard/', TemplateView.as_view(template_name='index.html'), name='admin_dashboard'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATICFILES_DIRS[0]}),
    path('payment/vnpay-return/', donhang_views.vnpay_return, name='vnpay_return_spa'),
    # Frontend routes - bắt toàn bộ route SPA ngoài API/admin/static/media
    re_path(r'^(?!api/|admin/|static/|media/).*$', TemplateView.as_view(template_name='index.html'), name='frontend'),
]