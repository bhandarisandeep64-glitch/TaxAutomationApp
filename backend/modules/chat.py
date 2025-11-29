import json
import os
from datetime import datetime

CHAT_FILE = 'chat_data.json'

def load_messages():
    """Loads all messages, sorted by newest first."""
    if not os.path.exists(CHAT_FILE):
        return []
    try:
        with open(CHAT_FILE, 'r') as f:
            data = json.load(f)
            # Sort by ID descending (newest first)
            return sorted(data, key=lambda x: x.get('id', 0), reverse=True)
    except:
        return []

def save_message(data):
    """Saves a new message from a user."""
    messages = load_messages()
    
    # Generate simple ID
    new_id = 1
    if messages:
        new_id = max(m.get('id', 0) for m in messages) + 1
        
    new_msg = {
        "id": new_id,
        "username": data.get('username', 'Anonymous'),
        "content": data.get('content', ''),
        "type": data.get('type', 'general'), # 'access_request' or 'general'
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "read": False
    }
    
    messages.append(new_msg)
    
    try:
        with open(CHAT_FILE, 'w') as f:
            json.dump(messages, f, indent=4)
        return {"success": True, "message": "Request sent successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}