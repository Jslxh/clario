import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.user import User
from app.models.role import Role, ROLE_ADMIN, ROLE_ANALYST, ROLE_USER, SYSTEM_ROLES
from app.schemas.user import UserRead, UserUpdate, RoleRead
from app.api.deps import require_roles
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User & Role Management"])


@router.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
    summary="List Enterprise Users",
    description="Retrieve paginated list of enterprise users with assigned roles. Restricted to Admin role.",
)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_ADMIN])),
):
    query = db.query(User).options(joinedload(User.roles))
    if department:
        query = query.filter(User.department == department)
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [UserRead.model_validate(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get User Specifications",
    description="Retrieve single user profile, roles, and status. Restricted to Admin role.",
)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_ADMIN])),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user UUID: {user_id}",
        ) from err

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update User Attributes and Role",
    description="Modify a user's name, department, active status, or RBAC role. Restricted to Admin role.",
)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_ADMIN])),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user UUID: {user_id}",
        ) from err

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    previous_role = user.roles[0].name if user.roles else "user"

    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.department is not None:
        user.department = payload.department.strip() if payload.department else None
    if payload.is_active is not None:
        user.is_active = payload.is_active

    # Role update
    if payload.role is not None:
        normalized_role = payload.role.strip().lower()
        if normalized_role not in SYSTEM_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{payload.role}'. Supported roles: {SYSTEM_ROLES}",
            )

        target_role = db.query(Role).filter(Role.name == normalized_role).first()
        if not target_role:
            target_role = Role(
                id=uuid.uuid4(),
                name=normalized_role,
                description=f"System {normalized_role.capitalize()} Role",
            )
            db.add(target_role)
            db.flush()

        user.roles = [target_role]

    db.commit()
    db.refresh(user)

    # Audit role or status change
    try:
        audit_service.log_event(
            db=db,
            action="update_user",
            resource_type="user",
            user_id=current_user.id,
            resource_id=str(user.id),
            details={
                "target_email": user.email,
                "previous_role": previous_role,
                "new_role": user.roles[0].name if user.roles else None,
                "department": user.department,
                "is_active": user.is_active,
            },
        )
    except Exception as audit_err:
        logger.warning(f"Failed to record user update audit log: {audit_err}")

    return UserRead.model_validate(user)

