"""Build a safe, organization-scoped reporting hierarchy."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.user_service import role_codes_for_user


def build_org_tree(db: Session, organization_id: uuid.UUID) -> list[dict[str, object]]:
    """Return active users as nested reporting nodes without trusting the tree.

    Data imported from another HR system can contain a cycle even though normal
    user updates reject one.  The path guard deliberately leaves the repeated
    node unexpanded so a malformed relationship cannot crash the UI.
    """

    users = db.scalars(
        select(User)
        .where(
            User.organization_id == organization_id,
            User.is_deleted.is_(False),
            User.status == "active",
        )
        .order_by(User.full_name, User.email)
    ).all()
    by_id = {user.id: user for user in users}
    children: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    roots: list[uuid.UUID] = []

    for user in users:
        manager_id = user.manager_user_id
        if manager_id and manager_id in by_id and manager_id != user.id:
            children[manager_id].append(user.id)
        else:
            roots.append(user.id)

    for report_ids in children.values():
        report_ids.sort(key=lambda report_id: (by_id[report_id].full_name.lower(), by_id[report_id].email.lower()))
    roots.sort(key=lambda user_id: (by_id[user_id].full_name.lower(), by_id[user_id].email.lower()))

    expanded: set[uuid.UUID] = set()

    def node_for(user_id: uuid.UUID, ancestors: set[uuid.UUID]) -> dict[str, object]:
        user = by_id[user_id]
        expanded.add(user_id)
        next_ancestors = ancestors | {user_id}
        reports = [
            node_for(report_id, next_ancestors)
            for report_id in children.get(user_id, [])
            if report_id not in next_ancestors
        ]
        return {
            "id": str(user.id),
            "name": user.full_name,
            "email": user.email,
            "roles": role_codes_for_user(db, user.id),
            "reports": reports,
        }

    result = [node_for(user_id, set()) for user_id in roots]
    # A malformed cycle has no natural root.  Present each remaining component
    # once rather than silently hiding users from administrators.
    for user_id in sorted(
        set(by_id) - expanded,
        key=lambda candidate: (by_id[candidate].full_name.lower(), by_id[candidate].email.lower()),
    ):
        result.append(node_for(user_id, set()))
    return result
