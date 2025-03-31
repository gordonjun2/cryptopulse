import os
import time
import signal
import math
import re
import telebot
import aiohttp
import asyncio
import textwrap
from google import genai
from google.genai import types
from pyrogram import Client, utils, filters, idle
import binance.client
from binance.exceptions import BinanceAPIException
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST,
                    MAIN_CHAT_ID, BITDEER_AI_BEARER_TOKEN, PROMPT, MAX_RETRIES,
                    RETRY_AFTER, INITIAL_CAPITAL, LEVERAGE, HODL_TIME,
                    TRADE_SENTIMENT_THRESHOLD, BINANCE_TESTNET_API_KEY,
                    BINANCE_TESTNET_API_SECRET, BINANCE_TESTNET_FLAG,
                    LLM_OPTION, GEMINI_API_KEY)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# [Binance] Client
if BINANCE_TESTNET_FLAG:
    client = binance.client.Client(BINANCE_TESTNET_API_KEY,
                                   BINANCE_TESTNET_API_SECRET,
                                   testnet=True)
else:
    client = binance.client.Client()

client.session.verify = False


# [Binance] Retry logic
def retry_api_call(func, *args, **kwargs):
    retries = MAX_RETRIES or 3
    delay = RETRY_AFTER or 2
    for _ in range(retries):
        try:
            return func(*args, **kwargs)
        except BinanceAPIException as e:
            print(f"Binance API Error: {e}. Retrying...", flush=True)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying...", flush=True)
        time.sleep(delay)
    print("Max retries reached. Operation failed.", flush=True)
    return None


# [Binance] Get symbol's quantity precision
def get_symbol_precision():
    try:
        exchange_info = client.futures_exchange_info()
        symbol_quantity_precision_dict = {}
        for symbol_info in exchange_info["symbols"]:
            symbol = symbol_info.get("symbol")
            price_precision = symbol_info.get("quantityPrecision")
            if symbol and price_precision:
                symbol_quantity_precision_dict[symbol] = int(price_precision)
        return symbol_quantity_precision_dict
    except BinanceAPIException as e:
        print(f"Error fetching precision: {e}", flush=True)
        return {}


# [Binance] Settings
if BINANCE_TESTNET_FLAG:
    perps_tokens = retry_api_call(get_symbol_precision)
    if not perps_tokens:
        print("Failed to fetch quantity precision. Exiting...", flush=True)
        exit(1)
else:
    exchange_info = client.futures_exchange_info()
    perps_tokens = [
        symbol['symbol'] for symbol in exchange_info['symbols']
        if 'USDT' in symbol['symbol'] and symbol['status'] == 'TRADING'
    ]

symbol_queue = asyncio.Queue()
processing_symbols = set()


# [Binance] Get ticker price with retry logic
def get_price(symbol):
    return retry_api_call(client.futures_symbol_ticker, symbol=symbol)


# [Binance] Set leverage
def change_leverage(symbol, leverage):
    retry_api_call(client.futures_change_leverage,
                   symbol=symbol,
                   leverage=leverage)


# [Binance] Place market buy order with retry logic
def place_buy_order(symbol, order_size):
    return retry_api_call(client.futures_create_order,
                          symbol=symbol,
                          side="BUY",
                          type="MARKET",
                          quantity=order_size)


# [Binance] Place market sell order with retry logic
def place_sell_order(symbol, order_size):
    return retry_api_call(client.futures_create_order,
                          symbol=symbol,
                          side="SELL",
                          type="MARKET",
                          quantity=order_size)


