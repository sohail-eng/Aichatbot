# chat/models.py
from django.db import models
from django.contrib.auth.models import User
import json

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user or 'Anonymous'}"

class Message(models.Model):
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('ai', 'AI Assistant'),
        ('system', 'System'),
        ('file', 'File Upload'),
        ('db_query', 'Database Query'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    metadata = models.TextField(blank=True)  # JSON field for additional data
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def set_metadata(self, data):
        self.metadata = json.dumps(data)
    
    def get_metadata(self):
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."

class UploadedFile(models.Model):
    FILE_TYPES = [
        ('csv', 'CSV File'),
        ('xlsx', 'Excel File'),
        ('txt', 'Text File'),
        ('pdf', 'PDF File'),
        ('json', 'JSON File'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='files')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField()
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_status = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.file_name} ({self.file_type})"

class DatabaseConnection(models.Model):
    CONNECTION_TYPES = [
        ('mssql', 'Microsoft SQL Server'),
        ('postgresql', 'PostgreSQL'),
        ('mysql', 'MySQL'),
        ('sqlite', 'SQLite'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES)
    server = models.CharField(max_length=255)
    database = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255)  # Should be encrypted in production
    port = models.IntegerField(default=1433)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.connection_type})"

class QueryHistory(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='queries')
    database_connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE)
    query = models.TextField()
    result_count = models.IntegerField(default=0)
    execution_time = models.FloatField(default=0.0)  # in seconds
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"Query at {self.timestamp}: {self.query[:50]}..."