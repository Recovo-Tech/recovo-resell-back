from app.models.tenant import Tenant
from app.repositories.base import BaseRepository
from uuid import UUID


class TenantRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, Tenant)

    def list_all(self):
        return self.db.query(self.model).all()

    def get_by_id(self, user_id: UUID):
        return self.db.query(self.model).filter(self.model.id == user_id).first()
