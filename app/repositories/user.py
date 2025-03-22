from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, User)

    def get_by_username(self, username: str):
        return self.db.query(self.model).filter(self.model.username == username).first()
