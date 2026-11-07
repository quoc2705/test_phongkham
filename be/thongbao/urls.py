from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .notification_views import ThongBaoPhatHanhViewSet

router = DefaultRouter()
# Mount tại /api/thong-bao/phat-hanh/ (prefix trong phongkham.urls)
router.register(r'', ThongBaoPhatHanhViewSet, basename='thong-bao-phat-hanh')

urlpatterns = router.urls
