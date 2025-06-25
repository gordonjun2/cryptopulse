import json
import asyncio
import aiofiles


class DataStorage:
    def __init__(self, pnl_file_path="pnl_data.json", stats_file_path="stats_data.json"):
        self.pnl_file_path = pnl_file_path
        self.stats_file_path = stats_file_path
        self.lock = asyncio.Lock()

    async def load_data(self, file_path):
        """Load JSON data asynchronously without acquiring the lock."""
        try:
            async with aiofiles.open(file_path, "r") as f:
                contents = await f.read()
                return json.loads(contents)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def save_data(self, data, file_path):
        """Save JSON data asynchronously."""
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=4))

    async def update_pnl_data(self, new_data):
        """Load, update by summing values, and save JSON data with a lock."""
        async with self.lock:
            data = await self.load_data(self.pnl_file_path)
            key, value = list(new_data.items())[0]
            data[key] = round(data.get(key, 0) + value, 2)
            await self.save_data(data, self.pnl_file_path)

    async def update_stats_data(self, pnl):
        """Load, update by summing values, and save JSON data with a lock."""
        async with self.lock:
            data = await self.load_data(self.stats_file_path)
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

            await self.save_data(data, self.stats_file_path)

    async def get_pnl_data(self):
        """Get current PnL data"""
        return await self.load_data(self.pnl_file_path)

    async def get_stats_data(self):
        """Get current stats data"""
        return await self.load_data(self.stats_file_path)