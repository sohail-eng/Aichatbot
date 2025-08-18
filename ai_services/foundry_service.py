# ai_services/llama_service.py
import httpx
import json
import logging
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from django.conf import settings

logger = logging.getLogger('ai_services')

class FoundryService:
    def __init__(self):
        self.api_url = settings.AI_CONFIG['LLAMA_API_URL']
        self.model_name = settings.AI_CONFIG['MODEL_NAME']
        self.max_tokens = settings.AI_CONFIG['MAX_TOKENS']
        self.temperature = settings.AI_CONFIG['TEMPERATURE']

    async def generate_streaming_response(self, prompt: str, context: Optional[List[Dict]] = None) -> AsyncGenerator[str, None]:
        """Generate a streaming response from AI service (OpenAI-compatible or Google AI Studio)"""
        messages = self._build_openai_messages(prompt, context)
        
        # Check if this is Google AI Studio
        if 'generativelanguage.googleapis.com' in self.api_url:
            payload = self._build_google_ai_payload(messages)
            api_key = settings.AI_CONFIG.get('API_KEY', '')
            # Google AI Studio uses API key as query parameter, not Authorization header
            url = f"{self.api_url}?key={api_key}"
            headers = {}
            is_google_ai = True
        else:
            # OpenAI-compatible format
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": True
            }
            headers = {}
            url = self.api_url
            is_google_ai = False
        
        logger.info(f"Sending streaming request to AI service with model: {self.model_name}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if is_google_ai:
                    # Google AI Studio - non-streaming response
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if 'candidates' in data and data['candidates']:
                            candidate = data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                for part in candidate['content']['parts']:
                                    if 'text' in part and part['text']:
                                        # Simulate streaming by yielding the text in chunks
                                        text = part['text']
                                        chunk_size = 50  # Yield in chunks of 50 characters
                                        for i in range(0, len(text), chunk_size):
                                            yield text[i:i + chunk_size]
                                            await asyncio.sleep(0.01)  # Small delay to simulate streaming
                    else:
                        error_response = response.text
                        logger.error(f"Google AI service error: {response.status_code} - {error_response}")
                        yield "Error: AI service returned an error. Please try again later."
                else:
                    # OpenAI-compatible streaming format
                    async with client.stream("POST", url, json=payload, headers=headers) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    line = line[6:]
                                if line.strip() and line.strip() != "[DONE]":
                                    try:
                                        data = json.loads(line)
                                        delta = data.get("choices", [{}])[0].get("delta", {})
                                        content = delta.get("content")
                                        if content:
                                            yield content
                                    except Exception as e:
                                        logger.error(f"OpenAI streaming parse error: {e} | line: {line}")
                        else:
                            error_response = await response.aread()
                            logger.error(f"AI service error: {response.status_code} - {error_response}")
                            yield "Error: AI service returned an error. Please try again later."
        except httpx.ConnectError:
            logger.error(f"Connection error: Unable to connect to AI service at {self.api_url}")
            yield "I'm currently unable to connect to my AI service. Please check your configuration and API key. For now, I can help you with file uploads and database connections, but I won't be able to provide AI-generated responses."
        except httpx.TimeoutException:
            logger.error("Timeout error: AI service request timed out")
            yield "The AI service is taking too long to respond. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error in AI service: {e}")
            yield "An unexpected error occurred while connecting to the AI service. Please try again later."

    def _build_openai_messages(self, prompt: str, context: Optional[List[Dict]] = None) -> List[Dict]:
        """Build OpenAI-style messages"""
        messages = [
            {"role": "system", "content": (
                "You are a helpful AI assistant specialized in data analysis and file processing. "
                "You can help users with: analyzing uploaded files (CSV, Excel, text files), writing and explaining SQL queries, "
                "data interpretation and insights, and general questions and follow-ups. Always provide clear, concise, and helpful responses."
            )}
        ]
        if context:
            for msg in context[-10:]:
                role = "user" if msg['type'] == 'user' else "assistant"
                messages.append({"role": role, "content": msg['content']})
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def _build_google_ai_payload(self, messages: List[Dict]) -> Dict:
        """Build Google AI Studio payload"""
        # Convert OpenAI format to Google AI format
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                # Google AI doesn't have system messages, so we'll prepend to the first user message
                continue
            elif msg['role'] == 'user':
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg['content']}]
                })
            elif msg['role'] == 'assistant':
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg['content']}]
                })
        
        # Add system message to the first user message if it exists
        if messages and messages[0]['role'] == 'system':
            if contents and contents[0]['role'] == 'user':
                contents[0]['parts'][0]['text'] = messages[0]['content'] + "\n\n" + contents[0]['parts'][0]['text']
        
        return {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
            }
        }

    # Example for file analysis using streaming
    async def analyze_file_content(self, file_content: str, file_type: str, user_question: str = "") -> AsyncGenerator[str, None]:
        prompt = (
            f"I have a {file_type} file with the following content:\n\n"
            f"{file_content[:5000]}\n\n"
            f"{'User question: ' + user_question if user_question else 'Please provide an analysis of this data.'}\n"
            "Please analyze this data and provide insights."
        )
        async for chunk in self.generate_streaming_response(prompt):
            yield chunk

    # Add similar streaming wrappers for SQL and result explanations as needed
    
    async def explain_query_results(self, query: str, results: List[Dict]) -> str:
        """Explain SQL query results"""
        prompt = f"""I executed this SQL query: {query}
        
The results are: {results[:10]}  # Limit to first 10 results
        
Please explain what this query does and what the results mean."""
        
        response_chunks = []
        async for chunk in self.generate_streaming_response(prompt):
            response_chunks.append(chunk)
        return ''.join(response_chunks)
    
    async def generate_sql_query(self, natural_language: str, schema: Dict) -> str:
        """Generate SQL query from natural language"""
        schema_summary = self._format_schema_summary(schema)
        prompt = f"""Given this database schema:
{schema_summary}

Please generate a SQL query for: {natural_language}

Return only the SQL query, no explanations."""
        
        response_chunks = []
        async for chunk in self.generate_streaming_response(prompt):
            response_chunks.append(chunk)
        return ''.join(response_chunks)
    
    def _format_schema_summary(self, schema: Dict) -> str:
        """Format database schema for display"""
        if not schema:
            return "No schema information available"
        
        summary = "Database Tables:\n"
        for table_name, columns in schema.items():
            summary += f"\n{table_name}:\n"
            for column, data_type in columns.items():
                summary += f"  - {column} ({data_type})\n"
        
        return summary
    
    def health_check(self) -> bool:
        """Check if the AI service is available"""
        try:
            import httpx
            if 'generativelanguage.googleapis.com' in self.api_url:
                # For Google AI Studio, we'll test with a simple request
                api_key = settings.AI_CONFIG.get('API_KEY', '')
                if not api_key:
                    return False
                test_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro?key={api_key}"
                response = httpx.get(test_url, timeout=5.0)
                return response.status_code == 200
            else:
                # For OpenAI-compatible APIs
                response = httpx.get(self.api_url.replace('/chat/completions', '/models'), timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False