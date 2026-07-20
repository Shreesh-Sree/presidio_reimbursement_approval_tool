"""Generate demo policy PDFs and receipt files for seed data.

Usage:
    pip install reportlab Pillow
    python scripts/generate_demo_assets.py

Outputs to scripts/demo_assets/
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None  # type: ignore[assignment,misc]

ASSETS_DIR = Path(__file__).parent / "demo_assets"
STYLES = getSampleStyleSheet()

HEADING = ParagraphStyle("CustomHeading", parent=STYLES["Heading1"], fontSize=18, spaceAfter=14)
SUBHEADING = ParagraphStyle("CustomSub", parent=STYLES["Heading2"], fontSize=14, spaceAfter=10)
BODY = ParagraphStyle("CustomBody", parent=STYLES["BodyText"], fontSize=11, leading=15, spaceAfter=8)
SMALL = ParagraphStyle("Small", parent=STYLES["BodyText"], fontSize=9, leading=12, textColor=colors.grey)


def _doc(name: str) -> SimpleDocTemplate:
    path = ASSETS_DIR / name
    return SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)


def generate_travel_policy_pdf() -> Path:
    doc = _doc("travel_policy.pdf")
    story: list = []

    story.append(Paragraph("Presidio Travel & Expense Reimbursement Policy", HEADING))
    story.append(Paragraph("Version 2.0 | Effective: January 1, 2026 | Approved by: CFO Office", SMALL))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Purpose and Scope", SUBHEADING))
    story.append(Paragraph(
        "This policy governs all business-related travel and expense reimbursements for Presidio employees. "
        "It applies to domestic and international travel, client entertainment, daily commute claims, "
        "and office supply purchases. All employees must comply with these guidelines when incurring "
        "business expenses on behalf of the organization.", BODY))
    story.append(Paragraph(
        "The policy ensures fiscal responsibility while enabling employees to conduct business effectively. "
        "Exceptions require written pre-approval from the department head and CFO.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Eligible Expense Categories", SUBHEADING))
    categories_data = [
        ["Category", "Max Per Day (INR)", "Max Per Trip (INR)", "Receipt Required Above"],
        ["Meals & Dining", "2,000", "8,000", "500"],
        ["Air Travel (Domestic)", "25,000", "25,000", "All"],
        ["Air Travel (International)", "1,50,000", "1,50,000", "All"],
        ["Train Travel", "5,000", "5,000", "All"],
        ["Taxi / Cab", "3,000", "12,000", "200"],
        ["Hotel / Accommodation", "10,000", "50,000", "All"],
        ["Office Supplies", "5,000", "5,000", "500"],
        ["Daily Commute", "1,500", "N/A", "1,000"],
        ["Conference & Events", "50,000", "50,000", "All"],
        ["Client Entertainment", "5,000", "15,000", "All"],
    ]
    t = Table(categories_data, colWidths=[4.5 * cm, 3.5 * cm, 3.5 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#001E2B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C1CDC8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFA")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("3. Approval Workflow", SUBHEADING))
    story.append(Paragraph(
        "<b>Level 1 - Manager Approval:</b> All expense reports require immediate manager approval "
        "regardless of amount. The manager verifies business purpose, policy compliance, and receipt validity.", BODY))
    story.append(Paragraph(
        "<b>Level 2 - Finance Review:</b> Reports exceeding INR 10,000 total or containing flagged "
        "line items require additional finance team review before payment processing.", BODY))
    story.append(Paragraph(
        "<b>SLA:</b> Managers must act within 72 hours. Auto-escalation triggers after 5 business days.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. Receipt Requirements", SUBHEADING))
    story.append(Paragraph(
        "Original receipts must be attached for all expenses above the category threshold. "
        "Acceptable formats: PDF, JPEG, PNG, WebP. Maximum file size: 10 MB per receipt.", BODY))
    story.append(Paragraph(
        "Each receipt must clearly show: merchant name, date of purchase, itemized list of goods/services, "
        "total amount charged, and payment method used. Credit card statements are NOT acceptable as receipts.", BODY))
    story.append(Paragraph(
        "For expenses where an original receipt is lost, a Missing Receipt Affidavit must be completed "
        "and approved by the department head before submission.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. International Travel", SUBHEADING))
    story.append(Paragraph(
        "International travel requires pre-approval via the Travel Request Form submitted at least "
        "14 business days before departure. Economy class is the default for flights under 6 hours; "
        "premium economy may be used for flights exceeding 6 hours with manager pre-approval.", BODY))
    story.append(Paragraph(
        "Per-diem rates follow the Government of India DA rates for the destination country. "
        "Currency conversion uses the exchange rate on the date of the expense (as shown on the receipt). "
        "Foreign currency expenses must be reported in INR using the receipt date rate.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("6. Prohibited Expenses", SUBHEADING))
    prohibited = [
        "Personal entertainment, gifts, or shopping",
        "Alcohol purchases (except pre-approved client entertainment)",
        "Fines, penalties, or traffic violations",
        "First-class or business-class air travel without CFO approval",
        "Loyalty program upgrades charged to the company",
        "Expenses for non-employees (except approved client meals)",
        "Personal vehicle maintenance or insurance",
    ]
    for item in prohibited:
        story.append(Paragraph(f"• {item}", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("7. Reimbursement Timeline", SUBHEADING))
    story.append(Paragraph(
        "Approved expenses are processed within 5 business days via NEFT transfer to the employee's "
        "registered bank account. Employees must submit expense reports within 30 days of incurring "
        "the expense. Reports older than 60 days will not be processed without CFO exception approval.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("8. Policy Violations", SUBHEADING))
    story.append(Paragraph(
        "Repeated policy violations may result in: (1) Delayed reimbursement, (2) Mandatory training, "
        "(3) Suspension of corporate card privileges, (4) Disciplinary action per HR policy. "
        "Fraudulent claims are grounds for immediate termination and legal action.", BODY))

    doc.build(story)
    return ASSETS_DIR / "travel_policy.pdf"


def generate_expense_limits_policy_pdf() -> Path:
    doc = _doc("expense_limits_policy.pdf")
    story: list = []

    story.append(Paragraph("Expense Category Limits & Caps - Presidio", HEADING))
    story.append(Paragraph("Finance Department | Updated: June 2026 | Review: Quarterly", SMALL))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Category-wise Spending Limits", SUBHEADING))
    story.append(Paragraph(
        "The following limits apply per employee per calendar month unless otherwise specified. "
        "Limits are in Indian Rupees (INR). Expenses in foreign currency are converted at the "
        "transaction-date exchange rate.", BODY))
    story.append(Spacer(1, 6))

    limits_data = [
        ["Category", "Daily Cap", "Monthly Cap", "Annual Cap", "Notes"],
        ["Meals (Solo)", "2,000", "25,000", "2,50,000", "Client meals tracked separately"],
        ["Meals (Team)", "5,000", "40,000", "4,00,000", "Max 10 persons per claim"],
        ["Air Travel", "25,000", "75,000", "6,00,000", "Economy class default"],
        ["Hotels (Metro)", "10,000", "60,000", "5,00,000", "Delhi/Mumbai/Bangalore/Chennai"],
        ["Hotels (Non-Metro)", "6,000", "36,000", "3,00,000", "All other cities"],
        ["Taxi/Cab", "3,000", "20,000", "2,00,000", "Shared rides encouraged"],
        ["Office Supplies", "5,000", "15,000", "1,50,000", "Pre-approved PO for >5K"],
        ["Conference", "50,000", "50,000", "2,00,000", "Registration + travel combined"],
        ["Communication", "1,000", "3,000", "36,000", "Mobile/internet only"],
    ]
    t = Table(limits_data, colWidths=[3.2 * cm, 2.2 * cm, 2.5 * cm, 2.5 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00684A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E8EDEB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3FCF7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("2. Accommodation Guidelines", SUBHEADING))
    story.append(Paragraph(
        "Employees should book hotels rated 3-star or equivalent. 4-star properties are permitted "
        "for client-facing meetings with prior manager approval. 5-star properties require CFO approval. "
        "Airbnb and serviced apartments are permitted when cost-effective for stays exceeding 3 nights.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Transport Hierarchy", SUBHEADING))
    story.append(Paragraph("Employees must use the most cost-effective transport option:", BODY))
    transport_data = [
        ["Distance", "Recommended Mode", "Exception"],
        ["< 5 km", "Metro/Bus/Auto", "Late night (after 9 PM) - cab allowed"],
        ["5-20 km", "Shared cab / Metro", "Client meeting - direct cab allowed"],
        ["20-300 km", "Train (AC Chair)", "Time-critical - flight allowed with approval"],
        ["> 300 km", "Flight (Economy)", "6+ hours flight - premium economy allowed"],
    ]
    t2 = Table(transport_data, colWidths=[3 * cm, 4.5 * cm, 7 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#001E2B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C1CDC8")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 12))

    story.append(Paragraph("4. Currency Conversion Policy", SUBHEADING))
    story.append(Paragraph(
        "All claims must be submitted in INR. For foreign currency expenses, use the exchange rate "
        "as displayed on the credit card statement or receipt date. Employees must attach the card "
        "statement page showing the conversion rate. Cash advances in foreign currency must be "
        "reconciled within 7 days of return.", BODY))

    doc.build(story)
    return ASSETS_DIR / "expense_limits_policy.pdf"


def generate_receipt_requirements_policy_pdf() -> Path:
    doc = _doc("receipt_requirements_policy.pdf")
    story: list = []

    story.append(Paragraph("Receipt & Documentation Requirements", HEADING))
    story.append(Paragraph("Compliance Team | Version 1.3 | Effective: March 2026", SMALL))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. When Receipts Are Required", SUBHEADING))
    story.append(Paragraph(
        "A valid receipt must accompany every expense claim above the category-specific threshold. "
        "For certain categories (Air Travel, Hotel, Conference), receipts are mandatory regardless "
        "of amount. The receipt must be uploaded at the time of line-item creation.", BODY))
    story.append(Spacer(1, 6))

    thresholds = [
        ["Category", "Receipt Threshold (INR)", "Mandatory?"],
        ["Meals & Dining", "500", "Above threshold"],
        ["Air Travel", "0", "Always"],
        ["Train Travel", "0", "Always"],
        ["Taxi / Cab", "200", "Above threshold"],
        ["Hotel", "0", "Always"],
        ["Office Supplies", "500", "Above threshold"],
        ["Daily Commute", "1,000", "Above threshold"],
        ["Conference", "0", "Always"],
        ["Client Entertainment", "0", "Always"],
    ]
    t = Table(thresholds, colWidths=[4.5 * cm, 4.5 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7856FF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E8EDEB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("2. Valid Receipt Criteria", SUBHEADING))
    story.append(Paragraph("Every receipt must contain ALL of the following:", BODY))
    criteria = [
        "Merchant/vendor name and address",
        "Date of transaction (matching the claimed expense date)",
        "Itemized list of goods or services purchased",
        "Total amount charged (including taxes and fees)",
        "Payment method indicator (card last 4 digits, UPI ID, or cash notation)",
        "GST/tax registration number (for amounts > INR 2,000)",
    ]
    for item in criteria:
        story.append(Paragraph(f"• {item}", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Acceptable File Formats", SUBHEADING))
    story.append(Paragraph(
        "<b>Supported:</b> PDF, JPEG, PNG, WebP<br/>"
        "<b>Maximum size:</b> 10 MB per file<br/>"
        "<b>Resolution:</b> Minimum 300 DPI for photographed receipts<br/>"
        "<b>Legibility:</b> All text must be clearly readable. Blurry or truncated receipts will be rejected.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. Digital Receipts", SUBHEADING))
    story.append(Paragraph(
        "Email confirmations, e-tickets, and digital invoices are accepted if they contain all "
        "required information. Screenshots of payment apps (GPay, PhonePe, Paytm) are accepted "
        "only when the full transaction detail is visible including merchant name and amount. "
        "Cropped screenshots will be rejected.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. Missing Receipt Affidavit", SUBHEADING))
    story.append(Paragraph(
        "If an original receipt cannot be obtained (lost, not issued, etc.), the employee must:", BODY))
    story.append(Paragraph("1. Complete the Missing Receipt Affidavit form", BODY))
    story.append(Paragraph("2. Provide alternative evidence (bank statement, booking confirmation)", BODY))
    story.append(Paragraph("3. Obtain department head signature", BODY))
    story.append(Paragraph("4. Attach the signed affidavit in place of the receipt", BODY))
    story.append(Paragraph(
        "Note: Missing receipt affidavits are limited to 3 per quarter per employee. "
        "Exceeding this limit requires HR approval.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("6. Receipt Verification Process", SUBHEADING))
    story.append(Paragraph(
        "The Receipt Intelligence Service performs automated checks on uploaded receipts: "
        "duplicate detection (SHA-256 hash), format validation, OCR text extraction, and "
        "amount cross-verification. Flagged receipts are routed for manual review.", BODY))

    doc.build(story)
    return ASSETS_DIR / "receipt_requirements_policy.pdf"


def _draw_receipt_png(
    merchant: str,
    address: str,
    items: list[tuple[str, float]],
    total: float,
    date_str: str,
    receipt_type: str,
    output_name: str,
    gst: str = "29AABCU9603R1ZM",
    payment_method: str = "UPI",
) -> Path:
    if Image is None:
        raise RuntimeError("Pillow is required: pip install Pillow")

    width, height = 400, 180 + len(items) * 28 + 120
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except (OSError, IOError):
        font_bold = ImageFont.load_default()
        font_normal = font_bold
        font_small = font_bold

    y = 20
    draw.text((width // 2 - len(merchant) * 4, y), merchant.upper(), fill="#001E2B", font=font_bold)
    y += 22
    draw.text((width // 2 - len(address) * 3, y), address, fill="#5C6C75", font=font_small)
    y += 18
    draw.text((width // 2 - 60, y), f"GSTIN: {gst}", fill="#5C6C75", font=font_small)
    y += 22

    draw.line([(20, y), (width - 20, y)], fill="#E8EDEB", width=1)
    y += 12

    draw.text((20, y), f"Date: {date_str}", fill="#001E2B", font=font_normal)
    draw.text((width - 140, y), f"Type: {receipt_type.title()}", fill="#5C6C75", font=font_normal)
    y += 24

    draw.line([(20, y), (width - 20, y)], fill="#E8EDEB", width=1)
    y += 10

    draw.text((20, y), "Item", fill="#5C6C75", font=font_small)
    draw.text((width - 100, y), "Amount (INR)", fill="#5C6C75", font=font_small)
    y += 18

    for item_name, amount in items:
        draw.text((20, y), item_name[:35], fill="#001E2B", font=font_normal)
        draw.text((width - 100, y), f"{amount:,.2f}", fill="#001E2B", font=font_normal)
        y += 28

    draw.line([(20, y), (width - 20, y)], fill="#001E2B", width=2)
    y += 12

    draw.text((20, y), "TOTAL", fill="#001E2B", font=font_bold)
    draw.text((width - 110, y), f"INR {total:,.2f}", fill="#001E2B", font=font_bold)
    y += 28

    draw.text((20, y), f"Payment: {payment_method}", fill="#5C6C75", font=font_normal)
    y += 20
    draw.text((20, y), f"Bill No: {random.randint(10000, 99999)}", fill="#5C6C75", font=font_small)
    y += 16
    draw.text((width // 2 - 50, y), "Thank you!", fill="#5C6C75", font=font_small)

    out_path = ASSETS_DIR / output_name
    img.save(str(out_path), "PNG")
    return out_path


def _draw_receipt_pdf(
    merchant: str,
    address: str,
    items: list[tuple[str, float]],
    total: float,
    date_str: str,
    receipt_type: str,
    output_name: str,
    booking_ref: str = "",
) -> Path:
    doc = _doc(output_name)
    story: list = []

    story.append(Paragraph(merchant.upper(), ParagraphStyle("RM", parent=STYLES["Heading2"], fontSize=16, alignment=1)))
    story.append(Paragraph(address, ParagraphStyle("RA", parent=STYLES["Normal"], fontSize=9, alignment=1, textColor=colors.grey)))
    story.append(Spacer(1, 6))

    if booking_ref:
        story.append(Paragraph(f"Booking Ref: {booking_ref}", ParagraphStyle("Ref", parent=STYLES["Normal"], fontSize=10, textColor=colors.HexColor("#016BF8"))))

    story.append(Paragraph(f"Date: {date_str} | Type: {receipt_type.title()}", SMALL))
    story.append(Spacer(1, 10))

    table_data = [["Description", "Amount (INR)"]]
    for item_name, amount in items:
        table_data.append([item_name, f"{amount:,.2f}"])
    table_data.append(["TOTAL", f"INR {total:,.2f}"])

    t = Table(table_data, colWidths=[10 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#001E2B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E8EDEB")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E3FCF7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Invoice No: INV-{random.randint(100000, 999999)}", SMALL))

    doc.build(story)
    return ASSETS_DIR / output_name


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating policy PDFs...")
    generate_travel_policy_pdf()
    generate_expense_limits_policy_pdf()
    generate_receipt_requirements_policy_pdf()
    print(f"  3 policy PDFs created in {ASSETS_DIR}")

    print("Generating receipt files...")

    base_date = date(2026, 6, 1)

    png_receipts = [
        ("Dominos Pizza", "Brigade Road, Bangalore", [("Margherita Large", 499), ("Garlic Bread", 199), ("Coke 500ml", 80)], 778.0, (base_date + timedelta(days=15)).isoformat(), "restaurant", "receipt_dominos_001.png", "UPI - GPay"),
        ("Uber India", "Koramangala to Airport", [("Ride Fare", 380), ("Surge (1.2x)", 76), ("Toll", 45)], 501.0, (base_date + timedelta(days=16)).isoformat(), "taxi", "receipt_uber_001.png", "Card ending 4521"),
        ("Ola Cabs", "Office to Client Site", [("Base Fare", 250), ("Distance (12km)", 144), ("GST", 35)], 429.0, (base_date + timedelta(days=10)).isoformat(), "taxi", "receipt_ola_001.png", "UPI - PhonePe"),
        ("Swiggy Dineout", "Team Lunch - Sprint Review", [("Biryani x4", 1200), ("Starters", 650), ("Drinks", 320), ("GST", 195)], 2365.0, (base_date + timedelta(days=20)).isoformat(), "restaurant", "receipt_swiggy_001.png", "Card ending 8834"),
        ("Chai Point", "Office Coffee", [("Filter Coffee x3", 360), ("Samosa x3", 120)], 480.0, (base_date + timedelta(days=5)).isoformat(), "restaurant", "receipt_chai_001.png", "UPI"),
        ("Metro Smart Card", "Monthly Recharge", [("Namma Metro - 30 Day Pass", 1500)], 1500.0, (base_date + timedelta(days=1)).isoformat(), "commute", "receipt_metro_001.png", "UPI - Paytm"),
        ("Amazon India", "Office Supplies", [("Logitech Mouse", 899), ("USB-C Hub", 1299), ("Notebook Set", 349)], 2547.0, (base_date + timedelta(days=8)).isoformat(), "office", "receipt_amazon_001.png", "Card ending 4521"),
        ("Flipkart", "Monitor Stand", [("Wooden Monitor Riser", 1899), ("Cable Organizer", 299)], 2198.0, (base_date + timedelta(days=12)).isoformat(), "office", "receipt_flipkart_001.png", "UPI - GPay"),
        ("Bangalore Restaurant", "Client Dinner - Acme Corp", [("Dinner for 4", 3200), ("Drinks", 1100), ("Dessert", 600), ("GST + Service", 735)], 5635.0, (base_date + timedelta(days=22)).isoformat(), "restaurant", "receipt_dinner_client_001.png", "Card ending 8834"),
        ("Rapido Bike", "Quick Commute", [("Bike Ride (5km)", 85)], 85.0, (base_date + timedelta(days=14)).isoformat(), "taxi", "receipt_rapido_001.png", "UPI"),
        ("BMTC Bus", "Daily Commute x5", [("Bus Pass - Weekly", 250)], 250.0, (base_date + timedelta(days=7)).isoformat(), "commute", "receipt_bus_001.png", "Cash"),
    ]

    for merchant, addr, items, total, dt, rtype, fname, payment in png_receipts:
        _draw_receipt_png(merchant, addr, items, total, dt, rtype, fname, payment_method=payment)

    pdf_receipts = [
        ("IndiGo Airlines", "Bangalore (BLR) to Delhi (DEL)", [("Economy Fare", 4200), ("Convenience Fee", 350), ("GST (5%)", 228)], 4778.0, (base_date + timedelta(days=14)).isoformat(), "airline", "receipt_indigo_blr_del.pdf", "6E-2847"),
        ("Air India", "Delhi (DEL) to Mumbai (BOM)", [("Economy Fare", 5100), ("Meal Add-on", 350), ("Seat Selection", 200), ("GST", 283)], 5933.0, (base_date + timedelta(days=18)).isoformat(), "airline", "receipt_airindia_del_bom.pdf", "AI-806"),
        ("Taj Hotel", "Bangalore - 2 Nights", [("Deluxe Room (2N)", 14000), ("Room Service", 1200), ("Laundry", 450), ("GST (12%)", 1878)], 17528.0, (base_date + timedelta(days=15)).isoformat(), "hotel", "receipt_taj_blr.pdf", "TAJ-BLR-78234"),
        ("OYO Rooms", "Pune - 1 Night", [("Standard Room", 2800), ("Early Check-in", 500), ("GST (12%)", 396)], 3696.0, (base_date + timedelta(days=25)).isoformat(), "hotel", "receipt_oyo_pune.pdf", "OYO-PNE-44521"),
        ("IRCTC", "Bangalore to Mysore (Shatabdi)", [("AC Chair Car", 780), ("Catering", 150), ("IRCTC Convenience", 40)], 970.0, (base_date + timedelta(days=28)).isoformat(), "train", "receipt_irctc_blr_mys.pdf", "PNR-4521876234"),
        ("Lemon Tree Hotel", "Chennai - 2 Nights", [("Business Room (2N)", 9600), ("Breakfast", 800), ("Parking", 200), ("GST (12%)", 1272)], 11872.0, (base_date + timedelta(days=30)).isoformat(), "hotel", "receipt_lemontree_chn.pdf", "LTH-CHN-91023"),
        ("SpiceJet", "Bangalore to Hyderabad", [("Economy Fare", 3400), ("Priority Boarding", 500), ("GST", 195)], 4095.0, (base_date + timedelta(days=35)).isoformat(), "airline", "receipt_spicejet_blr_hyd.pdf", "SG-1247"),
        ("Amazon Business", "Conference Supplies", [("Portable Projector", 15999), ("HDMI Cable Set", 599), ("Presenter Remote", 1499), ("Carry Bag", 899)], 18996.0, (base_date + timedelta(days=9)).isoformat(), "office", "receipt_amazon_conf.pdf", "ORD-408-2847561"),
        ("TechSummit India 2026", "Conference Registration", [("Early Bird Pass", 25000), ("Workshop Add-on", 5000), ("GST (18%)", 5400)], 35400.0, (base_date + timedelta(days=2)).isoformat(), "conference", "receipt_techsummit_reg.pdf", "TS26-IND-00847"),
    ]

    for merchant, addr, items, total, dt, rtype, fname, ref in pdf_receipts:
        _draw_receipt_pdf(merchant, addr, items, total, dt, rtype, fname, booking_ref=ref)

    total_files = len(png_receipts) + len(pdf_receipts)
    print(f"  {total_files} receipt files created ({len(png_receipts)} PNG + {len(pdf_receipts)} PDF)")
    print(f"\nAll assets in: {ASSETS_DIR.resolve()}")


if __name__ == "__main__":
    main()
