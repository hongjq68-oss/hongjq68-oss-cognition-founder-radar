from sqlalchemy.orm import Session

from .models import AuditLog, User


def log(db: Session, user: User | None, action: str, entity: str, entity_id: int | None = None, **detail):
    db.add(AuditLog(user_id=user.id if user else None, user_name=user.name if user else "system",
                    action=action, entity=entity, entity_id=entity_id, detail=detail))
