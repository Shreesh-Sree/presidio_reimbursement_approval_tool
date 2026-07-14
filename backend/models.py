from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, JSON, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="employee")  # employee, approver, admin
    
    # Hierarchical structure: manager is another user
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    manager = relationship("User", remote_side=[id], backref="direct_reports")
    expense_reports = relationship("ExpenseReport", back_populates="employee")

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, unique=True, index=True, nullable=False)  # Travel, Food, Software, etc.
    limit_amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    rules = Column(JSON, nullable=True)  # additional JSON rules, e.g., {"receipt_required_above": 25.0}

class ExpenseReport(Base):
    __tablename__ = "expense_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, submitted, pending_approval, approved, rejected, reimbursed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee = relationship("User", back_populates="expense_reports")
    
    items = relationship("ExpenseItem", back_populates="report", cascade="all, delete-orphan")
    workflows = relationship("ApprovalWorkflow", back_populates="report", cascade="all, delete-orphan")

class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)
    
    report_id = Column(Integer, ForeignKey("expense_reports.id"), nullable=False)
    report = relationship("ExpenseReport", back_populates="items")

class ApprovalWorkflow(Base):
    __tablename__ = "approval_workflows"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    level = Column(Integer, default=1)  # 1st level (immediate manager), 2nd level, etc.
    comments = Column(String, nullable=True)
    ai_review = Column(JSON, nullable=True)  # AI audit result (anomalies, flags, suggestion, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    report_id = Column(Integer, ForeignKey("expense_reports.id"), nullable=False)
    report = relationship("ExpenseReport", back_populates="workflows")
    
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approver = relationship("User")
