import json
import aiofiles
import asyncio
import random
import string

FILE_PATH = "store.json"
lock = asyncio.Lock()  # Global lock for safe access


async def load_data():
    """Load JSON data asynchronously without acquiring the lock."""
    try:
        async with aiofiles.open(FILE_PATH, "r") as f:
            contents = await f.read()
            return json.loads(contents)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return empty dict if file is missing or corrupted


async def save_data(data):
    """Save JSON data asynchronously."""
    async with aiofiles.open(FILE_PATH, "w") as f:
        await f.write(json.dumps(data, indent=4))


async def update_data(new_data):
    """Load, update, and save JSON data with a single lock acquisition."""
    async with lock:  # Lock acquired only once here
        data = await load_data()  # Load data without locking
        data.update(new_data)  # Update existing data
        await save_data(data)  # Save the updated data


async def generate_random_key_value():
    """Generate a random key-value pair."""
    key = ''.join(random.choices(string.ascii_letters,
                                 k=5))  # Random 5-letter key
    value = ''.join(random.choices(string.ascii_letters + string.digits,
                                   k=8))  # Random 8-char value
    return {key: value}


async def demo():
    """Run indefinitely, updating and replacing JSON data continuously."""
    print("🔹 Initial Load:", await load_data())

    while True:  # Infinite loop
        new_data = await generate_random_key_value()  # Generate new key-value
        await update_data(new_data)  # Replace with new data
        print(f"🔸 Updated JSON:", await load_data())  # Show updated JSON
        await asyncio.sleep(2)  # Wait 2 seconds before next update


# Run the async demo indefinitely
asyncio.run(demo())
