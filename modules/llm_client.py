import aiohttp
from config import (LLM_OPTION, BITDEER_AI_BEARER_TOKEN, PROMPT, GEMINI_API_KEY)


class LLMClient:
    """Handles LLM API calls to both Bitdeer AI and Gemini"""
    
    def __init__(self):
        self.llm_option = LLM_OPTION.upper()
        self._setup_api_config()
    
    def _setup_api_config(self):
        """Setup API configuration based on LLM option"""
        if self.llm_option == "BITDEER":
            print("Using Bitdeer AI LLM API...\n")
            self.url = "https://api-inference.bitdeer.ai/v1/chat/completions"
            self.headers = {
                "Authorization": "Bearer " + BITDEER_AI_BEARER_TOKEN,
                "Content-Type": "application/json"
            }
        else:
            print("Using Gemini LLM API...\n")
            self.url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
            self.headers = {'Content-Type': 'application/json'}
    
    def _prepare_request_data(self, message_text):
        """Prepare request data based on LLM option"""
        if self.llm_option == "BITDEER":
            return {
                "model": "deepseek-ai/DeepSeek-V3",
                "messages": [
                    {
                        "role": "system",
                        "content": PROMPT
                    },
                    {
                        "role": "user",
                        "content": message_text
                    }
                ],
                "max_tokens": 1024,
                "temperature": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "top_p": 1,
                "stream": False
            }
        else:
            return {
                "contents": [{
                    "parts": [{
                        "text": message_text
                    }]
                }],
                "system_instruction": {
                    "parts": [{
                        "text": PROMPT
                    }]
                },
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                }
            }
    
    def _extract_content_from_response(self, response_json):
        """Extract content from API response based on LLM option"""
        if self.llm_option == 'BITDEER':
            choices = response_json.get('choices', [])
            if choices:
                return choices[0].get('message', {}).get('content', '')
        else:
            candidates = response_json.get('candidates', [])
            if candidates:
                return candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return None
    
    async def get_llm_response(self, message_text):
        """
        Get response from LLM API
        Returns tuple: (success: bool, content: str, error_msg: str)
        """
        data = self._prepare_request_data(message_text)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=self.headers, json=data) as response:
                    if response.status == 200:
                        try:
                            response_json = await response.json()
                            print(f"API Response: {response_json}\n")

                            content = self._extract_content_from_response(response_json)
                            
                            if not content:
                                return False, None, "No valid content in API response"
                            
                            return True, content, None
                            
                        except Exception as e:
                            return False, None, f"Error processing API response: {e}"
                    else:
                        return False, None, f"Error: Received status code {response.status}"
                        
        except aiohttp.ClientError as e:
            return False, None, f"Network error querying the API: {e}"
        except Exception as e:
            return False, None, f"Unexpected error querying the API: {e}"