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
        self.api_key = settings.AI_CONFIG.get('API_KEY', '')

    async def generate_streaming_response(self, prompt: str, context: Optional[List[Dict]] = None) -> AsyncGenerator[str, None]:
        """Generate a streaming response from AI service"""
        messages = self._build_openai_messages(prompt, context)
        
        # Detect service type
        service_type = self._detect_service_type()
        
        if service_type == 'google':
            async for chunk in self._handle_google_ai(messages):
                yield chunk
        elif service_type == 'qwen':
            async for chunk in self._handle_qwen_api(messages):
                yield chunk
        else:
            # Default OpenAI-compatible
            async for chunk in self._handle_openai_compatible(messages):
                yield chunk

    def _detect_service_type(self) -> str:
        """Detect which AI service we're using based on URL and model name"""
        if 'generativelanguage.googleapis.com' in self.api_url:
            return 'google'
        elif 'qwen' in self.model_name.lower() or 'dashscope' in self.api_url:
            return 'qwen'
        else:
            return 'openai'

    async def _handle_google_ai(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Handle Google AI Studio requests"""
        payload = self._build_google_ai_payload(messages)
        url = f"{self.api_url}?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and data['candidates']:
                        candidate = data['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            for part in candidate['content']['parts']:
                                if 'text' in part and part['text']:
                                    # Simulate streaming
                                    text = part['text']
                                    chunk_size = 50
                                    for i in range(0, len(text), chunk_size):
                                        yield text[i:i + chunk_size]
                                        await asyncio.sleep(0.01)
                else:
                    logger.error(f"Google AI error: {response.status_code} - {response.text}")
                    yield f"Error: Google AI service returned {response.status_code}"
        except Exception as e:
            logger.error(f"Google AI exception: {e}")
            yield f"Error connecting to Google AI: {str(e)}"

    async def _handle_qwen_api(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Handle Qwen/Alibaba Cloud DashScope API requests"""
        # Try different Qwen API endpoints
        endpoints_to_try = [
            self.api_url,
            self.api_url.rstrip('/') + '/v1/chat/completions',
            self.api_url.rstrip('/') + '/chat/completions',
            self.api_url.rstrip('/') + '/api/v1/chat/completions',
            self.api_url.rstrip('/') + '/v1/services/aigc/text-generation/generation'  # Alibaba DashScope
        ]
        
        logger.info(f"Trying Qwen connection - Model: {self.model_name}")
        
        # Try different endpoint formats
        for endpoint in endpoints_to_try:
            logger.info(f"Trying endpoint: {endpoint}")
            
            # Try different payload formats
            payloads_to_try = [
                # Standard OpenAI format
                {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": True
                },
                # Alibaba DashScope format
                {
                    "model": self.model_name,
                    "input": {
                        "messages": messages
                    },
                    "parameters": {
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "incremental_output": True
                    }
                },
                # Simple prompt format
                {
                    "model": self.model_name,
                    "prompt": self._convert_messages_to_prompt(messages),
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": True
                }
            ]
            
            for payload in payloads_to_try:
                # Try different auth header formats
                headers_variants = [
                    {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}'
                    } if self.api_key else {'Content-Type': 'application/json'},
                    {
                        'Content-Type': 'application/json',
                        'X-API-Key': self.api_key
                    } if self.api_key else {'Content-Type': 'application/json'},
                    {
                        'Content-Type': 'application/json',
                        'Api-Key': self.api_key
                    } if self.api_key else {'Content-Type': 'application/json'},
                ]
                
                for headers in headers_variants:
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            logger.debug(f"Trying payload: {json.dumps(payload, indent=2)}")
                            
                            async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                                logger.info(f"Qwen response status: {response.status_code}")
                                
                                if response.status_code == 200:
                                    # Success! Parse the streaming response
                                    async for chunk in self._parse_qwen_streaming_response(response):
                                        yield chunk
                                    return  # Exit after successful response
                                elif response.status_code == 405:
                                    logger.debug(f"Method not allowed for {endpoint}")
                                    break  # Try next endpoint
                                else:
                                    error_response = await response.aread()
                                    logger.warning(f"Qwen API error {response.status_code}: {error_response.decode()[:200]}")
                                    
                    except httpx.ConnectError:
                        logger.debug(f"Connection failed for {endpoint}")
                        break  # Try next endpoint
                    except Exception as e:
                        logger.debug(f"Request failed for {endpoint}: {e}")
                        continue  # Try next header format
        
        # If all attempts failed
        yield f"Unable to connect to Qwen service. Please verify:\n1. API URL: {self.api_url}\n2. Model name: {self.model_name}\n3. API key is correct\n4. Service supports POST requests\n\nCommon Qwen endpoints:\n- /v1/chat/completions\n- /chat/completions\n- /api/v1/chat/completions"

    async def _parse_qwen_streaming_response(self, response) -> AsyncGenerator[str, None]:
        """Parse streaming response from Qwen API"""
        async for line in response.aiter_lines():
            if not line.strip():
                continue
                
            # Handle different streaming formats
            if line.startswith("data: "):
                line = line[6:]
            
            if line.strip() in ["[DONE]", "data: [DONE]"]:
                break
                
            try:
                data = json.loads(line)
                logger.debug(f"Qwen chunk: {data}")
                
                # Try different response formats
                content = None
                
                # Standard OpenAI format
                if "choices" in data:
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                
                # Alibaba DashScope format
                elif "output" in data:
                    output = data.get("output", {})
                    if "text" in output:
                        content = output["text"]
                    elif "content" in output:
                        content = output["content"]
                
                # Another possible format
                elif "text" in data:
                    content = data["text"]
                
                if content:
                    yield content
                    
            except json.JSONDecodeError as e:
                logger.error(f"Qwen JSON parse error: {e} | line: {line}")
                # Sometimes response might not be JSON
                if line.strip() and not line.startswith("{"):
                    yield line.strip()

    def _convert_messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert OpenAI messages format to a simple prompt"""
        prompt_parts = []
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        return "\n\n".join(prompt_parts)

    async def _handle_openai_compatible(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Handle OpenAI-compatible API requests"""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", self.api_url, json=payload, headers=headers) as response:
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
                                    logger.error(f"OpenAI parse error: {e} | line: {line}")
                    else:
                        error_response = await response.aread()
                        logger.error(f"OpenAI API error: {response.status_code} - {error_response}")
                        yield f"Error: OpenAI-compatible service returned {response.status_code}"
        except Exception as e:
            logger.error(f"OpenAI-compatible error: {e}")
            yield f"Error with OpenAI-compatible service: {str(e)}"

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
        contents = []
        system_message = ""
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            elif msg['role'] == 'user':
                content = msg['content']
                if system_message:
                    content = system_message + "\n\n" + content
                    system_message = ""
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif msg['role'] == 'assistant':
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg['content']}]
                })
        
        return {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
            }
        }

    async def analyze_file_content(self, file_content: str, file_type: str, user_question: str = "") -> AsyncGenerator[str, None]:
        prompt = (
            f"I have a {file_type} file with the following content:\n\n"
            f"{file_content[:5000]}\n\n"
            f"{'User question: ' + user_question if user_question else 'Please provide an analysis of this data.'}\n"
            "Please analyze this data and provide insights."
        )
        async for chunk in self.generate_streaming_response(prompt):
            yield chunk

    async def explain_query_results(self, query: str, results: List[Dict]) -> str:
        """Explain SQL query results"""
        prompt = f"""I executed this SQL query: {query}
        
The results are: {results[:10]}
        
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
            service_type = self._detect_service_type()
            
            if service_type == 'google':
                if not self.api_key:
                    return False
                test_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro?key={self.api_key}"
                response = httpx.get(test_url, timeout=5.0)
                return response.status_code == 200
            else:
                # For Qwen and OpenAI-compatible APIs
                headers = {}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                
                # Try to get models endpoint or make a simple request
                test_urls = [
                    self.api_url.replace('/chat/completions', '/models'),
                    self.api_url.replace('/v1/chat/completions', '/v1/models'),
                    self.api_url  # Fallback to the main URL
                ]
                
                for test_url in test_urls:
                    try:
                        response = httpx.get(test_url, headers=headers, timeout=5.0)
                        if response.status_code in [200, 404]:  # 404 might be OK if endpoint exists but route doesn't
                            return True
                    except:
                        continue
                return False
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def test_connection(self) -> Dict:
        """Test connection and return detailed info for debugging"""
        service_type = self._detect_service_type()
        result = {
            'service_type': service_type,
            'api_url': self.api_url,
            'model_name': self.model_name,
            'has_api_key': bool(self.api_key),
            'connection_ok': False,
            'error': None,
            'endpoints_tried': [],
            'successful_endpoint': None
        }
        
        if service_type == 'qwen':
            # Test different Qwen endpoints
            endpoints_to_try = [
                self.api_url,
                self.api_url.rstrip('/') + '/v1/chat/completions',
                self.api_url.rstrip('/') + '/chat/completions',
                self.api_url.rstrip('/') + '/api/v1/chat/completions',
            ]
            
            for endpoint in endpoints_to_try:
                endpoint_result = {'url': endpoint, 'status': None, 'error': None}
                result['endpoints_tried'].append(endpoint_result)
                
                try:
                    headers = {'Content-Type': 'application/json'}
                    if self.api_key:
                        headers['Authorization'] = f'Bearer {self.api_key}'
                    
                    # Simple test payload
                    test_payload = {
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10,
                        "stream": False  # Non-streaming for test
                    }
                    
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(endpoint, json=test_payload, headers=headers)
                        endpoint_result['status'] = response.status_code
                        
                        if response.status_code == 200:
                            result['connection_ok'] = True
                            result['successful_endpoint'] = endpoint
                            endpoint_result['response'] = 'Success'
                            break
                        elif response.status_code == 405:
                            endpoint_result['error'] = 'Method not allowed'
                        else:
                            error_text = response.text[:200]
                            endpoint_result['error'] = f'HTTP {response.status_code}: {error_text}'
                            
                except Exception as e:
                    endpoint_result['error'] = str(e)
        
        else:
            # Test other service types
            try:
                test_prompt = "Hello, please respond with 'Connection successful'"
                response_chunks = []
                async for chunk in self.generate_streaming_response(test_prompt):
                    response_chunks.append(chunk)
                    if len(response_chunks) > 5:  # Don't wait for full response
                        break
                
                response_text = ''.join(response_chunks)
                result['connection_ok'] = len(response_text) > 0 and 'Error' not in response_text
                result['test_response'] = response_text[:100]
                
            except Exception as e:
                result['error'] = str(e)
        
        return result

    async def debug_qwen_request(self, test_message: str = "Hello") -> Dict:
        """Debug a Qwen request step by step"""
        debug_info = {
            'api_url': self.api_url,
            'model_name': self.model_name,
            'has_api_key': bool(self.api_key),
            'attempts': []
        }
        
        messages = [{"role": "user", "content": test_message}]
        
        # Try the most common Qwen endpoints
        endpoints = [
            self.api_url,
            self.api_url.rstrip('/') + '/v1/chat/completions',
            self.api_url.rstrip('/') + '/chat/completions',
        ]
        
        for endpoint in endpoints:
            attempt = {
                'endpoint': endpoint,
                'method': 'POST',
                'status_code': None,
                'headers_sent': {},
                'payload_sent': {},
                'response': None,
                'error': None
            }
            
            try:
                # Standard payload
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": 50,
                    "temperature": 0.7,
                    "stream": False  # Non-streaming for debug
                }
                
                headers = {'Content-Type': 'application/json'}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                
                attempt['payload_sent'] = payload
                attempt['headers_sent'] = {k: v[:20] + '...' if len(str(v)) > 20 else v for k, v in headers.items()}
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    attempt['status_code'] = response.status_code
                    
                    if response.status_code == 200:
                        response_json = response.json()
                        attempt['response'] = 'SUCCESS: ' + str(response_json)[:200]
                        debug_info['attempts'].append(attempt)
                        break
                    else:
                        attempt['response'] = response.text[:300]
                        
            except Exception as e:
                attempt['error'] = str(e)
            
            debug_info['attempts'].append(attempt)
        
        return debug_info
        