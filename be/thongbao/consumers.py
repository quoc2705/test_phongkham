import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class ThongBaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Lấy user từ scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Tạo group cho user
        self.group_name = f"thongbao_{self.user.id}"
        
        # Tham gia group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Gửi số thông báo chưa đọc
        so_thong_bao_chua_doc = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': so_thong_bao_chua_doc
        }))
    
    async def disconnect(self, close_code):
        # Rời group (chỉ khi đã tham gia)
        if not hasattr(self, 'group_name'):
            return
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def send_thong_bao(self, event):
        """Nhận thông báo từ group và gửi đến client"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'thong_bao': event['thong_bao']
        }))
        
        # Cập nhật số thông báo chưa đọc
        so_thong_bao_chua_doc = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': so_thong_bao_chua_doc
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Lấy số thông báo chưa đọc"""
        from .models import ThongBao
        return ThongBao.objects.filter(
            nguoi_nhan=self.user,
            da_doc_luc__isnull=True
        ).count()