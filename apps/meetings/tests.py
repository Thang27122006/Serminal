import json
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from core.asgi import application
from apps.meetings.models import MeetingRoom, MeetingParticipant
from apps.meetings.presence import RoomPresenceManager


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
        MeetingParticipant.objects.create(room=room, display_name="P1", peer_id="peer-1", status='joined')
        MeetingParticipant.objects.create(room=room, display_name="P2", peer_id="peer-2", status='joined')

        response = self.client.post(f"/api/v1/rooms/{room.room_code}/join/", {"display_name": "P3"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error']['code'], 'ROOM_FULL')


class WebSocketSignalingTests(TestCase):
    def setUp(self):
        self.host_user = User.objects.create_user(
            username='ws_host',
            email='ws_host@example.com',
            password='Password123'
        )
        self.client_user = User.objects.create_user(
            username='ws_client',
            email='ws_client@example.com',
            password='Password123'
        )
        self.host_token = str(RefreshToken.for_user(self.host_user).access_token)
        self.client_token = str(RefreshToken.for_user(self.client_user).access_token)

        self.room = MeetingRoom.objects.create(
            room_code='test-room-w3',
            title='Phòng Kiểm Thử Tuần 3',
            host=self.host_user,
            is_active=True,
            max_participants=6
        )

    def tearDown(self):
        from asgiref.sync import async_to_sync
        async_to_sync(RoomPresenceManager.clear_all)()

    async def test_websocket_connect_and_join_with_jwt_subprotocol(self):
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]
        communicator = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual(subprotocol, 'bearer')

        # Gửi thông điệp join_room
        await communicator.send_json_to({
            "type": "join_room",
            "request_id": "req-join-1",
            "payload": {
                "peer_id": "peer-w3-1"
            }
        })

        # Nhận phản hồi online_list
        resp = await communicator.receive_json_from()
        self.assertEqual(resp['type'], 'online_list')
        self.assertEqual(resp['request_id'], 'req-join-1')
        self.assertEqual(resp['payload']['self']['peer_id'], 'peer-w3-1')

        await communicator.disconnect()

    async def test_websocket_join_room_with_token_in_payload(self):
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]
        communicator = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Gửi join_room với token trong payload
        await communicator.send_json_to({
            "type": "join_room",
            "request_id": "req-join-payload",
            "payload": {
                "peer_id": "peer-payload-auth",
                "token": self.client_token
            }
        })

        resp = await communicator.receive_json_from()
        self.assertEqual(resp['type'], 'online_list')
        self.assertEqual(resp['payload']['self']['peer_id'], 'peer-payload-auth')
        await communicator.disconnect()

    async def test_websocket_join_nonexistent_room_closes_4004(self):
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]
        communicator = WebsocketCommunicator(
            application,
            "/ws/meeting/non-existent-code/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({
            "type": "join_room",
            "payload": {"peer_id": "peer-test"}
        })

        resp = await communicator.receive_json_from()
        self.assertEqual(resp['type'], 'error')
        self.assertEqual(resp['payload']['code'], 'ROOM_NOT_FOUND')

        close_event = await communicator.receive_output()
        self.assertEqual(close_event['type'], 'websocket.close')
        self.assertEqual(close_event['code'], 4004)

        try:
            await communicator.disconnect()
        except Exception:
            pass

    async def test_websocket_join_private_room_access_control(self):
        private_room = await database_sync_to_async(MeetingRoom.objects.create)(
            room_code='private-room-w3',
            title='Phòng Riêng Tư',
            host=self.host_user,
            is_active=True,
            is_private=True,
            passcode='SuperSecretPass'
        )

        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]

        # 1. Thử tham gia với sai mật khẩu -> bị từ chối với ACCESS_DENIED
        comm_wrong = WebsocketCommunicator(
            application,
            f"/ws/meeting/{private_room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        await comm_wrong.connect()
        await comm_wrong.send_json_to({
            "type": "join_room",
            "payload": {"peer_id": "peer-wrong-pass", "passcode": "WrongPassword"}
        })
        resp_err = await comm_wrong.receive_json_from()
        self.assertEqual(resp_err['type'], 'error')
        self.assertEqual(resp_err['payload']['code'], 'ACCESS_DENIED')

        close_event = await comm_wrong.receive_output()
        self.assertEqual(close_event['type'], 'websocket.close')
        self.assertEqual(close_event['code'], 4003)

        try:
            await comm_wrong.disconnect()
        except Exception:
            pass

        # 2. Tham gia với mật khẩu đúng -> thành công nhận online_list
        comm_ok = WebsocketCommunicator(
            application,
            f"/ws/meeting/{private_room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        await comm_ok.connect()
        await comm_ok.send_json_to({
            "type": "join_room",
            "payload": {"peer_id": "peer-right-pass", "passcode": "SuperSecretPass"}
        })
        resp_ok = await comm_ok.receive_json_from()
        self.assertEqual(resp_ok['type'], 'online_list')
        self.assertEqual(resp_ok['payload']['self']['peer_id'], 'peer-right-pass')
        await comm_ok.disconnect()

    async def test_websocket_targeted_signaling_and_presence_flow(self):
        """
        Kiểm thử quy trình bắt tay signaling điểm-tới-điểm:
        1. Peer 1 join.
        2. Peer 2 join -> Peer 2 nhận online_list có Peer 1; Peer 1 nhận user_joined có Peer 2.
        3. Peer 1 gửi Offer trực tiếp tới Peer 2.
        4. Peer 2 nhận Offer và phản hồi Answer tới Peer 1.
        5. Cả hai trao đổi ICE Candidates.
        """
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]

        # Peer 1 (Host)
        comm1 = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.host_token]
        )
        await comm1.connect()
        await comm1.send_json_to({
            "type": "join_room",
            "payload": {"peer_id": "peer-host-1"}
        })
        list1 = await comm1.receive_json_from()
        self.assertEqual(list1['type'], 'online_list')
        self.assertEqual(len(list1['payload']['peers']), 0)

        # Peer 2 (Client)
        comm2 = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        await comm2.connect()
        await comm2.send_json_to({
            "type": "join_room",
            "payload": {"peer_id": "peer-client-2"}
        })

        # Peer 2 nhận online_list chứa Peer 1
        list2 = await comm2.receive_json_from()
        self.assertEqual(list2['type'], 'online_list')
        self.assertEqual(len(list2['payload']['peers']), 1)
        self.assertEqual(list2['payload']['peers'][0]['peer_id'], 'peer-host-1')

        # Peer 1 nhận thông báo user_joined của Peer 2
        joined_event = await comm1.receive_json_from()
        self.assertEqual(joined_event['type'], 'user_joined')
        self.assertEqual(joined_event['payload']['peer_id'], 'peer-client-2')

        # 3. Peer 1 gửi Offer cho Peer 2
        offer_sdp = {"type": "offer", "sdp": "v=0...fake-sdp-offer"}
        await comm1.send_json_to({
            "type": "offer",
            "request_id": "req-offer-1",
            "payload": {
                "target_peer_id": "peer-client-2",
                "sdp": offer_sdp
            }
        })

        # Peer 2 nhận Offer trực tiếp
        offer_received = await comm2.receive_json_from()
        self.assertEqual(offer_received['type'], 'offer')
        self.assertEqual(offer_received['payload']['sender_peer_id'], 'peer-host-1')
        self.assertEqual(offer_received['payload']['sdp'], offer_sdp)

        # 4. Peer 2 phản hồi Answer cho Peer 1
        answer_sdp = {"type": "answer", "sdp": "v=0...fake-sdp-answer"}
        await comm2.send_json_to({
            "type": "answer",
            "request_id": "req-ans-1",
            "payload": {
                "target_peer_id": "peer-host-1",
                "sdp": answer_sdp
            }
        })

        # Peer 1 nhận Answer trực tiếp
        answer_received = await comm1.receive_json_from()
        self.assertEqual(answer_received['type'], 'answer')
        self.assertEqual(answer_received['payload']['sender_peer_id'], 'peer-client-2')
        self.assertEqual(answer_received['payload']['sdp'], answer_sdp)

        # 5. Peer 1 gửi ICE Candidate cho Peer 2
        candidate_data = {"candidate": "candidate:123...", "sdpMid": "0"}
        await comm1.send_json_to({
            "type": "ice_candidate",
            "payload": {
                "target_peer_id": "peer-client-2",
                "candidate": candidate_data
            }
        })

        # Peer 2 nhận ICE Candidate
        cand_received = await comm2.receive_json_from()
        self.assertEqual(cand_received['type'], 'ice_candidate')
        self.assertEqual(cand_received['payload']['sender_peer_id'], 'peer-host-1')
        self.assertEqual(cand_received['payload']['candidate'], candidate_data)

        # 6. Peer 2 ngắt kết nối -> Peer 1 nhận user_left
        await comm2.disconnect()
        left_event = await comm1.receive_json_from()
        self.assertEqual(left_event['type'], 'user_left')
        self.assertEqual(left_event['payload']['peer_id'], 'peer-client-2')

        await comm1.disconnect()

    async def test_websocket_room_isolation(self):
        """
        Kiểm thử tính cô lập giữa các phòng (Room Isolation):
        Thành viên ở Phòng A gửi chat/signaling, thành viên ở Phòng B tuyệt đối KHÔNG nhận được.
        """
        room_b = await database_sync_to_async(MeetingRoom.objects.create)(
            room_code='isolated-room-b',
            title='Phòng Biệt Lập B',
            host=self.host_user,
            is_active=True
        )

        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]

        # Peer A vào Phòng A
        comm_a = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.host_token]
        )
        await comm_a.connect()
        await comm_a.send_json_to({"type": "join_room", "payload": {"peer_id": "peer-in-room-a"}})
        await comm_a.receive_json_from()

        # Peer B vào Phòng B
        comm_b = WebsocketCommunicator(
            application,
            f"/ws/meeting/{room_b.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        await comm_b.connect()
        await comm_b.send_json_to({"type": "join_room", "payload": {"peer_id": "peer-in-room-b"}})
        await comm_b.receive_json_from()

        # Peer A gửi tin nhắn trong Phòng A
        await comm_a.send_json_to({
            "type": "chat_message",
            "payload": {"content": "Bí mật phòng A!"}
        })

        # Peer A nhận broadcast của chính phòng mình
        chat_a = await comm_a.receive_json_from()
        self.assertEqual(chat_a['type'], 'chat_message')
        self.assertEqual(chat_a['payload']['content'], 'Bí mật phòng A!')

        # Peer B không được nhận bất kỳ thông điệp nào từ phòng A
        nothing_received = await comm_b.receive_nothing(timeout=0.5)
        self.assertTrue(nothing_received)

        # Peer A cố gửi signaling tới Peer B (ở phòng khác) -> phải bị từ chối
        await comm_a.send_json_to({
            "type": "offer",
            "payload": {
                "target_peer_id": "peer-in-room-b",
                "sdp": {"type": "offer", "sdp": "..."}
            }
        })
        err_cross = await comm_a.receive_json_from()
        self.assertEqual(err_cross['type'], 'error')
        self.assertEqual(err_cross['payload']['code'], 'TARGET_PEER_NOT_FOUND')

        await comm_a.disconnect()
        await comm_b.disconnect()

    async def test_websocket_send_before_join_rejected(self):
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]
        communicator = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers,
            subprotocols=['bearer', self.client_token]
        )
        await communicator.connect()

        # Gửi chat_message khi chưa gọi join_room
        await communicator.send_json_to({
            "type": "chat_message",
            "payload": {"content": "Chào khi chưa join"}
        })

        resp = await communicator.receive_json_from()
        self.assertEqual(resp['type'], 'error')
        self.assertEqual(resp['payload']['code'], 'NOT_JOINED')

        await communicator.disconnect()

    async def test_websocket_malformed_json_handled_gracefully(self):
        headers = [
            (b"origin", b"http://localhost"),
            (b"host", b"localhost"),
        ]
        communicator = WebsocketCommunicator(
            application,
            f"/ws/meeting/{self.room.room_code}/",
            headers=headers
        )
        await communicator.connect()

        # Gửi text không phải JSON hợp lệ
        await communicator.send_to(text_data="{ bad json syntax without quotes")

        resp = await communicator.receive_json_from()
        self.assertEqual(resp['type'], 'error')
        self.assertEqual(resp['payload']['code'], 'MALFORMED_JSON')

        await communicator.disconnect()
