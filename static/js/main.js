/**
 * AI Meeting - Client Scripts (Tuần 1 Foundation)
 */

document.addEventListener('DOMContentLoaded', () => {
    const btnJoinRoom = document.getElementById('btnJoinRoom');
    const inputRoomCode = document.getElementById('inputRoomCode');
    const joinError = document.getElementById('joinError');
    const btnCreateRoom = document.getElementById('btnCreateRoom');

    if (btnJoinRoom && inputRoomCode) {
        btnJoinRoom.addEventListener('click', async () => {
            const roomCode = inputRoomCode.value.trim().toLowerCase();
            joinError.textContent = '';

            if (!roomCode) {
                joinError.textContent = 'Vui lòng nhập mã phòng.';
                return;
            }

            try {
                btnJoinRoom.disabled = true;
                btnJoinRoom.textContent = 'Đang kiểm tra...';

                const response = await fetch(`/api/v1/rooms/${encodeURIComponent(roomCode)}/`);
                const data = await response.json();

                if (response.ok && data.success) {
                    alert(`Phòng hợp lệ!\nTiêu đề: ${data.data.title}\nSố người hiện tại: ${data.data.current_participants_count}/${data.data.max_participants}\n\n(Chức năng giao diện gọi video WebRTC sẽ được triển khai ở Tuần 2)`);
                } else {
                    joinError.textContent = data.error?.message || 'Không tìm thấy phòng họp này.';
                }
            } catch (err) {
                joinError.textContent = 'Lỗi kết nối tới máy chủ backend.';
            } finally {
                btnJoinRoom.disabled = false;
                btnJoinRoom.textContent = 'Vào phòng';
            }
        });

        inputRoomCode.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                btnJoinRoom.click();
            }
        });
    }

    if (btnCreateRoom) {
        btnCreateRoom.addEventListener('click', () => {
            alert('Để tạo phòng họp mới, bạn cần đăng nhập tài khoản.\nVui lòng sử dụng API /api/v1/auth/login/ hoặc công cụ API client (Postman/Curl) trong tuần này.');
        });
    }
});
