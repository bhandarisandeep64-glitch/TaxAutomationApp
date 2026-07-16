import hmac
import os

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from models import User

TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24  # 24 hours


def _serializer():
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY environment variable is not set")
    return URLSafeTimedSerializer(secret, salt="auth-token")


def load_users():
    """Every user as a dict, including the password hash -- internal/admin use only."""
    return [u.to_dict(include_password=True) for u in User.query.order_by(User.id).all()]


def public_user(user):
    """Strips the password hash out of a user dict before it ever leaves the server."""
    return {k: v for k, v in user.items() if k != 'password'}


def authenticate_user(username, password):
    """Checks credentials against the env master admin first, then the database."""

    # 1. Master Admin Check (Environment Override) - constant-time compare
    env_user = os.environ.get("ADMIN_USER", "")
    env_pass = os.environ.get("ADMIN_PASS", "")

    if env_user and env_pass and hmac.compare_digest(username, env_user) and hmac.compare_digest(password, env_pass):
        user = {
            "id": 0,
            "username": env_user,
            "name": "Master Admin (Env)",
            "role": "admin",
            "status": "Active",
            "restrictedModules": []
        }
        return {"success": True, "user": user, "token": generate_token(user)}

    # 2. Standard User Check (DB, hashed passwords)
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        if user.status == 'Restricted':
            return {"success": False, "error": "Account is Restricted. Contact Admin."}
        safe_user = user.to_dict()
        return {"success": True, "user": safe_user, "token": generate_token(safe_user)}

    return {"success": False, "error": "Invalid Username or Password"}


def create_user(data):
    """Creates a new user with a hashed password. Used by the admin dashboard."""
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return {"success": False, "error": "Username and password are required"}

    if User.query.filter_by(username=username).first():
        return {"success": False, "error": "Username already exists"}

    user = User(
        username=username,
        password=generate_password_hash(password),
        name=data.get('name', username),
        role=data.get('role', 'user'),
        status=data.get('status', 'Active'),
        restricted_modules=data.get('restrictedModules', []),
    )
    db.session.add(user)
    db.session.commit()
    return {"success": True, "user": user.to_dict()}


def update_user(user_id, updates):
    """Partially updates a user (name, status, restrictedModules, role, and
    optionally password). Only fields present in `updates` are touched."""
    user = db.session.get(User, user_id)
    if not user:
        return {"success": False, "error": "User not found"}

    if 'name' in updates:
        user.name = updates['name']
    if 'status' in updates:
        user.status = updates['status']
    if 'restrictedModules' in updates:
        user.restricted_modules = updates['restrictedModules']
    if 'role' in updates:
        user.role = updates['role']
    if updates.get('password'):
        user.password = generate_password_hash(updates['password'])

    db.session.commit()
    return {"success": True, "user": user.to_dict()}


def delete_user(user_id):
    """Removes a user by id."""
    user = db.session.get(User, user_id)
    if not user:
        return {"success": False, "error": "User not found"}
    db.session.delete(user)
    db.session.commit()
    return {"success": True}


def generate_token(user):
    """Issues a signed, expiring token carrying just enough identity to authorize requests."""
    payload = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }
    return _serializer().dumps(payload)


def verify_token(token):
    """Returns the decoded payload for a valid, unexpired token, or None."""
    if not token:
        return None
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
