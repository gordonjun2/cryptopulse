import signal
import json
import aiohttp
import asyncio
from pyrogram import Client, utils, filters, idle
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST,
                    MAIN_CHAT_ID, BITDEER_AI_BEARER_TOKEN)


def get_peer_type(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"


utils.get_peer_type = get_peer_type

message_queue = asyncio.Queue()

url = "https://api-inference.bitdeer.ai/v1/chat/completions"
headers = {
    "Authorization": "Bearer " + BITDEER_AI_BEARER_TOKEN,
    "Content-Type": "application/json"
}

app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)


async def message_processor():
    async with aiohttp.ClientSession() as session:
        while True:
            message = await message_queue.get()

            data = {
                "model":
                "deepseek-ai/DeepSeek-V3",
                "messages": [{
                    "role":
                    "system",
                    "content":
                    "You are an assistant specialized in extracting \
                        cryptocurrencies mentioned in a given text and \
                        analyzing the tone of the news to generate a \
                        bullish prediction. Your task is to extract \
                        any cryptocurrency tickers in uppercase (e.g., \
                        XRP, SOL, ADA) and provide a bullish percentage \
                        prediction based on the tone of the news, \
                        formatted strictly as: 'Coins: [ticker 1], \
                        [ticker 2], ... Bullish: [percentage]%'"
                }, {
                    "role": "user",
                    "content": message.text
                }],
                "max_tokens":
                1024,
                "temperature":
                1,
                "frequency_penalty":
                0,
                "presence_penalty":
                0,
                "top_p":
                1,
                "stream":
                False
            }

            try:
                async with session.post(url, headers=headers,
                                        json=data) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        print(f"API Response: {response_json}\n")

                        choices = response_json.get('choices', [])
                        if choices:
                            content = choices[0].get('message',
                                                     {}).get('content', '')

                            if content:
                                content = content.replace(
                                    ' Bullish', '\nBullish')
                                await message.reply_text(content, quote=True)
                                print(f"Replied with content:\n{content}\n")
                    else:
                        print(
                            f"Error: Received status code {response.status}\n")
            except Exception as e:
                print(f"Error querying the API: {e}\n")

            message_queue.task_done()


@app.on_message(filters.chat(CHAT_ID_LIST))
async def my_handler(client, message):
    print(f"Message received from chat: {message.chat.id}")
    print(f"Message: {message.text}")

    try:
        forwarded_message = await message.forward(chat_id=MAIN_CHAT_ID)
        print("Message forwarded successfully.\n")

        if forwarded_message.text:
            await message_queue.put(forwarded_message)
    except Exception as e:
        print(f"Error forwarding message: {e}\n")


def signal_handler(sig, frame):
    print("Stopping the application...")
    if app:
        app.stop()
    print("The application has stopped. Exiting.")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)  # SIGINT for Ctrl + C
signal.signal(signal.SIGTSTP, signal_handler)  # SIGTSTP for Ctrl + Z


async def main():
    print("Starting bot...")

    await app.start()
    await asyncio.gather(message_processor(), idle())
    await app.stop()


if __name__ == "__main__":
    app.run(main())
