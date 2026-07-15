from sqlalchemy.orm import Session
from app.models.policy import Policy, PolicyRule
import json
from datetime import datetime


def create_policy_version(db: Session, name: str, version_label: str, effective_from: str, rules_data: dict = None):
    """Create a new policy version. Set is_active=False initially."""
    policy = Policy(
        name=name,
        version_label=version_label,
        is_active=False,
        effective_from=effective_from,
    )
    db.add(policy)
    db.flush()
    
    if rules_data:
        for rule in rules_data.get("rules", []):
            policy_rule = PolicyRule(
                policy_id=policy.id,
                category_id=rule.get("category_id"),
                vendor_id=rule.get("vendor_id"),
                max_per_day=rule.get("max_per_day"),
                max_per_trip=rule.get("max_per_trip"),
                per_category_cap=rule.get("per_category_cap"),
                receipt_required_above=rule.get("receipt_required_above"),
            )
            db.add(policy_rule)
    
    db.commit()
    db.refresh(policy)
    return policy


def activate_policy(db: Session, policy_id: str):
    """Activate a policy (deactivate all others first)."""
    # Deactivate all other policies
    db.query(Policy).filter(Policy.is_active == True).update({"is_active": False})
    
    # Activate the target policy
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise ValueError(f"Policy {policy_id} not found")
    policy.is_active = True
    db.commit()
    db.refresh(policy)
    return policy


def get_active_policy(db: Session):
    """Get the currently active policy."""
    return db.query(Policy).filter(Policy.is_active == True, Policy.is_deleted == False).first()


def list_policies(db: Session):
    """List all policies."""
    return db.query(Policy).filter(Policy.is_deleted == False).all()


def get_policy(db: Session, policy_id: str):
    """Get a specific policy with its rules."""
    policy = db.query(Policy).filter(Policy.id == policy_id, Policy.is_deleted == False).first()
    if policy:
        policy.rules  # Load rules
    return policy
