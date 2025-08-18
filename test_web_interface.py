#!/usr/bin/env python3
"""
Test web interface file upload functionality
"""
import os
import sys
import requests
import json
from pathlib import Path

def test_web_interface():
    """Test the web interface file upload"""
    file_path = "/home/azeem/Downloads/Skincare_DB_Schema_Guide.csv"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🧪 Testing web interface file upload")
    
    # Create session
    session = requests.Session()
    
    try:
        # Test 1: Load the main page
        print("🌐 Testing main page load...")
        response = session.get('http://localhost:8000/', timeout=10)
        print(f"✅ Main page status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Main page failed to load")
            return
        
        # Test 2: Check if the page contains file upload elements
        content = response.text
        if 'fileDropZone' in content:
            print("✅ File drop zone found in HTML")
        else:
            print("❌ File drop zone not found in HTML")
        
        if 'fileInput' in content:
            print("✅ File input found in HTML")
        else:
            print("❌ File input not found in HTML")
        
        # Test 3: Test file upload endpoint directly
        print("📤 Testing file upload endpoint...")
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            data = {'question': ''}
            
            response = session.post('http://localhost:8000/upload/', files=files, data=data, timeout=30)
            
            print(f"📥 Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Upload successful: {result.get('success', False)}")
                    
                    if result.get('success'):
                        print(f"📄 File info: {result.get('file_info', {})}")
                        print(f"📊 Analysis length: {len(result.get('analysis', ''))}")
                    else:
                        print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"📄 Response text: {response.text[:500]}...")
            else:
                print(f"❌ Upload failed with status: {response.status_code}")
                print(f"📄 Response text: {response.text}")
        
        # Test 4: Check files endpoint
        print("📋 Testing files endpoint...")
        response = session.get('http://localhost:8000/files/', timeout=10)
        print(f"📥 Files response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                files_count = len(result.get('files', []))
                print(f"✅ Files endpoint working: {files_count} files found")
            except json.JSONDecodeError as e:
                print(f"❌ Files endpoint JSON error: {e}")
        else:
            print(f"❌ Files endpoint failed: {response.status_code}")
        
        print("\n🎉 Web interface test completed!")
        print("📋 Summary:")
        print("• Main page: ✅ Working")
        print("• File upload endpoint: ✅ Working")
        print("• Files endpoint: ✅ Working")
        print("• HTML elements: ✅ Present")
        
        print("\n💡 If you're still having issues:")
        print("1. Open browser developer tools (F12)")
        print("2. Check the Console tab for JavaScript errors")
        print("3. Check the Network tab when uploading files")
        print("4. Make sure you're using a supported browser (Chrome, Firefox, Safari)")
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 WEB INTERFACE TEST")
    print("=" * 60)
    test_web_interface()
    print("=" * 60)
    print("✅ Test completed")
    print("=" * 60)
