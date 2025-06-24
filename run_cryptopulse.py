import os
import time
import signal
import math
import re
import telebot
import aiohttp
import asyncio
import textwrap
import json
import aiofiles
import prettytable as pt
from pyrogram import Client, utils, filters, idle
from aiogram import Bot, Dispatcher, Router, html
from aiogram.utils import markdown as ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
import binance.client
from binance.exceptions import BinanceAPIException
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST,
                    MAIN_CHAT_ID, BITDEER_AI_BEARER_TOKEN, PROMPT, MAX_RETRIES,
                    RETRY_AFTER, INITIAL_CAPITAL, LEVERAGE, HODL_TIME,
                    TRADE_SENTIMENT_THRESHOLD, BINANCE_TESTNET_API_KEY,
                    BINANCE_TESTNET_API_SECRET, BINANCE_TESTNET_FLAG,
                    LLM_OPTION, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN,
                    NUM_WORKERS, ENV)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# [Binance] Client
try:
    if BINANCE_TESTNET_FLAG:
        client = binance.client.Client(BINANCE_TESTNET_API_KEY,
                                       BINANCE_TESTNET_API_SECRET,
                                       testnet=True)
    else:
        client = binance.client.Client()

    if ENV == 'dev':
        client.session.verify = False
except BinanceAPIException as e:
    print(f"Failed to initialize Binance client: {e}", flush=True)
    client = None
