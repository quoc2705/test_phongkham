from django.urls import re_path
from thongbao.consumers import ThongBaoConsumer
from trochuyen.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/thong-bao/$', ThongBaoConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<room_name>[0-9a-f-]+)/$', ChatConsumer.as_asgi()),
]