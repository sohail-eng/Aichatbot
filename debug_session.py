#!/usr/bin/env python3
"""
Debug session and file retrieval
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')
django.setup()

from chat.models import ChatSession, UploadedFile
from ai_services.chat_processor import ChatProcessor
import asyncio

async def debug_session():
    """Debug session and file retrieval"""
    session_id = "bb0d88fc-8e09-4a8a-9d19-f46bca6b2408"
    
    print(f"🔍 Debugging session: {session_id}")
    
    # Test chat processor first
    print("\n🤖 Testing ChatProcessor...")
    chat_processor = ChatProcessor()
    chat_processor.session_id = session_id
    
    # Test session retrieval
    session_async = await chat_processor._get_session_async(session_id)
    if session_async:
        print(f"✅ ChatProcessor found session: {session_async.session_id}")
        print(f"   Created: {session_async.created_at}")
        print(f"   Updated: {session_async.updated_at}")
    else:
        print(f"❌ ChatProcessor could not find session")
        return
    
    # Test file retrieval
    files_async = await chat_processor._get_session_files_async(session_async)
    print(f"📁 ChatProcessor found {len(files_async)} files")
    
    for file in files_async:
        print(f"   📄 {file.file_name} (ID: {file.id})")
        print(f"      Path: {file.file_path}")
        print(f"      Type: {file.file_type}")
        print(f"      Size: {file.file_size}")
        print(f"      Uploaded: {file.upload_timestamp}")
    
    # Test file-related message processing
    print("\n💬 Testing file message processing...")
    result = await chat_processor._process_file_related_message("what is the 45th row?")
    print(f"Result: {result}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 SESSION DEBUG")
    print("=" * 60)
    asyncio.run(debug_session())
    print("=" * 60)
    print("✅ Debug completed")
    print("=" * 60)
