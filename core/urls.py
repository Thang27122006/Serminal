"""
URL configuration for AI Meeting project.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import render


def health_check(request):
    """API kiểm tra trạng thái sức khỏe của hệ thống."""
    return JsonResponse({
        "status": "healthy",
        "service": "AI Meeting Backend & Signaling",
        "version": "1.0.0-week1"
    })


def home_view(request):
    """Trang chủ chào mừng và hiển thị trạng thái hệ thống."""
    return render(request, 'index.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    
    # API endpoints
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/auth/', include('apps.authentication.urls', namespace='auth')),
    path('api/v1/rooms/', include('apps.meetings.urls', namespace='rooms')),
]
