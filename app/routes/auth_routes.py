# app/routes/auth_routes.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_auth_service, get_user_service
from app.schemas.auth import LoginRequest, RegisterResponse, Token, LoginResponse
from app.schemas.user import UserCreate

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse)
def register_user(
    user: UserCreate,
    user_service=Depends(get_user_service),
    auth_service=Depends(get_auth_service),
):
    new_user = user_service.create_user(user.username, user.email, user.password)
    # Create token data with user ID as string
    token_data = {
        "id": str(new_user.id),
        "username": new_user.username,
        "email": new_user.email,
        "role": new_user.role,
    }
    access_token = auth_service.create_access_token(data=token_data, expires_delta=timedelta(days=1))
    return {
        "user": new_user,
        "token": {"access_token": access_token, "token_type": "bearer"},
    }


@router.post("/login", response_model=LoginResponse)
def login(
    login_request: LoginRequest,
    auth_service=Depends(get_auth_service),
    user_service=Depends(get_user_service),
):
    user = auth_service.authenticate_user(
        login_request.username, login_request.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = auth_service.create_access_token(data=user, expires_delta=timedelta(days=1))
    return {
        "user": user,
        "token": {"access_token": access_token, "token_type": "bearer"},
    }
