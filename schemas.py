from pydantic import BaseModel, Field
from fastapi import UploadFile
from typing import Optional

class FeedbackRequest(BaseModel):
    original_text: str = Field(..., description="Original text provided by the user")
    translated_text: str = Field(..., description="Translated version of the text")
    corrected_text: Optional[str] = Field(None, description="Corrected version of the translated text")
    original_language: str = Field(..., description="Language of the original text")
    target_language: str = Field(..., description="Language for translation")
    rating: int = Field(..., description="User rating for the translation quality")
    file_id: Optional[str] = Field(None, description="ID of the related file")

    class Config:
        schema_extra = {
            "example": {
                "original_text": "Hello, world!",
                "translated_text": "Bonjour, le monde!",
                "corrected_text": "Bonjour, monde!",
                "original_language": "en",
                "target_language": "fr",
                "rating": 5,
                "file_id": "12345abcd",
            }
        }


class TranslateRequest(BaseModel):
    target_lang: str = Field(..., description="Target language code in the format 'source-target', e.g., 'en-cs'.")
    file: UploadFile = Field(..., description="File to be translated")