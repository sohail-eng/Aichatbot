"""
ChromaDB Service for RAG System

This service handles document storage, embedding generation, and semantic search
using ChromaDB as the vector database backend.
"""

import chromadb
import logging
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
from django.conf import settings

logger = logging.getLogger('ai_services')

class ChromaService:
    """
    ChromaDB service for document storage and retrieval
    """
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.collections = {}
        self._initialize_chroma()
        self._initialize_embedding_model()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client"""
        try:
            # Use persistent storage in media directory
            chroma_path = Path(settings.MEDIA_ROOT) / 'chroma_db'
            chroma_path.mkdir(exist_ok=True)
            
            self.client = chromadb.PersistentClient(path=str(chroma_path))
            logger.info(f"ChromaDB initialized at {chroma_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            # Fallback to in-memory client
            self.client = chromadb.Client()
            logger.warning("Using in-memory ChromaDB client")
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model"""
        try:
            # Use a lightweight but effective model
            model_name = "all-MiniLM-L6-v2"
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    def get_or_create_collection(self, session_id: str) -> chromadb.Collection:
        """Get or create a collection for a session"""
        collection_name = f"session_{session_id}"
        
        if collection_name not in self.collections:
            try:
                # Try to get existing collection
                collection = self.client.get_collection(collection_name)
                logger.info(f"Retrieved existing collection: {collection_name}")
            except:
                # Create new collection
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"session_id": session_id, "created_at": datetime.now().isoformat()}
                )
                logger.info(f"Created new collection: {collection_name}")
            
            self.collections[collection_name] = collection
        
        return self.collections[collection_name]
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not self.embedding_model:
            logger.error("Embedding model not available")
            return []
        
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
    
    def process_file_for_rag(self, session_id: str, file_path: str, file_type: str, 
                           file_name: str, file_id: str) -> Dict:
        """
        Process a file and store its chunks in ChromaDB
        
        Args:
            session_id: Chat session ID
            file_path: Path to the file
            file_type: Type of file (csv, xlsx, txt, json)
            file_name: Name of the file
            file_id: Database file ID
            
        Returns:
            Processing results with chunk information
        """
        try:
            logger.info(f"Processing file for RAG: {file_name} ({file_type})")
            
            # Get or create collection for this session
            collection = self.get_or_create_collection(session_id)
            
            # Extract content based on file type
            if file_type == 'csv':
                chunks = self._extract_csv_chunks(file_path, file_name)
            elif file_type in ['xlsx', 'xls']:
                chunks = self._extract_excel_chunks(file_path, file_name)
            elif file_type == 'txt':
                chunks = self._extract_text_chunks(file_path, file_name)
            elif file_type == 'json':
                chunks = self._extract_json_chunks(file_path, file_name)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_type}',
                    'chunks': []
                }
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'No content extracted from file',
                    'chunks': []
                }
            
            # Generate embeddings for chunks
            chunk_texts = [chunk['content'] for chunk in chunks]
            embeddings = self.generate_embeddings(chunk_texts)
            
            if not embeddings:
                return {
                    'success': False,
                    'error': 'Failed to generate embeddings',
                    'chunks': []
                }
            
            # Prepare data for ChromaDB
            ids = [f"{file_id}_{i}" for i in range(len(chunks))]
            metadatas = []
            documents = []
            
            for i, chunk in enumerate(chunks):
                metadata = {
                    'file_id': file_id,
                    'file_name': file_name,
                    'file_type': file_type,
                    'chunk_type': chunk['type'],
                    'chunk_index': i,
                    'session_id': session_id,
                    'upload_timestamp': datetime.now().isoformat()
                }
                
                if 'additional_metadata' in chunk:
                    metadata.update(chunk['additional_metadata'])
                
                metadatas.append(metadata)
                documents.append(chunk['content'])
            
            # Add to ChromaDB collection
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
            logger.info(f"Added {len(chunks)} chunks to ChromaDB for file: {file_name}")
            
            return {
                'success': True,
                'file_name': file_name,
                'file_type': file_type,
                'chunks_created': len(chunks),
                'total_content_length': sum(len(chunk['content']) for chunk in chunks),
                'chunks': chunks
            }
            
        except Exception as e:
            logger.error(f"Error processing file for RAG: {e}")
            return {
                'success': False,
                'error': str(e),
                'chunks': []
            }
    
    def _extract_csv_chunks(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract chunks from CSV file"""
        try:
            import pandas as pd
            
            df = pd.read_csv(file_path)
            chunks = []
            
            # Add column information chunk
            columns_info = {
                'type': 'columns',
                'content': f"Columns in {file_name}: {', '.join(df.columns.tolist())}",
                'additional_metadata': {
                    'total_columns': len(df.columns),
                    'total_rows': len(df)
                }
            }
            chunks.append(columns_info)
            
            # Add data summary chunk
            summary_info = {
                'type': 'summary',
                'content': f"Data summary for {file_name}: {len(df)} rows, {len(df.columns)} columns. File contains structured tabular data.",
                'additional_metadata': {
                    'total_rows': len(df),
                    'total_columns': len(df.columns)
                }
            }
            chunks.append(summary_info)
            
            # Add sample data chunks (in batches)
            sample_size = min(100, len(df))  # Limit to 100 rows
            sample_df = df.head(sample_size)
            
            # Split into smaller chunks for better search
            chunk_size = 20
            for i in range(0, len(sample_df), chunk_size):
                batch = sample_df.iloc[i:i+chunk_size]
                batch_data = batch.to_dict('records')
                
                chunk_content = f"Sample data from {file_name} (rows {i+1}-{min(i+chunk_size, len(sample_df))}):\n"
                chunk_content += json.dumps(batch_data, indent=2, default=str)
                
                chunk_info = {
                    'type': 'sample_data',
                    'content': chunk_content,
                    'additional_metadata': {
                        'row_start': i + 1,
                        'row_end': min(i + chunk_size, len(sample_df)),
                        'sample_size': len(batch)
                    }
                }
                chunks.append(chunk_info)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting CSV chunks: {e}")
            return []
    
    def _extract_excel_chunks(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract chunks from Excel file"""
        try:
            import pandas as pd
            
            excel_file = pd.ExcelFile(file_path)
            chunks = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Add sheet information chunk
                sheet_info = {
                    'type': 'sheet_info',
                    'content': f"Sheet '{sheet_name}' in {file_name}: {len(df)} rows, {len(df.columns)} columns",
                    'additional_metadata': {
                        'sheet_name': sheet_name,
                        'total_rows': len(df),
                        'total_columns': len(df.columns)
                    }
                }
                chunks.append(sheet_info)
                
                # Add sample data for this sheet
                if len(df) > 0:
                    sample_size = min(50, len(df))
                    sample_df = df.head(sample_size)
                    sample_data = sample_df.to_dict('records')
                    
                    sample_content = f"Sample data from sheet '{sheet_name}' in {file_name}:\n"
                    sample_content += json.dumps(sample_data, indent=2, default=str)
                    
                    sample_info = {
                        'type': 'sample_data',
                        'content': sample_content,
                        'additional_metadata': {
                            'sheet_name': sheet_name,
                            'sample_size': len(sample_data)
                        }
                    }
                    chunks.append(sample_info)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting Excel chunks: {e}")
            return []
    
    def _extract_text_chunks(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract chunks from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Split content into semantic chunks
            chunks = self._split_text_into_chunks(content, file_name)
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting text chunks: {e}")
            return []
    
    def _extract_json_chunks(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract chunks from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks = []
            
            # Add structure information chunk
            structure_info = {
                'type': 'structure',
                'content': f"JSON structure in {file_name}: {self._describe_json_structure(data)}",
                'additional_metadata': {
                    'data_type': type(data).__name__
                }
            }
            chunks.append(structure_info)
            
            # Add sample data chunk
            sample_content = f"Sample data from {file_name}:\n"
            sample_content += json.dumps(data, indent=2, default=str)[:3000] + "..."
            
            sample_info = {
                'type': 'sample_data',
                'content': sample_content,
                'additional_metadata': {
                    'data_type': type(data).__name__
                }
            }
            chunks.append(sample_info)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting JSON chunks: {e}")
            return []
    
    def _split_text_into_chunks(self, text: str, file_name: str, chunk_size: int = 1000, 
                               overlap: int = 200) -> List[Dict]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size * 0.5:  # At least 50% of chunk size
                    chunk = text[start:start + break_point + 1]
                    end = start + break_point + 1
            
            chunk_info = {
                'type': 'text_chunk',
                'content': chunk.strip(),
                'additional_metadata': {
                    'chunk_index': len(chunks),
                    'position_start': start,
                    'position_end': end
                }
            }
            chunks.append(chunk_info)
            
            start = end - overlap
        
        return chunks
    
    def _describe_json_structure(self, obj, max_depth=3, current_depth=0):
        """Describe JSON structure recursively"""
        if current_depth >= max_depth:
            return "..."
        
        if isinstance(obj, dict):
            if len(obj) == 0:
                return "empty object"
            keys = list(obj.keys())[:5]  # Show first 5 keys
            return f"object with keys: {', '.join(keys)}"
        elif isinstance(obj, list):
            if len(obj) == 0:
                return "empty array"
            return f"array with {len(obj)} items"
        else:
            return type(obj).__name__
    
    def search_similar_chunks(self, session_id: str, query: str, 
                            n_results: int = 5, file_filter: Optional[List[str]] = None) -> List[Dict]:
        """
        Search for similar chunks based on query
        
        Args:
            session_id: Chat session ID
            query: Search query
            n_results: Number of results to return
            file_filter: Optional list of file names to filter by
            
        Returns:
            List of search results with metadata
        """
        try:
            collection = self.get_or_create_collection(session_id)
            
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])
            if not query_embedding:
                return []
            
            # Build where clause for filtering
            where_clause = {}
            if file_filter and len(file_filter) > 0:
                # Filter by specific files only
                where_clause['file_name'] = {"$in": file_filter}
                logger.info(f"Filtering search to files: {file_filter}")
            
            # Search in collection
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            search_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    result = {
                        'chunk_id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'source_file': results['metadatas'][0][i]['file_name']
                    }
                    search_results.append(result)
            
            logger.info(f"Found {len(search_results)} similar chunks for query: {query} in files: {file_filter}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def get_file_chunks(self, session_id: str, file_name: str) -> List[Dict]:
        """Get all chunks for a specific file"""
        try:
            collection = self.get_or_create_collection(session_id)
            
            results = collection.get(
                where={'file_name': file_name},
                include=['metadatas', 'documents']
            )
            
            chunks = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    chunk = {
                        'chunk_id': results['ids'][i],
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    }
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting file chunks: {e}")
            return []
    
    def delete_file_chunks(self, session_id: str, file_name: str) -> bool:
        """Delete all chunks for a specific file"""
        try:
            collection = self.get_or_create_collection(session_id)
            
            # Get chunks to delete
            chunks_to_delete = collection.get(
                where={'file_name': file_name},
                include=['metadatas']
            )
            
            if chunks_to_delete['ids']:
                collection.delete(ids=chunks_to_delete['ids'])
                logger.info(f"Deleted {len(chunks_to_delete['ids'])} chunks for file: {file_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file chunks: {e}")
            return False
    
    def get_collection_stats(self, session_id: str) -> Dict:
        """Get statistics about the collection"""
        try:
            collection = self.get_or_create_collection(session_id)
            
            # Get all documents to count
            results = collection.get(include=['metadatas'])
            
            if not results['ids']:
                return {
                    'total_chunks': 0,
                    'total_files': 0,
                    'file_types': {},
                    'total_content_length': 0
                }
            
            # Count by file
            file_stats = {}
            total_content_length = 0
            
            for i, metadata in enumerate(results['metadatas']):
                file_name = metadata['file_name']
                if file_name not in file_stats:
                    file_stats[file_name] = {
                        'chunks': 0,
                        'file_type': metadata['file_type'],
                        'content_length': 0
                    }
                
                file_stats[file_name]['chunks'] += 1
                if 'content_length' in metadata:
                    file_stats[file_name]['content_length'] += metadata['content_length']
                    total_content_length += metadata['content_length']
            
            # Count file types
            file_types = {}
            for stats in file_stats.values():
                file_type = stats['file_type']
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            return {
                'total_chunks': len(results['ids']),
                'total_files': len(file_stats),
                'file_types': file_types,
                'total_content_length': total_content_length,
                'file_stats': file_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def clear_session_data(self, session_id: str) -> bool:
        """Clear all data for a session"""
        try:
            collection_name = f"session_{session_id}"
            
            if collection_name in self.collections:
                del self.collections[collection_name]
            
            # Delete collection from ChromaDB
            try:
                self.client.delete_collection(collection_name)
                logger.info(f"Deleted collection: {collection_name}")
            except:
                logger.warning(f"Collection {collection_name} not found for deletion")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session data: {e}")
            return False
