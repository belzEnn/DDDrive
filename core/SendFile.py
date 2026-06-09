import os
import aiofiles
import asyncio
from telethon.errors import FloodWaitError


async def Send(client, target, file_path):
    if os.path.exists(file_path):
        try:
            message = await client.send_file(target, file_path)
            print("File send!")
            print(message.id)
            return message
        except FloodWaitError as e:
            print(f"FloodWait: waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
            message = await client.send_file(target, file_path)
            print("File send!")
            print(message.id)
            return message


async def Split(file_path: str, chunk_size: int = 1 * 1024 * 1024):
    chunk_list = []
    async with aiofiles.open(file_path, "rb") as f:
        chunk_num = 0
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            fileNameOnly = os.path.splitext(file_path)
            chunk_name = f"{fileNameOnly[0]}{chunk_num}.ddd"
            async with aiofiles.open(chunk_name, "wb") as k:
                await k.write(chunk)
            chunk_list.append(chunk_name)
            chunk_num += 1
    return chunk_list