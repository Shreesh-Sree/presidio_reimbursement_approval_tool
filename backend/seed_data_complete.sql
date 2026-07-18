-- Comprehensive Seed Data for Presidio Reimbursement Tool
-- Covers all features: RBAC, workflows, approvals, payments, delegations, notifications
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

BEGIN;

-- ========================================================================
-- 1. ORGANIZATIONS
-- ========================================================================
INSERT INTO organizations (id, name, code, base_currency, status)
VALUES (gen_random_uuid(), 'Presidio Demo Corp', 'PRESIDIO', 'USD', 'active');

-- ========================================================================
-- 2. DEPARTMENTS
-- ========================================================================
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Engineering', 'ENG', org.id, 'active' FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Sales', 'SALES', org.id, 'active' FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Finance', 'FIN', org.id, 'active' FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'HR', 'HR', org.id, 'active' FROM org;

-- ========================================================================
-- 3. ROLES & PERMISSIONS (RBAC)
-- ========================================================================

-- Roles
INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), 'Admin', 'Full system access';

INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), 'Manager', 'Department manager - can approve reports';

INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), 'Finance', 'Finance team - manage payments';

INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), 'Employee', 'Regular employee - submit reports';

-- Permissions
INSERT INTO permissions (id, resource, action, description)
SELECT gen_random_uuid(), 'report', 'create', 'Create expense reports';

INSERT INTO permissions (id, resource, action, description)
SELECT gen_random_uuid(), 'report', 'approve', 'Approve expense reports';

INSERT INTO permissions (id, resource, action, description)
SELECT gen_random_uuid(), 'payment', 'process', 'Process payments';

INSERT INTO permissions (id, resource, action, description)
SELECT gen_random_uuid(), 'policy', 'manage', 'Manage policies';

INSERT INTO permissions (id, resource, action, description)
SELECT gen_random_uuid(), 'user', 'manage', 'Manage users';

-- Role-Permission Assignments
WITH admin_role AS (SELECT id FROM roles WHERE name = 'Admin' LIMIT 1);
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), admin_role.id, permissions.id
FROM admin_role, permissions;

WITH manager_role AS (SELECT id FROM roles WHERE name = 'Manager' LIMIT 1),
     perms AS (SELECT id FROM permissions WHERE action IN ('create', 'approve'));
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), manager_role.id, perms.id
FROM manager_role, perms;

WITH finance_role AS (SELECT id FROM roles WHERE name = 'Finance' LIMIT 1),
     perms AS (SELECT id FROM permissions WHERE action IN ('create', 'process'));
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), finance_role.id, perms.id
FROM finance_role, perms;

WITH employee_role AS (SELECT id FROM roles WHERE name = 'Employee' LIMIT 1),
     perms AS (SELECT id FROM permissions WHERE resource = 'report' AND action = 'create');
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), employee_role.id, perms.id
FROM employee_role, perms;

-- ========================================================================
-- 4. USERS (Hierarchical Structure)
-- ========================================================================
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation)
SELECT gen_random_uuid(), 'ceo@presidio.demo', 'ceo', 'EMP001', 'CEO Anderson', org.id, dept.id, 'active', 'Chief Executive Officer'
FROM org, dept;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'FIN' LIMIT 1),
     ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'cfo@presidio.demo', 'cfo', 'EMP002', 'CFO Martinez', org.id, dept.id, 'active', 'Chief Financial Officer', ceo.id
FROM org, dept, ceo

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1),
     ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'eng.manager@presidio.demo', 'engmanager', 'EMP003', 'Engineering Manager Smith', org.id, dept.id, 'active', 'Engineering Manager', ceo.id
FROM org, dept, ceo

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'SALES' LIMIT 1),
     ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'sales.manager@presidio.demo', 'salesmanager', 'EMP004', 'Sales Manager Brown', org.id, dept.id, 'active', 'Sales Manager', ceo.id
FROM org, dept, ceo

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'FIN' LIMIT 1),
     cfo AS (SELECT id FROM users WHERE email = 'cfo@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'accountant@presidio.demo', 'accountant', 'EMP005', 'Senior Accountant Lee', org.id, dept.id, 'active', 'Senior Accountant', cfo.id
FROM org, dept, cfo

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1),
     mgr AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'dev1@presidio.demo', 'dev1', 'EMP006', 'Developer Alice Chen', org.id, dept.id, 'active', 'Senior Developer', mgr.id
