"""
LLM API client for CryptoPulse trading bot.
"""

import asyncio
import aiohttp
from config import (LLM_OPTION, BITDEER_AI_BEARER_TOKEN, GEMINI_API_KEY, 
                   PROMPT)

# API configuration
if LLM_OPTION.upper() == "BITDEER":
    print("Using Bitdeer AI LLM API...\n")
    url = "https://api-inference.bitdeer.ai/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + BITDEER_AI_BEARER_TOKEN,
        "Content-Type": "application/json"
    }
else:
    print("Using Gemini LLM API...\n")
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + GEMINI_API_KEY
    headers = {'Content-Type': 'application/json'}

# Message queue for processing
message_queue = asyncio.Queue()


async def process_message_with_llm(session, forwarded_message, message, use_bot, bot):
    """Process a message with LLM API."""
    if LLM_OPTION.upper() == "BITDEER":
        data = {
            "model": "deepseek-ai/DeepSeek-V3",
            "messages": [{
                "role": "system",
                "content": PROMPT
            }, {
                "role": "user",
                "content": forwarded_message.text or forwarded_message.caption
            }],
            "max_tokens": 1024,
            "temperature": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "top_p": 1,
            "stream": False
        }
    else:
        data = {
            "contents": [{
                "parts": [{
                    "text": forwarded_message.text or forwarded_message.caption
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

    try:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                try:
                    response_json = await response.json()
                    print(f"API Response: {response_json}\n")

                    content = None
                    if LLM_OPTION == 'BITDEER':
                        choices = response_json.get('choices', [])
                        if choices:
                            content = choices[0].get('message', {}).get('content', '')
                    else:
                        candidates = response_json.get('candidates', [])
                        if candidates:
                            content = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')

                    if not content:
                        error_msg = "No valid content in API response"
                        print(error_msg, flush=True)
                        if use_bot:
                            await bot.send_message(
                                forwarded_message.chat.id,
                                error_msg,
                                reply_to_message_id=forwarded_message.id)
                        else:
                            await forwarded_message.reply_text(error_msg, quote=True)
                        return None

                    return content

                except Exception as e:
                    error_msg = f"Error parsing API response: {e}"
                    print(error_msg, flush=True)
                    if use_bot:
                        await bot.send_message(
                            forwarded_message.chat.id,
                            error_msg,
                            reply_to_message_id=forwarded_message.id)
                    else:
                        await forwarded_message.reply_text(error_msg, quote=True)
                    return None
            else:
                error_msg = f"API request failed with status {response.status}"
                print(error_msg, flush=True)
                if use_bot:
                    await bot.send_message(
                        forwarded_message.chat.id,
                        error_msg,
                        reply_to_message_id=forwarded_message.id)
                else:
                    await forwarded_message.reply_text(error_msg, quote=True)
                return None

    except Exception as e:
        error_msg = f"Error making API request: {e}"
        print(error_msg, flush=True)
        if use_bot:
            await bot.send_message(
                forwarded_message.chat.id,
                error_msg,
                reply_to_message_id=forwarded_message.id)
        else:
            await forwarded_message.reply_text(error_msg, quote=True)
        return None


async def message_processor(use_bot, bot):
    """LLM message processor."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                forwarded_message, message = await message_queue.get()
                content = await process_message_with_llm(session, forwarded_message, message, use_bot, bot)
                
                if content:
                    if use_bot:
                        await bot.send_message(
                            forwarded_message.chat.id,
                            content,
                            reply_to_message_id=forwarded_message.id)
                    else:
                        await forwarded_message.reply_text(content, quote=True)

                message_queue.task_done()
            except Exception as e:
                print(f"Error in message processor: {e}", flush=True)
                message_queue.task_done()