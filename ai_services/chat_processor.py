# ai_services/chat_processor.py
import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from channels.db import database_sync_to_async
from chat.models import ChatSession, Message, UploadedFile
from .foundry_service import FoundryService
from .database_service import DatabaseService
from .file_service import FileService
from .enhanced_llm_service import EnhancedLLMService
from .rag_service import RAGService

logger = logging.getLogger('ai_services')

class ChatProcessor:
    def __init__(self):
        self.llama_service = FoundryService()
        self.database_service = DatabaseService()
        self.file_service = FileService()
        self.enhanced_llm_service = EnhancedLLMService()
        self.rag_service = RAGService()
    
    async def process_message(self, session_id: str, message_content: str, 
                       message_type: str = 'user', metadata: Optional[Dict] = None) -> Dict:
        """Process incoming chat message"""
        try:
            # Get or create chat session
            session = await self._get_or_create_session(session_id)
            
            # Save user message
            await self._create_message(session, message_type, message_content, metadata)
            
            # Get conversation context
            context = await self._get_conversation_context(session)
            
            # Handle attached files if any
            attached_files = metadata.get('attached_files', []) if metadata else []
            
            # If message has attached files, process with enhanced LLM service
            if attached_files:
                logger.info(f"Processing message with {len(attached_files)} attached files")
                response = await self._process_message_with_attachments(
                    session, message_content, attached_files, context
                )
            else:
                # Determine message intent and process accordingly
                intent = self._analyze_intent(message_content, metadata)
                
                if intent['type'] == 'database_query':
                    response = await self._process_database_query(session, message_content, context, intent)
                elif intent['type'] == 'file_analysis':
                    response = await self._process_file_analysis(session, message_content, context, intent)
                elif intent['type'] == 'general_chat':
                    response = await self._process_general_chat(session, message_content, context)
                else:
                    response = await self._process_general_chat(session, message_content, context)
            
            # Save AI response
            ai_message = await self._create_message(
                session, 'ai', response['content'], response.get('metadata', {})
            )
            return {
                'success': True,
                'response': response['content'],
                'metadata': response.get('metadata', {}),
                'message_id': ai_message.id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Sorry, I encountered an error processing your message.'
            }
    
    @database_sync_to_async
    def _create_message(self, session, message_type, content, metadata):
        message = Message.objects.create(
            session=session,
            message_type=message_type,
            content=content,
            metadata=metadata or {}
        )
        message.set_metadata(metadata or {})
        message.save()
        return message

    async def process_file_upload(self, session_id: str, uploaded_file, user_question: str = "") -> Dict:
        """Process uploaded file"""
        try:
            session = await self._get_or_create_session(session_id)
            
            # Save file
            file_info = self.file_service.save_uploaded_file(uploaded_file, session_id)
            if not file_info['success']:
                return file_info
            
            # Create UploadedFile record
            file_record = await self._create_uploaded_file(session, file_info)
            
            # Process file content
            processed_file = self.file_service.process_file(
                file_info['full_path'], 
                file_info['file_type']
            )
            
            if not processed_file['success']:
                return processed_file
            
            # Generate AI analysis
            file_summary = self.file_service.get_file_summary(file_info['full_path'])
            # Streaming AI analysis
            analysis_chunks = []
            try:
                # TEMPORARY: Skip AI service for testing
                logger.info("Skipping AI service for testing - using fallback analysis")
                analysis_response = self._generate_fallback_analysis(processed_file, file_info, user_question)
                
                # Uncomment below when AI service is working
                # async for chunk in self.llama_service.analyze_file_content(
                #     file_summary, file_info['file_type'], user_question):
                #     analysis_chunks.append(chunk)
                # analysis_response = ''.join(analysis_chunks)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                # Fallback analysis when AI service is unavailable
                analysis_response = self._generate_fallback_analysis(processed_file, file_info, user_question)
            # Save file upload message
            await self._create_message(
                session, 'file', f"Uploaded file: {file_info['filename']}",
                {'file_id': file_record.id, 'file_info': file_info}
            )
            # Save AI analysis
            await self._create_message(
                session, 'ai', analysis_response,
                {'file_analysis': True, 'file_id': file_record.id}
            )
            
            file_record.processed = True
            file_record.processing_status = 'completed'
            await database_sync_to_async(file_record.save)()
            
            return {
                'success': True,
                'file_info': file_info,
                'processed_data': processed_file,
                'analysis': analysis_response,
                'file_id': file_record.id
            }
            
        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @database_sync_to_async
    def _create_uploaded_file(self, session, file_info):
        return UploadedFile.objects.create(
            session=session,
            file_name=file_info['filename'],
            file_type=file_info['file_type'],
            file_path=file_info['file_path'],
            file_size=file_info['file_size']
        )

    async def process_folder_path(self, session_id: str, folder_path: str) -> Dict:
        """Process folder path"""
        try:
            session = await self._get_or_create_session(session_id)
            
            # Process folder
            folder_info = self.file_service.process_folder_path(folder_path)
            if not folder_info['success']:
                return folder_info
            
            # Create summary for AI
            summary = f"""Folder Analysis: {folder_path}
Total files: {folder_info['total_files']}
Supported files: {folder_info['supported_files']}
Supported file types: {', '.join(folder_info['supported_extensions'])}

Files found:"""
            
            for file_info in folder_info['files'][:10]:  # Limit to first 10
                summary += f"\n- {file_info['name']} ({file_info['extension']}) - {file_info['size']} bytes"
            
            if folder_info['total_files'] > 10:
                summary += f"\n... and {folder_info['total_files'] - 10} more files"
            
            # Get AI response
            # Streaming AI response
            ai_chunks = []
            async for chunk in self.llama_service.generate_streaming_response(
                f"Please analyze this folder structure and suggest how I can help with the data:\n{summary}"):
                ai_chunks.append(chunk)
            ai_response = ''.join(ai_chunks)
            # Save messages
            await self._create_message(
                session, 'user', f"Folder path: {folder_path}", folder_info
            )
            await self._create_message(
                session, 'ai', ai_response, {'folder_analysis': True}
            )
            
            return {
                'success': True,
                'folder_info': folder_info,
                'summary': summary,
                'ai_response': ai_response
            }
            
        except Exception as e:
            logger.error(f"Error processing folder path: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_database_connection(self, session_id: str, connection_config: Dict) -> Dict:
        """Process database connection request"""
        try:
            # Test connection
            is_valid, message = self.database_service.test_connection(connection_config)
            
            if not is_valid:
                return {
                    'success': False,
                    'error': f'Database connection failed: {message}'
                }
            
            # Create connection
            connection_id = self.database_service.create_connection(connection_config)
            
            # Get schema information
            schema = self.database_service.get_table_schema(connection_id)
            
            session = await self._get_or_create_session(session_id)
            
            # Save connection info
            await self._create_message(
                session, 'system', f"Connected to database: {connection_config['server']}/{connection_config['database']}",
                {'connection_id': connection_id, 'schema': schema}
            )
            
            # Generate schema summary for AI
            schema_summary = self._format_schema_summary(schema)
            # Streaming AI response
            ai_chunks = []
            async for chunk in self.llama_service.generate_streaming_response(
                f"I've connected to a database with the following schema:\n{schema_summary}\n\nHow can I help you query this data?"):
                ai_chunks.append(chunk)
            ai_response = ''.join(ai_chunks)
            await self._create_message(
                session, 'ai', ai_response,
                {'database_connection': True, 'connection_id': connection_id}
            )
            
            return {
                'success': True,
                'connection_id': connection_id,
                'schema': schema,
                'ai_response': ai_response
            }
            
        except Exception as e:
            logger.error(f"Error processing database connection: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @database_sync_to_async
    def _get_or_create_session(self, session_id: str) -> ChatSession:
        """Get existing session or create new one"""
        session, created = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={'created_at': timezone.now()}
        )
        return session
    
    @database_sync_to_async
    def _get_conversation_context(self, session: ChatSession, limit: int = 10) -> List[Dict]:
        """Get recent conversation context"""
        messages = session.messages.order_by('-timestamp')[:limit]
        context = []
        
        for message in reversed(messages):
            context.append({
                'type': message.message_type,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'metadata': message.get_metadata()
            })
        
        return context
    
    def _analyze_intent(self, message: str, metadata: Optional[Dict] = None) -> Dict:
        """Analyze message intent"""
        message_lower = message.lower()
        
        # Database-related keywords
        db_keywords = ['query', 'sql', 'select', 'table', 'database', 'data from']
        if any(keyword in message_lower for keyword in db_keywords):
            return {'type': 'database_query', 'confidence': 0.8}
        
        # File analysis keywords - expanded to catch more file-related questions
        file_keywords = [
            'analyze', 'file', 'csv', 'excel', 'data analysis',
            'row', 'column', 'field', 'how many', 'what is', 'show me',
            'first', 'last', 'count', 'rows', 'columns', 'data'
        ]
        if any(keyword in message_lower for keyword in file_keywords):
            return {'type': 'file_analysis', 'confidence': 0.7}
        
        return {'type': 'general_chat', 'confidence': 1.0}
    
    async def _process_database_query(self, session: ChatSession, message: str, 
                              context: List[Dict], intent: Dict) -> Dict:
        """Process database-related query"""
        # Find active database connection in context
        connection_id = None
        schema = None
        
        context = await self._get_conversation_context(session)
        for msg in reversed(context):
            if msg.get('metadata', {}).get('connection_id'):
                connection_id = msg['metadata']['connection_id']
                schema = msg['metadata'].get('schema')
                break
        
        if not connection_id:
            return {
                'content': "I don't see an active database connection. Please connect to a database first.",
                'metadata': {'requires_connection': True}
            }
        
        # Check if this is a direct SQL query or natural language
        if message.strip().upper().startswith('SELECT'):
            # Direct SQL query
            result = self.database_service.execute_query(connection_id, message, session.session_id)
            
            if result['success']:
                explanation = await self.llama_service.explain_query_results(
                    message, result['data']
                )
                response_content = f"Query executed successfully!\n\n{explanation}\n\nRows returned: {result['row_count']}\nExecution time: {result['execution_time']:.3f}s"
            else:
                response_content = f"Query failed: {result['error']}"
                
        else:
            # Natural language to SQL
            if schema:
                generated_query = await self.llama_service.generate_sql_query(message, schema)
                response_content = f"Based on your request, here's the SQL query I generated:\n\n```sql\n{generated_query}\n```\n\nWould you like me to execute this query?"
            else:
                response_content = "I need database schema information to help with queries. Please reconnect to the database."
        
        return {
            'content': response_content,
            'metadata': {'database_query': True, 'connection_id': connection_id}
        }
    
    async def _process_file_analysis(self, session: ChatSession, message: str, 
                             context: List[Dict], intent: Dict) -> Dict:
        """Process file analysis request"""
        # Use the file-related message processing logic
        file_result = await self._process_file_related_message(message)
        return {
            'content': file_result['response'],
            'metadata': {'file_analysis': True, **file_result.get('metadata', {})}
        }
    
    async def _process_message_with_attachments(self, session: ChatSession, message: str, 
                                              attached_files: List[Dict], context: List[Dict]) -> Dict:
        """
        Process message with attached files using enhanced LLM service
        
        Args:
            session: Chat session
            message: User message
            attached_files: List of attached file information
            context: Conversation context
            
        Returns:
            Response with file analysis and LLM answer
        """
        try:
            logger.info(f"Processing message with {len(attached_files)} attached files")
            
            # Use enhanced LLM service to process question with files
            result = await self.enhanced_llm_service.process_question_with_files(
                message, attached_files
            )
            
            if not result['success']:
                return {
                    'content': result['response'],
                    'metadata': {
                        'chat_type': 'file_analysis',
                        'error': True,
                        'attached_files': len(attached_files)
                    }
                }
            
            # Return successful response
            return {
                'content': result['response'],
                'metadata': {
                    'chat_type': 'file_analysis',
                    'attached_files': len(attached_files),
                    'data_found': result['metadata']['data_found'],
                    'files_analyzed': result['metadata']['files_analyzed'],
                    'search_keywords': result['metadata']['search_keywords']
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message with attachments: {e}")
            return {
                'content': f"Sorry, I encountered an error processing your question with the attached files: {str(e)}",
                'metadata': {
                    'chat_type': 'file_analysis',
                    'error': True,
                    'attached_files': len(attached_files)
                }
            }
    
    async def _process_general_chat(self, session: ChatSession, message: str, 
                            context: List[Dict]) -> Dict:
        """Process general chat message"""
        try:
            # Check if message is file-related
            if any(keyword in message.lower() for keyword in ['file', 'upload', 'csv', 'data', 'row', 'column', 'what\'s in', 'show me', 'question about']):
                # Handle file-related messages
                file_result = await self._process_file_related_message(message)
                return {
                    'content': file_result['response'],
                    'metadata': {'chat_type': 'file_analysis', **file_result.get('metadata', {})}
                }
            
            # Streaming AI response
            response_chunks = []
            async for chunk in self.llama_service.generate_streaming_response(message, context):
                response_chunks.append(chunk)
            response = ''.join(response_chunks)
            
            # Check if the response indicates an error
            if response.startswith("I'm currently unable to connect to my AI service"):
                return {
                    'content': response + "\n\nIn the meantime, I can help you with:\n• File uploads and analysis\n• Database connections and queries\n• Basic data processing tasks\n\nWould you like to try uploading a file or connecting to a database?",
                    'metadata': {'chat_type': 'general', 'ai_service_unavailable': True}
                }
            
            return {
                'content': response,
                'metadata': {'chat_type': 'general'}
            }
        except Exception as e:
            logger.error(f"Error in general chat processing: {e}")
            # Provide a helpful fallback response
            fallback_response = self._get_fallback_response(message)
            return {
                'content': fallback_response,
                'metadata': {'chat_type': 'general', 'fallback': True}
            }
    
    def _get_fallback_response(self, message: str) -> str:
        """Get a fallback response when AI service is unavailable"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! I'm your AI data assistant. I'm currently having trouble connecting to my AI service, but I can still help you with:\n\n• **File Uploads**: Upload CSV, Excel, or text files for analysis\n• **Database Connections**: Connect to SQL Server, PostgreSQL, or MySQL databases\n• **Data Queries**: Execute SQL queries and get results\n• **File Processing**: Process files in folders\n\nWould you like to try any of these features?"
        
        elif any(word in message_lower for word in ['help', 'what can you do']):
            return "I'm an AI data assistant that can help you with:\n\n📁 **File Management**\n• Upload and analyze CSV, Excel, text, and JSON files\n• Process entire folders of data files\n• Extract insights from your data\n\n🗄️ **Database Operations**\n• Connect to various databases (SQL Server, PostgreSQL, MySQL)\n• Execute SQL queries\n• Analyze database schemas\n\n💬 **Data Analysis**\n• Generate insights from your data\n• Create visualizations (when AI service is available)\n• Answer questions about your datasets\n\nTry uploading a file or connecting to a database to get started!"
        
        elif any(word in message_lower for word in ['upload', 'file', 'csv', 'excel']):
            return "Great! To upload a file:\n\n1. **Drag and drop** a file into the upload area, or\n2. **Click** the upload area to select a file\n\nSupported formats: CSV, Excel (.xlsx, .xls), Text files, JSON, PDF\n\nYou can also ask a specific question about your file in the optional question field!"
        
        elif any(word in message_lower for word in ['database', 'sql', 'query']):
            return "To connect to a database:\n\n1. Click the **'Connect to Database'** button\n2. Select your database type (SQL Server, PostgreSQL, MySQL)\n3. Enter your connection details\n4. Click **'Connect'**\n\nOnce connected, you can ask me to write SQL queries or execute them directly!"
        
        else:
            return "I understand you said: '" + message + "'\n\nI'm currently having trouble connecting to my AI service, but I can still help you with data-related tasks. Would you like to:\n\n• Upload a file for analysis\n• Connect to a database\n• Learn about my capabilities\n\nJust let me know what you'd like to do!"
    
    def _format_schema_summary(self, schema: Dict) -> str:
        """Format database schema for display"""
        if not schema:
            return "No schema information available"
        
        summary = "Database Tables:\n"
        for table_name, columns in schema.items():
            summary += f"\n{table_name}:\n"
            for column, data_type in columns.items():
                summary += f"  - {column} ({data_type})\n"
        
        return summary
    
    def _generate_fallback_analysis(self, processed_file: Dict, file_info: Dict, user_question: str = "") -> str:
        """Generate fallback analysis when AI service is unavailable"""
        file_type = file_info['file_type']
        filename = file_info['filename']
        
        if file_type == 'csv':
            analysis = processed_file.get('analysis', {})
            rows = analysis.get('rows', 0)
            columns = analysis.get('columns', 0)
            column_names = analysis.get('column_names', [])
            
            response = f"📊 **File Analysis: {filename}**\n\n"
            response += f"**File Type:** CSV\n"
            response += f"**Rows:** {rows:,}\n"
            response += f"**Columns:** {columns}\n"
            response += f"**Column Names:** {', '.join(column_names[:5])}"
            if len(column_names) > 5:
                response += f" and {len(column_names) - 5} more"
            response += "\n\n"
            
            if user_question:
                response += f"**Your Question:** {user_question}\n\n"
                response += "I'm currently unable to provide AI-powered analysis, but I can help you with:\n"
                response += "• Basic statistics and data overview\n"
                response += "• Column information and data types\n"
                response += "• Sample data from your file\n\n"
                response += "Try asking specific questions about your data, and I'll do my best to help!"
            else:
                response += "**Data Overview:**\n"
                response += "• The file contains structured data with multiple columns\n"
                response += "• You can ask questions about specific columns or data patterns\n"
                response += "• I can help you understand the data structure and content\n\n"
                response += "**Sample Data:**\n"
                sample_data = processed_file.get('data', [])
                if sample_data:
                    response += "First few rows:\n"
                    for i, row in enumerate(sample_data[:3]):
                        response += f"Row {i+1}: {str(row)[:100]}...\n"
        
        else:
            response = f"📁 **File Uploaded: {filename}**\n\n"
            response += f"**File Type:** {file_type.upper()}\n"
            response += f"**File Size:** {file_info['file_size']:,} bytes\n\n"
            response += "The file has been successfully uploaded and processed.\n"
            if user_question:
                response += f"**Your Question:** {user_question}\n\n"
            response += "I'm currently unable to provide AI-powered analysis, but the file is ready for further processing."
        
        return response
    
    async def _process_file_question(self, message: str, metadata: Dict) -> Dict:
        """Process file-related question"""
        try:
            file_id = metadata.get('file_id')
            if not file_id:
                return {
                    'response': 'No file specified for analysis. Please select a file first.',
                    'metadata': {}
                }
            
            # Get file information
            from chat.models import UploadedFile
            try:
                file_obj = UploadedFile.objects.get(id=file_id)
            except UploadedFile.DoesNotExist:
                return {
                    'response': 'File not found. Please upload the file again.',
                    'metadata': {}
                }
            
            # Process file question
            file_summary = self.file_service.get_file_summary(file_obj.file_path)
            
            # Get AI analysis
            analysis_chunks = []
            async for chunk in self.llama_service.analyze_file_content(
                file_summary, file_obj.file_type, message):
                analysis_chunks.append(chunk)
            
            response = ''.join(analysis_chunks)
            
            return {
                'response': response,
                'metadata': {
                    'file_id': file_id,
                    'file_name': file_obj.file_name,
                    'file_type': file_obj.file_type
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing file question: {e}")
            return {
                'response': f"Sorry, I couldn't analyze the file: {str(e)}",
                'metadata': {}
            }
    
    async def _process_file_related_message(self, message: str) -> Dict:
        """Process messages that might be about files"""
        try:
            # Check if user is asking about uploaded files
            from chat.models import ChatSession, UploadedFile
            
            logger.info(f"Looking for session: {self.session_id}")
            session = await self._get_session_async(self.session_id)
            if not session:
                logger.warning(f"Session not found: {self.session_id}")
                return {
                    'response': 'No active session found. Please refresh the page.',
                    'metadata': {}
                }
            logger.info(f"Session found: {session.session_id}")
            
            files = await self._get_session_files_async(session)
            logger.info(f"Found {len(files)} files for session {self.session_id}")
            
            if not files:
                logger.warning(f"No files found for session {self.session_id}")
                return {
                    'response': 'I don\'t see any uploaded files to analyze. Please upload a file first.',
                    'metadata': {}
                }
            
            # Check if message contains specific file references
            if "row" in message.lower() and any(char.isdigit() for char in message):
                # Handle row-specific questions
                return await self._handle_row_question(message, files[0])
            elif "column" in message.lower() or "field" in message.lower():
                # Handle column questions
                return await self._handle_column_question(message, files[0])
            elif "how many" in message.lower() and "row" in message.lower():
                # Handle count questions
                return await self._handle_count_question(message, files[0])
            else:
                # General file question
                return await self._handle_general_file_question(message, files[0])
                
        except Exception as e:
            logger.error(f"Error processing file-related message: {e}")
            return {
                'response': f"Sorry, I couldn't process your file-related question: {str(e)}",
                'metadata': {}
            }
    
    async def _handle_row_question(self, message: str, file_obj) -> Dict:
        """Handle questions about specific rows"""
        try:
            import re
            row_match = re.search(r'(\d+)', message)
            if not row_match:
                return {
                    'response': 'Please specify which row number you\'d like to see.',
                    'metadata': {}
                }
            
            row_num = int(row_match.group(1)) - 1  # Convert to 0-based index
            
            # Get file data
            from django.conf import settings
            full_file_path = f"{settings.MEDIA_ROOT}/{file_obj.file_path}"
            processed_file = self.file_service.process_file(full_file_path, file_obj.file_type)
            if not processed_file['success']:
                return {
                    'response': f"Sorry, I couldn't process the file {file_obj.file_name}.",
                    'metadata': {}
                }
            
            full_data = processed_file.get('full_data', [])
            if 0 <= row_num < len(full_data):
                row_data = full_data[row_num]
                response = f"**Row {row_num + 1} of {file_obj.file_name}:**\n\n"
                for key, value in row_data.items():
                    response += f"• **{key}:** {value}\n"
                return {
                    'response': response,
                    'metadata': {'file_name': file_obj.file_name, 'row': row_num + 1}
                }
            else:
                return {
                    'response': f"Row {row_num + 1} doesn't exist. The file has {len(full_data)} rows.",
                    'metadata': {'file_name': file_obj.file_name, 'total_rows': len(full_data)}
                }
                
        except Exception as e:
            logger.error(f"Error handling row question: {e}")
            return {
                'response': f"Sorry, I couldn't answer your row question: {str(e)}",
                'metadata': {}
            }
    
    async def _handle_column_question(self, message: str, file_obj) -> Dict:
        """Handle questions about columns"""
        try:
            from django.conf import settings
            full_file_path = f"{settings.MEDIA_ROOT}/{file_obj.file_path}"
            processed_file = self.file_service.process_file(full_file_path, file_obj.file_type)
            if not processed_file['success']:
                return {
                    'response': f"Sorry, I couldn't process the file {file_obj.file_name}.",
                    'metadata': {}
                }
            
            analysis = processed_file.get('analysis', {})
            columns = analysis.get('column_names', [])
            
            response = f"**Columns in {file_obj.file_name}:**\n\n"
            for i, col in enumerate(columns, 1):
                response += f"{i}. **{col}**\n"
            
            return {
                'response': response,
                'metadata': {'file_name': file_obj.file_name, 'column_count': len(columns)}
            }
            
        except Exception as e:
            logger.error(f"Error handling column question: {e}")
            return {
                'response': f"Sorry, I couldn't answer your column question: {str(e)}",
                'metadata': {},
            }
    
    async def _handle_count_question(self, message: str, file_obj) -> Dict:
        """Handle questions about counts"""
        try:
            from django.conf import settings
            full_file_path = f"{settings.MEDIA_ROOT}/{file_obj.file_path}"
            processed_file = self.file_service.process_file(full_file_path, file_obj.file_type)
            if not processed_file['success']:
                return {
                    'response': f"Sorry, I couldn't process the file {file_obj.file_name}.",
                    'metadata': {}
                }
            
            analysis = processed_file.get('analysis', {})
            rows = analysis.get('rows', 0)
            columns = analysis.get('columns', 0)
            
            response = f"**File Statistics for {file_obj.file_name}:**\n\n"
            response += f"• **Rows:** {rows:,}\n"
            response += f"• **Columns:** {columns}\n"
            response += f"• **Total cells:** {rows * columns:,}\n"
            
            return {
                'response': response,
                'metadata': {'file_name': file_obj.file_name, 'rows': rows, 'columns': columns}
            }
            
        except Exception as e:
            logger.error(f"Error handling count question: {e}")
            return {
                'response': f"Sorry, I couldn't answer your count question: {str(e)}",
                'metadata': {}
            }
    
    async def _handle_general_file_question(self, message: str, file_obj) -> Dict:
        """Handle general questions about files"""
        try:
            # Use AI service for complex questions
            from django.conf import settings
            full_file_path = f"{settings.MEDIA_ROOT}/{file_obj.file_path}"
            file_summary = self.file_service.get_file_summary(full_file_path)
            
            try:
                analysis_chunks = []
                async for chunk in self.llama_service.analyze_file_content(
                    file_summary, file_obj.file_type, message):
                    analysis_chunks.append(chunk)
                response = ''.join(analysis_chunks)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                # Fallback to basic analysis
                processed_file = self.file_service.process_file(full_file_path, file_obj.file_type)
                response = self._generate_fallback_analysis(processed_file, {
                    'filename': file_obj.file_name,
                    'file_type': file_obj.file_type,
                    'file_size': file_obj.file_size
                }, message)
            
            return {
                'response': response,
                'metadata': {'file_name': file_obj.file_name, 'file_type': file_obj.file_type}
            }
            
        except Exception as e:
            logger.error(f"Error handling general file question: {e}")
            return {
                'response': f"Sorry, I couldn't answer your question about {file_obj.file_name}: {str(e)}",
                'metadata': {}
            }
    
    @database_sync_to_async
    def _get_session_async(self, session_id: str):
        """Get session asynchronously"""
        from chat.models import ChatSession
        try:
            session = ChatSession.objects.get(session_id=session_id)
            logger.info(f"Found existing session: {session_id}")
            return session
        except ChatSession.DoesNotExist:
            # Create session if it doesn't exist
            logger.info(f"Creating new session: {session_id}")
            session = ChatSession.objects.create(session_id=session_id)
            return session
    
    @database_sync_to_async
    def _get_session_files_async(self, session):
        """Get session files asynchronously"""
        from chat.models import UploadedFile
        return list(UploadedFile.objects.filter(session=session).order_by('-upload_timestamp'))
    
    @database_sync_to_async
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat session history"""
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.order_by('timestamp')[:limit]
            
            history = []
            for message in messages:
                history.append({
                    'id': message.id,
                    'type': message.message_type,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'metadata': message.get_metadata()
                })
            
            return history
            
        except ChatSession.DoesNotExist:
            return []
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return []