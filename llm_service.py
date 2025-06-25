import aiohttp
from config import (LLM_OPTION, BITDEER_AI_BEARER_TOKEN, GEMINI_API_KEY, PROMPT)


class LLMService:
    def __init__(self):
        self.llm_option = LLM_OPTION.upper()
        self.prompt = PROMPT
        
        if self.llm_option == "BITDEER":
            print("Using Bitdeer AI LLM API...\n")
            self.url = "https://api-inference.bitdeer.ai/v1/chat/completions"
            self.headers = {
                "Authorization": "Bearer " + BITDEER_AI_BEARER_TOKEN,
                "Content-Type": "application/json"
            }
        else:
            print("Using Gemini LLM API...\n")
            self.url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + GEMINI_API_KEY
            self.headers = {'Content-Type': 'application/json'}

    def _prepare_bitdeer_payload(self, message_text):
        """Prepare payload for Bitdeer API"""
        return {
            "model": "deepseek-ai/DeepSeek-V3",
            "messages": [{
                "role": "system",
                "content": self.prompt
            }, {
                "role": "user",
                "content": message_text
            }],
            "max_tokens": 1024,
            "temperature": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "top_p": 1,
            "stream": False
        }

    def _prepare_gemini_payload(self, message_text):
        """Prepare payload for Gemini API"""
        return {
            "contents": [{
                "parts": [{
                    "text": message_text
                }]
            }],
            "system_instruction": {
                "parts": [{
                    "text": self.prompt
                }]
            },
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
            }
        }

    def _extract_content_from_response(self, response_json):
        """Extract content from API response"""
        content = None
        if self.llm_option == 'BITDEER':
            choices = response_json.get('choices', [])
            if choices:
                content = choices[0].get('message', {}).get('content', '')
        else:
            candidates = response_json.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        return content

    async def analyze_sentiment(self, session, message_text):
        """Analyze sentiment using LLM API"""
        if self.llm_option == "BITDEER":
            data = self._prepare_bitdeer_payload(message_text)
        else:
            data = self._prepare_gemini_payload(message_text)

        try:
            async with session.post(self.url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    response_json = await response.json()
                    print(f"API Response: {response_json}\n")
                    
                    content = self._extract_content_from_response(response_json)
                    
                    if not content:
                        return None, "No valid content in API response"
                    
                    return content, None
                else:
                    return None, f"Error: Received status code {response.status}"
        except aiohttp.ClientError as e:
            return None, f"Network error querying the API: {e}"
        except Exception as e:
            return None, f"Unexpected error querying the API: {e}"