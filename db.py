from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()  # Nejdřív načti environment variabely

mongo_uri = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = client["translation"]

# Asynchronní funkce pro uložení zpětné vazby
async def save_feedback(original_text, translated_text, corrected_text, rating, file_id, created_at, translated, deleted):
    feedback_collection = db["feedback"]

    feedback = {
        "original_text": original_text,
        "translated_text": translated_text,
        "corrected_text": corrected_text,
        "rating": rating,
        "file_id": file_id,
        "created_at": created_at,
        "translated": translated,
        "deleted": deleted
    }

    await feedback_collection.insert_one(feedback)

# Asynchronní funkce pro uložení souboru
async def save_file(file_id, created_at, translated, deleted):
    file_collection = db["files"]

    file_info = {
        "file_id": file_id,
        "created_at": created_at,
        "translated": translated,
        "deleted": deleted
    }

    await file_collection.insert_one(file_info)

# Asynchronní funkce pro získání souboru podle ID
async def get_file(file_id):
    file_collection = db["files"]
    file_info = await file_collection.find_one({"file_id": file_id})
    return file_info

# Asynchronní funkce pro získání všech souborů
async def get_files():
    file_collection = db["files"]

    files = []
    async for file in file_collection.find():
        files.append(file)
    return files

# Asynchronní funkce pro získání počtu záznamů v kolekci "files"
async def get_file_count():
    file_collection = db["files"]
    count = await file_collection.count_documents({})
    return count

# Asynchronní funkce pro získání zpětné vazby podle ID souboru
async def get_feedback(file_id):
    feedback_collection = db["feedback"]

    feedbacks = []
    async for feedback in feedback_collection.find({"file_id": file_id}):
        feedbacks.append(feedback)
    return feedbacks

# Asynchronní funkce pro získání počtu záznamů v kolekci "feedback"
async def get_feedback_count():
    feedback_collection = db["feedback"]
    count = await feedback_collection.count_documents({})
    return count
