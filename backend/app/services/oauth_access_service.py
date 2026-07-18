"""Email-allowlist authorization for verified OAuth identities.

Supabase Auth authenticates the person.  This service decides whether that verified
email has an active application account and resolves the application's own
database-backed roles/permissions.  It intentionally never accepts role
claims from an identity provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.supabase_auth import SupabaseIdentity
from app.core.config import Settings
from app.models.department import Department
from app.models.organization import Organization
from app.models.user import User
from app.services import user_service


class OAuthAccessDeniedError(RuntimeError):
    """A verified identity is not on the active application email allowlist."""

    public_message = "Your account has not been granted access to this platform."


class OAuthBootstrapConfigurationError(RuntimeError):
    """The configured first-admin identity cannot be provisioned safely."""


def _normalise_configured_email(value: str) -> str:
    if not value.strip():
        raise OAuthBootstrapConfigurationError("SUPER_ADMIN_EMAIL is required for first OAuth admin setup")
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise OAuthBootstrapConfigurationError("SUPER_ADMIN_EMAIL is invalid") from exc


def _active_users_for_email(db: Session, email: str) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(func.lower(User.email) == email.lower(), User.is_deleted.is_(False))
            .order_by(User.created_at, User.id)
        ).all()
    )


def _bootstrap_organization_and_department(db: Session, settings: Settings) -> tuple[Organization, Department]:
    organizations = list(
        db.scalars(
            select(Organization).where(
                Organization.is_deleted.is_(False), Organization.status == "active"
            )
        ).all()
    )
    if len(organizations) > 1:
        raise OAuthBootstrapConfigurationError(
            "Cannot choose an organization for the first OAuth administrator"
        )

    if organizations:
        organization = organizations[0]
    else:
        conflicting_organization = db.scalar(
            select(Organization.id).where(Organization.code == settings.default_organization_code)
        )
        if conflicting_organization is not None:
            raise OAuthBootstrapConfigurationError("Configured default organization code is already in use")
        organization = Organization(
            name=settings.default_organization_name.strip(),
            code=settings.default_organization_code.strip().upper(),
            status="active",
        )
        db.add(organization)
        db.flush()

    departments = list(
        db.scalars(
            select(Department)
            .where(
                Department.organization_id == organization.id,
                Department.is_deleted.is_(False),
                Department.status == "active",
            )
            .order_by(Department.created_at, Department.id)
        ).all()
    )
    if departments:
        return organization, departments[0]

    conflicting_department = db.scalar(
        select(Department.id).where(
            Department.organization_id == organization.id,
            Department.code == settings.default_department_code.strip().upper(),
        )
    )
    if conflicting_department is not None:
        raise OAuthBootstrapConfigurationError("Configured default department code is already in use")
    department = Department(
        organization_id=organization.id,
        name=settings.default_department_name.strip(),
        code=settings.default_department_code.strip().upper(),
        status="active",
    )
    db.add(department)
    db.flush()
    return organization, department


def _bootstrap_super_administrator(
    db: Session, *, identity: SupabaseIdentity, settings: Settings
) -> User:
    organization, department = _bootstrap_organization_and_department(db, settings)
    created = user_service.create_user(
        db,
        organization_id=organization.id,
        department_id=department.id,
        email=identity.email,
        full_name=identity.email.split("@", 1)[0].replace(".", " ").title() or "Platform Administrator",
        role_codes=["administrator"],
        manager_id=None,
        external_auth_subject=identity.subject,
    )
    user = db.scalar(select(User).where(User.id == UUID(str(created["id"]))))
    if user is None:  # Defensive: the creation service committed successfully.
        raise OAuthBootstrapConfigurationError("Unable to provision the first OAuth administrator")
    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def resolve_oauth_user(db: Session, *, identity: SupabaseIdentity, settings: Settings) -> User:
    """Return an allowlisted account or safely bootstrap the configured admin."""

    users = _active_users_for_email(db, identity.email)
    active_users = [user for user in users if user.status == "active"]
    if len(active_users) > 1:
        # An email can be unique per organization in historic data.  Never
        # guess a tenant for a shared identity.
        raise OAuthBootstrapConfigurationError("OAuth email is ambiguous across application organizations")

    super_admin_email = _normalise_configured_email(settings.super_admin_email)
    if not active_users:
        if identity.email != super_admin_email:
            raise OAuthAccessDeniedError()
        # An inactive/deleted row must be reactivated deliberately through
        # application administration; do not let configuration resurrect it.
        if users:
            raise OAuthAccessDeniedError()
        try:
            return _bootstrap_super_administrator(db, identity=identity, settings=settings)
        except IntegrityError as exc:
            # React development mode, multiple browser tabs, or an operator
            # signing in at the same moment can race the empty-database path.
            # The unique allowlist constraints remain the authority; once a
            # competing request wins, bind/return that same admin instead of
            # surfacing a transient 500 or creating a second tenant.
            db.rollback()
            concurrent_users = [
                user
                for user in _active_users_for_email(db, identity.email)
                if user.status == "active"
            ]
            if len(concurrent_users) != 1:
                raise OAuthBootstrapConfigurationError(
                    "Unable to provision the first OAuth administrator safely"
                ) from exc
            user = user_service.ensure_administrator_role(db, concurrent_users[0])
            try:
                return user_service.link_external_identity(db, user, subject=identity.subject)
            except user_service.UserServiceError as link_error:
                raise OAuthAccessDeniedError() from link_error

    user = active_users[0]
    if identity.email == super_admin_email:
        user = user_service.ensure_administrator_role(db, user)
    try:
        return user_service.link_external_identity(db, user, subject=identity.subject)
    except user_service.UserServiceError as exc:
        # Identity binding failures intentionally share the generic public
        # allowlist response; the API should not disclose account linkage.
        if exc.status_code in {401, 403}:
            raise OAuthAccessDeniedError() from exc
        raise
