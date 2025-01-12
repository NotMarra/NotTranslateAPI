from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
from fastapi.responses import FileResponse
from translate import translate_file, get_translation_status
from db import save_feedback, save_file, get_file_count
import os
from datetime import datetime
import asyncio
from functions import parse_ass_file

not_translated_folder = "not_translated_files"
if not os.path.exists(not_translated_folder):
    os.makedirs(not_translated_folder)
translated_folder = "translated_files"
if not os.path.exists(translated_folder):
    os.makedirs(translated_folder)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/translate")
async def translate(file: UploadFile):
    content = await file.read()
    print(f"Received file with {len(content)} bytes")
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    file_path = os.path.join(not_translated_folder, f"{file_id}{file_extension}")
    with open(file_path, "wb") as f:
        f.write(content)
    creation_time = datetime.utcnow()
    await save_file(file_id, creation_time, False, False)
    asyncio.create_task(translate_file(file_id, file_path))
    return {
        "file_id": file_id
    }

@app.get("/get-file/{file_id}")
async def get_file(file_id: str):
    file_path = os.path.join(translated_folder, f"{file_id}.ass")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/octet-stream', filename=f"{file_id}.ass")
    else:
        return {"error": "File not found"}

@app.get("/get-file-content/{file_id}")
async def get_file_content(file_id: str):
    file_path = os.path.join(translated_folder, f"{file_id}.ass")
    original_file_path = os.path.join(not_translated_folder, f"{file_id}.ass")
    
    if os.path.exists(file_path) and os.path.exists(original_file_path):
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
    else:
        return {"error": "File not found"}

@app.get("/translation-status/{file_id}")
async def get_status(file_id: str):
    return get_translation_status(file_id)

@app.post("/feedback")
async def feedback(
    original_text: str = Form(...),
    translated_text: str = Form(...),
    corrected_text: str = Form(None),
    rating: int = Form(...),
    file_id: str = Form(None) 
):
    try:
        await save_feedback(
            original_text=original_text,
            translated_text=translated_text,
            corrected_text=corrected_text,
            rating=rating,
            file_id=file_id or str(uuid.uuid4()),  
            created_at=datetime.utcnow(),
        )
        return {"status": "Feedback saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def stats():
    files_count = await get_file_count()
    return {
        "files_count": files_count
    }