# [Binance] Function to simulate a trading operation for a single ticker
async def trade(symbol, direction, message):
    base_symbol = symbol.replace("USDT", "")

    print(f"\nTrading Parameters:")
    print(f"----------------------------------", flush=True)
    print(f"Symbol: {symbol}", flush=True)
    if BINANCE_TESTNET_FLAG:
        selected_symbol_price_precision = perps_tokens.get(symbol)
        print(f"Symbol Quantity Precision: {selected_symbol_price_precision}",
              flush=True)
        # Get ticker's price
        ticker = get_price(symbol)
    else:
        # Get ticker's price
        ticker = client.futures_symbol_ticker(symbol=symbol)

    print(f"Initial Capital (Margin): ${INITIAL_CAPITAL:,.2f}", flush=True)
    print(f"Leverage: {LEVERAGE}x", flush=True)
    print(f"Order Size (in USDT): ${INITIAL_CAPITAL * LEVERAGE:,.2f}",
          flush=True)

    price = float(ticker["price"])

    # Calculate order size
    order_size = (INITIAL_CAPITAL * LEVERAGE) / price
    if BINANCE_TESTNET_FLAG and selected_symbol_price_precision:
        change_leverage(symbol, LEVERAGE)
        order_size = math.floor(order_size *
                                (10**selected_symbol_price_precision)) / (
                                    10**selected_symbol_price_precision)
        corrected_initial_capital = (order_size * price) / LEVERAGE
    else:
        corrected_initial_capital = INITIAL_CAPITAL

    print(f"Order Size (in {base_symbol}): {order_size:,.2f}", flush=True)
    print(f"----------------------------------\n", flush=True)

    buy_order = place_buy_order(symbol,
                                order_size) if BINANCE_TESTNET_FLAG else True

    if buy_order:
        print(
            f"Market {'Buy' if direction == 'LONG' else 'Sell'} Order Executed: {order_size:,.2f} {base_symbol} at ${price}\n",
            flush=True)

        await asyncio.sleep(HODL_TIME)  # Simulate holding the position
        print(f"\nHodling for {HODL_TIME} seconds...\n", flush=True)

        if BINANCE_TESTNET_FLAG:
            ticker = get_price(symbol)
        else:
            ticker = client.futures_symbol_ticker(symbol=symbol)

        new_price = float(ticker["price"])

        sell_order = place_sell_order(
            symbol, order_size) if BINANCE_TESTNET_FLAG else True

        if sell_order:
            print(
                f"Market {'Sell' if direction == 'LONG' else 'Buy'} Order Executed: {order_size:,.2f} {base_symbol} at ${new_price}\n",
                flush=True)
            if direction == 'LONG':
                final_capital = corrected_initial_capital + (
                    (new_price - price) * order_size)
            else:
                final_capital = corrected_initial_capital - (
                    (new_price - price) * order_size)
            percentage_gained = ((final_capital - corrected_initial_capital) /
                                 corrected_initial_capital) * 100
            print(f"Trade Summary:", flush=True)
            print(f"----------------------------------", flush=True)
            print(f"Before Capital: ${corrected_initial_capital:.2f}",
                  flush=True)
            print(
                f"After Capital: ${final_capital:.2f} ({percentage_gained:+.2f}%)",
                flush=True)
            print(f"----------------------------------\n", flush=True)

            content = textwrap.dedent(f"""\
            🚀 **{direction} Trade Simulated** 🚀

            **Trading Parameters:**
            __Symbol:__ {symbol}  
            __Order Size (in USDT):__ ${INITIAL_CAPITAL * LEVERAGE:,.2f}  

            **Market {'Buy' if direction == 'LONG' else 'Sell'} Order Executed:**  
            {order_size:,.2f} {base_symbol} at ${price}  

            **Market {'Sell' if direction == 'LONG' else 'Buy'} Order Executed {HODL_TIME / 60:,.2f} mins later:**  
            {order_size:,.2f} {base_symbol} at ${new_price}  

            **Trade Summary:**  
            __Before Capital:__ ${corrected_initial_capital:.2f}  
            __After Capital:__ ${final_capital:.2f} ({percentage_gained:+.2f}%)
            """)

            await message.reply_text(content, quote=True)
        else:
            print(f"Sell order failed for {symbol}\n", flush=True)
    else:
        print(f"Buy order failed for {symbol}\n", flush=True)

    processing_symbols.remove(symbol)


# [Binance] Worker function to process tickers from the queue asynchronously
async def worker():
    while True:
        item = await symbol_queue.get(
        )  # Asynchronously get a symbol and message from the queue
        if item is None:
            break

        symbol, direction, message = item

        processing_symbols.add(symbol)

        # Execute trade
        await trade(symbol, direction, message)

        symbol_queue.task_done()


# [Telebot] Client
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


# [Pyrogram] Monkey Patch
def get_peer_type(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"


utils.get_peer_type = get_peer_type

# [Pyrogram] Client
app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)

# [Pyrogram] Settings
message_queue = asyncio.Queue()

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


