from fastapi import FastAPI, UploadFile, Form, HTTPException, Security, Query
from fastapi.middleware.cors import CORSMiddleware
import uuid
from fastapi.responses import FileResponse
from translate import (
    translate_file,
    active_translations,
    get_translation_status, 
    get_available_languages
)
from db import save_feedback, save_file, get_file_count
import os
from datetime import datetime
import asyncio
from functions import parse_ass_file
from fastapi.security.api_key import APIKeyHeader
from api import is_valid_api_key
from typing import List
from cleanup import schedule_cleanup
import time

not_translated_folder = "not_translated_files"
if not os.path.exists(not_translated_folder):
    os.makedirs(not_translated_folder)
translated_folder = "translated_files"
if not os.path.exists(translated_folder):
    os.makedirs(translated_folder)

# Use asyncio.Queue for the translation queue
translation_queue = asyncio.Queue()
background_task = None


async def process_queue():
    while True:
        try:
            # Get item from queue with timeout to prevent blocking
            try:
                file_id, file_path, target_lang = await asyncio.wait_for(
                    translation_queue.get(), timeout=60
                )
                print(f"Processing file: {file_id} -> {target_lang}")
            except asyncio.TimeoutError:
                continue

            try:
                # Update status before starting translation
                from translate import translation_status
                translation_status[file_id] = {
                    "status": "pending",
                    "queue_position": len(active_translations),
                    "completed": 0,
                    "total": 0,
                    "target_language": target_lang,
                    "start_time": time.time()
                }

                # Start translation
                await translate_file(file_id, file_path, target_lang)
                
            except Exception as translate_error:
                print(f"Error translating file {file_id}: {translate_error}")
                # Update status on error
                translation_status[file_id] = {
                    "status": "error",
                    "error_message": str(translate_error)
                }
            finally:
                translation_queue.task_done()
                
        except asyncio.CancelledError:
            print("Shutting down process_queue gracefully...")
            break
        except Exception as e:
            print(f"Unexpected error in process_queue: {str(e)}")
            # Brief pause to prevent tight error loop
            await asyncio.sleep(1)


api_key_header = APIKeyHeader(name="X-API-Key")

async def validate_api_key(api_key: str = Security(api_key_header)):
    if not await is_valid_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

app = FastAPI(
    title="NotTranslate API",
    description="API for translating subtitle files",
    version="0.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global background_task
    background_task = asyncio.create_task(process_queue())
    asyncio.create_task(schedule_cleanup())
    print("Background task started.")

@app.on_event("shutdown")
async def shutdown_event():
    global background_task
    print("Waiting for queue to finish...")
    await translation_queue.join()

    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            print("Background task cancelled successfully.")
    print("Application shutdown complete.")

    print("Shutting down completed.")

@app.get("/languages", response_model=List[str])
async def available_languages():
    """Get list of available target languages for translation"""
    return get_available_languages()

@app.post("/translate")
async def translate(
    file: UploadFile, 
    target_lang: str = Query("en-cs", description="Target language code"),
    api_key: str = Security(api_key_header)
):
    await validate_api_key(api_key)
    
    if target_lang not in get_available_languages():
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported target language. Available languages: {', '.join(get_available_languages())}"
        )
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension != '.ass':
        raise HTTPException(
            status_code=400,
            detail="Only .ass subtitle files are supported"
        )
    
    content = await file.read()
    file_id = str(uuid.uuid4())
    file_path = os.path.join(not_translated_folder, f"{file_id}{file_extension}")
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    creation_time = datetime.utcnow()
    await save_file(file_id, creation_time, False, False)
    
    # Put the item in the queue with all required parameters
    await translation_queue.put((file_id, file_path, target_lang))
    
    
    return {
        "file_id": file_id,
        "status": "queued",
        "target_language": target_lang
    }

@app.get("/get-file/{file_id}")
async def get_file(file_id: str):
    """Download translated file by ID"""
    file_path = os.path.join(translated_folder, f"{file_id}.ass")
    if os.path.exists(file_path):
        return FileResponse(
            file_path, 
            media_type='application/octet-stream', 
            filename=f"{file_id}.ass"
        )
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/get-file-content/{file_id}")
async def get_file_content(file_id: str):
    """Get original and translated content as paired subtitles"""
    file_path = os.path.join(translated_folder, f"{file_id}.ass")
    original_file_path = os.path.join(not_translated_folder, f"{file_id}.ass")
    
    if not (os.path.exists(file_path) and os.path.exists(original_file_path)):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            translated_content = f.read()
        with open(original_file_path, "r", encoding="utf-8") as f:
            original_content = f.read()
            
        original_subtitles = parse_ass_file(original_content)
        translated_subtitles = parse_ass_file(translated_content)
        
        subtitle_pairs = []
        for orig, trans in zip(original_subtitles, translated_subtitles):
            subtitle_pairs.append({
                "original": orig,
                "translated": trans,
                "id": len(subtitle_pairs)
            })
            
        return {"subtitles": subtitle_pairs}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file content: {str(e)}"
        )

@app.get("/translation-status/{file_id}")
async def get_status(file_id: str):
    """Get current translation status, including queue position and ETA"""
    status = get_translation_status(file_id)
    if not status:
        raise HTTPException(status_code=404, detail="Translation not found")
    return status

@app.post("/feedback")
async def feedback(
    original_text: str = Form(...),
    translated_text: str = Form(...),
    corrected_text: str = Form(None),
    original_language: str = Form(...),
    target_language: str = Form(...),
    rating: int = Form(...),
    file_id: str = Form(None)
):
    """Submit feedback for a translation"""
    if rating not in range(1, 6):
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5"
        )
        
    try:
        await save_feedback(
            original_text=original_text,
            translated_text=translated_text,
            corrected_text=corrected_text,
            original_language=original_language,
            target_language=target_language,
            rating=rating,
            file_id=file_id or str(uuid.uuid4()),
            created_at=datetime.utcnow(),
        )
        return {"status": "Feedback saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def stats():
    """Get global translation statistics"""
    try:
        files_count = await get_file_count()
        return {
            "files_count": files_count,
            "available_languages": get_available_languages()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )