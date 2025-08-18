# AI Data Assistant Chat Application

A Django-based chat application that allows users to upload files, connect to databases, and interact with an AI assistant for data analysis.

## Features

- **File Upload & Analysis**: Upload CSV, Excel, text, JSON, and PDF files
- **Database Connections**: Connect to SQL Server, PostgreSQL, MySQL databases
- **AI Chat**: Interactive chat with AI assistant for data analysis
- **Real-time WebSocket Communication**: Live chat interface
- **File Processing**: Process entire folders of data files

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations

```bash
python manage.py migrate
```

### 3. Create Admin User

```bash
python manage.py steup_chat
```

This will create an admin user with credentials: `admin` / `admin123`

### 4. AI Service Setup (Optional but Recommended)

The application requires an AI service for chat functionality. You have several options:

#### Option A: Foundry Local (Recommended)
1. Install Foundry Local: https://foundry.local/
2. Start the service: `foundry local`
3. The application will automatically connect to `localhost:8080`

#### Option B: Ollama
1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama2`
3. Start Ollama: `ollama serve`
4. Update `AI_CONFIG` in `settings.py` to point to Ollama

#### Option C: OpenAI API
1. Get an OpenAI API key
2. Update `AI_CONFIG` in `settings.py`:
```python
AI_CONFIG = {
    'LLAMA_API_URL': 'https://api.openai.com/v1/chat/completions',
    'MODEL_NAME': 'gpt-3.5-turbo',
    'API_KEY': 'your-openai-api-key',
}
```

### 5. Start the Application

```bash
python manage.py runserver
```

Visit http://localhost:8000 to access the application.

## Usage

### File Upload
1. Drag and drop files into the upload area
2. Optionally ask a specific question about your file
3. The AI will analyze the file and provide insights

### Database Connection
1. Click "Connect to Database"
2. Select your database type
3. Enter connection details
4. Ask questions about your data or request SQL queries

### Chat Interface
- Type messages in the chat input
- The AI will respond with helpful information
- Upload files or connect databases for enhanced functionality

## Configuration

### Environment Variables (Recommended for Production)
```bash
export SECRET_KEY="your-secret-key"
export DEBUG="False"
export ALLOWED_HOSTS="your-domain.com"
export AI_SERVICE_URL="your-ai-service-url"
```

### Database Configuration
Update `DATABASES` in `settings.py` for production use.

### Channel Layers
For production, switch to Redis:
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('your-redis-host', 6379)],
        },
    },
}
```

## Troubleshooting

### AI Service Not Available
If you see "Unable to connect to AI service" messages:
1. Make sure your AI service is running
2. Check the URL in `AI_CONFIG`
3. Verify network connectivity
4. The application will still work for file uploads and database connections

### WebSocket Connection Issues
1. Ensure Redis is running (for production)
2. Check firewall settings
3. Verify the routing configuration

### File Upload Issues
1. Check file size limits in `settings.py`
2. Ensure the media directory is writable
3. Verify file format support

## Development

### Running Tests
```bash
python manage.py test
```

### Testing AI Service
```bash
python manage.py test_ai
```

### Code Structure
- `chat/`: Main Django app with models, views, and consumers
- `ai_services/`: AI service integrations and data processing
- `templates/`: HTML templates
- `static/`: Static files (CSS, JS)

## License

This project is licensed under the MIT License.
