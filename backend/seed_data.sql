-- Seed database with sample data
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/sql

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

BEGIN;

-- 1. Organization
INSERT INTO organizations (id, name, code, base_currency, status)
VALUES (gen_random_uuid(), 'Presidio Demo Corp', 'PRESIDIO', 'USD', 'active')
ON CONFLICT (code) DO NOTHING;

-- 2. Departments
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Engineering', 'ENG', org.id, 'active' FROM org
ON CONFLICT (organization_id, code) DO NOTHING;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Sales', 'SALES', org.id, 'active' FROM org
ON CONFLICT (organization_id, code) DO NOTHING;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Marketing', 'MKT', org.id, 'active' FROM org
ON CONFLICT (organization_id, code) DO NOTHING;

-- 3. Users
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' AND organization_id = (SELECT id FROM org) LIMIT 1)
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status)
SELECT gen_random_uuid(), 'admin@presidio.demo', 'admin', 'EMP001', 'Admin User', org.id, dept.id, 'active'
FROM org, dept
ON CONFLICT (organization_id, email) DO NOTHING;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' AND organization_id = (SELECT id FROM org) LIMIT 1)
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status)
SELECT gen_random_uuid(), 'manager@presidio.demo', 'manager', 'EMP002', 'Manager Smith', org.id, dept.id, 'active'
FROM org, dept
ON CONFLICT (organization_id, email) DO NOTHING;

WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' AND organization_id = (SELECT id FROM org) LIMIT 1)
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status)
SELECT gen_random_uuid(), 'employee@presidio.demo', 'employee', 'EMP003', 'Employee Jones', org.id, dept.id, 'active'
FROM org, dept
ON CONFLICT (organization_id, email) DO NOTHING;

-- Set manager relationships
UPDATE users
SET manager_user_id = (SELECT id FROM users WHERE email = 'admin@presidio.demo' LIMIT 1)
WHERE email = 'manager@presidio.demo';

UPDATE users
SET manager_user_id = (SELECT id FROM users WHERE email = 'manager@presidio.demo' LIMIT 1)
WHERE email = 'employee@presidio.demo';

-- 4. Expense Categories (no organization_id or is_active in schema)
INSERT INTO expense_categories (id, name, code, description)
SELECT gen_random_uuid(), 'Travel', 'TRAVEL', 'Travel expenses'
ON CONFLICT (code) DO NOTHING;

INSERT INTO expense_categories (id, name, code, description)
SELECT gen_random_uuid(), 'Meals', 'MEALS', 'Meal expenses'
ON CONFLICT (code) DO NOTHING;

INSERT INTO expense_categories (id, name, code, description)
SELECT gen_random_uuid(), 'Office Supplies', 'SUPPLIES', 'Office supplies'
ON CONFLICT (code) DO NOTHING;

-- 5. Policies (complex schema - requires version_label, effective_from, is_active)
WITH org AS (SELECT id FROM organizations WHERE code = 'PRESIDIO')
INSERT INTO policies (id, name, version_label, organization_id, is_active, effective_from)
SELECT gen_random_uuid(), 'General Expense Policy', 'v1.0', org.id, true, NOW()
FROM org;

-- 6. Sample Expense Reports (requires report_number, employee_user_id, department_id)
WITH employee AS (SELECT id, department_id FROM users WHERE email = 'employee@presidio.demo' LIMIT 1)
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at)
SELECT gen_random_uuid(), 'RPT-001', employee.id, employee.department_id, 'Team Lunch - Q3 Planning', 'Team lunch for Q3 planning meeting', 85.50, 'pending', 'USD', NOW() - INTERVAL '2 days'
FROM employee;

WITH employee AS (SELECT id, department_id FROM users WHERE email = 'employee@presidio.demo' LIMIT 1)
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at)
SELECT gen_random_uuid(), 'RPT-002', employee.id, employee.department_id, 'Client Visit Travel', 'Flight and hotel for client visit', 1250.00, 'pending', 'USD', NOW() - INTERVAL '5 days'
FROM employee;

WITH manager AS (SELECT id, department_id FROM users WHERE email = 'manager@presidio.demo' LIMIT 1)
INSERT INTO expense_reports (id, report_number, employee_user_id, department_id, title, description, total_amount, status, currency_code, created_at)
SELECT gen_random_uuid(), 'RPT-003', manager.id, manager.department_id, 'Office Supplies', 'Monthly office supplies', 150.00, 'approved', 'USD', NOW() - INTERVAL '10 days'
FROM manager;

-- 7. Expense Items (requires expense_report_id, line_number, category_id)
WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-001' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'MEALS' LIMIT 1)
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, 'Team lunch at Italian restaurant', 85.50, NOW() - INTERVAL '2 days'
FROM report, cat;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL' LIMIT 1)
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, 'Round-trip flight to NYC', 450.00, NOW() - INTERVAL '5 days'
FROM report, cat;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-002' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'TRAVEL' LIMIT 1)
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 2, cat.id, 'Hotel - 3 nights', 800.00, NOW() - INTERVAL '5 days'
FROM report, cat;

WITH report AS (SELECT id FROM expense_reports WHERE report_number = 'RPT-003' LIMIT 1),
     cat AS (SELECT id FROM expense_categories WHERE code = 'SUPPLIES' LIMIT 1)
INSERT INTO expense_items (id, expense_report_id, line_number, category_id, description, amount, expense_date)
SELECT gen_random_uuid(), report.id, 1, cat.id, 'Printer paper and pens', 150.00, NOW() - INTERVAL '10 days'
FROM report, cat;

COMMIT;

-- Verify seeded data
SELECT 'Organizations' AS table_name, COUNT(*) AS count FROM organizations WHERE code = 'PRESIDIO'
UNION ALL
SELECT 'Departments', COUNT(*) FROM departments WHERE organization_id = (SELECT id FROM organizations WHERE code = 'PRESIDIO' LIMIT 1)
UNION ALL
SELECT 'Users', COUNT(*) FROM users WHERE organization_id = (SELECT id FROM organizations WHERE code = 'PRESIDIO' LIMIT 1)
UNION ALL
SELECT 'Categories', COUNT(*) FROM expense_categories WHERE code IN ('TRAVEL', 'MEALS', 'SUPPLIES')
UNION ALL
SELECT 'Policies', COUNT(*) FROM policies WHERE organization_id = (SELECT id FROM organizations WHERE code = 'PRESIDIO' LIMIT 1)
UNION ALL
SELECT 'Reports', COUNT(*) FROM expense_reports WHERE report_number LIKE 'RPT-%'
UNION ALL
SELECT 'Items', COUNT(*) FROM expense_items WHERE expense_report_id IN (SELECT id FROM expense_reports WHERE report_number LIKE 'RPT-%');
