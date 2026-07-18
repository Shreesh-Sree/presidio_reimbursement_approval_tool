-- FULL DATABASE RESET + COMPREHENSIVE SEED
-- WARNING: Deletes ALL data, then seeds comprehensive demo dataset
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/sql

BEGIN;

-- ========================================================================
-- CLEANUP - Delete all data in reverse dependency order
-- ========================================================================

DELETE FROM audit_logs;
DELETE FROM payment_events;
DELETE FROM payment_records;
DELETE FROM payment_batches;
DELETE FROM notifications;
DELETE FROM comments;
DELETE FROM approval_history;
DELETE FROM approval_levels;
DELETE FROM attachments;
DELETE FROM expense_items;
DELETE FROM expense_reports;
DELETE FROM policy_rules;
DELETE FROM policies;
DELETE FROM vendors;
DELETE FROM expense_categories;
DELETE FROM workflow_rules;
DELETE FROM delegations;
DELETE FROM sessions;
DELETE FROM role_permissions;
DELETE FROM user_roles;
DELETE FROM permissions;
DELETE FROM roles;
DELETE FROM users;
DELETE FROM departments;
DELETE FROM organizations;

-- ========================================================================
-- SEED DATA
-- ========================================================================

-- Organizations
INSERT INTO organizations (id, name, code, base_currency, status)
VALUES (gen_random_uuid(), 'Presidio Demo Corp', 'PRESIDIO', 'USD', 'active');

-- Departments
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Engineering', 'ENG', org.id, 'active' FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Sales', 'SALES', org.id, 'active' FROM org;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Finance', 'FIN', org.id, 'active' FROM org;

-- Roles (schema: code, name, description, is_system_role, is_active)
INSERT INTO roles (id, code, name, description, is_system_role, is_active)
VALUES
  (gen_random_uuid(), 'admin', 'Administrator', 'Full system access', true, true),
  (gen_random_uuid(), 'manager', 'Manager', 'Approve reports', true, true),
  (gen_random_uuid(), 'finance', 'Finance', 'Process payments', true, true),
  (gen_random_uuid(), 'employee', 'Employee', 'Submit reports', true, true);

-- Permissions (schema: code, module, action)
INSERT INTO permissions (id, code, module, action, description, is_active)
VALUES
  (gen_random_uuid(), 'report_create', 'report', 'create', 'Create reports', true),
  (gen_random_uuid(), 'report_read', 'report', 'read', 'Read reports', true),
  (gen_random_uuid(), 'report_approve', 'report', 'approve', 'Approve reports', true),
  (gen_random_uuid(), 'payment_process', 'payment', 'process', 'Process payments', true),
  (gen_random_uuid(), 'user_manage', 'user', 'manage', 'Manage users', true);

-- Role-Permission mappings
WITH admin_role AS (SELECT id FROM roles WHERE code = 'admin'),
     all_perms AS (SELECT id FROM permissions)
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), admin_role.id, all_perms.id
FROM admin_role, all_perms;

WITH mgr_role AS (SELECT id FROM roles WHERE code = 'manager'),
     perms AS (SELECT id FROM permissions WHERE action IN ('create', 'read', 'approve'))
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), mgr_role.id, perms.id
FROM mgr_role, perms;

WITH fin_role AS (SELECT id FROM roles WHERE code = 'finance'),
     perms AS (SELECT id FROM permissions WHERE module IN ('report', 'payment'))
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), fin_role.id, perms.id
FROM fin_role, perms;

WITH emp_role AS (SELECT id FROM roles WHERE code = 'employee'),
     perms AS (SELECT id FROM permissions WHERE module = 'report' AND action IN ('create', 'read'))
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), emp_role.id, perms.id
FROM emp_role, perms;

-- Users (hierarchical structure)
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1)
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation)
SELECT gen_random_uuid(), 'ceo@presidio.demo', 'ceo', 'E001', 'CEO Anderson', org.id, dept.id, 'active', 'CEO'
FROM org, dept;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'FIN' LIMIT 1),
     ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo')
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'cfo@presidio.demo', 'cfo', 'E002', 'CFO Martinez', org.id, dept.id, 'active', 'CFO', ceo.id
FROM org, dept, ceo;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1),
     ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo')
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'manager@presidio.demo', 'manager', 'E003', 'Eng Manager', org.id, dept.id, 'active', 'Manager', ceo.id
FROM org, dept, ceo;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'SALES' LIMIT 1),
     ceo AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo')
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'sales@presidio.demo', 'sales', 'E004', 'Sales Rep', org.id, dept.id, 'active', 'Sales', ceo.id
FROM org, dept, ceo;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1),
     mgr AS (SELECT id FROM users WHERE email = 'manager@presidio.demo')
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status, designation, manager_user_id)
SELECT gen_random_uuid(), 'dev@presidio.demo', 'dev', 'E005', 'Developer', org.id, dept.id, 'active', 'Developer', mgr.id
FROM org, dept, mgr;

