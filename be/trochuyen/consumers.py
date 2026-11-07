import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import PhongChat, TinNhan, TinNhanDaXem

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Lấy thông tin phòng từ URL
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"
        
        # Lấy user từ scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Kiểm tra quyền truy cập phòng
        co_quyen = await self.kiem_tra_quyen_phong()
        if not co_quyen:
            await self.close()
            return
        
        # Tham gia room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Gửi thông báo user đã tham gia
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': {
                    'id': str(self.user.id),
                    'ho_ten': self.user.ho_ten,
                    'vai_tro': self.user.vai_tro
                }
            }
        )
        
        # Đánh dấu tin nhắn đã đọc khi user vào phòng
        await self.danh_dau_tin_nhan_da_doc()
    
    async def disconnect(self, close_code):
        # Chỉ xử lý nếu đã tham gia room group
        if not hasattr(self, 'room_group_name'):
            return

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        if not self.user.is_anonymous:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user': {
                        'id': str(self.user.id),
                        'ho_ten': self.user.ho_ten,
                        'vai_tro': self.user.vai_tro
                    }
                }
            )
    
    async def receive(self, text_data):
        """Nhận tin nhắn từ client"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'get_old_messages':
                await self.send_old_messages(data)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Dữ liệu không hợp lệ'
            }))
    
    async def handle_chat_message(self, data):
        """Xử lý tin nhắn chat"""
        message = data.get('message', '')
        loai = data.get('loai', 'TEXT')
        
        # Lưu tin nhắn vào database
        tin_nhan = await self.luu_tin_nhan(message, loai)
        
        if tin_nhan:
            # Gửi tin nhắn đến tất cả trong room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'tin_nhan': tin_nhan
                }
            )
    
    async def handle_typing(self, data):
        """Xử lý thông báo đang gõ"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': {
                    'id': str(self.user.id),
                    'ho_ten': self.user.ho_ten
                },
                'is_typing': data.get('is_typing', False)
            }
        )
    
    async def handle_read_receipt(self, data):
        """Xử lý xác nhận đã đọc"""
        tin_nhan_id = data.get('tin_nhan_id')
        
        if tin_nhan_id:
            await self.danh_dau_da_xem(tin_nhan_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'tin_nhan_id': tin_nhan_id,
                    'user': {
                        'id': str(self.user.id),
                        'ho_ten': self.user.ho_ten
                    }
                }
            )
    
    async def send_old_messages(self, data):
        """Gửi tin nhắn cũ khi client yêu cầu"""
        before_id = data.get('before_id')
        limit = data.get('limit', 50)
        
        messages = await self.lay_tin_nhan_cu(before_id, limit)
        
        await self.send(text_data=json.dumps({
            'type': 'old_messages',
            'messages': messages,
            'has_more': len(messages) == limit
        }))
    
    async def chat_message(self, event):
        """Gửi tin nhắn đến client"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'tin_nhan': event['tin_nhan']
        }))
    
    async def user_joined(self, event):
        """Thông báo user đã tham gia"""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user']
        }))
    
    async def user_left(self, event):
        """Thông báo user đã rời"""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user']
        }))
    
    async def typing_indicator(self, event):
        """Thông báo đang gõ"""
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'user': event['user'],
            'is_typing': event['is_typing']
        }))
    
    async def read_receipt(self, event):
        """Xác nhận đã đọc"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'tin_nhan_id': event['tin_nhan_id'],
            'user': event['user']
        }))
    
    @database_sync_to_async
    def kiem_tra_quyen_phong(self):
        """Kiểm tra user có quyền vào phòng không"""
        try:
            phong_chat = PhongChat.objects.get(id=self.room_id)
            return phong_chat.kiem_tra_quyen(self.user)
        except PhongChat.DoesNotExist:
            return False
    
    @database_sync_to_async
    def luu_tin_nhan(self, message, loai='TEXT'):
        """Lưu tin nhắn vào database"""
        try:
            phong_chat = PhongChat.objects.get(id=self.room_id)
            
            tin_nhan = TinNhan.objects.create(
                phong_chat=phong_chat,
                nguoi_gui=self.user,
                loai=loai,
                noi_dung=message
            )
            
            return tin_nhan.to_dict()
        except Exception as e:
            print(f"Lỗi lưu tin nhắn: {e}")
            return None
    
    @database_sync_to_async
    def danh_dau_da_xem(self, tin_nhan_id):
        """Đánh dấu tin nhắn đã xem (dùng TinNhanDaXem)"""
        try:
            tin_nhan = TinNhan.objects.get(id=tin_nhan_id)
            if tin_nhan.nguoi_gui != self.user:
                TinNhanDaXem.objects.get_or_create(
                    tin_nhan=tin_nhan,
                    nguoi_dung=self.user,
                )
        except TinNhan.DoesNotExist:
            pass

    @database_sync_to_async
    def danh_dau_tin_nhan_da_doc(self):
        """Đánh dấu tất cả tin nhắn trong phòng đã đọc khi user vào"""
        try:
            chua_xem = TinNhan.objects.filter(
                phong_chat_id=self.room_id,
            ).exclude(
                nguoi_gui=self.user,
            ).exclude(
                trang_thai_xem__nguoi_dung=self.user,
            )
            for tin_nhan in chua_xem:
                TinNhanDaXem.objects.get_or_create(
                    tin_nhan=tin_nhan,
                    nguoi_dung=self.user,
                )
        except Exception as e:
            print(f"Lỗi đánh dấu đã đọc: {e}")
    
    @database_sync_to_async
    def lay_tin_nhan_cu(self, before_id=None, limit=50):
        """Lấy tin nhắn cũ"""
        try:
            phong_chat = PhongChat.objects.get(id=self.room_id)
            queryset = phong_chat.tin_nhan.select_related('nguoi_gui')
            
            if before_id:
                tin_nhan = TinNhan.objects.get(id=before_id)
                queryset = queryset.filter(ngay_gui__lt=tin_nhan.ngay_gui)
            
            messages = queryset.order_by('-ngay_gui')[:limit]
            
            return [msg.to_dict() for msg in messages]
        except Exception as e:
            print(f"Lỗi lấy tin nhắn cũ: {e}")
            return []