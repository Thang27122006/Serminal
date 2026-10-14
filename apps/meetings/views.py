from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import MeetingRoom, MeetingParticipant, ChatMessage
from .serializers import (
    MeetingRoomSerializer,
    CreateMeetingRoomSerializer,
    MeetingParticipantSerializer,
    ChatMessageSerializer
)


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = MeetingRoom.objects.filter(host=request.user)
        serializer = MeetingRoomSerializer(rooms, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CreateMeetingRoomSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            room = serializer.save()
            return Response({
                "success": True,
                "data": MeetingRoomSerializer(room).data,
                "message": "Tạo phòng họp thành công."
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu tạo phòng không hợp lệ.",
                "details": serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class RoomDetailView(APIView):
    # Cho phép kiểm tra phòng trước khi vào
    permission_classes = [AllowAny]

    def get(self, request, room_code):
        try:
            room = MeetingRoom.objects.get(room_code=room_code)
        except MeetingRoom.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": "ROOM_NOT_FOUND",
                    "message": "Phòng họp không tồn tại trên hệ thống."
                }
            }, status=status.HTTP_404_NOT_FOUND)

        if not room.is_active:
            return Response({
                "success": False,
                "error": {
                    "code": "ROOM_CLOSED",
                    "message": "Phòng họp này đã kết thúc."
                }
            }, status=status.HTTP_410_GONE)

        return Response({
            "success": True,
            "data": MeetingRoomSerializer(room).data
        }, status=status.HTTP_200_OK)


class RoomParticipantsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, room_code):
        room = get_object_or_404(MeetingRoom, room_code=room_code)
        participants = room.participants.filter(status='joined')
        serializer = MeetingParticipantSerializer(participants, many=True)
        return Response({
            "success": True,
            "data": {
                "room_code": room.room_code,
                "count": participants.count(),
                "participants": serializer.data
            }
        }, status=status.HTTP_200_OK)


class RoomMessagesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, room_code):
        room = get_object_or_404(MeetingRoom, room_code=room_code)
        messages = room.messages.all()[:50]
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