-- User role assignments
WITH ceo_usr AS (SELECT id FROM users WHERE email = 'ceo@presidio.demo'),
     admin_role AS (SELECT id FROM roles WHERE code = 'admin')
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), ceo_usr.id, admin_role.id FROM ceo_usr, admin_role;

WITH cfo_usr AS (SELECT id FROM users WHERE email = 'cfo@presidio.demo'),
     fin_role AS (SELECT id FROM roles WHERE code = 'finance')
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), cfo_usr.id, fin_role.id FROM cfo_usr, fin_role;

WITH mgr_usr AS (SELECT id FROM users WHERE email = 'manager@presidio.demo'),
     mgr_role AS (SELECT id FROM roles WHERE code = 'manager')
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), mgr_usr.id, mgr_role.id FROM mgr_usr, mgr_role;

WITH emp_usr AS (SELECT id FROM users WHERE email IN ('sales@presidio.demo', 'dev@presidio.demo')),
     emp_role AS (SELECT id FROM roles WHERE code = 'employee')
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), emp_usr.id, emp_role.id FROM emp_usr, emp_role;

-- Expense Categories
INSERT INTO expense_categories (id, code, name, description, receipt_required, max_amount)
VALUES
  (gen_random_uuid(), 'TRAVEL-FLIGHT', 'Flight', 'Air travel', true, 3000),
  (gen_random_uuid(), 'TRAVEL-HOTEL', 'Hotel', 'Accommodation', true, 2000),
  (gen_random_uuid(), 'MEALS', 'Meals', 'Business meals', true, 100),
  (gen_random_uuid(), 'OFFICE', 'Office Supplies', 'Stationery', true, 500),
  (gen_random_uuid(), 'TECH', 'Technology', 'Hardware/Software', true, 5000);

-- Vendors
INSERT INTO vendors (id, name, category, contact_email, status)
VALUES
  (gen_random_uuid(), 'Delta Airlines', 'Travel', 'corporate@delta.com', 'active'),
  (gen_random_uuid(), 'Marriott', 'Travel', 'corporate@marriott.com', 'active'),
  (gen_random_uuid(), 'AWS', 'Technology', 'billing@aws.com', 'active');

-- Policies
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO policies (id, organization_id, name, version_label, is_active, effective_from)
SELECT gen_random_uuid(), org.id, 'General Expense Policy', 'v1.0', true, NOW() - INTERVAL '30 days'
FROM org;

-- Policy Rules
WITH policy AS (SELECT id FROM policies WHERE name = 'General Expense Policy'),
     meals AS (SELECT id FROM expense_categories WHERE code = 'MEALS')
INSERT INTO policy_rules (id, policy_id, category_id, max_per_day, receipt_required_above)
SELECT gen_random_uuid(), policy.id, meals.id, 150, 25
FROM policy, meals;

-- Workflow Rules
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO workflow_rules (id, name, conditions_json, approval_chain_json, priority, is_active)
VALUES
  (gen_random_uuid(), 'Auto-Approve Small', '{"max_amount": 100}'::json, '[]'::json, 1, true),
  (gen_random_uuid(), 'Manager Approval', '{"min_amount": 100, "max_amount": 1000}'::json, '[]'::json, 2, true),
  (gen_random_uuid(), 'CFO Approval', '{"min_amount": 1000}'::json, '[]'::json, 3, true);

-- Expense Reports (various statuses)
WITH emp AS (SELECT id, department_id FROM users WHERE email = 'dev@presidio.demo')
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, currency_code, status, created_at, last_saved_at)
SELECT gen_random_uuid(), 'RPT-001', emp.id, emp.department_id, 'Office Supplies - Draft', 'Keyboard and mouse', 0, 'USD', 'draft', NOW() - INTERVAL '1 day', NOW()
FROM emp;

WITH emp AS (SELECT id, department_id FROM users WHERE email = 'dev@presidio.demo')
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, currency_code, status, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-002', emp.id, emp.department_id, 'Team Lunch', 'Q3 planning dinner', 85.50, 'USD', 'pending', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'
FROM emp;

