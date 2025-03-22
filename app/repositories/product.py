from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, Product)

    def get_by_name(self, name: str):
        return self.db.query(self.model).filter(self.model.name == name).all()
