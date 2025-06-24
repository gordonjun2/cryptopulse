import aiohttp
import asyncio
from typing import Optional, Tuple, List
from config import (
    LLM_OPTION, BITDEER_AI_BEARER_TOKEN, GEMINI_API_KEY, PROMPT
)


class LLMProcessor:
    """Handles LLM API calls and sentiment analysis"""
    
    def __init__(self):
        self.llm_option = LLM_OPTION.upper()
        self._setup_api_config()
    
    def _setup_api_config(self):
        """Setup API configuration based on selected LLM option"""
        if self.llm_option == "BITDEER":
            self.url = "https://api-inference.bitdeer.ai/v1/chat/completions"
            self.headers = {
                "Authorization": f"Bearer {BITDEER_AI_BEARER_TOKEN}",
                "Content-Type": "application/json"
            }
        else:  # GEMINI
            self.url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
            self.headers = {'Content-Type': 'application/json'}
    
    def _prepare_bitdeer_payload(self, message_text: str) -> dict:
        """Prepare payload for Bitdeer AI API"""
        return {
            "model": "deepseek-ai/DeepSeek-V3",
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": message_text}
            ],
            "max_tokens": 1024,
            "temperature": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "top_p": 1,
            "stream": False
        }
    
    def _prepare_gemini_payload(self, message_text: str) -> dict:
        """Prepare payload for Gemini AI API"""
        return {
            "contents": [{
                "parts": [{"text": message_text}]
            }],
            "system_instruction": {
                "parts": [{"text": PROMPT}]
            },
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
            }
        }
    
    def _extract_bitdeer_response(self, response_json: dict) -> Optional[str]:
        """Extract content from Bitdeer AI response"""
        try:
            choices = response_json.get('choices', [])
            if choices:
                return choices[0].get('message', {}).get('content', '')
        except Exception as e:
            print(f"Error extracting Bitdeer response: {e}")
        return None
    
    def _extract_gemini_response(self, response_json: dict) -> Optional[str]:
        """Extract content from Gemini AI response"""
        try:
            candidates = response_json.get('candidates', [])
            if candidates:
                return candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        except Exception as e:
            print(f"Error extracting Gemini response: {e}")
        return None
    
    async def analyze_sentiment(self, message_text: str) -> Optional[str]:
        """Analyze sentiment of message text using configured LLM"""
        try:
            # Prepare payload based on LLM option
            if self.llm_option == "BITDEER":
                data = self._prepare_bitdeer_payload(message_text)
            else:
                data = self._prepare_gemini_payload(message_text)
            
            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=self.headers, json=data) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        print(f"LLM API Response: {response_json}")
                        
                        # Extract content based on LLM option
                        if self.llm_option == "BITDEER":
                            content = self._extract_bitdeer_response(response_json)
                        else:
                            content = self._extract_gemini_response(response_json)
                        
                        return content
                    else:
                        print(f"LLM API error: {response.status} - {await response.text()}")
                        return None
        
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return None
    
    def parse_llm_response(self, response_text: str) -> Tuple[List[str], Optional[float], str]:
        """Parse LLM response to extract coins, sentiment, and explanation"""
        try:
            lines = response_text.strip().split('\n')
            coins = []
            sentiment = None
            explanation = ""
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if line.startswith('Coins:'):
                    coins_str = line.replace('Coins:', '').strip()
                    if coins_str != 'N/A':
                        coins = [coin.strip() for coin in coins_str.split(',')]
                
                elif line.startswith('Sentiment:'):
                    sentiment_str = line.replace('Sentiment:', '').strip()
                    if sentiment_str.endswith('%'):
                        try:
                            sentiment = float(sentiment_str.replace('%', ''))
                        except ValueError:
                            sentiment = None
                
                elif line.startswith('Explanation:'):
                    explanation = line.replace('Explanation:', '').strip()
                    # Add remaining lines to explanation
                    if i + 1 < len(lines):
                        explanation += ' ' + ' '.join(lines[i + 1:])
                    break
            
            return coins, sentiment, explanation
        
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return [], None, ""
    
    async def process_message(self, message_text: str) -> Tuple[List[str], Optional[float], str]:
        """Process message and return extracted information"""
        response = await self.analyze_sentiment(message_text)
        
        if response:
            return self.parse_llm_response(response)
        else:
            return [], None, "Failed to analyze sentiment"


# Convenience function for backward compatibility
async def analyze_message_sentiment(message_text: str) -> Tuple[List[str], Optional[float], str]:
    """Analyze message sentiment using LLM processor"""
    processor = LLMProcessor()
    return await processor.process_message(message_text)