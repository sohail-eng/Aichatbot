#!/usr/bin/env python3
"""
Minimal file upload test - just save the file, no processing
"""
import os
import sys
import requests
import json
from pathlib import Path

def test_minimal_upload():
    """Test just file saving, no processing"""
    file_path = "/home/azeem/Downloads/Skincare_DB_Schema_Guide.csv"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🧪 Testing minimal file upload for: {file_path}")
    
    # First, get a session by visiting the chat page
    session = requests.Session()
    
    try:
        # Get the chat page to create a session
        print("🌐 Loading chat page...")
        response = session.get('http://localhost:8000/', timeout=10)
        print(f"✅ Chat page loaded: {response.status_code}")
        
        # Test a very small file first
        small_content = b"test,data\n1,2\n3,4"
        files = {'file': ('test.csv', small_content, 'text/csv')}
        data = {'question': ''}
        
        print("📤 Uploading small test file...")
        response = session.post('http://localhost:8000/upload/', files=files, data=data, timeout=10)
        
        print(f"📥 Upload response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Small file upload successful!")
                print(f"📊 Result: {result}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"📄 Response text: {response.text[:500]}...")
        else:
            print(f"❌ Small file upload failed with status: {response.status_code}")
            print(f"📄 Response text: {response.text}")
            
        # Now test the actual file
        print("\n📤 Uploading actual file...")
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            data = {'question': ''}
            
            response = session.post('http://localhost:8000/upload/', files=files, data=data, timeout=30)
            
            print(f"📥 Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ File upload successful!")
                    print(f"📊 Success: {result.get('success', False)}")
                    
                    if result.get('success'):
                        print(f"📁 File info: {result.get('file_info', {})}")
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
    print("🧪 MINIMAL FILE UPLOAD TEST")
    print("=" * 60)
    test_minimal_upload()
    print("=" * 60)
    print("✅ Test completed")
    print("=" * 60)
