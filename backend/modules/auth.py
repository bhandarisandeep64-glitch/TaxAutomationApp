import json
import os

# --- FIX: USE ABSOLUTE PATH ---
# This gets the folder where THIS file (auth.py) lives
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# This goes one step back to the ROOT folder (Black Rose Inc folder)
BASE_DIR = os.path.dirname(CURRENT_DIR)
# Now we lock the file path to the root. It will never move.
USER_DATA_FILE = os.path.join(BASE_DIR, 'users_data.json')

def load_users():
    """Loads users from JSON. Creates default Admin if missing."""
    # Check if file exists at the ABSOLUTE path
    if not os.path.exists(USER_DATA_FILE):
        env_user = os.environ.get("ADMIN_USER", "admin")
        env_pass = os.environ.get("ADMIN_PASS", "123")
        
        default_users = [
            {
                "id": 99, 
                "username": env_user, 
                "password": env_pass, 
                "name": "Super Admin", 
                "role": "admin", 
                "status": "Active",
                "restrictedModules": [] 
            },
            {
                "id": 1, 
                "username": "user", 
                "password": "123", 
                "name": "John Doe", 
                "role": "user", 
                "status": "Active",
                "restrictedModules": ["indirect_tax"] 
            }
        ]
        save_users(default_users)
        return default_users
    
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    """Saves user list to JSON."""
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def authenticate_user(username, password):
    """Checks credentials against Env Vars first, then JSON file."""
    
    # 1. Master Admin Check (Environment Override)
    env_user = os.environ.get("ADMIN_USER", "admin")
    env_pass = os.environ.get("ADMIN_PASS", "123")

    if username == env_user and password == env_pass:
        return {
            "success": True, 
            "user": {
                "id": 0,
                "username": env_user,
                "name": "Master Admin (Env)",
                "role": "admin",
                "status": "Active",
                "restrictedModules": []
            }
        }

    # 2. Standard User Check (File Based)
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            if user.get('status') == 'Restricted':
                return {"success": False, "error": "Account is Restricted. Contact Admin."}
            return {"success": True, "user": user}
            
    return {"success": False, "error": "Invalid Username or Password"}