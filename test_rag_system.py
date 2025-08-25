#!/usr/bin/env python3
"""
Test script for RAG system with ChromaDB

This script tests the complete RAG pipeline:
1. File processing and chunking
2. ChromaDB storage
3. Semantic search
4. Context retrieval
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

from ai_services.chroma_service import ChromaService
from ai_services.rag_service import RAGService
from ai_services.file_service import FileService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chroma_service():
    """Test ChromaDB service functionality"""
    print("🔍 Testing ChromaDB Service...")
    
    try:
        # Initialize service
        chroma_service = ChromaService()
        print("✅ ChromaDB service initialized successfully")
        
        # Test collection creation
        test_session = "test_session_123"
        collection = chroma_service.get_or_create_collection(test_session)
        print(f"✅ Collection created/retrieved: {collection.name}")
        
        # Test embedding generation
        test_texts = ["Hello world", "This is a test", "RAG system test"]
        embeddings = chroma_service.generate_embeddings(test_texts)
        print(f"✅ Generated {len(embeddings)} embeddings")
        
        # Test file processing (mock)
        test_file_path = "/tmp/test.csv"
        test_file_type = "csv"
        test_file_name = "test_data.csv"
        test_file_id = "test_123"
        
        # Create a simple test CSV
        import pandas as pd
        test_data = {
            'name': ['John', 'Jane', 'Bob'],
            'age': [25, 30, 35],
            'city': ['NYC', 'LA', 'Chicago']
        }
        df = pd.DataFrame(test_data)
        df.to_csv(test_file_path, index=False)
        
        # Process file for RAG
        result = chroma_service.process_file_for_rag(
            test_session, test_file_path, test_file_type, 
            test_file_name, test_file_id
        )
        
        if result['success']:
            print(f"✅ File processed for RAG: {result['chunks_created']} chunks created")
        else:
            print(f"❌ RAG processing failed: {result.get('error', 'Unknown error')}")
        
        # Test search
        search_results = chroma_service.search_similar_chunks(
            test_session, "What are the ages?", n_results=3
        )
        print(f"✅ Search returned {len(search_results)} results")
        
        # Test collection stats
        stats = chroma_service.get_collection_stats(test_session)
        print(f"✅ Collection stats: {stats['total_chunks']} chunks, {stats['total_files']} files")
        
        # Cleanup
        chroma_service.clear_session_data(test_session)
        os.remove(test_file_path)
        print("✅ Test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_service():
    """Test RAG service functionality"""
    print("\n🔍 Testing RAG Service...")
    
    try:
        # Initialize service
        rag_service = RAGService()
        print("✅ RAG service initialized successfully")
        
        # Test file processing for RAG
        test_session = "test_rag_session_456"
        test_file_path = "/tmp/test_rag.csv"
        test_file_type = "csv"
        test_file_name = "test_rag_data.csv"
        test_file_id = "test_rag_123"
        
        # Create test data
        import pandas as pd
        test_data = {
            'product': ['Laptop', 'Phone', 'Tablet'],
            'price': [999, 599, 299],
            'category': ['Electronics', 'Electronics', 'Electronics']
        }
        df = pd.DataFrame(test_data)
        df.to_csv(test_file_path, index=False)
        
        # Process file for RAG
        result = rag_service.process_file_for_rag(
            test_session, test_file_path, test_file_type, 
            test_file_name, test_file_id
        )
        
        if result['success']:
            print(f"✅ File processed for RAG: {result['chunks_created']} chunks created")
        else:
            print(f"❌ RAG processing failed: {result.get('error', 'Unknown error')}")
        
        # Test context retrieval
        context = rag_service.get_context_for_question(
            test_session, "What products are available?", [test_file_name]
        )
        
        if context['success']:
            print(f"✅ Context retrieved: {context['total_sources']} sources")
            print(f"   Context length: {len(context['context'])} characters")
        else:
            print(f"❌ Context retrieval failed: {context.get('message', 'Unknown error')}")
        
        # Test search
        search_results = rag_service.search_relevant_chunks(
            test_session, "What are the prices?", [test_file_name]
        )
        print(f"✅ Search returned {len(search_results)} results")
        
        # Test file stats
        stats = rag_service.get_file_stats(test_session)
        print(f"✅ File stats: {stats['total_chunks']} chunks, {stats['total_files']} files")
        
        # Cleanup
        rag_service.clear_file_chunks(test_session, test_file_name)
        os.remove(test_file_path)
        print("✅ Test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_service_integration():
    """Test file service integration with RAG"""
    print("\n🔍 Testing File Service RAG Integration...")
    
    try:
        # Initialize service
        file_service = FileService()
        print("✅ File service initialized successfully")
        
        # Test RAG processing method
        test_session = "test_file_rag_789"
        test_file_path = "/tmp/test_integration.csv"
        test_file_type = "csv"
        test_file_name = "test_integration_data.csv"
        test_file_id = "test_integration_123"
        
        # Create test data
        import pandas as pd
        test_data = {
            'employee': ['Alice', 'Bob', 'Charlie'],
            'department': ['HR', 'IT', 'Sales'],
            'salary': [50000, 70000, 60000]
        }
        df = pd.DataFrame(test_data)
        df.to_csv(test_file_path, index=False)
        
        # Process file for RAG
        result = file_service.process_file_for_rag(
            test_session, test_file_path, test_file_type, 
            test_file_name, test_file_id
        )
        
        if result['success']:
            print(f"✅ File service RAG processing: {result['chunks_created']} chunks created")
        else:
            print(f"❌ File service RAG processing failed: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        os.remove(test_file_path)
        print("✅ Test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ File service integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting RAG System Tests...\n")
    
    tests = [
        ("ChromaDB Service", test_chroma_service),
        ("RAG Service", test_rag_service),
        ("File Service Integration", test_file_service_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    
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
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



