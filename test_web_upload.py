#!/usr/bin/env python3
"""
Test web file upload via HTTP request
"""
import os
import sys
import requests
import json
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')

def test_web_upload():
    """Test file upload via web interface"""
    file_path = "/home/azeem/Downloads/Skincare_DB_Schema_Guide.csv"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🧪 Testing web file upload for: {file_path}")
    
    # First, get a session by visiting the chat page
    session = requests.Session()
    
    try:
        # Get the chat page to create a session
        response = session.get('http://localhost:8000/')
        print(f"✅ Chat page loaded: {response.status_code}")
        
        # Upload the file
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            data = {'question': 'What is this file about?'}
            
            print("📤 Uploading file...")
            response = session.post('http://localhost:8000/upload/', files=files, data=data, timeout=30)
            
            print(f"📥 Upload response status: {response.status_code}")
            print(f"📥 Upload response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Upload successful!")
                    print(f"📊 Result keys: {list(result.keys())}")
                    print(f"📊 Success: {result.get('success', False)}")
                    
                    if result.get('success'):
                        print(f"📁 File info: {result.get('file_info', {})}")
                        print(f"🤖 Analysis length: {len(result.get('analysis', ''))}")
                    else:
                        print(f"❌ Error: {result.get('error', 'Unknown error')}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"📄 Response text: {response.text[:500]}...")
            else:
                print(f"❌ Upload failed with status: {response.status_code}")
                print(f"📄 Response text: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 WEB FILE UPLOAD TEST")
    print("=" * 60)
    test_web_upload()
    print("=" * 60)
    print("✅ Test completed")
    print("=" * 60)
