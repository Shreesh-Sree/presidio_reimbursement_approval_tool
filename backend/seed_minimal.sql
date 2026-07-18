-- Minimal Seed Data - Matches Actual Migration Schema
-- Run in Supabase SQL Editor after migrations complete
-- Safe to re-run (handles existing data)

BEGIN;

-- Organization
INSERT INTO organizations (id, name, code, base_currency, status)
VALUES (gen_random_uuid(), 'Presidio Demo', 'DEMO', 'USD', 'active')
ON CONFLICT (code) DO NOTHING;

-- Departments
WITH org AS (SELECT id FROM organizations WHERE code = 'DEMO')
INSERT INTO departments (id, name, code, organization_id, status)
SELECT gen_random_uuid(), 'Engineering', 'ENG', org.id, 'active' FROM org
ON CONFLICT (organization_id, code) DO NOTHING;

-- Roles (schema: code, name, description, is_system_role, is_active)
INSERT INTO roles (id, code, name, description, is_system_role, is_active)
VALUES
  (gen_random_uuid(), 'admin', 'Administrator', 'Full access', true, true),
  (gen_random_uuid(), 'employee', 'Employee', 'Submit reports', true, true)
ON CONFLICT (code) DO NOTHING;

-- Permissions (schema: code, module, action, description, is_active)
INSERT INTO permissions (id, code, module, action, description, is_active)
VALUES
  (gen_random_uuid(), 'report_create', 'report', 'create', 'Create reports', true),
  (gen_random_uuid(), 'report_approve', 'report', 'approve', 'Approve reports', true)
ON CONFLICT (module, action) DO NOTHING;

-- Users (password_hash nullable in OAuth mode per migration 007)
WITH org AS (SELECT id FROM organizations WHERE code = 'DEMO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1)
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status)
SELECT gen_random_uuid(), 'admin@demo.local', 'admin', 'E001', 'Admin User', org.id, dept.id, 'active'
FROM org, dept
ON CONFLICT (organization_id, email) DO NOTHING;

WITH org AS (SELECT id FROM organizations WHERE code = 'DEMO'),
     dept AS (SELECT id FROM departments WHERE code = 'ENG' LIMIT 1)
INSERT INTO users (id, email, username, employee_number, full_name, organization_id, department_id, status)
SELECT gen_random_uuid(), 'emp@demo.local', 'emp', 'E002', 'Employee User', org.id, dept.id, 'active'
FROM org, dept
ON CONFLICT (organization_id, email) DO NOTHING;

-- User Roles
WITH admin_usr AS (SELECT id FROM users WHERE email = 'admin@demo.local' LIMIT 1),
     admin_role AS (SELECT id FROM roles WHERE code = 'admin' LIMIT 1)
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), admin_usr.id, admin_role.id FROM admin_usr, admin_role
WHERE EXISTS (SELECT 1 FROM admin_usr) AND EXISTS (SELECT 1 FROM admin_role)
  AND NOT EXISTS (SELECT 1 FROM user_roles WHERE user_id = admin_usr.id AND role_id = admin_role.id);

WITH emp_usr AS (SELECT id FROM users WHERE email = 'emp@demo.local' LIMIT 1),
     emp_role AS (SELECT id FROM roles WHERE code = 'employee' LIMIT 1)
INSERT INTO user_roles (id, user_id, role_id)
SELECT gen_random_uuid(), emp_usr.id, emp_role.id FROM emp_usr, emp_role
WHERE EXISTS (SELECT 1 FROM emp_usr) AND EXISTS (SELECT 1 FROM emp_role)
  AND NOT EXISTS (SELECT 1 FROM user_roles WHERE user_id = emp_usr.id AND role_id = emp_role.id);

COMMIT;

-- Verify
SELECT 'Organizations' AS table_name, COUNT(*) AS count FROM organizations
UNION ALL SELECT 'Departments', COUNT(*) FROM departments
UNION ALL SELECT 'Users', COUNT(*) FROM users
UNION ALL SELECT 'Roles', COUNT(*) FROM roles
UNION ALL SELECT 'Permissions', COUNT(*) FROM permissions
UNION ALL SELECT 'User Roles', COUNT(*) FROM user_roles;
