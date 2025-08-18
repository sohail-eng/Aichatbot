#!/usr/bin/env python3
"""
Simple file upload test that bypasses AI service
"""
import os
import sys
import requests
import json
from pathlib import Path

def test_simple_upload():
    """Test file upload without AI processing"""
    file_path = "/home/azeem/Downloads/Skincare_DB_Schema_Guide.csv"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🧪 Testing simple file upload for: {file_path}")
    
    # First, get a session by visiting the chat page
    session = requests.Session()
    
    try:
        # Get the chat page to create a session
        print("🌐 Loading chat page...")
        response = session.get('http://localhost:8000/', timeout=10)
        print(f"✅ Chat page loaded: {response.status_code}")
        
        # Upload the file with a simple question
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            data = {'question': ''}  # Empty question to minimize processing
            
            print("📤 Uploading file (timeout: 30s)...")
            response = session.post('http://localhost:8000/upload/', files=files, data=data, timeout=30)
            
            print(f"📥 Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Upload successful!")
                    print(f"📊 Result keys: {list(result.keys())}")
                    print(f"📊 Success: {result.get('success', False)}")
                    
                    if result.get('success'):
                        print(f"📁 File info: {result.get('file_info', {})}")
                        analysis = result.get('analysis', '')
                        print(f"🤖 Analysis length: {len(analysis)}")
                        print(f"🤖 Analysis preview: {analysis[:200]}...")
                    else:
                        print(f"❌ Error: {result.get('error', 'Unknown error')}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"📄 Response text: {response.text[:500]}...")
            else:
                print(f"❌ Upload failed with status: {response.status_code}")
                print(f"📄 Response text: {response.text}")
                
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The server is taking too long to respond.")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SIMPLE FILE UPLOAD TEST (No AI)")
    print("=" * 60)
    test_simple_upload()
    print("=" * 60)
    print("✅ Test completed")
    print("=" * 60)
