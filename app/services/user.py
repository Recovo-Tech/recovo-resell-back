import bcrypt
from fastapi import HTTPException
from uuid import UUID

from app.models.user import User
from app.repositories import UserRepository


class UserService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    def get_user_by_id(self, user_id: UUID):
        return self.repo.get_by_id(user_id)

    def get_user_by_username(self, username: str):
        return self.repo.get_by_username(username)

    def create_user(
        self, username: str, email: str, password: str, role: str = "client"
    ):
        existing_user = self.repo.get_by_username_or_email(username, email)
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Username or email already in use"
            )

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            role=role or "client",
        )
        return self.repo.create(new_user)

    def update_user(self, user_id: UUID, update_data: dict):
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        if "password" in update_data and update_data["password"]:
            hashed = bcrypt.hashpw(
                update_data["password"].encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            update_data["hashed_password"] = hashed
            del update_data["password"]

        return self.repo.update(user, update_data)

    def delete_user(self, user_id: UUID):
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        self.repo.delete(user)
        return True

    def list_users(self):
        return self.repo.list_all()

    def update_user_role(self, user_id: UUID, role: str):
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        user.role = role
        self.repo.db.commit()
        self.repo.db.refresh(user)
        return user
