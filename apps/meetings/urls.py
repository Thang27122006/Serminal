from django.urls import path
from .views import (
    RoomListCreateView,
    RoomDetailView,
    RoomJoinView,
    RoomParticipantsView,
    RoomMessagesView
)

app_name = 'meetings'

urlpatterns = [
    path('', RoomListCreateView.as_view(), name='room-list-create'),
    path('<str:room_code>/', RoomDetailView.as_view(), name='room-detail'),
    path('<str:room_code>/join/', RoomJoinView.as_view(), name='room-join'),
    path('<str:room_code>/participants/', RoomParticipantsView.as_view(), name='room-participants'),
    path('<str:room_code>/messages/', RoomMessagesView.as_view(), name='room-messages'),
]
