from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            user_data = UserSerializer(user).data
            return Response({
                "success": True,
                "data": {
                    "access": access_token,
                    "refresh": refresh_token,
                    "token": access_token,
                    "user": user_data
                },
                "message": "Đăng ký tài khoản thành công."
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu đăng ký không hợp lệ.",
                "details": serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            return Response({
                "success": True,
                "data": {
                    "access": access_token,
                    "refresh": refresh_token,
                    "token": access_token,
                    "user": UserSerializer(user).data
                },
                "message": "Đăng nhập thành công."
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Tên đăng nhập hoặc mật khẩu không chính xác.",
                "details": serializer.errors
            }
        }, status=status.HTTP_401_UNAUTHORIZED)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                "success": False,
                "error": {
                    "code": "MISSING_REFRESH_TOKEN",
                    "message": "Vui lòng cung cấp refresh token."
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            # Nếu bật rotation trong settings, refresh.set_jti() sinh refresh mới
            new_refresh = str(refresh)
            return Response({
                "success": True,
                "data": {
                    "access": access_token,
                    "refresh": new_refresh,
                    "token": access_token
                },
                "message": "Làm mới access token thành công."
            }, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_REFRESH_TOKEN",
                    "message": "Refresh token không hợp lệ hoặc đã hết hạn."
                }
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        if hasattr(request.user, 'auth_token'):
            try:
                request.user.auth_token.delete()
            except Exception:
                pass

        return Response({
            "success": True,
            "message": "Đăng xuất thành công."
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "success": True,
            "data": UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)
