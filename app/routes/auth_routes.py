# app/routes/auth_routes.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_auth_service
from app.schemas.auth import LoginRequest, Token

# from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(login_request: LoginRequest, auth_service=Depends(get_auth_service)):
    user_data = auth_service.authenticate_user(
        login_request.username, login_request.password
    )
    if not user_data:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = auth_service.create_access_token(
        data=user_data, expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# @router.post("/login", response_model=Token)
# def login(
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     auth_service = Depends(get_auth_service)
# ):
#     user_data = auth_service.authenticate_user(form_data.username, form_data.password)
#     if not user_data:
#         raise HTTPException(status_code=401, detail="Incorrect username or password")

#     access_token = auth_service.create_access_token(data=user_data)
#     return {"access_token": access_token, "token_type": "bearer"}
