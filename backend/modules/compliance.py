import json
import os

DATA_FILE = 'compliance_data.json'

def load_compliance_data(user_id=None):
    """
    Loads client data.
    - If user_id is provided: Returns ONLY that user's clients.
    - If user_id is None (Admin view): Returns ALL clients from EVERYONE flattened into one list.
    """
    if not os.path.exists(DATA_FILE):
        return []
    
    try:
        with open(DATA_FILE, 'r') as f:
            all_data = json.load(f)

        # Handle migration from old format (list) to new format (dict)
        if isinstance(all_data, list):
            # If it's the old list format, return it only if no user_id is specified,
            # or return empty for specific users to start fresh.
            # Ideally, you'd migrate this, but starting fresh for specific users is safer.
            return all_data if user_id is None else []

        if user_id:
            # Return specific user's data
            return all_data.get(str(user_id), [])
        else:
            # Admin View: Combine all lists
            master_list = []
            for uid, clients in all_data.items():
                master_list.extend(clients)
            return master_list

    except:
        return []

def save_compliance_data(user_id, clients):
    """Saves the list of clients for a SPECIFIC user."""
    if not user_id:
        return {"success": False, "error": "User ID required"}

    all_data = {}
    
    # Load existing data first
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                content = json.load(f)
                if isinstance(content, dict):
                    all_data = content
                # If it was a list (old format), we overwrite it with the new dict structure
        except:
            pass

    # Update this specific user's list
    all_data[str(user_id)] = clients
    
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(all_data, f, indent=4)
        return {"success": True, "message": "Saved successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}