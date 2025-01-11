from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(mongo_uri)
db = client["translation_feedback"]

async def cleanup_old_files():
    collection = db["translations"]
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Delete documents older than 1 hour
    result = await collection.delete_many({
        "created_at": {"$lt": one_hour_ago}
    })
    
    print(f"Deleted {result.deleted_count} old translations")

if __name__ == "__main__":
    asyncio.run(cleanup_old_files())