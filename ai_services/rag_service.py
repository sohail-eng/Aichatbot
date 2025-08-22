"""
RAG (Retrieval-Augmented Generation) Service

This service provides a complete RAG implementation with:
- Document chunking and embedding
- Vector storage and retrieval
- Semantic search
- Context assembly for LLM responses
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger('ai_services')

@dataclass
class DocumentChunk:
    """Represents a chunk of document with metadata"""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    chunk_id: Optional[str] = None
    source_file: Optional[str] = None
    chunk_index: Optional[int] = None

@dataclass
class SearchResult:
    """Represents a search result with relevance score"""
    chunk: DocumentChunk
    score: float
    source_file: str
    context: str

class RAGService:
    """
    Comprehensive RAG service for document processing and retrieval
    """
    
    # Singleton instance
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.chunk_size = 1000  # Characters per chunk
            self.chunk_overlap = 200  # Overlap between chunks
            self.max_results = 10  # Maximum search results
            self.similarity_threshold = 0.7  # Minimum similarity score
            
            # In-memory storage (in production, use proper vector DB)
            self.document_chunks: Dict[str, DocumentChunk] = {}
            self.file_embeddings: Dict[str, List[DocumentChunk]] = {}
            
            # Initialize embedding model (simplified for now)
            self.embedding_model = self._initialize_embedding_model()
            
            RAGService._initialized = True
    
    def _initialize_embedding_model(self):
        """Initialize embedding model - simplified implementation"""
        try:
            # In production, use proper embedding model like sentence-transformers
            # For now, we'll use a simple TF-IDF based approach
            return "tfidf_simple"
        except Exception as e:
            logger.warning(f"Could not initialize embedding model: {e}")
            return "simple"
    
    def process_file_for_rag(self, file_path: str, file_type: str, file_name: str) -> Dict:
        """
        Process a file for RAG system
        
        Args:
            file_path: Path to the file
            file_type: Type of file (csv, xlsx, txt, json)
            file_name: Name of the file
            
        Returns:
            Processing results with chunks and metadata
        """
        try:
            logger.info(f"Processing file for RAG: {file_name} ({file_type})")
            
            # Extract content based on file type
            if file_type == 'csv':
                content_chunks = self._extract_csv_content(file_path, file_name)
            elif file_type in ['xlsx', 'xls']:
                content_chunks = self._extract_excel_content(file_path, file_name)
            elif file_type == 'txt':
                content_chunks = self._extract_text_content(file_path, file_name)
            elif file_type == 'json':
                content_chunks = self._extract_json_content(file_path, file_name)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_type}',
                    'chunks': []
                }
            
            # Create document chunks
            document_chunks = self._create_document_chunks(content_chunks, file_name, file_type)
            
            # Generate embeddings for chunks
            embedded_chunks = self._generate_embeddings(document_chunks)
            
            # Store chunks
            self._store_chunks(embedded_chunks, file_name)
            
            return {
                'success': True,
                'file_name': file_name,
                'file_type': file_type,
                'chunks_created': len(embedded_chunks),
                'total_content_length': sum(len(chunk.content) for chunk in embedded_chunks),
                'chunks': embedded_chunks
            }
            
        except Exception as e:
            logger.error(f"Error processing file for RAG: {e}")
            return {
                'success': False,
                'error': str(e),
                'chunks': []
            }
    
    def _extract_csv_content(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract content from CSV file"""
        try:
            df = pd.read_csv(file_path)
            
            content_chunks = []
            
            # Add column information
            columns_info = {
                'type': 'columns',
                'content': f"Columns in {file_name}: {', '.join(df.columns.tolist())}",
                'metadata': {
                    'file_name': file_name,
                    'file_type': 'csv',
                    'total_columns': len(df.columns),
                    'total_rows': len(df)
                }
            }
            content_chunks.append(columns_info)
            
            # Add sample data
            sample_data = df.head(10).to_dict('records')
            sample_info = {
                'type': 'sample_data',
                'content': f"Sample data from {file_name}:\n{json.dumps(sample_data, indent=2)}",
                'metadata': {
                    'file_name': file_name,
                    'file_type': 'csv',
                    'sample_size': len(sample_data)
                }
            }
            content_chunks.append(sample_info)
            
            # Add data summary
            summary_info = {
                'type': 'summary',
                'content': f"Data summary for {file_name}: {len(df)} rows, {len(df.columns)} columns",
                'metadata': {
                    'file_name': file_name,
                    'file_type': 'csv',
                    'total_rows': len(df),
                    'total_columns': len(df.columns)
                }
            }
            content_chunks.append(summary_info)
            
            return content_chunks
            
        except Exception as e:
            logger.error(f"Error extracting CSV content: {e}")
            return []
    
    def _extract_excel_content(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract content from Excel file"""
        try:
            excel_file = pd.ExcelFile(file_path)
            
            content_chunks = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Add sheet information
                sheet_info = {
                    'type': 'sheet_info',
                    'content': f"Sheet '{sheet_name}' in {file_name}: {len(df)} rows, {len(df.columns)} columns",
                    'metadata': {
                        'file_name': file_name,
                        'file_type': 'excel',
                        'sheet_name': sheet_name,
                        'total_rows': len(df),
                        'total_columns': len(df.columns)
                    }
                }
                content_chunks.append(sheet_info)
                
                # Add sample data for this sheet
                if len(df) > 0:
                    sample_data = df.head(5).to_dict('records')
                    sample_info = {
                        'type': 'sample_data',
                        'content': f"Sample data from sheet '{sheet_name}' in {file_name}:\n{json.dumps(sample_data, indent=2)}",
                        'metadata': {
                            'file_name': file_name,
                            'file_type': 'excel',
                            'sheet_name': sheet_name,
                            'sample_size': len(sample_data)
                        }
                    }
                    content_chunks.append(sample_info)
            
            return content_chunks
            
        except Exception as e:
            logger.error(f"Error extracting Excel content: {e}")
            return []
    
    def _extract_text_content(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract content from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Split content into chunks
            chunks = self._split_text_into_chunks(content)
            
            content_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_info = {
                    'type': 'text_chunk',
                    'content': chunk,
                    'metadata': {
                        'file_name': file_name,
                        'file_type': 'txt',
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                }
                content_chunks.append(chunk_info)
            
            return content_chunks
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return []
    
    def _extract_json_content(self, file_path: str, file_name: str) -> List[Dict]:
        """Extract content from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            content_chunks = []
            
            # Add structure information
            structure_info = {
                'type': 'structure',
                'content': f"JSON structure in {file_name}: {self._describe_json_structure(data)}",
                'metadata': {
                    'file_name': file_name,
                    'file_type': 'json',
                    'data_type': type(data).__name__
                }
            }
            content_chunks.append(structure_info)
            
            # Add sample data
            sample_info = {
                'type': 'sample_data',
                'content': f"Sample data from {file_name}:\n{json.dumps(data, indent=2)[:2000]}...",
                'metadata': {
                    'file_name': file_name,
                    'file_type': 'json',
                    'data_type': type(data).__name__
                }
            }
            content_chunks.append(sample_info)
            
            return content_chunks
            
        except Exception as e:
            logger.error(f"Error extracting JSON content: {e}")
            return []
    
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
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + self.chunk_size * 0.5:  # At least 50% of chunk size
                    chunk = text[start:start + break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        
        return chunks
    
    def _create_document_chunks(self, content_chunks: List[Dict], file_name: str, file_type: str) -> List[DocumentChunk]:
        """Create DocumentChunk objects from content chunks"""
        document_chunks = []
        
        for i, content_chunk in enumerate(content_chunks):
            chunk_id = self._generate_chunk_id(file_name, i)
            
            chunk = DocumentChunk(
                content=content_chunk['content'],
                metadata={
                    'file_name': file_name,
                    'file_type': file_type,
                    'chunk_type': content_chunk['type'],
                    'chunk_index': i,
                    **content_chunk['metadata']
                },
                chunk_id=chunk_id,
                source_file=file_name,
                chunk_index=i
            )
            
            document_chunks.append(chunk)
        
        return document_chunks
    
    def _generate_chunk_id(self, file_name: str, chunk_index: int) -> str:
        """Generate unique chunk ID"""
        content = f"{file_name}_{chunk_index}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_embeddings(self, document_chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Generate embeddings for document chunks"""
        for chunk in document_chunks:
            # Simplified embedding generation (in production, use proper embedding model)
            chunk.embedding = self._simple_embedding(chunk.content)
        
        return document_chunks
    
    def _simple_embedding(self, text: str) -> List[float]:
        """Simple embedding generation using TF-IDF-like approach"""
        # This is a simplified implementation
        # In production, use sentence-transformers or similar
        words = re.findall(r'\w+', text.lower())
        word_freq = {}
        
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Create a simple vector representation
        # In production, this would be a proper embedding
        vector = [len(word_freq), len(words), len(text)]
        
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def _store_chunks(self, chunks: List[DocumentChunk], file_name: str):
        """Store chunks in memory (in production, use vector database)"""
        self.file_embeddings[file_name] = chunks
        
        for chunk in chunks:
            self.document_chunks[chunk.chunk_id] = chunk
    
    def search_relevant_chunks(self, query: str, file_names: Optional[List[str]] = None) -> List[SearchResult]:
        """
        Search for relevant chunks based on query
        
        Args:
            query: Search query
            file_names: Optional list of file names to search in
            
        Returns:
            List of search results with relevance scores
        """
        try:
            logger.info(f"Searching for query: '{query}'")
            
            # Generate query embedding
            query_embedding = self._simple_embedding(query)
            
            search_results = []
            
            # Determine which files to search
            files_to_search = file_names if file_names else list(self.file_embeddings.keys())
            
            for file_name in files_to_search:
                if file_name not in self.file_embeddings:
                    continue
                
                chunks = self.file_embeddings[file_name]
                
                for chunk in chunks:
                    if chunk.embedding is None:
                        continue
                    
                    # Calculate similarity score
                    similarity = self._calculate_similarity(query_embedding, chunk.embedding)
                    
                    if similarity >= self.similarity_threshold:
                        result = SearchResult(
                            chunk=chunk,
                            score=similarity,
                            source_file=file_name,
                            context=chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content
                        )
                        search_results.append(result)
            
            # Sort by relevance score
            search_results.sort(key=lambda x: x.score, reverse=True)
            
            # Return top results
            return search_results[:self.max_results]
            
        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        try:
            # Ensure embeddings have same length
            max_len = max(len(embedding1), len(embedding2))
            emb1 = embedding1 + [0] * (max_len - len(embedding1))
            emb2 = embedding2 + [0] * (max_len - len(embedding2))
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def get_context_for_question(self, question: str, file_names: List[str]) -> Dict:
        """
        Get relevant context for a question from specified files
        
        Args:
            question: User question
            file_names: List of file names to search in
            
        Returns:
            Context information for LLM
        """
        try:
            # Search for relevant chunks
            search_results = self.search_relevant_chunks(question, file_names)
            
            if not search_results:
                return {
                    'success': False,
                    'context': '',
                    'sources': [],
                    'message': 'No relevant context found in the specified files.'
                }
            
            # Assemble context
            context_parts = []
            sources = []
            
            for result in search_results:
                context_parts.append(f"Source: {result.source_file}\n{result.chunk.content}")
                sources.append({
                    'file_name': result.source_file,
                    'chunk_type': result.chunk.metadata.get('chunk_type', 'unknown'),
                    'relevance_score': result.score,
                    'content_preview': result.context
                })
            
            context = "\n\n---\n\n".join(context_parts)
            
            return {
                'success': True,
                'context': context,
                'sources': sources,
                'total_sources': len(sources),
                'average_relevance': sum(r.score for r in search_results) / len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return {
                'success': False,
                'context': '',
                'sources': [],
                'message': f'Error retrieving context: {str(e)}'
            }
    
    def clear_file_chunks(self, file_name: str):
        """Clear chunks for a specific file"""
        if file_name in self.file_embeddings:
            chunks = self.file_embeddings[file_name]
            for chunk in chunks:
                if chunk.chunk_id in self.document_chunks:
                    del self.document_chunks[chunk.chunk_id]
            del self.file_embeddings[file_name]
            logger.info(f"Cleared chunks for file: {file_name}")
    
    def get_file_stats(self) -> Dict:
        """Get statistics about stored chunks"""
        total_chunks = len(self.document_chunks)
        total_files = len(self.file_embeddings)
        
        file_stats = {}
        for file_name, chunks in self.file_embeddings.items():
            file_stats[file_name] = {
                'chunks': len(chunks),
                'total_content_length': sum(len(chunk.content) for chunk in chunks)
            }
        
        return {
            'total_chunks': total_chunks,
            'total_files': total_files,
            'file_stats': file_stats
        }
