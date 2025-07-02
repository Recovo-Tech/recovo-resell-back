# app/routes/auth_routes.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
    # Validate tenant exists and is active by name/subdomain
    tenant = tenant_service.get_tenant_by_subdomain(user.tenant_name)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid tenant name '{user.tenant_name}' or tenant is not active"
        )
    
    if user.password != user.password_confirmation:
        raise HTTPException(
            status_code=400, detail="Password and confirmation do not match"
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


@router.post("/login", response_model=LoginResponse)
def login(
    login_request: LoginRequest,
    auth_service=Depends(get_auth_service),
):  
    # For login, we need to search across all tenants first, then validate
    user_data = auth_service.authenticate_user_global(
        login_request.username, login_request.password
    )
    if not user_data:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # user_data is already a dict with the token data we need
    access_token = auth_service.create_access_token(
        data=user_data, expires_delta=timedelta(days=1)
    )
    return {
        "user": user_data,  # user_data is already in the correct format
        "token": {"access_token": access_token, "token_type": "bearer"},
    }
