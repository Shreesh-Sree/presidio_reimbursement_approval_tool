from sqlalchemy.orm import Session
from app.models.notification import Notification


def notify(db, recipient_id, template_code, payload, channels):
    notif = Notification(recipient_user_id=recipient_id, template_code=template_code, payload_json=payload, status="pending")
    db.add(notif)
    db.commit()
    return notif
