import json
import asyncio
import aiofiles
from typing import Dict, Any, Optional


class DataManager:
    """Handles data persistence and management operations"""
    
    def __init__(self):
        self.pnl_file = "pnl_data.json"
        self.stats_file = "stats_data.json"
        self.lock = asyncio.Lock()
    
    async def load_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load data from JSON file asynchronously"""
        try:
            async with aiofiles.open(file_path, 'r') as file:
                content = await file.read()
                return json.loads(content)
        except FileNotFoundError:
            print(f"File {file_path} not found, returning empty dict")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path}: {e}")
            return {}
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
            return {}
    
    async def save_data(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save data to JSON file asynchronously"""
        try:
            async with aiofiles.open(file_path, 'w') as file:
                content = json.dumps(data, indent=4)
                await file.write(content)
            return True
        except Exception as e:
            print(f"Error saving data to {file_path}: {e}")
            return False
    
    async def update_pnl_data(self, new_data: Dict[str, float]) -> bool:
        """Update P&L data with new trade results"""
        async with self.lock:
            try:
                current_data = await self.load_data(self.pnl_file) or {}
                
                for chat_id, pnl in new_data.items():
                    if chat_id in current_data:
                        current_data[chat_id] += pnl
                    else:
                        current_data[chat_id] = pnl
                
                return await self.save_data(current_data, self.pnl_file)
            except Exception as e:
                print(f"Error updating P&L data: {e}")
                return False
    
    async def update_stats_data(self, pnl: float) -> bool:
        """Update overall statistics with new trade result"""
        async with self.lock:
            try:
                stats_data = await self.load_data(self.stats_file)
                
                # Initialize stats if not present
                if not stats_data:
                    stats_data = {
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "total_pnl": 0.0,
                        "average_pnl": 0.0,
                        "win_rate": 0.0
                    }
                
                # Update stats
                stats_data["total_trades"] += 1
                stats_data["total_pnl"] += pnl
                
                if pnl > 0:
                    stats_data["winning_trades"] += 1
                elif pnl < 0:
                    stats_data["losing_trades"] += 1
                
                # Calculate derived metrics
                stats_data["average_pnl"] = stats_data["total_pnl"] / stats_data["total_trades"]
                stats_data["win_rate"] = (stats_data["winning_trades"] / stats_data["total_trades"]) * 100
                
                return await self.save_data(stats_data, self.stats_file)
            except Exception as e:
                print(f"Error updating stats data: {e}")
                return False
    
    async def get_pnl_data(self) -> Dict[str, float]:
        """Get current P&L data"""
        return await self.load_data(self.pnl_file) or {}
    
    async def get_stats_data(self) -> Dict[str, Any]:
        """Get current statistics data"""
        return await self.load_data(self.stats_file) or {}
    
    async def reset_pnl_data(self) -> bool:
        """Reset P&L data to empty state"""
        return await self.save_data({}, self.pnl_file)
    
    async def reset_stats_data(self) -> bool:
        """Reset statistics data to initial state"""
        initial_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "average_pnl": 0.0,
            "win_rate": 0.0
        }
        return await self.save_data(initial_stats, self.stats_file)