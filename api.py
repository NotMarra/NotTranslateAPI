from pocketbase import PocketBase
import os
from dotenv import load_dotenv
import logging

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

PB_URL = os.getenv("PB_URL")
PB_KEY = os.getenv("PB_KEY")

PB_CLIENT = PocketBase(PB_URL)
PB_CLIENT.http_client.headers.update({"x_server_key": PB_KEY})

async def is_valid_api_key(api_key: str) -> bool:
    try:
        logger.debug(f"Validating API key: {api_key[:4]}...")
        
        result = PB_CLIENT.collection("api_keys").get_list(
            1, 
            50, 
            {"filter": f"key='{api_key}' && enabled=true"}
        )
        
        if result.items:
            first_key = result.items[0]
            logger.debug(f"Found matching API key record. Name: {getattr(first_key, 'name', 'N/A')}")
            return True
        
        logger.debug("No matching API key found")
        return False
        
    except Exception as e:
        error_details = getattr(e, 'response', {})
        if hasattr(error_details, 'json'):
            try:
                json_error = error_details.json()
                logger.error(f"PocketBase error details: {json_error}")
            except:
                pass
        logger.error(f"Error validating API key: {str(e)}")
        return False