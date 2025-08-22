# chat/views.py
import json
import uuid
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import View
from ai_services.chat_processor import ChatProcessor

logger = logging.getLogger(__name__)

class ChatView(View):
    def get(self, request):
        """Render chat interface"""
        session_id = request.session.get('chat_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['chat_session_id'] = session_id
        
        context = {
            'session_id': session_id,
            'websocket_url': f'ws://localhost:8000/ws/chat/{session_id}/',
            'user': request.user,
        }
        return render(request, 'chat/chat_room.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class FileUploadView(View):
    def post(self, request):
        """Handle file upload"""
        try:
            logger.info("File upload request received")
            session_id = request.session.get('chat_session_id')
            if not session_id:
                logger.error("No session found")
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            if 'file' not in request.FILES:
                logger.error("No file provided in request")
                return JsonResponse({'success': False, 'error': 'No file provided'})
            
            uploaded_file = request.FILES['file']
            
            # Validate file
            if uploaded_file.size == 0:
                return JsonResponse({'success': False, 'error': 'File is empty'})
            
            if uploaded_file.size > 50 * 1024 * 1024:  # 50MB limit
                return JsonResponse({'success': False, 'error': 'File too large (max 50MB)'})
            
            # Check file extension
            import os
            allowed_extensions = ['.csv', '.xlsx', '.xls', '.txt', '.json', '.pdf']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            if file_extension not in allowed_extensions:
                return JsonResponse({'success': False, 'error': f'File type not supported. Allowed: {", ".join(allowed_extensions)}'})
            
            user_question = request.POST.get('question', '')
            logger.info(f"Processing file: {uploaded_file.name}, size: {uploaded_file.size}, question: {user_question}")
            
            # Use synchronous file processing for now
            logger.info("Using synchronous file processing...")
            result = self._process_file_sync(session_id, uploaded_file, user_question)
            logger.info(f"File processing completed, result type: {type(result)}")
            
            # Log success for debugging
            if result.get('success'):
                logger.info(f"File upload successful: {result.get('file_info', {}).get('filename', 'Unknown')}")
            else:
                logger.error(f"File upload failed: {result.get('error', 'Unknown error')}")
            
            # Ensure result is JSON serializable
            result = self._ensure_json_serializable(result)
            
            # Debug: Try to serialize to catch any remaining issues
            try:
                import json
                json.dumps(result)
            except Exception as e:
                print(f"JSON serialization error: {e}")
                print(f"Result type: {type(result)}")
                if isinstance(result, dict):
                    for key, value in result.items():
                        print(f"Key: {key}, Type: {type(value)}")
                return JsonResponse({'success': False, 'error': f'Serialization error: {str(e)}'})
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"File upload error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e)})
    
    def _ensure_json_serializable(self, obj):
        """Ensure object is JSON serializable"""
        if isinstance(obj, dict):
            return {key: self._ensure_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        elif hasattr(obj, 'dtype'):  # Handle numpy/pandas objects
            return str(obj)
        elif hasattr(obj, 'to_dict'):  # Handle pandas Series/DataFrame
            try:
                return obj.to_dict()
            except:
                return str(obj)
        else:
            # Convert any other objects to string
            return str(obj)
    
    def _process_file_sync(self, session_id: str, uploaded_file, user_question: str = ""):
        """Synchronous file processing without async operations"""
        try:
            logger.info("Starting synchronous file processing...")
            
            # Save file
            from ai_services.file_service import FileService
            file_service = FileService()
            file_info = file_service.save_uploaded_file(uploaded_file, session_id)
            
            if not file_info['success']:
                return {'success': False, 'error': file_info['error']}
            
            logger.info(f"File saved: {file_info['filename']}")
            
            # Process file
            processed_file = file_service.process_file(file_info['full_path'], file_info['file_type'])
            
            if not processed_file['success']:
                return {'success': False, 'error': processed_file['error']}
            
            logger.info("File processed successfully")
            
            # Generate fallback analysis (no AI service)
            from ai_services.chat_processor import ChatProcessor
            chat_processor = ChatProcessor()
            analysis_response = chat_processor._generate_fallback_analysis(processed_file, file_info, user_question)
            
            logger.info("Analysis generated")
            
            # Save to database
            from chat.models import ChatSession, UploadedFile
            session, created = ChatSession.objects.get_or_create(session_id=session_id)
            
            uploaded_file_record = UploadedFile.objects.create(
                session=session,
                file_name=file_info['filename'],
                file_type=file_info['file_type'],
                file_path=file_info['file_path'],
                file_size=file_info['file_size'],
                processed=True
            )
            
            logger.info("File record saved to database")
            
            return {
                'success': True,
                'file_info': {
                    'filename': file_info['filename'],
                    'file_type': file_info['file_type'],
                    'file_size': file_info['file_size']
                },
                'analysis': analysis_response,
                'data': processed_file.get('data', [])
            }
            
        except Exception as e:
            logger.error(f"Error in synchronous file processing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

@method_decorator(csrf_exempt, name='dispatch')
class FolderPathView(View):
    def post(self, request):
        """Handle folder path processing"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            data = json.loads(request.body)
            folder_path = data.get('folder_path', '')
            
            if not folder_path:
                return JsonResponse({'success': False, 'error': 'No folder path provided'})
            
            chat_processor = ChatProcessor()
            result = chat_processor.process_folder_path(session_id, folder_path)
            
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class DatabaseConnectionView(View):
    def post(self, request):
        """Handle database connection"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            data = json.loads(request.body)
            connection_config = {
                'type': data.get('type', 'mssql'),
                'server': data.get('server', ''),
                'database': data.get('database', ''),
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'port': data.get('port', 1433)
            }
            
            # Validate required fields
            required_fields = ['server', 'database', 'username', 'password']
            if not all(connection_config.get(field) for field in required_fields):
                return JsonResponse({'success': False, 'error': 'Missing required connection details'})
            
            chat_processor = ChatProcessor()
            result = chat_processor.process_database_connection(session_id, connection_config)
            
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class ChatHistoryView(View):
    def get(self, request):
        """Get chat session history"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            chat_processor = ChatProcessor()
            history = chat_processor.get_session_history(session_id)
            
            return JsonResponse({
                'success': True,
                'history': history,
                'session_id': session_id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class UploadedFilesView(View):
    def get(self, request):
        """Get uploaded files for current session"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            from chat.models import ChatSession, UploadedFile
            
            try:
                session = ChatSession.objects.get(session_id=session_id)
                files = UploadedFile.objects.filter(session=session).order_by('-upload_timestamp')
                
                file_list = []
                for file in files:
                    file_list.append({
                        'id': file.id,
                        'name': file.file_name,
                        'type': file.file_type,
                        'size': file.file_size,
                        'uploaded_at': file.upload_timestamp.isoformat(),
                        'processed': file.processed
                    })
                
                return JsonResponse({
                    'success': True,
                    'files': file_list
                })
                
            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'success': True,
                    'files': []
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def delete(self, request, file_id):
        """Delete uploaded file"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            from chat.models import ChatSession, UploadedFile
            from django.core.files.storage import default_storage
            import os
            
            try:
                session = ChatSession.objects.get(session_id=session_id)
                file_obj = UploadedFile.objects.get(id=file_id, session=session)
                
                # Delete the physical file
                if default_storage.exists(file_obj.file_path):
                    default_storage.delete(file_obj.file_path)
                
                # Delete the database record
                file_name = file_obj.file_name
                file_obj.delete()
                
                logger.info(f"File deleted: {file_name} (ID: {file_id})")
                
                return JsonResponse({
                    'success': True,
                    'message': f'File "{file_name}" deleted successfully'
                })
                
            except UploadedFile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'File not found'
                })
            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Session not found'
                })
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class ExecuteQueryView(View):
    def post(self, request):
        """Execute SQL query"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            data = json.loads(request.body)
            query = data.get('query', '')
            connection_id = data.get('connection_id', '')
            
            if not query or not connection_id:
                return JsonResponse({'success': False, 'error': 'Missing query or connection'})
            
            chat_processor = ChatProcessor()
            
            # Execute query through database service
            result = chat_processor.database_service.execute_query(
                connection_id, query, session_id
            )
            
            if result['success']:
                # Get AI explanation of results
                explanation = chat_processor.llama_service.explain_query_results(
                    query, result['data']
                )
                
                # Save query and response
                from chat.models import ChatSession, Message
                session_obj = ChatSession.objects.get(session_id=session_id)
                
                Message.objects.create(
                    session=session_obj,
                    message_type='db_query',
                    content=query,
                    metadata={'connection_id': connection_id}
                )
                
                Message.objects.create(
                    session=session_obj,
                    message_type='ai',
                    content=explanation,
                    metadata={'query_result': True, 'row_count': result['row_count']}
                )
                
                return JsonResponse({
                    'success': True,
                    'data': result['data'],
                    'explanation': explanation,
                    'row_count': result['row_count'],
                    'execution_time': result['execution_time']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class ProcessAttachmentsView(View):
    def post(self, request):
        """Process attached files for chat context"""
        try:
            session_id = request.session.get('chat_session_id')
            if not session_id:
                return JsonResponse({'success': False, 'error': 'No session found'})
            
            if 'files' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No files provided'})
            
            uploaded_files = request.FILES.getlist('files')
            results = []
            
            for uploaded_file in uploaded_files:
                # Validate file
                if uploaded_file.size == 0:
                    results.append({'success': False, 'filename': uploaded_file.name, 'error': 'File is empty'})
                    continue
                
                if uploaded_file.size > 50 * 1024 * 1024:  # 50MB limit
                    results.append({'success': False, 'filename': uploaded_file.name, 'error': 'File too large (max 50MB)'})
                    continue
                
                # Check file extension
                import os
                allowed_extensions = ['.csv', '.xlsx', '.xls', '.txt', '.json', '.pdf']
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                if file_extension not in allowed_extensions:
                    results.append({'success': False, 'filename': uploaded_file.name, 'error': f'File type not supported. Allowed: {", ".join(allowed_extensions)}'})
                    continue
                
                # Process file
                result = self._process_attachment_sync(session_id, uploaded_file)
                results.append(result)
            
            return JsonResponse({
                'success': True,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error processing attachments: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    def _process_attachment_sync(self, session_id: str, uploaded_file):
        """Synchronous attachment processing"""
        try:
            # Save file
            from ai_services.file_service import FileService
            file_service = FileService()
            file_info = file_service.save_uploaded_file(uploaded_file, session_id)
            
            if not file_info['success']:
                return {'success': False, 'filename': uploaded_file.name, 'error': file_info['error']}
            
            # Process file
            processed_file = file_service.process_file(file_info['full_path'], file_info['file_type'])
            
            if not processed_file['success']:
                return {'success': False, 'filename': uploaded_file.name, 'error': processed_file['error']}
            
            # Save to database
            from chat.models import ChatSession, UploadedFile
            session, created = ChatSession.objects.get_or_create(session_id=session_id)
            
            uploaded_file_record = UploadedFile.objects.create(
                session=session,
                file_name=file_info['filename'],
                file_type=file_info['file_type'],
                file_path=file_info['file_path'],
                file_size=file_info['file_size'],
                processed=True
            )
            
            return {
                'success': True,
                'filename': uploaded_file.name,
                'file_id': uploaded_file_record.id,
                'file_type': file_info['file_type'],
                'file_size': file_info['file_size'],
                'processed_data': processed_file.get('data', [])
            }
            
        except Exception as e:
            logger.error(f"Error in attachment processing: {e}")
            return {'success': False, 'filename': uploaded_file.name, 'error': str(e)}