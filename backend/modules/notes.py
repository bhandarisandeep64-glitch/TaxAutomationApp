from database import db
from models import Note


def list_notes(owner_user_id, client_name=None):
    """All of this user's notes, optionally filtered to one client, newest
    first."""
    query = Note.query.filter_by(owner_user_id=str(owner_user_id))
    if client_name:
        query = query.filter_by(client_name=client_name)
    return [n.to_dict() for n in query.order_by(Note.created_at.desc()).all()]


def create_note(owner_user_id, client_name, content):
    if not client_name or not str(client_name).strip():
        return {"success": False, "error": "Client name is required."}
    if not content or not str(content).strip():
        return {"success": False, "error": "Note content is required."}

    note = Note(owner_user_id=str(owner_user_id), client_name=client_name.strip(), content=content.strip())
    db.session.add(note)
    try:
        db.session.commit()
        return {"success": True, "note": note.to_dict()}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def update_note(note_id, owner_user_id, content):
    note = Note.query.filter_by(id=note_id, owner_user_id=str(owner_user_id)).first()
    if not note:
        return {"success": False, "error": "Note not found."}
    if not content or not str(content).strip():
        return {"success": False, "error": "Note content is required."}

    note.content = content.strip()
    try:
        db.session.commit()
        return {"success": True, "note": note.to_dict()}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def delete_note(note_id, owner_user_id):
    note = Note.query.filter_by(id=note_id, owner_user_id=str(owner_user_id)).first()
    if not note:
        return {"success": False, "error": "Note not found."}

    db.session.delete(note)
    try:
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
