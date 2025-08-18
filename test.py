import logging
import re
import json
import requests

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dynamic_table_lookup")

class DynamicTableLookup:
    def __init__(self, api_key="AIzaSyA7vBmqL-zZpJrvNoijDzHTvYaEeNctEig"):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        # Sample data - 50 records
        self.data = [
            {'Azeem': '1'}, {'Sohail': '45'}, {'Ahmad': '1A'}, {'Sara': '2B'}, {'Ali': '33'},
            {'Fatima': '7C'}, {'Usman': '12'}, {'Hina': '8D'}, {'Bilal': '21'}, {'Zara': '5E'},
            {'Omar': '14'}, {'Nida': '9F'}, {'Imran': '27'}, {'Sadia': '3G'}, {'Kashif': '18'},
            {'Rabia': '6H'}, {'Tariq': '29'}, {'Ayesha': '4I'}, {'Hassan': '11'}, {'Mariam': '10J'},
            {'Noman': '31'}, {'Sana': '13K'}, {'Junaid': '24'}, {'Lubna': '15L'}, {'Faisal': '38'},
            {'Samina': '16M'}, {'Danish': '41'}, {'Uzma': '17N'}, {'Shahid': '22'}, {'Mehwish': '19O'},
            {'Rizwan': '25'}, {'Bushra': '20P'}, {'Adnan': '36'}, {'Hafsa': '23Q'}, {'Saad': '28'},
            {'Iqra': '26R'}, {'Yasir': '30'}, {'Farah': '32S'}, {'Asad': '34'}, {'Sumbal': '35T'},
            {'Naveed': '37'}, {'Hira': '39U'}, {'Waqar': '40'}, {'Shazia': '42V'}, {'Kamran': '43'},
            {'Noreen': '44W'}, {'Salman': '46'}, {'Sidra': '47X'}, {'Zeeshan': '48'}, {'Aqsa': '49Y'},
            {'Talha': '50'}
        ]
        
        # Convert to a more searchable format
        self.name_to_id = {}
        for record in self.data:
            for name, id_val in record.items():
                self.name_to_id[name.lower()] = id_val
    
    def generate_search_code(self, user_query):
        """Generate Python code to search the data based on user query"""
        
        system_prompt = """You are a Python code generator. Generate ONLY executable Python code for finding IDs from a dataset.

The data variable is available as: data = [{'Azeem': '1'}, {'Sohail': '45'}, {'Ahmad': '1A'}, ...]

IMPORTANT RULES:
1. Generate ONLY Python code - no explanations, no markdown, no comments
2. Use the existing 'data' variable - do NOT redefine it
3. Store final result in variable called 'result'
4. Handle case-insensitive search
5. For multiple names, return comma-separated results

EXAMPLES:

For single name query:
result = next((list(item.values())[0] for item in data if 'sohail' in str(item).lower()), "Not found")

For multiple names query:
names = ['sohail', 'sara', 'ali']
results = []
for name in names:
    found = next((f"{name.title()}: {list(item.values())[0]}" for item in data if name.lower() in str(item).lower()), f"{name.title()}: Not found")
    results.append(found)
result = ", ".join(results)

Generate code for the query below - ONLY Python code, nothing else:"""

        full_prompt = f"{system_prompt}\n\nGenerate Python code for this query: {user_query}"

        try:
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": full_prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            
            if 'candidates' in response_data and response_data['candidates']:
                generated_code = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # Clean the generated code
                generated_code = self.clean_generated_code(generated_code)
                logger.info(f"Generated code: {generated_code}")
                return generated_code
            else:
                logger.error("No candidates in response")
                return None
                
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return None
    
    def clean_generated_code(self, code):
        """Clean and validate the generated code"""
        # Remove markdown code blocks if present
        code = re.sub(r'```python\s*', '', code)
        code = re.sub(r'```\s*$', '', code)
        code = code.strip()
        
        # Split into lines and filter
        lines = code.split('\n')
        python_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Skip lines that redefine data variable or print it
            if line.startswith('data =') or 'print(data)' in line:
                continue
            # Skip explanatory text
            if line.startswith('Here') or line.startswith('This') or line.startswith('The'):
                continue
            # Keep lines that have actual Python logic
            if any(keyword in line for keyword in ['result', 'names', 'found', 'for ', 'if ', '=', 'next(', 'append', 'items()', 'keys()', 'values()']):
                python_lines.append(line)
        
        cleaned_code = '\n'.join(python_lines)
        
        # If the code doesn't assign to result, wrap it
        if 'result =' not in cleaned_code and cleaned_code and not cleaned_code.startswith('result'):
            # Check if it's a simple expression
            if '=' not in cleaned_code:
                cleaned_code = f"result = {cleaned_code}"
        
        return cleaned_code
    
    def execute_search_code(self, code):
        """Safely execute the generated code"""
        if not code:
            return "Error: No code generated"
        
        try:
            # Validate the code first
            compile(code, '<string>', 'exec')
            
            # Create a safe execution environment
            safe_globals = {
                'data': self.data,
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'list': list,
                    'dict': dict,
                    'range': range,
                    'enumerate': enumerate,
                    'next': next,
                    'zip': zip,
                    'any': any,
                    'all': all,
                    'sorted': sorted,
                    'print': print
                }
            }
            safe_locals = {}
            
            # Execute the code
            exec(code, safe_globals, safe_locals)
            
            # Try to get the result
            if 'result' in safe_locals:
                return str(safe_locals['result'])
            elif 'result' in safe_globals:
                return str(safe_globals['result'])
            else:
                return "Code executed but no result variable found"
                
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return f"Syntax error: {str(e)}"
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            return f"Execution error: {str(e)}"
    
    def fallback_search(self, query):
        """Fallback method using direct string matching"""
        query_lower = query.lower()
        results = []
        
        # Extract potential names from query
        words = re.findall(r'\b[a-zA-Z]+\b', query)
        
        for word in words:
            word_lower = word.lower()
            if word_lower in self.name_to_id:
                results.append(f"{word}: {self.name_to_id[word_lower]}")
        
        if results:
            return ", ".join(results)
        else:
            return "No matching names found"
    
    def process_query(self, user_query):
        """Main method to process user queries"""
        print(f"\n🔍 Processing query: '{user_query}'")
        
        # Step 1: Generate search code
        print("📝 Generating search code...")
        generated_code = self.generate_search_code(user_query)
        
        if generated_code:
            print(f"✅ Generated code:\n{generated_code}\n")
            
            # Step 2: Execute the code
            print("⚡ Executing search code...")
            result = self.execute_search_code(generated_code)
            print(f"🎯 Result: {result}")
            
            # If execution failed, use fallback
            if "error" in result.lower() or "not found" in result.lower():
                print("🔄 Using fallback search...")
                fallback_result = self.fallback_search(user_query)
                print(f"🎯 Fallback result: {fallback_result}")
                return fallback_result
            
            return result
        else:
            print("❌ Code generation failed, using fallback...")
            return self.fallback_search(user_query)

def main():
    """Main function to run the interactive system"""
    lookup_system = DynamicTableLookup()
    
    print("🚀 Dynamic Table Lookup System Initialized!")
    print("🤖 Now powered by Google Gemini 2.0 Flash!")
    print("💡 Ask questions like:")
    print("   - 'What is the ID of Sohail?'")
    print("   - 'Find the ID for Sara and Ali'")
    print("   - 'Hey what's the ID of Sidra?'")
    print("   - Type 'quit' to exit")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n🤖 Your query: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            result = lookup_system.process_query(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()