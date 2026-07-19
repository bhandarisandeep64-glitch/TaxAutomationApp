import re

from database import db
from models import QuickLink

_URL_SCHEME_RE = re.compile(r'^https?://', re.IGNORECASE)


def _normalize_url(url):
    url = (url or '').strip()
    if url and not _URL_SCHEME_RE.match(url):
        url = 'https://' + url
    return url


def list_links(owner_user_id):
    """All of this user's links, grouped by category (insertion order per
    category preserved, categories in first-seen order) -- newest first
    within each category."""
    links = (QuickLink.query
             .filter_by(owner_user_id=str(owner_user_id))
             .order_by(QuickLink.created_at.desc())
             .all())

    grouped = {}
    for link in links:
        grouped.setdefault(link.category, []).append(link.to_dict())

    return [{"category": cat, "links": items} for cat, items in grouped.items()]


def create_link(owner_user_id, title, url, category):
    if not title or not str(title).strip():
        return {"success": False, "error": "Title is required."}
    if not url or not str(url).strip():
        return {"success": False, "error": "URL is required."}

    link = QuickLink(
        owner_user_id=str(owner_user_id),
        title=title.strip(),
        url=_normalize_url(url),
        category=(category or '').strip() or 'General',
    )
    db.session.add(link)
    try:
        db.session.commit()
        return {"success": True, "link": link.to_dict()}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def update_link(link_id, owner_user_id, title, url, category):
    link = QuickLink.query.filter_by(id=link_id, owner_user_id=str(owner_user_id)).first()
    if not link:
        return {"success": False, "error": "Link not found."}
    if title is not None:
        if not str(title).strip():
            return {"success": False, "error": "Title is required."}
        link.title = title.strip()
    if url is not None:
        if not str(url).strip():
            return {"success": False, "error": "URL is required."}
        link.url = _normalize_url(url)
    if category is not None:
        link.category = category.strip() or 'General'

    try:
        db.session.commit()
        return {"success": True, "link": link.to_dict()}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def delete_link(link_id, owner_user_id):
    link = QuickLink.query.filter_by(id=link_id, owner_user_id=str(owner_user_id)).first()
    if not link:
        return {"success": False, "error": "Link not found."}

    db.session.delete(link)
    try:
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
