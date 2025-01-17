from transformers import pipeline
import asyncio
from typing import Dict
import os
import time
import logging

# Nastavení logování
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")

# Dictionary of available Helsinki-NLP models
AVAILABLE_MODELS = {
    "en-cs": "Helsinki-NLP/opus-mt-en-cs",
    "en-de": "Helsinki-NLP/opus-mt-en-de",
    "en-fr": "Helsinki-NLP/opus-mt-en-fr",
    "en-es": "Helsinki-NLP/opus-mt-en-es",
    "en-it": "Helsinki-NLP/opus-mt-en-it",
    "en-pl": "Helsinki-NLP/opus-mt-en-pl",
    "en-ru": "Helsinki-NLP/opus-mt-en-ru"
}

# Mapping for language names
LANGUAGE_NAMES = {
    "en-cs": "Czech",
    "en-de": "German",
    "en-fr": "French",
    "en-es": "Spanish",
    "en-it": "Italian",
    "en-pl": "Polish",
    "en-ru": "Russian"
}

translators = {}
translation_status: Dict[str, Dict] = {}
active_translations = []
AVERAGE_TIME_PER_LINE = 0.1

def initialize_translator(target_lang: str):
    if target_lang not in translators and target_lang in AVAILABLE_MODELS:
        translators[target_lang] = pipeline("translation", model=AVAILABLE_MODELS[target_lang])
    return translators.get(target_lang)

def get_queue_position(file_id: str) -> int:
    try:
        return active_translations.index(file_id)
    except ValueError:
        return -1

def create_info_dialogue(target_lang: str) -> str:
    language_name = LANGUAGE_NAMES.get(target_lang, target_lang.upper())
    
    return (
        f"Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,**** "
        f"Translated to {language_name} using NotTranslate | "
        f"For more information, visit translate.notmarra.com ****"
    )

async def translate_file(file_id: str, file_path: str, target_lang: str = "en-cs"):
    logging.debug(f"Starting translation for file: {file_id}, target language: {target_lang}")
    try:
        if file_id not in active_translations:
            active_translations.append(file_id)
        
        translator = initialize_translator(target_lang)
        if not translator:
            raise ValueError(f"Unsupported target language: {target_lang}")

        content = open(file_path, "r", encoding="utf-8-sig").read()
        lines = content.split("\n")
        total_lines = len(lines)
        dialogue_lines = sum(1 for line in lines if "Dialogue:" in line)
        translated_lines = 0
        
        # Initialize translations list
        translations = []
        
        start_time = time.time()
        
        translation_status[file_id] = {
            "total": total_lines,
            "dialogue_lines": dialogue_lines,
            "completed": 0,
            "status": "in_progress",
            "queue_position": get_queue_position(file_id),
            "target_language": target_lang,
            "start_time": start_time,
            "estimated_completion_time": start_time + (dialogue_lines * AVERAGE_TIME_PER_LINE),
            "eta_seconds": dialogue_lines * AVERAGE_TIME_PER_LINE
        }

        logging.debug(f"Translation status initialized: {translation_status[file_id]}")

        # Find position to insert info line (after style section, before first dialogue)
        insert_position = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("[Events]"):
                # Find the Format line that follows [Events]
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("Format:"):
                        insert_position = j + 1
                        break
                break

        # Create the translated content with information line
        translated_lines = lines[:insert_position]
        translated_lines.append(create_info_dialogue(target_lang))
        
        # Process and add remaining lines
        for line in lines[insert_position:]:
            if "Dialogue:" in line:
                parts = line.split(",", 9)
                if len(parts) > 9:
                    original = parts[9].strip()
                    translated = translator(original)[0]["translation_text"]
                    translations.append((original, translated))
                    line = line.replace(original, translated)
                    
                    translated_lines.append(line)
                    translated_lines_count = sum(1 for l in translated_lines if "Dialogue:" in l)
                    
                    current_time = time.time()
                    time_per_line = (current_time - start_time) / translated_lines_count
                    remaining_lines = dialogue_lines - translated_lines_count
                    
                    translation_status[file_id].update({
                        "completed": translated_lines_count,
                        "eta_seconds": remaining_lines * time_per_line,
                        "estimated_completion_time": current_time + (remaining_lines * time_per_line)
                    })
                    
                    await asyncio.sleep(AVERAGE_TIME_PER_LINE)
            else:
                translated_lines.append(line)

        # Save the translated file
        translated_file_path = file_path.replace("not_translated_files", "translated_files")
        with open(translated_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(translated_lines))
            
        translation_status[file_id].update({
            "status": "completed",
            "queue_position": -1,
            "completion_time": time.time()
        })

    except Exception as e:
        logging.error(f"Translation error for {file_id}: {str(e)}")
        translation_status[file_id] = {
            "status": "error",
            "error_message": str(e)
        }
        raise
    finally:
        if file_id in active_translations:
            active_translations.remove(file_id)


def get_translation_status(file_id: str):
    status = translation_status.get(file_id, {
        "total": 0,
        "completed": 0,
        "status": "not_found",
        "queue_position": -1,
        "eta_seconds": 0,
        "target_language": None
    })
    
    print(f"Status for {file_id}: {status}")  # Debugging line

    if status.get("status") in ["pending", "in_progress"]:
        status["queue_position"] = get_queue_position(file_id)
        
    return status


def get_available_languages():
    return list(AVAILABLE_MODELS.keys())