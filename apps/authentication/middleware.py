"""
Middleware xác thực JWT cho Django Channels WebSocket.
Hỗ trợ lấy Token qua:
1. WebSocket Subprotocol: Sec-WebSocket-Protocol: bearer, <jwt_access_token>
2. Query String (Fallback / Dev / Testing): ws://.../?token=<jwt_access_token>
"""

import urllib.parse
from django.contrib.auth.models import AnonymousUser, User
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token_str(token_str):
    """Xác minh chuỗi JWT Access Token và trả về đối tượng User tương ứng."""
    if not token_str:
        return AnonymousUser()
    try:
        token = AccessToken(token_str)
        user_id = token.get('user_id')
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id, is_active=True)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Channels Middleware trích xuất và xác minh JWT Token cho WebSocket.
    Không bắt buộc truyền qua Query String để tránh ghi token vào web server access logs.
    """

    async def __call__(self, scope, receive, send):
        if scope.get('type') == 'websocket':
            token = None
            accepted_subprotocol = None

            # 1. Kiểm tra Sec-WebSocket-Protocol (Khuyến nghị chuẩn bảo mật)
            # Browser: new WebSocket(url, ['bearer', jwtToken])
            subprotocols = scope.get('subprotocols', [])
            if subprotocols and len(subprotocols) >= 2 and subprotocols[0].lower() == 'bearer':
                token = subprotocols[1]
                accepted_subprotocol = 'bearer'
            elif subprotocols and len(subprotocols) == 1 and subprotocols[0].lower() != 'bearer':
                # Trường hợp truyền trực tiếp token làm subprotocol duy nhất
                token = subprotocols[0]

            # 2. Kiểm tra Headers nếu có authorization header
            if not token:
                headers = dict(scope.get('headers', []))
                auth_header = headers.get(b'authorization', b'').decode('utf-8')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:].strip()
                elif b'sec-websocket-protocol' in headers:
                    proto_val = headers[b'sec-websocket-protocol'].decode('utf-8')
                    parts = [p.strip() for p in proto_val.split(',')]
                    if len(parts) >= 2 and parts[0].lower() == 'bearer':
                        token = parts[1]
                        accepted_subprotocol = 'bearer'

            # 3. Fallback: Query String (?token=...)
            if not token:
                query_string = scope.get('query_string', b'').decode('utf-8')
                if query_string:
                    query_params = urllib.parse.parse_qs(query_string)
                    token_list = query_params.get('token', [])
                    if token_list:
                        token = token_list[0]

            # Xác thực người dùng
            if token:
                user = await get_user_from_token_str(token)
                scope['user'] = user
                scope['jwt_token_present'] = True
                scope['jwt_token_valid'] = user.is_authenticated
                if accepted_subprotocol:
                    scope['accepted_subprotocol'] = accepted_subprotocol
            else:
                scope['jwt_token_present'] = False
                scope['jwt_token_valid'] = False
                # Giữ nguyên user từ AuthMiddlewareStack nếu đã có session
                if 'user' not in scope or not scope['user'].is_authenticated:
                    scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Bọc AuthMiddlewareStack và JWTAuthMiddleware cho Channels routing."""
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
