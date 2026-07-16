from datetime import datetime

from database import db
from models import ChatMessage


def load_messages():
    """Loads all messages, sorted by newest first."""
    messages = ChatMessage.query.order_by(ChatMessage.id.desc()).all()
    return [m.to_dict() for m in messages]


def save_message(data):
    """Saves a new message from a user."""
    message = ChatMessage(
        username=data.get('username', 'Anonymous'),
        content=data.get('content', ''),
        type=data.get('type', 'general'),  # 'access_request', 'system', or 'general'
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        read=False,
    )
    try:
        db.session.add(message)
        db.session.commit()
        return {"success": True, "message": "Request sent successfully."}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
