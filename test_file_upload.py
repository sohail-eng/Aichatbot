#!/usr/bin/env python3
"""
Test script to debug file upload serialization issues
"""
import os
import sys
import json
import logging
import django
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')
django.setup()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_upload.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from ai_services.file_service import FileService
from ai_services.chat_processor import ChatProcessor
from chat.models import ChatSession, UploadedFile
from django.core.files.uploadedfile import SimpleUploadedFile

def test_file_processing():
    """Test file processing directly"""
    file_path = "/home/azeem/Downloads/Skincare_DB_Schema_Guide.csv"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    logger.info(f"Testing file processing for: {file_path}")
    
    # Test FileService directly
    file_service = FileService()
    logger.info("Created FileService instance")
    
    try:
        result = file_service.process_file(file_path, 'csv')
        logger.info(f"File processing result type: {type(result)}")
        logger.info(f"File processing success: {result.get('success', False)}")
        
        if result.get('success'):
            logger.info("File processed successfully, testing JSON serialization...")
            
            # Test JSON serialization
            try:
                json_str = json.dumps(result, indent=2)
                logger.info("✅ JSON serialization successful")
                logger.info(f"JSON length: {len(json_str)} characters")
                
                # Save to file for inspection
                with open('test_result.json', 'w') as f:
                    f.write(json_str)
                logger.info("✅ Result saved to test_result.json")
                
            except Exception as e:
                logger.error(f"❌ JSON serialization failed: {e}")
                logger.error(f"Result type: {type(result)}")
                
                # Debug the problematic object
                debug_json_serialization(result)
                
        else:
            logger.error(f"❌ File processing failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Exception during file processing: {e}")
        import traceback
        logger.error(traceback.format_exc())

def debug_json_serialization(obj, path=""):
    """Recursively debug JSON serialization issues"""
    try:
        json.dumps(obj)
        logger.info(f"✅ Object at {path} is JSON serializable")
    except Exception as e:
        logger.error(f"❌ Object at {path} is NOT JSON serializable: {e}")
        logger.error(f"   Type: {type(obj)}")
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                debug_json_serialization(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                debug_json_serialization(item, f"{path}[{i}]")
        else:
            logger.error(f"   Value: {str(obj)[:200]}...")

def test_chat_processor():
    """Test ChatProcessor file upload"""
    file_path = "/home/azeem/Downloads/Skincare_DB_Schema_Guide.csv"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    logger.info("Testing ChatProcessor file upload...")
    
    # Create a test session
    session_id = "test-session-123"
    session, created = ChatSession.objects.get_or_create(
        session_id=session_id,
        defaults={'user': None}
    )
    logger.info(f"Created test session: {session_id}")
    
    # Create a mock uploaded file
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    uploaded_file = SimpleUploadedFile(
        name=os.path.basename(file_path),
        content=file_content,
        content_type='text/csv'
    )
    
    logger.info(f"Created mock uploaded file: {uploaded_file.name}")
    
    # Test ChatProcessor
    chat_processor = ChatProcessor()
    logger.info("Created ChatProcessor instance")
    
    try:
        import asyncio
        result = asyncio.run(chat_processor.process_file_upload(session_id, uploaded_file, "Test question"))
        logger.info(f"ChatProcessor result type: {type(result)}")
        logger.info(f"ChatProcessor success: {result.get('success', False)}")
        
        if result.get('success'):
            logger.info("✅ ChatProcessor processing successful")
            
            # Test JSON serialization
            try:
                json.dumps(result)
                logger.info("✅ ChatProcessor result is JSON serializable")
            except Exception as e:
                logger.error(f"❌ ChatProcessor result JSON serialization failed: {e}")
                debug_json_serialization(result)
        else:
            logger.error(f"❌ ChatProcessor processing failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Exception during ChatProcessor processing: {e}")
        import traceback
        logger.error(traceback.format_exc())

def test_view_serialization():
    """Test the view's JSON serialization helper"""
    from chat.views import FileUploadView
    
    view = FileUploadView()
    
    # Test with problematic data
    test_data = {
        'success': True,
        'file_info': {
            'filename': 'test.csv',
            'file_type': 'csv',
            'file_size': 1024
        },
        'analysis': 'Test analysis',
        'data': [{'col1': 'value1', 'col2': 'value2'}]
    }
    
    logger.info("Testing view's JSON serialization helper...")
    
    try:
        serialized = view._ensure_json_serializable(test_data)
        json.dumps(serialized)
        logger.info("✅ View serialization helper works with test data")
    except Exception as e:
        logger.error(f"❌ View serialization helper failed: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("STARTING FILE UPLOAD DEBUG TESTS")
    logger.info("=" * 60)
    
    # Test 1: Direct file processing
    logger.info("\n" + "=" * 40)
    logger.info("TEST 1: Direct FileService Processing")
    logger.info("=" * 40)
    test_file_processing()
    
    # Test 2: View serialization helper
    logger.info("\n" + "=" * 40)
    logger.info("TEST 2: View Serialization Helper")
    logger.info("=" * 40)
    test_view_serialization()
    
    # Test 3: ChatProcessor integration
    logger.info("\n" + "=" * 40)
    logger.info("TEST 3: ChatProcessor Integration")
    logger.info("=" * 40)
    test_chat_processor()
    
    logger.info("\n" + "=" * 60)
    logger.info("DEBUG TESTS COMPLETED")
    logger.info("Check test_upload.log for detailed results")
    logger.info("=" * 60)