FROM org, dept, mgr

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1),
     mgr AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'dev2@presidio.demo', 'dev2', 'EMP007', 'Developer Bob Wilson', org.id, dept.id, 'active', 'Developer', mgr.id
FROM org, dept, mgr

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'SALES' LIMIT 1),
     mgr AS (SELECT id FROM users WHERE email = 'sales.manager@presidio.demo' LIMIT 1);
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'sales1@presidio.demo', 'sales1', 'EMP008', 'Sales Rep Carol Davis', org.id, dept.id, 'active', 'Sales Representative', mgr.id
FROM org, dept, mgr

-- User Role Assignments
WITH ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo' LIMIT 1),
     admin_role AS (SELECT id FROM roles WHERE name = 'Admin' LIMIT 1);
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), ceo.id, admin_role.id FROM ceo, admin_role;

WITH cfo AS (SELECT id FROM users WHERE email = 'cfo@presidio.demo' LIMIT 1),
     finance_role AS (SELECT id FROM roles WHERE name = 'Finance' LIMIT 1);
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), cfo.id, finance_role.id FROM cfo, finance_role;

WITH mgr AS (SELECT id FROM users WHERE email IN ('eng.manager@presidio.demo', 'sales.manager@presidio.demo')),
     manager_role AS (SELECT id FROM roles WHERE name = 'Manager' LIMIT 1);
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), mgr.id, manager_role.id FROM mgr, manager_role;

WITH emp AS (SELECT id FROM users WHERE email IN ('accountant@presidio.demo', 'dev1@presidio.demo', 'dev2@presidio.demo', 'sales1@presidio.demo')),
     employee_role AS (SELECT id FROM roles WHERE name = 'Employee' LIMIT 1);
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), emp.id, employee_role.id FROM emp, employee_role;

-- ========================================================================
-- 5. EXPENSE CATEGORIES
-- ========================================================================
INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'TRAVEL-FLIGHT', 'Flight Travel', 'Airline tickets and baggage fees', true, 3000.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'TRAVEL-HOTEL', 'Hotel Accommodation', 'Hotel stays during business travel', true, 2000.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'TRAVEL-CAR', 'Car Rental', 'Vehicle rentals and fuel', true, 1000.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'MEALS-BUSINESS', 'Business Meals', 'Client meetings and team meals', true, 100.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'MEALS-PERDIEM', 'Per Diem', 'Daily meal allowance', false, 75.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'OFFICE-SUPPLIES', 'Office Supplies', 'Stationery and office equipment', true, 500.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'TECH-HARDWARE', 'Tech Hardware', 'Computers, monitors, peripherals', true, 5000.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'TECH-SOFTWARE', 'Software/SaaS', 'Software licenses and subscriptions', true, 1000.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'TRAINING', 'Training & Conferences', 'Professional development', true, 2500.00

INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
SELECT gen_random_uuid(), 'MISC', 'Miscellaneous', 'Other business expenses', true, 250.00

-- ========================================================================
-- 6. VENDORS
-- ========================================================================
INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'Delta Airlines', 'Travel', 'corporate@delta.com', '+1-800-221-1212', 'active';

INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'Marriott Hotels', 'Travel', 'corporate@marriott.com', '+1-800-627-7468', 'active';

INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'Enterprise Rent-A-Car', 'Travel', 'corporate@enterprise.com', '+1-855-266-9565', 'active';

INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'Uber', 'Transportation', 'business@uber.com', null, 'active';

INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'AWS', 'Technology', 'billing@aws.com', null, 'active';

INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'Microsoft', 'Technology', 'accounts@microsoft.com', null, 'active';

INSERT INTO vendors (id, name, category, contact_email, phone, status)
SELECT gen_random_uuid(), 'Staples', 'Office Supplies', 'corporate@staples.com', '+1-800-378-2753', 'active';

