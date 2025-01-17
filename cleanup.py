from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import asyncio
import shutil

load_dotenv()
mongo_uri = os.getenv("MONGO_URL")
not_translated_path = "not_translated_files"
translated_path = "translated_files"

client = AsyncIOMotorClient(mongo_uri)
db = client["translation"]

async def cleanup_old_files():
    collection = db["files"]
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(seconds=30)
    old_files = collection.find({"created_at": {"$lt": thirty_days_ago}, "deleted": False})

    async for file in old_files:
        file_id = file["file_id"]

        not_translated_file = os.path.join(not_translated_path, file_id)
        translated_file = os.path.join(translated_path, file_id)

        try:
            # Log před pokusem o smazání složky
            print(f"Checking directories: {not_translated_file}, {translated_file}")

            # Mazání celé složky
            if os.path.exists(not_translated_file):
                shutil.rmtree(not_translated_file)
                print(f"Removed directory: {not_translated_file}")
            if os.path.exists(translated_file):
                shutil.rmtree(translated_file)
                print(f"Removed directory: {translated_file}")
        except Exception as e:
            print(f"Error deleting directory {file_id}: {e}")

        # Aktualizace v databázi
        await collection.update_one(
            {"file_id": file_id},
            {"$set": {"deleted": True}}
        )
        print(f"Marked as deleted in DB: {file_id}")

    print("Cleanup completed.")

async def schedule_cleanup():
    while True:
        now = datetime.utcnow()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_time = (midnight - now).total_seconds()

        print(f"Waiting for next cleanup at {midnight}...")
        await asyncio.sleep(wait_time)

        # Spuštění čištění
        await cleanup_old_files()
