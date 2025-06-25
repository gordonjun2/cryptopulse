import re
import asyncio
import telebot
import prettytable as pt
from pyrogram import Client, utils, filters, idle
from aiogram import Bot, Dispatcher, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST, 
                    MAIN_CHAT_ID, TELEGRAM_BOT_TOKEN, NUM_WORKERS)


class TelegramBots:
    """Handles both Pyrogram and Aiogram bot setup and management"""
    
    def __init__(self, message_processor, data_manager):
        self.message_processor = message_processor
        self.data_manager = data_manager
        self.chat_id_name_dict = {}
        self.use_bot = False
        
        # Initialize bots
        self._setup_pyrogram()
        self._setup_aiogram()
        self._check_bot_status()
    
    def _setup_pyrogram(self):
        """Setup Pyrogram client"""
        # Monkey patch for peer type
        def get_peer_type(peer_id: int) -> str:
            peer_id_str = str(peer_id)
            if not peer_id_str.startswith("-"):
                return "user"
            elif peer_id_str.startswith("-100"):
                return "channel"
            else:
                return "chat"
        
        utils.get_peer_type = get_peer_type
        self.pyrogram_app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)
    
    def _setup_aiogram(self):
        """Setup Aiogram bot"""
        self.aiogram_bot = Bot(
            token=TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)
        self._setup_aiogram_handlers()
    
    def _check_bot_status(self):
        """Check if the bot can be used"""
        try:
            sync_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
            bot_info = sync_bot.get_me()
            bot_member = sync_bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

            if bot_member.status in ["administrator", "member"]:
                print(f"Telegram Bot is in the chat (status: {bot_member.status})")
                print(f"Telegram Bot will reply to messages...\n")
                self.use_bot = True
            else:
                print(f"Telegram Bot is not in the chat (status: {bot_member.status})")
                print(f"User will reply to messages instead...\n")
                self.use_bot = False
        except Exception as e:
            print(f"Telegram Bot cannot be used: {e}")
            print(f"User will reply to messages instead...\n")
            self.use_bot = False
    
    def _setup_aiogram_handlers(self):
        """Setup Aiogram command handlers"""
        @self.router.message(CommandStart())
        async def command_start_handler(message: Message) -> None:
            await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

        @self.router.message(Command("pnl"))
        async def cmd_pnl(message: Message, chat_name_width: int = 17, pnl_width: int = 12):
            """Handle /pnl command, send current data to Telegram group."""
            data = await self.data_manager.get_pnl_data()

            if data:
                renamed_data = []
                total_pnl = 0
                for chat_id, pnl in data.items():
                    chat_name = self.chat_id_name_dict.get(chat_id, chat_id)
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

        @self.router.message(Command("stats"))
        async def cmd_stats(message: Message, chat_name_width: int = 17, pnl_width: int = 12):
            """Handle /stats command, send current statistics to Telegram group."""
            data = await self.data_manager.get_stats_data()

            if data:
                ordered_data = [
                    ('Maximum Gain', data.get("Maximum Gain", 0)),
                    ('Maximum Drawdown', data.get("Maximum Drawdown", 0)),
                    ('Average Gain', data.get("Average Gain", 0)),
                    ('Total No. of Trades', data.get("Total No. of Trades", 0))
                ]

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

        @self.router.message(Command("help"))
        async def cmd_help(message: Message):
            """Handle /help command, list all available commands."""
            help_message = (
                "Here are the available commands:\n\n"
                "/pnl - Displays the current PNL data (a JSON with PNLs from different Telegram channels and their total PNL).\n\n"
                "/help - Displays this help message with a list of available commands."
            )
            await message.answer(help_message)
    
    def setup_pyrogram_handlers(self):
        """Setup Pyrogram message handlers"""
        @self.pyrogram_app.on_message(filters.chat(CHAT_ID_LIST))
        async def message_handler(client, message):
            if message.text or message.caption:
                print(f"Message received from chat: {message.chat.id}")
                print(f"Message: {message.text or message.caption}")

                try:
                    forwarded_message = await message.forward(chat_id=int(MAIN_CHAT_ID))
                    print("Message forwarded successfully.\n")
                    await self.message_processor.add_message_to_queue(forwarded_message, message)
                except Exception as e:
                    print(f"Error forwarding message: {e}\n")
    
    async def check_bot_membership(self):
        """Check if the bot is a member of the chat"""
        try:
            bot_info = await self.aiogram_bot.get_me()
            bot_member = await self.aiogram_bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

            if bot_member.status not in ["administrator", "member"]:
                print("Bot is not in the chat MAIN_CHAT_ID. Exiting...\n")
                await self.aiogram_bot.session.close()
                asyncio.get_event_loop().stop()
            else:
                print("Bot is a member of the chat MAIN_CHAT_ID. Continuing...\n")
        except Exception as e:
            print(f"Error checking chat membership: {e}\n")
            await self.aiogram_bot.session.close()
            asyncio.get_event_loop().stop()
    
    async def get_chat_id_name_dict(self):
        """Get chat ID and name dictionary"""
        for chat_id in CHAT_ID_LIST:
            chat_id_str = str(chat_id)
            try:
                chat_info = await self.pyrogram_app.get_chat(chat_id)
                self.chat_id_name_dict[chat_id_str] = chat_info.title
            except Exception as e:
                self.chat_id_name_dict[chat_id_str] = chat_id_str
                continue
    
    async def set_commands(self):
        """Set bot commands"""
        commands = [
            BotCommand(
                command="/pnl",
                description="Displays the current PNL data from Telegram channels."
            ),
            BotCommand(
                command="/stats",
                description="Displays the current trading statistics."
            ),
            BotCommand(
                command="/help",
                description="Displays available commands."
            ),
        ]
        await self.aiogram_bot.set_my_commands(commands)
    
    async def start_pyrogram(self):
        """Start Pyrogram client"""
        await self.pyrogram_app.start()
        self.setup_pyrogram_handlers()
    
    async def stop_pyrogram(self):
        """Stop Pyrogram client"""
        await self.pyrogram_app.stop()
    
    async def start_aiogram_polling(self):
        """Start Aiogram polling"""
        return asyncio.create_task(self.dp.start_polling(self.aiogram_bot))
    
    async def close_aiogram_session(self):
        """Close Aiogram bot session"""
        await self.aiogram_bot.session.close()
    
    def get_bot_for_message_processor(self):
        """Get bot instance for message processor"""
        return self.aiogram_bot if self.use_bot else None