-- ========================================================================
-- 7. POLICIES & POLICY RULES
-- ========================================================================
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO policies (id, organization_id, name, version_label, is_active, effective_from)
SELECT gen_random_uuid(), org.id, 'General Travel & Expense Policy', 'v1.0', true, NOW() - INTERVAL '30 days'
FROM org;

-- Policy Rules
WITH policy AS (SELECT id FROM policies WHERE name = 'General Travel & Expense Policy' LIMIT 1),
     meals_cat AS (SELECT id FROM expense_categories WHERE code = 'MEALS-BUSINESS' LIMIT 1);
INSERT INTO policy_rules (id, policy_id, category_id, max_per_day, receipt_required_above)
SELECT gen_random_uuid(), policy.id, meals_cat.id, 150.00, 25.00
FROM policy, meals_cat;

WITH policy AS (SELECT id FROM policies WHERE name = 'General Travel & Expense Policy' LIMIT 1),
     flight_cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL-FLIGHT' LIMIT 1);
INSERT INTO policy_rules (id, policy_id, category_id, max_per_trip, receipt_required_above)
SELECT gen_random_uuid(), policy.id, flight_cat.id, 3000.00, 0.01
FROM policy, flight_cat;

WITH policy AS (SELECT id FROM policies WHERE name = 'General Travel & Expense Policy' LIMIT 1),
     hotel_cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL-HOTEL' LIMIT 1);
INSERT INTO policy_rules (id, policy_id, category_id, max_per_day, receipt_required_above)
SELECT gen_random_uuid(), policy.id, hotel_cat.id, 250.00, 0.01
FROM policy, hotel_cat;

-- ========================================================================
-- 8. WORKFLOW RULES (Auto-Approval Logic)
-- ========================================================================
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO workflow_rules (id, organization_id, name, description, condition_json, is_active, priority)
SELECT gen_random_uuid(), org.id, 'Auto-Approve Small Expenses', 'Auto-approve reports under $100', '{"max_amount": 100}', true, 1
FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO workflow_rules (id, organization_id, name, description, condition_json, is_active, priority)
SELECT gen_random_uuid(), org.id, 'Manager Approval Required', 'Reports over $100 need manager approval', '{"min_amount": 100, "max_amount": 1000}', true, 2
FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO');
INSERT INTO workflow_rules (id, organization_id, name, description, condition_json, is_active, priority)
SELECT gen_random_uuid(), org.id, 'CFO Approval Required', 'Reports over $1000 need CFO approval', '{"min_amount": 1000}', true, 3
FROM org;

-- ========================================================================
-- 9. EXPENSE REPORTS (Various States)
-- ========================================================================

-- Draft Report
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'dev1@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, last_saved_at)
SELECT gen_random_uuid(), 'RPT-2026-001', emp.id, emp.department_id, 'Conference Expenses - Draft', 'Tickets and hotel for tech conference', 0, 'draft', 'USD', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 hour'
FROM emp;

-- Pending Approval (Small)
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'dev2@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-2026-002', emp.id, emp.department_id, 'Office Supplies', 'Keyboard and mouse', 75.50, 'pending', 'USD', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'
FROM emp;

-- Pending Approval (Medium - Needs Manager)
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'dev1@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-2026-003', emp.id, emp.department_id, 'Client Dinner', 'Dinner with potential client', 285.00, 'pending', 'USD', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'
FROM emp;

-- Approved Report
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'sales1@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-2026-004', emp.id, emp.department_id, 'Sales Trip to NYC', 'Flight, hotel, and meals', 1545.75, 'approved', 'USD', NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'
FROM emp;

-- Paid Report
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'accountant@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-2026-005', emp.id, emp.department_id, 'Monthly SaaS Subscriptions', 'Software licenses', 450.00, 'paid', 'USD', NOW() - INTERVAL '20 days', NOW() - INTERVAL '20 days'
FROM emp;

-- Rejected Report
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'dev2@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-2026-006', emp.id, emp.department_id, 'Gym Membership', 'Personal gym membership - rejected', 120.00, 'rejected', 'USD', NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days'
FROM emp;

-- Large Report (Needs CFO Approval)
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-2026-007', emp.id, emp.department_id, 'Team Conference - Annual Summit', 'Conference tickets for 5 team members', 3250.00, 'pending', 'USD', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'
FROM emp;

