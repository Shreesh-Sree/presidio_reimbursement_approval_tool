-- Fix: add role codes required by role_code workflow lookups.
UPDATE roles SET code = 'admin' WHERE name = 'Admin' AND (code IS NULL OR code = '');
UPDATE roles SET code = 'administrator' WHERE name = 'Administrator' AND (code IS NULL OR code = '');
UPDATE roles SET code = 'manager' WHERE name = 'Manager' AND (code IS NULL OR code = '');
UPDATE roles SET code = 'finance' WHERE name = 'Finance' AND (code IS NULL OR code = '');
UPDATE roles SET code = 'employee' WHERE name = 'Employee' AND (code IS NULL OR code = '');

INSERT INTO roles (id, code, name, description, is_system_role, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'finance',
    'Finance',
    'Finance team - manage payments and final approval',
    true,
    true,
    now(),
    now()
)
ON CONFLICT (code) DO NOTHING;
