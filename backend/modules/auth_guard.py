from functools import wraps

from flask import request, jsonify, g

from modules.auth import verify_token


def _extract_token():
    header = request.headers.get('Authorization', '')
    if header.startswith('Bearer '):
        return header[len('Bearer '):].strip()
    return None


def require_auth(fn):
    """Rejects the request unless it carries a valid, unexpired bearer token."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = verify_token(_extract_token())
        if not payload:
            return jsonify({"error": "Authentication required"}), 401
        g.current_user = payload
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    """Rejects the request unless it carries a valid token belonging to an admin."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = verify_token(_extract_token())
        if not payload:
            return jsonify({"error": "Authentication required"}), 401
        if payload.get('role') != 'admin':
            return jsonify({"error": "Admin privileges required"}), 403
        g.current_user = payload
        return fn(*args, **kwargs)
    return wrapper
