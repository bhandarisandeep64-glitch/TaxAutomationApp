import json
import os

USER_DATA_FILE = 'users_data.json'

def load_users():
    """Loads users from JSON. Creates default Admin if missing."""
    if not os.path.exists(USER_DATA_FILE):
        # NOW USES ENVIRONMENT VARIABLES FOR DEFAULT CREATION
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
    except:
        return False

def authenticate_user(username, password):
    """Checks credentials against Env Vars first, then JSON file."""
    
    # --- SECURITY UPGRADE: CHECK ENVIRONMENT VARIABLES FIRST ---
    # This allows the Master Admin to login even if the JSON file is old/broken
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
    # -----------------------------------------------------------

    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            if user.get('status') == 'Restricted':
                return {"success": False, "error": "Account is Restricted. Contact Admin."}
            return {"success": True, "user": user}
            
    return {"success": False, "error": "Invalid Username or Password"}