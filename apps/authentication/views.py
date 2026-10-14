from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            user_data = UserSerializer(user).data
            return Response({
                "success": True,
                "data": {
                    "token": token.key,
                    "user": user_data
                },
                "message": "Đăng ký tài khoản thành công."
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": false if hasattr(__builtins__, 'false') else False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu đăng ký không hợp lệ.",
                "details": serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "success": True,
                "data": {
                    "token": token.key,
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


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
