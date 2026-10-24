from django.contrib import admin
from .models import MeetingRoom, MeetingParticipant, ChatMessage


@admin.register(MeetingRoom)
class MeetingRoomAdmin(admin.ModelAdmin):
    list_display = ('title', 'room_code', 'host', 'is_active', 'is_private', 'max_participants', 'created_at')
    list_filter = ('is_active', 'is_private', 'created_at')
    search_fields = ('title', 'room_code', 'host__username')


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'room', 'role', 'status', 'joined_at', 'left_at')
    list_filter = ('role', 'status', 'joined_at')
    search_fields = ('display_name', 'room__room_code', 'peer_id')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender_name', 'content', 'created_at')
    list_filter = ('created_at', 'message_type')
    search_fields = ('sender_name', 'content', 'room__room_code')
