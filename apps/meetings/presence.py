"""
Quản lý trạng thái thành viên trực tuyến (Online Presence Manager) cho phòng họp.
Độc lập với các bản ghi cơ sở dữ liệu PostgreSQL lâu dài.
Đảm bảo tính cô lập hoàn toàn giữa các phòng (Room Isolation).
"""

import asyncio
from datetime import datetime, timezone


class RoomPresenceManager:
    """
    Quản lý danh sách thành viên đang có mặt trực tuyến trong từng phòng họp.
    Cung cấp các phương thức async-safe để thêm, bớt, tra cứu thành viên và định tuyến signaling.
    """
    _rooms = {}  # room_code -> { peer_id: peer_dict }
    _lock = asyncio.Lock()

    @classmethod
    async def add_peer(cls, room_code: str, peer_id: str, peer_info: dict) -> list:
        """
        Thêm một thành viên vào danh sách trực tuyến của phòng.
        Trả về danh sách tất cả các thành viên hiện có khác trong phòng.
        """
        async with cls._lock:
            if room_code not in cls._rooms:
                cls._rooms[room_code] = {}

            # Thu thập danh sách các peer hiện có trước khi thêm peer mới
            existing_peers = [
                {
                    "peer_id": p["peer_id"],
                    "user_id": p.get("user_id"),
                    "display_name": p.get("display_name", "Khách"),
                    "is_host": p.get("is_host", False),
                    "joined_at": p.get("joined_at")
                }
                for pid, p in cls._rooms[room_code].items()
                if pid != peer_id
            ]

            # Lưu thông tin peer mới
            peer_info["joined_at"] = peer_info.get("joined_at") or datetime.now(timezone.utc).isoformat()
            cls._rooms[room_code][peer_id] = peer_info

            return existing_peers

    @classmethod
    async def remove_peer(cls, room_code: str, peer_id: str) -> dict:
        """
        Xóa thành viên khỏi danh sách trực tuyến khi rời phòng hoặc ngắt kết nối.
        Trả về thông tin thành viên vừa bị xóa nếu tồn tại.
        """
        async with cls._lock:
            if room_code in cls._rooms and peer_id in cls._rooms[room_code]:
                removed = cls._rooms[room_code].pop(peer_id)
                if not cls._rooms[room_code]:
                    del cls._rooms[room_code]
                return removed
            return None

    @classmethod
    async def get_peer(cls, room_code: str, peer_id: str) -> dict:
        """Tra cứu thông tin thành viên theo room_code và peer_id."""
        async with cls._lock:
            return cls._rooms.get(room_code, {}).get(peer_id)

    @classmethod
    async def get_peer_channel(cls, room_code: str, peer_id: str) -> str:
        """Lấy channel_name của một peer cụ thể trong đúng phòng."""
        async with cls._lock:
            peer = cls._rooms.get(room_code, {}).get(peer_id)
            return peer.get("channel_name") if peer else None

    @classmethod
    async def get_online_peers(cls, room_code: str) -> list:
        """Lấy danh sách tất cả thành viên đang trực tuyến trong phòng."""
        async with cls._lock:
            if room_code not in cls._rooms:
                return []
            return [
                {
                    "peer_id": p["peer_id"],
                    "user_id": p.get("user_id"),
                    "display_name": p.get("display_name", "Khách"),
                    "is_host": p.get("is_host", False),
                    "joined_at": p.get("joined_at")
                }
                for p in cls._rooms[room_code].values()
            ]

    @classmethod
    async def get_online_count(cls, room_code: str) -> int:
        """Đếm số thành viên đang trực tuyến trong phòng."""
        async with cls._lock:
            return len(cls._rooms.get(room_code, {}))

    @classmethod
    async def clear_all(cls):
        """Xóa sạch toàn bộ presence (dùng khi reset hoặc trong test case)."""
        async with cls._lock:
            cls._rooms.clear()
