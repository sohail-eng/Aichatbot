# Django Chat App with Llama3 - Installation Guide

## Prerequisites

1. **Python 3.9+** installed
2. **Redis** server running
3. **Ollama with Llama3** installed locally
4. **MS SQL Server** (if using database features)

## Quick Setup

### 1. Install Ollama and Llama3

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Llama3 model
ollama pull llama3

# Start Ollama service (runs on http://localhost:11434)
ollama serve
```

### 2. Install Redis

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**On macOS:**
```bash
brew install redis
brew services start redis
```

**On Windows:**
Download and install from: https://redis.io/download

### 3. Project Setup

```bash
# Create project directory
mkdir django-chat-app
cd django-chat-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create Django project
django-admin startproject chat_project .
cd chat_project
python manage.py startapp chat
mkdir ai_services
```

### 4. Database Setup

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Setup application
python manage.py setup_chat

# Create superuser (optional)
python manage.py createsuperuser
```

### 5. Test AI Connection

```bash
# Test Llama3 connection
python manage.py test_ai
```

### 6. Run the Application

```bash
# Start Django development server
python manage.py runserver

# In another terminal, ensure Redis is running
redis-cli ping  # Should return PONG
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Configuration
LLAMA_API_URL=http://localhost:11434/api/generate
MODEL_NAME=llama3
MAX_TOKENS=2048
TEMPERATURE=0.7

# Database Configuration
MSSQL_SERVER=your_server
MSSQL_DATABASE=your_database
MSSQL_USERNAME=your_username
MSSQL_PASSWORD=your_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
```

### MS SQL Server Setup

If using MS SQL Server, install the ODBC driver:

**On Ubuntu/Debian:**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

**On Windows:**
Download and install the Microsoft ODBC Driver 17 for SQL Server

## Usage

1. **Access the Application:**
   - Open your browser to `http://localhost:8000`

2. **Upload Files:**
   - Drag and drop files or click the upload area
   - Supported formats: CSV, Excel, Text, JSON, PDF
   - Add optional questions about the file

3. **Connect to Database:**
   - Click "Connect to Database"
   - Enter your MS SQL Server credentials
   - Ask natural language questions about your data

4. **Process Folders:**
   - Enter a local folder path
   - Get analysis of all supported files in the folder

5. **Chat Features:**
   - Real-time responses from Llama3
   - Context-aware conversations
   - File and database analysis
   - SQL query generation and execution

## Architecture

### AI Services (Separated Files)

- **`llama_service.py`**: Handles all Llama3 interactions
- **`database_service.py`**: Manages database connections and queries
- **`file_service.py`**: Processes file uploads and content extraction
- **`chat_processor.py`**: Orchestrates all AI services

### Key Features

- **Real-time WebSocket communication**
- **File upload with drag-and-drop**
- **MS SQL Server integration**
- **Context-aware AI responses**
- **Query history and logging**
- **Secure query validation**

## Troubleshooting

### Common Issues

1. **Llama3 not responding:**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Restart Ollama
   ollama serve
   ```

2. **Redis connection issues:**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Restart Redis
   sudo systemctl restart redis-server
   ```

3. **Database connection fails:**
   - Verify ODBC driver installation
   - Check firewall settings
   - Ensure SQL Server allows remote connections

4. **WebSocket connection issues:**
   - Check if Daphne is running
   - Verify Redis is accessible
   - Check browser console for errors

### Development Commands

```bash
# Run with debug output
python manage.py runserver --verbosity=2

# Check logs
tail -f chat_app.log

# Clean up old files
python manage.py shell -c "from ai_services.file_service import FileService; FileService().cleanup_old_files()"

# Reset database
python manage.py flush
python manage.py migrate
```

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in settings
2. Configure proper database (PostgreSQL recommended)
3. Use proper web server (nginx + gunicorn/daphne)
4. Set up SSL certificates
5. Configure environment variables securely
6. Use Docker for containerized deployment

## Security Notes

- Database passwords should be encrypted in production
- Implement proper authentication and authorization
- Validate and sanitize all user inputs
- Use HTTPS in production
- Implement rate limiting for API endpoints
- Regularly update dependencies

## Support

- Check Django logs: `chat_app.log`
- Monitor Redis: `redis-cli monitor`
- Ollama logs: Check Ollama service logs
- Database connectivity: Test with SQL client tools