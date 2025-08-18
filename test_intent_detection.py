#!/usr/bin/env python3
"""
Test intent detection for file-related questions
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')
django.setup()

from ai_services.chat_processor import ChatProcessor
import asyncio

async def test_intent_detection():
    """Test intent detection for various messages"""
    chat_processor = ChatProcessor()
    
    test_messages = [
        "what is the 45th row?",
        "show me the columns",
        "how many rows are there?",
        "what's in the file?",
        "hello there",
        "connect to database",
        "SELECT * FROM users"
    ]
    
    print("🧪 Testing Intent Detection")
    print("=" * 50)
    
    for message in test_messages:
        intent = chat_processor._analyze_intent(message)
        print(f"Message: '{message}'")
        print(f"Intent: {intent['type']} (confidence: {intent['confidence']})")
        print("-" * 30)
    
    # Test file processing
    print("\n💬 Testing File Message Processing")
    print("=" * 50)
    
    chat_processor.session_id = "bb0d88fc-8e09-4a8a-9d19-f46bca6b2408"
    
    test_file_questions = [
        "what is the 45th row?",
        "show me the columns",
        "how many rows are there?"
    ]
    
    for question in test_file_questions:
        print(f"\nQuestion: '{question}'")
        try:
            result = await chat_processor._process_file_related_message(question)
            print(f"Response: {result['response'][:100]}...")
            print(f"Success: ✅")
        except Exception as e:
            print(f"Error: {e}")
            print(f"Success: ❌")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 INTENT DETECTION TEST")
    print("=" * 60)
    asyncio.run(test_intent_detection())
    print("=" * 60)
    print("✅ Test completed")
    print("=" * 60)
