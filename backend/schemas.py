from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date

# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str  # employee, approver, admin
    manager_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Policy Schemas
class PolicyBase(BaseModel):
    category: str
    limit_amount: float
    currency: Optional[str] = "USD"
    rules: Optional[dict] = None

class PolicyCreate(PolicyBase):
    pass

class PolicyResponse(PolicyBase):
    id: int

    class Config:
        from_attributes = True

# Expense Item Schemas
class ExpenseItemBase(BaseModel):
    category: str
    amount: float
    date: date
    description: Optional[str] = None
    receipt_url: Optional[str] = None

class ExpenseItemCreate(ExpenseItemBase):
    pass

class ExpenseItemResponse(ExpenseItemBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True

# Expense Report Schemas
class ExpenseReportBase(BaseModel):
    title: str
    description: Optional[str] = None

class ExpenseReportCreate(ExpenseReportBase):
    items: List[ExpenseItemCreate]

class ApprovalWorkflowResponse(BaseModel):
    id: int
    status: str
    level: int
    comments: Optional[str] = None
    ai_review: Optional[dict] = None
    approver: UserResponse
    created_at: datetime

    class Config:
        from_attributes = True

class ExpenseReportResponse(ExpenseReportBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    employee_id: int
    employee: UserResponse
    items: List[ExpenseItemResponse]
    workflows: List[ApprovalWorkflowResponse]

    class Config:
        from_attributes = True

# Approval Schemas
class ApprovalAction(BaseModel):
    status: str  # approved, rejected
    comments: Optional[str] = None
