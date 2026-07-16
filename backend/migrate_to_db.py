"""One-time migration: existing JSON files -> Postgres.

Run once, locally, after DATABASE_URL is set in backend/.env:
    python migrate_to_db.py

Safe to re-run: existing rows (matched by id / user_id) are left untouched.
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask

from database import init_db, db
from models import User, ChatMessage, ComplianceRecord

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _reset_sequence(table, column='id'):
    """After inserting rows with explicit ids, point the auto-increment
    sequence past the highest one so future INSERTs don't collide."""
    db.session.execute(db.text(
        f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), "
        f"COALESCE((SELECT MAX({column}) FROM {table}), 1))"
    ))


def migrate_users():
    path = os.path.join(BASE_DIR, 'users_data.json')
    if not os.path.exists(path):
        print("No users_data.json found, skipping users.")
        return

    with open(path) as f:
        users = json.load(f)

    migrated = 0
    for u in users:
        if db.session.get(User, u['id']):
            continue
        db.session.add(User(
            id=u['id'],
            username=u['username'],
            password=u['password'],  # already hashed
            name=u.get('name', u['username']),
            role=u.get('role', 'user'),
            status=u.get('status', 'Active'),
            restricted_modules=u.get('restrictedModules', []),
        ))
        migrated += 1

    db.session.commit()
    _reset_sequence('users')
    db.session.commit()
    print(f"Users: migrated {migrated} of {len(users)} (rest already present).")


def migrate_chat():
    path = os.path.join(BASE_DIR, 'chat_data.json')
    if not os.path.exists(path):
        print("No chat_data.json found, skipping chat messages.")
        return

    with open(path) as f:
        messages = json.load(f)

    migrated = 0
    for m in messages:
        if db.session.get(ChatMessage, m['id']):
            continue
        db.session.add(ChatMessage(
            id=m['id'],
            username=m.get('username', 'Anonymous'),
            content=m.get('content', ''),
            type=m.get('type', 'general'),
            timestamp=m.get('timestamp', ''),
            read=m.get('read', False),
        ))
        migrated += 1

    db.session.commit()
    _reset_sequence('chat_messages')
    db.session.commit()
    print(f"Chat messages: migrated {migrated} of {len(messages)} (rest already present).")


def migrate_compliance():
    path = os.path.join(BASE_DIR, 'compliance_data.json')
    if not os.path.exists(path):
        print("No compliance_data.json found, skipping compliance data.")
        return

    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("compliance_data.json is in the old list format -- nothing to migrate per-user.")
        return

    migrated = 0
    for user_id, clients in data.items():
        if db.session.get(ComplianceRecord, str(user_id)):
            continue
        db.session.add(ComplianceRecord(user_id=str(user_id), clients=clients))
        migrated += 1

    db.session.commit()
    print(f"Compliance records: migrated {migrated} of {len(data)} (rest already present).")


if __name__ == '__main__':
    app = Flask(__name__)
    init_db(app)
    with app.app_context():
        migrate_users()
        migrate_chat()
        migrate_compliance()
    print("Migration complete.")
