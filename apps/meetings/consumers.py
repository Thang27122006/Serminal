"""
WebSocket Signaling & Chat Consumer for AI Meeting (Tuần 3).
Quản lý kết nối WebSocket, xác thực JWT, điều phối presence và chuyển tiếp signaling
theo mô hình P2P Full Mesh với tính cô lập phòng nghiêm ngặt (Strict Room Isolation).
"""

import json
import uuid
from datetime import datetime, timezone
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone as django_tz

from apps.meetings.models import MeetingRoom, MeetingParticipant, ChatMessage
from apps.meetings.presence import RoomPresenceManager
from apps.authentication.middleware import get_user_from_token_str


# ------------------------------------------------------------------------------
# Database Helpers (Asynchronous ORM wrappers)
# ------------------------------------------------------------------------------
@database_sync_to_async
def get_room_by_code(room_code: str):
    """Truy vấn phòng họp theo mã phòng từ PostgreSQL."""
    try:
        return MeetingRoom.objects.select_related('host').get(room_code=room_code)
    except MeetingRoom.DoesNotExist:
        return None


@database_sync_to_async
def record_participant_join(room_id, user, display_name: str, peer_id: str, role: str):
    """Ghi nhận hoặc cập nhật trạng thái thành viên tham gia vào DB."""
    try:
        MeetingParticipant.objects.update_or_create(
            room_id=room_id,
            peer_id=peer_id,
            defaults={
                'user': user if (user and user.is_authenticated) else None,
                'display_name': display_name,
                'role': role,
                'status': 'joined'
            }
        )
    except Exception:
        pass


@database_sync_to_async
def record_participant_leave(peer_id: str, status_val: str = 'left'):
    """Cập nhật trạng thái thành viên rời phòng trong DB."""
    try:
        MeetingParticipant.objects.filter(peer_id=peer_id).update(
            status=status_val,
            left_at=django_tz.now()
        )
    except Exception:
        pass


@database_sync_to_async
def save_chat_message(room_id, user, sender_name: str, content: str):
    """Lưu trữ tin nhắn chat vào DB."""
    try:
        ChatMessage.objects.create(
            room_id=room_id,
            sender=user if (user and user.is_authenticated) else None,
            sender_name=sender_name,
            content=content
        )
    except Exception:
        pass


