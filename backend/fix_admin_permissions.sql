-- Fix admin permissions for access requests page

-- 1. Add user:manage permission
INSERT INTO permissions (id, code, module, action, description, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), 'user_manage', 'user', 'manage', 'Manage users and access requests', true, now(), now())
ON CONFLICT (module, action) DO NOTHING;

-- 2. Link permission to admin role
WITH admin_role AS (SELECT id FROM roles WHERE code = 'admin'),
     perm AS (SELECT id FROM permissions WHERE module = 'user' AND action = 'manage')
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), admin_role.id, perm.id, now(), now()
FROM admin_role, perm
ON CONFLICT DO NOTHING;

-- 3. Verify - show admin permissions
SELECT r.code as role, p.module, p.action, p.code
FROM roles r
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'admin'
ORDER BY p.module, p.action;
