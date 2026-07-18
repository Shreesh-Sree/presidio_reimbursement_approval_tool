-- Grant access-request administration to the admin role.
INSERT INTO permissions (id, code, module, action, description, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), 'user_manage', 'user', 'manage', 'Manage users and access requests', true, now(), now())
ON CONFLICT (module, action) DO NOTHING;

WITH admin_role AS (SELECT id FROM roles WHERE code = 'admin'),
     permission AS (SELECT id FROM permissions WHERE module = 'user' AND action = 'manage')
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), admin_role.id, permission.id, now(), now()
FROM admin_role, permission
ON CONFLICT DO NOTHING;

SELECT r.code AS role, p.module, p.action, p.code
FROM roles AS r
JOIN role_permissions AS rp ON rp.role_id = r.id
JOIN permissions AS p ON p.id = rp.permission_id
WHERE r.code = 'admin'
ORDER BY p.module, p.action;
