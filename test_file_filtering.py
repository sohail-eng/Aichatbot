#!/usr/bin/env python3
"""
Test File Filtering in RAG System

This script tests that the RAG system properly filters results by specific files.
"""

import os
import sys
import django
import logging
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')
django.setup()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_file_filtering():
    """Test that RAG system properly filters by files"""
    print("🔍 Testing File Filtering in RAG System...")
    
    try:
        from ai_services.rag_service import RAGService
        rag_service = RAGService()
        
        # Create test files with different content
        import pandas as pd
        
        # File 1: Device status data
        device_data = {
            'device_name': ['Router1', 'Switch1', 'Router2'],
            'status': ['up', 'down', 'up'],
            'ip_address': ['192.168.1.1', '192.168.1.2', '192.168.1.3']
        }
        df_devices = pd.DataFrame(device_data)
        device_file = "/tmp/devices.csv"
        df_devices.to_csv(device_file, index=False)
        
        # File 2: Network interface data
        interface_data = {
            'interface': ['eth0', 'eth1', 'eth2'],
            'speed': ['1G', '10G', '1G'],
            'status': ['active', 'inactive', 'active']
        }
        df_interfaces = pd.DataFrame(interface_data)
        interface_file = "/tmp/interfaces.csv"
        df_interfaces.to_csv(interface_file, index=False)
        
        print("   ✅ Created test files")
        
        # Process both files for RAG
        session_id = "test_filtering_session"
        
        print("   🔄 Processing devices.csv for RAG...")
        rag_result1 = rag_service.process_file_for_rag(
            session_id, device_file, 'csv', 'devices.csv', 'dev_001'
        )
        
        print("   🔄 Processing interfaces.csv for RAG...")
        rag_result2 = rag_service.process_file_for_rag(
            session_id, interface_file, 'csv', 'interfaces.csv', 'int_001'
        )
        
        if not rag_result1['success'] or not rag_result2['success']:
            print("   ❌ Failed to process files for RAG")
            return False
        
        print(f"   ✅ Files processed: {rag_result1['chunks_created']} + {rag_result2['chunks_created']} chunks")
        
        # Test 1: Search in devices.csv only
        print("\n   🔍 Test 1: Searching in devices.csv only...")
        context1 = rag_service.get_context_for_question(
            session_id, "which device status is down?", ['devices.csv']
        )
        
        if context1['success']:
            print(f"      ✅ Found {context1['total_sources']} sources in devices.csv")
            print(f"      📄 Context preview: {context1['context'][:200]}...")
            
            # Check that all sources are from devices.csv
            all_from_devices = all(source['file_name'] == 'devices.csv' for source in context1['sources'])
            if all_from_devices:
                print("      ✅ All sources correctly from devices.csv")
            else:
                print("      ❌ Found sources from wrong file!")
                return False
        else:
            print(f"      ❌ Failed to get context: {context1['message']}")
            return False
        
        # Test 2: Search in interfaces.csv only
        print("\n   🔍 Test 2: Searching in interfaces.csv only...")
        context2 = rag_service.get_context_for_question(
            session_id, "which interface status is inactive?", ['interfaces.csv']
        )
        
        if context2['success']:
            print(f"      ✅ Found {context2['total_sources']} sources in interfaces.csv")
            print(f"      📄 Context preview: {context2['context'][:200]}...")
            
            # Check that all sources are from interfaces.csv
            all_from_interfaces = all(source['file_name'] == 'interfaces.csv' for source in context2['sources'])
            if all_from_interfaces:
                print("      ✅ All sources correctly from interfaces.csv")
            else:
                print("      ❌ Found sources from wrong file!")
                return False
        else:
            print(f"      ❌ Failed to get context: {context2['message']}")
            return False
        
        # Test 3: Search in both files
        print("\n   🔍 Test 3: Searching in both files...")
        context3 = rag_service.get_context_for_question(
            session_id, "what is the status?", ['devices.csv', 'interfaces.csv']
        )
        
        if context3['success']:
            print(f"      ✅ Found {context3['total_sources']} sources across both files")
            
            # Check that sources come from both files
            file_names = set(source['file_name'] for source in context3['sources'])
            if file_names == {'devices.csv', 'interfaces.csv'}:
                print("      ✅ Sources correctly from both files")
            else:
                print(f"      ❌ Expected both files, got: {file_names}")
                return False
        else:
            print(f"      ❌ Failed to get context: {context3['message']}")
            return False
        
        # Test 4: Search in non-existent file
        print("\n   🔍 Test 4: Searching in non-existent file...")
        context4 = rag_service.get_context_for_question(
            session_id, "test query", ['nonexistent.csv']
        )
        
        if not context4['success']:
            print("      ✅ Correctly returned no results for non-existent file")
        else:
            print("      ❌ Should have returned no results")
            return False
        
        # Cleanup
        print("\n   🧹 Cleaning up...")
        rag_service.clear_file_chunks(session_id, 'devices.csv')
        rag_service.clear_file_chunks(session_id, 'interfaces.csv')
        os.remove(device_file)
        os.remove(interface_file)
        print("      ✅ Cleanup completed")
        
        print("\n🎉 File filtering tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ File filtering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_file_filtering()
    sys.exit(0 if success else 1)
