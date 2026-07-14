import os
from sqlalchemy.orm import Session
import models

def analyze_expense_report(db: Session, report: models.ExpenseReport) -> dict:
    # 1. Fetch policies
    policies = {p.category.lower(): p for p in db.query(models.Policy).all()}
    
    # 2. Setup flags list & initial states
    flags = []
    anomalies = []
    total_amount = 0.0
    category_totals = {}
    
    # 3. Rule-based checking
    for item in report.items:
        total_amount += item.amount
        cat_lower = item.category.lower()
        category_totals[item.category] = category_totals.get(item.category, 0.0) + item.amount
        
        # Policy limit validation
        policy = policies.get(cat_lower)
        if policy:
            if item.amount > policy.limit_amount:
                flags.append({
                    "item_id": item.id,
                    "category": item.category,
                    "amount": item.amount,
                    "type": "POLICY_VIOLATION",
                    "severity": "HIGH",
                    "message": f"Expense amount {item.amount} exceeds policy limit of {policy.limit_amount} for category '{item.category}'."
                })
            
            # Receipt checking based on policy json rules
            rules = policy.rules or {}
            receipt_required_above = rules.get("receipt_required_above", 0.0)
            if item.amount > receipt_required_above and not item.receipt_url:
                flags.append({
                    "item_id": item.id,
                    "category": item.category,
                    "amount": item.amount,
                    "type": "MISSING_RECEIPT",
                    "severity": "MEDIUM",
                    "message": f"Receipt required for {item.category} expenses exceeding {receipt_required_above}."
                })
        else:
            # Category not in policy
            flags.append({
                "item_id": item.id,
                "category": item.category,
                "amount": item.amount,
                "type": "UNKNOWN_CATEGORY",
                "severity": "LOW",
                "message": f"Expense category '{item.category}' is not explicitly defined in company policy."
            })
            
        # Duplicate detection (same category, same amount, same date, or similar description)
        duplicate_query = db.query(models.ExpenseItem).join(models.ExpenseReport).filter(
            models.ExpenseItem.id != item.id,
            models.ExpenseItem.category == item.category,
            models.ExpenseItem.amount == item.amount,
            models.ExpenseItem.date == item.date,
            models.ExpenseReport.employee_id == report.employee_id
        ).first()
        if duplicate_query:
            anomalies.append({
                "item_id": item.id,
                "type": "POTENTIAL_DUPLICATE",
                "severity": "HIGH",
                "message": f"Potential duplicate claim. Similar expense of {item.amount} for category '{item.category}' exists on date {item.date}."
            })
            
    # Unusual spending patterns (e.g. employee's average in this category is much lower)
    for cat, total in category_totals.items():
        prev_items = db.query(models.ExpenseItem).join(models.ExpenseReport).filter(
            models.ExpenseReport.employee_id == report.employee_id,
            models.ExpenseReport.status == "approved",
            models.ExpenseItem.category == cat
        ).all()
        if prev_items:
            avg_prev = sum(pi.amount for pi in prev_items) / len(prev_items)
            if total > avg_prev * 2.5:  # more than 2.5 times the average
                anomalies.append({
                    "category": cat,
                    "type": "UNUSUAL_SPENDING",
                    "severity": "MEDIUM",
                    "message": f"Spending on '{cat}' ({total}) is significantly higher than employee's historical average of {avg_prev:.2f}."
                })

    # Combine results
    all_issues = flags + anomalies
    
    # 4. Generate summary and recommendation (Using LLM if GEMINI_API_KEY is available)
    api_key = os.environ.get("GEMINI_API_KEY")
    summary = ""
    recommendation = ""
    
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Analyze the following expense report submitted for reimbursement approval.
            
            Report Title: {report.title}
            Employee: {report.employee.name} (Role: {report.employee.role})
            Total Amount: {total_amount}
            
            Items:
            {[{'category': i.category, 'amount': i.amount, 'date': str(i.date), 'description': i.description, 'has_receipt': bool(i.receipt_url)} for i in report.items]}
            
            Rules / Flags found:
            {[issue['message'] for issue in all_issues]}
            
            Please provide a structured response containing:
            1. An analysis summary of the claim.
            2. Anomalies, duplications, or policy violations found.
            3. Final recommendation (Approve, Reject, or Request Info) with brief rationale.
            
            Keep the response professional, concise, and structured.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            summary = response.text
            recommendation = "Review Required" if all_issues else "Approve"
        except Exception as e:
            # Fallback
            summary = f"Rule-based check identified {len(all_issues)} flags/anomalies."
            recommendation = "Review Required" if all_issues else "Approve"
    else:
        # Structured fallback generation
        if not all_issues:
            summary = f"All items in the report '{report.title}' conform to the company policies. Total claim amount is {total_amount} across {len(report.items)} items."
            recommendation = "Approve"
        else:
            summary = f"The report '{report.title}' with total amount {total_amount} has triggered {len(all_issues)} alerts.\n\n"
            summary += "Issues found include:\n" + "\n".join([f"- {issue['message']}" for issue in all_issues])
            recommendation = "Review Required"
            
    return {
        "flags": flags,
        "anomalies": anomalies,
        "summary": summary,
        "recommendation": recommendation,
        "risk_level": "HIGH" if any(x["severity"] == "HIGH" for x in all_issues) else ("MEDIUM" if any(x["severity"] == "MEDIUM" for x in all_issues) else "LOW")
    }
