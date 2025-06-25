"""
Telegram command handlers for CryptoPulse bot.
"""

import re
import prettytable as pt
from aiogram import html
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode
from cryptopulse.core.data_persistence import load_data, PNL_FILE_PATH, STATS_FILE_PATH


class CommandHandlers:
    """Handles all bot commands."""
    
    def __init__(self, router, chat_id_name_dict):
        self.router = router
        self.chat_id_name_dict = chat_id_name_dict
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up command handlers."""
        @self.router.message(CommandStart())
        async def command_start_handler(message: Message) -> None:
            await self.handle_start(message)
        
        @self.router.message(Command("pnl"))
        async def cmd_pnl(message: Message):
            await self.handle_pnl(message)
        
        @self.router.message(Command("stats"))
        async def cmd_stats(message: Message):
            await self.handle_stats(message)
        
        @self.router.message(Command("help"))
        async def cmd_help(message: Message):
            await self.handle_help(message)
    
    async def handle_start(self, message: Message) -> None:
        """Handle /start command."""
        await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")
    
    async def handle_pnl(self, message: Message, chat_name_width: int = 17, pnl_width: int = 12):
        """Handle /pnl command."""
        data = await load_data(PNL_FILE_PATH)
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
    
    async def handle_stats(self, message: Message, chat_name_width: int = 17, pnl_width: int = 12):
        """Handle /stats command."""
        data = await load_data(STATS_FILE_PATH)
        
        if not data:
            await message.answer("No trading statistics available yet.")
            return
        
        table = pt.PrettyTable(['Metric', 'Value'])
        table.align['Metric'] = 'l'
        table.align['Value'] = 'r'
        table.max_width['Metric'] = chat_name_width
        table.max_width['Value'] = pnl_width

        table_title = "Trading Statistics"
        table.add_row(["Total Trades", str(data.get("total_trades", 0))])
        table.add_row(["Total PNL", f"${data.get('total_pnl', 0):.2f}"])
        table.add_row(["Winning Trades", str(data.get("winning_trades", 0))])
        table.add_row(["Losing Trades", str(data.get("losing_trades", 0))])
        table.add_row(["Win Rate", f"{data.get('win_rate', 0):.1f}%"])
        table.add_row(["Best Trade", f"${data.get('best_trade', 0):.2f}"])
        table.add_row(["Worst Trade", f"${data.get('worst_trade', 0):.2f}"])

        await message.answer(f'<b>{table_title}:</b>\n<pre>{table}</pre>',
                           parse_mode=ParseMode.HTML)
    
    async def handle_help(self, message: Message):
        """Handle /help command."""
        help_message = (
            "Here are the available commands:\n\n"
            "/start - Start the bot\n"
            "/pnl - Displays the current PNL data from different Telegram channels\n"
            "/stats - Shows detailed trading statistics\n"
            "/help - Displays this help message with a list of available commands"
        )
        await message.answer(help_message)


async def set_commands(bot):
    """Set bot commands."""
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/pnl", description="Displays the current PNL data from Telegram channels"),
        BotCommand(command="/stats", description="Shows detailed trading statistics"),
        BotCommand(command="/help", description="Displays available commands")
    ]
    await bot.set_my_commands(commands)