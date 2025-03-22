# app/routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.dependencies import get_user_service, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, user_service = Depends(get_user_service)):
    return user_service.create_user(user.username, user.email, user.password)

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user(user: UserUpdate, current_user = Depends(get_current_user), user_service = Depends(get_user_service)):
    updated = user_service.update_user(current_user.id, user.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated

@router.delete("/me")
def delete_current_user(current_user = Depends(get_current_user), user_service = Depends(get_user_service)):
    success = user_service.delete_user(current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User deleted"}
