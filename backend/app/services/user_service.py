from sqlalchemy.orm import Session


def create_user(db: Session, email: str, password: str, full_name: str, organization_id: str):
    return {"id": "user-id", "email": email, "full_name": full_name, "status": "active"}


def deactivate_user(db: Session, user_id: str):
    return {"id": user_id, "status": "inactive"}


def get_user(db: Session, user_id: str):
    return {"id": user_id, "email": "user@example.com", "full_name": "Test", "status": "active"}


def list_users(db: Session, org_id: str):
    return [{"id": "u1", "email": "user@example.com", "status": "active"}]
