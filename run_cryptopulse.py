import signal
import telebot
import aiohttp
import asyncio
from pyrogram import Client, utils, filters, idle
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST,
                    MAIN_CHAT_ID, BITDEER_AI_BEARER_TOKEN, TELEGRAM_BOT_TOKEN,
                    PROMPT)

# bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
bot = telebot.TeleBot('', threaded=False)
print(f"Checking Telegram Bot status...")

try:
    bot_info = bot.get_me()
    bot_member = bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

    if bot_member.status in ["administrator", "member"]:
        print(f"Telegram Bot is in the chat (status: {bot_member.status})")
        print(f"Telegram Bot will reply to messages...\n")
        use_bot = True
    else:
        print(f"Telegram Bot is not in the chat (status: {bot_member.status})")
        print(f"User will reply to messages instead...\n")
        use_bot = False

except Exception as e:
    print(f"Telegram Bot cannot be used: {e}")
    print(f"User will reply to messages instead...\n")
    use_bot = False


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
                    "role": "system",
                    "content": PROMPT
                }, {
                    "role": "user",
                    "content": message.text or message.caption
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
                                if use_bot:
                                    # bot.send_message(
                                    #     message.chat.id,
                                    #     content,
                                    #     reply_to_message_id=message.id)
                                    bot.send_message(message.chat.id, content)
                                else:
                                    await message.reply_text(content,
                                                             quote=True)
                                print(f"Replied with content:\n{content}\n")
                    else:
                        print(
                            f"Error: Received status code {response.status}\n")
            except Exception as e:
                print(f"Error querying the API: {e}\n")

            message_queue.task_done()


@app.on_message(filters.chat(CHAT_ID_LIST))
async def my_handler(client, message):
    if message.text or message.caption:
        print(f"Message received from chat: {message.chat.id}")
        print(f"Message: {message.text or message.caption}")

        try:
            forwarded_message = await message.forward(chat_id=int(MAIN_CHAT_ID)
                                                      )
            print("Message forwarded successfully.\n")

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
