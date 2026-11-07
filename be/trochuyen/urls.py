from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'phong-chat', views.PhongChatViewSet, basename='phongchat')
# Static paths BEFORE router so /phong-chat/tao/ is not captured as detail pk.
# Các path t��nh ph�ng TR����C router để không bị coi là pk (vd: tao, lay-hoac-tao).
urlpatterns = [
    path(
        'phong-chat/lay-hoac-tao/',
        views.lay_hoac_tao_phong_bs_bn,
        name='lay_hoac_tao_phong_bs_bn',
    ),
    path('phong-chat/tao/', views.tao_phong_chat, name='tao_phong_chat'),
    path(
        'phong-chat/<uuid:phong_id>/tin-nhan/',
        views.danh_sach_tin_nhan,
        name='danh_sach_tin_nhan',
    ),
    path(
        'phong-chat/<uuid:phong_id>/gui-tin-nhan/',
        views.gui_tin_nhan,
        name='gui_tin_nhan',
    ),
    path(
        'phong-chat/<uuid:phong_id>/danh-dau-da-doc/',
        views.danh_dau_da_doc,
        name='danh_dau_da_doc',
    ),
    path('', include(router.urls)),
]