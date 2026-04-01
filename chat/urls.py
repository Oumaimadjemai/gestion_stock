# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('rooms/', views.ChatRoomListCreateView.as_view()),
    path('rooms/<int:pk>/', views.ChatRoomDetailView.as_view()),
    path('rooms/<int:room_id>/messages/', views.MessageListView.as_view()),
    path('rooms/<int:room_id>/send/', views.MessageCreateView.as_view()),
    path('rooms/<int:room_id>/mark-read/', views.MarkMessagesReadView.as_view()),
    path('rooms/<int:room_id>/add-participants/', views.AddParticipantsToRoomView.as_view()),
    path('rooms/<int:room_id>/remove-participant/', views.RemoveParticipantFromRoomView.as_view()),
    path('rooms/<int:room_id>/leave/', views.LeaveRoomView.as_view()),
    
    # Message endpoints
    path('messages/<int:pk>/', views.MessageDetailView.as_view()),
    path('messages/<int:message_id>/mark-read/', views.MarkSingleMessageReadView.as_view()),
    
    # Download endpoint - ADD THIS
    path('download/<int:message_id>/', views.DownloadFileView.as_view(), name='download_file'),
    
    # Other endpoints
    path('unread/', views.UnreadMessagesView.as_view()),
    path('upload/', views.FileUploadView.as_view()),
]