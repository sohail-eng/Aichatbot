# chat_project/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'your-secret-key-here'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'chat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chat_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'chat_project.asgi.application'

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# MS SQL Configuration (for data queries)
MSSQL_CONFIG = {
    'server': 'your_server_name',
    'database': 'your_database_name',
    'username': 'your_username',
    'password': 'your_password',
    'driver': '{ODBC Driver 17 for SQL Server}',
}

# AI Configuration
AI_CONFIG = {
    'LLAMA_API_URL': 'http://127.0.0.1:11434', 
    # 'LLAMA_API_URL': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent',  # Google AI Studio
    'MODEL_NAME': 'qwen2.5:7b',
    # 'MODEL_NAME': 'gemini-1.5-flash',
    'MAX_TOKENS': 2048,
    'TEMPERATURE': 0.7,
    # 'API_KEY': 'AIzaSyA7vBmqL-zZpJrvNoijDzHTvYaEeNctEig',  # Replace with your actual API key
}

# File Upload Settings
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB

# ChromaDB settings
CHROMA_DB_PATH = MEDIA_ROOT / 'chroma_db'
CHROMA_DB_HOST = 'localhost'
CHROMA_DB_PORT = 8000

# RAG System settings
RAG_CHUNK_SIZE = 1000
RAG_CHUNK_OVERLAP = 200
RAG_MAX_RESULTS = 15
RAG_SIMILARITY_THRESHOLD = 0.7

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Security Settings
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'chat_app.log',
        },
    },
    'loggers': {
        'ai_services': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