-- ========================================================================
-- 10. EXPENSE ITEMS
-- ========================================================================

-- RPT-2026-002 items
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-002' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'OFFICE-SUPPLIES' LIMIT 1),
     vendor AS (SELECT id FROM vendors WHERE name = 'Staples' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, vendor.id, 'Staples', 'Mechanical keyboard', 55.50, NOW() - INTERVAL '2 days'
FROM report, cat, vendor;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-002' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'OFFICE-SUPPLIES' LIMIT 1),
     vendor AS (SELECT id FROM vendors WHERE name = 'Staples' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 2, cat.id, vendor.id, 'Staples', 'Ergonomic mouse', 20.00, NOW() - INTERVAL '2 days'
FROM report, cat, vendor;

-- RPT-2026-003 items
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-003' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'MEALS-BUSINESS' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, 'The Capital Grille', 'Dinner for 4 people with client', 285.00, NOW() - INTERVAL '3 days'
FROM report, cat;

-- RPT-2026-004 items (Approved - NYC Trip)
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL-FLIGHT' LIMIT 1),
     vendor AS (SELECT id FROM vendors WHERE name = 'Delta Airlines' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, vendor.id, 'Delta Airlines', 'Round-trip flight to NYC', 485.00, NOW() - INTERVAL '10 days'
FROM report, cat, vendor;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL-HOTEL' LIMIT 1),
     vendor AS (SELECT id FROM vendors WHERE name = 'Marriott Hotels' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 2, cat.id, vendor.id, 'Marriott Marquis NYC', 'Hotel - 3 nights', 875.00, NOW() - INTERVAL '9 days'
FROM report, cat, vendor;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'MEALS-BUSINESS' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 3, cat.id, 'Various restaurants', 'Meals during trip', 185.75, NOW() - INTERVAL '9 days'
FROM report, cat;

-- RPT-2026-005 items (Paid)
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-005' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TECH-SOFTWARE' LIMIT 1),
     vendor AS (SELECT id FROM vendors WHERE name = 'AWS' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, vendor.id, 'AWS', 'Monthly cloud hosting', 250.00, NOW() - INTERVAL '20 days'
FROM report, cat, vendor;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-005' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TECH-SOFTWARE' LIMIT 1),
     vendor AS (SELECT id FROM vendors WHERE name = 'Microsoft' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 2, cat.id, vendor.id, 'Microsoft', 'Office 365 licenses', 200.00, NOW() - INTERVAL '20 days'
FROM report, cat, vendor;

-- RPT-2026-007 items (Large pending)
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-007' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAINING' LIMIT 1);
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, 'TechSummit 2026', 'Conference tickets - 5 attendees', 3250.00, NOW() - INTERVAL '5 days'
FROM report, cat;

-- ========================================================================
-- 11. APPROVAL LEVELS (Multi-tier Approval Workflow)
-- ========================================================================

-- RPT-2026-003 needs manager approval
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-003' LIMIT 1),
     approver AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO approval_levels (id, expense_report_id, level_number, approver_user_id, status)
SELECT gen_random_uuid(), report.id, 1, approver.id, 'pending'
FROM report, approver;

-- RPT-2026-004 was approved by manager
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1),
     approver AS (SELECT id FROM users WHERE email = 'sales.manager@presidio.demo' LIMIT 1);
INSERT INTO approval_levels (id, expense_report_id, level_number, approver_user_id, status)
SELECT gen_random_uuid(), report.id, 1, approver.id, 'approved'
FROM report, approver;

-- RPT-2026-007 needs manager AND CFO approval
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-007' LIMIT 1),
     approver AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO approval_levels (id, expense_report_id, level_number, approver_user_id, status)
SELECT gen_random_uuid(), report.id, 1, approver.id, 'pending'
FROM report, approver;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-007' LIMIT 1),
     approver AS (SELECT id FROM users WHERE email = 'cfo@presidio.demo' LIMIT 1);
INSERT INTO approval_levels (id, expense_report_id, level_number, approver_user_id, status)
SELECT gen_random_uuid(), report.id, 2, approver.id, 'pending'
FROM report, approver;

-- ========================================================================
-- 12. APPROVAL HISTORY
-- ========================================================================

-- RPT-2026-004 approval history
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1),
     approver AS (SELECT id FROM users WHERE email = 'sales.manager@presidio.demo' LIMIT 1);
INSERT INTO approval_history (id, expense_report_id, approver_user_id, action, comments, created_at)
SELECT gen_random_uuid(), report.id, approver.id, 'approved', 'Approved - legitimate business trip', NOW() - INTERVAL '8 days'
FROM report, approver;

-- RPT-2026-006 rejection history
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-006' LIMIT 1),
     approver AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO approval_history (id, expense_report_id, approver_user_id, action, comments, created_at)
SELECT gen_random_uuid(), report.id, approver.id, 'rejected', 'Personal expense - not business related. Please submit only business expenses.', NOW() - INTERVAL '14 days'
FROM report, approver;

-- ========================================================================
-- 13. COMMENTS
-- ========================================================================

-- Comment on RPT-2026-003
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-003' LIMIT 1),
     usr AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1);
