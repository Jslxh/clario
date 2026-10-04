import uuid
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "secret",
    "api_key",
    "authorization",
    "key",
}


def sanitize_details(details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Recursively scrub sensitive keys (passwords, tokens, secrets) from audit log details."""
    if not details or not isinstance(details, dict):
        return None

    sanitized = {}
    for k, v in details.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            continue
        if isinstance(v, dict):
            sanitized[k] = sanitize_details(v)
        else:
            sanitized[k] = v
    return sanitized


class AuditService:
    """Service handling structured security and governance audit trail recording."""

    def log_event(
        self,
        db: Session,
        action: str,
        resource_type: str,
        user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create and persist an audit log entry with sensitive fields sanitized."""
        clean_details = sanitize_details(details)

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action.strip().lower(),
            resource_type=resource_type.strip().lower(),
            resource_id=str(resource_id) if resource_id else None,
            details=clean_details,
        )
        try:
            db.add(audit_entry)
            db.commit()
            db.refresh(audit_entry)
            logger.info(f"Audit log recorded: action={action} resource={resource_type} user={user_id}")
            return audit_entry
        except Exception as err:
            db.rollback()
            logger.error(f"Failed to record audit log event: {err}")
            return audit_entry

    def list_logs(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 50,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> List[AuditLog]:
        """Retrieve paginated audit logs with optional filtering."""
        query = db.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action.strip().lower())
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type.strip().lower())
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        return (
            query.order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


audit_service = AuditService()
