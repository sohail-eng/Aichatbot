"""
Professional File Analyzer Service

Generic file analysis service that extracts relevant data based on user questions
without domain-specific assumptions. Uses semantic matching and context building
for AI model integration.
"""

import pandas as pd
import json
import logging
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async
from .rag_service import RAGService

logger = logging.getLogger('ai_services')

class FileAnalyzer:
    """Generic file analysis service for AI-driven data retrieval"""
    
    def __init__(self):
        self.search_cache = {}
        self.rag_service = RAGService()
    
    def analyze_question_with_files(self, question: str, attached_files: List[Dict]) -> Dict:
        """
        Analyze user question against attached files to find relevant data
        
        Args:
            question: User's question
            attached_files: List of file info dicts with keys: id, name, type
            
        Returns:
            Dict with success, found_data, files_analyzed, search_keywords, comprehensive_analysis
        """
        try:
            logger.info(f"Analyzing question: '{question}' with {len(attached_files)} files")
            
            # Extract search terms from question
            search_terms = self._extract_search_terms(question)
            logger.info(f"Search terms: {search_terms}")
            
            # Process each file
            file_analyses = []
            all_found_data = []
            files_analyzed = 0
            
            for file_info in attached_files:
                file_path = self._resolve_file_path(file_info)
                if not file_path:
                    logger.warning(f"Could not resolve path for: {file_info}")
                    continue
                
                # Process file for RAG system
                rag_result = self.rag_service.process_file_for_rag(
                    file_path, 
                    file_info.get('type'), 
                    file_info.get('name')
                )
                
                # Analyze file content (legacy + RAG enhanced)
                analysis = self._analyze_file(file_path, file_info, search_terms, question)
                
                # Enhance analysis with RAG results
                if rag_result['success']:
                    analysis['rag_chunks'] = rag_result['chunks_created']
                    analysis['rag_enhanced'] = True
                
                file_analyses.append({
                    'file_id': file_info.get('id'),
                    'file_name': file_info.get('name'),
                    'file_type': file_info.get('type'),
                    'analysis': analysis
                })
                
                # Collect relevant data
                if analysis['relevance_score'] > 0:
                    all_found_data.append({
                        'file_name': file_info.get('name'),
                        'file_type': file_info.get('type'),
                        'data': analysis['found_data'],
                        'relevance_score': analysis['relevance_score'],
                        'summary': analysis['summary']
                    })
                
                files_analyzed += 1
            
            # Generate comprehensive analysis for AI
            comprehensive_analysis = self._build_comprehensive_analysis(
                question, file_analyses, all_found_data, search_terms
            )
            
            return {
                'success': True,
                'question': question,
                'files_analyzed': files_analyzed,
                'found_data': all_found_data,
                'file_analyses': file_analyses,
                'comprehensive_analysis': comprehensive_analysis,
                'search_keywords': search_terms
            }
            
        except Exception as e:
            logger.error(f"Error in file analysis: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'question': question,
                'files_analyzed': 0,
                'found_data': [],
                'file_analyses': []
            }
    
    async def analyze_question_with_files_async(self, question: str, attached_files: List[Dict]) -> Dict:
        """
        Async version of analyze_question_with_files for use in async contexts
        
        Args:
            question: User's question
            attached_files: List of file info dicts with keys: id, name, type
            
        Returns:
            Dict with success, found_data, files_analyzed, search_keywords, comprehensive_analysis
        """
        try:
            logger.info(f"Analyzing question (async): '{question}' with {len(attached_files)} files")
            
            # Extract search terms from question
            search_terms = self._extract_search_terms(question)
            logger.info(f"Search terms: {search_terms}")
            
            # Process each file
            file_analyses = []
            all_found_data = []
            files_analyzed = 0
            
            for file_info in attached_files:
                file_path = await self._resolve_file_path_async(file_info)
                if not file_path:
                    logger.warning(f"Could not resolve path for: {file_info}")
                    continue
                
                # Process file for RAG system
                rag_result = self.rag_service.process_file_for_rag(
                    file_path, 
                    file_info.get('type'), 
                    file_info.get('name')
                )
                
                # Analyze file content (legacy + RAG enhanced)
                analysis = self._analyze_file(file_path, file_info, search_terms, question)
                
                # Enhance analysis with RAG results
                if rag_result['success']:
                    analysis['rag_chunks'] = rag_result['chunks_created']
                    analysis['rag_enhanced'] = True
                
                file_analyses.append({
                    'file_id': file_info.get('id'),
                    'file_name': file_info.get('name'),
                    'file_type': file_info.get('type'),
                    'analysis': analysis
                })
                
                # Collect relevant data
                if analysis['relevance_score'] > 0:
                    all_found_data.append({
                        'file_name': file_info.get('name'),
                        'file_type': file_info.get('type'),
                        'data': analysis['found_data'],
                        'relevance_score': analysis['relevance_score'],
                        'summary': analysis['summary']
                    })
                
                files_analyzed += 1
            
            # Generate comprehensive analysis for AI
            comprehensive_analysis = self._build_comprehensive_analysis(
                question, file_analyses, all_found_data, search_terms
            )
            
            return {
                'success': True,
                'question': question,
                'files_analyzed': files_analyzed,
                'found_data': all_found_data,
                'file_analyses': file_analyses,
                'comprehensive_analysis': comprehensive_analysis,
                'search_keywords': search_terms
            }
            
        except Exception as e:
            logger.error(f"Error in async file analysis: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'question': question,
                'files_analyzed': 0,
                'found_data': [],
                'file_analyses': []
            }
    
    def _extract_search_terms(self, question: str) -> List[str]:
        """Extract meaningful search terms from question"""
        # Clean and tokenize
        clean_question = re.sub(r'[^\w\s]', ' ', question.lower())
        words = clean_question.split()
        
        # Remove stop words
        stop_words = {
            'what', 'is', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'within', 'without', 'against',
            'show', 'tell', 'give', 'find', 'get', 'make', 'do', 'have', 'has', 'had',
            'will', 'would', 'could', 'should', 'can', 'may', 'might', 'must', 'shall',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Filter meaningful terms (length > 2, not stop words)
        terms = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Add question type context
        if 'which' in question.lower() or 'what' in question.lower():
            terms.extend(['list', 'show', 'identify'])
        if 'how many' in question.lower():
            terms.extend(['count', 'number', 'total'])
        if 'down' in question.lower():
            terms.extend(['failed', 'inactive', 'offline'])
        
        return list(set(terms))
    
    def _resolve_file_path(self, file_info: Dict) -> Optional[str]:
        """Resolve file path from file info (synchronous version)"""
        try:
            file_id = file_info.get('id')
            file_name = file_info.get('name')
            
            # Check for direct path first (for testing)
            if 'path' in file_info:
                direct_path = file_info['path']
                if Path(direct_path).exists():
                    logger.info(f"Using direct path: {direct_path}")
                    return direct_path
            
            # Try Django model lookup (synchronous)
            try:
                from chat.models import UploadedFile
                
                # Try by ID first
                if file_id and str(file_id).isdigit():
                    try:
                        file_obj = UploadedFile.objects.get(id=file_id)
                        full_path = Path(settings.MEDIA_ROOT) / file_obj.file_path
                        if full_path.exists():
                            return str(full_path)
                    except UploadedFile.DoesNotExist:
                        pass
                
                # Try by name
                if file_name:
                    file_obj = UploadedFile.objects.filter(file_name=file_name).first()
                    if file_obj:
                        full_path = Path(settings.MEDIA_ROOT) / file_obj.file_path
                        if full_path.exists():
                            return str(full_path)
            
            except ImportError:
                logger.warning("Django models not available")
            
            # Fallback: search filesystem
            if file_name:
                media_root = Path(settings.MEDIA_ROOT)
                if media_root.exists():
                    # Exact match
                    for path in media_root.rglob(file_name):
                        if path.is_file():
                            return str(path)
                    
                    # Case insensitive
                    for path in media_root.rglob("*"):
                        if path.is_file() and path.name.lower() == file_name.lower():
                            return str(path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving file path: {e}")
            return None
    
    async def _resolve_file_path_async(self, file_info: Dict) -> Optional[str]:
        """Resolve file path from file info (async version)"""
        try:
            file_id = file_info.get('id')
            file_name = file_info.get('name')
            
            # Check for direct path first (for testing)
            if 'path' in file_info:
                direct_path = file_info['path']
                if Path(direct_path).exists():
                    logger.info(f"Using direct path: {direct_path}")
                    return direct_path
            
            # Try Django model lookup (async)
            try:
                from chat.models import UploadedFile
                
                # Try by ID first
                if file_id and str(file_id).isdigit():
                    try:
                        file_obj = await sync_to_async(UploadedFile.objects.get)(id=file_id)
                        full_path = Path(settings.MEDIA_ROOT) / file_obj.file_path
                        if full_path.exists():
                            return str(full_path)
                    except UploadedFile.DoesNotExist:
                        pass
                
                # Try by name
                if file_name:
                    file_obj = await sync_to_async(UploadedFile.objects.filter(file_name=file_name).first)()
                    if file_obj:
                        full_path = Path(settings.MEDIA_ROOT) / file_obj.file_path
                        if full_path.exists():
                            return str(full_path)
            
            except ImportError:
                logger.warning("Django models not available")
            
            # Fallback: search filesystem
            if file_name:
                media_root = Path(settings.MEDIA_ROOT)
                if media_root.exists():
                    # Exact match
                    for path in media_root.rglob(file_name):
                        if path.is_file():
                            return str(path)
                    
                    # Case insensitive
                    for path in media_root.rglob("*"):
                        if path.is_file() and path.name.lower() == file_name.lower():
                            return str(path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving file path (async): {e}")
            return None
    
    def _analyze_file(self, file_path: str, file_info: Dict, search_terms: List[str], question: str) -> Dict:
        """Analyze single file for relevant data"""
        try:
            file_type = file_info.get('type', '').lower()
            
            if file_type == 'csv':
                return self._analyze_csv(file_path, search_terms, question)
            elif file_type in ['xlsx', 'xls']:
                return self._analyze_excel(file_path, search_terms, question)
            elif file_type == 'json':
                return self._analyze_json(file_path, search_terms, question)
            elif file_type == 'txt':
                return self._analyze_text(file_path, search_terms, question)
            else:
                return {
                    'found_data': {},
                    'relevance_score': 0,
                    'summary': f'Unsupported file type: {file_type}',
                    'file_path': file_path
                }
                
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {
                'found_data': {},
                'relevance_score': 0,
                'summary': f'Error analyzing file: {str(e)}',
                'file_path': file_path
            }
    
    def _analyze_csv(self, file_path: str, search_terms: List[str], question: str) -> Dict:
        """Analyze CSV file"""
        try:
            df = pd.read_csv(file_path)
            logger.info(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")
            
            relevance_score = 0
            found_data = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns': list(df.columns),
                'sample_data': df.head(3).to_dict('records'),
                'matching_columns': [],
                'matching_data': [],
                'filtered_data': []
            }
            
            # 1. Check column names for relevance
            for col in df.columns:
                col_lower = str(col).lower()
                for term in search_terms:
                    if term.lower() in col_lower:
                        found_data['matching_columns'].append(col)
                        relevance_score += 2
                        break
            
            # 2. Search data content
            for term in search_terms:
                term_lower = term.lower()
                for col in df.columns:
                    # Convert column to string and search
                    col_str = df[col].astype(str).str.lower()
                    mask = col_str.str.contains(term_lower, na=False, regex=False)
                    
                    if mask.any():
                        matching_rows = df[mask]
                        found_data['matching_data'].append({
                            'search_term': term,
                            'column': col,
                            'matches': len(matching_rows),
                            'sample_rows': matching_rows.head(5).to_dict('records')
                        })
                        relevance_score += len(matching_rows)
            
            # 3. Apply intelligent filtering based on question
            filtered_df = self._apply_intelligent_filter(df, question, search_terms)
            if not filtered_df.empty and len(filtered_df) < len(df):
                found_data['filtered_data'] = filtered_df.head(20).to_dict('records')
                found_data['filtered_count'] = len(filtered_df)
                relevance_score += 5
            
            # Generate summary
            summary = self._generate_csv_summary(found_data, relevance_score)
            
            return {
                'found_data': found_data,
                'relevance_score': relevance_score,
                'summary': summary,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"CSV analysis error: {e}")
            return {
                'found_data': {},
                'relevance_score': 0,
                'summary': f'Error reading CSV: {str(e)}',
                'file_path': file_path
            }
    
    def _apply_intelligent_filter(self, df: pd.DataFrame, question: str, search_terms: List[str]) -> pd.DataFrame:
        """Apply intelligent filtering based on question context"""
        try:
            question_lower = question.lower()
            
            # State-based filtering (for any status/state columns)
            state_columns = [col for col in df.columns if any(word in str(col).lower() 
                           for word in ['state', 'status', 'condition', 'health'])]
            
            if state_columns and ('down' in search_terms or 'failed' in search_terms):
                state_col = state_columns[0]
                # Look for inactive/down/failed states
                down_patterns = ['down', 'idle', 'active', 'failed', 'disconnect', 'inactive', 'offline']
                mask = df[state_col].astype(str).str.lower().str.contains('|'.join(down_patterns), na=False)
                if mask.any():
                    return df[mask]
            
            # Name-based filtering (which/what devices/items)
            if 'which' in question_lower or 'what' in question_lower:
                name_columns = [col for col in df.columns if any(word in str(col).lower() 
                              for word in ['name', 'device', 'host', 'id', 'identifier'])]
                if name_columns:
                    # Return data with relevant name columns
                    return df.dropna(subset=[name_columns[0]])
            
            # Count-based filtering
            if 'how many' in question_lower:
                # Group by relevant columns and count
                group_columns = [col for col in df.columns if any(term in str(col).lower() 
                               for term in search_terms)]
                if group_columns:
                    grouped = df.groupby(group_columns[0]).size().reset_index(name='count')
                    return grouped
            
            return pd.DataFrame()  # No intelligent filter applied
            
        except Exception as e:
            logger.error(f"Error in intelligent filtering: {e}")
            return pd.DataFrame()
    
    def _analyze_excel(self, file_path: str, search_terms: List[str], question: str) -> Dict:
        """Analyze Excel file"""
        try:
            excel_file = pd.ExcelFile(file_path)
            
            all_data = {}
            relevance_score = 0
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # Reuse CSV analysis logic
                sheet_analysis = self._analyze_csv_dataframe(df, search_terms, question)
                if sheet_analysis['relevance_score'] > 0:
                    all_data[sheet_name] = sheet_analysis['found_data']
                    relevance_score += sheet_analysis['relevance_score']
            
            summary = f"Excel file with {len(excel_file.sheet_names)} sheets"
            if relevance_score > 0:
                relevant_sheets = len(all_data)
                summary += f", found relevant data in {relevant_sheets} sheet(s)"
            
            return {
                'found_data': all_data,
                'relevance_score': relevance_score,
                'summary': summary,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Excel analysis error: {e}")
            return {
                'found_data': {},
                'relevance_score': 0,
                'summary': f'Error reading Excel: {str(e)}',
                'file_path': file_path
            }
    
    def _analyze_csv_dataframe(self, df: pd.DataFrame, search_terms: List[str], question: str) -> Dict:
        """Analyze DataFrame (shared logic for CSV and Excel)"""
        # Same logic as _analyze_csv but operates on DataFrame directly
        relevance_score = 0
        found_data = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'matching_columns': [],
            'matching_data': []
        }
        
        # Column matching
        for col in df.columns:
            col_lower = str(col).lower()
            for term in search_terms:
                if term.lower() in col_lower:
                    found_data['matching_columns'].append(col)
                    relevance_score += 2
                    break
        
        # Data matching
        for term in search_terms:
            for col in df.columns:
                col_str = df[col].astype(str).str.lower()
                mask = col_str.str.contains(term.lower(), na=False, regex=False)
                if mask.any():
                    matching_rows = df[mask]
                    found_data['matching_data'].append({
                        'search_term': term,
                        'column': col,
                        'matches': len(matching_rows),
                        'sample_rows': matching_rows.head(3).to_dict('records')
                    })
                    relevance_score += len(matching_rows)
        
        return {
            'found_data': found_data,
            'relevance_score': relevance_score,
            'summary': self._generate_csv_summary(found_data, relevance_score)
        }
    
    def _analyze_json(self, file_path: str, search_terms: List[str], question: str) -> Dict:
        """Analyze JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            matches = []
            relevance_score = 0
            
            def search_recursive(obj, path=""):
                nonlocal matches, relevance_score
                
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        # Check key names
                        key_lower = str(key).lower()
                        for term in search_terms:
                            if term.lower() in key_lower:
                                matches.append({
                                    'path': current_path,
                                    'type': 'key_match',
                                    'key': key,
                                    'value': str(value)[:200],
                                    'search_term': term
                                })
                                relevance_score += 2
                        
                        search_recursive(value, current_path)
                
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        search_recursive(item, f"{path}[{i}]")
                
                else:
                    # Check values
                    value_str = str(obj).lower()
                    for term in search_terms:
                        if term.lower() in value_str:
                            matches.append({
                                'path': path,
                                'type': 'value_match',
                                'value': str(obj)[:200],
                                'search_term': term
                            })
                            relevance_score += 1
            
            search_recursive(data)
            
            summary = f"JSON file with {len(matches)} matches" if matches else "JSON file with no matches"
            
            return {
                'found_data': {
                    'matches': matches,
                    'data_type': type(data).__name__,
                    'sample': str(data)[:300] + "..." if len(str(data)) > 300 else str(data)
                },
                'relevance_score': relevance_score,
                'summary': summary,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"JSON analysis error: {e}")
            return {
                'found_data': {},
                'relevance_score': 0,
                'summary': f'Error reading JSON: {str(e)}',
                'file_path': file_path
            }
    
    def _analyze_text(self, file_path: str, search_terms: List[str], question: str) -> Dict:
        """Analyze text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            matches = []
            relevance_score = 0
            
            content_lower = content.lower()
            for term in search_terms:
                term_lower = term.lower()
                if term_lower in content_lower:
                    # Find all occurrences
                    start = 0
                    while True:
                        pos = content_lower.find(term_lower, start)
                        if pos == -1:
                            break
                        
                        # Extract context
                        context_start = max(0, pos - 100)
                        context_end = min(len(content), pos + len(term) + 100)
                        context = content[context_start:context_end]
                        
                        matches.append({
                            'search_term': term,
                            'position': pos,
                            'context': context
                        })
                        relevance_score += 1
                        start = pos + 1
            
            summary = f"Text file with {len(matches)} matches" if matches else "Text file with no matches"
            
            return {
                'found_data': {
                    'matches': matches,
                    'total_length': len(content),
                    'sample': content[:500] + "..." if len(content) > 500 else content
                },
                'relevance_score': relevance_score,
                'summary': summary,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            return {
                'found_data': {},
                'relevance_score': 0,
                'summary': f'Error reading text: {str(e)}',
                'file_path': file_path
            }
    
    def _generate_csv_summary(self, found_data: Dict, relevance_score: int) -> str:
        """Generate summary for CSV analysis"""
        if relevance_score == 0:
            return f"CSV file with {found_data['total_rows']} rows, no relevant data found"
        
        summary_parts = [f"CSV file with {found_data['total_rows']} rows"]
        
        if found_data['matching_columns']:
            summary_parts.append(f"relevant columns: {', '.join(found_data['matching_columns'])}")
        
        if found_data['matching_data']:
            total_matches = sum(item['matches'] for item in found_data['matching_data'])
            summary_parts.append(f"{total_matches} data matches found")
        
        if found_data.get('filtered_data'):
            summary_parts.append(f"{found_data['filtered_count']} filtered results")
        
        return ", ".join(summary_parts)
    
    def _build_comprehensive_analysis(self, question: str, file_analyses: List[Dict], 
                                    all_found_data: List[Dict], search_terms: List[str]) -> str:
        """Build comprehensive analysis for AI model consumption"""
        
        if not all_found_data:
            return f"""
QUESTION: {question}
SEARCH TERMS: {', '.join(search_terms)}
FILES ANALYZED: {len(file_analyses)}
RESULT: No relevant data found in any attached files.

The user asked about: {question}
We searched for: {', '.join(search_terms)}
Files checked: {len(file_analyses)} files
Conclusion: No matching data found. Please provide a helpful response explaining this and suggest alternatives.
            """.strip()
        
        # Build context for AI
        analysis_parts = [
            f"QUESTION: {question}",
            f"SEARCH TERMS: {', '.join(search_terms)}",
            f"FILES WITH RELEVANT DATA: {len(all_found_data)}/{len(file_analyses)}",
            "",
            "FOUND DATA:"
        ]
        
        for i, data in enumerate(all_found_data, 1):
            analysis_parts.append(f"\n{i}. FILE: {data['file_name']} ({data['file_type']})")
            analysis_parts.append(f"   RELEVANCE: {data['relevance_score']} points")
            analysis_parts.append(f"   SUMMARY: {data['summary']}")
            
            # Add specific data examples
            file_data = data['data']
            if isinstance(file_data, dict):
                if 'matching_columns' in file_data and file_data['matching_columns']:
                    analysis_parts.append(f"   MATCHING COLUMNS: {', '.join(file_data['matching_columns'])}")
                
                if 'filtered_data' in file_data and file_data['filtered_data']:
                    analysis_parts.append(f"   FILTERED RESULTS: {len(file_data['filtered_data'])} rows")
                    analysis_parts.append(f"   SAMPLE DATA: {json.dumps(file_data['filtered_data'][:3], indent=2)}")
                
                elif 'matching_data' in file_data and file_data['matching_data']:
                    analysis_parts.append("   MATCHING DATA:")
                    for match in file_data['matching_data'][:2]:  # Show top 2 matches
                        analysis_parts.append(f"     - {match['search_term']} in column '{match['column']}': {match['matches']} matches")
        
        analysis_parts.extend([
            "",
            "INSTRUCTION: Use this data to provide a comprehensive answer to the user's question. Reference the specific files and data found."
        ])
        
        return "\n".join(analysis_parts)
    
    def get_rag_context(self, question: str, file_names: List[str]) -> Dict:
        """
        Get RAG context for a question from specified files
        
        Args:
            question: User question
            file_names: List of file names to search in
            
        Returns:
            RAG context with relevant information
        """
        return self.rag_service.get_context_for_question(question, file_names)