# ------------------------------------------------------------------------------
# Meeting Signaling Consumer
# ------------------------------------------------------------------------------
class MeetingSignalingConsumer(AsyncJsonWebsocketConsumer):
    """
    Consumer chịu trách nhiệm điều phối WebSocket Signaling cho WebRTC (Full Mesh)
    và truyền phát tin nhắn tức thời giữa các Client trong cùng phòng họp.
    """

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs'].get('room_code', '').strip().lower()
        self.room_group_name = f"meeting_{self.room_code}"
        self.peer_id = None
        self.display_name = "Khách"
        self.is_host = False
        self.joined = False
        self.room_db_id = None

        # Trạng thái xác thực từ handshake
        self.user = self.scope.get('user')
        self.is_authenticated = bool(self.user and self.user.is_authenticated)

        # Chấp nhận kết nối (hỗ trợ subprotocol bearer nếu client gửi Sec-WebSocket-Protocol)
        accepted_subprotocol = self.scope.get('accepted_subprotocol')
        if accepted_subprotocol:
            await self.accept(subprotocol=accepted_subprotocol)
        else:
            await self.accept()

    async def disconnect(self, close_code):
        """Xử lý dọn dẹp khi client ngắt kết nối (bình thường hoặc bất thường)."""
        if self.joined and self.peer_id:
            # 1. Xóa khỏi presence manager
            removed = await RoomPresenceManager.remove_peer(self.room_code, self.peer_id)

            # 2. Rời khỏi Django Channels group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # 3. Thông báo user_left cho các peer còn lại trong phòng
            if removed:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "room.user.left",
                        "peer_id": self.peer_id,
                        "display_name": self.display_name,
                        "reason": "normal" if close_code == 4000 else "disconnect"
                    }
                )

            # 4. Cập nhật bản ghi DB
            await record_participant_leave(self.peer_id, 'left' if close_code == 4000 else 'disconnected')

    async def receive(self, text_data=None, bytes_data=None):
        """Tiếp nhận text và validate JSON định dạng chuẩn."""
        if not text_data:
            return

        try:
            content = json.loads(text_data)
        except Exception:
            await self.send_error(
                code="MALFORMED_JSON",
                message="Dữ liệu gửi lên không đúng định dạng JSON hợp lệ."
            )
            return

        if not isinstance(content, dict) or 'type' not in content:
            await self.send_error(
                code="INVALID_STRUCTURE",
                message="Thông điệp phải là JSON object chứa trường 'type'."
            )
            return

        await self.process_message(content)

    async def process_message(self, content: dict):
        """Điều phối xử lý thông điệp dựa trên type."""
        msg_type = content.get('type')
        request_id = content.get('request_id')
        payload = content.get('payload', {})

        if not isinstance(payload, dict):
            await self.send_error(
                code="INVALID_PAYLOAD",
                message="Trường 'payload' phải là một JSON object.",
                request_id=request_id
            )
            return

        # 1. Tham gia phòng
        if msg_type == 'join_room':
            await self.handle_join_room(payload, request_id)
            return

        # Các thông điệp còn lại bắt buộc phải đã tham gia phòng (Joined)
        if not self.joined:
            await self.send_error(
                code="NOT_JOINED",
                message="Bạn phải gửi 'join_room' và được phê duyệt trước khi gửi thông điệp khác.",
                request_id=request_id
            )
            return

        # 2. Signaling P2P (Offer, Answer, ICE Candidate)
        if msg_type in ('offer', 'answer', 'ice_candidate'):
            await self.handle_signaling_forward(msg_type, payload, request_id)
        # 3. Tin nhắn chat
        elif msg_type == 'chat_message':
            await self.handle_chat_message(payload, request_id)
        # 4. Rời phòng chủ động
        elif msg_type == 'leave_room':
            await self.close(code=4000)
        # 5. Loại thông điệp không hỗ trợ
        else:
            await self.send_error(
                code="UNSUPPORTED_TYPE",
                message=f"Loại thông điệp '{msg_type}' không được hỗ trợ.",
                request_id=request_id
            )

    # --------------------------------------------------------------------------
    # Handlers chi tiết
    # --------------------------------------------------------------------------
    async def handle_join_room(self, payload: dict, request_id: str = None):
        """Xử lý kiểm tra quyền và đưa client vào phòng."""
        if self.joined:
            await self.send_error(
                code="ALREADY_JOINED",
                message="Bạn đã tham gia phòng họp này rồi.",
                request_id=request_id
            )
            return

        # 1. Kiểm tra xác thực động qua token trong payload nếu handshake chưa có
        token_str = payload.get('token', '').strip()
        if token_str and not self.is_authenticated:
            user = await get_user_from_token_str(token_str)
            if user and user.is_authenticated:
                self.user = user
                self.is_authenticated = True
            else:
                await self.send_error(
                    code="INVALID_TOKEN",
                    message="JWT Token cung cấp không hợp lệ hoặc đã hết hạn.",
                    request_id=request_id,
                    close_code=4001
                )
                return

        # 2. Kiểm tra tính hợp lệ của phòng từ cơ sở dữ liệu
        room = await get_room_by_code(self.room_code)
        if not room:
            await self.send_error(
                code="ROOM_NOT_FOUND",
                message=f"Phòng họp '{self.room_code}' không tồn tại.",
                request_id=request_id,
                close_code=4004
            )
            return

        if not room.is_active:
            await self.send_error(
                code="ROOM_CLOSED",
                message=f"Phòng họp '{self.room_code}' đã kết thúc.",
                request_id=request_id,
                close_code=4005
            )
            return

        self.room_db_id = room.id
        self.is_host = self.is_authenticated and (self.user.id == room.host_id)

        # 3. Kiểm tra bảo mật phòng riêng tư (Private Room Access Check)
        passcode = payload.get('passcode', '').strip()
        if room.is_private and not self.is_host:
            if not passcode or passcode != room.passcode:
                await self.send_error(
                    code="ACCESS_DENIED",
                    message="Phòng này là phòng riêng tư. Mật khẩu phòng không chính xác hoặc chưa được cung cấp.",
                    request_id=request_id,
                    close_code=4003
                )
                return

        # 4. Kiểm tra sức chứa tối đa của phòng
        current_online = await RoomPresenceManager.get_online_count(self.room_code)
        if current_online >= room.max_participants:
            await self.send_error(
                code="ROOM_FULL",
                message=f"Phòng họp đã đạt giới hạn tối đa ({room.max_participants} người).",
                request_id=request_id,
                close_code=4003
            )
            return

        # 5. Xác định tên hiển thị
        custom_name = payload.get('display_name', '').strip()
        if self.is_authenticated:
            full_name = f"{self.user.last_name} {self.user.first_name}".strip()
            self.display_name = custom_name or full_name or self.user.username
        else:
            if not custom_name:
                await self.send_error(
                    code="DISPLAY_NAME_REQUIRED",
                    message="Khách vãng lai bắt buộc phải cung cấp 'display_name'.",
                    request_id=request_id,
                    close_code=4000
                )
                return
            self.display_name = custom_name

        # 6. Cấp phát peer_id
        client_peer_id = payload.get('peer_id', '').strip()
        self.peer_id = client_peer_id if client_peer_id else str(uuid.uuid4())

        # 7. Thêm vào Channels Group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        peer_info = {
            "peer_id": self.peer_id,
            "user_id": self.user.id if self.is_authenticated else None,
            "display_name": self.display_name,
            "is_host": self.is_host,
            "channel_name": self.channel_name,
            "joined_at": now_iso
        }

        # 8. Cập nhật presence và lấy danh sách thành viên hiện có
        existing_peers = await RoomPresenceManager.add_peer(self.room_code, self.peer_id, peer_info)
        self.joined = True

        # 9. Gửi online_list cho chính client vừa tham gia
        await self.send_envelope(
            msg_type="online_list",
            request_id=request_id,
            payload={
                "room_code": self.room_code,
                "self": {
                    "peer_id": self.peer_id,
                    "display_name": self.display_name,
                    "is_host": self.is_host
                },
                "peers": existing_peers
            }
        )

        # 10. Broadcast user_joined cho các thành viên khác trong phòng
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.user.joined",
                "sender_channel": self.channel_name,
                "peer_id": self.peer_id,
                "display_name": self.display_name,
                "is_host": self.is_host,
                "joined_at": now_iso
            }
        )

        # 11. Lưu DB
        await record_participant_join(
            room_id=self.room_db_id,
            user=self.user,
            display_name=self.display_name,
            peer_id=self.peer_id,
            role='host' if self.is_host else 'participant'
        )

    async def handle_signaling_forward(self, msg_type: str, payload: dict, request_id: str = None):
        """
        Chuyển tiếp SDP Offer/Answer hoặc ICE Candidate tới đúng target_peer trong cùng phòng.
        Đảm bảo tính cô lập: chỉ chuyển tiếp cho peer trong self.room_code.
        """
        target_peer_id = payload.get('target_peer_id')
        if not target_peer_id:
            await self.send_error(
                code="MISSING_TARGET_PEER",
                message="Thông điệp signaling bắt buộc phải có 'target_peer_id'.",
                request_id=request_id
            )
            return

        # Tra cứu channel_name của target peer trong đúng phòng này
        target_channel = await RoomPresenceManager.get_peer_channel(self.room_code, target_peer_id)
        if not target_channel:
            await self.send_error(
                code="TARGET_PEER_NOT_FOUND",
                message=f"Thành viên nhận '{target_peer_id}' không tồn tại hoặc đã rời khỏi phòng này.",
                request_id=request_id
            )
            return

        # Chuẩn bị payload chuyển tiếp: Server đóng dấu sender_peer_id thật, client không thể giả mạo
        forward_payload = {
            "sender_peer_id": self.peer_id,
            "sender_name": self.display_name,
            "target_peer_id": target_peer_id
        }

        if msg_type in ('offer', 'answer'):
            forward_payload['sdp'] = payload.get('sdp')
        elif msg_type == 'ice_candidate':
            forward_payload['candidate'] = payload.get('candidate')

        # Chuyển tiếp điểm-tới-điểm (Point-to-Point) trực tiếp tới channel của recipient
        await self.channel_layer.send(
            target_channel,
            {
                "type": "peer.direct.message",
                "envelope": {
                    "type": msg_type,
                    "request_id": request_id,
                    "payload": forward_payload
                }
            }
        )

    async def handle_chat_message(self, payload: dict, request_id: str = None):
        """Broadcast tin nhắn văn bản tới toàn bộ các thành viên trong phòng."""
        content = payload.get('content', '').strip()
        if not content:
            await self.send_error(
                code="EMPTY_MESSAGE",
                message="Nội dung tin nhắn không được rỗng.",
                request_id=request_id
            )
            return

        content_clean = content[:1000]
        now_iso = datetime.now(timezone.utc).isoformat()
        message_id = str(uuid.uuid4())

        # Broadcast tin nhắn vào group phòng họp
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room.chat.message",
                "message_id": message_id,
                "sender_peer_id": self.peer_id,
                "sender_name": self.display_name,
                "content": content_clean,
                "timestamp": now_iso
            }
        )

        # Lưu tin nhắn vào cơ sở dữ liệu nếu có room_db_id
        if self.room_db_id:
            await save_chat_message(self.room_db_id, self.user, self.display_name, content_clean)

    # --------------------------------------------------------------------------
    # Group & Direct Message Handlers (Gọi từ Channel Layer)
    # --------------------------------------------------------------------------
    async def room_user_joined(self, event):
        """Thông báo thành viên mới vào phòng tới các client khác."""
        if self.channel_name != event.get('sender_channel'):
            await self.send_envelope(
                msg_type="user_joined",
                payload={
                    "peer_id": event['peer_id'],
                    "display_name": event['display_name'],
                    "is_host": event.get('is_host', False),
                    "joined_at": event.get('joined_at')
                }
            )

    async def room_user_left(self, event):
        """Thông báo thành viên rời phòng tới các client còn lại."""
        await self.send_envelope(
            msg_type="user_left",
            payload={
                "peer_id": event['peer_id'],
                "display_name": event['display_name'],
                "reason": event.get('reason', 'normal')
            }
        )

    async def room_chat_message(self, event):
        """Phân phối tin nhắn chat trong phòng."""
        await self.send_envelope(
            msg_type="chat_message",
            payload={
                "message_id": event['message_id'],
                "sender_peer_id": event['sender_peer_id'],
                "sender_name": event['sender_name'],
                "content": event['content'],
                "timestamp": event['timestamp']
            }
        )

    async def peer_direct_message(self, event):
        """Tiếp nhận thông điệp signaling trực tiếp điểm-tới-điểm."""
        envelope = event.get('envelope', {})
        await self.send_json(envelope)

    # --------------------------------------------------------------------------
    # Helper gửi thông điệp chuẩn hóa
    # --------------------------------------------------------------------------
    async def send_envelope(self, msg_type: str, payload: dict, request_id: str = None):
        """Đóng gói và gửi khung thông điệp JSON tiêu chuẩn."""
        envelope = {
            "type": msg_type,
            "payload": payload
        }
        if request_id:
            envelope["request_id"] = request_id
        await self.send_json(envelope)

    async def send_error(self, code: str, message: str, request_id: str = None, close_code: int = None):
        """Gửi thông điệp lỗi chuẩn hóa và tùy chọn đóng kết nối socket."""
        await self.send_envelope(
            msg_type="error",
            request_id=request_id,
            payload={
                "code": code,
                "message": message
            }
        )
        if close_code:
            await self.close(code=close_code)
