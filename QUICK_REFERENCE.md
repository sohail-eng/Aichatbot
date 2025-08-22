# Quick Reference Guide - Key Files & Functions

## 🎯 **Core Files for Next Development Steps**

### **1. AI Processing Pipeline**
```
ai_services/chat_processor.py          # Main orchestrator
ai_services/file_analyzer.py           # File analysis engine  
ai_services/enhanced_llm_service.py    # AI response generation
```

**Key Functions to Modify:**
- `process_message()` - Main entry point
- `_process_message_with_attachments()` - File-attached questions
- `analyze_question_with_files()` - File analysis
- `process_question_with_files()` - AI response generation

### **2. Real-time Communication**
```
chat/consumers.py                      # WebSocket handling
chat/routing.py                        # WebSocket URLs
```

**Key Functions to Modify:**
- `_handle_chat_message()` - Message processing
- `_process_message_async()` - Async processing

### **3. File Management**
```
chat/views.py                          # HTTP endpoints
ai_services/file_service.py            # File processing
```

**Key Functions to Modify:**
- `FileUploadView` - File uploads
- `ProcessAttachmentsView` - Multi-file processing
- `save_uploaded_file()` - File storage
- `process_file()` - File content processing

### **4. Database & Models**
```
chat/models.py                         # Data models
chat_project/settings.py               # Configuration
```

**Key Models:**
- `ChatSession` - Chat sessions
- `Message` - Chat messages  
- `UploadedFile` - File metadata
- `DatabaseConnection` - DB connections

### **5. Frontend Interface**
```
templates/chat/chat_room.html          # Main UI
templates/chat/base.html               # Base template
```

**Key Features:**
- Two-column layout (chat + sidebar)
- File attachment badges
- Real-time status updates
- Accordion sections

## 🔧 **Configuration Files**

### **Django Settings**
```python
# chat_project/settings.py
AI_CONFIG = {
    'api_key': 'your-ai-api-key',
    'base_url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:streamGenerateContent'
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### **URL Configuration**
```python
# chat/urls.py
urlpatterns = [
    path('', views.ChatView.as_view(), name='chat_room'),
    path('upload/', views.FileUploadView.as_view(), name='file_upload'),
    path('attachments/', views.ProcessAttachmentsView.as_view(), name='process_attachments'),
    path('files/', views.UploadedFilesView.as_view(), name='uploaded_files'),
]
```

## 🚀 **Common Development Tasks**

### **1. Add New File Type Support**
```python
# In ai_services/file_analyzer.py
def _analyze_new_file_type(self, file_path, search_keywords, question):
    # Add your analysis logic here
    pass

# Update _analyze_single_file() to include new type
elif file_type == 'new_type':
    return self._analyze_new_file_type(file_path, search_keywords, question)
```

### **2. Add New Status Updates**
```python
# In ai_services/enhanced_llm_service.py
def get_processing_status(self, step: str) -> str:
    status_messages = {
        'analyzing': "🔍 Analyzing attached files...",
        'searching': "🔎 Searching for relevant data...",
        'processing': "⚙️ Processing found data...",
        'generating': "🤖 Generating AI response...",
        'compiling': "📝 Compiling final response...",
        'thinking': "💭 Thinking...",
        'new_step': "🆕 New processing step...",  # Add here
    }
```

### **3. Add New WebSocket Message Type**
```python
# In chat/consumers.py
async def receive(self, text_data):
    data = json.loads(text_data)
    message_type = data.get('type')
    
    if message_type == 'message':
        await self._handle_chat_message(data)
    elif message_type == 'new_type':  # Add here
        await self._handle_new_message_type(data)
```

### **4. Add New Database Model**
```python
# In chat/models.py
class NewModel(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'new_model'
```

## 🧪 **Testing Commands**

```bash
# Test file analysis
python manage.py test_file_analysis

# Test BGP analysis
python test_bgp_analysis.py

# Test complete flow
python test_complete_bgp_flow.py

# Run Django server
python manage.py runserver

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

## 📊 **Key Data Flow**

```
User Question + Attached Files
           ↓
    WebSocket (consumers.py)
           ↓
    Chat Processor (chat_processor.py)
           ↓
    File Analyzer (file_analyzer.py)
           ↓
    Enhanced LLM (enhanced_llm_service.py)
           ↓
    AI Response + File Analysis
           ↓
    WebSocket Response
```

## 🔍 **Debugging Tips**

### **1. Check File Analysis**
```python
# Test file analysis directly
from ai_services.file_analyzer import FileAnalyzer
analyzer = FileAnalyzer()
result = analyzer.analyze_question_with_files(question, attached_files)
print(result)
```

### **2. Check WebSocket Connection**
```javascript
// In browser console
console.log('WebSocket status:', chatSocket.readyState);
// 0: Connecting, 1: Open, 2: Closing, 3: Closed
```

### **3. Check Database Models**
```python
# In Django shell
python manage.py shell
from chat.models import UploadedFile, ChatSession
print(UploadedFile.objects.all())
print(ChatSession.objects.all())
```

## 🎯 **Next Steps for Claude**

### **Immediate Improvements (1-2 steps)**
1. **Performance Optimization**
   - Add caching for file analysis results
   - Optimize database queries
   - Implement background task processing

2. **Enhanced User Experience**
   - Add data visualization (charts, graphs)
   - Implement export functionality
   - Add keyboard shortcuts

### **Medium-term Features (2-3 steps)**
3. **Advanced Search**
   - Fuzzy matching for search terms
   - Synonym detection
   - Advanced filtering options

4. **Production Readiness**
   - Security hardening
   - Monitoring and logging
   - Load testing

### **Long-term Scalability (3+ steps)**
5. **Architecture Improvements**
   - Microservices architecture
   - Database optimization
   - Horizontal scaling support

This quick reference provides the essential information needed to continue development with Claude, focusing on the most important files and common development tasks.
