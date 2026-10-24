/**
 * AI MEETING — CLIENT SCRIPT (Tuần 2: JWT & Room Management)
 */

document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // 1. Quản lý Token JWT trong LocalStorage & Helper API
    // =========================================================================
    const TOKEN_KEY = 'ai_meeting_access_token';
    const REFRESH_KEY = 'ai_meeting_refresh_token';
    const USER_KEY = 'ai_meeting_user';

    function getAccessToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function getRefreshToken() {
        return localStorage.getItem(REFRESH_KEY);
    }

    function getStoredUser() {
        try {
            return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
        } catch {
            return null;
        }
    }

    function saveAuth(access, refresh, user) {
        if (access) localStorage.setItem(TOKEN_KEY, access);
        if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
        if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    }

    function clearAuth() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(USER_KEY);
    }

    // Helper gọi API có tự động đính kèm JWT Bearer Token và tự động Refresh Token khi hết hạn
    async function apiFetch(url, options = {}) {
        options.headers = options.headers || {};
        if (!(options.body instanceof FormData)) {
            options.headers['Content-Type'] = 'application/json';
        }

        const token = getAccessToken();
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }

        let response = await fetch(url, options);

        // Nếu nhận mã 401 và có refresh token, thử refresh access token tự động
        if (response.status === 401 && getRefreshToken() && !url.includes('/auth/token/refresh/')) {
            const refreshRes = await fetch('/api/v1/auth/token/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: getRefreshToken() })
            });

            if (refreshRes.ok) {
                const refreshData = await refreshRes.json();
                if (refreshData.success && refreshData.data?.access) {
                    saveAuth(refreshData.data.access, refreshData.data.refresh || getRefreshToken(), null);
                    // Thử gọi lại request ban đầu với token mới
                    options.headers['Authorization'] = `Bearer ${refreshData.data.access}`;
                    response = await fetch(url, options);
                }
            } else {
                // Refresh token đã hết hạn -> xóa phiên và chuyển về màn hình đăng nhập
                clearAuth();
                renderAuthUI();
                showToast('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.', 'error');
            }
        }

        return response;
    }

    // Toast Notification Utility
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 4000);
    }

    // =========================================================================
    // 2. DOM Elements & State Management
    // =========================================================================
    const guestSection = document.getElementById('guestSection');
    const authSection = document.getElementById('authSection');
    const navAuthArea = document.getElementById('navAuthArea');

    // Tabs
    const tabLoginBtn = document.getElementById('tabLoginBtn');
    const tabRegisterBtn = document.getElementById('tabRegisterBtn');
    const formLogin = document.getElementById('formLogin');
    const formRegister = document.getElementById('formRegister');
    const linkSwitchToRegister = document.getElementById('linkSwitchToRegister');
    const linkSwitchToLogin = document.getElementById('linkSwitchToLogin');

    // Alerts
    const loginAlert = document.getElementById('loginAlert');
    const registerAlert = document.getElementById('registerAlert');
    const guestJoinAlert = document.getElementById('guestJoinAlert');
    const createRoomAlert = document.getElementById('createRoomAlert');
    const createRoomSuccess = document.getElementById('createRoomSuccess');
    const authJoinAlert = document.getElementById('authJoinAlert');

    // Forms
    const formGuestJoin = document.getElementById('formGuestJoin');
    const formCreateRoom = document.getElementById('formCreateRoom');
    const formAuthJoin = document.getElementById('formAuthJoin');
    const checkIsPrivate = document.getElementById('checkIsPrivate');
    const passcodeFieldGroup = document.getElementById('passcodeFieldGroup');
    const hostedRoomsContainer = document.getElementById('hostedRoomsContainer');
    const btnRefreshRooms = document.getElementById('btnRefreshRooms');
    const btnLogout = document.getElementById('btnLogout');

    // Modal
    const roomModal = document.getElementById('roomModal');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const btnProceedMeeting = document.getElementById('btnProceedMeeting');
    const btnCopyModalCode = document.getElementById('btnCopyModalCode');
    const modalRoomTitle = document.getElementById('modalRoomTitle');
    const modalRoomCode = document.getElementById('modalRoomCode');
    const modalDisplayName = document.getElementById('modalDisplayName');
    const modalRole = document.getElementById('modalRole');
    const modalPeerId = document.getElementById('modalPeerId');

    // =========================================================================
    // TUẦN 3: WebSocket Signaling & Room DOM Elements & State
    // =========================================================================
    const meetingRoomSection = document.getElementById('meetingRoomSection');
    const roomViewTitle = document.getElementById('roomViewTitle');
    const roomViewCode = document.getElementById('roomViewCode');
    const roomViewRole = document.getElementById('roomViewRole');
    const wsStatusBadge = document.getElementById('wsStatusBadge');
    const wsStatusText = document.getElementById('wsStatusText');
    const btnLeaveMeetingTop = document.getElementById('btnLeaveMeetingTop');
    const btnLeaveMeetingBottom = document.getElementById('btnLeaveMeetingBottom');
    const btnCopyRoomViewCode = document.getElementById('btnCopyRoomViewCode');

    const onlinePeerCount = document.getElementById('onlinePeerCount');
    const selfDisplayName = document.getElementById('selfDisplayName');
    const selfPeerId = document.getElementById('selfPeerId');
    const onlinePeersList = document.getElementById('onlinePeersList');

    const selectTargetPeer = document.getElementById('selectTargetPeer');
    const btnSendOffer = document.getElementById('btnSendOffer');
    const btnSendAnswer = document.getElementById('btnSendAnswer');
    const btnSendIce = document.getElementById('btnSendIce');
    const btnClearSignalingLogs = document.getElementById('btnClearSignalingLogs');
    const signalingLogsBox = document.getElementById('signalingLogsBox');

    const chatMessagesContainer = document.getElementById('chatMessagesContainer');
    const formSendChat = document.getElementById('formSendChat');
    const inputChatMessage = document.getElementById('inputChatMessage');

    const toolbarRoomTitle = document.getElementById('toolbarRoomTitle');
    const toolbarRoomCode = document.getElementById('toolbarRoomCode');
    const btnToggleMic = document.getElementById('btnToggleMic');
    const btnToggleCam = document.getElementById('btnToggleCam');
    const btnToggleScreen = document.getElementById('btnToggleScreen');

    let currentMeetingSocket = null;
    let currentRoomData = null;
    let currentPasscode = '';
    let onlinePeersMap = new Map();

    // =========================================================================
    // 3. Tab Switching
    // =========================================================================
    function switchTab(isLogin) {
        if (isLogin) {
            tabLoginBtn.classList.add('active');
            tabRegisterBtn.classList.remove('active');
            formLogin.classList.remove('hidden');
            formRegister.classList.add('hidden');
        } else {
            tabRegisterBtn.classList.add('active');
            tabLoginBtn.classList.remove('active');
            formRegister.classList.remove('hidden');
            formLogin.classList.add('hidden');
        }
    }

    if (tabLoginBtn) tabLoginBtn.addEventListener('click', () => switchTab(true));
    if (tabRegisterBtn) tabRegisterBtn.addEventListener('click', () => switchTab(false));
    if (linkSwitchToRegister) linkSwitchToRegister.addEventListener('click', (e) => { e.preventDefault(); switchTab(false); });
    if (linkSwitchToLogin) linkSwitchToLogin.addEventListener('click', (e) => { e.preventDefault(); switchTab(true); });

    // Toggle passcode input khi bấm checkbox "Phòng riêng tư"
    if (checkIsPrivate && passcodeFieldGroup) {
        checkIsPrivate.addEventListener('change', () => {
            if (checkIsPrivate.checked) {
                passcodeFieldGroup.classList.remove('hidden');
            } else {
                passcodeFieldGroup.classList.add('hidden');
                document.getElementById('roomPasscode').value = '';
            }
        });
    }

    // =========================================================================
    // 4. Kiểm tra Trạng thái Đăng nhập & Render Giao diện (Render Auth UI)
    // =========================================================================
    async function renderAuthUI() {
        const token = getAccessToken();
        let user = getStoredUser();

        if (token) {
            // Xác thực token với endpoint /auth/me/
            try {
                const res = await apiFetch('/api/v1/auth/me/');
                if (res.ok) {
                    const data = await res.json();
                    if (data.success && data.data) {
                        user = data.data;
                        saveAuth(null, null, user);
                    }
                } else {
                    // Token không hợp lệ
                    clearAuth();
                    user = null;
                }
            } catch (err) {
                console.error("Lỗi xác minh token:", err);
            }
        }

        if (user && getAccessToken()) {
            // Trạng thái: Đã đăng nhập
            guestSection.classList.add('hidden');
            authSection.classList.remove('hidden');

            const displayName = user.full_name || user.username;
            const firstLetter = displayName.charAt(0).toUpperCase();

            document.getElementById('userFullName').textContent = displayName;
            document.getElementById('userUsername').textContent = user.username;
            document.getElementById('userEmail').textContent = user.email;
            document.getElementById('userAvatarText').textContent = firstLetter;

            // Cập nhật Header
            navAuthArea.innerHTML = `
                <div class="nav-user-tag">
                    <span class="nav-avatar-mini">${firstLetter}</span>
                    <span>${displayName}</span>
                </div>
            `;

            // Tải danh sách phòng do người dùng làm Host
            loadHostedRooms();
        } else {
            // Trạng thái: Chưa đăng nhập (Guest)
            guestSection.classList.remove('hidden');
            authSection.classList.add('hidden');
            navAuthArea.innerHTML = `
                <button id="navLoginBtn" class="btn btn-sm btn-secondary">Đăng nhập</button>
            `;
            const navLoginBtn = document.getElementById('navLoginBtn');
            if (navLoginBtn) {
                navLoginBtn.addEventListener('click', () => {
                    switchTab(true);
                    document.getElementById('authCard').scrollIntoView({ behavior: 'smooth' });
                });
            }
        }
    }

    // =========================================================================
    // 5. Đăng ký & Đăng nhập (Authentication APIs)
    // =========================================================================
    // Đăng ký tài khoản
    if (formRegister) {
        formRegister.addEventListener('submit', async (e) => {
            e.preventDefault();
            registerAlert.classList.add('hidden');
            registerAlert.textContent = '';
            document.querySelectorAll('.field-error').forEach(el => el.textContent = '');

            const payload = {
                username: document.getElementById('regUsername').value.trim(),
                email: document.getElementById('regEmail').value.trim(),
                password: document.getElementById('regPassword').value,
                first_name: document.getElementById('regFirstName').value.trim(),
                last_name: document.getElementById('regLastName').value.trim(),
            };

            const submitBtn = document.getElementById('btnRegisterSubmit');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang xử lý đăng ký...';

            try {
                const res = await fetch('/api/v1/auth/register/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    saveAuth(data.data.access, data.data.refresh, data.data.user);
                    showToast('Đăng ký tài khoản thành công! Đã tự động đăng nhập.', 'success');
                    renderAuthUI();
                } else {
                    const err = data.error;
                    if (err?.details) {
                        for (const [field, msgs] of Object.entries(err.details)) {
                            const errEl = document.getElementById(`err_reg${field.charAt(0).toUpperCase() + field.slice(1)}`);
                            if (errEl) {
                                errEl.textContent = Array.isArray(msgs) ? msgs.join(' ') : msgs;
                            }
                        }
                    }
                    registerAlert.textContent = err?.message || 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.';
                    registerAlert.classList.remove('hidden');
                }
            } catch (err) {
                registerAlert.textContent = 'Lỗi kết nối tới máy chủ. Vui lòng thử lại sau.';
                registerAlert.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Tạo tài khoản';
            }
        });
    }

    // Đăng nhập
    if (formLogin) {
        formLogin.addEventListener('submit', async (e) => {
            e.preventDefault();
            loginAlert.classList.add('hidden');
            loginAlert.textContent = '';

            const payload = {
                username: document.getElementById('loginUsername').value.trim(),
                password: document.getElementById('loginPassword').value,
            };

            const submitBtn = document.getElementById('btnLoginSubmit');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang đăng nhập...';

            try {
                const res = await fetch('/api/v1/auth/login/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    saveAuth(data.data.access, data.data.refresh, data.data.user);
                    showToast('Đăng nhập thành công!', 'success');
                    renderAuthUI();
                } else {
                    loginAlert.textContent = data.error?.message || 'Tên đăng nhập hoặc mật khẩu không chính xác.';
                    loginAlert.classList.remove('hidden');
                }
            } catch (err) {
                loginAlert.textContent = 'Lỗi kết nối tới máy chủ.';
                loginAlert.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Đăng nhập';
            }
        });
    }

    // Đăng xuất (Blacklist JWT Refresh Token)
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            const refreshToken = getRefreshToken();
            try {
                await apiFetch('/api/v1/auth/logout/', {
                    method: 'POST',
                    body: JSON.stringify({ refresh: refreshToken })
                });
            } catch (err) {
                console.warn("Lỗi khi thu hồi token tại backend:", err);
            }
            clearAuth();
            renderAuthUI();
            showToast('Đã đăng xuất thành công.', 'info');
        });
    }

    // =========================================================================
    // 6. Quản lý Phòng họp (Room Management APIs)
    // =========================================================================
    // Tạo phòng họp mới
    if (formCreateRoom) {
        formCreateRoom.addEventListener('submit', async (e) => {
            e.preventDefault();
            createRoomAlert.classList.add('hidden');
            createRoomSuccess.classList.add('hidden');

            const isPrivate = checkIsPrivate.checked;
            const passcode = document.getElementById('roomPasscode').value.trim();

            if (isPrivate && !passcode) {
                createRoomAlert.textContent = 'Vui lòng nhập mật khẩu cho phòng riêng tư.';
                createRoomAlert.classList.remove('hidden');
                return;
            }

            const payload = {
                title: document.getElementById('roomTitle').value.trim() || 'Cuộc họp mới',
                max_participants: parseInt(document.getElementById('roomMaxParticipants').value, 10),
                is_private: isPrivate,
                passcode: passcode
            };

            const submitBtn = document.getElementById('btnCreateRoomSubmit');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang khởi tạo phòng...';

            try {
                const res = await apiFetch('/api/v1/rooms/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    const room = data.data;
                    createRoomSuccess.innerHTML = `
                        <strong>Tạo phòng thành công!</strong><br>
                        Mã phòng: <strong class="highlight-code">${room.room_code}</strong>
                        <button type="button" class="btn btn-sm btn-secondary btn-copy-inline" data-code="${room.room_code}">Sao chép mã</button>
                    `;
                    createRoomSuccess.classList.remove('hidden');
                    document.getElementById('roomPasscode').value = '';
                    checkIsPrivate.checked = false;
                    passcodeFieldGroup.classList.add('hidden');

                    showToast(`Phòng họp "${room.title}" đã được tạo.`, 'success');
                    loadHostedRooms();

                    // Gán sự kiện nút sao chép inline
                    const copyBtn = createRoomSuccess.querySelector('.btn-copy-inline');
                    if (copyBtn) {
                        copyBtn.addEventListener('click', () => {
                            navigator.clipboard.writeText(room.room_code);
                            copyBtn.textContent = 'Đã chép!';
                            setTimeout(() => { copyBtn.textContent = 'Sao chép mã'; }, 2000);
                        });
                    }
                } else {
                    createRoomAlert.textContent = data.error?.message || 'Không thể tạo phòng họp.';
                    createRoomAlert.classList.remove('hidden');
                }
            } catch (err) {
                createRoomAlert.textContent = 'Lỗi kết nối tới máy chủ khi tạo phòng.';
                createRoomAlert.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Khởi tạo phòng ngay';
            }
        });
    }

    // Tải danh sách phòng do User làm Host
    async function loadHostedRooms() {
        if (!hostedRoomsContainer) return;
        hostedRoomsContainer.innerHTML = '<div class="loading-spinner">Đang tải danh sách phòng...</div>';

        try {
            const res = await apiFetch('/api/v1/rooms/');
            const data = await res.json();

            if (res.ok && data.success) {
                const rooms = data.data || [];
                if (rooms.length === 0) {
                    hostedRoomsContainer.innerHTML = `
                        <div class="empty-state">
                            <p>Bạn chưa tạo phòng họp nào.</p>
                            <small class="text-muted">Hãy khởi tạo phòng họp đầu tiên bằng form bên cạnh!</small>
                        </div>
                    `;
                    return;
                }

                hostedRoomsContainer.innerHTML = '';
                rooms.forEach(room => {
                    const card = document.createElement('div');
                    card.className = 'room-card-item';
                    const createdDate = new Date(room.created_at).toLocaleString('vi-VN');

                    card.innerHTML = `
                        <div class="room-card-top">
                            <div class="room-card-title">${escapeHTML(room.title)}</div>
                            <div class="room-card-badges">
                                <span class="badge-status ${room.is_active ? 'active' : 'closed'}">
                                    ${room.is_active ? 'Đang mở' : 'Đã đóng'}
                                </span>
                                ${room.is_private ? '<span class="badge-private">Riêng tư 🔒</span>' : ''}
                            </div>
                        </div>
                        <div class="room-card-code-row">
                            <span class="room-code-tag">${room.room_code}</span>
                            <button class="btn btn-sm btn-secondary btn-copy-card" data-code="${room.room_code}">Sao chép</button>
                        </div>
                        <div class="room-card-bottom">
                            <span>Sức chứa: ${room.current_participants_count}/${room.max_participants}</span>
                            <span>Tạo lúc: ${createdDate}</span>
                        </div>
                    `;

                    // Sự kiện sao chép mã phòng
                    const copyBtn = card.querySelector('.btn-copy-card');
                    copyBtn.addEventListener('click', () => {
                        navigator.clipboard.writeText(room.room_code);
                        copyBtn.textContent = 'Đã chép!';
                        setTimeout(() => { copyBtn.textContent = 'Sao chép'; }, 1500);
                    });

                    hostedRoomsContainer.appendChild(card);
                });
            } else {
                hostedRoomsContainer.innerHTML = '<div class="empty-state">Không thể tải danh sách phòng.</div>';
            }
        } catch (err) {
            hostedRoomsContainer.innerHTML = '<div class="empty-state">Lỗi kết nối khi tải danh sách phòng.</div>';
        }
    }

    if (btnRefreshRooms) {
        btnRefreshRooms.addEventListener('click', () => loadHostedRooms());
    }

    // Tham gia phòng họp (Authenticated User)
    if (formAuthJoin) {
        formAuthJoin.addEventListener('submit', async (e) => {
            e.preventDefault();
            authJoinAlert.classList.add('hidden');
            authJoinAlert.textContent = '';

            const roomCode = document.getElementById('authRoomCode').value.trim().toLowerCase();
            const passcode = document.getElementById('authPasscode').value.trim();

            await handleJoinRoom(roomCode, passcode, '', authJoinAlert, document.getElementById('btnAuthJoinSubmit'));
        });
    }

    // Tham gia phòng họp (Guest User)
    if (formGuestJoin) {
        formGuestJoin.addEventListener('submit', async (e) => {
            e.preventDefault();
            guestJoinAlert.classList.add('hidden');
            guestJoinAlert.textContent = '';

            const roomCode = document.getElementById('guestRoomCode').value.trim().toLowerCase();
            const displayName = document.getElementById('guestDisplayName').value.trim();
            const passcode = document.getElementById('guestPasscode').value.trim();

            if (!displayName) {
                guestJoinAlert.textContent = 'Vui lòng nhập tên hiển thị của bạn.';
                guestJoinAlert.classList.remove('hidden');
                return;
            }

            await handleJoinRoom(roomCode, passcode, displayName, guestJoinAlert, document.getElementById('btnGuestJoinSubmit'));
        });
    }

    // Hàm gọi API /rooms/{code}/join/ và hiển thị kết quả
    async function handleJoinRoom(roomCode, passcode, displayName, alertBox, submitBtn) {
        if (!roomCode) {
            alertBox.textContent = 'Vui lòng nhập mã phòng hợp lệ.';
            alertBox.classList.remove('hidden');
            return;
        }

        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Đang kiểm tra quyền truy cập...';

        try {
            const res = await apiFetch(`/api/v1/rooms/${encodeURIComponent(roomCode)}/join/`, {
                method: 'POST',
                body: JSON.stringify({
                    passcode: passcode,
                    display_name: displayName
                })
            });

            const data = await res.json();

            if (res.ok && data.success) {
                // Lưu trạng thái phòng hiện tại
                currentRoomData = data.data;
                currentPasscode = passcode || '';
                // Hiển thị modal thông tin phòng đã được phê duyệt tham gia
                openRoomModal(data.data);
            } else {
                alertBox.textContent = data.error?.message || 'Không thể tham gia phòng họp.';
                alertBox.classList.remove('hidden');
            }
        } catch (err) {
            alertBox.textContent = 'Lỗi kết nối tới máy chủ kiểm tra phòng.';
            alertBox.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    // =========================================================================
    // 7. Modal Handlers
    // =========================================================================
    function openRoomModal(roomData) {
        modalRoomTitle.textContent = roomData.title || 'Phòng họp';
        modalRoomCode.textContent = roomData.room_code;
        modalDisplayName.textContent = roomData.display_name;
        modalRole.textContent = roomData.role === 'host' ? 'Chủ tọa (Host) 👑' : 'Thành viên tham gia (Participant)';
        modalPeerId.textContent = roomData.peer_id;

        btnCopyModalCode.onclick = () => {
            navigator.clipboard.writeText(roomData.room_code);
            btnCopyModalCode.textContent = 'Đã chép!';
            setTimeout(() => { btnCopyModalCode.textContent = 'Sao chép'; }, 1500);
        };

        btnProceedMeeting.onclick = () => {
            roomModal.classList.add('hidden');
            enterMeetingRoom(currentRoomData, currentPasscode);
        };

        roomModal.classList.remove('hidden');
    }

    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', () => {
            roomModal.classList.add('hidden');
        });
    }

    // Đóng modal khi bấm ra ngoài hộp
    window.addEventListener('click', (e) => {
        if (e.target === roomModal) {
            roomModal.classList.add('hidden');
        }
    });

    // =========================================================================
    // 8. TUẦN 3: WEBSOCKET SIGNALING & PHÒNG HỌP TRỰC TIẾP
    // =========================================================================

    function enterMeetingRoom(roomData, passcode) {
        if (!roomData) return;
        currentRoomData = roomData;
        currentPasscode = passcode || '';
        onlinePeersMap.clear();

        // Chuyển màn hình: ẩn guest & auth dashboard, hiện meeting room
        if (guestSection) guestSection.classList.add('hidden');
        if (authSection) authSection.classList.add('hidden');
        if (meetingRoomSection) meetingRoomSection.classList.remove('hidden');

        // Gán thông tin hiển thị trên UI
        if (roomViewTitle) roomViewTitle.textContent = roomData.title || 'Phòng họp trực tuyến';
        if (toolbarRoomTitle) toolbarRoomTitle.textContent = roomData.title || 'Phòng họp trực tuyến';
        if (roomViewCode) roomViewCode.textContent = roomData.room_code;
        if (toolbarRoomCode) toolbarRoomCode.textContent = roomData.room_code;
        if (roomViewRole) {
            roomViewRole.textContent = roomData.role === 'host' ? 'Chủ tọa 👑' : 'Thành viên';
        }
        if (selfDisplayName) selfDisplayName.textContent = roomData.display_name;
        if (selfPeerId) selfPeerId.textContent = roomData.peer_id;

        // Reset logs & chat
        if (signalingLogsBox) {
            signalingLogsBox.innerHTML = '<div class="log-entry log-system">[Hệ thống] Đang khởi tạo kết nối WebSocket...</div>';
        }
        if (chatMessagesContainer) {
            chatMessagesContainer.innerHTML = '<div class="chat-system-message">Chào mừng bạn vào phòng họp! Mọi tin nhắn sẽ được đồng bộ tức thì qua WebSocket.</div>';
        }
        renderOnlinePeers();

        // Kết nối WebSocket Signaling
        connectMeetingWebSocket(roomData.room_code, roomData.display_name, currentPasscode);
    }

    function connectMeetingWebSocket(roomCode, displayName, passcode) {
        if (currentMeetingSocket) {
            try { currentMeetingSocket.close(); } catch (e) {}
            currentMeetingSocket = null;
        }

        updateWsStatus('connecting', 'Đang kết nối WebSocket...');
        logSignaling('system', `Bắt đầu kết nối ws/meetings/${roomCode}/...`);

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/meetings/${encodeURIComponent(roomCode)}/`;

        // Chuẩn bảo mật Subprotocol: 'bearer', <access_token>
        const token = getAccessToken();
        const subprotocols = token ? ['bearer', token] : [];

        try {
            currentMeetingSocket = new WebSocket(wsUrl, subprotocols);
        } catch (err) {
            updateWsStatus('disconnected', 'Không thể tạo kết nối WebSocket');
            logSignaling('err', `Lỗi kết nối: ${err.message}`);
            return;
        }

        currentMeetingSocket.onopen = () => {
            updateWsStatus('connected', `Đã kết nối (Group: room_${roomCode})`);
            logSignaling('system', `WebSocket đã mở (READY). Gửi thông điệp join_room...`);

            // Gửi thông điệp join_room chuẩn JSON Envelope
            const reqId = 'req_' + Date.now();
            const joinPayload = {
                display_name: displayName,
                passcode: passcode || ''
            };
            if (token) {
                joinPayload.token = token;
            }

            sendSignalingPacket('join_room', joinPayload, reqId);
        };

        currentMeetingSocket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleIncomingMessage(msg);
            } catch (err) {
                logSignaling('err', `Nhận dữ liệu không phải JSON: ${event.data}`);
            }
        };

        currentMeetingSocket.onerror = (err) => {
            logSignaling('err', 'Sự kiện lỗi WebSocket phát sinh.');
        };

        currentMeetingSocket.onclose = (event) => {
            updateWsStatus('disconnected', `Đã ngắt kết nối (Mã: ${event.code})`);
            logSignaling('err', `WebSocket đóng. Code: ${event.code}, Reason: ${event.reason || 'None'}`);

            if (event.code === 4001) {
                showToast('Chưa xác thực JWT. Vui lòng đăng nhập lại.', 'error');
            } else if (event.code === 4003) {
                showToast('Từ chối truy cập: Sai mật khẩu phòng hoặc phòng đầy.', 'error');
            } else if (event.code === 4004) {
                showToast('Phòng họp không tồn tại.', 'error');
            } else if (event.code === 4005) {
                showToast('Phòng họp này đã kết thúc/đóng.', 'error');
            }
        };
    }

    function handleIncomingMessage(msg) {
        const { type, request_id, payload } = msg;
        logSignaling('in', `[RX] ${type}: ${JSON.stringify(payload || {})}`);

        switch (type) {
            case 'online_list': {
                onlinePeersMap.clear();
                const peers = payload?.peers || [];
                peers.forEach(p => {
                    onlinePeersMap.set(p.peer_id, p);
                });
                renderOnlinePeers();
                break;
            }
            case 'user_joined': {
                const user = payload?.user;
                if (user && user.peer_id) {
                    onlinePeersMap.set(user.peer_id, user);
                    renderOnlinePeers();
                    appendSystemChatMessage(`👋 ${user.display_name || 'Một thành viên'} đã tham gia phòng họp.`);
                }
                break;
            }
            case 'user_left': {
                const peerId = payload?.peer_id;
                const user = onlinePeersMap.get(peerId);
                const name = user ? user.display_name : (payload?.display_name || peerId);
                if (peerId) {
                    onlinePeersMap.delete(peerId);
                    renderOnlinePeers();
                    appendSystemChatMessage(`🚪 ${name} đã rời khỏi phòng họp.`);
                }
                break;
            }
            case 'chat_message': {
                appendChatMessageBubble(payload);
                break;
            }
            case 'offer': {
                const sender = payload?.sender_peer_id;
                const peerObj = onlinePeersMap.get(sender);
                const sName = peerObj ? peerObj.display_name : sender;
                showToast(`Nhận SDP Offer từ [${sName}]`, 'info');
                appendSystemChatMessage(`📨 Nhận SDP Offer từ [${sName}]. WebRTC sẵn sàng đàm phán.`);
                break;
            }
            case 'answer': {
                const sender = payload?.sender_peer_id;
                const peerObj = onlinePeersMap.get(sender);
                const sName = peerObj ? peerObj.display_name : sender;
                showToast(`Nhận SDP Answer từ [${sName}]`, 'info');
                appendSystemChatMessage(`📬 Nhận SDP Answer từ [${sName}]. Bắt tay WebRTC thành công.`);
                break;
            }
            case 'ice_candidate': {
                const sender = payload?.sender_peer_id;
                showToast(`Nhận ICE Candidate từ ${sender}`, 'info');
                break;
            }
            case 'error': {
                const errMsg = payload?.message || 'Lỗi từ Signaling Server';
                showToast(`Lỗi WebSocket: ${errMsg}`, 'error');
                logSignaling('err', `[Server Error] ${payload?.code}: ${errMsg}`);
                break;
            }
            default:
                logSignaling('system', `Thông điệp chưa hỗ trợ: ${type}`);
        }
    }

    function sendSignalingPacket(type, payload, requestId = null) {
        if (!currentMeetingSocket || currentMeetingSocket.readyState !== WebSocket.OPEN) {
            showToast('WebSocket chưa kết nối!', 'warning');
            return false;
        }
        const packet = {
            type: type,
            request_id: requestId || ('req_' + Date.now()),
            payload: payload || {}
        };
        const raw = JSON.stringify(packet);
        currentMeetingSocket.send(raw);
        logSignaling('out', `[TX] ${type}: ${JSON.stringify(payload)}`);
        return true;
    }

    function updateWsStatus(state, text) {
        if (!wsStatusBadge || !wsStatusText) return;
        wsStatusBadge.className = `ws-status-badge ${state}`;
        wsStatusText.textContent = text;
    }

    function logSignaling(type, text) {
        if (!signalingLogsBox) return;
        const time = new Date().toLocaleTimeString('vi-VN');
        const entry = document.createElement('div');
        entry.className = `log-entry log-${type}`;
        entry.textContent = `[${time}] ${text}`;
        signalingLogsBox.appendChild(entry);
        signalingLogsBox.scrollTop = signalingLogsBox.scrollHeight;

        // Giới hạn 100 dòng log
        if (signalingLogsBox.children.length > 100) {
            signalingLogsBox.removeChild(signalingLogsBox.firstChild);
        }
    }

    function renderOnlinePeers() {
        if (!onlinePeersList) return;

        // Lọc các peer khác (loại bỏ bản thân theo peer_id)
        const myPeerId = currentRoomData?.peer_id;
        const otherPeers = Array.from(onlinePeersMap.values()).filter(p => p.peer_id !== myPeerId);

        // Cập nhật tổng số thành viên online (bao gồm bản thân)
        if (onlinePeerCount) {
            onlinePeerCount.textContent = otherPeers.length + 1;
        }

        // Cập nhật dropdown chọn peer nhận signaling
        if (selectTargetPeer) {
            const currentSelected = selectTargetPeer.value;
            selectTargetPeer.innerHTML = '';

            if (otherPeers.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = '-- Chưa có peer nào khác --';
                selectTargetPeer.appendChild(opt);
                btnSendOffer.disabled = true;
                btnSendAnswer.disabled = true;
                btnSendIce.disabled = true;
            } else {
                otherPeers.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.peer_id;
                    opt.textContent = `${p.display_name} (${p.peer_id.slice(0, 8)}...)`;
                    if (p.peer_id === currentSelected) opt.selected = true;
                    selectTargetPeer.appendChild(opt);
                });
                btnSendOffer.disabled = false;
                btnSendAnswer.disabled = false;
                btnSendIce.disabled = false;
            }
        }

        // Render danh sách peer items
        onlinePeersList.innerHTML = '';
        if (otherPeers.length === 0) {
            onlinePeersList.innerHTML = '<div class="empty-peers-notice">Chưa có thành viên nào khác trong phòng...</div>';
            return;
        }

        otherPeers.forEach(peer => {
            const item = document.createElement('div');
            item.className = 'peer-item';
            const initial = (peer.display_name || 'U').charAt(0).toUpperCase();

            item.innerHTML = `
                <div class="peer-item-info">
                    <div class="peer-item-avatar">${initial}</div>
                    <div>
                        <div class="peer-item-name">${escapeHTML(peer.display_name)}</div>
                        <div class="peer-item-meta">${peer.peer_id.slice(0, 8)}...</div>
                    </div>
                </div>
                <div class="peer-actions">
                    <span class="peer-item-role">${peer.role === 'host' ? 'Chủ tọa 👑' : 'Thành viên'}</span>
                    <button class="btn btn-xs btn-outline-primary btn-quick-offer" data-peer="${peer.peer_id}" title="Gửi Offer SDP">
                        📨 Offer
                    </button>
                </div>
            `;

            // Nút gửi Offer nhanh
            const quickBtn = item.querySelector('.btn-quick-offer');
            quickBtn.addEventListener('click', () => {
                sendTestSignaling('offer', peer.peer_id);
            });

            onlinePeersList.appendChild(item);
        });
    }

    function appendChatMessageBubble(payload) {
        if (!chatMessagesContainer) return;

        const isSelf = payload.sender_peer_id === currentRoomData?.peer_id;
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${isSelf ? 'self' : ''}`;

        const senderName = isSelf ? 'Bạn' : (payload.sender_name || 'Ẩn danh');
        const time = new Date(payload.timestamp || Date.now()).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });

        bubble.innerHTML = `
            <div class="chat-bubble-sender">
                <span>${escapeHTML(senderName)}</span>
                ${!isSelf ? `<span class="peer-id-meta">(${payload.sender_peer_id?.slice(0, 6)}...)</span>` : ''}
            </div>
            <div class="chat-bubble-text">${escapeHTML(payload.message)}</div>
            <div class="chat-bubble-time">${time}</div>
        `;

        chatMessagesContainer.appendChild(bubble);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    function appendSystemChatMessage(text) {
        if (!chatMessagesContainer) return;
        const msg = document.createElement('div');
        msg.className = 'chat-system-message';
        msg.textContent = text;
        chatMessagesContainer.appendChild(msg);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    function sendTestSignaling(type, targetPeerId) {
        if (!targetPeerId) {
            targetPeerId = selectTargetPeer ? selectTargetPeer.value : '';
        }
        if (!targetPeerId) {
            showToast('Vui lòng chọn Peer nhận (Target Peer)!', 'warning');
            return;
        }

        let payload = {
            target_peer_id: targetPeerId
        };

        if (type === 'offer') {
            payload.sdp = {
                type: 'offer',
                sdp: 'v=0\r\no=- 42000 2 IN IP4 127.0.0.1\r\ns=AI Meeting WebRTC Test Session\r\nt=0 0\r\na=sendrecv\r\n'
            };
        } else if (type === 'answer') {
            payload.sdp = {
                type: 'answer',
                sdp: 'v=0\r\no=- 42001 2 IN IP4 127.0.0.1\r\ns=AI Meeting WebRTC Test Session Answer\r\nt=0 0\r\na=recvonly\r\n'
            };
        } else if (type === 'ice_candidate') {
            payload.candidate = {
                candidate: 'candidate:842163049 1 udp 1677729535 192.168.1.100 54321 typ host',
                sdpMid: '0',
                sdpMLineIndex: 0
            };
        }

        const sent = sendSignalingPacket(type, payload);
        if (sent) {
            showToast(`Đã gửi ${type.toUpperCase()} tới Peer ${targetPeerId.slice(0, 8)}...`, 'info');
        }
    }

    function leaveMeetingRoom() {
        if (currentMeetingSocket && currentMeetingSocket.readyState === WebSocket.OPEN) {
            sendSignalingPacket('leave_room', {});
            try { currentMeetingSocket.close(); } catch (e) {}
        }
        currentMeetingSocket = null;
        currentRoomData = null;
        currentPasscode = '';
        onlinePeersMap.clear();

        // Ẩn phòng họp
        if (meetingRoomSection) meetingRoomSection.classList.add('hidden');

        // Quay lại màn hình tương ứng
        renderAuthUI();
        if (getAccessToken()) {
            loadHostedRooms();
        }
        showToast('Đã rời khỏi phòng họp.', 'info');
    }

    // =========================================================================
    // 9. Event Listeners cho Tuần 3 UI
    // =========================================================================

    // Rời phòng
    if (btnLeaveMeetingTop) {
        btnLeaveMeetingTop.addEventListener('click', () => leaveMeetingRoom());
    }
    if (btnLeaveMeetingBottom) {
        btnLeaveMeetingBottom.addEventListener('click', () => leaveMeetingRoom());
    }

    // Sao chép mã phòng trong meeting room view
    if (btnCopyRoomViewCode) {
        btnCopyRoomViewCode.addEventListener('click', () => {
            if (currentRoomData?.room_code) {
                navigator.clipboard.writeText(currentRoomData.room_code);
                btnCopyRoomViewCode.textContent = 'Đã chép!';
                setTimeout(() => { btnCopyRoomViewCode.textContent = '📋 Chép mã'; }, 1500);
            }
        });
    }

    // Xóa logs
    if (btnClearSignalingLogs) {
        btnClearSignalingLogs.addEventListener('click', () => {
            if (signalingLogsBox) {
                signalingLogsBox.innerHTML = '<div class="log-entry log-system">[Hệ thống] Đã xóa toàn bộ log.</div>';
            }
        });
    }

    // Gửi chat
    if (formSendChat) {
        formSendChat.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = inputChatMessage.value.trim();
            if (!text) return;

            const sent = sendSignalingPacket('chat_message', { message: text });
            if (sent) {
                inputChatMessage.value = '';
            }
        });
    }

    // Nút gửi Signaling Simulator
    if (btnSendOffer) {
        btnSendOffer.addEventListener('click', () => {
            sendTestSignaling('offer');
        });
    }
    if (btnSendAnswer) {
        btnSendAnswer.addEventListener('click', () => {
            sendTestSignaling('answer');
        });
    }
    if (btnSendIce) {
        btnSendIce.addEventListener('click', () => {
            sendTestSignaling('ice_candidate');
        });
    }

    // Nút toolbar media giả lập (Tuần 4 Preview)
    if (btnToggleMic) {
        btnToggleMic.addEventListener('click', () => {
            btnToggleMic.classList.toggle('active');
            btnToggleMic.classList.toggle('muted');
            const isMuted = btnToggleMic.classList.contains('muted');
            btnToggleMic.innerHTML = isMuted ? '🔇 Mic Tắt' : '🎤 Mic Bật';
            showToast(isMuted ? 'Đã tắt Micro (Audio Track Muted)' : 'Đã bật Micro', 'info');
        });
    }
    if (btnToggleCam) {
        btnToggleCam.addEventListener('click', () => {
            btnToggleCam.classList.toggle('active');
            btnToggleCam.classList.toggle('muted');
            const isOff = btnToggleCam.classList.contains('muted');
            btnToggleCam.innerHTML = isOff ? '🚫 Cam Tắt' : '📹 Cam Bật';
            showToast(isOff ? 'Đã tắt Camera (Video Track Stopped)' : 'Đã bật Camera', 'info');
        });
    }
    if (btnToggleScreen) {
        btnToggleScreen.addEventListener('click', () => {
            btnToggleScreen.classList.toggle('active');
            showToast('Chia sẻ màn hình (getDisplayMedia) sẽ kết nối WebRTC Media trong Tuần 4.', 'info');
        });
    }

    // Helper escape HTML ngăn chặn XSS
    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag));
    }

    // Khởi chạy ứng dụng
    renderAuthUI();
});
