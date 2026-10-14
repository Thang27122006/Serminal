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

    class Meta:
        model = MeetingRoom
        fields = [
            'id', 'room_code', 'title', 'host', 'is_active',
            'max_participants', 'current_participants_count', 'created_at', 'ended_at'
        ]
        read_only_fields = ['id', 'room_code', 'host', 'is_active', 'created_at', 'ended_at']

    def get_current_participants_count(self, obj):
        return obj.participants.filter(status='joined').count()


class CreateMeetingRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingRoom
        fields = ['title', 'max_participants']
        extra_kwargs = {
            'title': {'required': False},
            'max_participants': {'required': False, 'default': 6},
        }

    def create(self, validated_data):
        user = self.context['request'].user
        room = MeetingRoom.objects.create(
            host=user,
            title=validated_data.get('title', 'Cuộc họp mới'),
            max_participants=validated_data.get('max_participants', 6)
        )
        return room


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender_name', 'content', 'message_type', 'created_at']
        read_only_fields = ['id', 'created_at']
