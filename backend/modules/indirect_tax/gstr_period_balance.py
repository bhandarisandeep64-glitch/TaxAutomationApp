"""
Shared opening/closing ITC balance helpers -- used by both the Odoo and
Zoho GSTR-3B engines so a client's opening ITC each month auto-carries from
the previous period's closing balance instead of needing manual re-entry.
"""
from database import db
from models import GstrPeriodBalance


def get_opening_itc(owner_user_id, client_name, period, override=None):
    """Reads the closing balance from the period immediately before `period`
    for this client. Falls back to 0 if there's no prior record (first run
    for a new client) or if `override` is explicitly provided."""
    if override is not None:
        return override

    year, month = (int(x) for x in period.split('-'))
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_period = f"{prev_year:04d}-{prev_month:02d}"

    record = db.session.get(GstrPeriodBalance, (owner_user_id, client_name, prev_period))
    if record:
        return {'igst': record.closing_itc_igst, 'cgst': record.closing_itc_cgst, 'sgst': record.closing_itc_sgst}
    return {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0}


def save_closing_itc(owner_user_id, client_name, period, remaining):
    record = db.session.get(GstrPeriodBalance, (owner_user_id, client_name, period))
    if not record:
        record = GstrPeriodBalance(owner_user_id=owner_user_id, client_name=client_name, period=period)
        db.session.add(record)
    record.closing_itc_igst = remaining['igst']
    record.closing_itc_cgst = remaining['cgst']
    record.closing_itc_sgst = remaining['sgst']
    db.session.commit()