# [Pyrogram] LLM API
async def message_processor():
    async with aiohttp.ClientSession() as session:
        while True:
            message = await message_queue.get()

            if LLM_OPTION.upper() == "BITDEER":
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
            else:
                data = {
                    "contents": [{
                        "parts": [{
                            "text": message.text or message.caption
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
                async with session.post(url, headers=headers,
                                        json=data) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        print(f"API Response: {response_json}\n")

                        if LLM_OPTION == 'BITDEER':
                            choices = response_json.get('choices', [])
                            if choices:
                                content = choices[0].get('message', {}).get(
                                    'content', '')

                        else:
                            candidates = response_json.get('candidates', [])
                            if candidates:
                                content = candidates[0].get('content', {}).get(
                                    'parts', [{}])[0].get('text', '')

                        if content:
                            if use_bot:
                                # replied_messsage = bot.send_message(
                                #     message.chat.id,
                                #     content,
                                #     reply_to_message_id=message.id)
                                replied_messsage = bot.send_message(
                                    message.chat.id, content)
                            else:
                                replied_messsage = await message.reply_text(
                                    content, quote=True)
                            print(f"Replied with content:\n{content}\n")

                            # Extract sentiment from the content
                            sentiment_match = re.search(
                                r"Sentiment:\s*([-+]?\d+)%", content)
                            sentiment = float(sentiment_match.group(
                                1)) if sentiment_match else 0

                            if abs(sentiment) >= TRADE_SENTIMENT_THRESHOLD:
                                direction = "LONG" if sentiment > 0 else "SHORT"

                                # Extract symbols from the content
                                matches = re.findall(r"Coins:\s*([\w, /]+)",
                                                     content)
                                symbols = matches[0].replace(
                                    " ", "").split(",") if matches else []
                                not_found_tickers = []
                                for symbol in symbols:
                                    if symbol == 'N/A' or not symbol:
                                        continue
                                    if "USDT" not in symbol:
                                        symbol += "USDT"
                                    # Check if ticker can be traded in Binance
                                    if symbol in perps_tokens:
                                        # Check if symbol is already in queue or being processed
                                        if symbol in processing_symbols or symbol in symbol_queue._queue:
                                            text = f"{symbol} is already in queue or being processed for a trade, skipping...\n"
                                            print(text, flush=True)
                                            await replied_messsage.reply_text(
                                                text, quote=True)
                                        else:
                                            text = f"Ticker {symbol} found in Binance API, hence a trade will be executed now. It will be closed in {HODL_TIME / 60:,.2f} minutes. \n"
                                            print(text, flush=True)
                                            trade_replied_messsage = await replied_messsage.reply_text(
                                                text, quote=True)
                                            print(
                                                f"Adding {symbol} to the queue\n",
                                                flush=True)
                                            await symbol_queue.put(
                                                (symbol, direction,
                                                 trade_replied_messsage))

                                    else:
                                        not_found_tickers.append(symbol)

                                if not_found_tickers:
                                    not_found_tickers_string = ", ".join(
                                        not_found_tickers)
                                    text = f"Ticker(s) {not_found_tickers_string} not found in Binance API, hence no trade is executed.\n"
                                    print(text)
                                    await replied_messsage.reply_text(
                                        text, quote=True)

                            else:
                                print(
                                    "Trade sentiment is below the threshold, hence no trade is executed.\n"
                                )

                    else:
                        print(
                            f"Error: Received status code {response.status}\n")
            except Exception as e:
                print(f"Error querying the API: {e}\n")

            message_queue.task_done()


# [Pyrogram] Handler for incoming messages
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
    print("Starting bot and trade system...")

    # Start Pyrogram
    await app.start()

    # Start worker tasks for trading system
    cpu_allocated = max(1, os.cpu_count() // 2)
    workers = [asyncio.create_task(worker()) for _ in range(cpu_allocated)]

    # Start Pyrogram-related tasks
    bot_task = asyncio.create_task(message_processor())
    idle_task = asyncio.create_task(idle())

    # Program will now keep running forever, waiting for items to be added to the queue
    try:
        # Main loop that waits for workers to finish their tasks
        while True:
            await asyncio.sleep(
                0.5
            )  # Sleep to avoid busy-waiting, replace with your actual logic

    except KeyboardInterrupt:
        print("\nShutting down gracefully...\n")
        for _ in range(cpu_allocated):
            await symbol_queue.put(None)

    # Wait for workers and tasks to finish
    await asyncio.gather(*workers, bot_task, idle_task)

    # Stop Pyrogram
    await app.stop()


if __name__ == "__main__":
    app.run(main())
