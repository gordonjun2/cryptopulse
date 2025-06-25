import re
import telebot
from aiogram import Bot, Dispatcher, Router, html
from aiogram.utils import markdown as ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
import prettytable as pt
from config import TELEGRAM_BOT_TOKEN, MAIN_CHAT_ID


class TelegramHandlers:
    def __init__(self, data_storage):
        self.data_storage = data_storage
        self.chat_id_name_dict = {}
        
        # Initialize bots
        self.sync_bot = telebot.TeleBot('', threaded=False)
        self.async_bot = Bot(token=TELEGRAM_BOT_TOKEN,
                            default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Initialize dispatcher and router
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)
        
        # Register handlers
        self._register_handlers()
        
        # Check bot status
        self.use_bot = self._check_bot_status()

    def _check_bot_status(self):
        """Check if the bot can be used"""
        print(f"Checking Telegram Bot status...\n")
        try:
            bot_info = self.sync_bot.get_me()
            bot_member = self.sync_bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

            if bot_member.status in ["administrator", "member"]:
                print(f"Telegram Bot is in the chat (status: {bot_member.status})")
                print(f"Telegram Bot will reply to messages...\n")
                return True
            else:
                print(f"Telegram Bot is not in the chat (status: {bot_member.status})")
                print(f"User will reply to messages instead...\n")
                return False

        except Exception as e:
            print(f"Telegram Bot cannot be used: {e}")
            print(f"User will reply to messages instead...\n")
            return False

    def _register_handlers(self):
        """Register all command handlers"""
        self.router.message(CommandStart())(self.command_start_handler)
        self.router.message(Command("pnl"))(self.cmd_pnl)
        self.router.message(Command("stats"))(self.cmd_stats)
        self.router.message(Command("help"))(self.cmd_help)

    async def check_bot_membership(self):
        """Check if the bot is a member of the chat"""
        try:
            bot_info = await self.async_bot.get_me()
            bot_member = await self.async_bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)

            if bot_member.status not in ["administrator", "member"]:
                print("Bot is not in the chat MAIN_CHAT_ID. Exiting...\n")
                await self.async_bot.session.close()
                return False
            else:
                print("Bot is a member of the chat MAIN_CHAT_ID. Continuing...\n")
                return True

        except Exception as e:
            print(f"Error checking chat membership: {e}\n")
            await self.async_bot.session.close()
            return False

    async def set_commands(self):
        """Set bot commands"""
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

        await self.async_bot.set_my_commands(commands)

    def set_chat_id_name_dict(self, chat_id_name_dict):
        """Set the chat ID to name dictionary"""
        self.chat_id_name_dict = chat_id_name_dict

    # Command Handlers
    async def command_start_handler(self, message: Message) -> None:
        """Handle /start command"""
        await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

    async def cmd_pnl(self, message: Message,
                      chat_name_width: int = 17,
                      pnl_width: int = 12):
        """Handle /pnl command, send current data to Telegram group."""
        data = await self.data_storage.get_pnl_data()

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

    async def cmd_stats(self, message: Message,
                        chat_name_width: int = 17,
                        pnl_width: int = 12):
        """Handle /stats command, send current data to Telegram group."""
        data = await self.data_storage.get_stats_data()

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

    async def cmd_help(self, message: Message):
        """Handle /help command, list all available commands."""
        help_message = (
            "Here are the available commands:\n\n"
            "/pnl - Displays the current PNL data (a JSON with PNLs from different Telegram channels and their total PNL).\n\n"
            "/help - Displays this help message with a list of available commands."
        )
        await message.answer(help_message)

    def get_bot(self):
        """Get the async bot instance"""
        return self.async_bot

    def get_dispatcher(self):
        """Get the dispatcher"""
        return self.dp

    def is_bot_available(self):
        """Check if bot is available for use"""
        return self.use_bot

    async def close_bot(self):
        """Close bot session"""
        try:
            await self.async_bot.session.close()
        except Exception as e:
            print(f"Error closing bot session: {e}\n")