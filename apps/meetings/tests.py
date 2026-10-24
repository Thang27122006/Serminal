from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from channels.testing import WebsocketCommunicator
from core.asgi import application
from apps.meetings.models import MeetingRoom, MeetingParticipant


class MeetingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.host_user = User.objects.create_user(
            username='hostuser',
            email='host@example.com',
            password='Password123'
        )
        refresh = RefreshToken.for_user(self.host_user)
        self.access_token = str(refresh.access_token)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
        self.rooms_url = '/api/v1/rooms/'

    def test_create_meeting_room_unauthenticated_fails(self):
        response = self.client.post(self.rooms_url, {"title": "Phòng vô danh"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_meeting_room_with_jwt_bearer(self):
        payload = {"title": "Phòng họp tuần 2", "max_participants": 6}
        response = self.client.post(self.rooms_url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('room_code', response.data['data'])
        self.assertEqual(response.data['data']['title'], 'Phòng họp tuần 2')
        self.assertFalse(response.data['data']['is_private'])
        self.assertFalse(response.data['data']['has_passcode'])

    def test_create_private_meeting_room_with_passcode(self):
        payload = {
            "title": "Phòng họp bí mật",
            "is_private": True,
            "passcode": "SecretPass123"
        }
        response = self.client.post(self.rooms_url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room_data = response.data['data']
        self.assertTrue(room_data['is_private'])
        self.assertTrue(room_data['has_passcode'])
        # Đảm bảo KHÔNG lộ passcode trong response
        self.assertNotIn('passcode', room_data)

    def test_create_private_room_without_passcode_fails(self):
        payload = {
            "title": "Phòng thiếu pass",
            "is_private": True,
            "passcode": ""
        }
        response = self.client.post(self.rooms_url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_create_room_invalid_capacity_fails(self):
        payload = {"title": "Phòng quá tải", "max_participants": 20}
        response = self.client.post(self.rooms_url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_user_hosted_rooms(self):
        MeetingRoom.objects.create(title="Phòng của host", host=self.host_user)
        other_user = User.objects.create_user(username='other', email='other@example.com', password='123')
        MeetingRoom.objects.create(title="Phòng của người khác", host=other_user)

        response = self.client.get(self.rooms_url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['title'], 'Phòng của host')

    def test_room_code_uniqueness(self):
        r1 = MeetingRoom.objects.create(title="Room 1", host=self.host_user)
        r2 = MeetingRoom.objects.create(title="Room 2", host=self.host_user)
        self.assertNotEqual(r1.room_code, r2.room_code)

    def test_get_room_detail_success(self):
        room = MeetingRoom.objects.create(title="Phòng công khai", host=self.host_user)
        response = self.client.get(f"/api/v1/rooms/{room.room_code}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['room_code'], room.room_code)

    def test_get_room_detail_not_found(self):
        response = self.client.get("/api/v1/rooms/non-existent-code/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_room_detail_closed_returns_410(self):
        room = MeetingRoom.objects.create(title="Phòng đóng", host=self.host_user, is_active=False)
        response = self.client.get(f"/api/v1/rooms/{room.room_code}/")
        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    # --------------------------------------------------------------------------
    # Tests cho API Join Room & Access Control (Backend Permissions)
    # --------------------------------------------------------------------------
    def test_join_public_room_authenticated(self):
        room = MeetingRoom.objects.create(title="Phòng công khai", host=self.host_user)
        normal_user = User.objects.create_user(username='guestuser', email='g@example.com', password='123')
        refresh = RefreshToken.for_user(normal_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}

        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", {}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('peer_id', response.data['data'])
        self.assertEqual(response.data['data']['role'], 'participant')
        self.assertFalse(response.data['data']['is_host'])

    def test_join_public_room_guest_success(self):
        room = MeetingRoom.objects.create(title="Phòng khách", host=self.host_user)
        payload = {"display_name": "Khách Vãng Lai A"}
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['display_name'], "Khách Vãng Lai A")

    def test_join_public_room_guest_without_name_fails(self):
        room = MeetingRoom.objects.create(title="Phòng khách", host=self.host_user)
        payload = {"display_name": ""}
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error']['code'], 'DISPLAY_NAME_REQUIRED')

    def test_join_private_room_without_passcode_fails(self):
        room = MeetingRoom.objects.create(
            title="Phòng riêng tư",
            host=self.host_user,
            is_private=True,
            passcode="CorrectPass123"
        )
        payload = {"display_name": "Kẻ tò mò"}
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error']['code'], 'ACCESS_DENIED')

    def test_join_private_room_with_wrong_passcode_fails(self):
        room = MeetingRoom.objects.create(
            title="Phòng riêng tư",
            host=self.host_user,
            is_private=True,
            passcode="CorrectPass123"
        )
        payload = {"display_name": "Người lạ", "passcode": "WrongPass"}
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error']['code'], 'ACCESS_DENIED')

    def test_join_private_room_with_correct_passcode_success(self):
        room = MeetingRoom.objects.create(
            title="Phòng riêng tư",
            host=self.host_user,
            is_private=True,
            passcode="CorrectPass123"
        )
        payload = {"display_name": "Đồng nghiệp", "passcode": "CorrectPass123"}
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_join_private_room_by_host_without_passcode_success(self):
        room = MeetingRoom.objects.create(
            title="Phòng riêng tư",
            host=self.host_user,
            is_private=True,
            passcode="CorrectPass123"
        )
        # Host vào phòng của chính mình không cần pass
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", {}, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['is_host'])
        self.assertEqual(response.data['data']['role'], 'host')

    def test_join_full_room_fails(self):
        room = MeetingRoom.objects.create(
            title="Phòng 2 người",
            host=self.host_user,
            max_participants=2
        )
        # Tạo sẵn 2 người trong phòng
        MeetingParticipant.objects.create(room=room, display_name="P1", peer_id="peer-1", status='joined')
        MeetingParticipant.objects.create(room=room, display_name="P2", peer_id="peer-2", status='joined')

        # Người thứ 3 cố gắng vào
        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", {"display_name": "P3"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error']['code'], 'ROOM_FULL')


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
