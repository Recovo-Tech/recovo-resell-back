# app/routes/user_routes.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import admin_required, get_current_user, get_user_service
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, user_service=Depends(get_user_service)):
    # The role is intentionally not passed to the service layer.
    # The service will use the default role "client".
    return user_service.create_user(user.username, user.email, user.password)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user: UserUpdate,
    current_user=Depends(get_current_user),
    user_service=Depends(get_user_service),
):

    updated = user_service.update_user(
        current_user.id, user.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="error.user_not_found")
    return updated


@router.delete("/me")
def delete_current_user(
    current_user=Depends(get_current_user), user_service=Depends(get_user_service)
):
    success = user_service.delete_user(current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="error.user_not_found")
    return {"detail": "User deleted"}


@router.get(
    "/", response_model=list[UserResponse], dependencies=[Depends(admin_required)]
)
def list_users(user_service=Depends(get_user_service)):
    return user_service.list_users()


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(admin_required)],
)
def update_user_role(user_id: UUID, role: str, user_service=Depends(get_user_service)):
    updated = user_service.update_user_role(user_id, role)
    if not updated:
        raise HTTPException(status_code=404, detail="error.user_not_found")
    return updated
