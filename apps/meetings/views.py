import uuid
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import MeetingRoom, MeetingParticipant, ChatMessage
from .serializers import (
    MeetingRoomSerializer,
    CreateMeetingRoomSerializer,
    JoinRoomSerializer,
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
    # Cho phép kiểm tra trạng thái phòng trước khi vào
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


class RoomJoinView(APIView):
    """
    API kiểm tra và xác nhận quyền truy cập trước khi vào phòng.
    Không coi việc chỉ biết Room ID là đủ để được phép vào phòng riêng tư.
    """
    permission_classes = [AllowAny]

    def post(self, request, room_code):
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

        serializer = JoinRoomSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Dữ liệu tham gia không hợp lệ.",
                    "details": serializer.errors
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        passcode = serializer.validated_data.get('passcode', '').strip()
        custom_display_name = serializer.validated_data.get('display_name', '').strip()

        is_authenticated = request.user and request.user.is_authenticated
        is_host = is_authenticated and (request.user == room.host)

        # Kiểm tra bảo mật phòng riêng tư (Private Room Access Control)
        if room.is_private and not is_host:
            if not passcode or passcode != room.passcode:
                return Response({
                    "success": False,
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Phòng này là phòng riêng tư. Mật khẩu phòng không chính xác hoặc chưa được cung cấp."
                    }
                }, status=status.HTTP_403_FORBIDDEN)

        # Kiểm tra giới hạn thành viên (Full Mesh Capacity Limit)
        current_active = room.participants.filter(status='joined').count()
        if current_active >= room.max_participants:
            return Response({
                "success": False,
                "error": {
                    "code": "ROOM_FULL",
                    "message": f"Phòng họp đã đạt số lượng tối đa ({room.max_participants} người)."
                }
            }, status=status.HTTP_403_FORBIDDEN)

        # Xác định tên hiển thị
        if is_authenticated:
            full_name = f"{request.user.last_name} {request.user.first_name}".strip()
            display_name = custom_display_name or full_name or request.user.username
        else:
            if not custom_display_name:
                return Response({
                    "success": False,
                    "error": {
                        "code": "DISPLAY_NAME_REQUIRED",
                        "message": "Vui lòng nhập tên hiển thị để tham gia phòng họp."
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            display_name = custom_display_name

        # Cấp phát peer_id cho phiên kết nối
        peer_id = str(uuid.uuid4())
        role = 'host' if is_host else 'participant'

        # Đăng ký thành viên vào cơ sở dữ liệu
        participant = MeetingParticipant.objects.create(
            room=room,
            user=request.user if is_authenticated else None,
            display_name=display_name,
            peer_id=peer_id,
            role=role,
            status='joined'
        )

        return Response({
            "success": True,
            "data": {
                "room_code": room.room_code,
                "title": room.title,
                "peer_id": peer_id,
                "display_name": display_name,
                "role": role,
                "is_host": is_host,
                "max_participants": room.max_participants,
                "current_participants_count": room.participants.filter(status='joined').count()
            },
            "message": "Xác nhận quyền truy cập và tham gia phòng thành công."
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
