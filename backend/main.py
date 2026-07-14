import os
from datetime import date, datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
import auth
import agent
from database import engine, Base, get_db

# Create Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Presidio Reimbursement Approval Tool API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed Database
@app.on_event("startup")
def seed_db():
    db = next(get_db())
    try:
        # Check if users already seeded
        if db.query(models.User).count() == 0:
            print("Seeding initial database...")
            
            # Hash password
            hp = auth.get_password_hash("password123")
            
            # Create users
            admin = models.User(name="Admin Alice", email="admin@presidio.com", hashed_password=hp, role="admin")
            ceo = models.User(name="CEO Charlie", email="ceo@presidio.com", hashed_password=hp, role="approver")
            db.add_all([admin, ceo])
            db.commit()
            
            # Refresh to get IDs
            db.refresh(ceo)
            
            mgr1 = models.User(name="Manager Bob", email="manager1@presidio.com", hashed_password=hp, role="approver", manager_id=ceo.id)
            db.add(mgr1)
            db.commit()
            db.refresh(mgr1)
            
            emp1 = models.User(name="Employee Emma", email="employee1@presidio.com", hashed_password=hp, role="employee", manager_id=mgr1.id)
            emp2 = models.User(name="Employee Ethan", email="employee2@presidio.com", hashed_password=hp, role="employee", manager_id=mgr1.id)
            
            db.add_all([emp1, emp2])
            db.commit()
            
            # Seed Policies
            policies = [
                models.Policy(category="Travel", limit_amount=500.0, rules={"receipt_required_above": 50.0}),
                models.Policy(category="Food", limit_amount=50.0, rules={"receipt_required_above": 15.0}),
                models.Policy(category="Software", limit_amount=200.0, rules={"receipt_required_above": 0.0}),
                models.Policy(category="Office Supplies", limit_amount=100.0, rules={"receipt_required_above": 20.0}),
            ]
            db.add_all(policies)
            db.commit()
            print("Seeding complete.")
    finally:
        db.close()

# Dependency to get current user from token
def get_current_user(token: str = Depends(auth.decode_access_token), db: Session = Depends(get_db)) -> models.User:
    if not token or "user_id" not in token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.id == token["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Health check
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "backend"}

# Auth Endpoints
@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user_in.password)
    user = models.User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed_password,
        role=user_in.role,
        manager_id=user_in.manager_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(login_in: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_in.email).first()
    if not user or not auth.verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/api/auth/users", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# Policy Endpoints
