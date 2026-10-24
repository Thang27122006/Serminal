from rest_framework import serializers
from .models import MeetingRoom, MeetingParticipant, ChatMessage
from apps.authentication.serializers import UserSerializer


class MeetingParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingParticipant
        fields = ['id', 'peer_id', 'display_name', 'role', 'status', 'joined_at', 'left_at']


class MeetingRoomSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    current_participants_count = serializers.SerializerMethodField()
    has_passcode = serializers.SerializerMethodField()

    class Meta:
        model = MeetingRoom
        fields = [
            'id', 'room_code', 'title', 'host', 'is_active',
            'is_private', 'has_passcode',
            'max_participants', 'current_participants_count', 'created_at', 'ended_at'
        ]
        read_only_fields = ['id', 'room_code', 'host', 'is_active', 'has_passcode', 'created_at', 'ended_at']

    def get_current_participants_count(self, obj):
        return obj.participants.filter(status='joined').count()

    def get_has_passcode(self, obj):
        return bool(obj.passcode)


class CreateMeetingRoomSerializer(serializers.ModelSerializer):
    passcode = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=64)

    class Meta:
        model = MeetingRoom
        fields = ['title', 'max_participants', 'is_private', 'passcode']
        extra_kwargs = {
            'title': {'required': False},
            'max_participants': {'required': False, 'default': 6},
            'is_private': {'required': False, 'default': False},
        }

    def validate_max_participants(self, value):
        if value < 2 or value > 12:
            raise serializers.ValidationError("Số lượng người tham gia tối đa trong mô hình Mesh phải từ 2 đến 12.")
        return value

    def validate(self, data):
        is_private = data.get('is_private', False)
        passcode = data.get('passcode', '').strip()

        # Nếu có đặt passcode thì tự động xem là phòng riêng tư
        if passcode:
            data['is_private'] = True
            data['passcode'] = passcode
        elif is_private and not passcode:
            raise serializers.ValidationError({"passcode": "Phòng riêng tư bắt buộc phải thiết lập mật khẩu truy cập."})

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        room = MeetingRoom.objects.create(
            host=user,
            title=validated_data.get('title', 'Cuộc họp mới').strip() or 'Cuộc họp mới',
            max_participants=validated_data.get('max_participants', 6),
            is_private=validated_data.get('is_private', False),
            passcode=validated_data.get('passcode', '')
        )
        return room


class JoinRoomSerializer(serializers.Serializer):
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    passcode = serializers.CharField(required=False, allow_blank=True, max_length=64)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender_name', 'content', 'message_type', 'created_at']
        read_only_fields = ['id', 'created_at']
