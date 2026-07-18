-- Default two-stage workflow: Manager -> Finance.
-- workflow_rules is global in the current schema; it is not organization-scoped.
INSERT INTO workflow_rules (
    id,
    name,
    conditions_json,
    approval_chain_json,
    priority,
    is_active,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    'Standard Two-Stage Approval',
    '{}'::json,
    '[
        {"manager_level": 1},
        {"role_code": "finance"}
    ]'::json,
    100,
    true,
    now(),
    now()
WHERE NOT EXISTS (
    SELECT 1
    FROM workflow_rules
    WHERE name = 'Standard Two-Stage Approval'
);
