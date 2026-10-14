from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from channels.testing import WebsocketCommunicator
from core.asgi import application
from apps.meetings.models import MeetingRoom


class MeetingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='hostuser',
            email='host@example.com',
            password='Password123'
        )
        self.client.force_authenticate(user=self.user)
        self.rooms_url = '/api/v1/rooms/'

    def test_create_meeting_room(self):
        payload = {"title": "Phòng họp kiểm thử"}
        response = self.client.post(self.rooms_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('room_code', response.data['data'])
        self.assertEqual(response.data['data']['title'], 'Phòng họp kiểm thử')

    def test_get_room_detail_success(self):
        room = MeetingRoom.objects.create(
            title="Phòng công khai",
            host=self.user
        )
        anonymous_client = APIClient()
        response = anonymous_client.get(f"/api/v1/rooms/{room.room_code}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['room_code'], room.room_code)

    def test_get_room_detail_not_found(self):
        anonymous_client = APIClient()
        response = anonymous_client.get("/api/v1/rooms/non-existent-room/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])

    def test_get_room_detail_closed_returns_410(self):
        room = MeetingRoom.objects.create(
            title="Phòng đã đóng",
            host=self.user,
            is_active=False
        )
        anonymous_client = APIClient()
        response = anonymous_client.get(f"/api/v1/rooms/{room.room_code}/")
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertFalse(response.data['success'])


class WebSocketSignalingTests(TestCase):
    async def test_websocket_signaling_connect_and_join(self):
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]
        communicator = WebsocketCommunicator(
            application,
            "/ws/meeting/test-room-123/",
            headers=headers
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Gửi thông điệp join_room
        await communicator.send_json_to({
            "type": "join_room",
            "payload": {
                "peer_id": "test-peer-uuid-1",
                "display_name": "Tester A"
            }
        })

        # Nhận phản hồi room_state
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'room_state')
        self.assertEqual(response['payload']['self_peer_id'], 'test-peer-uuid-1')

        # Test gửi tin nhắn chat và nhận broadcast
        await communicator.send_json_to({
            "type": "chat_message",
            "payload": {
                "content": "Xin chào từ test case!"
            }
        })

        chat_resp = await communicator.receive_json_from()
        self.assertEqual(chat_resp['type'], 'chat_broadcast')
        self.assertEqual(chat_resp['payload']['content'], 'Xin chào từ test case!')

        # Đóng kết nối an toàn
        await communicator.disconnect()
