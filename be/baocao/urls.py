from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BaoCaoViewSet, MauBaoCaoViewSet

router = DefaultRouter()
router.register(r'bao-cao', BaoCaoViewSet, basename='bao-cao')
router.register(r'mau-bao-cao', MauBaoCaoViewSet, basename='mau-bao-cao')

urlpatterns = [
    path('', include(router.urls)),
]