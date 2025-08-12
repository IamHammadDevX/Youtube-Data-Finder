import os
import json

API_KEY_FILE = "apikey.json"

def get_api_key():
    """Load API key from file, or return empty string if not set."""
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            data = json.load(f)
            return data.get("YOUTUBE_API_KEY", "")
    return ""

def set_api_key(api_key):
    """Save the API key to file."""
    with open(API_KEY_FILE, "w") as f:
        json.dump({"YOUTUBE_API_KEY": api_key.strip()}, f)