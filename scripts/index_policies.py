"""Index policy documents into the RAG assistant.

Run inside the backend pod:
    python /app/../scripts/index_policies.py

Or locally with proper env vars set.
"""
import sys
import os

sys.path.insert(0, os.environ.get("APP_PATH", "/app"))

from app.services import policy_assistant_client

ORG_ID = os.environ.get("ORG_ID", "a7344e57-becb-4b4f-95c6-992b78fd838e")
POLICY_ID = os.environ.get("POLICY_ID", "2632448b-18f7-4f75-bd0d-a370ebd7a1a7")

DOCUMENTS = [
    ("Travel & Expense Policy", """
PRESIDIO TRAVEL AND EXPENSE REIMBURSEMENT POLICY - Version 2.0
Effective: January 1, 2026 | Approved by: CFO Office

1. PURPOSE AND SCOPE
This policy governs all business-related travel and expense reimbursements for Presidio employees. It applies to domestic and international travel, client entertainment, daily commute claims, and office supply purchases. All employees must comply with these guidelines when incurring business expenses on behalf of the organization. Exceptions require written pre-approval from the department head and CFO.

2. ELIGIBLE EXPENSE CATEGORIES AND LIMITS
- Meals and Dining: Maximum INR 2,000 per day, INR 8,000 per trip. Receipt required above INR 500. Team meals capped at INR 5,000 per day (max 10 persons).
- Air Travel Domestic: Maximum INR 25,000 per trip. Receipt always required. Economy class is mandatory for all domestic flights.
- Air Travel International: Maximum INR 1,50,000 per trip. Receipt always required. Economy for flights under 6 hours, premium economy for flights exceeding 6 hours with manager pre-approval.
- Train Travel: Maximum INR 5,000 per trip. Receipt always required. AC Chair Car is the standard class.
- Taxi and Cab Services: Maximum INR 3,000 per day, INR 12,000 per trip. Receipt required above INR 200. Shared rides are encouraged.
- Hotel and Accommodation: Maximum INR 10,000 per day, INR 50,000 per trip. Receipt always required. 3-star properties are the default. 4-star permitted for client-facing meetings with manager approval. 5-star requires CFO approval.
- Office Supplies: Maximum INR 5,000 per category cap. Receipt required above INR 500. Purchase orders required above INR 5,000.
- Daily Commute: Maximum INR 1,500 per day. Receipt required above INR 1,000. Metro and bus passes preferred.
- Conference and Events: Maximum INR 50,000 per trip. Receipt always required. Includes registration fees and associated travel.
- Client Entertainment: Maximum INR 5,000 per day, INR 15,000 per trip. Receipt always required. Pre-approval needed for groups exceeding 4.

3. APPROVAL WORKFLOW
Level 1 - Manager Approval: All expense reports require immediate manager approval regardless of amount. The manager verifies business purpose, policy compliance, and receipt validity.
Level 2 - Finance Review: Reports exceeding INR 10,000 total or containing flagged line items require additional finance team review before payment processing.
SLA: Managers must act on submitted reports within 72 hours. Auto-escalation triggers after 5 business days of inaction.
Delegation: Managers can delegate approval authority to a nominated peer for planned absences via the Delegations module.

4. RECEIPT REQUIREMENTS
Original receipts must be attached for all expenses above the category threshold. Acceptable file formats: PDF, JPEG, PNG, WebP. Maximum file size: 10 MB per receipt.
Each receipt must clearly show: merchant name, date of purchase, itemized list of goods/services, total amount charged, and payment method used.
Credit card statements alone are NOT acceptable as receipts.
Digital receipts: Email confirmations, e-tickets, and digital invoices are accepted. Screenshots of UPI/GPay/PhonePe accepted only when full transaction detail is visible.
Missing Receipt Affidavit: If receipt is lost, complete the affidavit form with department head signature. Limited to 3 per quarter per employee. Exceeding this requires HR approval.

5. INTERNATIONAL TRAVEL
Requires pre-approval via Travel Request Form submitted at least 14 business days before departure.
Per-diem rates follow the Government of India DA rates for the destination country.
Currency conversion uses the exchange rate on the date of the expense as shown on the receipt.
Foreign currency expenses must be reported in INR using the receipt-date rate.
Cash advances in foreign currency must be reconciled within 7 days of return.

6. PROHIBITED EXPENSES
The following are never reimbursable:
- Personal entertainment, gifts, or shopping
- Alcohol purchases (except pre-approved client entertainment)
- Fines, penalties, or traffic violations
- First-class or business-class air travel without CFO approval
- Loyalty program upgrades charged to the company
- Expenses for non-employees (except approved client meals)
- Personal vehicle maintenance or insurance
- Gym memberships, spa services, or personal grooming
- Political donations or charitable contributions

7. REIMBURSEMENT TIMELINE
Approved expenses are processed within 5 business days via NEFT transfer to the employee's registered bank account.
Employees must submit expense reports within 30 days of incurring the expense.
Reports older than 60 days will not be processed without CFO exception approval.
Payment confirmation is sent via in-app notification and email.

8. POLICY VIOLATIONS
Repeated policy violations may result in:
1. Delayed reimbursement processing
2. Mandatory expense policy training
3. Suspension of corporate card privileges
4. Formal disciplinary action per HR policy
Fraudulent claims are grounds for immediate termination and legal action.
"""),
    ("Expense Category Limits", """
PRESIDIO EXPENSE CATEGORY LIMITS AND CAPS
Finance Department | Updated: June 2026 | Review: Quarterly

MONTHLY AND ANNUAL SPENDING LIMITS (per employee, in INR)
- Meals Solo: Daily cap 2,000 | Monthly cap 25,000 | Annual cap 2,50,000
- Meals Team: Daily cap 5,000 | Monthly cap 40,000 | Annual cap 4,00,000 (max 10 persons per claim)
- Air Travel: Daily cap 25,000 | Monthly cap 75,000 | Annual cap 6,00,000
- Hotels Metro Cities (Delhi/Mumbai/Bangalore/Chennai): Daily cap 10,000 | Monthly cap 60,000 | Annual cap 5,00,000
- Hotels Non-Metro: Daily cap 6,000 | Monthly cap 36,000 | Annual cap 3,00,000
- Taxi/Cab: Daily cap 3,000 | Monthly cap 20,000 | Annual cap 2,00,000
- Office Supplies: Daily cap 5,000 | Monthly cap 15,000 | Annual cap 1,50,000
- Conference: Per event cap 50,000 | Monthly cap 50,000 | Annual cap 2,00,000
- Communication (Mobile/Internet): Monthly cap 3,000 | Annual cap 36,000

TRANSPORT HIERARCHY
Employees must use the most cost-effective transport option:
- Under 5 km: Metro, Bus, or Auto-rickshaw. Late night (after 9 PM) allows cab.
- 5 to 20 km: Shared cab or Metro. Client meeting allows direct cab.
- 20 to 300 km: Train AC Chair Car. Time-critical allows flight with approval.
- Over 300 km: Flight Economy class. Flights over 6 hours allow premium economy.

ACCOMMODATION GUIDELINES
- Book 3-star or equivalent hotels by default
- 4-star permitted for client-facing meetings with prior manager approval
- 5-star requires CFO approval before booking
- Airbnb and serviced apartments permitted for stays exceeding 3 nights when cost-effective
- Room service and minibar charges above INR 500/night require justification

CURRENCY CONVERSION
All claims must be submitted in INR. For foreign currency expenses:
- Use exchange rate displayed on credit card statement or receipt date
- Attach card statement page showing conversion rate
- Cash advances in foreign currency reconciled within 7 days of return
"""),
    ("Receipt and Documentation Requirements", """
PRESIDIO RECEIPT AND DOCUMENTATION REQUIREMENTS
Compliance Team | Version 1.3 | Effective: March 2026

WHEN RECEIPTS ARE REQUIRED
A valid receipt must accompany every expense claim above the category threshold:
- Meals and Dining: Receipt required above INR 500
- Air Travel: Receipt ALWAYS required (any amount)
- Train Travel: Receipt ALWAYS required (any amount)
- Taxi/Cab: Receipt required above INR 200
- Hotel/Accommodation: Receipt ALWAYS required (any amount)
- Office Supplies: Receipt required above INR 500
- Daily Commute: Receipt required above INR 1,000
- Conference/Events: Receipt ALWAYS required (any amount)
- Client Entertainment: Receipt ALWAYS required (any amount)

VALID RECEIPT CRITERIA
Every receipt must contain ALL of the following:
1. Merchant/vendor name and address
2. Date of transaction (must match claimed expense date)
3. Itemized list of goods or services purchased
4. Total amount charged (including taxes and fees)
5. Payment method indicator (card last 4 digits, UPI ID, or cash notation)
6. GST/tax registration number (for amounts exceeding INR 2,000)

ACCEPTABLE FILE FORMATS
- Supported: PDF, JPEG, PNG, WebP
- Maximum size: 10 MB per file
- Minimum resolution: 300 DPI for photographed receipts
- All text must be clearly readable; blurry or truncated receipts will be rejected

DIGITAL RECEIPTS
Email confirmations, e-tickets, and digital invoices are accepted if they contain all required information.
Screenshots of payment apps (GPay, PhonePe, Paytm) accepted only when full transaction detail is visible including merchant name and amount.
Cropped or partial screenshots will be rejected.

MISSING RECEIPT AFFIDAVIT PROCESS
If an original receipt cannot be obtained (lost, not issued, etc.):
1. Complete the Missing Receipt Affidavit form from the templates section
2. Provide alternative evidence (bank statement, booking confirmation, email receipt)
3. Obtain department head signature on the affidavit
4. Attach the signed affidavit in place of the receipt
Limit: 3 missing receipt affidavits per quarter per employee. Exceeding this requires HR approval.

RECEIPT VERIFICATION
The Receipt Intelligence Service performs automated checks:
- Duplicate detection via SHA-256 hash comparison
- File format and magic-byte validation
- OCR text extraction for cross-verification of amounts
- Suspicious pattern detection (embedded instructions, altered dates)
Flagged receipts are automatically routed for manual review by the finance team.
"""),
]


def main():
    for name, content in DOCUMENTS:
        print(f"Indexing: {name}...")
        try:
            result = policy_assistant_client.index_policy_text(
                organization_id=ORG_ID,
                policy_id=POLICY_ID,
                content=content.strip(),
            )
            print(f"  Done: {result}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\nAll documents indexed.")


if __name__ == "__main__":
    main()
