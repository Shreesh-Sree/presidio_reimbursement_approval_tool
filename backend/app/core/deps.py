from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token


async def get_current_user(token: str, db: Session = Depends(get_db)):
    """Get current user from JWT token."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"user_id": payload.get("sub"), "email": payload.get("email")}


def require_permission(code: str):
    """Dependency to check user has permission."""
    async def check_permission(user = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=403, detail=f"Missing permission: {code}")
        return user
    return check_permission
