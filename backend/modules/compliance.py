from database import db
from models import ComplianceRecord


def load_compliance_data(user_id=None):
    """
    Loads client data.
    - If user_id is provided: Returns ONLY that user's clients.
    - If user_id is None (Admin view): Returns ALL clients from EVERYONE flattened into one list.
    """
    if user_id:
        record = db.session.get(ComplianceRecord, str(user_id))
        return record.clients if record else []

    master_list = []
    for record in ComplianceRecord.query.all():
        master_list.extend(record.clients or [])
    return master_list


def save_compliance_data(user_id, clients):
    """Saves the list of clients for a SPECIFIC user."""
    if not user_id:
        return {"success": False, "error": "User ID required"}

    record = db.session.get(ComplianceRecord, str(user_id))
    if record:
        record.clients = clients
    else:
        record = ComplianceRecord(user_id=str(user_id), clients=clients)
        db.session.add(record)

    try:
        db.session.commit()
        return {"success": True, "message": "Saved successfully"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
