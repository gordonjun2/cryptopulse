"""
Data persistence utilities for CryptoPulse trading bot.
"""

import asyncio
import json
import aiofiles

# Settings
PNL_FILE_PATH = "pnl_data.json"
STATS_FILE_PATH = "stats_data.json"
lock = asyncio.Lock()


async def load_data(file_path):
    """Load JSON data asynchronously."""
    try:
        async with aiofiles.open(file_path, "r") as f:
            contents = await f.read()
            return json.loads(contents)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def save_data(data, file_path):
    """Save JSON data asynchronously."""
    async with aiofiles.open(file_path, "w") as f:
        await f.write(json.dumps(data, indent=4))


async def update_pnl_data(new_data):
    """Load, update PNL data by summing values, and save JSON data with a lock."""
    async with lock:
        data = await load_data(PNL_FILE_PATH)
        for key, value in new_data.items():
            data[key] = round(data.get(key, 0) + value, 2)
        await save_data(data, PNL_FILE_PATH)


async def update_stats_data(pnl):
    """Update stats data with new PNL."""
    async with lock:
        data = await load_data(STATS_FILE_PATH)
        
        # Initialize stats if empty
        if not data:
            data = {
                "total_trades": 0,
                "total_pnl": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "win_rate": 0.0
            }
        
        # Update stats
        data["total_trades"] += 1
        data["total_pnl"] = round(data["total_pnl"] + pnl, 2)
        
        if pnl > 0:
            data["winning_trades"] += 1
        elif pnl < 0:
            data["losing_trades"] += 1
        
        if pnl > data["best_trade"]:
            data["best_trade"] = round(pnl, 2)
        
        if pnl < data["worst_trade"]:
            data["worst_trade"] = round(pnl, 2)
        
        # Calculate win rate
        if data["total_trades"] > 0:
            data["win_rate"] = round((data["winning_trades"] / data["total_trades"]) * 100, 2)
        
        await save_data(data, STATS_FILE_PATH)