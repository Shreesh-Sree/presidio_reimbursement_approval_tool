import pytest
from datetime import UTC, datetime
from app.models.policy import Policy, PolicyRule
from app.models.expense_category import ExpenseCategory


def test_policy_model_create(db, seeded_org):
    """Test creating a policy with versioning."""
    policy = Policy(
        organization_id=seeded_org.id,
        name="Travel Policy",
        version_label="v1.0",
        is_active=True,
        effective_from=datetime(2026, 7, 15, tzinfo=UTC),
    )
    db.add(policy)
    db.commit()
    
    fetched = db.query(Policy).filter(Policy.name == "Travel Policy").first()
    assert fetched is not None
    assert fetched.version_label == "v1.0"
    assert fetched.is_active is True


def test_policy_rule_model_create(db, seeded_org):
    """Test creating policy rules tied to categories."""
    policy = Policy(
        organization_id=seeded_org.id,
        name="Travel Policy",
        version_label="v1.0",
        is_active=True,
        effective_from=datetime(2026, 7, 15, tzinfo=UTC),
    )
    db.add(policy)
    db.flush()
    
    category = ExpenseCategory(
        code="TAXI",
        name="Taxi",
        receipt_required=True,
    )
    db.add(category)
    db.flush()
    
    rule = PolicyRule(
        policy_id=policy.id,
        category_id=category.id,
        max_per_day=100.00,
        max_per_trip=50.00,
        per_category_cap=500.00,
        receipt_required_above=25.00,
    )
    db.add(rule)
    db.commit()
    
    fetched = db.query(PolicyRule).filter(PolicyRule.policy_id == policy.id).first()
    assert fetched is not None
    assert fetched.max_per_day == 100.00
