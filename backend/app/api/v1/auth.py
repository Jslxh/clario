import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.role import Role, ROLE_USER, ROLE_ADMIN, ROLE_ANALYST, SYSTEM_ROLES
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    req: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    # Resolve or create role
    target_role_name = req.role if req.role in SYSTEM_ROLES else ROLE_USER
    role = db.query(Role).filter(Role.name == target_role_name).first()
    if not role:
        role = Role(name=target_role_name, description=f"System role: {target_role_name}")
        db.add(role)
        db.flush()

    new_user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        department=req.department,
        is_active=True,
    )
    new_user.roles.append(role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    role_names = [r.name for r in new_user.roles]
    token = create_access_token(
        subject=str(new_user.id),
        email=new_user.email,
        roles=role_names,
        department=new_user.department,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(new_user),
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    role_names = [r.name for r in user.roles]
    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        roles=role_names,
        department=user.department,
    )

    from app.services.audit_service import audit_service
    audit_service.log_event(
        db=db,
        action="login",
        resource_type="auth",
        user_id=user.id,
        details={"email": user.email, "department": user.department},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )



@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserRead.model_validate(current_user)
