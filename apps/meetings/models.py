import uuid
import secrets
import string
from django.db import models
from django.contrib.auth.models import User


def generate_unique_room_code():
    """Tạo mã phòng ngẫu nhiên định dạng xxx-yyy-zzz, kiểm tra tính duy nhất."""
    chars = string.ascii_lowercase + string.digits
    # Loại bỏ các ký tự dễ gây nhầm lẫn
    safe_chars = ''.join(c for c in chars if c not in ('0', 'o', '1', 'l', 'i'))
    
    # Thử tối đa 10 lần sinh mã ngẫu nhiên
    for _ in range(10):
        part1 = ''.join(secrets.choice(safe_chars) for _ in range(3))
        part2 = ''.join(secrets.choice(safe_chars) for _ in range(3))
        part3 = ''.join(secrets.choice(safe_chars) for _ in range(3))
        code = f"{part1}-{part2}-{part3}"
        # Tránh query nếu model chưa sẵn sàng (trong lúc migration)
        try:
            if not MeetingRoom.objects.filter(room_code=code).exists():
                return code
        except Exception:
            return code
            
    # Fallback chuỗi an toàn
    return f"mtg-{secrets.token_hex(4)}"


class MeetingRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_code = models.CharField(max_length=32, unique=True, db_index=True, default=generate_unique_room_code)
    title = models.CharField(max_length=255, default='Cuộc họp mới')
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    is_active = models.BooleanField(default=True, db_index=True)
    is_private = models.BooleanField(default=False)
    passcode = models.CharField(max_length=64, blank=True, default='')
    max_participants = models.IntegerField(default=6)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Phòng họp'
        verbose_name_plural = 'Danh sách phòng họp'

    def __str__(self):
        return f"{self.title} ({self.room_code})"


class MeetingParticipant(models.Model):
    ROLE_CHOICES = (
        ('host', 'Host'),
        ('participant', 'Participant'),
    )
    STATUS_CHOICES = (
        ('joined', 'Joined'),
        ('left', 'Left'),
        ('disconnected', 'Disconnected'),
    )

    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='participations')
    display_name = models.CharField(max_length=100)
    peer_id = models.CharField(max_length=64, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='joined')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-joined_at']
        verbose_name = 'Thành viên tham gia'
        verbose_name_plural = 'Danh sách thành viên tham gia'

    def __str__(self):
        return f"{self.display_name} in {self.room.room_code}"


class ChatMessage(models.Model):
    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_messages')
    sender_name = models.CharField(max_length=100)
    content = models.TextField(max_length=1000)
    message_type = models.CharField(max_length=20, default='text')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Tin nhắn cuộc họp'
        verbose_name_plural = 'Danh sách tin nhắn cuộc họp'

    def __str__(self):
        return f"[{self.sender_name}]: {self.content[:30]}"