WITH emp AS (SELECT id, department_id FROM users WHERE email = 'sales@presidio.demo')
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, currency_code, status, created_at, submitted_at)
SELECT gen_random_uuid(), 'RPT-003', emp.id, emp.department_id, 'Client Visit NYC', 'Flight + hotel', 1450, 'USD', 'approved', NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'
FROM emp;

-- Expense Items
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002'),
     cat AS (SELECT id FROM expense_categories WHERE code = 'MEALS')
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, 'Team dinner at Italian restaurant', 85.50, NOW() - INTERVAL '3 days'
FROM report, cat;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-003'),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL-FLIGHT'),
     vendor AS (SELECT id FROM vendors WHERE name = 'Delta Airlines')
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, vendor.id, 'Delta Airlines', 'Round-trip NYC', 550, NOW() - INTERVAL '10 days'
FROM report, cat, vendor;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-003'),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL-HOTEL'),
     vendor AS (SELECT id FROM vendors WHERE name = 'Marriott')
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, vendor_id, merchant_name, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 2, cat.id, vendor.id, 'Marriott', 'Hotel 3 nights', 900, NOW() - INTERVAL '10 days'
FROM report, cat, vendor;

-- Approval Levels
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002'),
     approver AS (SELECT id FROM users WHERE email = 'manager@presidio.demo')
INSERT INTO approval_levels (id, expense_report_id, approver_user_id, level_number, status)
SELECT gen_random_uuid(), report.id, approver.id, 1, 'pending'
FROM report, approver;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-003'),
     approver AS (SELECT id FROM users WHERE email = 'manager@presidio.demo')
INSERT INTO approval_levels (id, expense_report_id, approver_user_id, level_number, status, decision_date)
SELECT gen_random_uuid(), report.id, approver.id, 1, 'approved', NOW() - INTERVAL '8 days'
FROM report, approver;

-- Approval History
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-003'),
     approver AS (SELECT id FROM users WHERE email = 'manager@presidio.demo')
INSERT INTO approval_history (id, expense_report_id, action, performed_by, performed_at, remarks)
SELECT gen_random_uuid(), report.id, 'approved', approver.id, NOW() - INTERVAL '8 days', 'Approved - legitimate business trip'
FROM report, approver;

-- Comments
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002'),
     usr AS (SELECT id FROM users WHERE email = 'manager@presidio.demo')
INSERT INTO comments (id, expense_report_id, user_id, comment_text, visibility)
SELECT gen_random_uuid(), report.id, usr.id, 'Please attach receipt for amounts over $25', 'public'
FROM report, usr;

-- Delegations
WITH delegator AS (SELECT id FROM users WHERE email = 'manager@presidio.demo'),
     delegate AS (SELECT id FROM users WHERE email = 'dev@presidio.demo')
INSERT INTO delegations (id, delegator_user_id, delegate_user_id, start_date, end_date, scope, is_active, remarks)
SELECT gen_random_uuid(), delegator.id, delegate.id, NOW(), NOW() + INTERVAL '14 days', 'all', true, 'Vacation - 2 weeks'
FROM delegator, delegate;

-- Notifications
WITH usr AS (SELECT id FROM users WHERE email = 'dev@presidio.demo'),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002')
INSERT INTO notifications (id, recipient_user_id, template_code, channel, status, payload)
SELECT gen_random_uuid(), usr.id, 'report_pending_approval', 'in_app', 'pending',
  json_build_object('report_id', report.id, 'report_number', 'RPT-002')
FROM usr, report;

WITH usr AS (SELECT id FROM users WHERE email = 'manager@presidio.demo'),
     report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002')
INSERT INTO notifications (id, recipient_user_id, template_code, channel, status, payload)
SELECT gen_random_uuid(), usr.id, 'approval_needed', 'in_app', 'pending',
  json_build_object('report_id', report.id, 'report_number', 'RPT-002')
FROM usr, report;

COMMIT;

-- Verification
SELECT 'Organizations' AS table_name, COUNT(*) FROM organizations
UNION ALL SELECT 'Departments', COUNT(*) FROM departments
UNION ALL SELECT 'Users', COUNT(*) FROM users
UNION ALL SELECT 'Roles', COUNT(*) FROM roles
UNION ALL SELECT 'Permissions', COUNT(*) FROM permissions
UNION ALL SELECT 'User Roles', COUNT(*) FROM user_roles
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
UNION ALL SELECT 'Notifications', COUNT(*) FROM notifications;
