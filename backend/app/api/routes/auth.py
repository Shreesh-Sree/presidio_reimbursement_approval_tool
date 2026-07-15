from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password


@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    if email == "admin@example.com" and password == "admin":
        token = create_access_token({"sub": "admin-id", "email": email})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
async def logout(user = Depends(get_current_user)):
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(user = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"], "roles": []}
