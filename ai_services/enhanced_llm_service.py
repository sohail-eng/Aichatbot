"""
Enhanced LLM Service

This service integrates with the File Analyzer to provide intelligent, context-aware
responses based on data found in uploaded files. It handles both data-found and
data-not-found scenarios with appropriate LLM responses.
"""

import logging
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from .foundry_service import FoundryService
from .file_analyzer import FileAnalyzer
from .rag_service import RAGService

logger = logging.getLogger('ai_services')

class EnhancedLLMService:
    """
    Enhanced LLM service that provides intelligent responses based on file analysis
    
    This service combines file analysis with LLM generation to provide:
    1. Data-driven answers when information is found in files
    2. Helpful responses when no relevant data is found
    3. Context-aware explanations and insights
    """
    
    def __init__(self):
        self.llm_service = FoundryService()
        self.file_analyzer = FileAnalyzer()
        self.rag_service = RAGService()
    
    async def process_question_with_files(self, question: str, attached_files: List[Dict]) -> Dict:
        """
        Process a user question with attached files using intelligent analysis
        
        Args:
            question: User's question
            attached_files: List of attached file information
            
        Returns:
            Dict containing the complete response with analysis and LLM answer
        """
        try:
            logger.info(f"Processing question with {len(attached_files)} attached files")
            
            # Step 1: Get file names for RAG
            file_names = [file_info.get('name') for file_info in attached_files]
            
            # Step 2: Analyze files for relevant data (legacy + RAG enhanced)
            # This will also process files for RAG system
            file_analysis = await self.file_analyzer.analyze_question_with_files_async(
                question, attached_files
            )
            
            if not file_analysis['success']:
                return {
                    'success': False,
                    'error': file_analysis['error'],
                    'response': 'Sorry, I encountered an error analyzing your files.'
                }
            
            # Step 3: Get RAG context (after files are processed for RAG)
            rag_context = self.rag_service.get_context_for_question(question, file_names)
            
            # Step 2: Generate LLM response based on analysis and RAG context
            llm_response = await self._generate_llm_response(question, file_analysis, rag_context)
            
            # Step 3: Compile final response
            final_response = self._compile_final_response(file_analysis, llm_response, rag_context)
            
            return {
                'success': True,
                'response': final_response,
                'file_analysis': file_analysis,
                'llm_response': llm_response,
                'rag_context': rag_context,
                'metadata': {
                    'files_analyzed': file_analysis['files_analyzed'],
                    'data_found': len(file_analysis['found_data']) > 0,
                    'search_keywords': file_analysis['search_keywords'],
                    'rag_enhanced': rag_context.get('success', False) if rag_context else False,
                    'rag_sources': len(rag_context.get('sources', [])) if rag_context else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing question with files: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Sorry, I encountered an error processing your question.'
            }
    
    async def _generate_llm_response(self, question: str, file_analysis: Dict, rag_context: Dict = None) -> str:
        """
        Generate LLM response based on file analysis and RAG context
        
        Args:
            question: User's question
            file_analysis: Results from file analysis
            rag_context: RAG context with relevant chunks
            
        Returns:
            LLM-generated response
        """
        try:
            found_data = file_analysis['found_data']
            search_keywords = file_analysis['search_keywords']
            
            # Use RAG context if available
            if rag_context and rag_context.get('success'):
                return await self._generate_rag_enhanced_response(question, file_analysis, rag_context)
            elif not found_data:
                # No data found - generate helpful response
                return await self._generate_no_data_response(question, file_analysis)
            else:
                # Data found - generate data-driven response
                return await self._generate_data_driven_response(question, file_analysis)
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return f"Sorry, I encountered an error generating a response: {str(e)}"
    
    async def _generate_no_data_response(self, question: str, file_analysis: Dict) -> str:
        """
        Generate response when no relevant data is found in files
        
        Args:
            question: User's question
            file_analysis: File analysis results
            
        Returns:
            Helpful response explaining no data was found
        """
        try:
            # Create prompt for no-data scenario
            prompt = f"""
            The user asked: "{question}"
            
            I searched through {file_analysis['files_analyzed']} attached files but could not find any relevant data.
            
            Search keywords used: {', '.join(file_analysis['search_keywords'])}
            
            Please provide a helpful response that:
            1. Acknowledges that no relevant data was found
            2. Explains what was searched for
            3. Suggests alternative approaches or questions
            4. Maintains a helpful and professional tone
            
            Keep the response concise but informative.
            """
            
            # Generate response using LLM
            response_chunks = []
            async for chunk in self.llm_service.generate_streaming_response(prompt):
                response_chunks.append(chunk)
            
            return ''.join(response_chunks)
            
        except Exception as e:
            logger.error(f"Error generating no-data response: {e}")
            return f"I searched through your attached files but couldn't find any data related to '{question}'. The search used keywords: {', '.join(file_analysis['search_keywords'])}. You might want to try rephrasing your question or checking if the relevant information exists in your files."
    
    async def _generate_data_driven_response(self, question: str, file_analysis: Dict) -> str:
        """
        Generate response when relevant data is found in files
        
        Args:
            question: User's question
            file_analysis: File analysis results with found data
            
        Returns:
            Data-driven LLM response
        """
        try:
            # Create comprehensive prompt with found data
            prompt = self._build_data_driven_prompt(question, file_analysis)
            
            # Generate response using LLM
            response_chunks = []
            async for chunk in self.llm_service.generate_streaming_response(prompt):
                response_chunks.append(chunk)
            
            return ''.join(response_chunks)
            
        except Exception as e:
            logger.error(f"Error generating data-driven response: {e}")
            return f"I found some relevant data in your files related to '{question}', but encountered an error generating a detailed response. Here's what I found: {file_analysis['comprehensive_analysis']}"
    
    def _build_data_driven_prompt(self, question: str, file_analysis: Dict) -> str:
        """
        Build a comprehensive prompt for data-driven responses
        
        Args:
            question: User's question
            file_analysis: File analysis results
            
        Returns:
            Formatted prompt for LLM
        """
        prompt = f"""
        The user asked: "{question}"
        
        I found relevant data in the attached files. Here's the analysis:
        
        {file_analysis['comprehensive_analysis']}
        
        Please provide a comprehensive answer that:
        1. Directly addresses the user's question
        2. References specific data found in the files
        3. Mentions which files contained the relevant information
        4. Provides insights and explanations based on the found data
        5. Maintains a professional and helpful tone
        
        Structure your response to be clear and easy to understand.
        Include specific examples from the data when relevant.
        """
        
        return prompt
    
    async def _generate_rag_enhanced_response(self, question: str, file_analysis: Dict, rag_context: Dict) -> str:
        """
        Generate RAG-enhanced response using retrieved context
        
        Args:
            question: User's question
            file_analysis: File analysis results
            rag_context: RAG context with relevant chunks
            
        Returns:
            RAG-enhanced LLM response
        """
        try:
            # Build RAG-enhanced prompt
            prompt = self._build_rag_enhanced_prompt(question, file_analysis, rag_context)
            
            # Generate response using LLM
            response_chunks = []
            async for chunk in self.llm_service.generate_streaming_response(prompt):
                response_chunks.append(chunk)
            
            return ''.join(response_chunks)
            
        except Exception as e:
            logger.error(f"Error generating RAG-enhanced response: {e}")
            return f"I found relevant information in your files, but encountered an error generating a detailed response. Here's what I found: {rag_context.get('context', '')[:500]}..."
    
    def _build_rag_enhanced_prompt(self, question: str, file_analysis: Dict, rag_context: Dict) -> str:
        """
        Build RAG-enhanced prompt with retrieved context
        
        Args:
            question: User's question
            file_analysis: File analysis results
            rag_context: RAG context
            
        Returns:
            Formatted prompt for LLM
        """
        context = rag_context.get('context', '')
        sources = rag_context.get('sources', [])
        
        prompt = f"""
You are an AI assistant with access to relevant information from the user's files. Use the following context to answer the user's question accurately and comprehensively.

USER QUESTION: {question}

RELEVANT CONTEXT FROM FILES:
{context}

SOURCE INFORMATION:
"""
        
        for i, source in enumerate(sources, 1):
            prompt += f"{i}. File: {source['file_name']} (Type: {source['chunk_type']}, Relevance: {source['relevance_score']:.2f})\n"
        
        prompt += f"""

INSTRUCTIONS:
1. Answer the user's question based on the provided context
2. Reference specific information from the files when possible
3. If the context doesn't fully answer the question, acknowledge what you can answer and what might need additional information
4. Be accurate and cite your sources
5. Provide a comprehensive and helpful response

Please provide your answer:
"""
        
        return prompt
    
    def _compile_final_response(self, file_analysis: Dict, llm_response: str, rag_context: Dict = None) -> str:
        """
        Compile the final response combining file analysis, RAG context, and LLM output
        
        Args:
            file_analysis: Results from file analysis
            llm_response: Response from LLM
            rag_context: RAG context information
            
        Returns:
            Final formatted response
        """
        try:
            found_data = file_analysis['found_data']
            
            if not found_data:
                # No data found - start with clear indication
                header = "❌ **No relevant data found in attached files**\n\n"
                body = llm_response
            else:
                # Data found - start with success indication
                header = "✅ **Data found in attached files**\n\n"
                body = llm_response
            
            # Add RAG enhancement indicator if available
            if rag_context and rag_context.get('success'):
                header = "🚀 **RAG-Enhanced Analysis**\n\n"
                body = llm_response
            
            # Add file analysis summary
            analysis_summary = f"\n\n---\n\n**File Analysis Summary:**\n"
            analysis_summary += f"• Files analyzed: {file_analysis['files_analyzed']}\n"
            analysis_summary += f"• Search keywords: {', '.join(file_analysis['search_keywords'])}\n"
            
            if found_data:
                analysis_summary += f"• Relevant data found: Yes\n"
                analysis_summary += f"• Data instances: {len(found_data)}\n"
            else:
                analysis_summary += f"• Relevant data found: No\n"
            
            # Add RAG information if available
            if rag_context and rag_context.get('success'):
                analysis_summary += f"• RAG-enhanced: Yes\n"
                analysis_summary += f"• Context sources: {rag_context.get('total_sources', 0)}\n"
                analysis_summary += f"• Average relevance: {rag_context.get('average_relevance', 0):.2f}\n"
            
            return header + body + analysis_summary
            
        except Exception as e:
            logger.error(f"Error compiling final response: {e}")
            return llm_response
    
    async def generate_streaming_response(self, question: str, attached_files: List[Dict]) -> AsyncGenerator[str, None]:
        """
        Generate streaming response for real-time chat
        
        Args:
            question: User's question
            attached_files: List of attached files
            
        Yields:
            Response chunks for streaming
        """
        try:
            # First yield a status update
            yield "🔍 **Analyzing attached files...**\n\n"
            
            # Process the question with files
            result = await self.process_question_with_files(question, attached_files)
            
            if not result['success']:
                yield f"❌ **Error:** {result['error']}"
                return
            
            # Yield the complete response
            yield result['response']
            
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"❌ **Error:** Sorry, I encountered an error processing your request: {str(e)}"
    
    def get_processing_status(self, step: str) -> str:
        """
        Get status message for different processing steps
        
        Args:
            step: Current processing step
            
        Returns:
            Status message
        """
        status_messages = {
            'analyzing': "🔍 Analyzing attached files...",
            'searching': "🔎 Searching for relevant data...",
            'processing': "⚙️ Processing found data...",
            'generating': "🤖 Generating AI response...",
            'compiling': "📝 Compiling final response...",
            'thinking': "💭 Thinking..."
        }
        
        return status_messages.get(step, "💭 Processing...")
