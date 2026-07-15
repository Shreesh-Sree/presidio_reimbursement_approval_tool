from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email, User.is_deleted == False).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(user = Depends(get_current_user)):
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(user = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"], "roles": []}
