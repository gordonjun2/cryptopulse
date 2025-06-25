"""
Aiogram bot client for handling commands.
"""

import telebot
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import (TELEGRAM_BOT_TOKEN, MAIN_CHAT_ID)


class AiogramBotManager:
    """Manages Aiogram bot for handling commands."""
    
    def __init__(self):
        self.use_bot = False
        self.bot = None
        self.dp = None
        self.router = None
        self._initialize_bot()
        self._initialize_aiogram()
    
    def _initialize_bot(self):
        """Initialize Telegram bot and check permissions."""
        try:
            # Check bot status using telebot first
            temp_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
            print(f"Checking Telegram Bot status...\n")
            
            bot_info = temp_bot.get_me()
            bot_member = temp_bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

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
    
    def _initialize_aiogram(self):
        """Initialize Aiogram bot for async operations."""
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN,
                      default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)
    
    async def check_bot_membership(self):
        """Check if bot is member of the main chat."""
        try:
            bot_info = await self.bot.get_me()
            bot_member = await self.bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

            if bot_member.status not in ["administrator", "member"]:
                print("Bot is not in the chat MAIN_CHAT_ID. Exiting...\n")
                await self.bot.session.close()
                return False
            else:
                print("Bot is a member of the chat MAIN_CHAT_ID. Continuing...\n")
                return True

        except Exception as e:
            print(f"Error checking chat membership: {e}\n")
            await self.bot.session.close()
            return False
    
    async def start_polling(self):
        """Start bot polling."""
        return await self.dp.start_polling(self.bot)