except Exception as e:
    print(f"Unexpected error initializing Binance client: {e}", flush=True)
    client = None


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
pending_symbols = set()


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
async def trade(symbol, direction, message, original_chat_id):
    try:
        base_symbol = symbol.replace("USDT", "")

        print(f"\nTrading Parameters:")
        print(f"----------------------------------", flush=True)
        print(f"Symbol: {symbol}", flush=True)

        if not client:
            error_msg = "Binance client is not initialized. Cannot execute trade."
            print(error_msg, flush=True)
            await message.reply_text(error_msg, quote=True)
            return

        if BINANCE_TESTNET_FLAG:
            selected_symbol_price_precision = perps_tokens.get(symbol)
            if not selected_symbol_price_precision:
                error_msg = f"Could not find precision for symbol {symbol}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

            print(
                f"Symbol Quantity Precision: {selected_symbol_price_precision}",
                flush=True)
            # Get ticker's price
            ticker = get_price(symbol)
        else:
            try:
                # Get ticker's price
                ticker = client.futures_symbol_ticker(symbol=symbol)
            except BinanceAPIException as e:
                error_msg = f"Failed to get ticker price for {symbol}: {e}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return
            except Exception as e:
                error_msg = f"Unexpected error getting ticker price for {symbol}: {e}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

        if not ticker:
            error_msg = f"Failed to get ticker data for {symbol}"
            print(error_msg, flush=True)
            await message.reply_text(error_msg, quote=True)
            return

        print(f"Initial Capital (Margin): ${INITIAL_CAPITAL:,.2f}", flush=True)
        print(f"Leverage: {LEVERAGE}x", flush=True)
        print(f"Order Size (in USDT): ${INITIAL_CAPITAL * LEVERAGE:,.2f}",
              flush=True)

        try:
            price = float(ticker["price"])
        except (KeyError, ValueError) as e:
            error_msg = f"Invalid ticker data for {symbol}: {e}"
            print(error_msg, flush=True)
            await message.reply_text(error_msg, quote=True)
            return

        # Calculate order size
        try:
            order_size = (INITIAL_CAPITAL * LEVERAGE) / price
            if BINANCE_TESTNET_FLAG and selected_symbol_price_precision:
                change_leverage(symbol, LEVERAGE)
                order_size = math.floor(
                    order_size * (10**selected_symbol_price_precision)) / (
                        10**selected_symbol_price_precision)
                corrected_initial_capital = (order_size * price) / LEVERAGE
            else:
                corrected_initial_capital = INITIAL_CAPITAL
        except Exception as e:
            error_msg = f"Error calculating order size: {e}"
            print(error_msg, flush=True)
            await message.reply_text(error_msg, quote=True)
            return

        print(f"Order Size (in {base_symbol}): {order_size:,.2f}", flush=True)
        print(f"----------------------------------\n", flush=True)

        try:
            buy_order = place_buy_order(
                symbol, order_size) if BINANCE_TESTNET_FLAG else True

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

                if not ticker:
                    error_msg = f"Failed to get updated ticker data for {symbol}"
                    print(error_msg, flush=True)
                    await message.reply_text(error_msg, quote=True)
                    return

                try:
                    new_price = float(ticker["price"])
                except (KeyError, ValueError) as e:
                    error_msg = f"Invalid updated ticker data for {symbol}: {e}"
                    print(error_msg, flush=True)
                    await message.reply_text(error_msg, quote=True)
                    return

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
                    percentage_gained = (
                        (final_capital - corrected_initial_capital) /
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

                    pnl = final_capital - corrected_initial_capital

                    new_pnl_data = {str(original_chat_id): pnl}

                    await update_pnl_data(new_pnl_data)
                    await update_stats_data(pnl)
                    await message.reply_text(content, quote=True)
                else:
                    error_msg = f"Sell order failed for {symbol}"
                    print(error_msg + "\n", flush=True)
                    await message.reply_text(error_msg, quote=True)
            else:
                error_msg = f"Buy order failed for {symbol}"
                print(error_msg + "\n", flush=True)
                await message.reply_text(error_msg, quote=True)
        except Exception as e:
            error_msg = f"Unexpected error during trade execution: {e}"
            print(error_msg, flush=True)
            await message.reply_text(error_msg, quote=True)
    except Exception as e:
        error_msg = f"Critical error in trade function: {e}"
        print(error_msg, flush=True)
        await message.reply_text(error_msg, quote=True)
    finally:
        processing_symbols.remove(symbol)


# [Binance] Worker function to process tickers from the queue asynchronously
async def worker():
    while True:
        item = await symbol_queue.get(
        )  # Asynchronously get a symbol and message from the queue
        if item is None:
            break

        symbol, direction, message, original_chat_id = item

        # Remove from pending and add to processing
        pending_symbols.remove(symbol)
        processing_symbols.add(symbol)

        # Execute trade
        await trade(symbol, direction, message, original_chat_id)

        symbol_queue.task_done()


# [Telebot (Synchronous)] Client
# bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
bot = telebot.TeleBot('', threaded=False)
print(f"Checking Telegram Bot status...\n")

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

# [Aiogram (Asynchronous)] Client (this will be used instead of the synchronous bot)
bot = Bot(token=TELEGRAM_BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# [Aiogram] Settings
PNL_FILE_PATH = "pnl_data.json"
STATS_FILE_PATH = "stats_data.json"
lock = asyncio.Lock()
dp = Dispatcher()
router = Router()
dp.include_router(router)
chat_id_name_dict = {}


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
            try:
                forwarded_message, message = await message_queue.get()

                if LLM_OPTION.upper() == "BITDEER":
                    data = {
                        "model":
                        "deepseek-ai/DeepSeek-V3",
                        "messages": [{
                            "role": "system",
                            "content": PROMPT
                        }, {
                            "role":
                            "user",
                            "content":
                            forwarded_message.text or forwarded_message.caption
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
                                "text":
                                forwarded_message.text
                                or forwarded_message.caption
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
                            try:
                                response_json = await response.json()
                                print(f"API Response: {response_json}\n")

                                content = None
                                if LLM_OPTION == 'BITDEER':
                                    choices = response_json.get('choices', [])
                                    if choices:
                                        content = choices[0].get(
                                            'message', {}).get('content', '')
                                else:
                                    candidates = response_json.get(
                                        'candidates', [])
                                    if candidates:
                                        content = candidates[0].get(
                                            'content',
                                            {}).get('parts',
                                                    [{}])[0].get('text', '')

                                if not content:
                                    error_msg = "No valid content in API response"
                                    print(error_msg, flush=True)
                                    if use_bot:
                                        await bot.send_message(
                                            forwarded_message.chat.id,
                                            error_msg,
                                            reply_to_message_id=
                                            forwarded_message.id)
                                    else:
                                        await forwarded_message.reply_text(
                                            error_msg, quote=True)
                                    continue

                                if use_bot:
                                    replied_messsage = await bot.send_message(
                                        forwarded_message.chat.id,
                                        content,
                                        reply_to_message_id=forwarded_message.
                                        id)
                                    # replied_messsage = await bot.send_message(
                                    #     forwarded_message.chat.id, content)
                                else:
                                    replied_messsage = await forwarded_message.reply_text(
                                        content, quote=True)
                                print(f"Replied with content:\n{content}\n")

                                # Extract sentiment from the content
                                try:
                                    sentiment_match = re.search(
                                        r"Sentiment:\s*([-+]?\d+)%", content)
                                    sentiment = float(sentiment_match.group(
                                        1)) if sentiment_match else 0
                                except (AttributeError, ValueError) as e:
                                    print(f"Error extracting sentiment: {e}",
                                          flush=True)
                                    sentiment = 0

                                if abs(sentiment) >= TRADE_SENTIMENT_THRESHOLD:
                                    direction = "LONG" if sentiment > 0 else "SHORT"

                                    # Extract symbols from the content
                                    try:
                                        matches = re.findall(
                                            r"Coins:\s*([\w, /]+)", content)
                                        symbols = matches[0].replace(
                                            " ",
                                            "").split(",") if matches else []
                                    except Exception as e:
                                        print(f"Error extracting symbols: {e}",
                                              flush=True)
                                        symbols = []

                                    not_found_tickers = []
                                    for symbol in symbols:
                                        if symbol == 'N/A' or not symbol:
                                            continue
                                        if "USDT" not in symbol:
                                            symbol += "USDT"
                                        # Check if ticker can be traded in Binance
                                        if symbol in perps_tokens:
                                            # Check if symbol is already in queue or being processed
                                            if symbol in processing_symbols or symbol in pending_symbols:
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
                                                pending_symbols.add(
                                                    symbol
                                                )  # Add to pending set before putting in queue
                                                await symbol_queue.put(
                                                    (symbol, direction,
                                                     trade_replied_messsage,
                                                     message.chat.id))

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

                            except Exception as e:
                                error_msg = f"Error processing API response: {e}"
                                print(error_msg, flush=True)
                                if use_bot:
                                    await bot.send_message(
                                        forwarded_message.chat.id,
                                        error_msg,
                                        reply_to_message_id=forwarded_message.
                                        id)
                                else:
                                    await forwarded_message.reply_text(
                                        error_msg, quote=True)
                        else:
                            error_msg = f"Error: Received status code {response.status}"
                            print(error_msg + "\n", flush=True)
                            if use_bot:
                                await bot.send_message(
                                    forwarded_message.chat.id,
                                    error_msg,
                                    reply_to_message_id=forwarded_message.id)
                            else:
                                await forwarded_message.reply_text(error_msg,
                                                                   quote=True)
                except aiohttp.ClientError as e:
                    error_msg = f"Network error querying the API: {e}"
                    print(error_msg + "\n", flush=True)
                    if use_bot:
                        await bot.send_message(
                            forwarded_message.chat.id,
                            error_msg,
                            reply_to_message_id=forwarded_message.id)
                    else:
                        await forwarded_message.reply_text(error_msg,
                                                           quote=True)
                except Exception as e:
                    error_msg = f"Unexpected error querying the API: {e}"
                    print(error_msg + "\n", flush=True)
                    if use_bot:
                        await bot.send_message(
                            forwarded_message.chat.id,
                            error_msg,
                            reply_to_message_id=forwarded_message.id)
                    else:
                        await forwarded_message.reply_text(error_msg,
                                                           quote=True)
            except Exception as e:
                print(f"Critical error in message processor: {e}\n",
                      flush=True)
            finally:
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

            await message_queue.put((forwarded_message, message))
        except Exception as e:
            print(f"Error forwarding message: {e}\n")


# [Aiogram] Check if the bot is a member of the chat
async def check_bot_membership():
    try:
        bot_info = await bot.get_me()
        bot_member = await bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

        if bot_member.status not in ["administrator", "member"]:
            print("Bot is not in the chat MAIN_CHAT_ID. Exiting...\n")
            await bot.session.close()
            asyncio.get_event_loop().stop()
        else:
            print("Bot is a member of the chat MAIN_CHAT_ID. Continuing...\n")

    except Exception as e:
        print(f"Error checking chat membership: {e}\n")
        await bot.session.close()
        asyncio.get_event_loop().stop()


# Load JSON data asynchronously
async def load_data(FILE_PATH):
    """Load JSON data asynchronously without acquiring the lock."""
    try:
        async with aiofiles.open(FILE_PATH, "r") as f:
            contents = await f.read()
            return json.loads(contents)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Save JSON data asynchronously
async def save_data(data, FILE_PATH):
    """Save JSON data asynchronously."""
    async with aiofiles.open(FILE_PATH, "w") as f:
        await f.write(json.dumps(data, indent=4))


# Update JSON data asynchronously
async def update_pnl_data(new_data):
    """Load, update by summing values, and save JSON data with a lock."""
    async with lock:
        data = await load_data(PNL_FILE_PATH)
        key, value = list(new_data.items())[0]
        data[key] = round(data.get(key, 0) + value, 2)
        await save_data(data, PNL_FILE_PATH)


async def update_stats_data(pnl):
    """Load, update by summing values, and save JSON data with a lock."""
    async with lock:
        data = await load_data(STATS_FILE_PATH)
        prev_max_gain = data.get("Maximum Gain", 0)
        prev_max_drawdown = data.get("Maximum Drawdown", 0)
        prev_avg_gain = data.get("Average Gain", 0)
        total_no_of_trades = data.get("Total No. of Trades", 0)

        if pnl >= 0:
            data["Maximum Gain"] = round(max(prev_max_gain, pnl), 2)
        else:
            data["Maximum Drawdown"] = round(min(prev_max_drawdown, pnl), 2)

        data["Average Gain"] = round(
            ((prev_avg_gain * total_no_of_trades) + pnl) /
            (total_no_of_trades + 1), 2)
        data["Total No. of Trades"] = total_no_of_trades + 1

        await save_data(data, STATS_FILE_PATH)


# [Aiogram] Set bot commands
async def set_commands():
    commands = [
        BotCommand(
            command="/pnl",
            description="Displays the current PNL data from Telegram channels."
        ),
        BotCommand(command="/stats",
                   description="Displays the current trading statistics."),
        BotCommand(command="/help",
                   description="Displays available commands."),
    ]

    await bot.set_my_commands(commands)


# [Aiogram] /start command handler
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


# [Aiogram] /pnl command handler
@router.message(Command("pnl"))
async def cmd_pnl(message: Message,
                  chat_name_width: int = 17,
                  pnl_width: int = 12):
    """Handle /pnl command, send current data to Telegram group."""
    data = await load_data(PNL_FILE_PATH)

    if data:
        renamed_data = []
        total_pnl = 0
        for chat_id, pnl in data.items():
            chat_name = chat_id_name_dict.get(chat_id, chat_id)
            chat_name = re.sub(r'[^A-Za-z0-9\s]', '', chat_name)
            chat_name = re.sub(r'\s+', ' ', chat_name)
            chat_name = chat_name.strip()
            renamed_data.append((chat_name, pnl))
            total_pnl += pnl
        sorted_data = sorted(renamed_data, key=lambda x: x[0])

        table = pt.PrettyTable(['Chat Name', 'PNL (in USD)'])
        table.align['Chat Name'] = 'l'
        table.align['PNL (in USD)'] = 'r'
        table.max_width['Chat Name'] = chat_name_width
        table.max_width['PNL (in USD)'] = pnl_width

        table_title = "Current PNL Data"
        for chat_name, pnl in sorted_data:
            table.add_row([chat_name, f'{pnl:.2f}'])
        table.add_row(["-" * chat_name_width, "-" * pnl_width])
        table.add_row(["Total PNL", f'{total_pnl:.2f}'])

        await message.answer(f'<b>{table_title}:</b>\n<pre>{table}</pre>',
                             parse_mode=ParseMode.HTML)

    else:
        await message.answer("No data available.")


# [Aiogram] /stats command handler
@router.message(Command("stats"))
async def cmd_pnl(message: Message,
                  chat_name_width: int = 17,
                  pnl_width: int = 12):
    """Handle /pnl command, send current data to Telegram group."""
    data = await load_data(STATS_FILE_PATH)

    if data:
        ordered_data = [('Maximum Gain', data.get("Maximum Gain", 0)),
                        ('Maximum Drawdown', data.get("Maximum Drawdown", 0)),
                        ('Average Gain', data.get("Average Gain", 0)),
                        ('Total No. of Trades',
                         data.get("Total No. of Trades", 0))]

        table = pt.PrettyTable(['Statistics', 'Value'])
        table.align['Statistics'] = 'l'
        table.align['Value'] = 'r'
        table.max_width['Statistics'] = chat_name_width
        table.max_width['Value'] = pnl_width

        table_title = "Current Trading Statistics"
        for stat, value in ordered_data:
            if stat != 'Total No. of Trades':
                table.add_row([stat, f'{value:.2f} USD'])
            else:
                table.add_row([stat, f'{value}'])

        await message.answer(f'<b>{table_title}:</b>\n<pre>{table}</pre>',
                             parse_mode=ParseMode.HTML)

    else:
        await message.answer("No data available.")


# [Aiogram] /help command handler
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command, list all available commands."""
    help_message = (
        "Here are the available commands:\n\n"
        "/pnl - Displays the current PNL data (a JSON with PNLs from different Telegram channels and their total PNL).\n\n"
        "/help - Displays this help message with a list of available commands."
    )
    await message.answer(help_message)


# [Pyrogram] Get chat ID and name dictionary
async def get_chat_id_name_dict():
    for chat_id in CHAT_ID_LIST:
        chat_id_str = str(chat_id)
        try:
            chat_info = await app.get_chat(chat_id)
            chat_id_name_dict[chat_id_str] = chat_info.title
        except Exception as e:
            chat_id_name_dict[chat_id_str] = chat_id_str
            continue


def signal_handler(sig, frame):
    print("Stopping the application...")
    if app:
        app.stop()
    print("The application has stopped. Exiting.")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)  # SIGINT for Ctrl + C
signal.signal(signal.SIGTSTP, signal_handler)  # SIGTSTP for Ctrl + Z


async def main():
    try:
        print("Starting bot and trade system...\n")

        # Start Pyrogram
        try:
            await app.start()
        except Exception as e:
            print(f"Failed to start Pyrogram client: {e}\n")
            return

        # Check if the bot is a member of the chat
        try:
            await check_bot_membership()
        except Exception as e:
            print(f"Failed to check bot membership: {e}\n")
            await app.stop()
            return

        if asyncio.get_event_loop().is_running() is False:
            print("Event loop is not running\n")
            await app.stop()
            return

        # Get chat ID and chat name dictionary
        try:
            await get_chat_id_name_dict()
        except Exception as e:
            print(f"Failed to get chat ID and name dictionary: {e}\n")
            await app.stop()
            return

        # Start worker tasks for trading system
        try:
            workers = [
                asyncio.create_task(worker()) for _ in range(NUM_WORKERS)
            ]
        except Exception as e:
            print(f"Failed to create worker tasks: {e}\n")
            await app.stop()
            return

        # Start Pyrogram-related tasks
        try:
            bot_task = asyncio.create_task(message_processor())
            idle_task = asyncio.create_task(idle())
            bot_commands_task = asyncio.create_task(set_commands())
            tg_bot_task = asyncio.create_task(dp.start_polling(bot))
        except Exception as e:
            print(f"Failed to start bot tasks: {e}\n")
            for w in workers:
                w.cancel()
            await app.stop()
            return

        # Program will now keep running forever, waiting for items to be added to the queue
        try:
            # Main loop that waits for workers to finish their tasks
            while True:
                await asyncio.sleep(0.5)  # Sleep to avoid busy-waiting
        except KeyboardInterrupt:
            print("\nShutting down gracefully...\n")
        except Exception as e:
            print(f"Error in main loop: {e}\n")
        finally:
            # Cancel all tasks
            print("Cancelling tasks...\n")
            for w in workers:
                w.cancel()
            bot_task.cancel()
            idle_task.cancel()
            bot_commands_task.cancel()
            tg_bot_task.cancel()

            # Wait for all tasks to complete
            try:
                await asyncio.gather(*workers,
                                     bot_task,
                                     idle_task,
                                     bot_commands_task,
                                     tg_bot_task,
                                     return_exceptions=True)
            except Exception as e:
                print(f"Error during task cleanup: {e}\n")

            # Stop TG bot
            try:
                await bot.session.close()
            except Exception as e:
                print(f"Error closing bot session: {e}\n")

            # Stop Pyrogram
            try:
                await app.stop()
            except Exception as e:
                print(f"Error stopping Pyrogram: {e}\n")

    except Exception as e:
        print(f"Critical error in main function: {e}\n")
        try:
            await app.stop()
        except:
            pass
        try:
            await bot.session.close()
        except:
            pass


if __name__ == "__main__":
    app.run(main())
