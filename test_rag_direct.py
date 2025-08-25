#!/usr/bin/env python3
"""
Direct RAG System Test

This script directly tests the RAG system components to identify any issues.
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

def test_rag_system_direct():
    """Test RAG system directly"""
    print("🧠 Testing RAG System Directly...")
    
    try:
        # Test 1: Import RAG service
        print("1. Testing RAG service import...")
        from ai_services.rag_service import RAGService
        rag_service = RAGService()
        print("   ✅ RAG service imported successfully")
        
        # Test 2: Import ChromaDB service
        print("2. Testing ChromaDB service import...")
        from ai_services.chroma_service import ChromaService
        chroma_service = ChromaService()
        print("   ✅ ChromaDB service imported successfully")
        
        # Test 3: Test file processing for RAG
        print("3. Testing file processing for RAG...")
        
        # Create a test CSV file
        import pandas as pd
        test_data = {
            'device_name': ['Router1', 'Switch1', 'Router2', 'Switch2'],
            'status': ['up', 'down', 'up', 'down'],
            'ip_address': ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4'],
            'location': ['DC1', 'DC1', 'DC2', 'DC2']
        }
        df = pd.DataFrame(test_data)
        
        test_file_path = "/tmp/test_devices.csv"
        df.to_csv(test_file_path, index=False)
        print(f"   ✅ Created test CSV file: {test_file_path}")
        
        # Test RAG processing
        test_session = "test_session_123"
        test_file_type = "csv"
        test_file_name = "test_devices.csv"
        test_file_id = "test_123"
        
        print("   🔄 Processing file for RAG...")
        rag_result = rag_service.process_file_for_rag(
            test_session, test_file_path, test_file_type, 
            test_file_name, test_file_id
        )
        
        if rag_result['success']:
            print(f"   ✅ RAG processing successful: {rag_result['chunks_created']} chunks created")
        else:
            print(f"   ❌ RAG processing failed: {rag_result.get('error', 'Unknown error')}")
            return False
        
        # Test 4: Test search functionality
        print("4. Testing search functionality...")
        search_results = rag_service.search_relevant_chunks(
            test_session, "which device status is down?", n_results=3
        )
        
        if search_results:
            print(f"   ✅ Search successful: {len(search_results)} results found")
            for i, result in enumerate(search_results[:2]):
                print(f"      Result {i+1}: Score {result.score:.3f}, Source: {result.source_file}")
        else:
            print("   ❌ Search failed: No results found")
            return False
        
        # Test 5: Test context retrieval
        print("5. Testing context retrieval...")
        context = rag_service.get_context_for_question(
            test_session, "which device status is down?", [test_file_name]
        )
        
        if context['success']:
            print(f"   ✅ Context retrieval successful: {context['total_sources']} sources")
            print(f"      Context length: {len(context['context'])} characters")
        else:
            print(f"   ❌ Context retrieval failed: {context.get('message', 'Unknown error')}")
            return False
        
        # Test 6: Test file stats
        print("6. Testing file statistics...")
        stats = rag_service.get_file_stats(test_session)
        print(f"   ✅ Stats retrieved: {stats['total_chunks']} chunks, {stats['total_files']} files")
        
        # Cleanup
        print("7. Cleaning up...")
        rag_service.clear_file_chunks(test_session, test_file_name)
        os.remove(test_file_path)
        print("   ✅ Cleanup completed")
        
        print("\n🎉 All RAG system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_analyzer():
    """Test file analyzer with RAG integration"""
    print("\n🔍 Testing File Analyzer with RAG...")
    
    try:
        from ai_services.file_analyzer import FileAnalyzer
        
        analyzer = FileAnalyzer()
        print("   ✅ File analyzer created successfully")
        
        # Test question analysis
        question = "which device status is down?"
        attached_files = [
            {
                'id': 'test_1',
                'name': 'test_devices.csv',
                'type': 'csv',
                'session_id': 'test_session_456'
            }
        ]
        
        print("   🔄 Testing question analysis...")
        result = analyzer.analyze_question_with_files(question, attached_files)
        
        if result['success']:
            print(f"   ✅ Question analysis successful: {result['files_analyzed']} files analyzed")
        else:
            print(f"   ❌ Question analysis failed: {result.get('error', 'Unknown error')}")
            return False
        
        print("   ✅ File analyzer tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ File analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Direct RAG System Tests...\n")
    
    tests = [
        ("RAG System", test_rag_system_direct),
        ("File Analyzer", test_file_analyzer)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! RAG system is working correctly.")
        print("\n💡 You can now use the RAG system in your chat application!")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
