from transformers import pipeline
import asyncio
from typing import Dict

translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-cs")

# Globální slovník pro sledování stavu překladů
translation_status: Dict[str, Dict] = {}

async def translate_file(file_id: str, file_path: str):
    content = open(file_path, "r", encoding="utf-8-sig").read()
    total_lines = len(content.split("\n"))
    translated_lines = 0
    translations = []
    
    # Inicializace stavu
    translation_status[file_id] = {
        "total": total_lines,
        "completed": 0,
        "status": "in_progress"
    }

    lines = content.split("\n")
    for line in lines:
        if "Dialogue:" in line:
            parts = line.split(",", 9)
            if len(parts) > 9:
                original = parts[9]
                translated = translator(original)[0]["translation_text"]
                translations.append((original, translated))
                
                # Aktualizace stavu
                translated_lines += 1
                translation_status[file_id]["completed"] = translated_lines
                
                # Simulace delšího překladu pro testování
                await asyncio.sleep(0.1)
    
    # Uložení přeloženého souboru do složky "translated_files"
    translated_content = content
    for original, translated in translations:
        translated_content = translated_content.replace(original, translated)
    translated_file_path = file_path.replace("not_translated_files", "translated_files")
    with open(translated_file_path, "w", encoding="utf-8") as f:
        f.write(translated_content)
        
    translation_status[file_id]["status"] = "completed"

def get_translation_status(file_id: str):
    return translation_status.get(file_id, {
        "total": 0,
        "completed": 0,
        "status": "not_found"
    })