INSERT INTO comments (id, expense_report_id, user_id, content, created_at)
SELECT gen_random_uuid(), report.id, usr.id, 'Please attach the receipt for this dinner. Required for amounts over $25.', NOW() - INTERVAL '2 days'
FROM report, user;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-003' LIMIT 1),
     usr AS (SELECT id FROM users WHERE email = 'dev1@presidio.demo' LIMIT 1);
INSERT INTO comments (id, expense_report_id, user_id, content, created_at)
SELECT gen_random_uuid(), report.id, usr.id, 'Receipt uploaded! Sorry for the delay.', NOW() - INTERVAL '1 day'
FROM report, user;

-- ========================================================================
-- 14. DELEGATIONS (Manager Delegation While On Leave)
-- ========================================================================

-- Eng Manager delegates to Senior Dev for 2 weeks
WITH delegator AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1),
     delegate AS (SELECT id FROM users WHERE email = 'dev1@presidio.demo' LIMIT 1);
INSERT INTO delegations (id, delegator_user_id, delegate_user_id, start_date, end_date, reason, is_active)
SELECT gen_random_uuid(), delegator.id, delegate.id, NOW(), NOW() + INTERVAL '14 days', 'Vacation - on leave for 2 weeks', true
FROM delegator, delegate;

-- ========================================================================
-- 15. NOTIFICATIONS
-- ========================================================================

-- Notification to dev2 about approval
WITH usr AS (SELECT id FROM users WHERE email = 'dev2@presidio.demo' LIMIT 1),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-002' LIMIT 1);
INSERT INTO notifications (id, user_id, type, title, message, reference_type, reference_id, is_read, created_at)
SELECT gen_random_uuid(), usr.id, 'report_pending', 'Report Submitted', 'Your expense report RPT-2026-002 is pending approval', 'expense_report', report.id, false, NOW() - INTERVAL '2 days'
FROM usr, report;

-- Notification to manager about pending approval
WITH usr AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-003' LIMIT 1);
INSERT INTO notifications (id, user_id, type, title, message, reference_type, reference_id, is_read, created_at)
SELECT gen_random_uuid(), usr.id, 'approval_needed', 'Approval Needed', 'Expense report RPT-2026-003 from Developer Alice Chen requires your approval', 'expense_report', report.id, false, NOW() - INTERVAL '3 days'
FROM usr, report;

-- Notification to sales1 about approval
WITH usr AS (SELECT id FROM users WHERE email = 'sales1@presidio.demo' LIMIT 1),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1);
INSERT INTO notifications (id, user_id, type, title, message, reference_type, reference_id, is_read, created_at)
SELECT gen_random_uuid(), usr.id, 'report_approved', 'Report Approved', 'Your expense report RPT-2026-004 has been approved and sent to finance', 'expense_report', report.id, true, NOW() - INTERVAL '8 days'
FROM usr, report;

-- ========================================================================
-- 16. PAYMENT RECORDS & BATCHES
-- ========================================================================

-- Payment Batch
INSERT INTO payment_batches (id, batch_number, total_amount, currency_code, status, created_by_user_id, created_at)
SELECT gen_random_uuid(), 'BATCH-2026-001', 450.00, 'USD', 'processed',
       (SELECT id FROM users WHERE email = 'accountant@presidio.demo' LIMIT 1),
       NOW() - INTERVAL '15 days';