@app.post("/api/policies", response_model=schemas.PolicyResponse)
def create_policy(policy_in: schemas.PolicyCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage policies")
    
    # Overwrite if exists, otherwise create
    db_policy = db.query(models.Policy).filter(models.Policy.category == policy_in.category).first()
    if db_policy:
        db_policy.limit_amount = policy_in.limit_amount
        db_policy.currency = policy_in.currency
        db_policy.rules = policy_in.rules
    else:
        db_policy = models.Policy(**policy_in.dict())
        db.add(db_policy)
    
    db.commit()
    db.refresh(db_policy)
    return db_policy

@app.get("/api/policies", response_model=List[schemas.PolicyResponse])
def get_policies(db: Session = Depends(get_db)):
    return db.query(models.Policy).all()

@app.post("/api/policies/upload-doc")
def upload_policy_doc(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can upload policy documents")
    
    # Mock text extraction and parsing of rules from uploaded policy document.
    # In a full RAG implementation, this might index paragraphs in a vector DB.
    # Here, we parse a simple textual list of categories and limits, or seed default ones, and return the log.
    content = file.file.read().decode("utf-8", errors="ignore")
    parsed_count = 0
    logs = []
    
    # Simple parser line-by-line: "Category: Limit" or similar
    for line in content.split("\n"):
        if ":" in line:
            parts = line.split(":")
            cat = parts[0].strip()
            val_str = parts[1].strip()
            try:
                # Remove currency symbols if present
                val_str_clean = val_str.replace("$", "").replace("€", "").replace("₹", "").strip()
                val = float(val_str_clean)
                
                # Check/update category
                db_policy = db.query(models.Policy).filter(models.Policy.category.ilike(cat)).first()
                if db_policy:
                    db_policy.limit_amount = val
                    logs.append(f"Updated policy {db_policy.category} to {val}")
                else:
                    db_policy = models.Policy(category=cat, limit_amount=val, rules={"receipt_required_above": val * 0.1})
                    db.add(db_policy)
                    logs.append(f"Created policy {cat} with limit {val}")
                parsed_count += 1
            except ValueError:
                continue
                
    db.commit()
    return {
        "filename": file.filename,
        "message": f"Successfully processed policy document. Parsed {parsed_count} rules.",
        "logs": logs
    }

# Expense Report Endpoints
@app.post("/api/expenses", response_model=schemas.ExpenseReportResponse)
def create_expense_report(
    report_in: schemas.ExpenseReportCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Create the base expense report
    report = models.ExpenseReport(
        title=report_in.title,
        description=report_in.description,
        employee_id=current_user.id,
        status="submitted"  # immediately submit upon creation
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # 2. Add line items
    for item_in in report_in.items:
        item = models.ExpenseItem(
            category=item_in.category,
            amount=item_in.amount,
            date=item_in.date,
            description=item_in.description,
            receipt_url=item_in.receipt_url,
            report_id=report.id
        )
        db.add(item)
    db.commit()
    db.refresh(report)
    
    # 3. Create the multi-level workflow entry
    # First level is the employee's direct manager
    if not current_user.manager_id:
        # If no manager, CEO or admin approves, or automatically assign CEO
        ceo = db.query(models.User).filter(models.User.email == "ceo@presidio.com").first()
        approver_id = ceo.id if ceo else current_user.id
    else:
        approver_id = current_user.manager_id
        
    workflow = models.ApprovalWorkflow(
        report_id=report.id,
        approver_id=approver_id,
        level=1,
        status="pending"
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # 4. Trigger the AI agent audit and store it in the workflow
    ai_audit = agent.analyze_expense_report(db, report)
    workflow.ai_review = ai_audit
    db.commit()
    
    # Refresh and return
    db.refresh(report)
    return report

@app.get("/api/expenses", response_model=List[schemas.ExpenseReportResponse])
def list_expense_reports(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        return db.query(models.ExpenseReport).all()
    elif current_user.role == "approver":
        # Return reports where the user is the current active approver in a pending workflow
        # OR reports they submitted themselves
        subquery = db.query(models.ApprovalWorkflow.report_id).filter(
            models.ApprovalWorkflow.approver_id == current_user.id,
            models.ApprovalWorkflow.status == "pending"
        ).subquery()
        
        return db.query(models.ExpenseReport).filter(
            (models.ExpenseReport.id.in_(subquery)) | (models.ExpenseReport.employee_id == current_user.id)
        ).all()
    else:
        # Regular employee: only their own reports
        return db.query(models.ExpenseReport).filter(models.ExpenseReport.employee_id == current_user.id).all()

@app.get("/api/expenses/{report_id}", response_model=schemas.ExpenseReportResponse)
def get_expense_report(report_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(models.ExpenseReport).filter(models.ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")
        
    # Check permissions
    is_approver = db.query(models.ApprovalWorkflow).filter(
        models.ApprovalWorkflow.report_id == report_id,
        models.ApprovalWorkflow.approver_id == current_user.id
    ).count() > 0
    
    if current_user.role != "admin" and report.employee_id != current_user.id and not is_approver:
        raise HTTPException(status_code=403, detail="Not authorized to view this report")
        
    return report

@app.post("/api/expenses/{report_id}/action", response_model=schemas.ExpenseReportResponse)
def expense_action(
    report_id: int,
    action: schemas.ApprovalAction,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(models.ExpenseReport).filter(models.ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")
        
    # Find pending workflow step for this user
    workflow = db.query(models.ApprovalWorkflow).filter(
        models.ApprovalWorkflow.report_id == report_id,
        models.ApprovalWorkflow.approver_id == current_user.id,
        models.ApprovalWorkflow.status == "pending"
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=400, detail="No pending approval workflow found for you on this report")
        
    # Update workflow step
    workflow.status = action.status
    workflow.comments = action.comments
    db.commit()
    
    if action.status == "rejected":
        report.status = "rejected"
        db.commit()
    elif action.status == "approved":
        # Multi-level check: Does the approver have a manager (second level)?
        # If yes, advance to level 2. If no, report is fully approved.
        current_approver = db.query(models.User).filter(models.User.id == current_user.id).first()
        
        if current_approver.manager_id:
            # Create Level 2 workflow
            next_workflow = models.ApprovalWorkflow(
                report_id=report.id,
                approver_id=current_approver.manager_id,
                level=workflow.level + 1,
                status="pending"
            )
            db.add(next_workflow)
            db.commit()
            
            # Re-run AI analysis for next workflow
            ai_audit = agent.analyze_expense_report(db, report)
            next_workflow.ai_review = ai_audit
            db.commit()
            
            report.status = "pending_approval"  # Remains pending
            db.commit()
        else:
            # No higher manager, fully approved!
            report.status = "approved"
            db.commit()
            
    db.refresh(report)
    return report

# Mock Upload Receipt
@app.post("/api/expenses/upload-receipt")
def upload_receipt(file: UploadFile = File(...)):
    # In production, save to S3 or a local media dir. Here we return a mock URL.
    # We can create a local folder for uploads to make it real
    upload_dir = "/home/shreesh/Documents/presidio_reimbursement_approval_tool/backend/static/receipts"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
        
    return {
        "filename": file.filename,
        "receipt_url": f"http://127.0.0.1:8000/static/receipts/{file.filename}"
    }

# Serve static files for uploads
from fastapi.staticfiles import StaticFiles
static_dir = "/home/shreesh/Documents/presidio_reimbursement_approval_tool/backend/static"
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
