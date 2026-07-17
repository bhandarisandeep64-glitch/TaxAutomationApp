from database import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # werkzeug hash, never plaintext
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    status = db.Column(db.String(20), nullable=False, default='Active')
    restricted_modules = db.Column(db.JSON, nullable=False, default=list)

    def to_dict(self, include_password=False):
        data = {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "restrictedModules": self.restricted_modules or [],
        }
        if include_password:
            data["password"] = self.password
        return data


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='general')
    timestamp = db.Column(db.String(30), nullable=False)
    read = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "content": self.content,
            "type": self.type,
            "timestamp": self.timestamp,
            "read": self.read,
        }


class ComplianceRecord(db.Model):
    __tablename__ = 'compliance_records'

    user_id = db.Column(db.String(50), primary_key=True)
    clients = db.Column(db.JSON, nullable=False, default=list)


class GstrPeriodBalance(db.Model):
    """Closing ITC balance for a client at the end of a given period, read
    back as next period's opening ITC so it doesn't need re-entering by
    hand every month."""
    __tablename__ = 'gstr_period_balances'

    owner_user_id = db.Column(db.String(50), primary_key=True)
    client_name = db.Column(db.String(120), primary_key=True)
    period = db.Column(db.String(7), primary_key=True)  # 'YYYY-MM'

    closing_itc_igst = db.Column(db.Float, nullable=False, default=0.0)
    closing_itc_cgst = db.Column(db.Float, nullable=False, default=0.0)
    closing_itc_sgst = db.Column(db.Float, nullable=False, default=0.0)