-- Payment Record for RPT-2026-005
WITH batch AS (SELECT id FROM payment_batches WHERE batch_number = 'BATCH-2026-001' LIMIT 1),
     report AS (SELECT id, employee_user_id, total_amount FROM expense_reports WHERE report_number = 'RPT-2026-005' LIMIT 1);
INSERT INTO payment_records (id, batch_id, expense_report_id, payee_user_id, amount, currency_code, payment_method, payment_date, status)
SELECT gen_random_uuid(), batch.id, report.id, report.employee_user_id, report.total_amount, 'USD', 'bank_transfer', NOW() - INTERVAL '15 days', 'completed'
FROM batch, report;

-- Payment Event
WITH record AS (SELECT id FROM payment_records LIMIT 1);
INSERT INTO payment_events (id, payment_record_id, event_type, description, created_at)
SELECT gen_random_uuid(), record.id, 'payment_initiated', 'Payment initiated via ACH transfer', NOW() - INTERVAL '15 days'
FROM record;

WITH record AS (SELECT id FROM payment_records LIMIT 1);
INSERT INTO payment_events (id, payment_record_id, event_type, description, created_at)
SELECT gen_random_uuid(), record.id, 'payment_completed', 'Payment successfully completed', NOW() - INTERVAL '14 days'
FROM record;

-- ========================================================================
-- 17. AUDIT LOGS
-- ========================================================================

WITH usr AS (SELECT id FROM users WHERE email = 'dev1@presidio.demo' LIMIT 1),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-003' LIMIT 1);
INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details, created_at)
SELECT gen_random_uuid(), usr.id, 'create', 'expense_report', report.id, '{"report_number": "RPT-2026-003", "total_amount": 285.00}', NOW() - INTERVAL '3 days'
FROM usr, report;

WITH usr AS (SELECT id FROM users WHERE email = 'eng.manager@presidio.demo' LIMIT 1),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-2026-004' LIMIT 1);
INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details, created_at)
SELECT gen_random_uuid(), usr.id, 'approve', 'expense_report', report.id, '{"report_number": "RPT-2026-004", "status": "approved"}', NOW() - INTERVAL '8 days'
FROM usr, report;

COMMIT;

-- ========================================================================
-- VERIFICATION QUERY
-- ========================================================================
SELECT 'Organizations' AS table_name, COUNT(*) AS count FROM organizations
UNION ALL SELECT 'Departments', COUNT(*) FROM departments
UNION ALL SELECT 'Users', COUNT(*) FROM usrs
UNION ALL SELECT 'Roles', COUNT(*) FROM roles
UNION ALL SELECT 'Permissions', COUNT(*) FROM permissions
UNION ALL SELECT 'User Roles', COUNT(*) FROM usr_roles
UNION ALL SELECT 'Expense Categories', COUNT(*) FROM expense_categories
UNION ALL SELECT 'Vendors', COUNT(*) FROM vendors
UNION ALL SELECT 'Policies', COUNT(*) FROM policies
UNION ALL SELECT 'Policy Rules', COUNT(*) FROM policy_rules
UNION ALL SELECT 'Workflow Rules', COUNT(*) FROM workflow_rules
UNION ALL SELECT 'Expense Reports', COUNT(*) FROM expense_reports
UNION ALL SELECT 'Expense Items', COUNT(*) FROM expense_items
UNION ALL SELECT 'Approval Levels', COUNT(*) FROM approval_levels
UNION ALL SELECT 'Approval History', COUNT(*) FROM approval_history
UNION ALL SELECT 'Comments', COUNT(*) FROM comments
UNION ALL SELECT 'Delegations', COUNT(*) FROM delegations
UNION ALL SELECT 'Notifications', COUNT(*) FROM notifications
UNION ALL SELECT 'Payment Batches', COUNT(*) FROM payment_batches
UNION ALL SELECT 'Payment Records', COUNT(*) FROM payment_records
UNION ALL SELECT 'Payment Events', COUNT(*) FROM payment_events
UNION ALL SELECT 'Audit Logs', COUNT(*) FROM audit_logs;
