# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ChatView.as_view(), name='chat_room'),
    path('upload/', views.FileUploadView.as_view(), name='file_upload'),
    path('attachments/', views.ProcessAttachmentsView.as_view(), name='process_attachments'),
    path('files/', views.UploadedFilesView.as_view(), name='uploaded_files'),
    path('files/<int:file_id>/', views.UploadedFilesView.as_view(), name='delete_file'),
    path('folder/', views.FolderPathView.as_view(), name='folder_path'),
    path('database/connect/', views.DatabaseConnectionView.as_view(), name='db_connect'),
    path('database/query/', views.ExecuteQueryView.as_view(), name='execute_query'),
    path('history/', views.ChatHistoryView.as_view(), name='chat_history'),
]

