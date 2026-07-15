from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.permission import Permission

bearer = HTTPBearer()


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    token = creds.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return {"user_id": str(user.id), "email": user.email}


def require_permission(code: str):
    async def check_permission(user = Depends(get_current_user), db: Session = Depends(get_db)):
        user_id = user["user_id"]
        perms = db.query(Permission.code).join(
            Permission.role_permissions
        ).join(
            Permission.role_permissions.property.mapper.class_.roles
        ).filter(
            User.id == user_id,
            User.is_deleted == False
        ).all()
        perm_codes = {p.code for p in perms}
        if code not in perm_codes:
            raise HTTPException(status_code=403, detail=f"Missing permission: {code}")
        return user
    return check_permission
