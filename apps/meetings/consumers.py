"""
Signaling & Chat WebSocket Consumer for AI Meeting.
Tuần 1: Khởi tạo nền tảng kết nối Channels, routing và skeleton xử lý signaling.
"""

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class MeetingSignalingConsumer(AsyncJsonWebsocketConsumer):
    """
    Consumer chịu trách nhiệm điều phối WebSocket Signaling cho WebRTC (Full Mesh)
    và phát tin nhắn văn bản tức thời trong phòng họp.
    """

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs'].get('room_code')
        self.room_group_name = f"meeting_{self.room_code}"
        self.peer_id = None
        self.display_name = "Khách"

        # Gia nhập group Channels của phòng
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Chấp nhận kết nối WebSocket
        await self.accept()

    async def disconnect(self, close_code):
        # Rời khỏi group Channels của phòng
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Nếu đã có peer_id, broadcast thông báo rời phòng cho các peer khác
        if self.peer_id:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user.left.broadcast",
                    "peer_id": self.peer_id,
                    "display_name": self.display_name,
                    "sender_channel": self.channel_name,
                }
            )

    async def receive_json(self, content):
        """
        Tiếp nhận thông điệp JSON từ client và điều phối xử lý theo type.
        """
        msg_type = content.get('type')
        payload = content.get('payload', {})

        if msg_type == 'join_room':
            await self.handle_join_room(payload)
        elif msg_type in ('offer', 'answer', 'ice_candidate'):
            await self.handle_signaling_forward(msg_type, payload)
        elif msg_type == 'chat_message':
            await self.handle_chat_message(payload)
        elif msg_type == 'leave_room':
            await self.close(code=4000)
        else:
            await self.send_json({
                "type": "error",
                "payload": {
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"Không nhận diện được loại thông điệp: {msg_type}"
                }
            })

    async def handle_join_room(self, payload):
        self.peer_id = payload.get('peer_id')
        self.display_name = payload.get('display_name', self.display_name)

        # Broadcast sự kiện user_joined tới toàn bộ thành viên khác trong phòng
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user.joined.broadcast",
                "peer_id": self.peer_id,
                "display_name": self.display_name,
                "sender_channel": self.channel_name,
            }
        )

        # Phản hồi room_state cho chính client mới gia nhập
        await self.send_json({
            "type": "room_state",
            "payload": {
                "room_code": self.room_code,
                "self_peer_id": self.peer_id,
                "status": "ready_for_mesh"
            }
        })

    async def handle_signaling_forward(self, msg_type, payload):
        # Chuyển tiếp Offer / Answer / ICE Candidate
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "signaling.forward",
                "signaling_type": msg_type,
                "payload": payload,
                "sender_channel": self.channel_name,
            }
        )

    async def handle_chat_message(self, payload):
        content = payload.get('content', '').strip()
        if not content:
            return

        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Broadcast tin nhắn chat cho toàn bộ thành viên trong phòng
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.broadcast",
                "sender_peer_id": self.peer_id,
                "sender_name": self.display_name,
                "content": content[:1000],
                "timestamp": timestamp,
            }
        )

    # --------------------------------------------------------------------------
    # Handlers cho các sự kiện Channels group broadcast
    # --------------------------------------------------------------------------

    async def user_joined_broadcast(self, event):
        # Không gửi lại cho chính người vừa tham gia
        if self.channel_name != event.get('sender_channel'):
            await self.send_json({
                "type": "user_joined",
                "payload": {
                    "peer_id": event['peer_id'],
                    "display_name": event['display_name']
                }
            })

    async def user_left_broadcast(self, event):
        if self.channel_name != event.get('sender_channel'):
            await self.send_json({
                "type": "user_left",
                "payload": {
                    "peer_id": event['peer_id'],
                    "display_name": event['display_name']
                }
            })

    async def signaling_forward(self, event):
        # Không chuyển tiếp lại cho chính client phát tín hiệu
        if self.channel_name != event.get('sender_channel'):
            await self.send_json({
                "type": event['signaling_type'],
                "payload": event['payload']
            })

    async def chat_broadcast(self, event):
        await self.send_json({
            "type": "chat_broadcast",
            "payload": {
                "sender_peer_id": event['sender_peer_id'],
                "sender_name": event['sender_name'],
                "content": event['content'],
                "timestamp": event['timestamp']
            }
        })
