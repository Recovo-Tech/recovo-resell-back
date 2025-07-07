# app/routes/auth_routes.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services import AuthService, TenantService

from app.config.db_config import get_db
from app.models.tenant import Tenant
from app.dependencies import get_auth_service, get_user_service, get_tenant_service
from app.schemas.auth import LoginRequest, RegisterResponse, Token, LoginResponse
from app.schemas.user import UserCreate

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse)
def register_user(
    user: UserCreate,
    user_service=Depends(get_user_service),
    auth_service=Depends(get_auth_service),
    tenant_service=Depends(get_tenant_service),
):
    # Validate tenant exists and is active by name
    tenant = tenant_service.get_tenant_by_name(user.tenant_name)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"error.invalid_tenant_name '{user.tenant_name}' or tenant is not active",
        )

    if user.password != user.password_confirmation:
        raise HTTPException(
            status_code=400, detail="error.password_and_confirmation_do_not_match"
        )
    new_user = user_service.create_user(
        user.username, user.email, user.password, tenant.id, user.name, user.surname
    )
    # Create token data with user ID and tenant ID as strings
    token_data = {
        "id": str(new_user.id),
        "tenant_id": str(new_user.tenant_id),
        "username": new_user.username,
        "email": new_user.email,
        "role": new_user.role,
    }
    access_token = auth_service.create_access_token(
        data=token_data, expires_delta=timedelta(days=1)
    )
    return {
        "user": new_user,
        "token": {"access_token": access_token, "token_type": "bearer"},
    }


@router.post("/login", 
    summary="User Login", 
    description="Login with username, password and tenant name. Returns user info and Bearer token.",
    response_model=LoginResponse
)
async def login(
    request: LoginRequest,
    auth_service=Depends(get_auth_service),
    tenant_service: TenantService = Depends(get_tenant_service),
):
    """Login endpoint that requires tenant_name for proper tenant isolation"""
    try:
        # First, validate that the tenant exists and is active
        tenant = tenant_service.get_tenant_by_name(request.tenant_name)
        if not tenant or not tenant.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"error.invalid_tenant_name '{request.tenant_name}' or tenant is not active",
            )

        # Authenticate user within the specific tenant
        user = auth_service.authenticate_user(
            request.username, request.password, tenant.id
        )
        if not user:
            raise HTTPException(status_code=401, detail="error.invalid_username_or_password")

        # Create JWT token with tenant context

        access_token = auth_service.create_access_token(
            data=user, expires_delta=timedelta(days=7)
        )

        return {
            "user": user,
            "token": {"access_token": access_token, "token_type": "bearer"},
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error.login_failed: {str(e)}")
