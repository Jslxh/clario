import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.role import ROLE_ADMIN, ROLE_ANALYST
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=List[AuditLogRead],
    status_code=status.HTTP_200_OK,
    summary="List Governance Audit Logs",
    description="Retrieve paginated security, access, and governance audit records. Restricted to Admin and Analyst roles.",
)
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_ADMIN, ROLE_ANALYST])),
):
    logs = audit_service.list_logs(
        db=db,
        skip=skip,
        limit=limit,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
    )
    return logs
