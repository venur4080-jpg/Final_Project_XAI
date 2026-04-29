import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# List of API keys supplied by the user
USER_SUPPLIED_KEYS = [
    "AIzaSyAngc__ZWSN5JxG5vPvceJZtHxUCIcpKYg",
    "AIzaSyCS0su8aXyMp8ysgXh6o6eR8uTY7fWRh-I",
    "AIzaSyBIr1OvwVDo_vkv_5tb2yaDemcxgbWfAmc",
    "AIzaSyDn8eW89HOJLq8MabbqTjw5gI1cZY_4vTo"
]

# Extract potential .env key if present and add to rotation (skip duplicates)
API_KEYS = []
env_key = os.getenv("GEMINI_API_KEY")
if env_key and env_key not in API_KEYS and env_key not in USER_SUPPLIED_KEYS:
    API_KEYS.append(env_key)

for key in USER_SUPPLIED_KEYS:
    if key not in API_KEYS:
        API_KEYS.append(key)

current_key_idx = 0

# Initialize first client
def _get_active_client():
    if not API_KEYS:
        raise ValueError("No GEMINI_API_KEY found.")
    return genai.Client(api_key=API_KEYS[current_key_idx])

# Global instance initialized below
client = _get_active_client()

def _rotate_key():
    global current_key_idx, client
    current_key_idx = (current_key_idx + 1) % len(API_KEYS)
    print(f"[Gemini API Manager] Switching to next API key ({current_key_idx + 1}/{len(API_KEYS)})")
    client = _get_active_client()

def generate_content_with_retry(model, contents, max_retries=None):
    """
    Wrapper around client.models.generate_content that catches 429 quota errors
    and rotates the API key until exhausting all available keys.
    """
    global client
    
    if max_retries is None:
        max_retries = len(API_KEYS)
        
    for attempt in range(max_retries):
        try:
            # We explicitly pass contents. Depending on format, python SDK will handle list or string
            response = client.models.generate_content(
                model=model,
                contents=contents
            )
            return response
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg:
                print(f"[Gemini API Manager] Quota exceeded on key {current_key_idx + 1}. Attempting to rotate...")
                if attempt < max_retries - 1:
                    _rotate_key()
                else:
                    print("[Gemini API Manager] All Gemini API keys have exceeded their quota.")
                    # Re-raise so existing error handlers catch "429" fallback paths
                    raise Exception("429 All Gemini API keys have exhausted their quota limits.")
            else:
                # If it is another type of error (bad request, authentication failing), we bubble it up
                raise e
    
    # Should not reach here due to the raise inside the loop for the last max_retries
    raise Exception("429 Quota Exceeded across all keys")
