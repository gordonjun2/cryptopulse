import signal
import json
import aiofiles
import asyncio
import random
import re
import prettytable as pt
from pyrogram import Client
from aiogram import Bot, Dispatcher, Router, html
from aiogram.utils import markdown as ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, MAIN_CHAT_ID,
                    CHAT_ID_LIST, TELEGRAM_BOT_TOKEN)

bot = Bot(token=TELEGRAM_BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)

FILE_PATH = "store.json"
lock = asyncio.Lock()
dp = Dispatcher()
router = Router()
dp.include_router(router)
chat_id_name_dict = {}


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


async def load_data():
    """Load JSON data asynchronously without acquiring the lock."""
    try:
        async with aiofiles.open(FILE_PATH, "r") as f:
            contents = await f.read()
            return json.loads(contents)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def save_data(data):
    """Save JSON data asynchronously."""
    async with aiofiles.open(FILE_PATH, "w") as f:
        await f.write(json.dumps(data, indent=4))


async def update_data(new_data):
    """Load, update by summing values, and save JSON data with a lock."""
    async with lock:
        data = await load_data()
        key, value = list(new_data.items())[0]
        data[key] = round(data.get(key, 0) + value, 2)
        await save_data(data)


async def generate_random_chat_id_net_profit():
    """Generate a random key-value pair."""
    random_chat_id = random.choice(CHAT_ID_LIST)
    net_profit = round(random.uniform(-1000, 1000), 2)
    return {str(random_chat_id): net_profit}


async def demo():
    """Run indefinitely, updating and replacing JSON data continuously."""
    print("🔹 Initial Load:", await load_data())

    while True:
        new_data = await generate_random_chat_id_net_profit()
        await update_data(new_data)
        print(f"🔸 Updated JSON:", await load_data())
        await asyncio.sleep(2)


async def set_commands():
    commands = [
        BotCommand(
            command="/pnl",
            description="Displays the current PNL data from Telegram channels."
        ),
        BotCommand(command="/help",
                   description="Displays available commands."),
    ]

    await bot.set_my_commands(commands)


# /start command handler
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


# /pnl command handler
@router.message(Command("pnl"))
async def cmd_pnl(message: Message,
                  chat_name_width: int = 17,
                  pnl_width: int = 12):
    """Handle /pnl command, send current data to Telegram group."""
    data = await load_data()
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


# /help command handler
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command, list all available commands."""
    help_message = (
        "Here are the available commands:\n\n"
        "/pnl - Displays the current PNL data (a JSON with PNLs from different Telegram channels and their total PNL).\n\n"
        "/help - Displays this help message with a list of available commands."
    )
    await message.answer(help_message)


def signal_handler(sig, frame):
    print("Stopping the application...")
    print("The application has stopped. Exiting.")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)  # SIGINT for Ctrl + C
signal.signal(signal.SIGTSTP, signal_handler)  # SIGTSTP for Ctrl + Z


async def get_chat_id_name_dict():
    for chat_id in CHAT_ID_LIST:
        chat_id_str = str(chat_id)
        try:
            chat_info = await app.get_chat(chat_id)
            chat_id_name_dict[chat_id_str] = chat_info.title
        except Exception as e:
            chat_id_name_dict[chat_id_str] = chat_id_str
            continue


async def main():

    await app.start()
    await check_bot_membership()
    await get_chat_id_name_dict()

    if asyncio.get_event_loop().is_running() is False:
        return

    bot_commands_task = asyncio.create_task(set_commands())
    bot_task = asyncio.create_task(dp.start_polling(bot))
    demo_task = asyncio.create_task(demo())

    await asyncio.gather(bot_commands_task, bot_task, demo_task)
    await bot.session.close()
    await app.stop()


if __name__ == "__main__":
    app.run(main())
