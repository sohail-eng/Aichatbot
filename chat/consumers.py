# chat/consumers.py
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from ai_services.chat_processor import ChatProcessor

logger = logging.getLogger('ai_services')

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.room_group_name = None
        self._chat_processor = None
    
    @property
    def chat_processor(self):
        if self._chat_processor is None:
            self._chat_processor = ChatProcessor()
        return self._chat_processor
    
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Connected to chat. You can upload files, connect to databases, or ask me anything!',
            'timestamp': self._get_timestamp()
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'message')
            
            if message_type == 'message':
                await self._handle_chat_message(text_data_json)
            elif message_type == 'file_question':
                await self._handle_file_question(text_data_json)
            elif message_type == 'database_query':
                await self._handle_database_query(text_data_json)
            elif message_type == 'ping':
                await self._handle_ping()
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred processing your message'
            }))
    
    async def _handle_chat_message(self, data):
        """Handle regular chat message"""
        message = data.get('message', '')
        attached_files = data.get('attached_files', [])
        
        if not message.strip():
            return
        
        # Echo user message with file info
        user_message = message
        if attached_files:
            file_names = [f['name'] for f in attached_files]
            user_message += f"\n\n📎 Attached files: {', '.join(file_names)}"
        
        await self.send(text_data=json.dumps({
            'type': 'user',
            'message': user_message,
            'timestamp': self._get_timestamp()
        }))
        
        # Send initial thinking status
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'message': '💭 Thinking...'
        }))
        
        # If there are attached files, send processing status updates
        if attached_files:
            # Send analyzing status
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'message': '🔍 Analyzing attached files...'
            }))
            
            # Small delay to show the status
            await asyncio.sleep(1)
            
            # Send RAG processing status
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'message': '🧠 Processing with RAG system...'
            }))
            
            # Small delay to show the status
            await asyncio.sleep(1)
            
            # Send searching status
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'message': '🔎 Searching for relevant data...'
            }))
            
            # Small delay to show the status
            await asyncio.sleep(1)
        
        # Send generating status
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'message': '🤖 Generating AI response...'
        }))
        
        # Process message with attachments
        metadata = {
            'attached_files': attached_files
        }
        result = await self._process_message_async(message, metadata)
        
        # Send AI response (only once)
        import uuid
        await self.send(text_data=json.dumps({
            'type': 'ai',
            'message': result['response'],
            'metadata': result.get('metadata', {}),
            'timestamp': self._get_timestamp(),
            'id': str(uuid.uuid4())  # Unique message ID to prevent duplicates
        }))
    
    async def _handle_file_question(self, data):
        """Handle file-related question"""
        message = data.get('message', '')
        file_id = data.get('file_id', '')
        
        if not message.strip():
            return
        
        # Echo user message
        await self.send(text_data=json.dumps({
            'type': 'user',
            'message': f"Question about file: {message}",
            'timestamp': self._get_timestamp()
        }))
        
        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'message': 'Analyzing file...'
        }))
        
        # Process file question
        metadata = {'file_question': True, 'file_id': file_id}
        result = await self._process_message_async(message, metadata)
        
        # Send AI response
        await self.send(text_data=json.dumps({
            'type': 'ai',
            'message': result['response'],
            'metadata': result.get('metadata', {}),
            'timestamp': self._get_timestamp()
        }))
    
    async def _handle_database_query(self, data):
        """Handle database query"""
        query = data.get('query', '')
        connection_id = data.get('connection_id', '')
        
        if not query.strip():
            return
        
        # Echo user query
        await self.send(text_data=json.dumps({
            'type': 'user',
            'message': f"SQL Query: {query}",
            'timestamp': self._get_timestamp()
        }))
        
        # Send processing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'message': 'Executing query...'
        }))
        
        # Process database query
        metadata = {'database_query': True, 'connection_id': connection_id}
        result = await self._process_message_async(query, metadata)
        
        # Send AI response
        await self.send(text_data=json.dumps({
            'type': 'ai',
            'message': result['response'],
            'metadata': result.get('metadata', {}),
            'timestamp': self._get_timestamp()
        }))
    
    async def _handle_ping(self):
        """Handle ping message"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': self._get_timestamp()
        }))
    
    async def _process_message_async(self, message: str, metadata=None):
        """Async wrapper for message processing"""
        # Set the session_id in the chat processor
        self.chat_processor.session_id = self.session_id
        return await self.chat_processor.process_message(
            self.session_id, message, 'user', metadata
        )
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()
    
    # Handlers for group messages
    async def chat_message(self, event):
        message = event['message']
        message_type = event.get('type', 'message')
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': message_type,
            'message': message,
            'timestamp': self._get_timestamp()
        }))